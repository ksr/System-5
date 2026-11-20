# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-26 (Rev B); Rev B-Clean 2026-11-20
"""6845 video card Rev B-Clean (Rev B, Ken's working card, without the DB9), redrawn by
tools/kicad/sch/gen_schematic.py from ../reports/netlist.net. Rev B's specification (../../rev-b/schematic/spec.py)
with the connectors under their new names (J1 the bus, J2 the RCA jack), X1 gone and IC3's pin 3 on ground.
Theory: docs/manual/video-6845-card.md; against BYTE: ../../../BYTE-COMPARISON.md."""
PROJ = "video-6845-rev-b-clean-schematic"
TITLE = "System-5 6845 video card Rev B-Clean"
SUBTITLE = "64 x 16 text from BYTE May 1979: dual-port IDT7134 video RAM at 7000, HD6845 CRTC at 7800, composite out"
THEORY = "Theory: docs/manual/video-6845-card.md; BYTE comparison: hardware/video-6845/BYTE-COMPARISON.md"
DATE = "2026-11-20"
REV = "B-Clean"
BUSREF = "J1"
SYMBOLS = {"IC8": "74xx:74LS161"}        # the 74LS163 pinout; KiCad's 74LS163 symbol hides VCC (an ERC complaint)
ROOT_NOTE = "Rev B (Ken's working card) without the DB9 and with the 6845's light-pen input (pin 3) tied to ground, 2026-11-20. Redrawn from the board netlist and proven pin for pin against it (gen_schematic.py). IC8 must be a 74LS163."
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
     ["IC2", "IC4", "SV1", "RN1", ("IC6", 5), ("IC6", 6), ("IC5", 1), ("IC5", 2)], (["J1"], "left"),
     "IC2 latches A8-A15 while TPA is high. IC4 compares A12-A15 with SV1 (1-2: block 7) and matches only while -VMA is low\n"
     "(IC6F): BLOCK. Within the block A11 picks the device: A11 = 0 enables the video RAM's bus port (~VRAM_CE),\n"
     "A11 = 1 the 6845 (~CRTC_CS). E = TPB, R/W = -MRW, RS = A0: 7800 address register, 7801 data, repeated."),
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
    ("power", "Power", "POWER, DECOUPLING, LED", ["LED1", "R1", "R4"], None, "One 0.1 uF per IC; 10 uF bulk. LED1: power. R4 holds the latches' and counter's clears high."),
]
