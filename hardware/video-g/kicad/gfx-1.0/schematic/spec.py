# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-01
"""VIDEO-G 1.0 GFX, redrawn by tools/kicad/sch/gen_schematic.py from ../reports/netlist.net.
Design: hardware/video-g/DESIGN.md."""
PROJ = "video-g-gfx-schematic"
TITLE = "System-5 VIDEO-G 1.0 GFX"
SUBTITLE = "512 x 200 / 512 x 256 graphics in two pages, Y register (7806), control register (7804), PS/2 mouse (7806); needs TEXT"
THEORY = "Design: hardware/video-g/DESIGN.md; board: ../video-g-gfx.kicad_pcb (generated from ../gen/netlist.py)"
DATE = "2026-11-17"
REV = "1.0"
BUSREF = "J1"
ROOT_NOTE = "Redrawn 2026-11-17 (memory-mapped; power LED) from the board netlist; proven pin for pin against it (gen_schematic.py)."
SHEETS = [
    ("cpu", "CPU side", "THE WINDOW: READ LATCH, WRITE BUFFER, WRITE REQUEST; THE Y AND CONTROL REGISTERS",
     ["IC6", "IC7", "IC10", "IC19", ("IC13", 1), ("IC14", 2), ("IC14", 3), ("IC16", 1), ("IC16", 2), ("IC17", 1),
      ("IC17", 2), ("IC14", 5)], (["J1"], "left"),
     "Memory-mapped; every decode is on TEXT (on the ribbon: WSEL = the window 7C00-7FFF, -WRY = a write to 7806,\n"
     "-WRCTL = a write to 7804, -RDMOUSE = a read of 7806). Reads: IC6 loads the CPU-half byte on each QC rise and drives\n"
     "D0-D7 while WSEL AND -MRD low (IC17B). Writes: WRQ (IC13A) = WSEL AND -MRW low (IC16A) at CHARCLOCK;\n"
     "-WE = NAND(WRQ, NMUX, WEPH, GWR) (IC17A) = counts 9-10, IC7 drives the RAM only then; RAM -OE off in that half.\n"
     "IC10: the Y register (7806). IC19: the control register (7804): TEXT-OFF (TEXT-ON to TEXT), GFX-ON, XOR, DPAGE,\n"
     "CPAGE, MOUSE-ON."),
    ("ram", "Graphics RAM", "THE 62256 AND ITS ADDRESS MULTIPLEXERS",
     ["IC1", "IC2", "IC3", "IC4", "IC5", "RN1", ("IC14", 1)], None,
     "Display: {DPAGE, RA2-RA0, MA10-MA0}; CPU: {CPAGE, Y2-Y0, Y7-Y3, A5-A0} - the same layout, so pixel line y, byte\n"
     "x/8 is wiring. NMUX = NOT(QC OR RCO) (IC14A): CPU in counts 8-11, display in 12-15. RN1 holds the data bus."),
    ("display", "Display", "DISPLAY LATCH, DOT SHIFTER, THE GFX-ON GATE",
     ["IC8", "IC9", ("IC16", 4)], None,
     "IC8 latches the display-half byte at CHARCLOCK, IC9 shifts it out at the dot clock (bit 7 = leftmost), IC16D\n"
     "passes the dots only while GFX-ON: GDOT to TEXT, two characters behind like the text dots."),
    ("mouse", "Mouse", "PS/2 MOUSE (ATmega328P), MOUSE LATCH (READ AT 7806), MOUSE-READY",
     ["IC11", "Y1", "C23", "C24", "R1", "R2", "R3", "R4", "R5", "R6", "F1", "J2", "J3", "C21", "IC12", ("IC13", 2),
      ("IC14", 4), ("IC18", 1), ("IC16", 3), ("IC15", 1), ("IC15", 2)], None,
     "The keyboard firmware in mouse mode (PD7 low through R6). It loads IC12 with LDDATA, which sets MOUSE-READY (IC13B);\n"
     "a read of 7806 (-RDMOUSE) clears it at TPB (IC18A, IC16C). It reports only while MOUSE-ON. The bus -RESET resets it through IC15A/B."),
    ("ribbon", "Ribbon from TEXT", "J4: THE 40-PIN RIBBON FROM THE TEXT BOARD", ["J4"], None,
     "Pin map: hardware/video-g/kicad/common/ribbon.py; GFX-PRESENT (pin 36) is tied high here."),
    ("power", "Power", "POWER, DECOUPLING, SPARE GATES",
     ["C22", "LED1", "R7", ("IC14", 6), ("IC15", 3), ("IC15", 4), ("IC15", 5), ("IC15", 6), ("IC18", 2), ("IC18", 3), ("IC18", 4)], None,
     "One 0.1 uF (0.1 in leads) per IC, beside its socket; 47 uF bulk. LED1: power, as on TEXT. Spare gate inputs to GND."),
]
