#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-18
"""silk.py - Rev F's silkscreen (Ken, 2026-11-18: "create the next version of memory card with fixed silkscreen"; then
"yes put in Rev F", the EEPROM sockets), on the board gen/make_board.py makes from Rev E's and gen/route.py routes, which
still carries Rev E's silkscreen texts: run it after them (gen/build.sh does), with KiCad's Python:

    /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 gen/silk.py

Ken's silkscreen rules for new boards, as they stand on 2026-11-18 (~/.claude/CLAUDE.md, "Board layout"):
  * every reference readable with the parts fitted, outside each part, never under a chip or socket (2026-10-31, after
    MEM3-E: "IC2" sat under the chip while he debugged it), with the type or value beside it (2026-11-02)
  * **all silkscreen text reads upright, left to right, with the card standing in the bus, connector down** (2026-11-18:
    MEM3-E is the rule's example, "drawn to be read lying flat": 77 texts at 0, 30 at 90, 4 at 180, only its 5 LED
    labels at 270). System-5's cards are drawn with the bus on the left, so every text is at KiCad angle 270. The one
    exception is the name, revision and cottageworker.com line, which may run up a side edge (angle 0 along the bottom
    edge as drawn), and does here
  * the name with its revision, and cottageworker.com beside it (2026-10-26); none of it in the card-guide strips
    (3.00 x 0.15 in from the bus edge along the top and bottom edges), where a guide would hide it

What this script does (nothing on a copper layer: every track, via, zone and pad stays where make_board.py and
route.py put them):
  * removes every silkscreen text but the LEDs' five labels (EPROM HI ... PWR, already at 270) and moves the
    footprints' own texts to F.Fab, then writes them all again at 270, each at the first spot clear of every pad (0.3 mm), part
    outline, courtyard, other text and the board edge:
      - the bus pins' names, in two staggered columns on the board side of J1's pads (side by side they would not fit
        the 2.54 mm pitch), and "J1 BUS" in the margin past the header's GND end. The names stood between the pads and
        the board edge until the night of 2026-11-18: J1 is a right-angle pin header, and its plastic body lies there
        (Ken's photo of the built MEM3-E shows it), so all thirty would have been under it. The C30 footprint in this
        folder's library now draws the body (F.Fab), a courtyard round it and KiCad's 3D model, and this script brings
        the board's J1 up to it (tools/kicad/fp_update.py) before anything is placed
      - each chip's name, type and job ("IC7 CD4050" over "A0-A5 BUFFER") at one end of the chip, where the socket
        cannot cover it; one line, or the name and type alone, where two lines do not fit
      - the capacitors', resistors' and networks' references with their values, the networks' pin 1
      - the jumper blocks: the 4K blocks' addresses (F000 ... 0000) under each column, the rows (ROM, GND, RAM), the
        blocks' names (HI 32K, LO 32K) and their headers' references (SV1-SV4)
      - the EEPROM sockets' jumper blocks JP1 (EPROM HI) and JP2 (EPROM LO): 27C256 under each (both shunts down, with
        the card standing), 28C256 over its right-hand column (that shunt up) and WRITE over its left-hand one (that
        shunt up too, to let the CPU write the 28C256)
  * adds a courtyard round each part's pads (0.1 mm out), in the board and in this folder's copy of the footprint
    library, so DRC and pcb-check see where each part is; the chips also have a body on F.Fab there, the chip in its
    socket (1.33 mm past the end pins, 1.27 mm past the rows, as KiCad's DIP sockets), so no label is placed where a
    socket's frame would cover it, and pcb-check's BODIES line finds every part drawn (2026-11-19)
The LEDs keep their labels by function; pcb-check.ini exempts their references, as on CPU Rev D and the IO panel."""
import os, sys
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__)); DEST = os.path.dirname(HERE)
PCB = os.path.join(DEST, "memory-rev-f.kicad_pcb")
REVE = os.path.join(DEST, "..", "rev-e", "memory-rev-e.kicad_pcb")
MM, T = pcbnew.FromMM, pcbnew.ToMM
V = lambda x, y: pcbnew.VECTOR2I(MM(x), MM(y))
UP = 270                                               # upright with the card standing in the bus (bus on the left)

