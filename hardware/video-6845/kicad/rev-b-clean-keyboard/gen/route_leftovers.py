#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-20
"""route_leftovers.py [--first] [BOARD.kicad_pcb] - join the nets Freerouting leaves in pieces, on the same two layers.
Run with KiCad's Python after gen/route.py import (gen/build.sh does). DRC is the judge afterwards.

Freerouting adds this card's keyboard section to Rev B's copper, which is locked. It leaves a few long connections
open whatever the order (four to six of 143 on every one of sixteen runs): each must cross 70 to 130 mm of Rev B's
tracks, and it gives up where a way exists that it does not find. This is a plain maze router for those: slower, but
it tries every way there is. (hardware/video-g/kicad/common/route_leftovers.py, from memory Rev E, routes from one open
pad; here both ends of an open connection are whole pieces of a net, so this one works from piece to piece.)

  * the pieces: every pad, track and via of a net, grouped by what touches what. A net in more than one piece is open
  * the grid: 0.127 mm (5 mil), laid on J1's pads, so Rev B's copper (drawn on Eagle's 25 and 50 mil grids) lies on its
    lines and a new track between two old ones sits where Eagle would have put it
  * a cell is closed to a net if a pad, track or via of another net is nearer than the clearance (0.2 mm) plus half the
    new track's width plus 0.09 mm (what a step between two cell centres can cut off a corner); to a via, the same
    with the via's radius, and any hole nearer than 0.254 mm edge to edge; and 0.5 mm from the board edge.
    A keep-out area (the crystal's footprint has one: no vias under the can) is closed as its rule says
  * the search (A*) runs from every cell of the smallest piece to any cell of another piece of the net: straight and
    slanting steps, a change of layer where a via fits (it costs what 5 mm of track does)
  * the new track is 0.254 mm (0.5 mm for VCC and GND, the Power class), its vias 0.8 / 0.4 mm, as the net classes say
  * last, on the nets it joined and on keyboard.TIDY's: a track end that now touches nothing is cut back to the last place something joins
    the track, and a track left hanging by one end goes. That is for Rev B's select track, cut at IC5 pin 3
    (gen/make_board.py): the new decoder's track joins it part way along, and the piece beyond the join is taken off

--first, before Freerouting: only keyboard.FIRST's connections, while nothing but Rev B's copper is in their way; their tracks
are locked, so Freerouting keeps them. Afterwards, what is left open is joined in the order keyboard.SOON, then by name: left
to the names alone the 6845's E came out 306 mm long with 16 vias (2026-11-24, seed 2); in this order it is 97.
"""
import heapq, math, os, sys, time
from array import array
import pcbnew
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "..", "tools", "kicad"))
import kicad_route

HERE = os.path.dirname(os.path.abspath(__file__)); DEST = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import keyboard as K
_ARGS = [a for a in sys.argv[1:] if a != "--first"]
FIRST = "--first" in sys.argv
PCB = os.path.abspath(_ARGS[0]) if _ARGS else os.environ.get("ROUTE_PCB") or os.path.join(DEST, K.NEW + ".kicad_pcb")
G = 0.127; CLR = 0.2; SLACK = 0.09; VIA_D = 0.8; VIA_DRILL = 0.4; HOLE_GAP = 0.254; EDGE = 0.5
WIDTH = {"VCC": 0.5, "GND": 0.5}; W_DEFAULT = 0.254
STEP, DIAG, VIA_COST = 10, 14, 400
mm, FM = pcbnew.ToMM, pcbnew.FromMM
MANY = 65535


def seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay; L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


