# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-26 (Rev B); Rev B-Clean-Keyboard 2026-11-20
"""6845 video card Rev B-Clean-Keyboard (Rev B-Clean on the 36-pin bus with VIDEO-G TEXT's PS/2 keyboard section),
redrawn by tools/kicad/sch/gen_schematic.py from ../reports/netlist.net. Rev B-Clean's specification
(../../rev-b-clean/schematic/spec.py) with the register decoder on the decode sheet and two sheets for the keyboard.
Theory: docs/manual/video-6845-card.md; the keyboard section: ../README.md and ../gen/keyboard.py."""
PROJ = "video-6845-rev-b-clean-keyboard-schematic"
TITLE = "System-5 6845 video card Rev B-Clean-Keyboard"
SUBTITLE = "Text from BYTE May 1979 (video RAM at 7000, 6845 at 7800 / 7801, composite out) with a PS/2 keyboard: key at 7802, status at 7804"
THEORY = "Theory: docs/manual/video-6845-card.md; BYTE comparison: hardware/video-6845/BYTE-COMPARISON.md"
DATE = "2026-11-20"
REV = "B-Clean-Keyboard"
BUSREF = "J1"
SYMBOLS = {"IC8": "74xx:74LS161"}        # the 74LS163 pinout; KiCad's 74LS163 symbol hides VCC (an ERC complaint)
ROOT_NOTE = "Rev B-Clean (Rev B, Ken's working card, without the DB9) on the 36-pin bus, with VIDEO-G TEXT's PS/2 keyboard section, 2026-11-20: the 6845 at 7800 / 7801 only, the key at 7802, status at 7804. Redrawn from the board netlist and proven pin for pin against it (gen_schematic.py). IC8 must be a 74LS163."
RENAME = {
    "Net-(IC1-~{CER})": "~VRAM_CE", "Net-(IC1-~{OER})": "~MRD", "Net-(IC10-CLR)": "PULLUP", "Net-(IC12-A9)": "CG_A9",
    **{"Net-(IC10-Q%d)" % i: "CG_A%d" % (9 - i) for i in range(1, 7)},
    **{"Net-(IC11-%s)" % c: "CG_O%d" % (3 + k) for k, c in enumerate("DEFGH")},
    "Net-(IC11-QH)": "DOTS", "Net-(IC13A-I0)": "CURSOR", "Net-(IC13A-O)": "REVCUR", "Net-(IC9-D2)": "REVCUR1",
    "Net-(IC13B-I0)": "REVCUR2", "Net-(IC13B-O)": "VIDEO_X", "Net-(IC3-DE)": "DE", "Net-(IC9-D4)": "DE1",
    "Net-(IC5D-I1)": "DE2", "Net-(IC14A-I)": "~VIDEO", "Net-(IC14A-O)": "VIDEO_TTL", "Net-(IC14B-I)": "VSYNC",
    "Net-(IC14C-I)": "HSYNC", "Net-(IC14B-O)": "COMPOSITE", "Net-(IC2-ENC)": "TPA", "Net-(IC3-CS)": "~CRTC_CS",
    **{"Net-(IC4-A%d)" % i: "BLK%d" % i for i in range(4)}, "Net-(IC4-A=B_I)": "VMA", "Net-(IC4-A=B_O)": "BLOCK",
    "Net-(IC5B-I1)": "~ADDR11", "Net-(IC5C-I0)": "CC_QA", "Net-(IC6A-I)": "OSC_IN", "Net-(IC6A-O)": "OSC_A",
    "Net-(IC6B-O)": "OSC_B", "Net-(IC6F-I)": "~VMA",
}
SHEETS = [
    ("decode", "Decode", "BUS DECODE: A8-A15 LATCH, 4K BLOCK COMPARE (SV1), RAM AND CRTC SELECTS",
     ["IC2", "IC4", "SV1", "RN1", ("IC6", 5), ("IC6", 6), ("IC5", 1), ("IC5", 2), "IC15"], (["J1"], "left"),
     "IC2 latches A8-A15 while TPA is high. IC4 compares A12-A15 with SV1 (1-2: block 7) and matches only while -VMA is low\n"
     "(IC6F): BLOCK. Within the block A11 picks: A11 = 0 the video RAM's bus port (~VRAM_CE), A11 = 1 the registers (-UPPER,\n"
     "which was Rev B's 6845 select). IC15, enabled by -UPPER and A10 low, picks by A1-A2: Y0 the 6845 (-CRTCCS: 7800 address\n"
     "register, 7801 data; E = TPB, R/W = -MRW, RS = A0), Y1 the key (7802), Y2 status (7804); the same every 8 addresses to 7BFF."),
    ("vram", "VRAM+CRTC", "DUAL-PORT VIDEO RAM AND THE 6845",
     ["IC1", "IC3"], None,
     "The IDT7134's right port is the bus (A0-A10; its A11R is tied low, so the bus sees 2K), its left port the display:\n"
     "the 6845's refresh address MA0-MA11 (VADDR) reads a character onto VDATA0-7 with no arbitration and no snow.\n"
     "The 6845 also gives the row address (VROWS), HSYNC, VSYNC, display enable (DE) and the cursor."),
    ("clock", "Clocks", "DOT CLOCK AND CHARACTER CLOCK (DIVIDE BY 6)",
     ["Q1", ("IC6", 1), ("IC6", 2), ("IC6", 3), "R2", "R3", "IC8", ("IC5", 3)], None,
     "Q1 (9 MHz in BYTE) and three 74LS04 gates oscillate: DOTCLOCK. IC8 (74LS163: a synchronous clear) counts 0-5 and is\n"
     "cleared by the NAND of QA and QC: CHARCLOCK every 6 dots; QC (high for two dots) is the 6845's clock. A 74HC160, as the\n"
     "2005 drawing has it, clears at once and would divide by 5."),
    ("video", "Video", "CHARACTER LATCHES, CHARACTER GENERATOR, DOT SHIFTER, PIPELINE, REVERSE VIDEO, COMPOSITE OUT",
     ["IC10", "IC7", "IC12", "IC11", "IC13", "IC9", ("IC5", 4), "IC14", "R5", "R6", "J2"], None,
     "IC10 / IC7 latch the character (bits 0-6) onto the 2732's A3-A9; VROWS are A0-A2: the font is 128 x 8 at 000-3FF\n"
     "(goodfont). IC11 shifts out the five dots. Bit 7 XOR CURSOR (IC13A) is reverse video; IC9 delays it and DE by two\n"
     "characters; IC13B XORs it into the dots; IC5D blanks outside DE. IC14 (7416) mixes video and syncs for the RCA jack\n"
     "(composite). Rev B's DB9, which carried the same video and the two syncs separately, is not on this board."),
    ("kbdbus", "Keyboard bus", "THE KEYBOARD ON THE BUS: KEY LATCH (7802), STATUS (7804), KEY-READY, THE FLAG LINE",
     ["IC16", "IC17", "IC18", "IC19", "IC20", "IC22", "JP1", "R10", "R11"], None,
     "IC16: -RDKEY and -RDSTAT are the decoder's selects while -MRD is low; KRDT is -RDKEY while TPB is high. IC19, the key latch,\n"
     "drives D0-D7 while -RDKEY is low; IC20 puts the status on them while -RDSTAT is low: bit 0 KEY-READY, 2 VSYNC, 3 DE, 7 = 1.\n"
     "The ATmega's LDDATA edge loads IC19 and sets KEY-READY (IC18B); KCLR (IC17: KRDT, or -RESET) clears it: a read of the key,\n"
     "at TPB. IC22 (7416, open collector) pulls the bus flag line JP1 picks (-EF1, -EF2, -EF3 or -EF) low while KEY-READY, and\n"
     "the ATmega's reset (MRST) low while RESETH; R11 pulls -EF up."),
    ("kbdmcu", "Keyboard", "PS/2 KEYBOARD CONTROLLER (VIDEO-G TEXT'S, FIRMWARE embedded/video-g-ps2)",
     ["IC21", "Y1", "C25", "C26", "R7", "C24", "J3", "J4", "F1", "R8", "R9"], None,
     "The ATmega328P reads the PS/2 keyboard on J3 (clock and data pulled up by R8, R9; +5 V through F1) and puts each key's\n"
     "code on MD0-MD7. IC22 holds it in reset while the bus -RESET is low (MRST); R7 pulls its reset up, and C24 lets\n"
     "the FTDI cable on J4 reset it to load firmware. Y1: 16 MHz."),
    ("power", "Power", "POWER, DECOUPLING, LED", ["LED1", "R1", "R4"], None, "One 0.1 uF per IC; 10 uF bulk. LED1: power. R4 holds the latches' and counter's clears high."),
]