# 0. the board make_board.py made from Rev E's (J1 named, the EEPROM sockets' parts in) and route.py routed; the drawing
#    of every part from this folder's library (memory-rev-d-eagle) brought up to its library file, which Rev E's board
#    is behind: J1's right-angle header (its body, courtyard and 3D model, 2026-11-18), the chips' bodies in their
#    sockets (2026-11-19) and the courtyards step 8 wrote there. No part's own reference or value field on the
#    silkscreen (the new parts' come from KiCad's library showing them)
sys.path.insert(0, os.path.join(DEST, "..", "..", "..", "..", "tools", "kicad")); import fp_update
LIBNAME = "memory-rev-d-eagle"
_board = open(PCB).read()
_mods = {ref: open(os.path.join(DEST, LIBNAME + ".pretty", fpid.split(":")[1] + ".kicad_mod")).read()
         for ref, fpid in fp_update.refs(_board).items() if fpid.split(":")[0] == LIBNAME}
_text, _n = fp_update.update_all(_board, _mods)
open(PCB, "w").write(_text)
print("drawings from the library: %d parts" % len(_mods))
b = pcbnew.LoadBoard(PCB)
for f in b.GetFootprints():
    f.Reference().SetVisible(False); f.Value().SetVisible(False)

JOB = {"IC12": "HI CE", "IC14": "BANK + LO CE", "IC7": "A0-A5 BUFFER", "IC8": "A6 A7 RD WR BUF", "IC9": "A12-A15 LATCH",
       "IC6": "A8-A11 LATCH", "IC5": "EPROM HI 8000-FFFF", "IC3": "EPROM LO 0000-7FFF", "IC11": "RAM HI 8000-FFFF",
       "IC1": "RAM LO 0000-7FFF", "IC13": "EPROM HI 4K SEL", "IC15": "EPROM LO 4K SEL", "IC4": "RAM HI 4K SEL",
       "IC2": "RAM LO 4K SEL"}
LEDS = {"EPROM HI", "EPROM LO", "RAM HI", "RAM LO", "PWR"}

# 1. Rev E's texts: keep the LEDs' labels; note where the jumper blocks' labels were, then remove the rest; move the
#    footprints' own texts (the bus pins' names, the passives' labels) to F.Fab, noting the pin names
old = [t for t in b.GetDrawings() if isinstance(t, pcbnew.PCB_TEXT) and t.GetLayer() == pcbnew.F_SilkS]
where = {}                                             # text -> [(x, y)] of Rev E's jumper-block labels
for t in old:
    if t.GetText() not in LEDS:
        where.setdefault(t.GetText(), []).append((T(t.GetPosition().x), T(t.GetPosition().y)))
for t in [t for t in old if t.GetText() not in LEDS]:   # (collected first: removing while walking breaks pcbnew)
    b.Remove(t)
pinname = {}
for f in b.GetFootprints():
    for g in f.GraphicalItems():
        if isinstance(g, pcbnew.PCB_TEXT) and g.GetLayer() == pcbnew.F_SilkS:
            if f.GetReference() == "J1":
                pinname[round(T(g.GetPosition().y), 1)] = g.GetText()
            g.SetLayer(pcbnew.F_Fab)                   # off the silk (KiCad keeps no hidden flag on these texts)
print("removed %d texts, kept the LEDs' %d" % (len(old) - len(LEDS), len(LEDS)))
# 1b. "RAM HI" 0.5 mm further from R3. Rev E has R3 1.27 mm nearer the front edge than the other LEDs' resistors, so its
#     front lead ends under the column the five labels stand in, and the label's end came within 0.1 mm of the resistor's
#     drawing: pcb-check's LABELS line, which reads every silkscreen text since 2026-11-19, said "'RAM HI' under R3"
#     (it was not hidden: the text stopped 0.4 mm short of R3's pad). The other four labels stay where Rev E has them
for t in b.GetDrawings():
    if isinstance(t, pcbnew.PCB_TEXT) and t.GetLayer() == pcbnew.F_SilkS and t.GetText() == "RAM HI":
        t.SetPosition(pcbnew.VECTOR2I(t.GetPosition().x, t.GetPosition().y - MM(0.5)))

