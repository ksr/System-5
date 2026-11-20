# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-01
"""place.py - VIDEO-G 1.0 TEXT placement for common/make_board.py (board coordinates, mm; the bus edge is x = 10.025,
the front edge x = 10.025 + LENGTH; along the backplane the card runs from y = YTOP, -0.35, to 106.215: 106.565 mm with
the 36-pin connector since 2026-11-18, 10.375 mm more than a 30-pin card's 96.19, all of it at the +5V end).

TEXT has 24 ICs, four of them 600-mil or 28-pin, plus three jacks at the front edge: it does not fit the standard
140.95 mm card (hardware/video-g/DESIGN.md section 1), so LENGTH is 188 mm - the same width along the backplane, the
bus edge, connector and card-guide corners of every System-5 card, 47 mm taller.

Every IC stands with pin 1 at the top-left (rotation 0) in columns: bus side first (latch, block decode, port decode,
status and key latch), then the IDT7134, the 6845 and the character ROM with its code latch, then the dot pipeline,
the gates and the keyboard ATmega. The band above each socket holds its bypass cap (right) and its label "ICn / type"
(left), readable with the chips in (Ken's rule, 2026-10-31). The ribbon header J6 lies along the bottom edge at
x 88-147.5, the same place as GFX's J4. Front edge, top to bottom: the DB9 (its flange at the edge, the D-shell
overhanging it, as right-angle DB9s mount), the RCA, the keyboard jack, the LED and the FTDI header; behind them a
strip of standing resistors and caps labelled on their sides. The MONITOR jumper JP1 sits under the bus-side columns,
past the bus header's GND end; the KBD FLAG block JP3 in the strip at the +5V end, by J1's -EF1, -EF2 and -EF3 pins.
"""
LENGTH = 188.0
# The 36-pin bus connector (Ken, 2026-11-18, for the keyboard's choice of four EF lines: -EF1 to -EF3 are on the slot's
# positions beyond +5V). Positions 1-30 are where the 30-pin C30's pins were (GND at the bottom as drawn, position 1),
# 31-36 run on past +5V, and the board grows 10.375 mm at that end only: its top edge is 6.40 mm beyond position 36 (the
# other 36-pin cards: 6.35; at the GND end 11.265, a 30-pin card's). No part moved, and J6 keeps its place against GFX's
# J4. 188 x 106.565 mm
YTOP = 10.025 - 10.375
J1 = (15.735, 50.50, 90)                          # the C36's middle; pad 1 (GND) at y 94.95, pad 36 at 6.05
ROUTE_SEED = 7          # common/route.py: the order of Freerouting's input. Tried 2026-11-17, seeds 0-10: nine routed
#                         every net; 7 finished soonest, with 14.9 m of track and 222 vias (0, the sorted order, routes too)
X0, Y0, Y1 = 10.025, 10.025, 106.215
X1 = X0 + LENGTH
BAND, GAP = 4.8, 0.3
LEN = {14: 16.9, 16: 19.4, 20: 24.5, 28: 34.7, 40: 49.9, 48: 60.0}
PLACE, LABELS = {}, {}                           # placements; labels by function (common/silk.py)


def _caps():
    import os, importlib.util
    spec = importlib.util.spec_from_file_location("nl", os.path.join(os.path.dirname(os.path.abspath(__file__)), "netlist.py"))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return {ic: cap for cap, ic in m.DECOUPLE.items() if cap != "C25"}      # C25 = the ATmega's AVCC, placed by hand
CAP_OF = _caps()


def column(x, y_top, items, wide=False):
    """stack ICs (ref, pins) from y_top down at pin-1 x; each gets its bypass cap in the band above it"""
    y = y_top
    for ref, n in items:
        PLACE[ref] = (x, y + BAND + 1.6, 0)
        cap = CAP_OF.get(ref)
        if cap: PLACE[cap] = (x + (15.6 if wide else 8.0), y + 2.4, 0)
        y += BAND + 1.6 + LEN[n] + GAP
    return y


