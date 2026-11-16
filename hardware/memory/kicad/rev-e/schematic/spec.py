# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-26
"""Memory card Rev E (MEM3-E; the circuit of Rev D), redrawn by tools/kicad/sch/gen_schematic.py from ../reports/netlist.net.
Theory: docs/manual/memory-card.md."""
PROJ = "memory-rev-e-schematic"
TITLE = "System-5 memory card Rev E (MEM3-E)"
SUBTITLE = "32K RAM + 32K EPROM, every 4K block jumpered to the RAM, the EPROM or neither"
THEORY = "Theory of operation: docs/manual/memory-card.md; board: ../memory-rev-e.kicad_pcb (unchanged)"
DATE = "2026-10-26"
REV = "E"
BUSREF = "U$1"
ROOT_NOTE = "Redrawn 2026-10-26 from the board netlist; proven pin for pin against it (gen_schematic.py). Fit 74HCT151 muxes."
RENAME = {
    "Net-(IC7A-I)": "A0", "Net-(IC7B-I)": "A1", "Net-(IC7C-I)": "A2", "Net-(IC7D-I)": "A3", "Net-(IC7E-I)": "A4",
    "Net-(IC7F-I)": "A5", "Net-(IC8A-I)": "A6", "Net-(IC8B-I)": "A7", "Net-(IC8C-I)": "~MRD", "Net-(IC8D-I)": "~MRW",
    "Net-(IC6-CLK)": "TPA", "Net-(IC14A-I0)": "~VMA", "Net-(IC14B-I1)": "~BUFFADDR15", "Net-(IC14A-O)": "~LO_BANK",
    "Net-(IC12A-I1)": "~HI_BANK", "Net-(IC14C-I0)": "RAM_LO_Y", "Net-(IC12A-I0)": "RAM_HI_Y",
    "Net-(IC14D-I0)": "EPROM_LO_Y", "Net-(IC12B-I0)": "EPROM_HI_Y",
    **{"Net-(IC2-D%d)" % i: "RAM_LO_J%d" % i for i in range(8)}, **{"Net-(IC4-D%d)" % i: "RAM_HI_J%d" % i for i in range(8)},
    **{"Net-(IC15-D%d)" % i: "EPROM_LO_J%d" % i for i in range(8)}, **{"Net-(IC13-D%d)" % i: "EPROM_HI_J%d" % i for i in range(8)},
}
def chip(key, name, what, mux, hdr, rn, gate, led, r, note):
    return (key, name, "%s: 74HCT151 BLOCK SELECT, JUMPERS, GATED !CE AND LED" % what,
            [mux, hdr, rn, gate, led, r], None, note)


SHEETS = [
    ("address", "Address", "BUS BUFFERS, THE A8-A15 LATCHES AND THE BANK SELECTS",
     ["IC7", "IC8", "IC6", "IC9", ("IC14", 1), ("IC14", 2)], (["U$1"], "left"),
     "CD4050B buffers (IC7, IC8) put one CMOS input on A0-A7, -MRD and -MRW. The CD4042B latches (IC6, IC9; clock = TPA,\n"
     "POL high) are transparent while TPA is high and hold when it falls: they capture A8-A15 from the buffered A0-A7.\n"
     "Bank selects (IC14A, IC14B): ~LO_BANK = -VMA OR A15, ~HI_BANK = -VMA OR /A15: low for a valid address in that half."),
    chip("ramlo", "RAM lo", "RAM 0000-7FFF (IC1)", "IC2", "SV2", "RN1", ("IC14", 3), "LED2", "R2",
         "SV2 is the LO jumper field: its odd pins are IC2's eight block inputs (0000 ... 7000), pulled high by RN1; its even\n"
         "pins are GND. A jumper from GND to a RAM pin gives that 4K block to the RAM. A12-A14 pick the input; !CE = Y OR\n"
         "~LO_BANK (IC14C): low only for a valid address in a jumpered block. LED2 sinks into it: lit while IC1 is enabled."),
    chip("ramhi", "RAM hi", "RAM 8000-FFFF (IC11)", "IC4", "SV1", "RN3", ("IC12", 1), "LED3", "R3",
         "SV1 is the HI jumper field (8000 ... F000), as SV2. !CE = Y OR ~HI_BANK (IC12A). LED3: IC11 enabled."),
    chip("epromlo", "EPROM lo", "EPROM 0000-7FFF (IC3)", "IC15", "SV3", "RN2", ("IC14", 4), "LED4", "R4",
         "SV3 is the ROM row of the LO field: a jumper from it to the GND row (SV2's even pins) gives the block to the EPROM.\n"
         "One jumper per column, so a block is never both. !CE = Y OR ~LO_BANK (IC14D). LED4: IC3 enabled."),
    chip("epromhi", "EPROM hi", "EPROM 8000-FFFF (IC5)", "IC13", "SV4", "RN4", ("IC12", 2), "LED5", "R5",
         "SV4: the ROM row of the HI field. !CE = Y OR ~HI_BANK (IC12B). LED5: IC5 enabled."),
    ("chips", "Memory", "THE MEMORY CHIPS: 62256 RAM AND 27256 EPROM, LOWER AND UPPER 32K",
     ["IC1", "IC3", "IC11", "IC5"], None,
     "IC1 / IC3: RAM / EPROM in 0000-7FFF; IC11 / IC5: in 8000-FFFF. A0-A14 from the buffers and latches, data straight to\n"
     "the bus, buffered -MRD on every !OE, buffered -MRW on the RAMs' !WE. EPROM VPP on VCC."),
    ("power", "Power", "POWER, DECOUPLING, LED", ["LED1", "R1"], None, "One 0.1 uF per IC; 10 uF bulk. LED1: power."),
]
