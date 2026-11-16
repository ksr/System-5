# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-26
"""S5BUS-D, redrawn by tools/kicad/sch/gen_schematic.py from ../reports/netlist.net. Design: ../README.md."""
PROJ = "s5bus-d-schematic"
TITLE = "System-5 bus backplane Rev D (S5BUS-D)"
SUBTITLE = "Eight 36-pin slots, power terminal, bypass and bulk capacitors, pull-ups on D0-D7 and the open-collector lines"
THEORY = "Design: hardware/bus/kicad/rev-d/README.md; the bus: docs/manual/bus.md"
DATE = "2026-10-27"
REV = "D"
BUSREF = "J1"
POWER = ("+5V", "GND")
ROOT_NOTE = "Redrawn from the board netlist; proven pin for pin against it (gen_schematic.py)."
SHEETS = [
    ("slots", "Slots", "EIGHT 36-PIN SLOTS, EVERY POSITION BUSSED",
     [], (["J%d" % k for k in range(1, 9)], "top"),
     "Socket positions 1-3: -EF1, -EF2, -EF3 (the outer end); 4-33: the 30-pin System-5 bus, +5V at 4 ... GND at 33;\n"
     "34-36: -PAUSE, -DMAIN, SC0. A 30-pin card plugs into positions 4-33."),
    ("pullups", "Pull-ups", "10K PULL-UPS: D0-D7 (RN1) AND THE OPEN-COLLECTOR LINES (RN2)", ["RN1", "RN2"], None,
     "RN1: an empty read gives FF. RN2: -EF, -EF1-3, -PAUSE, -DMAIN, -INT, -RESET (the CPU card also pulls up -INT and -RESET; these hold them with it out)."),
    ("power", "Power", "POWER IN, SWITCH, FUSE, REVERSE PROTECTION, BULK CAPACITOR, POWER LED", ["J9", "SW1", "F1", "Q1", "R2", "C1", "R1", "D1"], None,
     "J9: +5V (pin 1) and GND (pin 2). SW1 power switch (ON = common to pin 3; pin 1 open), F1 4 A polyfuse. Q1 P-MOSFET,\n"
     "drain to the supply, source to the cards, gate to GND (R2): on when the supply is right, off when it is reversed.\n"
     "C1 220 uF bulk; C2-C9 0.1 uF, one at each slot. No regulator."),
]
