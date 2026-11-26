#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-20
"""silk.py - Rev B-Clean-Keyboard's silkscreen, on the routed board (gen/make_board.py, gen/route.py). It is Rev
B-Clean's gen/silk.py (../../rev-b-clean/gen/silk.py, which says what the rules are and how each label is placed) with
the keyboard section's parts added. Run it after the routing (gen/build.sh does), with KiCad's Python; it can be run
again on its own for a silkscreen-only change:

    /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 gen/silk.py

Every text at KiCad angle 270 (upright with the card standing in the bus, connector down), on tools/kicad/silk270.py,
but the name line, at angle 0 along the top or bottom edge as drawn (up the side of the standing card). Added here:

  * the bus: all 36 pins named (J1's pads 1-30 are the 30-pin card's pins, +5V to GND, as on Rev B's drawing; 31-36
    the slot's positions -EF1, -EF2, -EF3, -DMAIN, SC0, -PAUSE: tools/s5bus.py)
  * JP1 KBD FLAG: -EF1 -EF2 -EF3 -EF at its four pairs (one shunt picks the flag line the keyboard pulls low)
  * the keyboard chips IC15-IC21 with their jobs, J3 (PS/2 keyboard), J4 (FTDI: GND and DTR at its ends), the 16 MHz
    crystal Y1, the fuse, and every new resistor and capacitor with its value
  * the chips' real length (BODY below): the Eagle DIL footprints draw a 14-pin chip 1.33 mm past its end pins; a real one
    is 19.3 mm long, 2 mm past them, and hid part of IC5's label (Ken, 2026-11-24). No text goes where a fitted chip is
  * the name line: "System-5 6845 video  Rev B-Clean-Keyboard  2026" with cottageworker.com

Nothing on a copper layer changes."""
import os, sys
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__)); DEST = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(DEST, "..", "..", "..", ".."))
sys.path.insert(0, HERE); import keyboard as K
PCB = os.path.join(DEST, K.NEW + ".kicad_pcb")
sys.path.insert(0, os.path.join(ROOT, "tools", "kicad")); import silk270
sys.path.insert(0, os.path.join(ROOT, "tools")); import s5bus
MM, T = pcbnew.FromMM, pcbnew.ToMM

NAME, URL = "System-5 6845 video  Rev %s  2026" % K.REV, "cottageworker.com"
# each chip's job, short enough to stand beside its reference and type within the chip's own length (the chips of the
# right-hand column lie one above the other 2.5 mm apart: a longer label would run on into the next chip's)
JOB = {"IC1": "VIDEO RAM", "IC2": "A8-A15 LATCH", "IC3": "CRTC", "IC4": "BLOCK SELECT", "IC5": "SEL/CHAR CLK",
       "IC6": "OSC/INVERT", "IC7": "CHAR BIT 6", "IC8": "CHAR CLK /6", "IC9": "CURSOR/DE",
       "IC10": "CHAR LATCH", "IC11": "DOT SHIFT", "IC12": "CHAR ROM", "IC13": "VIDEO XOR", "IC14": "VIDEO/SYNC OUT",
       # the keyboard section
       "IC15": "KBD DECODE", "IC16": "KBD STROBES", "IC17": "TPB/RESET INV", "IC18": "KEY RDY/CRTC E", "IC19": "KEY LATCH",
       "IC20": "STATUS", "IC21": "PS/2 KEYBOARD", "IC22": "FLAG/RESET OC"}

b = pcbnew.LoadBoard(PCB)
# 1. every silkscreen text off the board (Rev B-Clean's, or this script's own from an earlier run)
old = [t for t in b.GetDrawings() if isinstance(t, pcbnew.PCB_TEXT) and t.GetLayer() == pcbnew.F_SilkS]
for t in old:                                           # (collected first: removing while walking breaks pcbnew)
    b.Remove(t)
eb = b.GetBoardEdgesBoundingBox(); EDGE = (T(eb.GetLeft()), T(eb.GetTop()), T(eb.GetRight()), T(eb.GetBottom()))
STRIPS = [(EDGE[0], EDGE[1], EDGE[0] + 76.2, EDGE[1] + 3.81), (EDGE[0], EDGE[3] - 3.81, EDGE[0] + 76.2, EDGE[3])]
s = silk270.Silk(b, no_silk=STRIPS)                     # hides the parts' own fields, moves their own texts to F.Fab
# how far a fitted chip's body runs past the centres of its end pins, mm: 14 pins 19.3 mm long; for the long chips the JEDEC
# maxima (24 pins 1.29 in, the 2732; 40 pins 2.07 in, the 6845; 48 pins 2.45 in, the IDT7134; 20 pins 1.06 in; 28 pins 1.45 in)
BODY = {14: 2.0, 16: 0.95, 20: 2.03, 24: 2.41, 28: 1.91, 40: 2.16, 48: 1.91}
for f in b.GetFootprints():
    if f.GetReference().startswith("IC"):
        n = len(list(f.Pads())); l_, t_, r_, b_ = s.pads(f.GetReference()); p_ = BODY[n]
        s.blocks.append((l_ - p_, t_, r_ + p_, b_) if r_ - l_ > b_ - t_ else (l_, t_ - p_, r_, b_ + p_))