def side(ref, x, y, rot=90, short=False, away=1):
    """where a label went beside a part until 2026-11-18; since then common/silk.py places every label at 270 itself
    (Ken's rule: upright with the card standing), so this records nothing"""


TOP_GUIDE, TOP = 14.3, 11.0                       # below the card-guide keep-out (x < 86.2) / beyond it
# ---- bus side --------------------------------------------------------------------------------------------------------
column(23.0, TOP_GUIDE, [("IC1", 20), ("IC2", 16), ("IC24", 14)])          # A8-A15 latch, block decode, IOCYC/KEY-READY
column(38.0, TOP_GUIDE, [("IC8", 20), ("IC5", 16), ("IC6", 16)])           # status, port select, read enables
column(53.0, TOP_GUIDE, [("IC9", 20), ("IC7", 16), ("IC18", 14)])          # key latch, write strobes, HCT08
PLACE["JP1"] = (24.0, 98.7, -90)                                            # MONITOR, under the bus-side columns
PLACE["JP3"] = (24.0, 8.0, 90)             # KBD FLAG, a 2 x 4 block at the top edge by J1's -EF1..-EF3 pins (2026-11-18): odd
#                                            pins (y 8.0) -EF1, -EF2, -EF3, -EF; even pins (y 5.46) the flag; it was a 1 x 2 at (54, 98.7)
y = column(68.0, TOP_GUIDE, [("IC3", 48)], wide=True)                      # the IDT7134
PLACE["RN1"] = (69.6, y + 2.0, 0); PLACE["RN2"] = (69.6, y + 6.0, 0); PLACE["RN3"] = (69.6, y + 10.0, 0)

PLACE["SV1"] = (69.6, 100.0, 90)                                            # BLOCK, under the IDT
# ---- middle: 6845, ROM + code latch (above the ribbon header) ---------------------------------------------------------
y = column(90.6, TOP, [("IC4", 40), ("IC21", 14)], wide=True)
y = column(113.2, TOP, [("IC12", 28), ("IC11", 20)], wide=True)
PLACE["R3"] = (114.0, y + 2.0, 0)                                           # CNTEN pull-up
PLACE["R1"] = (124.5, y + 2.0, 0); PLACE["R2"] = (124.5, y + 6.0, 0)       # oscillator bias, next to Y1
for k, r in enumerate(("R11", "R12", "R13")):                               # ribbon clock series resistors
    PLACE[r] = (109.5 + 6.5 * k, 92.7, 0); side(r, 109.5 + 6.5 * k + 4.3, 92.7, short=(r == "R13"))   # R13: R2 above
