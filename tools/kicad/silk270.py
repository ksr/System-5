#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-18
"""silk270.py - silkscreen labels that read upright with a System-5 card standing in the bus, connector down (Ken's rule
of 2026-11-18, every board on every system: "all silkscreen text reads correctly with the card held connector down").
System-5's cards are drawn with the bus connector on the left, so every text is at KiCad angle 270; the one exception is
the board's name, revision and cottageworker.com, which may run up a side edge (angle 0 along the top or bottom edge as
drawn) or across the top (angle 270 along the front edge).

Each label goes at the first spot clear of every pad (0.3 mm), every part's body (its F.Fab drawing) and outline (its
F.SilkS drawing), every other text (0.2 mm) and the board edge (0.5 mm), so references and values stay readable with the
parts fitted (Ken, 2026-10-31 and 2026-11-02). The same placer as the IO panel's make_board.py and memory Rev F's
gen/silk.py, made a module for VIDEO-G's common/silk.py and CPU Rev D's gen/make_board.py.

    s = Silk(board)                       hides the parts' own reference and value fields, moves the footprints' own
                                          silkscreen texts (a bus connector's pin names) to F.Fab and notes them
    s.put(text, x, y, h, angle, just)     a fixed text (no check)
    s.place(variants, spots)              the first (text, height) of variants that fits at one of spots
    s.beside(ref)                         spots round a part, under it with the card standing first (left as drawn)
    s.label(ref, text, two=None)          a part's label beside it: one line at 1.0 or 0.8 mm, else two lines
    s.pin_names(ref, names)               a connector's pin names in two staggered columns beside its pads
    s.bus_label(ref, text)                the bus connector's own label, never under the right-angle header's body
    s.edge_line(text, h, xs, edge)        the name line along the top or bottom edge as drawn (angle 0)
"""
import pcbnew

MM, T = pcbnew.FromMM, pcbnew.ToMM
V = lambda x, y: pcbnew.VECTOR2I(MM(x), MM(y))
UP = 270


def boxof(bb, m=0.0):
    return T(bb.GetLeft()) - m, T(bb.GetTop()) - m, T(bb.GetRight()) + m, T(bb.GetBottom()) + m


def union(boxes):
    return (min(c[0] for c in boxes), min(c[1] for c in boxes), max(c[2] for c in boxes), max(c[3] for c in boxes))