class Pad:
    def __init__(self, fp, p):
        self.ref, self.num, self.net = fp.GetReference(), p.GetNumber(), p.GetNetname()
        self.x, self.y = mm(p.GetPosition().x), mm(p.GetPosition().y)
        sx, sy = mm(p.GetSize(pcbnew.F_Cu).x), mm(p.GetSize(pcbnew.F_Cu).y)
        a = math.radians(p.GetOrientationDegrees()); self.ux, self.uy = math.cos(a), -math.sin(a)     # the pad's own x axis
        shape = p.GetShape(pcbnew.F_Cu)
        self.hole = max(mm(p.GetDrillSize().x), mm(p.GetDrillSize().y)) / 2
        if shape == pcbnew.PAD_SHAPE_CIRCLE or (shape == pcbnew.PAD_SHAPE_OVAL and abs(sx - sy) < 1e-6):
            self.kind, self.r, self.h = "round", sx / 2, 0.0
        elif shape == pcbnew.PAD_SHAPE_OVAL:                             # a stadium: a line with a radius
            self.kind, self.r, self.h = "oval", min(sx, sy) / 2, abs(sx - sy) / 2
            if sy > sx: self.ux, self.uy = -self.uy, self.ux             # its long axis is the pad's y
        else:                                                            # a rectangle (rounded, chamfered: taken whole)
            self.kind, self.hx, self.hy = "box", sx / 2, sy / 2
        self.reach = max(sx, sy) / 2 * (1.42 if self.kind == "box" else 1.0)

    def dist(self, x, y):
        """from the point to the pad's copper (0 or less: on it)"""
        dx, dy = x - self.x, y - self.y
        if self.kind == "round": return math.hypot(dx, dy) - self.r
        u, v = dx * self.ux + dy * self.uy, -dx * self.uy + dy * self.ux
        if self.kind == "oval":
            return math.hypot(u - max(-self.h, min(self.h, u)), v) - self.r
        qx, qy = abs(u) - self.hx, abs(v) - self.hy
        return math.hypot(max(qx, 0.0), max(qy, 0.0)) + min(max(qx, qy), 0.0)


class Seg:
    def __init__(self, t, layer):
        self.t = t; self.net = t.GetNetname(); self.layer = layer; self.hw = mm(t.GetWidth()) / 2
        self.ax, self.ay, self.bx, self.by = mm(t.GetStart().x), mm(t.GetStart().y), mm(t.GetEnd().x), mm(t.GetEnd().y)


class Via:
    def __init__(self, t):
        self.t = t; self.net = t.GetNetname(); self.x, self.y = mm(t.GetPosition().x), mm(t.GetPosition().y)
        self.r = mm(t.GetWidth(pcbnew.F_Cu)) / 2; self.hole = mm(t.GetDrillValue()) / 2


def load(b):
    pads = [Pad(f, p) for f in b.GetFootprints() for p in f.Pads()]
    segs, vias = [], []
    for t in b.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T: vias.append(Via(t))
        elif t.GetLayer() in (pcbnew.F_Cu, pcbnew.B_Cu): segs.append(Seg(t, 0 if t.GetLayer() == pcbnew.F_Cu else 1))
    return pads, segs, vias