# ---- dot pipeline, gates, keyboard ------------------------------------------------------------------------------------
y = column(135.8, TOP, [("IC13", 16), ("IC15", 16), ("IC16", 14)])         # shifter, counter, oscillator
PLACE["Y1"] = (135.6, y + 2.6, 0); side("Y1", 145.4, y + 2.6)              # 12 MHz, right under the oscillator
column(150.8, TOP, [("IC17", 14), ("IC19", 14), ("IC23", 14), ("IC20", 14)])
column(165.8, TOP, [("IC22", 14), ("IC14", 16), ("IC10", 28)])             # XORs, delays, keyboard ATmega
# ---- the strip behind the jacks (x 176.5-183.3): standing parts, labels turned on their right ---------------------------
SX, LX = 178.0, 182.4
PLACE["JP2"] = (178.3, 14.6, 0)                                            # VSYNC +/-, next to the DB9
PLACE["R4"] = (SX, 25.5, 0); side("R4", LX, 25.5)                          # video mix
PLACE["R5"] = (SX, 30.5, 0); side("R5", LX, 30.5)
PLACE["F1"] = (178.0, 46.0, 90); side("F1", 181.6, 42.6)                   # keyboard +5 V
# R9/R10 keyboard pull-ups, R7 ATmega reset, R8 RESETH: a label each, reference and value on one line
PLACE["R9"] = (SX, 51.0, 0); side("R9", LX, 51.0)                          # 6 mm apart (2026-11-17, from 5): each
PLACE["R10"] = (SX, 57.0, 0); side("R10", LX, 57.0)                        # label fits on one line ("R10 4.7k")
PLACE["R7"] = (SX, 63.0, 0); side("R7", LX, 63.0)
PLACE["R8"] = (SX, 69.0, 0); side("R8", LX, 69.0)
PLACE["C25"] = (179.0, 75.0, 0); side("C25", LX, 75.0)                     # ATmega AVCC
PLACE["Y2"] = (179.4, 86.0, 90); side("Y2", 183.0, 83.0)                   # 16 MHz
PLACE["C28"] = (179.0, 93.0, 0); side("C28", LX, 93.0)
PLACE["C29"] = (179.0, 98.0, 0); side("C29", LX, 98.0)
# ---- front edge: DB9 (flange at the edge), RCA, keyboard, LED, FTDI ----------------------------------------------------
PLACE["J3"] = (X1 - 11.5, 27.2, -90)                                        # DB9: TTL video / IBM 5151
PLACE["J2"] = (X1 - 11.8, 48.0, -90)                                        # RCA: composite
PLACE["J4"] = (X1 - 0.3, 70.0, 0)                                           # keyboard
PLACE["R6"] = (185.5, 83.5, 0); side("R6", 189.7, 83.5)
PLACE["LED1"] = (X1 - 5.5, 85.5, 0)
PLACE["C27"] = (188.5, 93.0, 0); side("C27", 191.6, 93.0)                  # DTR
PLACE["C26"] = (187.0, 100.5, 0)                                             # bulk
PLACE["J5"] = (X1 - 2.5, 91.0, 0)                                           # FTDI
# ---- the ribbon header along the bottom edge (same place on GFX) --------------------------------------------------------
PLACE["J6"] = (93.6, 101.3, 90)

# ---- silkscreen (common/silk.py; Ken's rule of 2026-11-18: every text upright with the card standing, KiCad 270) ------
# jacks, jumpers and LEDs by what they do: (one line, two lines); the chips and passives get "ref value" by themselves
LABELS.update({
    "J2": ("J2 RCA COMPOSITE", "J2 RCA\nCOMPOSITE"), "J3": ("J3 DB9 TTL 5151", "J3 DB9\nTTL 5151"),
    "J4": ("J4 KEYBOARD", "J4\nKEYBOARD"), "J5": ("J5 FTDI", "J5\nFTDI"), "J6": ("J6 TO GFX (J4)", "J6\nTO GFX (J4)"),
    "LED1": "PWR",                                # by its function alone, centred on the LED (Ken, 2026-11-18; pcb-check.ini)
    "SV1": "SV1 ADDRESS BLOCK\nSHUNT = 0\nA15 ONLY = 7000",    # all three lines or none (Ken: "can sv1 have better label")
    "JP1": ("JP1 MONITOR", "JP1\nMONITOR"),        # its settings at its ends (PIN_LABELS), like JP2's
    "JP2": ("JP2 VSYNC", "JP2\nVSYNC"), "JP3": ("JP3 KBD FLAG", "JP3\nKBD FLAG"),
})
# what a jumper's shunt picks, at the header's ends: 1-2 at pin 1, 2-3 at pin 3. JP1's were in its label ("1-2 NTSC
# 2-3 5151") until 2026-11-18: that label lay in the margin beside J1's last pads, half of it under the bus header's
# plastic body, and the name line had left no room at JP1's pin 1 end (it starts 1.2 mm further along now)
PIN_LABELS = {"JP2": {"1": "+", "3": "-"}, "JP1": {"1": "NTSC", "3": "5151"}}
# each pair of the two 2 x 4 blocks named: SV1's address bits above its pairs (a shunt makes that bit 0), JP3's flag
# lines below its pairs (one shunt). Fixed texts at 270, placed before every other label
FIXED = ([(n, 69.6 + 2.54 * k, 94.3, 0.8, 270, None) for k, n in enumerate(("A15", "A14", "A13", "A12"))]
         + [(n, 24.0 + 2.54 * k, 11.5 if len(n) == 4 else 11.1, 0.8, 270, None) for k, n in enumerate(("-EF1", "-EF2", "-EF3", "-EF"))])
