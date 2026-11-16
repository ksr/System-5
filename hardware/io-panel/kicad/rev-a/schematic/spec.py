# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-30
"""IO panel card Rev A, redrawn by tools/kicad/sch/gen_schematic.py from ../reports/netlist.net. Design: ../DESIGN.md."""
PROJ = "io-panel-rev-a-schematic"
TITLE = "System-5 IO panel card Rev A"
SUBTITLE = "The front panel: port 4 LEDs, TIL311s and switches; INPUT; ELF-style RUN and LOAD with DMA loading; 36-pin bus"
THEORY = "Design: hardware/io-panel/kicad/rev-a/DESIGN.md; the bus: docs/manual/bus.md (the 36-pin extension)"
DATE = "2026-10-30"
REV = "A"
BUSREF = "J1"
POWER = ("+5V", "GND")
ROOT_NOTE = "Redrawn from the board netlist; proven pin for pin against it (gen_schematic.py)."
VALUES = {"U1": "74HCT138", "U2": "74HCT374", "U3": "74HCT244", "U4": "74HCT14", "U5": "74HCT10", "U6": "74HCT00",
          "U9": "74HC05", "U10": "74HCT74", "U11": "74HCT74"}
SHEETS = [
    ("decode", "Decode", "PORT 4 DECODE AND STROBES",
     ["U1", ("U4", 2), ("U4", 3), ("U5", 1), ("U6", 1), ("U6", 2)], (["J1"], "left"),
     "U1 decodes N0-N2: PORT4_L is low through an INP 4 / OUT 4. OUT 4: OUTCLK = NAND(port 4, -MRD low, TPB) (U5A)\n"
     "clocks the 74HCT374 as TPB ends. INP 4 or this card's DMA: the 74HCT244 drives the bus while -MRD is high (U6A, U6B)."),
    ("output", "Output", "OUT 4: LATCH, EIGHT LEDS, TWO TIL311 HEX DISPLAYS",
     ["U2", "U7", "U8"] + ["D%d" % k for k in range(1, 9)] + ["R%d" % k for k in range(1, 9)], None,
     "U2 latches the OUT 4 byte. The LEDs show it bit by bit (sourced through 1k), U7 shows bits 7-4 and U8 bits 3-0 in\n"
     "hex (TIL311 strobe low = transparent, blanking low = on). TIL311 pinout as on Ken's YACC1 IO card."),
    ("input", "Input", "INP 4 (AND LOAD DATA): EIGHT TOGGLE SWITCHES",
     ["U3"] + ["SW%d" % k for k in range(1, 9)], None,
     "Eight SPDT toggles SW1-SW8 (as on the YACC1 IO card): common = the bit, +5V = 1, GND = 0. U3 puts them on D0-D7 for INP 4 and, in LOAD mode, for this\n"
     "card's own DMA IN."),
    ("control", "Control", "INPUT BUTTON, RUN AND LOAD, ONE DMA IN PER PRESS, Q LED",
     ["SW9", "R9", "C1", ("U4", 1), ("U4", 4), ("U4", 5), ("U4", 6), ("U6", 3), "SW10", "SW11", "U10", ("U11", 1),
      ("U9", 1), ("U9", 2), ("U9", 3), "D9", "R10"], None,
     "INPUT (SW9, R9/C1 + Schmitt) drives -EF1 (open collector, U9). SW10 RUN/RESET grounds -RESET, SW11 LOAD grounds\n"
     "-PAUSE: both = LOAD mode (LOAD_H). In LOAD mode a press sets REQ (U10A: -DMAIN); the write's -MWR rise sets ACK (U10B),\n"
     "which clears REQ until the button is let go. DRIVE (U11A) keeps the switches on the bus until -MRD falls."),
    ("power", "Power", "POWER, DECOUPLING, POWER LED", ["D10", "R11", "C2"], None, "One 0.1 uF (0.1\" leads) per chip; C2 10 uF."),
]