def pieces(net, pads, segs, vias):
    """the net's copper grouped by what touches what -> a list of pieces, each a list of items"""
    items = [p for p in pads if p.net == net] + [s for s in segs if s.net == net] + [v for v in vias if v.net == net]
    parent = list(range(len(items)))
    def find(i):
        while parent[i] != i: parent[i] = parent[parent[i]]; i = parent[i]
        return i
    def touch(a, c):
        if isinstance(a, Seg) and isinstance(c, Seg):
            if a.layer != c.layer: return False
            e = 0.005
            return (seg_dist(a.ax, a.ay, c.ax, c.ay, c.bx, c.by) <= c.hw + e or seg_dist(a.bx, a.by, c.ax, c.ay, c.bx, c.by) <= c.hw + e or
                    seg_dist(c.ax, c.ay, a.ax, a.ay, a.bx, a.by) <= a.hw + e or seg_dist(c.bx, c.by, a.ax, a.ay, a.bx, a.by) <= a.hw + e)
        if isinstance(a, Seg): a, c = c, a
        if isinstance(c, Seg):
            if isinstance(a, Via):
                return seg_dist(a.x, a.y, c.ax, c.ay, c.bx, c.by) <= max(c.hw, a.r) + 0.005
            return a.dist(c.ax, c.ay) <= 0.005 or a.dist(c.bx, c.by) <= 0.005 or seg_dist(a.x, a.y, c.ax, c.ay, c.bx, c.by) <= c.hw + 0.005
        if isinstance(a, Via) and isinstance(c, Via): return math.hypot(a.x - c.x, a.y - c.y) <= a.r + c.r
        if isinstance(a, Via): a, c = c, a
        if isinstance(c, Via): return a.dist(c.x, c.y) <= 0.005
        return False                                                     # two pads: only through copper
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if find(i) != find(j) and touch(items[i], items[j]): parent[find(i)] = find(j)
    out = {}
    for i, it in enumerate(items): out.setdefault(find(i), []).append(it)
    return list(out.values())


