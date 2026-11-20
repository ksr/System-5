# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-18 (from BUSDRV-B's)
"""Bus driver Rev C (BUSDRV-C), redrawn by tools/kicad/sch/gen_schematic.py from ../reports/netlist.net. Design: ../DESIGN.md."""
PROJ = "busdrv-c-schematic"
TITLE = "System-5 bus driver card Rev C (BUSDRV-C)"
SUBTITLE = ("Arduino Nano + three MCP23017 expanders on all 36 bus positions: monitor, bus master, LOAD mode by the "
            "clock; CLK OUT, probes, the DEBUG cable to CPU Rev D")
THEORY = "Design: hardware/bus-driver/kicad/rev-c/DESIGN.md; BUSDRV-B: docs/manual/bus-driver-card.md; the bus: docs/manual/bus.md"
DATE = "2026-11-18"
REV = "C"
BUSREF = "J1"
POWER = ("+5V", "GND")
ROOT_NOTE = "Redrawn from the board netlist; proven pin for pin against it (gen_schematic.py)."
SHEETS = [
    ("expanders", "Expanders", "THREE MCP23017 I/O EXPANDERS ON THE 36-PIN BUS",
     ["U1", "U2", "U3"], (["J1"], "left"),
     "U1 (0x20) and U2 (0x21) as on BUSDRV-B: D0-D7, A0-A7, TPA, TPB, -MRD, -MRW, -VMA, Q, -RESET, -INT, -EF, N0-N2.\n"
     "U3 (0x22): GPA0-5 = -EF1, -EF2, -EF3, -PAUSE, -DMAIN, SC0 (read only); GPB0-2 = the DEBUG cable's CLOCK, SC0, SC1.\n"
     "No buffers: a pin is an input (monitor) or drives the line; the open-collector lines are only pulled low or let go.\n"
     "GPA7/GPB7 are output-only: SPARE1-4, SPARE10-11."),
    ("nano", "Nano", "ARDUINO NANO: I2C, EXPANDER RESET, BUS SENSE, CLOCK OUT, PROBES, HEADERS",
     ["U4", "R1", "R2", "R3", "R4", "R5", "R7", "R8", "R9", "J2", "J3", "J4"], None,
     "I2C on A4/A5 with 4.7k pull-ups to bus +5V (R1, R2). XRST (D4, R3) holds the expanders reset until the bus has\n"
     "power, sensed on A0 through R4/R5. D2, D3, D5 take the expanders' INTA. CLK OUT: Timer 1 (D9) through R7, on J2\n"
     "and on J4 DEBUG, cabled to CPU Rev D's J2 (EXT CLK, GND, CLOCK, SC0, SC1, GND). PROBE1 (D8, input capture) and\n"
     "PROBE2 (A1) through 1k. J2: CLK OUT, the probes, SPARE1-4, +5V, GND; J3: SPARE5-11, GND."),
    ("power", "Power", "POWER, DECOUPLING, POWER LED", ["LED1", "R6", "C4"], None,
     "C1-C3 0.1 uF (0.1\" leads) at the expanders; C4 10 uF bulk. The Nano runs from its USB, the rest from the bus."),
]
