# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-01
"""ribbon.py - the 40-pin ribbon between VIDEO-G TEXT (J6) and GFX (J4), pin for pin. Both netlists import it.

A 2 x 20 IDC header on each board, at the same edge and height, joined by a straight 40-way flat cable: conductor n
is pin n on both ends. The fast clocks each have a ground conductor on both sides. TEXT drives the display timing,
and the decoded GFX strobes (OUT 4, OUT 7, INP 7); GFX returns its dot stream (already gated by GFX-ON),
TEXT-ON and XOR from the control register it holds, MOUSE-READY and its presence.
"""
PINS = {1: "GND"}
for i in range(11):
    PINS[2 + i] = "MA%d" % i                     # 2-12  the 6845's MA0-MA10 (refresh address)
for i in range(3):
    PINS[13 + i] = "RA%d" % i                    # 13-15 RA0-RA2 (scan line in the character row)
PINS.update({16: "GND", 17: "DOTCLK", 18: "GND", 19: "CHARCLK", 20: "GND", 21: "QC", 22: "GND",
             23: "QCR",                          # QC OR RCO: the GFX address-mux select (1 = display)
             24: "WEPH",                         # QA XOR QB: counts 9-10, the GFX -WE phase
             25: "GND",
             26: "-WR4",                         # OUT 4 strobe: loads the control register (on GFX)
             27: "TEXTON",                       # GFX -> TEXT: NOT control bit 0 (TEXT pulls it up: text on alone)
             28: "XORM",                         # GFX -> TEXT: control bit 2, text XOR graphics (TEXT pulls it down)
             29: "GSEL",                         # the CPU is in 7800-7FFF (the graphics window)
             30: "-WR7",                         # OUT 7 strobe: loads the Y register
             31: "-RD7",                         # INP 7 read enable: the mouse latch drives D0-D7
             32: "GND",
             33: "GDOT",                         # GFX -> TEXT: graphics dots
             34: "GND",
             35: "MREADY",                       # GFX -> TEXT: a mouse byte waits (status bit 1)
             36: "GFXPRES",                      # GFX -> TEXT: tied high on GFX (status bit 5)
             37: "GND", 38: "GND", 39: "GND", 40: "GND"})
assert sorted(PINS) == list(range(1, 41))

FROM_GFX = ("GDOT", "MREADY", "GFXPRES", "TEXTON", "XORM")
TEXT_NET = {"DOTCLK": "RDOTCLK", "CHARCLK": "RCHARCLK", "QC": "RQC"}   # TEXT drives these through 33-ohm resistors
GFX_NET = {"CHARCLK": "CHARCLOCK"}
