# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-01
"""VIDEO-G 1.0 TEXT, redrawn by tools/kicad/sch/gen_schematic.py from ../reports/netlist.net.
Design: hardware/video-g/DESIGN.md."""
PROJ = "video-g-text-schematic"
TITLE = "System-5 VIDEO-G 1.0 TEXT"
SUBTITLE = "64 x 25 / 64 x 32 text (6845, IDT7134), status register, PS/2 keyboard, all memory-mapped; the GFX board on the J6 ribbon"
THEORY = "Design: hardware/video-g/DESIGN.md; board: ../video-g-text.kicad_pcb (generated from ../gen/netlist.py)"
DATE = "2026-11-17"
REV = "1.0"
BUSREF = "J1"
ROOT_NOTE = "Redrawn 2026-11-17 (memory-mapped) from the board netlist; proven pin for pin against it (gen_schematic.py)."
SHEETS = [
    ("decode", "Decode", "BUS: THE CARD'S BLOCK (7000-7FFF): TEXT RAM, REGISTERS, GFX WINDOW",
     ["IC1", "IC2", "SV1", "RN1", ("IC16", 4), ("IC17", 3), ("IC20", 4), ("IC18", 4), ("IC19", 4), "IC5", "IC6", "IC7",
      ("IC17", 2), "RN2"], (["J1"], "left"),
     "Memory-mapped, no I/O ports. IC1 latches A8-A15 while TPA is high; IC2 compares A12-A15 with the BLOCK jumper (1-2\n"
     "only = block 7) while -VMA is low -> BOARDSEL. A11 low: -TXTCE, the text RAM 7000-77FF (IC20D). A11 high: UPPER,\n"
     "7800-7FFF (IC18D); in it A10 high = WSEL, the GFX window 7C00-7FFF (IC19D), A10 low = the registers, from A1-A2\n"
     "(repeating to 7BFF): IC5 the 6845's -CS (7800/7801, RS = A0); IC6 reads while -MRD low (7800 6845, 7802 key, 7804\n"
     "status, 7806 mouse); IC7 writes while -MRW low and TPB high (7800 6845, 7804 control, 7806 Y). RN2: pull-ups."),
    ("crtc", "CRTC + RAM", "THE 6845 AT 7800/7801 AND THE IDT7134 TEXT RAM",
     ["IC3", "IC4", ("IC21", 3), ("IC24", 1)], None,
     "The IDT7134's right port is the bus (2K: A11R low), its left port the 6845's refresh address MA0-MA11: no snow.\n"
     "6845 (HD68B45, the 2 MHz grade): -CS from IC5, RS = A0. E = NAND(-RDCRTC, -WRCRTC) (IC21C): the whole -MRD time on\n"
     "a read, TPB within -MRW on a write. R/-W from IC24A: set while -MRD is low, cleared while -MRW is low, so it holds\n"
     "between cycles and never changes while E is high; a write latches as E falls."),
    ("clock", "Clock + pipeline", "12 MHz DOT CLOCK, CHARACTER COUNTER, CODE LATCH, CHARACTER ROM, SHIFTER",
     ["Y1", "R1", "R2", ("IC16", 1), ("IC16", 2), ("IC16", 3), ("IC16", 6), "IC15", "R3", ("IC20", 2), ("IC22", 4),
      "IC11", "IC12", "IC13", "IC14", ("IC22", 1), ("IC22", 2)], None,
     "IC15 counts 8-15 (8 dots): QC clocks the 6845, CHARCLOCK = NOT RCO loads the shifter and the latches. The code\n"
     "latch IC11 takes 7 bits of the IDT's left port: 28C64 A3-A9, A0-A2 = RA0-RA2. IC14 delays reverse/cursor (IC22A)\n"
     "and DE by two characters. For GFX: QCR = QC OR RCO (IC20B), WEPH = QA XOR QB (IC22D)."),
    ("video", "Video out", "THE TEXT / GRAPHICS COMBINE, THE SYNC BUFFERS, RCA AND DB9",
     [("IC19", 1), ("IC20", 1), ("IC21", 1), ("IC21", 2), ("IC19", 3), ("IC18", 1), ("IC17", 4), ("IC23", 1),
      ("IC23", 2), ("IC23", 3), "R4", "R5", "J2", "J3", "JP2"], None,
     "dot = (text AND TEXT-ON) OR GDOT, or their XOR when XORM (from GFX); gated by DE3. The syncs are buffered (IC19C,\n"
     "IC18A) so the cable never loads the 6845. RCA: composite through R4 / R5. DB9: TTL video, HSYNC, VSYNC +/- by JP2."),
    ("keyboard", "Keyboard + status", "PS/2 KEYBOARD (ATmega328P), KEY LATCH (7802) AND -EF, STATUS (7804)",
     ["IC10", "Y2", "C28", "C29", "R7", "R8", "R9", "R10", "F1", "J4", "J5", "C27", "IC9", ("IC24", 2), ("IC20", 3),
      ("IC19", 2), ("IC23", 4), "JP3", ("IC18", 2), ("IC23", 5), ("IC23", 6), "IC8", "JP1"], None,
     "The ATmega loads IC9 with LDDATA, which also sets KEY-READY (IC24B); a read of 7802 clears it at TPB (IC20C, IC19B).\n"
     "KEY-READY also pulls a bus flag line low through IC23D: JP3 KBD FLAG picks -EF1, -EF2, -EF3 or -EF (set to -EF: EF3\n"
     "through CPU Rev A's JP1). The VIDEO-G HBIOS polls KEY-READY at 7804, so either CPU card will do. The bus -RESET resets the ATmega through IC18B and IC23E/F. Status (IC8, read\n"
     "at 7804): KEY-READY, MOUSE-READY, VSYNC, DE, MONITOR (JP1), GFX-PRESENT, ID 10."),
    ("ribbon", "Ribbon to GFX", "J6: THE 40-PIN RIBBON TO THE GFX BOARD",
     ["J6", "R11", "R12", "R13", "RN3"], None,
     "Pin map: hardware/video-g/kicad/common/ribbon.py. The clocks leave through 33 ohm (R11-R13). With GFX absent RN2\n"
     "holds TEXT-ON high and RN3 holds GDOT, XORM, MOUSE-READY, GFX-PRESENT (and MONITOR, JP1 open) low."),
    ("power", "Power", "POWER, DECOUPLING, SPARE GATES, LED",
     ["LED1", "R6", "C26", ("IC16", 5), ("IC17", 1), ("IC17", 5), ("IC17", 6), ("IC18", 3), ("IC22", 3)], None,
     "One 0.1 uF (0.1 in leads) per IC, beside its socket; 47 uF bulk. LED1: power. Spare gate inputs to GND."),
]