class Grid:
    def __init__(self, b, pads, segs, vias, ref):
        eb = b.GetBoardEdgesBoundingBox()
        self.l, self.t, self.r, self.b = mm(eb.GetLeft()), mm(eb.GetTop()), mm(eb.GetRight()), mm(eb.GetBottom())
        self.x0 = ref.x - math.floor((ref.x - self.l) / G) * G; self.y0 = ref.y - math.floor((ref.y - self.t) / G) * G   # on J1's pads
        self.nx = int((self.r - self.x0) / G) + 1; self.ny = int((self.b - self.y0) / G) + 1
        self.ids = {"": 0}
        n = self.nx * self.ny
        # per track width in use: the cells closed to a track's centre line, on each layer; then to a via's centre, and holes
        self.maps = {}; self.vmap = array("H", bytes(2 * n)); self.holes = bytearray(n)
        self.pads, self.segs, self.vias = pads, segs, vias

    def nid(self, net):
        if net not in self.ids: self.ids[net] = len(self.ids)
        return self.ids[net]

    def cell(self, x, y): return int(round((x - self.x0) / G)), int(round((y - self.y0) / G))

    def _stamp(self, a, nid, dist, cx, cy, reach, limit):
        nx, ny = self.nx, self.ny
        i0, i1 = max(0, int((cx - reach - self.x0) / G)), min(nx - 1, int((cx + reach - self.x0) / G) + 1)
        k0, k1 = max(0, int((cy - reach - self.y0) / G)), min(ny - 1, int((cy + reach - self.y0) / G) + 1)
        x0, y0 = self.x0, self.y0
        for k in range(k0, k1 + 1):
            y = y0 + k * G; row = k * nx
            for i in range(i0, i1 + 1):
                if dist(x0 + i * G, y) < limit:
                    v = a[row + i]
                    if v == 0: a[row + i] = nid
                    elif v != nid: a[row + i] = MANY

    def _stamp_seg(self, a, nid, s, limit):
        """a track's capsule: cells within `limit` of its line, walked along it in boxes so a long slanted track costs its
        length, not its bounding box"""
        L = math.hypot(s.bx - s.ax, s.by - s.ay); n = max(1, int(L / 2.0) + 1)
        d = lambda x, y: seg_dist(x, y, s.ax, s.ay, s.bx, s.by)
        if s.ax == s.bx or s.ay == s.by: n = 1                           # upright or level: its box is tight already
        for j in range(n):
            x1, y1 = s.ax + (s.bx - s.ax) * j / n, s.ay + (s.by - s.ay) * j / n
            x2, y2 = s.ax + (s.bx - s.ax) * (j + 1) / n, s.ay + (s.by - s.ay) * (j + 1) / n
            nx, ny = self.nx, self.ny
            i0, i1 = max(0, int((min(x1, x2) - limit - self.x0) / G)), min(nx - 1, int((max(x1, x2) + limit - self.x0) / G) + 1)
            k0, k1 = max(0, int((min(y1, y2) - limit - self.y0) / G)), min(ny - 1, int((max(y1, y2) + limit - self.y0) / G) + 1)
            for k in range(k0, k1 + 1):
                y = self.y0 + k * G; row = k * nx
                for i in range(i0, i1 + 1):
                    if d(self.x0 + i * G, y) < limit:
                        v = a[row + i]
                        if v == 0: a[row + i] = nid
                        elif v != nid: a[row + i] = MANY

    def add(self, item, widths):
        """close the cells round one pad, track or via, in every map"""
        nid = self.nid(item.net); n = self.nx * self.ny
        layers = (item.layer,) if isinstance(item, Seg) else (0, 1)
        for w in widths:
            a = self.maps.setdefault(w, array("H", bytes(2 * 2 * n))); grow = CLR + w / 2 + SLACK
            for Lr in layers:
                view = _Layer(a, Lr * n)
                if isinstance(item, Seg): self._stamp_seg(view, nid, item, item.hw + grow)
                elif isinstance(item, Via): self._stamp(view, nid, lambda x, y: math.hypot(x - item.x, y - item.y), item.x, item.y, item.r + grow, item.r + grow)
                else: self._stamp(view, nid, item.dist, item.x, item.y, item.reach + grow, grow)
        grow = CLR + VIA_D / 2 + SLACK; view = _Layer(self.vmap, 0)       # a via stands on both layers: one map
        if isinstance(item, Seg): self._stamp_seg(view, nid, item, item.hw + grow)
        elif isinstance(item, Via): self._stamp(view, nid, lambda x, y: math.hypot(x - item.x, y - item.y), item.x, item.y, item.r + grow, item.r + grow)
        else: self._stamp(view, nid, item.dist, item.x, item.y, item.reach + grow, grow)
        if not isinstance(item, Seg) and item.hole > 0:                  # hole to hole, whatever the net
            lim = item.hole + VIA_DRILL / 2 + HOLE_GAP + SLACK
            i, k = self.cell(item.x, item.y); r = int(lim / G) + 1
            for kk in range(max(0, k - r), min(self.ny, k + r + 1)):
                for ii in range(max(0, i - r), min(self.nx, i + r + 1)):
                    if math.hypot(self.x0 + ii * G - item.x, self.y0 + kk * G - item.y) < lim: self.holes[kk * self.nx + ii] = 1

    def keep_out(self, box, tracks, vias, layers):
        """a rule area (a footprint's or the board's), taken as its box: closed to tracks on its layers, to vias, or both"""
        i0, k0 = self.cell(box[0], box[1]); i1, k1 = self.cell(box[2], box[3]); n = self.nx * self.ny
        i0, i1 = max(0, i0 - 1), min(self.nx - 1, i1 + 1); k0, k1 = max(0, k0 - 1), min(self.ny - 1, k1 + 1)
        for k in range(k0, k1 + 1):
            row = k * self.nx
            for i in range(i0, i1 + 1):
                if vias: self.holes[row + i] = 1
                if tracks:
                    for a in self.maps.values():
                        for Lr in layers: a[Lr * n + row + i] = MANY

    def cells_of(self, piece):
        """the cells on a piece's own copper: (layer, i, k)"""
        out = set()
        for it in piece:
            if isinstance(it, Seg):
                L = math.hypot(it.bx - it.ax, it.by - it.ay); n = max(1, int(L / (G / 2)))
                for j in range(n + 1):
                    x, y = it.ax + (it.bx - it.ax) * j / n, it.ay + (it.by - it.ay) * j / n
                    i, k = self.cell(x, y)
                    if seg_dist(self.x0 + i * G, self.y0 + k * G, it.ax, it.ay, it.bx, it.by) <= it.hw: out.add((it.layer, i, k))
            else:
                i, k = self.cell(it.x, it.y); out |= {(0, i, k), (1, i, k)}
        return out