# 2. a courtyard on every footprint without one: its pads, 0.1 mm out (Rev E's parts sit closer than their outlines)
added = 0
for f in b.GetFootprints():
    if f.GetCourtyard(pcbnew.F_CrtYd).OutlineCount():
        continue
    edges = [(T(x.GetLeft()), T(x.GetTop()), T(x.GetRight()), T(x.GetBottom())) for x in (p.GetBoundingBox() for p in f.Pads())]
    if not edges:
        continue
    s = pcbnew.PCB_SHAPE(f); s.SetShape(pcbnew.SHAPE_T_RECT); s.SetLayer(pcbnew.F_CrtYd); s.SetWidth(MM(0.05))
    s.SetStart(V(min(e[0] for e in edges) - 0.1, min(e[1] for e in edges) - 0.1))
    s.SetEnd(V(max(e[2] for e in edges) + 0.1, max(e[3] for e in edges) + 0.1)); f.Add(s); added += 1
print("courtyards added: %d" % added)

# what a label must keep clear of
eb = b.GetBoardEdgesBoundingBox(); EDGE = (T(eb.GetLeft()), T(eb.GetTop()), T(eb.GetRight()), T(eb.GetBottom()))
def boxof(bb, m=0.0): return (T(bb.GetLeft()) - m, T(bb.GetTop()) - m, T(bb.GetRight()) + m, T(bb.GetBottom()) + m)
blocks = []
for f in b.GetFootprints():
    for p in f.Pads():
        blocks.append(boxof(p.GetBoundingBox(), 0.3))
    for g in f.GraphicalItems():
        if g.GetLayer() in (pcbnew.F_SilkS, pcbnew.F_CrtYd, pcbnew.F_Fab) and not isinstance(g, pcbnew.PCB_TEXT):
            blocks.append(boxof(g.GetBoundingBox(), 0.1))
for t in b.GetDrawings():
    if isinstance(t, pcbnew.PCB_TEXT) and t.GetLayer() == pcbnew.F_SilkS:
        blocks.append(boxof(t.GetBoundingBox(), 0.2))
# the card-guide strips, 3.00 x 0.15 in from the bus edge along the top and bottom edges as drawn: no label in them,
# where a guide would hide it (the name line first stood in the bottom one; fixed the same day)
STRIPS = [(EDGE[0], EDGE[1], EDGE[0] + 76.2, EDGE[1] + 3.81), (EDGE[0], EDGE[3] - 3.81, EDGE[0] + 76.2, EDGE[3])]
blocks += STRIPS
def free(box):
    if box[0] < EDGE[0] + 0.5 or box[1] < EDGE[1] + 0.5 or box[2] > EDGE[2] - 0.5 or box[3] > EDGE[3] - 0.5:
        return False
    return not any(box[0] < c[2] and c[0] < box[2] and box[1] < c[3] and c[1] < box[3] for c in blocks)

def text(s, x, y, h=1.0, angle=UP):
    t = pcbnew.PCB_TEXT(b); t.SetText(s); t.SetLayer(pcbnew.F_SilkS); t.SetTextSize(V(h, h))
    t.SetTextThickness(MM(max(0.15, 0.15 * h))); t.SetPosition(V(x, y))
    if angle: t.SetTextAngleDegrees(angle)
    return t

def place(variants, spots, need=True):
    """the first variant (text, height) that fits at one of spots [(x, y)], tried variant by variant: -> (x, y, s, h)"""
    for s, h in variants:
        for x, y in spots:
            t = text(s, x, y, h)
            if free(boxof(t.GetBoundingBox())):
                b.Add(t); blocks.append(boxof(t.GetBoundingBox(), 0.2)); return (x, y, s, h)
    if need:
        raise SystemExit("no room for %r near (%.1f, %.1f)" % (variants[0][0], spots[0][0], spots[0][1]))

def pins(ref):
    ps = [p.GetPosition() for p in b.FindFootprintByReference(ref).Pads()]
    return min(T(p.x) for p in ps), min(T(p.y) for p in ps), max(T(p.x) for p in ps), max(T(p.y) for p in ps)

