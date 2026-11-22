# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-30
"""CPU Rev D, redrawn by tools/kicad/sch/gen_schematic.py from ../reports/netlist.net. Design: ../DESIGN.md."""
PROJ = "cpu-rev-d-schematic"
TITLE = "System-5 CPU card Rev D"
SUBTITLE = "CDP1802 at 2 MHz, reset/run and LOAD control, 2732 boot EPROM at F000, debug header; the 36-pin bus"
THEORY = "Design: hardware/cpu/kicad/rev-d/DESIGN.md; the bus: docs/manual/bus.md (the 36-pin extension)"
DATE = "2026-11-21"
REV = "D"
BUSREF = "J1"
POWER = ("+5V", "GND")
ROOT_NOTE = "Redrawn from the board netlist; proven pin for pin against it (gen_schematic.py)."
VALUES = {"U2": "74HCT373", "U4": "74HCT74", "U5": "74HCT00", "U6": "74HCT20", "U7": "74HCT14", "U8": "74HCT74", "U9": "74HCT14"}
SHEETS = [
    ("cpu", "CPU", "THE CDP1802 AND THE 36-PIN BUS",
     ["U1"], (["J1"], "left"),
     "U1's signals go to the bus unbuffered (D0-D7, A0-A7, TPA, TPB, -MRD, -MRW, Q, N0-N2), as on Rev A.\n"
     "Bus positions, counted from GND (1): 31-33 -EF1..-EF3, 34 -DMAIN, 35 SC0, 36 -PAUSE (the 36-pin extension)."),
    ("clock", "Clock", "4 MHz OSCILLATOR / 2, OR AN EXTERNAL CLOCK; THE DEBUG HEADER",
     ["X1", ("U4", 1), "JP1", ("U7", 1), "R2", "J2", ("U9", 4), ("U9", 5)], None,
     "X1 4 MHz; U4A divides it by 2: CLK_INT 2 MHz. JP1 picks INT or EXT for the 1802's CLOCK. EXT_CLK comes in on J2\n"
     "(a jumper wire from a debug board), held low by R2, through a Schmitt inverter (U7A). J2 also brings out CLOCK,\n"
     "SC0 and SC1; U9D/U9E buffer SC0 onto the bus (position 36): low = an instruction fetch."),
    ("control", "Control", "RESET, RUN, PAUSE, LOAD: DS1813, RESET/RUN SWITCH, CLEAR/WAIT/DMA-IN BUFFERS, LOADED",
     ["U10", "SW1", "D1", "R1", "C12", ("U7", 2), ("U7", 3), ("U7", 4), ("U7", 5), ("U7", 6), ("U9", 1), ("U9", 2),
      ("U9", 3), ("U8", 1), ("U5", 4), "RN1", "LED3", "R5", "LED4", "R6", "LED6", "R8"], None,
     "CLEAR = -RESET, WAIT = -PAUSE, DMA_IN = -DMAIN, each through two Schmitt inverters: reset, run, pause (-PAUSE low)\n"
     "and load (both low) follow directly. U10 DS1813: power-on reset and switch debounce on the open-collector -RESET\n"
     "(no watchdog). SW1 RESET grounds SW_RST: -RESET through D1, and LOADED (U8A) cleared. LOAD mode sets LOADED;\n"
     "LED6 RAM (on U8A's Q through R8) is lit while it is set: the next RUN starts in RAM at 0000, not in the EPROM."),
    ("boot", "Boot", "A8-A15 LATCH, 2732 BOOT EPROM AT F000, BOOT MAP AND -VMA",
     ["U2", "U3", ("U4", 2), ("U6", 1), ("U5", 1), ("U5", 2), ("U5", 3), "LED5", "R7"], None,
     "U2 latches A8-A15 while TPA is high. After a reset the boot map puts the EPROM at every address (-VMA high) until\n"
     "the first access with A15 high (U4B), unless LOADED is set. Then the EPROM answers only at F000-FFFF (U6A: WIN_L);\n"
     "-VMA = BOOTMAP + WIN (U5B), the EPROM's CE = ROM_SEL_L (U5C)."),
    ("flags", "Flags", "EF ROUTING, INTERRUPT, Q LED",
     ["JP2", "JP3", "JP4", "JP5", "RN2", ("U9", 6), "LED2", "R4"], None,
     "JP2-JP5: one block per EF input (EF1-EF4); its rows are the bus flag lines -EF1, -EF2, -EF3, -EF, and a jumper\n"
     "across a row puts that line on the input (any input from any line). RN2 holds an unjumpered input high (off)."),
    ("power", "Power", "POWER, DECOUPLING, POWER LED", ["LED1", "R3", "C1"], None,
     "One 0.1 uF (0.1\" leads) per chip; C1 10 uF bulk. LED1: power."),
]
