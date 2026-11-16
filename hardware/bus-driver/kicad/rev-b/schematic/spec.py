# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-26
"""Bus driver Rev B (BUSDRV-B), redrawn by tools/kicad/sch/gen_schematic.py from ../reports/netlist.net.
Theory: docs/manual/bus-driver-card.md."""
PROJ = "busdrv-b-schematic"
TITLE = "System-5 bus driver card Rev B (BUSDRV-B)"
SUBTITLE = "Arduino Nano + two MCP23017 expanders on the 30-pin bus: monitor, or bus master with the CPU card out"
THEORY = "Theory: docs/manual/bus-driver-card.md; firmware embedded/bus-driver; host tools software/busdrv"
DATE = "2026-10-26"
REV = "B"
BUSREF = "J1"
POWER = ("+5V", "GND")
ROOT_NOTE = "Redrawn 2026-10-26 from the board netlist; proven pin for pin against it (gen_schematic.py)."
SHEETS = [
    ("expanders", "Expanders", "TWO MCP23017 I/O EXPANDERS ON THE SYSTEM-5 BUS",
     ["U1", "U2"], (["J1"], "left"),
     "U1 (0x20): GPA0-6 = D0-D6, GPB0-6 = A0-A6. U2 (0x21): GPA0-6 = D7, A7, TPA, TPB, -MRD, -MRW, -VMA;\n"
     "GPB0-6 = Q, -RESET, -INT, -EF, N0-N2. GPA7/GPB7 are output-only: SPARE1-4. No buffers: a pin is an input (monitor)\n"
     "or drives the line; -RESET, -INT, -EF are only pulled low or released."),
    ("nano", "Nano", "ARDUINO NANO: I2C, EXPANDER RESET, BUS POWER SENSE, SPARE HEADER",
     ["A1", "R1", "R2", "R3", "R4", "R5", "J2"], None,
     "I2C on A4/A5 with 4.7k pull-ups to bus +5V (R1, R2). XRST (D4, R3 pull-up) holds the expanders reset while the bus\n"
     "has no power, sensed on A0 through R4/R5. D2/D3 take the expanders' INTA. J2: SPARE1-4, +5V, GND."),
    ("power", "Power", "POWER, DECOUPLING, LED", ["D1", "R6"], None, "C1, C2 0.1 uF at the expanders; C3 10 uF bulk. D1: bus power."),
]
