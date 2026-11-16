#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-19
"""route_leftovers.py BOARD.kicad_pcb - route the connections Freerouting leaves open, on F.Cu/B.Cu only.
Copied 2026-11-01 from hardware/memory/kicad/rev-e/gen/route_leftovers.py (written for MEM3-E's RN1.4 and RN3.4);
the search box now spans the open pad and every pad of its net (+ 6 mm), so long nets route too.
A small A* maze router on a 0.1 mm grid: obstacles are every pad, track and via of another net, grown by the
clearance plus half the new track's width; a layer change costs a via (which must also clear everything, both layers).
It finds DRC's open connections itself (kicad-cli drc), routes each from the pad to the nearest copper of its net,
and adds the tracks. DRC is the judge afterwards. Run with KiCad's Python: <KiCad python> route_leftovers.py BOARD.kicad_pcb"""
import os, sys, json, heapq, math, subprocess, tempfile
import pcbnew
PCB = os.path.abspath(sys.argv[1])
CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
G = 0.1; W = 0.25; CLR = 0.2; VIA_D = 0.6; VIA_DRILL = 0.3; HOLE_CLR = 0.25; EDGE = 0.5
mm = pcbnew.ToMM; FM = pcbnew.FromMM

def opens():
    j = os.path.join(tempfile.gettempdir(), "_left.json")
    subprocess.run([CLI, "pcb", "drc", "--format", "json", "--refill-zones", "-o", j, PCB], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return json.load(open(j))["unconnected_items"]

def seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay; L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))

