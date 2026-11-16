# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-26
"""The IDE/CF card Rev A, redrawn: what tools/kicad/sch/gen_schematic.py needs beyond the board netlist.
Theory: docs/manual/ide-cf-card.md. The parts and every connection come from ../reports/netlist.net."""
PROJ = "ide-cf-rev-a-schematic"
TITLE = "System-5 IDE/CF card Rev A"
SUBTITLE = "Mike Riley's 8-bit IDE interface with port-select jumpers: register select OUT 2, data port 3 (SV1/SV2)"
THEORY = "Theory of operation: docs/manual/ide-cf-card.md; board: ../ide-cf-rev-a.kicad_pcb (unchanged)"
DATE = "2026-10-26"
REV = "A"
BUSREF = "U$1"
SYMBOLS = {"JP1": "system5:IDE40"}
ROOT_NOTE = "Redrawn 2026-10-26 from the board netlist; proven pin for pin against it (gen_schematic.py)."

# the unnamed nets, by what they do (the 2005 names kept for the rest)
RENAME = {
    "Net-(IC1A-I)": "NOIO",          # 74LS138 Y0: N = 0, no I/O instruction
    "Net-(IC1A-O)": "IOCYC",
    "Net-(IC1D-O)": "~TPA",
    "Net-(IC1C-O)": "~TPB",
    "Net-(IC1B-O)": "REGLATCH",      # opens the 74LS75 on OUT to the select port
    "Net-(IC1B-I)": "~REGLATCH",
    "Net-(IC6B-O)": "~DIOW",
    "Net-(IC6C-O)": "~DIOR",
    "Net-(IC7-Q1)": "DA0",
    "Net-(IC7-Q2)": "DA1",
    "Net-(IC7-Q3)": "DA2",
    "Net-(IC7-Q4)": "CS0",
    "Net-(IC7-~{Q4})": "CS1",
    "Net-(U$1--RESET)": "~RESET",
}

# (key, sheet name, title, parts drawn wired, (parts drawn label-style, where) or None, note)
SHEETS = [
    ("decode", "Decode", "BUS, I/O DECODE AND THE STROBE WINDOW",
     ["IC4", ("IC1", 1), ("IC1", 3), ("IC1", 4), ("IC1", 5), ("IC1", 6), "IC2", "IC3", "IC5", "SV1", "SV2"], (["U$1"], "left"),
     "U$1: the System-5 bus (only D0-D7, -MRD, TPA, TPB, N0-N2 and -RESET are used). IC4 decodes N0-N2 into PORT1-7\n"
     "(Y0 = no I/O). -MRD tells OUT (low) from INP (high); the NAND latch IC2 makes the strobe window from TPA and TPB.\n"
     "SV1 picks the register-select port (IDESEL: port 2 on Ken's card), SV2 the data port (IDERW: port 3)."),
    ("ide", "IDE", "REGISTER LATCH, READ/WRITE STROBES AND THE 40-PIN IDE HEADER",
     [("IC1", 2), "IC6", "IC7", "JP1", "R13", "R14", "JP2"], None,
     "OUT to IDESEL opens the 74LS75 (IC7): D0-D2 = DA0-DA2, D3 = CS0 (0) or CS1 (1, the control block).\n"
     "IDERW with OUT = -DIOW, with INP = -DIOR (IC6, pulled up by R13/R14). D0-D7 go straight to the drive's DD0-DD7:\n"
     "8-bit mode only (the BIOS sends SET FEATURES 01). The bus -RESET resets the drive (pin 1)."),
    ("power", "Power", "POWER, DECOUPLING, LED", ["LED1", "R1"], None,
     "One 0.1 uF per IC; C8 bulk. LED1: power."),
]
