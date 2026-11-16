# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-01
"""VIDEO-G 1.0 TEXT, redrawn by tools/kicad/sch/gen_schematic.py from ../reports/netlist.net.
Design: hardware/video-g/DESIGN.md."""
PROJ = "video-g-text-schematic"
TITLE = "System-5 VIDEO-G 1.0 TEXT"
SUBTITLE = "64 x 25 / 64 x 32 text (6845, IDT7134), status port, PS/2 keyboard; the GFX board on the J6 ribbon"
THEORY = "Design: hardware/video-g/DESIGN.md; board: ../video-g-text.kicad_pcb (generated from ../gen/netlist.py)"
DATE = "2026-11-01"
REV = "1.0"
BUSREF = "J1"
ROOT_NOTE = "Redrawn 2026-11-01 from the board netlist; proven pin for pin against it (gen_schematic.py)."
SHEETS = [
    ("decode", "Decode", "BUS: MEMORY DECODE (7000-7FFF), PORT DECODE, IOCYC",
     ["IC1", "IC2", "SV1", "RN1", ("IC16", 4), ("IC17", 3), ("IC20", 4), ("IC18", 4), "IC5", "IC6", "IC7",
      ("IC16", 5), ("IC17", 1), ("IC17", 2), ("IC24", 1), "RN2"], (["J1"], "left"),
     "IC1 latches A8-A15 while TPA is high; IC2 compares A12-A15 with the BLOCK jumper (1-2 only = block 7) while -VMA is\n"
     "low -> BOARDSEL. A11 low: -TXTCE (the text RAM, 7000-77FF); A11 high: GSEL (the GFX window, 7800-7FFF).\n"
     "IC5 decodes N0-N2 always (Y0 = no port: IOCYC's D); IOCYC (IC24A) = N != 0 sampled as TPA falls. IC6: read enables\n"
     "(IOCYC and -MRD high = INP); IC7: write strobes (TPB and -MRD low = OUT). RN2 pulls up -EF, -VMA, -RESET."),
    ("crtc", "CRTC + RAM", "THE 6845 ON PORTS 5 / 6 AND THE IDT7134 TEXT RAM",
     ["IC3", "IC4", ("IC18", 3), ("IC21", 3)], None,
     "The IDT7134's right port is the bus (2K: A11R low), its left port the 6845's refresh address MA0-MA11: no snow.\n"
     "6845: -CS = port 5 or 6 (IC18C), RS = N1 (5 = address, 6 = data), R/-W = -MRD, E = NAND(-RD6, -WR5, -WR6) (IC21C):\n"
     "the whole INP 6 from 2 T, or TPB in an OUT; it latches as E falls with R/-W still low."),
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
    ("keyboard", "Keyboard + status", "PS/2 KEYBOARD (ATmega328P), KEY LATCH (INP 1) AND -EF, STATUS (INP 4)",
     ["IC10", "Y2", "C28", "C29", "R7", "R8", "R9", "R10", "F1", "J4", "J5", "C27", "IC9", ("IC24", 2), ("IC20", 3),
      ("IC19", 2), ("IC23", 4), "JP3", ("IC18", 2), ("IC23", 5), ("IC23", 6), "IC8", "JP1"], None,
     "The ATmega loads IC9 with LDDATA, which also sets KEY-READY (IC24B); INP 1 clears it at TPB (IC20C, IC19B).\n"
     "KEY-READY pulls the bus -EF low through IC23D and JP3 (CPU JP1 row 3 = EF3: HBIOS unchanged). The bus -RESET resets\n"
     "the ATmega through IC18B and IC23E/F. INP 4: KEY-READY, MOUSE-READY, VSYNC, DE, MONITOR (JP1), GFX-PRESENT, ID 10."),
    ("ribbon", "Ribbon to GFX", "J6: THE 40-PIN RIBBON TO THE GFX BOARD",
     ["J6", "R11", "R12", "R13", "RN3"], None,
     "Pin map: hardware/video-g/kicad/common/ribbon.py. The clocks leave through 33 ohm (R11-R13). With GFX absent RN2\n"
     "holds TEXT-ON high and RN3 holds GDOT, XORM, MOUSE-READY, GFX-PRESENT (and MONITOR, JP1 open) low."),
    ("power", "Power", "POWER, DECOUPLING, SPARE GATES, LED",
     ["LED1", "R6", "C26", ("IC17", 5), ("IC17", 6), ("IC19", 4), ("IC22", 3)], None,
     "One 0.1 uF (0.1 in leads) per IC, beside its socket; 47 uF bulk. LED1: power. Spare gate inputs to GND."),
]