def around(ref, reach=6.0, dys=(0.0, 1.0, -1.0, 2.0, -2.0, 3.0, -3.0)):
    """spots beside a part: off either end along x (where a 270 text stands clear of its pins), nearest first, then
    above and below it"""
    l, t_, r, bt = pins(ref); cy = (t_ + bt) / 2; cx = (l + r) / 2
    out = []
    for k in range(int(reach / 0.2)):
        d = 1.0 + 0.2 * k
        for dy in dys:
            out += [(r + d, cy + dy), (l - d, cy + dy)]
    for k in range(int(reach / 0.2)):
        d = 1.5 + 0.2 * k
        for dx in (0.0, 2.0, -2.0, 4.0, -4.0):
            out += [(cx + dx, bt + d), (cx + dx, t_ - d)]
    return out

# 3. the bus pins' names: two staggered columns on the board side of J1's pads, 0.8 mm, each name level with its pin;
#    "J1 BUS" in the margin past an end of the header, clear of the guide strips. Never between the pads and the board
#    edge: the header's plastic body lies there (the docstring). The columns stand 1.84 and 3.51 mm from the pads
#    (the other cards': 2.4 and 4.2): the bottom row's chips are 7.6 mm from J1, which leaves 6.2 mm between the two
#    rows of pads for these two columns and the chips' labels (step 5), 0.2 mm apart. A name that does not fit in its
#    own column stops the build: in the other column it would stand on its neighbours
l, t_, r, bt = pins("J1")
COLS = (1.84, 3.51)
jp = sorted([p for p in b.FindFootprintByReference("J1").Pads()], key=lambda p: p.GetPosition().y)
for k, p in enumerate(jp):
    y = T(p.GetPosition().y); name = pinname.get(round(y, 1)) or min(pinname.items(), key=lambda kv: abs(kv[0] - y))[1]
    place([(name, 0.8)], [(r + COLS[k % 2], y)])
place([("J1 BUS", 1.0)], [((l + EDGE[0]) / 2 + 0.3 + dx, y) for d in [2.0 + 0.2 * k for k in range(40)]   # past an end of
       for y in (bt + d, t_ - d) for dx in (0.0, 0.4)])                                    # J1, clear of the guide strips

# 4. the name with its revision, cottageworker.com beside it (placed before the parts' labels, which go round it):
#    along the bottom edge as drawn (the rule's one exception, running up the right-hand side with the card standing),
#    beyond the bottom card-guide strip, where the only room is (above the strip the parts leave none): the name and
#    rev at 1.2 mm (pcb-check's least for them), cottageworker.com at 1.0 mm right after them on the same line
sys.path.insert(0, os.path.join(DEST, "..", "..", "..", "..", "tools", "kicad")); import silk270
s = silk270.Silk(b, no_silk=STRIPS)
NAME, URL = "System-5 memory  Rev F  2026", "cottageworker.com"        # no MEM3-F (Ken, 2026-11-18: one naming for all)
if not s.name_pair(NAME, 1.2, URL, 1.0, [(x, EDGE[3] - 1.6) for x in [EDGE[0] + 76.4 + 0.2 * k for k in range(20)]], gap=1.0):
    raise SystemExit("no room for the name line")
for t in b.GetDrawings():
    if isinstance(t, pcbnew.PCB_TEXT) and t.GetText() in (NAME, URL):
        blocks.append(boxof(t.GetBoundingBox(), 0.2))
        print("name line: %r at (%.1f, %.1f)" % (t.GetText(), T(t.GetPosition().x), T(t.GetPosition().y)))

# 5. the chips: name, type and job at one end, where the socket cannot cover them. The bottom row's four (IC7, IC8, IC9,
#    IC6) share the 6.2 mm between their pads and J1's with the bus pins' names: their labels fit on two lines at
#    0.8 mm, 2.5 mm from the chip's pins, a spot that around()'s 0.2 mm steps miss, so it is tried first
for ref, job in JOB.items():
    val = b.FindFootprintByReference(ref).GetValue()
    l, t_, r, bt = pins(ref)
    tight = [(l - 2.5, (t_ + bt) / 2 + dy) for dy in (0.0, 0.5, -0.5, 1.0, -1.0, 1.5, -1.5, 2.0, -2.0)] if ref in ("IC7", "IC8", "IC9", "IC6") else []
    got = place([("%s %s\n%s" % (ref, val, job), 1.0), ("%s %s\n%s" % (ref, val, job), 0.8),
                 ("%s %s  %s" % (ref, val, job), 0.8), ("%s %s" % (ref, val), 1.0), ("%s %s" % (ref, val), 0.8)], tight + around(ref))
    print("%-5s at (%.1f, %.1f) %.1f mm: %r" % (ref, got[0], got[1], got[3], got[2].replace("\n", " / ")))

