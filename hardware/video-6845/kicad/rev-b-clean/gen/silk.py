#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-20
"""silk.py - Rev B-Clean's silkscreen (Ken, 2026-11-20: "add bypass caps and proper silkscreen"), on the board
gen/make_board.py makes from Rev B's, which still carries Rev B's silkscreen texts. Run it after make_board.py
(gen/build.sh does), with KiCad's Python; it can be run again on its own for a silkscreen-only change:

    /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 gen/silk.py

Rev B's silkscreen, as the 2005 board and its 2026 order master have it, is what Ken's rules for new boards rule out
(~/.claude/CLAUDE.md, "Board layout"): each chip's label printed inside the chip's outline, where the chip hides it;
texts at 0 and 90 degrees, read with the board lying flat; no name line. This script takes every Rev B text off and
writes them all again, on tools/kicad/silk270.py, the placer the other new cards use:

  * every text at KiCad angle 270: upright, left to right, with the card standing in the bus, connector down (the cards
    are drawn with the bus on the left). The one exception is the name line, at angle 0 along the bottom edge as
    drawn, where the DB9 was: it reads up the side of the standing card
  * each label at the first spot clear of every pad, every part's body (the chip in its socket, the bus header's
    plastic: gen/footprints.py draws them) and outline, every other text, the board edge and the card-guide strips
    (3.00 x 0.15 in from the bus edge along the top and bottom edges), so that it can be read with the parts fitted
  * each chip: its reference and type over its job ("IC4 74LS85" / "BLOCK SELECT"), beside the chip
  * each capacitor, resistor and network: its reference and value ("C1 0.1uF", "RN1 10k x4"); the crystal its
    frequency; pin 1 of the network; + at the 10 uF capacitor's positive lead
  * the bus pins' names, as the bus Rev D backplane names them (tools/s5bus.py), on the board side of J1's pads, and
    "J1 BUS"; nothing between the pads and the board edge, where the right-angle header's body lies
  * SV1, the address block: A15 A14 A13 A12 at its four pairs, and what a shunt does (SHUNT = 0; A15 ONLY = 7000,
    where HBIOS expects the card)
  * J2, the RCA jack: COMPOSITE VIDEO; the LED by its function, PWR (pcb-check.ini exempts its reference, as on the
    other new cards)
  * the name line: "System-5 6845 video  Rev B-Clean  2026" with cottageworker.com

Nothing on a copper layer changes: every track, via and pad stays where make_board.py left it."""
import os, sys
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__)); DEST = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(DEST, "..", "..", "..", ".."))
PCB = os.path.join(DEST, "video-6845-rev-b-clean.kicad_pcb")
sys.path.insert(0, os.path.join(ROOT, "tools", "kicad")); import silk270
sys.path.insert(0, os.path.join(ROOT, "tools")); import s5bus
MM, T = pcbnew.FromMM, pcbnew.ToMM

NAME, URL = "System-5 6845 video  Rev B-Clean  2026", "cottageworker.com"
# each chip's job, short enough to stand beside its reference and type within the chip's own length (the chips of the
# right-hand column lie one above the other 2.5 mm apart: a longer label would run on into the next chip's)
JOB = {"IC1": "VIDEO RAM", "IC2": "A8-A15 LATCH", "IC3": "CRTC", "IC4": "BLOCK SELECT", "IC5": "SEL/CHAR CLK",
       "IC6": "OSC/INVERT", "IC7": "CHAR BIT 6", "IC8": "CHAR CLK /6", "IC9": "CURSOR/DE",
       "IC10": "CHAR LATCH", "IC11": "DOT SHIFT", "IC12": "CHAR ROM", "IC13": "VIDEO XOR", "IC14": "VIDEO/SYNC OUT"}

b = pcbnew.LoadBoard(PCB)
# 1. every silkscreen text off the board (Rev B's 36, or this script's own from an earlier run)
old = [t for t in b.GetDrawings() if isinstance(t, pcbnew.PCB_TEXT) and t.GetLayer() == pcbnew.F_SilkS]
for t in old:                                           # (collected first: removing while walking breaks pcbnew)
    b.Remove(t)
