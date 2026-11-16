# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-01
"""place.py - VIDEO-G 1.0 TEXT placement for common/make_board.py (board coordinates, mm; the bus edge is x = 10.025,
the front edge x = 10.025 + LENGTH; the card is 96.19 mm along the backplane, y = 10.025 to 106.215).

TEXT has 24 ICs, four of them 600-mil or 28-pin, plus three jacks at the front edge: it does not fit the standard
140.95 mm card (hardware/video-g/DESIGN.md section 1), so LENGTH is 188 mm - the same width along the backplane, the
bus edge, connector and card-guide corners of every System-5 card, 47 mm taller.

Every IC stands with pin 1 at the top-left (rotation 0) in columns: bus side first (latch, block decode, port decode,
status and key latch), then the IDT7134, the 6845 and the character ROM with its code latch, then the dot pipeline,
the gates and the keyboard ATmega. The band above each socket holds its bypass cap (right) and its label "ICn / type"
(left), readable with the chips in (Ken's rule, 2026-10-31). The ribbon header J6 lies along the bottom edge at
x 88-147.5, the same place as GFX's J4. Front edge, top to bottom: the DB9 (its flange at the edge, the D-shell
overhanging it, as right-angle DB9s mount), the RCA, the keyboard jack, the LED and the FTDI header; behind them a
strip of standing resistors and caps labelled on their sides. The MONITOR and KBD-EF jumpers sit under the bus-side
columns, next to the status port and the -EF pin.
"""
LENGTH = 188.0
X0, Y0, Y1 = 10.025, 10.025, 106.215
X1 = X0 + LENGTH
BAND, GAP = 4.8, 0.3
LEN = {14: 16.9, 16: 19.4, 20: 24.5, 28: 34.7, 40: 49.9, 48: 60.0}
PLACE, REFPOS, TEXTS, LABELS = {}, {}, [], {}


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


def side(ref, x, y, rot=90, short=False):
    """a label beside a part, turned (the strips are narrow); capacitors there, and parts too close together for their
    values (short), carry just the reference"""
    REFPOS[ref] = (x, y, 0.8, rot, "c")
    if short or ref.startswith("C"): LABELS[ref] = ref


TOP_GUIDE, TOP = 14.3, 11.0                       # below the card-guide keep-out (x < 86.2) / beyond it
# ---- bus side --------------------------------------------------------------------------------------------------------
column(23.0, TOP_GUIDE, [("IC1", 20), ("IC2", 16), ("IC24", 14)])          # A8-A15 latch, block decode, IOCYC/KEY-READY
column(38.0, TOP_GUIDE, [("IC8", 20), ("IC5", 16), ("IC6", 16)])           # status, port select, read enables
column(53.0, TOP_GUIDE, [("IC9", 20), ("IC7", 16), ("IC18", 14)])          # key latch, write strobes, HCT08
PLACE["JP1"] = (24.0, 98.7, -90)                                            # MONITOR, under the bus-side columns
PLACE["JP3"] = (54.0, 98.7, -90)                                            # KBD-EF
y = column(68.0, TOP_GUIDE, [("IC3", 48)], wide=True)                      # the IDT7134
PLACE["RN1"] = (69.6, y + 2.0, 0); PLACE["RN2"] = (69.6, y + 6.0, 0); PLACE["RN3"] = (69.6, y + 10.0, 0)
for k, r in enumerate(("RN1", "RN2", "RN3")):
    REFPOS[r] = (84.3, y + 2.0 + 4.0 * k, 0.8, 0, "left"); LABELS[r] = r
PLACE["SV1"] = (69.6, 100.0, 90)                                            # BLOCK, under the IDT
# ---- middle: 6845, ROM + code latch (above the ribbon header) ---------------------------------------------------------
y = column(90.6, TOP, [("IC4", 40), ("IC21", 14)], wide=True)
TEXTS += [("VIDEO-G 1.0 TEXT", 88.4, y + 1.5, 1.2, 0, "left"),
          ("System-5   cottageworker.com", 88.4, y + 3.3, 0.8, 0, "left")]