# 6. the jumper blocks: each 4K block's address under its column (where Rev E had it), the rows, the names, SV1-SV4
for addr in ["%X000" % k for k in range(16)]:
    (x, y), = where[addr]
    place([(addr, 1.0), (addr, 0.8)], [(x, y), (x, y + 0.5), (x, y - 0.5)])
for k in range(2):                                     # the rows' names: at 270 each is longer than the rows' 2.54 mm
    rows = [(row,) + where[row][k] for row in ("ROM", "GND", "RAM")]          # pitch, so they stagger, as the bus pins'
    for out in ({"GND": (-1.8, 0.0)}, {"ROM": (-1.8, -0.6), "RAM": (-1.8, 0.6)},  # names do: GND out of line, or ROM and
                {"ROM": (-2.2, -0.8), "RAM": (-2.2, 0.8)}):                       # RAM, spread a little where a pad is near
        ts = [text(row, x + out.get(row, (0, 0))[0], y + out.get(row, (0, 0))[1], 0.8) for row, x, y in rows]
        if all(free(boxof(t.GetBoundingBox())) for t in ts):
            for t in ts:
                b.Add(t); blocks.append(boxof(t.GetBoundingBox(), 0.2))
            break
    else:
        raise SystemExit("no room for the rows' names at %s" % (rows,))
for one, two in (("SV4", "SV1"), ("SV3", "SV2")):     # each block's two headers with their sizes ("SV1 2x8"), one label
    size = lambda ref: b.FindFootprintByReference(ref).GetValue().split()[0]     # above the block when standing
    l1, t1, r1, b1 = pins(one); l2, t2, r2, b2 = pins(two); r, cy = max(r1, r2), (min(t1, t2) + max(b1, b2)) / 2
    label = "%s %s\n%s %s" % (one, size(one), two, size(two))
    got = place([(label, 1.0), (label, 0.8)], [(r + dx, cy + dy) for dx in (2.6, 3.0, 3.4, 3.8) for dy in
                                               (0.0, -1.0, 1.0, -2.0, 2.0, -3.0, -4.0, -5.0, -6.0)])
    print("%s/%s at (%.1f, %.1f) %.1f mm" % (one, two, got[0], got[1], got[3]))
for name in ("HI 32K", "LO 32K"):
    (x, y), = where[name]
    ref = "SV1" if name.startswith("HI") else "SV2"
    l, t_, r, bt = pins(ref)
    ya = where["F000" if name.startswith("HI") else "0000"][0][1]           # the block's addresses, under its columns
    place([(name, 1.6), (name, 1.2), (name, 1.0)],
          [(xx, yy) for xx in (r + 2.2, r + 3.2, l - 4.0, l - 5.0) for yy in ((t_ + bt) / 2 - 2.0, (t_ + bt) / 2, (t_ + bt) / 2 + 2.0)]
          + [((l + r) / 2 + dx, ya + d) for d in (4.5, 5.0, 5.5, 6.0, 6.5) for dx in (0.0, 2.0, -2.0, 4.0, -4.0)])   # beyond them