class Silk:
    def __init__(self, b, edge=0.5, stroke=0.15, no_silk=()):
        """no_silk: boxes (x0, y0, x1, y1) where no label may go: the card-guide strips (3.00 x 0.15 in from the bus edge
        along the top and bottom edges as drawn), where a guide would hide it. Rule areas named "card guide" (VIDEO-G's)
        are taken as such too"""
        self.b, self.margin, self.stroke = b, edge, stroke
        eb = b.GetBoardEdgesBoundingBox(); self.edge = boxof(eb)
        self.blocks, self.fp_texts, self.missed = list(no_silk), {}, []
        for z in b.Zones():
            if z.GetIsRuleArea() and z.GetZoneName() == "card guide":
                self.blocks.append(boxof(z.GetBoundingBox()))
        self.body = {}                                   # ref -> the part's body box (F.Fab, else courtyard, else pads)
        self.courts = []                                 # every courtyard: the name line keeps clear of them too
        for fp in b.GetFootprints():
            ref = fp.GetReference()
            fp.Reference().SetVisible(False); fp.Value().SetVisible(False)
            for g in fp.GraphicalItems():                # the footprints' own texts (a bus connector's pin names): off
                if isinstance(g, pcbnew.PCB_TEXT) and g.GetLayer() in (pcbnew.F_SilkS, pcbnew.F_Fab) \
                        and not g.GetText().startswith("${"):   # the silk to F.Fab (KiCad 10 keeps no hidden flag on
                    self.fp_texts.setdefault(ref, []).append((T(g.GetPosition().x), T(g.GetPosition().y), g.GetText()))
                    g.SetLayer(pcbnew.F_Fab)             # them); read from either layer, so a second run finds them
            pads = [boxof(p.GetBoundingBox()) for p in fp.Pads()]
            for p in fp.Pads():
                self.blocks.append(boxof(p.GetBoundingBox(), 0.3))
            fab = [boxof(g.GetBoundingBox(), 0.1) for g in fp.GraphicalItems()
                   if g.GetLayer() == pcbnew.F_Fab and not isinstance(g, pcbnew.PCB_TEXT)]
            out = [boxof(g.GetBoundingBox(), 0.1) for g in fp.GraphicalItems()
                   if g.GetLayer() == pcbnew.F_SilkS and not isinstance(g, pcbnew.PCB_TEXT)]
            for boxes in (fab, out):                     # each drawing as one box: drawn as separate lines, a part's
                if boxes:                                # inside would look free
                    self.blocks.append(union(boxes))
            cy = fp.GetCourtyard(pcbnew.F_CrtYd)
            if not fab and cy.OutlineCount():
                self.blocks.append(boxof(cy.BBox()))
            if cy.OutlineCount():
                self.courts.append(boxof(cy.BBox()))
            self.body[ref] = union(fab) if fab else boxof(cy.BBox()) if cy.OutlineCount() else union(pads) if pads else None
        for d in b.GetDrawings():                        # what is already on the silkscreen stays clear too
            if d.GetLayer() == pcbnew.F_SilkS:
                self.blocks.append(boxof(d.GetBoundingBox(), 0.2))

    # ---- texts -------------------------------------------------------------------------------------------------------
    def text(self, s, x, y, h=1.0, angle=UP, just=None):
        t = pcbnew.PCB_TEXT(self.b); t.SetText(s); t.SetLayer(pcbnew.F_SilkS); t.SetTextSize(V(h, h))
        t.SetTextThickness(MM(max(self.stroke, 0.15 * h))); t.SetPosition(V(x, y))
        if just == "left": t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
        elif just == "right": t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_RIGHT)
        if angle: t.SetTextAngleDegrees(angle)
        return t

    def free(self, box):
        e, m = self.edge, self.margin
        if box[0] < e[0] + m or box[1] < e[1] + m or box[2] > e[2] - m or box[3] > e[3] - m:
            return False
        return not any(box[0] < c[2] and c[0] < box[2] and box[1] < c[3] and c[1] < box[3] for c in self.blocks)

    def add(self, t):
        self.b.Add(t); self.blocks.append(boxof(t.GetBoundingBox(), 0.2)); return t

    def put(self, s, x, y, h=1.0, angle=UP, just=None):
        return self.add(self.text(s, x, y, h, angle, just))

    def place(self, variants, spots, angle=UP, just=None, need=True, nearest=False):
        """the first variant (text, height) that fits at one of spots [(x, y)]: variant by variant, or (nearest) spot by
        spot, each spot's variants in turn, so a label goes on two lines beside its part sooner than on one further
        off -> (x, y, text, h)"""
        rel = []
        for s, h in variants:                            # each variant's box about its anchor, measured once
            bb = boxof(self.text(s, 0.0, 0.0, h, angle, just).GetBoundingBox()); rel.append((s, h, bb))
        tries = [(v, p) for p in spots for v in rel] if nearest else [(v, p) for v in rel for p in spots]
        for (s, h, bb), (x, y) in tries:
            if self.free((bb[0] + x, bb[1] + y, bb[2] + x, bb[3] + y)):
                self.add(self.text(s, x, y, h, angle, just)); return x, y, s, h
        if need:
            self.missed.append((variants[0][0], spots[0] if spots else None))
        return None

    # ---- spots ---------------------------------------------------------------------------------------------------------
    def bbox(self, ref):
        return self.body[ref]

    def pads(self, ref):
        ps = [p.GetPosition() for p in self.b.FindFootprintByReference(ref).Pads()]
        return min(T(p.x) for p in ps), min(T(p.y) for p in ps), max(T(p.x) for p in ps), max(T(p.y) for p in ps)

    def beside(self, ref, reach=8.0, dys=(0.0, 1.0, -1.0, 2.0, -2.0, 3.0, -3.0, 4.0, -4.0), order=("left", "right", "ends")):
        """spots beside a part, nearest first: off its left side as drawn (under it, with the card standing), off its
        right side (over it), then off its ends (a 270 text runs along y, beside the part's length)"""
        l, t, r, bt = self.bbox(ref); cx, cy = (l + r) / 2, (t + bt) / 2
        out = []
        for k in range(int(reach / 0.2)):
            d = 0.9 + 0.2 * k
            for dy in dys:
                if "left" in order: out.append((l - d, cy + dy))
                if "right" in order: out.append((r + d, cy + dy))
        if "ends" in order:
            for k in range(int(reach / 0.2)):
                d = 1.0 + 0.2 * k
                for dx in (0.0, 1.5, -1.5, 3.0, -3.0):
                    out += [(cx + dx, bt + d), (cx + dx, t - d)]
        return out

    def label(self, ref, text, two=None, sizes=(1.0, 0.8), spots=None):
        """a part's label beside it: one line at 1.0 or 0.8 mm, else two (reference over value)"""
        v = [(text, h) for h in sizes] + ([(two, h) for h in sizes] if two else [])
        return self.place(v, spots if spots is not None else self.beside(ref), nearest=True)

    def pin_names(self, ref, names, side="right", cols=(2.4, 4.2), sizes=(0.8,)):
        """a connector's pin names beside its pads in staggered columns (side by side at 270 they would not fit the
        2.54 mm pitch): names = {pad number: name}; cols, the columns' distances from the pads"""
        pads = sorted(self.b.FindFootprintByReference(ref).Pads(), key=lambda p: (p.GetPosition().y, p.GetPosition().x))
        mid = (T(pads[0].GetPosition().y) + T(pads[-1].GetPosition().y)) / 2 if pads else 0.0
        for k, p in enumerate(pads):
            name = names.get(p.GetNumber())
            if not name:
                continue
            x, y = T(p.GetPosition().x), T(p.GetPosition().y)
            sx = 1 if side == "right" else -1           # each pin's name in its own column first, the others next
            order = cols[k % len(cols):] + cols[:k % len(cols)]   # (two columns for short names, three for longer)
            xs = [x + sx * c for c in order]
            # then, for a long name at an end pin (2026-11-18: "-PAUSE" at the 36-pin connector's top end touched the
            # card-guide strip by 0.01 mm and was left out), one column further out and the others, 0.5 or 1.0 mm
            # towards the connector's middle
            far = x + sx * (max(cols) + 1.8); toward = 1.0 if y < mid else -1.0
            spots = [(xx, y) for xx in xs] + [(xx, y + toward * d) for d in (0.5, 1.0) for xx in [far] + xs]
            self.place([(name, h) for h in sizes], spots)

    def bus_label(self, ref="J1", text="J1 BUS", sizes=(1.0, 0.8), spots=None, side="right", cols=(2.4, 4.2)):
        """the bus connector's own label, where it stays readable with the connector fitted. The connector is a
        right-angle pin header: its plastic body lies on the board between the pads and the card edge (drawn on F.Fab in
        the C30 / C36 footprints since 2026-11-18; until then this label was printed in that margin, under the header, on
        every new card). Tried in turn: spots (the board's own choice, the larger size first); past either end of the pad
        row in the margin, clear of the card-guide strips; then on the board side of the pin names (side and cols as
        pin_names had them), nearest the pads first, the connector's middle first -> (x, y, text, h), or None (missed)"""
        v = [(text, h) for h in sizes]
        if spots:
            return self.place(v, spots)
        l, t, r, bt = self.pads(ref); mid = (t + bt) / 2; sx = 1 if side == "right" else -1
        mx = ((l + self.edge[0]) / 2 + 0.2) if side == "right" else ((r + self.edge[2]) / 2 - 0.2)
        got = self.place(v, [(mx + dx, y) for d in [2.0 + 0.2 * k for k in range(40)] for y in (bt + d, t - d)
                             for dx in (0.0, 0.4, -0.4, 0.8, -0.8)], need=False)
        if got:
            return got
        x0 = (r if side == "right" else l) + sx * (max(cols) + 1.8)
        ys = [mid + sg * 0.25 * n for n in range(160) for sg in (1, -1)]
        # right beside the names (the first 1.6 mm), the larger size wherever it fits before the smaller, the
        # connector's middle first; then further in, the first spot that takes either size
        return self.place(v, [(x0 + sx * 0.2 * k, y) for y in ys for k in range(8)], need=False) or \
            self.place(v, [(x0 + sx * 0.2 * k, y) for k in range(8, 40) for y in ys], nearest=True)

    def ends(self, ref, labels, h=0.8):
        """what a jumper's shunt or a switch's lever picks, at the part's ends: labels {pin: text}, each beyond its pin
        along the part, out from its middle"""
        pads = {p.GetNumber(): (T(p.GetPosition().x), T(p.GetPosition().y)) for p in self.b.FindFootprintByReference(ref).Pads()
                if p.GetNumber()}
        mx = sum(x for x, _ in pads.values()) / len(pads); my = sum(y for _, y in pads.values()) / len(pads)
        for pin, text in labels.items():
            px, py = pads[pin]; dx, dy = px - mx, py - my; n = (dx * dx + dy * dy) ** 0.5 or 1.0
            self.place([(text, h)], [(px + dx / n * d + ox, py + dy / n * d + oy) for d in [1.8 + 0.2 * k for k in range(25)]
                                     for ox, oy in ((0, 0), (0, 0.6), (0, -0.6), (0.6, 0), (-0.6, 0))], nearest=True)

    def edge_line(self, s, h, xs, edge="bottom", inset=1.6):
        """the name line along the bottom (or top) edge as drawn, angle 0: up the side with the card standing. inset: the
        distance of its middle from that edge, or several to try in turn (beside a card-guide strip, more than 3.81 mm)"""
        insets = inset if isinstance(inset, (list, tuple)) else (inset,)
        spots = [(x, self.edge[3] - i if edge == "bottom" else self.edge[1] + i) for i in insets for x in xs]
        return self.place([(s, h)], spots, angle=0)

    def name_pair(self, name, h1, url, h2, spots, gap=2.0):
        """the name line (the rule's exception: angle 0, up a side edge with the card standing): the name with its
        revision left-justified at one of spots, cottageworker.com right after it on the same line, else next to it on
        a line of its own (toward the board edge, then away), both kept together -> True"""
        def box(s, x, y, h):
            return boxof(self.text(s, x, y, h, 0, "left").GetBoundingBox())
        def clear(bx):                                   # free, and over no part's courtyard (pcb-check: "runs under")
            return self.free(bx) and not any(bx[0] < c[2] and c[0] < bx[2] and bx[1] < c[3] and c[1] < bx[3]
                                             for c in self.courts)
        for x, y in spots:
            b1 = box(name, x, y, h1)
            if not clear(b1):
                continue
            r2 = box(url, x, 0.0, h2)                    # the URL's box about its anchor: stacked 0.2 mm or more off
            tries = [(b1[2] + gap, y)]                   # the name, shifted along it a little if it must
            for g in (0.2, 0.6, 1.0, 1.5):
                for dx in (0.0, -0.5, 0.5, -1.0, 1.0, -1.5, 1.5, -2.0, 2.0, -3.0, 3.0):
                    tries += [(x + dx, b1[3] + g - r2[1]), (x + dx, b1[1] - g - r2[3])]
            for ux, uy in tries:
                b2 = box(url, ux, uy, h2)
                if clear(b2) and not (b1[0] < b2[2] and b2[0] < b1[2] and b1[1] < b2[3] and b2[1] < b1[3]):
                    self.add(self.text(name, x, y, h1, 0, "left")); self.add(self.text(url, ux, uy, h2, 0, "left"))
                    return True
        self.missed.append((name + " / " + url, spots[0] if spots else None))
        return False

    def report(self):
        for s, at in self.missed:
            print("  silk: no room for %r near %s" % (s, at))
        return not self.missed