class _Layer:
    """one layer's part of a map, addressed from 0"""
    __slots__ = ("a", "off")
    def __init__(self, a, off): self.a, self.off = a, off
    def __getitem__(self, i): return self.a[self.off + i]
    def __setitem__(self, i, v): self.a[self.off + i] = v


def search(g, net, w, src, dst):
    """A* from the cells src to any of dst -> the path [(layer, i, k), ...] or None"""
    nx, ny = g.nx, g.ny; n = nx * ny; a = g.maps[w]; vm = g.vmap; holes = g.holes; nid = g.nid(net)
    ei = int((EDGE + w / 2 - (g.x0 - g.l)) / G) + 1; ek = int((EDGE + w / 2 - (g.y0 - g.t)) / G) + 1
    imin, imax = max(0, ei), min(nx - 1, int((g.r - EDGE - w / 2 - g.x0) / G))
    kmin, kmax = max(0, ek), min(ny - 1, int((g.b - EDGE - w / 2 - g.y0) / G))
    goal = set(L * n + k * nx + i for L, i, k in dst)
    ti0, ti1 = min(i for _, i, _ in dst), max(i for _, i, _ in dst); tk0, tk1 = min(k for _, _, k in dst), max(k for _, _, k in dst)
    def h(i, k):
        dx = ti0 - i if i < ti0 else i - ti1 if i > ti1 else 0; dy = tk0 - k if k < tk0 else k - tk1 if k > tk1 else 0
        return STEP * max(dx, dy) + (DIAG - STEP) * min(dx, dy)
    INF = 1 << 30; dist = {}; prev = {}; pq = []
    for L, i, k in src:
        s = L * n + k * nx + i; dist[s] = 0; heapq.heappush(pq, (h(i, k), 0, s))
    moves = ((1, 0, STEP), (-1, 0, STEP), (0, 1, STEP), (0, -1, STEP), (1, 1, DIAG), (1, -1, DIAG), (-1, 1, DIAG), (-1, -1, DIAG))
    found = None; pops = 0
    while pq:
        f, d, s = heapq.heappop(pq)
        if d > dist.get(s, INF): continue
        if s in goal and d > 0: found = s; break
        pops += 1
        L, rest = divmod(s, n); k, i = divmod(rest, nx); base = L * n
        for di, dk, c in moves:
            i2, k2 = i + di, k + dk
            if i2 < imin or i2 > imax or k2 < kmin or k2 > kmax: continue
            s2 = base + k2 * nx + i2; v = a[s2]
            if v != 0 and v != nid and s2 not in goal: continue
            nd = d + c
            if nd < dist.get(s2, INF): dist[s2] = nd; prev[s2] = s; heapq.heappush(pq, (nd + h(i2, k2), nd, s2))
        c2 = k * nx + i; v = vm[c2]
        if (v == 0 or v == nid) and not holes[c2]:                        # a via fits here
            s2 = (1 - L) * n + c2; v2 = a[s2]
            if v2 == 0 or v2 == nid:
                nd = d + VIA_COST
                if nd < dist.get(s2, INF): dist[s2] = nd; prev[s2] = s; heapq.heappush(pq, (nd + h(i, k), nd, s2))
    if found is None: return None, pops
    path = [found]
    while path[-1] in prev: path.append(prev[path[-1]])
    path.reverse()
    return [(s // n, (s % n) % nx, (s % n) // nx) for s in path], pops


def lay(b, g, net, w, path):
    """the path as tracks and vias on the board -> the new items as Seg / Via objects"""
    ni = b.FindNet(net); new = []; P = lambda i, k: pcbnew.VECTOR2I(FM(g.x0 + i * G), FM(g.y0 + k * G))
    def track(run):
        if len(run) < 2: return
        L = run[0][0]; pts = [run[0]]
        for j in range(1, len(run) - 1):                                # only where the direction changes
            a, c, e = pts[-1], run[j], run[j + 1]
            if (c[1] - a[1]) * (e[2] - c[2]) != (c[2] - a[2]) * (e[1] - c[1]): pts.append(c)
        pts.append(run[-1])
        for a, c in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(b); t.SetStart(P(a[1], a[2])); t.SetEnd(P(c[1], c[2])); t.SetLayer(pcbnew.F_Cu if L == 0 else pcbnew.B_Cu)
            t.SetWidth(FM(w)); t.SetNet(ni); b.Add(t); new.append(Seg(t, L))
    run = [path[0]]
    for s in path[1:]:
        if s[0] != run[-1][0]:
            track(run)
            v = pcbnew.PCB_VIA(b); v.SetPosition(P(s[1], s[2])); v.SetWidth(pcbnew.F_Cu, FM(VIA_D)) if _via_width_by_layer else v.SetWidth(FM(VIA_D))
            v.SetDrill(FM(VIA_DRILL)); v.SetNet(ni); b.Add(v); new.append(Via(v)); run = [s]
        else: run.append(s)
    track(run)
    return new


def trim(net, pads, segs, vias):
    """cut back the net's track ends that touch nothing, and a via left with no pad and copper on one layer only -> (tracks
    shortened, the uuids of tracks and vias to take off)"""
    mine = lambda: [s for s in segs if s.net == net and not getattr(s, "gone", False)]
    np_, nv = [p for p in pads if p.net == net], [v for v in vias if v.net == net]
    short = 0; gone = []
    def held(s, x, y):                                                   # does anything else of the net touch this point?
        return (any(p.dist(x, y) <= 0.005 for p in np_) or any(math.hypot(v.x - x, v.y - y) <= v.r for v in nv) or
                any(o is not s and o.layer == s.layer and seg_dist(x, y, o.ax, o.ay, o.bx, o.by) <= o.hw + 0.005 for o in mine()))
    changed = True
    while changed:
        changed = False
        for s in mine():
            L = math.hypot(s.bx - s.ax, s.by - s.ay)
            ends = [held(s, s.ax, s.ay), held(s, s.bx, s.by)]
            if all(ends) or L == 0: continue
            # where along the track something joins it: other tracks' ends, vias, pads (0 = its start, 1 = its end)
            pts = [(o.ax, o.ay) for o in mine() if o is not s and o.layer == s.layer] + [(o.bx, o.by) for o in mine() if o is not s and o.layer == s.layer]
            pts += [(v.x, v.y) for v in nv] + [(p.x, p.y) for p in np_]
            at = sorted(((x - s.ax) * (s.bx - s.ax) + (y - s.ay) * (s.by - s.ay)) / (L * L) for x, y in pts
                        if seg_dist(x, y, s.ax, s.ay, s.bx, s.by) <= s.hw + 0.005)
            at = [max(0.0, min(1.0, t)) for t in at]
            lo = min(at) if at else None; hi = max(at) if at else None
            if not at or (hi - lo) * L < 0.01:                           # held at one place only, or nowhere: it goes
                s.gone = True; gone.append(s.t.m_Uuid.AsString()); changed = True; continue
            x1, y1 = s.ax + (s.bx - s.ax) * lo, s.ay + (s.by - s.ay) * lo; x2, y2 = s.ax + (s.bx - s.ax) * hi, s.ay + (s.by - s.ay) * hi
            if not ends[0] and lo * L > 0.01:
                s.ax, s.ay = x1, y1; s.t.SetStart(pcbnew.VECTOR2I(FM(x1), FM(y1))); short += 1; changed = True
            if not ends[1] and (1 - hi) * L > 0.01:
                s.bx, s.by = x2, y2; s.t.SetEnd(pcbnew.VECTOR2I(FM(x2), FM(y2))); short += 1; changed = True
        for v in list(nv):                                               # (the -MRW via by the 6845's old R/W track, 2026-11-24)
            on = {o.layer for o in mine() if seg_dist(v.x, v.y, o.ax, o.ay, o.bx, o.by) <= max(o.hw, v.r) + 0.005}
            if len(on) < 2 and not any(p.dist(v.x, v.y) <= 0.005 for p in np_):
                nv.remove(v); gone.append(v.t.m_Uuid.AsString()); changed = True
    return short, gone


try:
    pcbnew.PCB_VIA(pcbnew.BOARD()).SetWidth(pcbnew.F_Cu, 1000); _via_width_by_layer = True
except TypeError:
    _via_width_by_layer = False


def first():
    """keyboard.FIRST's connections, in its order: (reference, pin, a pad of the piece to join, or None for any)"""
    b = pcbnew.LoadBoard(PCB); pads, segs, vias = load(b); w = W_DEFAULT
    g = Grid(b, pads, segs, vias, next(p for p in pads if p.ref == "J1" and p.num == "1"))
    for it in pads + segs + vias: g.add(it, [w])
    for z in [z for f in b.GetFootprints() for z in f.Zones() if z.GetIsRuleArea()]:
        bb = z.GetBoundingBox(); grow = VIA_D / 2 + SLACK
        g.keep_out((mm(bb.GetLeft()) - grow, mm(bb.GetTop()) - grow, mm(bb.GetRight()) + grow, mm(bb.GetBottom()) + grow),
                   z.GetDoNotAllowTracks(), z.GetDoNotAllowVias(), [Lr for Lr, lay_ in ((0, pcbnew.F_Cu), (1, pcbnew.B_Cu)) if z.IsOnLayer(lay_)])
    bad = 0
    for ref, num, to in K.FIRST:
        net = next(p.net for p in pads if (p.ref, p.num) == (ref, num)); pc = pieces(net, pads, segs, vias)
        has = lambda p, r: any(isinstance(i, Pad) and (i.ref, i.num) == r for i in p)
        src = next(p for p in pc if has(p, (ref, num))); dst = [p for p in pc if p is not src and (to is None or has(p, to))]
        cells = g.cells_of(src); path, pops = search(g, net, w, cells, set().union(*[g.cells_of(p) for p in dst]) - cells)
        if not path: print("  first: %s.%s (%s) NO WAY" % (ref, num, net)); bad += 1; continue
        new = lay(b, g, net, w, path)
        for it in new: (segs if isinstance(it, Seg) else vias).append(it); g.add(it, [w])
        print("  first: %s.%s (%s): %.1f mm, %d vias" % (ref, num, net.split("/")[-1], sum(math.hypot(s.bx - s.ax, s.by - s.ay) for s in new if isinstance(s, Seg)), sum(isinstance(s, Via) for s in new)))
    for t in b.GetTracks(): t.SetLocked(True)
    pcbnew.SaveBoard(PCB, b); sys.stdout.flush(); os._exit(1 if bad else 0)


def main():
    if FIRST: first()
    t0 = time.time()
    b = pcbnew.LoadBoard(PCB); pads, segs, vias = load(b)
    nets = sorted({p.net for p in pads if p.net and not p.net.startswith("unconnected-")})
    todo = {}
    for net in nets:
        pc = pieces(net, pads, segs, vias)
        if len(pc) > 1: todo[net] = pc
    print("route_leftovers: %d nets in more than one piece: %s" % (len(todo), ", ".join("%s (%d)" % (n.split("/")[-1], len(p)) for n, p in todo.items()) or "none"))
    ref = next(p for p in pads if p.ref == "J1" and p.num == "1")
    g = Grid(b, pads, segs, vias, ref); widths = sorted({WIDTH.get(n.split("/")[-1], W_DEFAULT) for n in todo})
    if todo:
        for it in pads + segs + vias: g.add(it, widths)
        areas = [z for z in b.Zones() if z.GetIsRuleArea()] + [z for f in b.GetFootprints() for z in f.Zones() if z.GetIsRuleArea()]
        for z in areas:                                   # keep-outs: the crystal's footprint has one (no vias under the can)
            bb = z.GetBoundingBox(); grow = VIA_D / 2 + SLACK
            g.keep_out((mm(bb.GetLeft()) - grow, mm(bb.GetTop()) - grow, mm(bb.GetRight()) + grow, mm(bb.GetBottom()) + grow),
                       z.GetDoNotAllowTracks(), z.GetDoNotAllowVias(), [Lr for Lr, lay_ in ((0, pcbnew.F_Cu), (1, pcbnew.B_Cu)) if z.IsOnLayer(lay_)])
        print("  the grid: %d x %d cells of %.3f mm, %d pads, %d tracks, %d vias, %d keep-out areas (%.0f s)" % (g.nx, g.ny, G, len(pads), len(segs), len(vias), len(areas), time.time() - t0))
    left = 0; added = 0
    soon = {n: k for k, n in enumerate(K.SOON)}
    for net in sorted(todo, key=lambda n: (n.split("/")[-1] in WIDTH, soon.get(n.split("/")[-1], 99), n)):       # the signals first, then the supplies
        w = WIDTH.get(net.split("/")[-1], W_DEFAULT)
        while True:
            pc = [p for p in pieces(net, pads, segs, vias) if any(isinstance(i, Pad) for i in p)]
            if len(pc) < 2: break                                        # (a piece with no pad is an old track's end: trimmed below)
            pc.sort(key=lambda p: sum(isinstance(i, Pad) for i in p) * 1000 + len(p))
            src = g.cells_of(pc[0]); dst = set()
            for other in pc[1:]: dst |= g.cells_of(other)
            t1 = time.time(); path, pops = search(g, net, w, src, dst - src)
            name = net.split("/")[-1]; what = ", ".join(sorted("%s.%s" % (i.ref, i.num) for i in pc[0] if isinstance(i, Pad))[:4]) or "a track"
            if not path:
                print("  %-10s NO WAY from the piece with %s (%d cells tried, %.0f s)" % (name, what, pops, time.time() - t1)); left += 1; break
            new = lay(b, g, net, w, path)
            for it in new:
                (segs if isinstance(it, Seg) else vias).append(it); g.add(it, widths)
            added += len(new)
            print("  %-10s joined (%s): %.1f mm, %d vias (%d cells tried, %.0f s)" % (
                name, what, sum(math.hypot(s.bx - s.ax, s.by - s.ay) for s in new if isinstance(s, Seg)), sum(isinstance(s, Via) for s in new), pops, time.time() - t1))
    short = 0; gone = []
    tidy = {p.net for ref, num in K.TIDY for p in pads if (p.ref, p.num) == (ref, num)}
    for net in sorted(set(todo) | tidy):
        n, u = trim(net, pads, segs, vias); short += n; gone += u
    pcbnew.SaveBoard(PCB, b)
    if gone:                                              # off the file's text (pcbnew loses its place when items are removed)
        forms = kicad_route.top_forms(open(PCB).read())
        keep = [f for f in forms if not (f.startswith(("(segment", "(via")) and any(u in f for u in gone))]
        assert len(forms) - len(keep) == len(gone), (len(forms) - len(keep), len(gone))
        open(PCB, "w").write("(kicad_pcb\n\t" + "\n\t".join(keep) + "\n)\n")
    print("route_leftovers: %d tracks and vias added; %d track ends cut back and %d hanging tracks taken off; %d nets still open (%.0f s)"
          % (added, short, len(gone), left, time.time() - t0))
    sys.stdout.flush(); os._exit(1 if left else 0)


if __name__ == "__main__":
    main()