# 6b. the EEPROM sockets' jumper blocks, each turned so its columns stand upright with the card in the bus: the
#     right-hand column (odd pins: VCC, P1, A14) picks the socket's pin 1, the left-hand one (even: A14, P27, WR) its
#     pin 27. Both shunts down: 27C256; right-hand up: 28C256; left-hand up as well: the CPU may write it
for jp in ("JP1", "JP2"):
    f = b.FindFootprintByReference(jp)
    pad = {p.GetNumber(): (T(p.GetPosition().x), T(p.GetPosition().y)) for p in f.Pads()}
    (x1, y1), (x5, _), (_, y2) = pad["1"], pad["5"], pad["2"]           # pins 1-3-5 run up the card, 2-4-6 beside them
    ym = (y1 + y2) / 2                                 # over the block "WRITE  28C256": each word over its column
    for txt, xs in (("27C256", [x1 - d for d in (2.0, 2.3, 2.6, 3.0)]), ("WRITE  28C256", [x5 + d for d in (2.0, 2.3, 2.6, 3.0)])):
        got = place([(txt, 0.8)], [(x, ym + dy) for x in xs for dy in (0.0, 0.3, 0.6, -0.3, 0.9, 1.2)])
    got = place([("%s %s" % (jp, "EPROM HI" if jp == "JP1" else "EPROM LO"), 1.0), ("%s %s" % (jp, "EPROM HI" if jp == "JP1" else "EPROM LO"), 0.8),
                 ("%s\n%s" % (jp, "EPROM HI" if jp == "JP1" else "EPROM LO"), 0.8)], around(jp))
    print("%s at (%.1f, %.1f): %r" % (jp, got[0], got[1], got[2]))

# 6c. the EEPROM sockets' pull-ups, upright beside JP1 and JP2: each label right under its resistor, on two lines (one
#     line is 4.6 mm long, and JP1 and R5 leave R6 4.45 mm), placed before the other passives so that they go round it
for ref in ("R7", "R6"):
    f = b.FindFootprintByReference(ref); l, t_, r, bt = pins(ref)
    for x, y in [(l - d, (t_ + bt) / 2 + dy) for d in [1.6 + 0.1 * k for k in range(25)] for dy in (0.0, 0.3, -0.3, 0.6, -0.6)]:
        got = place([("%s\n%s" % (ref, f.GetValue()), 1.0)], [(x, y)], need=False) or \
              place([("%s\n%s" % (ref, f.GetValue()), 0.8)], [(x, y)], need=False)
        if got:
            print("%s at (%.1f, %.1f): %r %.1f mm" % (ref, got[0], got[1], got[2], got[3])); break
    else:
        raise SystemExit("no room for %s's label under it" % ref)

# 7. the passives: reference and value beside each, and pin 1 of the networks
for f in sorted(b.GetFootprints(), key=lambda f: f.GetReference()):
    ref = f.GetReference()
    if ref[0] not in "CR":
        continue
    if ref in ("R6", "R7"):
        continue
    got = place([("%s %s" % (ref, f.GetValue()), 1.0), ("%s %s" % (ref, f.GetValue()), 0.8)], around(ref))
    if ref.startswith("RN"):
        p1 = next(p for p in f.Pads() if p.GetNumber() == "1").GetPosition()
        place([("1", 0.8)], [(T(p1.x) + d, T(p1.y) + dy) for d in (0.0, 0.8, -0.8) for dy in (-1.5, 1.5, -1.8, 1.8)], need=False)

pcbnew.SaveBoard(PCB, b)
print("wrote", PCB)

# 8. the same courtyards in this folder's copy of the footprint library, so the board still matches it (Rev E's library
#    is left as it is)
LIB = os.path.join(DEST, "memory-rev-d-eagle.pretty")
for fn in sorted(os.listdir(LIB)):
    f = pcbnew.FootprintLoad(LIB, fn[:-len(".kicad_mod")])
    if f is None or f.GetCourtyard(pcbnew.F_CrtYd).OutlineCount() or not len(f.Pads()):
        continue
    edges = [(T(x.GetLeft()), T(x.GetTop()), T(x.GetRight()), T(x.GetBottom())) for x in (p.GetBoundingBox() for p in f.Pads())]
    s = pcbnew.PCB_SHAPE(f); s.SetShape(pcbnew.SHAPE_T_RECT); s.SetLayer(pcbnew.F_CrtYd); s.SetWidth(MM(0.05))
    s.SetStart(V(min(e[0] for e in edges) - 0.1, min(e[1] for e in edges) - 0.1))
    s.SetEnd(V(max(e[2] for e in edges) + 0.1, max(e[3] for e in edges) + 0.1)); f.Add(s)
    pcbnew.FootprintSave(LIB, f)
print("library courtyards written")
sys.stdout.flush(); os._exit(0)
