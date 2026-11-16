# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-26
"""The 2009 bus backplane, redrawn by tools/kicad/sch/gen_schematic.py from ../reports/netlist.net.
Theory: docs/manual/bus.md."""
PROJ = "bus-rev-2009-schematic"
TITLE = "System-5 bus backplane (2009)"
SUBTITLE = "Six 36-pin slots: the 30-pin System-5 bus with -EF1-3 above and -INP, -OUT, EXP below; power on X1"
THEORY = "The bus: docs/manual/bus.md; Eagle source: hardware/bus/eagle/rev-2009 (from Eagle's 2009 backups)"
DATE = "2026-10-26"
REV = "2009"
BUSREF = "U$1"
RENAME = {"5V": "VCC"}                    # the 2009 drawing names the supply net 5V; KiCad's power symbol is VCC
ROOT_NOTE = "Redrawn 2026-10-26 from the board netlist; proven pin for pin against it (gen_schematic.py)."
SHEETS = [
    ("slots", "Slots", "SIX 36-PIN SLOTS, EVERY PIN BUSSED (X1, THE POWER CONNECTOR, IS NOT WIRED)",
     [], (["U$1", "U$2", "U$3", "U$4", "U$5", "U$6", "X1"], "top"),
     "Every slot carries the same 36 lines, pin for pin: -EF1, -EF2, -EF3, then the 30-pin System-5 bus (VCC, D0-D7, Q,\n"
     "TPA, TPB, -MRD, -MRW, A0-A7, -INT, N2, -EF, -VMA, -RESET, N1, N0, GND), then -INP, -OUT and EXP. A 30-pin card\n"
     "plugs into the middle 30: pins 1-30 are the System-5 bus pin for pin, 31-33 = -EF1-3, 34-36 = -INP, -OUT, EXP.\n"
     "X1 (power) is on no net in the drawing; on the copper its pin 2 touches GND and pin 1 nothing (the +5V track stops short)."),
    ("power", "Power", "POWER", [], None, "VCC (the drawing's 5V) and GND: slot pins 1 and 30. X1: on the copper pin 2 touches GND, pin 1 nothing (the +5V track stops short of it)."),
]