eb = b.GetBoardEdgesBoundingBox(); EDGE = (T(eb.GetLeft()), T(eb.GetTop()), T(eb.GetRight()), T(eb.GetBottom()))
STRIPS = [(EDGE[0], EDGE[1], EDGE[0] + 76.2, EDGE[1] + 3.81), (EDGE[0], EDGE[3] - 3.81, EDGE[0] + 76.2, EDGE[3])]
s = silk270.Silk(b, no_silk=STRIPS)                     # hides the parts' own fields, moves their own texts to F.Fab
value = lambda ref: b.FindFootprintByReference(ref).GetValue()
pad = lambda ref, n: next((T(p.GetPosition().x), T(p.GetPosition().y)) for p in b.FindFootprintByReference(ref).Pads() if p.GetNumber() == n)
placed = {}
def note(what, got):
    if got: placed[what] = got
    return got

# 2. the bus: its pins' names beside the pads on the board side, as the backplane names them; then "J1 BUS"
assert b.FindFootprintByReference("J1").FindPadByNumber("1").GetNetname() == "VCC"      # pin 1 is +5V, pin 30 GND
s.pin_names("J1", {str(n): name for n, name in s5bus.bus().items()})
note("J1", s.bus_label("J1", "J1 BUS"))

# 3. the name line, at angle 0 along the bottom edge as drawn (up the side of the standing card), ending where the DB9
#    was. At 1.2 mm (pcb-check's least for the name and rev) it is 40 mm long, and the edge beyond the card-guide
#    strip is 35 mm up to the RCA jack, so it runs just above the strip, as far right as it fits, with
#    cottageworker.com after it or under it
rows = [EDGE[3] - 3.81 - d for d in (1.2, 1.4, 1.6, 1.8, 2.0, 2.4)]
if not s.name_pair(NAME, 1.2, URL, 1.0, [(EDGE[0] + 77.0 + 0.5 * k, EDGE[3] - y) for y in (1.6, 2.0, 2.4, 3.0) for k in range(20)]
                   + [(x, y) for x in [EDGE[0] + 76.0 - 0.5 * k for k in range(130)] for y in rows], gap=1.5):
    raise SystemExit("no room for the name line")
for t in b.GetDrawings():
    if isinstance(t, pcbnew.PCB_TEXT) and t.GetText() in (NAME, URL):
        bb = t.GetBoundingBox()
        print("  name line  (%6.1f, %5.1f) %r, x %.1f to %.1f" % (T(t.GetPosition().x), T(t.GetPosition().y), t.GetText(), T(bb.GetLeft()), T(bb.GetRight())))

# 4. the chips: reference and type over the job, beside the chip (never on it: the socket and the chip would hide it)
#    Two lines within 5 mm of the chip (1.0 mm, then 0.8); else the reference and type alone there: one long line
#    would run on past the chip's end into the next chip's label. The chips that share a gap with a neighbour's label
#    go first (IC4 and IC5 with IC2; the right-hand column with IC12 and IC14), so each gets its two lines
ORDER = ["IC4", "IC5", "IC6", "IC7", "IC11", "IC8", "IC9"]
for ref in ORDER + sorted((r for r in JOB if r not in ORDER), key=lambda r: int(r[2:])):
    two = "%s %s\n%s" % (ref, value(ref), JOB[ref]); short = "%s %s" % (ref, value(ref))
    near = s.beside(ref, reach=5.0)
    got = s.place([(two, 1.0), (two, 0.8)], near, need=False) or s.place([(short, 1.0), (short, 0.8)], near, need=False) \
        or s.place([(two, 0.8), (short, 0.8)], s.beside(ref, reach=12.0), nearest=True)
    note(ref, got)

# 5. SV1, the address block: each pair's address line beside it (odd pins 1, 3, 5, 7 are A15, A14, A13, A12; the even
#    pins are ground, so a shunt makes that line 0), then what it is and what the shunts do
for n, name in (("1", "A15"), ("3", "A14"), ("5", "A13"), ("7", "A12")):
    (x, y1), (_, y2) = pad("SV1", n), pad("SV1", str(int(n) + 1))
    lo, hi = min(y1, y2), max(y1, y2)
    note("SV1 " + name, s.place([(name, 0.8)], [(x, yy) for d in (2.6, 2.8, 3.0, 3.3, 3.6, 4.0) for yy in (hi + d, lo - d)]))
