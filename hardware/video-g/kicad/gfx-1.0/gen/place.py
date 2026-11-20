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
PLACE, LABELS = {}, {}                           # placements; labels by function (common/silk.py)
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
# ---- the power LED (Ken, 2026-11-17): at TEXT's height (y 85.5) and as far in from the front edge as TEXT's, so the
#      two PWR LEDs line up side by side in the backplane; turned round so its anode (pad 2) faces R7: one short track
PLACE["R7"] = (138.0, 85.5, 0)
PLACE["LED1"] = (X1 - 3.0, 85.5, 180)

# ---- silkscreen (common/silk.py; Ken's rule of 2026-11-18: every text upright with the card standing, KiCad 270) ------
# jacks, the LED and the ATmega by what they are: (one line, two lines); the rest get "ref value" by themselves
LABELS.update({
    "J2": ("J2 MOUSE", "J2\nMOUSE"), "J3": ("J3 FTDI", "J3\nFTDI"), "J4": ("J4 FROM TEXT (J6)", "J4\nFROM TEXT (J6)"),
    "IC11": ("IC11 ATmega328P-PU", "IC11\nATmega328P-PU"), "LED1": "PWR",        # by its function alone, centred (Ken, 2026-11-18)
})
# fixed texts: the FTDI header's used pins named between it and the front edge, each beside its pin (GND toward the
# unused pin 2, DTR past pin 6); the header's pins run from pin 1 at y 42.0 down at 2.54 mm
FIXED = [("GND", 149.8, 43.0, 0.8, 270, None), ("TX", 149.8, 49.62, 0.8, 270, None),
         ("RX", 149.8, 52.16, 0.8, 270, None), ("DTR", 149.8, 55.5, 0.8, 270, None)]
# the name line along the bottom edge as drawn, angle 0 (up the right-hand side with the card standing), where the
# note stood until 2026-11-18, clear of the card-guide strip (the first 76.2 mm from the bus, 3.81 mm in from the
# edge): the name with its revision (pcb-check wants them in one text, 1.2 mm or more), cottageworker.com beside
# it, and the spots to try for the name
NAME = ("System-5 VIDEO-G GFX  Rev 1.0  2026", 1.2, "cottageworker.com", 0.9,   # one naming for all (Ken, 2026-11-18)
        [(x, Y1 - 1.7) for x in [120.0 - 1.0 * k for k in range(110)] if x > 86.5]       # beyond the guide strip
        + [(x, Y1 - 4.95) for x in [12.0 + 1.0 * k for k in range(170)]]                 # or just above it
        + [(x, Y0 + 1.7) for x in [96.0 + 1.0 * k for k in range(80)]]                  # or along the top edge
        + [(x, Y0 + 4.95) for x in [12.0 + 1.0 * k for k in range(80)]])
# no note on the board (Ken, 2026-11-18: "remove all the text on gfx 512x200/ ..."; it read "512x200 / 512x256, 2 pages,
# 7C00 window, 7804 control, 7806 Y / mouse": hardware/video-g/DESIGN.md has it)
NOTES = []
# the power LED's "PWR": level with the LED's middle, just off its body on the board side (the LED is turned round:
# its body runs from 6.77 to 1.77 mm in from the front edge)
SPOTS = {"LED1": [(X1 - 3.0 - 1.27 - 2.5 - 1.3 - 0.2 * k, 85.5) for k in range(12)]}


def _bus_names():
    """the 30 bus pins by the names the backplane has for them (tools/s5bus.py: "+5V", "-RESET"), as TEXT and the other
    new cards print them, in place of the C30 footprint's own texts (Eagle's "VCC" and "-RES") (2026-11-18)"""
    import os, sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "..", "tools"))
    import s5bus
    return {str(pin): name for pin, name in s5bus.bus().items()}
J1_NAMES = _bus_names()                            # beside J1's pads, {pad: name} (common/silk.py)