def route(b, pad):
    net = pad.GetNetname(); px, py = mm(pad.GetPosition().x), mm(pad.GetPosition().y)
    xs, ys = [px], [py]
    for fp in b.GetFootprints():                       # the box spans every pad of the net
        for p in fp.Pads():
            if p.GetNetname() == net: xs.append(mm(p.GetPosition().x)); ys.append(mm(p.GetPosition().y))
    x0, x1, y0, y1 = min(xs) - 6, max(xs) + 6, min(ys) - 6, max(ys) + 6
    eb = b.GetBoardEdgesBoundingBox(); bx0, bx1, by0, by1 = mm(eb.GetLeft()) + EDGE, mm(eb.GetRight()) - EDGE, mm(eb.GetTop()) + EDGE, mm(eb.GetBottom()) - EDGE
    nx, ny = int((x1 - x0) / G) + 1, int((y1 - y0) / G) + 1
    obst = {L: set() for L in (0, 1)}; targets = set(); holes = []
    def mark(L, shape_dist, cx, cy, reach):           # cells within reach of a shape
        for i in range(max(0, int((cx - reach - x0) / G)), min(nx, int((cx + reach - x0) / G) + 2)):
            for k in range(max(0, int((cy - reach - y0) / G)), min(ny, int((cy + reach - y0) / G) + 2)):
                if shape_dist(x0 + i * G, y0 + k * G) <= 0: obst[L].add((i, k))
    for fp in b.GetFootprints():
        for p in fp.Pads():
            cx, cy = mm(p.GetPosition().x), mm(p.GetPosition().y)
            if not (x0 - 3 < cx < x1 + 3 and y0 - 3 < cy < y1 + 3): continue
            r = max(mm(p.GetSize(pcbnew.F_Cu).x), mm(p.GetSize(pcbnew.F_Cu).y)) / 2
            holes.append((cx, cy, mm(p.GetDrillSize().x) / 2))
            same = p.GetNetname() == net
            for L in (0, 1):
                if same: continue
                mark(L, lambda x, y, cx=cx, cy=cy, r=r: math.hypot(x - cx, y - cy) - (r + CLR + W / 2), cx, cy, r + CLR + W)
    for t in b.GetTracks():
        a, e = t.GetStart(), t.GetEnd(); ax, ay, ex, ey = mm(a.x), mm(a.y), mm(e.x), mm(e.y)
        if not (min(ax, ex) < x1 + 2 and max(ax, ex) > x0 - 2 and min(ay, ey) < y1 + 2 and max(ay, ey) > y0 - 2): continue
        hw = mm(t.GetWidth()) / 2
        if t.Type() == pcbnew.PCB_VIA_T: layers = (0, 1); holes.append((ax, ay, mm(t.GetDrillValue()) / 2))
        else: layers = ((0,) if t.GetLayer() == pcbnew.F_Cu else (1,) if t.GetLayer() == pcbnew.B_Cu else ())
        for L in layers:
            if t.GetNetname() == net:
                for i in range(int((min(ax, ex) - x0) / G), int((max(ax, ex) - x0) / G) + 2):
                    for k in range(int((min(ay, ey) - y0) / G), int((max(ay, ey) - y0) / G) + 2):
                        if 0 <= i < nx and 0 <= k < ny and seg_dist(x0 + i * G, y0 + k * G, ax, ay, ex, ey) <= hw: targets.add((L, i, k))
                continue
            reach = hw + CLR + W / 2
            mark(L, lambda x, y, ax=ax, ay=ay, ex=ex, ey=ey, reach=reach: seg_dist(x, y, ax, ay, ex, ey) - reach,
                 (ax + ex) / 2, (ay + ey) / 2, math.hypot(ex - ax, ey - ay) / 2 + reach + 0.2)
    for fp in b.GetFootprints():                       # same-net pads (not this one) are targets too
        for p in fp.Pads():
            if p.GetNetname() == net and p != pad:
                cx, cy = mm(p.GetPosition().x), mm(p.GetPosition().y); i, k = round((cx - x0) / G), round((cy - y0) / G)
                if 0 <= i < nx and 0 <= k < ny: targets |= {(0, i, k), (1, i, k)}
    inb = lambda i, k: bx0 + W / 2 <= x0 + i * G <= bx1 - W / 2 and by0 + W / 2 <= y0 + k * G <= by1 - W / 2
    def via_ok(i, k):
        x, y = x0 + i * G, y0 + k * G
        if any(math.hypot(x - hx, y - hy) < hr + VIA_DRILL / 2 + HOLE_CLR for hx, hy, hr in holes): return False
        grow = int((VIA_D - W) / 2 / G) + 1
        return all((a, c) not in obst[L] for L in (0, 1) for a in range(i - grow, i + grow + 1) for c in range(k - grow, k + grow + 1))
    si, sk = round((px - x0) / G), round((py - y0) / G)
    start = [(0, (L, si, sk)) for L in (0, 1)]; dist = {s: 0 for _, s in start}; prev = {}; pq = list(start); heapq.heapify(pq)
    steps = [(1, 0, 1), (-1, 0, 1), (0, 1, 1), (0, -1, 1), (1, 1, 1.414), (1, -1, 1.414), (-1, 1, 1.414), (-1, -1, 1.414)]
    goal = None
    while pq:
        dcur, s = heapq.heappop(pq)
        if dcur > dist.get(s, 1e9): continue
        L, i, k = s
        if s in targets and dcur > 0: goal = s; break
        moves = [((L, i + a, k + c), w) for a, c, w in steps] + ([((1 - L, i, k), 25)] if via_ok(i, k) else [])
        for n2, w in moves:
            L2, i2, k2 = n2
            if not (0 <= i2 < nx and 0 <= k2 < ny) or not inb(i2, k2): continue
            near_start = math.hypot(i2 - si, k2 - sk) * G < 0.9
            if (i2, k2) in obst[L2] and not near_start and n2 not in targets: continue
            nd = dcur + w
            if nd < dist.get(n2, 1e9): dist[n2] = nd; prev[n2] = s; heapq.heappush(pq, (nd, n2))
    if not goal: return None
    path = [goal]
    while path[-1] in prev: path.append(prev[path[-1]])
    path.reverse()
    nets = b.FindNet(net); added = []
    run = [path[0]]
    def flush(run):
        L = run[0][0]; pts = [(x0 + i * G, y0 + k * G) for _, i, k in run]
        simp = [pts[0]]                                 # keep only direction changes
        for j in range(1, len(pts) - 1):
            d1 = (round(pts[j][0] - simp[-1][0], 3), round(pts[j][1] - simp[-1][1], 3)); d2 = (round(pts[j + 1][0] - pts[j][0], 3), round(pts[j + 1][1] - pts[j][1], 3))
            if abs(d1[0] * d2[1] - d1[1] * d2[0]) > 1e-6: simp.append(pts[j])
        simp.append(pts[-1])
        if len(run) == 1: return
        for (a, c), (e, f) in zip(simp, simp[1:]):
            t = pcbnew.PCB_TRACK(b); t.SetStart(pcbnew.VECTOR2I(FM(a), FM(c))); t.SetEnd(pcbnew.VECTOR2I(FM(e), FM(f)))
            t.SetLayer(pcbnew.F_Cu if L == 0 else pcbnew.B_Cu); t.SetWidth(FM(W)); t.SetNet(nets); b.Add(t); added.append(t)
    for s in path[1:]:
        if s[0] != run[-1][0]:
            flush(run); v = pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(FM(x0 + s[1] * G), FM(y0 + s[2] * G)))
            v.SetWidth(FM(VIA_D)); v.SetDrill(FM(VIA_DRILL)); v.SetNet(nets); b.Add(v); added.append(v); run = [s]
        else: run.append(s)
    flush(run)
    # first point: snap to the pad centre
    return len(added)

b = pcbnew.LoadBoard(PCB); done = 0
for u in opens():
    d = u["items"][0]["description"]
    import re
    m = re.match(r"PTH pad (\S+) \[[^\]]*\] of (\S+)", d)
    if not m: continue
    fp = b.FindFootprintByReference(m.group(2)); pad = [p for p in fp.Pads() if p.GetNumber() == m.group(1)][0]
    n = route(b, pad); print("%s.%s (%s): %s" % (m.group(2), m.group(1), pad.GetNetname(), "routed, %d items" % n if n else "NO ROUTE"))
    done += bool(n)
pcbnew.ZONE_FILLER(b).Fill(b.Zones()); pcbnew.SaveBoard(PCB, b); print("routed", done)
sys.stdout.flush(); os._exit(0)