# (JP3's four names start 0.3 mm off the block's outline: 0.5 mm nearer, as first drawn, each minus sign touched the
# outline and "-EF1" read as "EF1" with a tick; seen in the pcb-check session's facts, 2026-11-19)
# the power LED's "PWR": level with the LED's middle, just off its body on the board side.
# "J1 BUS": in the gap between IC1 and IC2, right beside the pin names at the connector's middle. Not in the margin
# beside J1's pads, where the right-angle header's plastic body lies (it was printed there, half under the header, until
# 2026-11-18), and the corner past the header's GND end is JP1's
SPOTS = {"LED1": [(X1 - 5.5 + 1.27 - 2.5 - 1.3 - 0.2 * k, 85.5) for k in range(12)],
         "J1": [(22.0 + 0.2 * k, 47.8 + dy) for k in range(20) for dy in (0.0, 0.2, -0.2, 0.4, -0.4)],
         # "JP1 / MONITOR" under JP1 with the card standing (left of it as drawn), past "5151": the corner between the
         # bus header's GND end and the card-guide strip, 6 mm along the edge, which the placer's 1 mm steps miss
         "JP1": [(14.2 - 0.2 * k, 99.4 + dy) for k in range(10) for dy in (0.0, 0.1, -0.1, 0.2, -0.2)],
         # "J3 DB9 TTL 5151" in the 1.5 mm between the DB9's back and R4's lead, level with the connector's middle: the
         # one place for it on the board side of the jack, and narrower than the placer's 0.2 mm steps from the part's
         # body (it was found by chance while the DB9's fab drawing was its pin tails; with the whole connector drawn
         # there, 2026-11-19, the steps fell either side of it and the label went beyond the resistors)
         "J3": [(182.376 + dx, 27.2) for dx in (0.0, 0.01, -0.01, 0.02, -0.02, 0.03, -0.03)]}
# the name line along the bottom edge as drawn, angle 0 (up the right-hand side with the card standing), clear of the
# card-guide strip (the first 76.2 mm from the bus, 3.81 mm in from the edge): the name with its revision (pcb-check
# wants them in one text, 1.2 mm or more), cottageworker.com beside it, and the spots to try for the name
_SPOTS = ([(x, Y1 - d) for d in (2.6, 2.8, 3.0) for x in [166.0 - 1.0 * k for k in range(110)] if x > 86.5]
          + [(x, Y1 - d) for d in (5.0, 5.3, 5.9, 6.2, 6.6, 7.4) for x in [27.5 + 1.0 * k for k in range(155)]]   # from 27.5:
          #   JP1's "NTSC" stands between JP1's pin 1 end and the name
          + [(x, Y0 + d) for d in (2.6, 2.8) for x in [96.0 + 1.0 * k for k in range(80)]]
          + [(x, Y0 + d) for d in (5.9, 6.2) for x in [12.0 + 1.0 * k for k in range(80)]])
# one naming for all (Ken, 2026-11-18): the board has no free run along an edge for "System-5 VIDEO-G TEXT  Rev 1.0
# 2026" on one line, so two lines, else three
def _positions():
    import os, importlib.util
    spec = importlib.util.spec_from_file_location("nl2", os.path.join(os.path.dirname(os.path.abspath(__file__)), "netlist.py"))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return {str(i + 1): n for i, n in enumerate(m.POS)}
J1_NAMES = _positions()                            # the 36 positions' names beside J1's pads (the C36 has no texts of its own)
NAME = [("System-5 VIDEO-G TEXT\nRev 1.0  2026", 1.2, "cottageworker.com", 0.8, _SPOTS, 1.2),     # 1.2: the gap between
        ("System-5\nVIDEO-G TEXT\nRev 1.0  2026", 1.2, "cottageworker.com", 0.8, _SPOTS, 1.2)]   # them (SV1's label follows)