y = column(113.2, TOP, [("IC12", 28), ("IC11", 20)], wide=True)
PLACE["R3"] = (114.0, y + 2.0, 0)                                           # CNTEN pull-up
PLACE["R1"] = (124.5, y + 2.0, 0); PLACE["R2"] = (124.5, y + 6.0, 0)       # oscillator bias, next to Y1
for k, r in enumerate(("R11", "R12", "R13")):                               # ribbon clock series resistors
    PLACE[r] = (109.5 + 6.5 * k, 92.7, 0); side(r, 109.5 + 6.5 * k + 4.3, 92.7)
# ---- dot pipeline, gates, keyboard ------------------------------------------------------------------------------------
y = column(135.8, TOP, [("IC13", 16), ("IC15", 16), ("IC16", 14)])         # shifter, counter, oscillator
PLACE["Y1"] = (135.6, y + 2.6, 0); side("Y1", 145.4, y + 2.6)              # 12 MHz, right under the oscillator
column(150.8, TOP, [("IC17", 14), ("IC19", 14), ("IC23", 14), ("IC20", 14)])
column(165.8, TOP, [("IC22", 14), ("IC14", 16), ("IC10", 28)])             # XORs, delays, keyboard ATmega
for ic in ("IC22", "IC14", "IC10"):                                        # their caps' labels go left of the cap
    cap = CAP_OF[ic]; cx, cy, _ = PLACE[cap]; side(cap, cx - 3.0, cy)     # (the strip on the right is full), so
    ix, iy, _ = PLACE[ic]; REFPOS[ic] = (ix - 1.4, iy - 4.0, 0.8, 0, "left")   # these IC labels are 0.8 mm
LABELS["IC10"] = "IC10\nATmega\n328P"
# ---- the strip behind the jacks (x 176.5-183.3): standing parts, labels turned on their right ---------------------------
SX, LX = 178.0, 182.4
PLACE["JP2"] = (178.3, 14.6, 0); side("JP2", 181.0, 16.8)                 # VSYNC +/-, next to the DB9
PLACE["R4"] = (SX, 25.5, 0); side("R4", LX, 25.5)                          # video mix
PLACE["R5"] = (SX, 30.5, 0); side("R5", LX, 30.5)
PLACE["F1"] = (178.0, 46.0, 90); side("F1", 181.6, 42.6)                   # keyboard +5 V
# R9/R10 keyboard pull-ups, R7 ATmega reset, R8 RESETH: 5 mm apart, so just the reference ("R10 4.7k" would run into
# the next label); the values are in BOM.md
PLACE["R9"] = (SX, 52.0, 0); side("R9", LX, 52.0, short=True)
PLACE["R10"] = (SX, 57.0, 0); side("R10", LX, 57.0, short=True)
PLACE["R7"] = (SX, 62.0, 0); side("R7", LX, 62.0, short=True)
PLACE["R8"] = (SX, 67.0, 0); side("R8", LX, 67.0, short=True)
PLACE["C25"] = (179.0, 72.5, 0); side("C25", LX, 72.5)                     # ATmega AVCC
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

# the front-edge jacks are close together, so each caption points at its own jack (a triangle up or down)
LABELS.update({
    "J2": "\u25bc COMPOSITE", "J3": "\u25b2 TTL VIDEO 5151", "J4": "\u25bc KEYBOARD", "J5": "FTDI", "J6": "J6 TO GFX (J4)",
    "LED1": "PWR", "SV1": "BLOCK\n1-2=7000", "C26": "C26 47u", "JP1": "MONITOR 1-2 NTSC 2-3 5151", "JP2": "VSYNC 1-2 + 2-3 -",
    "JP3": "KBD-EF",
})
REFPOS.update({
    "J3": (184.0, 43.5, 0.9, 0, "left"), "J2": (184.0, 45.1, 0.9, 0, "left"), "J4": (185.0, 61.8, 0.9, 0, "left"),
    "LED1": (191.0, 81.1, 0.9, 0, "left"), "J5": (192.2, 98.0, 0.8, 90, "c"), "C26": (184.8, 105.0, 0.8, 0, "left"),
    "J6": (128.5, 94.0, 0.9, 0, "left"), "SV1": (79.8, 98.7, 0.8, 0, "left"),
    "JP1": (29.3, 98.7, 0.8, 0, "left"), "JP3": (59.3, 98.7, 0.8, 0, "left"),
})