value = lambda ref: b.FindFootprintByReference(ref).GetValue()
pad = lambda ref, n: next((T(p.GetPosition().x), T(p.GetPosition().y)) for p in b.FindFootprintByReference(ref).Pads() if p.GetNumber() == n)
placed = {}
def note(what, got):
    if got: placed[what] = got
    return got

# 2. the bus: its pins' names beside the pads on the board side, as the backplane names them; then "J1 BUS"
assert b.FindFootprintByReference("J1").FindPadByNumber("1").GetNetname() == "VCC"      # pin 1 is +5V, pin 30 GND
names = {str(n): name for n, name in s5bus.bus().items()}                 # pads 1-30: the 30-pin card's pins
names.update({str(n): name for n, name in s5bus.positions().items() if n > 30})   # 31-36: the slot's positions
assert len(names) == 36
# The four pins beside the 10 uF capacitor's can (33, 32, 31 and 1) have a lane 2.9 mm wide between the placer's margin
# round the pads (0.3 mm) and the can's (0.1 mm), and a name's box is 1.46 mm across: the placer's two columns, 2.4 and
# 4.2 mm from the pads, do not fit, and two tight ones miss by 0.02 mm. So the outer column is placed (3.23 mm from the
# pads, 0.1 mm clear of the can) and the inner one is put 1.77 mm from the pads, 0.03 mm inside that 0.3 mm margin
# (0.28 mm from the pads' copper, on the board side: nothing is covered). The three pins beyond, clear of the can, are
# placed as usual, in columns that miss those names; then the other pins as on every card
xj = pad("J1", "1")[0]; A, B, C = xj + 1.77, xj + 3.23, xj + 4.8
ypin = lambda n: pad("J1", n)[1]
near = lambda x, y: [(x + dx, y + dy) for dy in (0.0, 0.1, -0.1, 0.2, -0.2) for dx in (0.0, 0.05, -0.05)]
for n in ("32", "1"):
    note("J1 " + names[n], s.place([(names[n], 0.8)], near(B, ypin(n))))
for n in ("33", "31"):
    s.put(names[n], A, ypin(n), 0.8); note("J1 " + names[n], (A, ypin(n), names[n], 0.8))
# (the three beyond the can: columns 1.7 mm apart, a name's box and the placer's 0.2 mm between texts; -PAUSE, at the
# end, 0.1 mm or more down from the card-guide strip)
c1, c2, c3, c4 = xj + 1.8, xj + 3.5, xj + 5.2, xj + 6.9
note("J1 " + names["36"], s.place([(names["36"], 0.8)], [(x, ypin("36") + d) for x in (c1, c2) for d in (0.1, 0.2, 0.3, 0.5)]))
note("J1 " + names["35"], s.place([(names["35"], 0.8)], near(c2, ypin("35")) + near(c3, ypin("35"))))
note("J1 " + names["34"], s.place([(names["34"], 0.8)], near(c3, ypin("34")) + near(c4, ypin("34")) + near(c2, ypin("34"))))
s.pin_names("J1", {n: v for n, v in names.items() if 2 <= int(n) <= 30})
note("J1", s.bus_label("J1", "J1 BUS"))

