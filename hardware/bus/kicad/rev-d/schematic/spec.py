# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-26
"""S5BUS-D, redrawn by tools/kicad/sch/gen_schematic.py from ../reports/netlist.net. Design: ../README.md."""
PROJ = "s5bus-d-schematic"
TITLE = "System-5 bus backplane Rev D (S5BUS-D)"
SUBTITLE = "Eight 36-pin slots, barrel jack and 5 V regulator or external 5 V, bypass and bulk capacitors, pull-ups and idle-state pulls"
THEORY = "Design: hardware/bus/kicad/rev-d/README.md; the bus: docs/manual/bus.md"
DATE = "2026-11-18"
REV = "D"
BUSREF = "J1"
POWER = ("+5V", "GND")
ROOT_NOTE = "Redrawn from the board netlist; proven pin for pin against it (gen_schematic.py)."
SHEETS = [
    ("slots", "Slots", "EIGHT 36-PIN SLOTS, EVERY POSITION BUSSED",
     [], (["J%d" % k for k in range(1, 9)], "top"),
     "Socket positions, counted from GND (Ken, 2026-11-18): 1-30 the 30-pin System-5 bus, GND at 1, the end pin, ... +5V at 30;\n"
     "31-36: -EF1, -EF2, -EF3, -DMAIN, SC0, -PAUSE. A 30-pin card plugs into positions 1-30, flush with the GND end."),
    ("pullups", "Pull-ups", "10K PULL-UPS: D0-D7 (RN1) AND THE OPEN-COLLECTOR LINES (RN2)", ["RN1", "RN2"], None,
     "RN1: an empty read gives FF. RN2: -EF, -EF1-3, -PAUSE, -DMAIN, -INT, -RESET (the CPU card also pulls up -INT and -RESET; these hold them with it out)."),
    ("power", "Power", "POWER IN, REVERSE PROTECTION, 5 V REGULATOR OR EXTERNAL 5 V, SOURCE JUMPER, SWITCH, BULK CAPACITORS, POWER LED",
     ["J9", "D2", "C10", "U1", "J10", "JP1", "SW1", "C1", "R1", "D1"], None,
     "J9: a 7-15 V adapter, centre positive (pin 1 the centre pin, pin 2 the sleeve). D2 SB540 Schottky: off if the plug\n"
     "is reversed. U1 TRACO TSR 3-2450N: 5 V at up to 3 A (92 %), C10 47 uF on its input. J10: an external regulated 5 V\n"
     "(pin 1 +5V, pin 2 GND; no protection: regulated 5 V only). JP1, one shunt: 1-2 REG (U1), 2-3 EXT (J10). SW1 power\n"
     "switch, either source: an M9040P toggle, as the IO panel's data switches (ON = common to pin 3; pin 1 open). C1 220 uF bulk on +5V (U1 takes up to 820 uF); C2-C9\n"
     "0.1 uF, one at each slot. No fuse."),
]
