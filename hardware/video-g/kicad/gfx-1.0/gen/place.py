# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-01
"""place.py - VIDEO-G 1.0 GFX placement for common/make_board.py (board coordinates, mm; the bus edge is x = 10.025,
the front edge x = 10.025 + LENGTH; the card is 96.19 mm along the backplane, y = 10.025 to 106.215).

Every IC stands with pin 1 at the top-left (rotation 0) in columns; the band above each socket holds its bypass cap
(right) and its label "ICn / type" (left), so references stay readable with the chips in (Ken's rule, 2026-10-31).
The ribbon header J4 lies along the bottom edge at x 88-147.5, the same place as TEXT's J6, so the 40-way cable goes
straight across between the two slots. The mouse jack J2 faces out of the front edge.
"""
LENGTH = 140.95                                   # the standard System-5 card
X0, Y0, Y1 = 10.025, 10.025, 106.215
BAND, GAP = 4.8, 0.4                              # cap + label band above each socket; gap below it
LEN = {14: 16.9, 16: 19.4, 20: 24.5, 28: 34.7}    # courtyard bottom below pin 1 (DIP sockets)
PLACE, REFPOS, TEXTS, LABELS = {}, {}, [], {}
CAP_OF = {}                                       # IC -> its bypass cap (netlist DECOUPLE, inverted)


def column(x, y_top, items, wide=False):
    """stack ICs (ref, pins) from y_top down at pin-1 x; each gets its bypass cap in the band above it"""
    y = y_top
    for ref, n in items:
        PLACE[ref] = (x, y + BAND + 1.6, 0)
        cap = CAP_OF.get(ref)
        if cap: PLACE[cap] = (x + (15.6 if wide else 8.0), y + 2.4, 0)
        y += BAND + 1.6 + LEN[n] + GAP
    return y


def _caps():
    import os, importlib.util
    spec = importlib.util.spec_from_file_location("nl", os.path.join(os.path.dirname(os.path.abspath(__file__)), "netlist.py"))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return {ic: cap for cap, ic in m.DECOUPLE.items() if cap != "C20"}      # C20 = the ATmega's AVCC, placed by hand
CAP_OF = _caps()

# ---- columns (pin-1 x), bus side first --------------------------------------------------------------------------------
TOP_GUIDE = 14.3                                  # below the card-guide keep-out (x < 86.2)
TOP = 11.0                                        # beyond the keep-out
column(23.0, TOP_GUIDE, [("IC7", 20), ("IC6", 20), ("IC17", 14)])           # write buffer, read latch, NAND4s
column(38.0, TOP_GUIDE, [("IC10", 20), ("IC19", 20), ("IC14", 14)])         # Y register, control register, inverters
column(53.0, TOP_GUIDE, [("IC12", 20), ("IC16", 14), ("IC18", 14)])         # mouse latch, ANDs, ORs
y = column(68.0, TOP_GUIDE, [("IC1", 28), ("IC8", 20)], wide=True)          # graphics RAM, display latch
PLACE["RN1"] = (64.6, 91.0, 0)                                               # GD pull-ups under the RAM column
column(90.6, TOP, [("IC2", 16), ("IC3", 16), ("IC4", 16)])                  # address muxes
column(105.6, TOP, [("IC5", 16), ("IC9", 16), ("IC13", 14)])                # mux, dot shifter, WRQ / MOUSE-READY
y = column(120.6, TOP, [("IC11", 28)])                                       # the mouse ATmega
PLACE["C20"] = (132.4, PLACE["IC11"][1] + 20.32, 90)                         # AVCC (pin 20) bypass
PLACE["Y1"] = (119.0, y + 3.2, 0)                                            # 16 MHz under the ATmega
PLACE["C23"] = (121.0, y + 9.4, 0); PLACE["C24"] = (127.0, y + 9.4, 0)
column(120.6, y + 12.0, [("IC15", 14)])                                      # reset inverters

# ---- the ribbon header along the bottom edge (same place on TEXT) -------------------------------------------------------
PLACE["J4"] = (93.6, 101.3, 90)
# ---- front edge: mouse jack; FTDI, fuse, pull-ups behind it -------------------------------------------------------------
X1 = X0 + LENGTH
PLACE["J2"] = (X1 - 0.3, 25.0, 0)
PLACE["F1"] = (138.5, 36.4, 0)
PLACE["R4"] = (133.0, 42.0, 0); PLACE["R5"] = (133.0, 46.0, 0)
PLACE["R1"] = (133.0, 50.0, 0); PLACE["R2"] = (133.0, 54.0, 0); PLACE["R3"] = (133.0, 58.0, 0); PLACE["R6"] = (133.0, 62.0, 0)
PLACE["J3"] = (147.5, 42.0, 0)
PLACE["C21"] = (141.0, 67.0, 0)
PLACE["C22"] = (140.0, 77.0, 0)

LABELS.update({
    "J2": "MOUSE", "J3": "FTDI  GND . . TX RX DTR", "J4": "J4 FROM TEXT (J6)   PIN 1",
    "IC11": "IC11\nATmega\n328P",
})
REFPOS.update({
    "IC11": (119.2, 13.4, 0.8, 0, "left"), "Y1": (128.4, PLACE["Y1"][1], 0.8, 90, "c"),
    "C23": (117.2, PLACE["C23"][1], 0.8, 90, "c"), "C24": (130.1, PLACE["C24"][1], 0.8, 90, "c"),
    "J2": (139.0, 16.6, 1.0, 0, "left"), "J3": (150.3, 40.6, 0.8, 90, "left"),
    "J4": (88.4, 93.8, 0.9, 0, "left"),
})
TEXTS = [
    ("VIDEO-G 1.0 GFX", 104.0, 89.5, 1.4, 0, "left"),
    ("System-5   cottageworker.com", 104.0, 91.6, 0.9, 0, "left"),
    ("512x200 / 512x256 graphics, 2 pages  OUT 4 control  OUT 7 Y  INP 7 mouse", 23.0, 101.8, 0.8, 0, "left"),   # above the card guide
]