# 3. the name line, at angle 0 (up the side of the standing card): in the strip along the top edge as drawn, past the
#    card-guide strip, where only tracks run; else just above the bottom card-guide strip, as on Rev B-Clean
top = [(EDGE[0] + 77.0 + 0.5 * k, EDGE[1] + y) for y in (2.0, 2.4, 3.0, 3.6, 4.2, 5.0) for k in range(110)]
rows = [EDGE[3] - 3.81 - d for d in (1.2, 1.4, 1.6, 1.8, 2.0, 2.4)]
if not s.name_pair(NAME, 1.2, URL, 1.0, top + [(EDGE[0] + 77.0 + 0.5 * k, EDGE[3] - y) for y in (1.6, 2.0, 2.4, 3.0) for k in range(60)]
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

# 5b. JP1 KBD FLAG: the flag line at each pair (odd pins -EF1, -EF2, -EF3, -EF; the even pins are the keyboard's
#     open-drain flag), 0.5 mm clear of the block's outline so that the minus sign reads; then what the block is
for n, name in (("1", "-EF1"), ("3", "-EF2"), ("5", "-EF3"), ("7", "-EF")):
    (x, y1), (_, y2) = pad("JP1", n), pad("JP1", str(int(n) + 1))
    lo, hi = min(y1, y2), max(y1, y2)
    note("JP1 " + name, s.place([(name, 0.8)], [(x, yy) for d in (3.3, 3.5, 3.7, 4.0, 4.4, 4.8) for yy in (hi + d, lo - d)]))
note("JP1", s.place([("JP1 KBD FLAG", 1.0), ("JP1 KBD FLAG", 0.8), ("JP1\nKBD FLAG", 0.8)], s.beside("JP1", reach=10.0, order=("left", "right", "ends")), nearest=True))

# 5c. the keyboard jack, the FTDI header (which end is which), the ATmega's crystal, the fuse
# (the two jacks stand one under the other at the front edge, the fuse and the pull-ups behind the PS/2 jack: its label
# goes above it, the RCA jack's in the gap behind it)
l3, t3, r3, b3 = s.bbox("J3")
note("J3", s.place([("J3 PS/2\nKEYBOARD", 1.0), ("J3 PS/2\nKEYBOARD", 0.8), ("J3 KEYBOARD", 0.8)],
                   [(x, t3 - d) for d in (4.6, 4.3, 4.9, 5.3, 4.0) for x in ((l3 + r3) / 2 + o for o in (0.0, -1.0, 1.0, -2.0, 2.0, -3.0, 3.0))]
                   + s.beside("J3", reach=10.0), nearest=True))
s.ends("J4", {"1": "GND", "6": "DTR"})                    # (its ends first: the header lies along the bottom edge)
note("J4", s.place([("J4 FTDI", 1.0), ("J4 FTDI", 0.8), ("J4\nFTDI", 0.8)], s.beside("J4", reach=12.0), nearest=True))
note("Y1", s.label("Y1", "Y1 %s" % value("Y1"), two="Y1\n%s" % value("Y1")))
for ref in ("F1",):
    note(ref, s.label(ref, "%s %s" % (ref, value(ref)), two="%s\n%s" % (ref, value(ref))))

# 6. the jack, the LED, the crystal
l2, t2, r2, b2 = s.bbox("J2")
behind = [(l2 - d, (t2 + b2) / 2 + o) for d in (2.2, 2.0, 2.4, 2.6, 1.8, 2.8, 3.0) for o in (0.0, 1.0, -1.0, 2.0, -2.0, 3.0, 4.0, 5.0)]
note("J2", s.place([("J2 RCA\nCOMPOSITE VIDEO", 0.8), ("J2 RCA\nVIDEO", 1.0), ("J2 RCA\nVIDEO", 0.8), ("J2 RCA VIDEO", 0.8)],
                   behind + s.beside("J2", reach=10.0)))
note("LED1", s.place([("PWR", 1.0), ("PWR", 0.8)], s.beside("LED1", reach=6.0), nearest=True))
note("Q1", s.label("Q1", "Q1 %s" % value("Q1"), two="Q1\n%s" % value("Q1")))

# 7. the passives: reference and value beside each; the network's pin 1; + at the 10 uF's positive lead.
#    R10 and R7 first: they stand in a row with C23 beside the 7416, and the capacitors, which come first in the
#    loop, would take the place beside R10 for C23's label and leave R10's under C23
for ref in ("R10", "R7"):
    note(ref, s.label(ref, "%s %s" % (ref, value(ref)), two="%s\n%s" % (ref, value(ref))))
for f in sorted(b.GetFootprints(), key=lambda f: (f.GetReference()[:1], int("".join(c for c in f.GetReference() if c.isdigit()) or 0))):
    ref = f.GetReference()
    if ref[0] not in "CR" or ref in placed:
        continue
    v = value(ref) + (" x4" if ref.startswith("RN") else "")
    note(ref, s.label(ref, "%s %s" % (ref, v), two="%s\n%s" % (ref, v)))
x, y = pad("RN1", "1")
note("RN1 pin 1", s.place([("1", 0.8)], [(x + dx, y + dy) for dy in (-1.9, 1.9, -2.2, 2.2, -2.6, 2.6) for dx in (0.0, 0.5, -0.5)]))
(xp, yp), (xm, ym) = pad("C8", "+"), pad("C8", "-")
dx = 1.0 if xp > xm else -1.0                           # beyond the + lead, away from the - lead, outside the can
note("C8 +", s.place([("+", 1.2), ("+", 1.0)], [(xp + dx * d, yp + dy) for d in (3.3, 3.6, 4.0, 4.4) for dy in (0.0, 1.0, -1.0, 2.0, -2.0)]
                     + [(xp + ox, yp + oy) for oy in (3.9, -3.9, 4.3, -4.3, -4.6, -5.0, 4.6, 5.0) for ox in (0.0, dx, -dx, 2 * -dx)]))

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
