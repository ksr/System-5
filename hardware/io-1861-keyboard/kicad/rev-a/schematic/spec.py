# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-26
"""The IO card (1861 + keyboard) Rev A, redrawn by tools/kicad/sch/gen_schematic.py from ../reports/netlist.net.
Theory: docs/manual/io-card.md."""
PROJ = "io-1861-keyboard-rev-a-schematic"
TITLE = "System-5 IO card Rev A (1861 video + PS/2 keyboard)"
SUBTITLE = "PS/2 keyboard via PAK-VI and PIC16F84 into a CDP1852 input port; CDP1861 graphics (unused on Ken's card)"
THEORY = "Theory of operation: docs/manual/io-card.md; board: ../io-1861-keyboard-rev-a.kicad_pcb (unchanged)"
DATE = "2026-10-26"
REV = "A"
BUSREF = "U$2"
ROOT_NOTE = "Redrawn 2026-10-26 from the board netlist; proven pin for pin against it (gen_schematic.py)."
RENAME = {
    "Net-(IC11A-I)": "NOIO", "Net-(IC11A-O)": "IOCYC", "Net-(IC11D-O)": "~TPA", "Net-(IC11C-O)": "~TPB",
    "Net-(IC11F-I)": "~KBDSEL", "Net-(IC11F-O)": "KBDSEL", "Net-(U$1-SR)": "~KBD_SR", "Net-(U$2--EF4)": "~EF",
    "Net-(IC1-RA0)": "PAK_TX", "Net-(IC1-RA1)": "PIC_LED", "Net-(IC1-RA2)": "KBD_STROBE",
    "Net-(IC1-OSC1)": "PIC_OSC1", "Net-(IC1-OSC2)": "PIC_OSC2", "Net-(U$5-RES1)": "PAK_RES1", "Net-(U$5-RES2)": "PAK_RES2",
    "Net-(U$5-DA)": "PAK_DA", "Net-(IC16A-I1)": "~PIXSEL", "Net-(IC16A-O)": "DISPON", "Net-(IC16B-O)": "DISPOFF",
    "Net-(IC2A-~{Q})": "~DISPLAY_ON", "Net-(U$3-SYNC)": "SYNC", "Net-(U$3-VIDEO)": "VIDEO", "Net-(R13-Pad1)": "COMPOSITE",
}
SHEETS = [
    ("decode", "Decode", "BUS, I/O DECODE AND THE STROBE WINDOW",
     ["IC12", ("IC11", 1), ("IC11", 3), ("IC11", 4), ("IC11", 5), "IC13", "IC14", "IC15", "SV2", "SV6"], (["U$2"], "left"),
     "U$2: the System-5 bus. IC12 decodes N0-N2 into PORT1-7 (Y0 = no I/O); -MRD tells OUT (low) from INP (high); the\n"
     "NAND latch IC14 makes the strobe window from TPA and TPB (the same circuit as the IDE card). SV2 picks the keyboard\n"
     "port (Ken's: port 1), SV6 the 1861's (Ken's: none)."),
    ("keyboard", "Keyboard", "PS/2 KEYBOARD: PAK-VI DECODER, PIC16F84 SERIAL TO PARALLEL, CDP1852 INPUT PORT",
     ["X1", "U$5", "U$6", "IC1", "Q1", "C1", "C2", ("IC11", 6), "U$1", "SV1", "LED2", "R3", "LED3", "R2", "LED5", "R5"], None,
     "The PAK-VI turns PS/2 key codes into ASCII on a serial line; the PIC (its code: pic-ps2-firmware/) puts each byte on\n"
     "RB0-7 and strobes the CDP1852's CLK. SR (character waiting) lights LED2 and, with SV1 on 2-3, drives the bus -EF\n"
     "(CPU JP1: EF3). INP on the keyboard port: CS1 = the port, CS2 = -MRD high; the 1852 drives the data bus."),
    ("pixie", "1861", "CDP1861 GRAPHICS: DISPLAY ON/OFF, DMA, COMPOSITE VIDEO, RIBBON TO THE CPU CARD",
     ["U$3", "IC16", "IC2", "LED4", "R4", "U$4", "R13", "R14", "R15", "SV3"], None,
     "The 1861 needs the CPU clock (LCLK), SC0/SC1, DMA OUT and its EF line: they come over the SV3 ribbon from the CPU card.\n"
     "With a port on SV6, INP = DISPLAY ON, OUT = DISPLAY OFF (IC16); IC2 remembers it for LED4. -INT goes to the bus.\n"
     "VIDEO and SYNC mix through R13/R14/R15 to the RCA jack. Not used on Ken's card (SV6 empty)."),
    ("power", "Power", "POWER, DECOUPLING, LED", ["LED1", "R1"], None, "One 0.1 uF per IC; bulk capacitor. LED1: power."),
]