block = "SV1 %s" % " ".join(value("SV1").split()[:2])  # "SV1 ADDRESS BLOCK"
note("SV1", s.place([(block, 1.0), (block, 0.8)], s.beside("SV1", reach=8.0, order=("left", "right")), nearest=True))
l, t_, r, bt = s.bbox("SV1")                            # what a shunt does: under the pairs' names when the card stands
note("SV1 note", s.place([("SHUNT = 0\n7000: A15 ONLY", 0.8)],
                         [(x, y) for y in [bt + 8.0 + 0.5 * k for k in range(16)] for x in [(l + r) / 2 + d for d in (0.0, 1.0, -1.0, 2.0, -2.0, 3.0, -3.0)]]
                         + s.beside("SV1", reach=14.0), nearest=True))

# 6. the jack, the LED, the crystal
note("J2", s.place([("J2 RCA\nCOMPOSITE VIDEO", 1.0), ("J2 RCA\nCOMPOSITE VIDEO", 0.8)], s.beside("J2", reach=8.0), need=False)
     or s.place([("J2 RCA  VIDEO", 0.8)], s.beside("J2", reach=10.0), nearest=True))
note("LED1", s.place([("PWR", 1.0), ("PWR", 0.8)], s.beside("LED1", reach=6.0), nearest=True))
note("Q1", s.label("Q1", "Q1 %s" % value("Q1"), two="Q1\n%s" % value("Q1")))

# 7. the passives: reference and value beside each; the network's pin 1; + at the 10 uF's positive lead
for f in sorted(b.GetFootprints(), key=lambda f: (f.GetReference()[:1], int("".join(c for c in f.GetReference() if c.isdigit()) or 0))):
    ref = f.GetReference()
    if ref[0] not in "CR":
        continue
    v = value(ref) + (" x4" if ref.startswith("RN") else "")
    note(ref, s.label(ref, "%s %s" % (ref, v), two="%s\n%s" % (ref, v)))
x, y = pad("RN1", "1")
note("RN1 pin 1", s.place([("1", 0.8)], [(x + dx, y + dy) for dy in (-1.9, 1.9, -2.2, 2.2, -2.6, 2.6) for dx in (0.0, 0.5, -0.5)]))
(xp, yp), (xm, ym) = pad("C8", "+"), pad("C8", "-")
dx = 1.0 if xp > xm else -1.0                           # beyond the + lead, away from the - lead, outside the can
note("C8 +", s.place([("+", 1.2), ("+", 1.0)], [(xp + dx * d, yp + dy) for d in (3.3, 3.6, 4.0, 4.4) for dy in (0.0, 1.0, -1.0, 2.0, -2.0)]
                     + [(xp + ox, yp + oy) for oy in (3.9, -3.9, 4.3, -4.3) for ox in (0.0, dx)]))

ok = s.report()
for what in sorted(placed, key=lambda w: (w[:2], len(w), w)):
    x, y, text, h = placed[what]
    print("  %-10s (%6.1f, %5.1f) %.1f mm  %r" % (what, x, y, h, text.replace("\n", " / ")))
texts = [t for t in b.GetDrawings() if isinstance(t, pcbnew.PCB_TEXT) and t.GetLayer() == pcbnew.F_SilkS]
angles = sorted({int(round(t.GetTextAngleDegrees())) for t in texts})
print("removed %d texts; wrote %d: %d at 270, %d at 0 (the name line)" % (
    len(old), len(texts), sum(int(round(t.GetTextAngleDegrees())) == 270 for t in texts), sum(int(round(t.GetTextAngleDegrees())) == 0 for t in texts)))
assert angles in ([0, 270], [270]), angles
if not ok:
    raise SystemExit("silk.py: a label found no room (above); nothing written")
pcbnew.SaveBoard(PCB, b)
print("wrote", PCB)
sys.stdout.flush(); os._exit(0)
