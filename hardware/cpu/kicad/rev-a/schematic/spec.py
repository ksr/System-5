# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-26
"""The CPU card Rev A, redrawn by tools/kicad/sch/gen_schematic.py from ../reports/netlist.net (the card AS DRAWN in
2005: the rework is in ../../../eagle/rev-a/rework/README.md). Theory: docs/manual/cpu-card.md."""
PROJ = "cpu-rev-a-schematic"
TITLE = "System-5 CPU card Rev A (as drawn)"
SUBTITLE = "CDP1802, clock, reset/run control, A8-A15 latch, 4K boot EPROM with remap, -VMA, EF routing"
THEORY = "Theory: docs/manual/cpu-card.md; the built card's rework: hardware/cpu/eagle/rev-a/rework/README.md"
DATE = "2026-10-26"
REV = "A"
BUSREF = "U$2"
ROOT_NOTE = ("Redrawn 2026-10-26 from the board netlist; proven pin for pin against it (gen_schematic.py).\n"
             "This is the card as DRAWN. As built: IC1 is a 74LS374, and IC8B (the boot flip-flop) is reworked:\n"
             "PRE = D = VCC, CLK = ADDR15 (hardware/cpu/eagle/rev-a/rework/README.md).")
RENAME = {
    "Net-(IC2-~{CE})": "~ROMCE", "Net-(IC5A-~{Q})": "~RUNPULSE", "Net-(IC7A-I0)": "OSC_IN", "Net-(IC7A-O)": "OSC_A",
    "Net-(IC7C-I0)": "OSC_XTAL", "Net-(IC7B-O)": "OSC_OUT", "Net-(IC7D-I0)": "~ROMWIN", "Net-(IC7D-I1)": "BOOT_Q",
    "Net-(IC7D-O)": "~REMAP", "Net-(IC8A-Q)": "CPUCLOCK", "Net-(IC8B-~{Q})": "~BOOT_Q", "Net-(IC9-G1)": "BANK_G1",
    "Net-(IC9-G2A)": "BANK_G2A", "Net-(S1-S1)": "~PBRST", "Net-(IC3A-I3)": "WAIT_FB", "Net-(IC4A-I3)": "CLEAR_FB",
    "Net-(IC5A-C)": "RUN_C", "Net-(IC5A-R{slash}C)": "RUN_RC", "Net-(U$1-N0)": "N0", "Net-(U$1-N1)": "N1", "Net-(U$1-N2)": "N2",
    **{"Net-(IC9-Y%d)" % i: "BANK%d" % i for i in range(8)},
}
SHEETS = [
    ("cpu", "CPU", "THE CDP1802 AND ITS CLOCK",
     ["U$1", "Q1", ("IC7", 1), ("IC7", 2), ("IC7", 3), ("IC8", 1), "R8", "R9", "R10", "C2"], (["U$2"], "left"),
     "U$2: the System-5 bus; the 1802's signals go to it unbuffered. Q1 with three NANDs of IC7 is the oscillator; IC8A\n"
     "divides it by 2 for the 1802's CLOCK, and its other output is LCLK for the 1861 (ribbon SV3)."),
    ("control", "Control", "RESET AND RUN CONTROL: CM1232, RUN ONE-SHOT, WAIT/CLEAR LATCHES, FRONT PANEL HEADER",
     ["U1", "S1", "SV1", "R6", "IC5", "C1", "R5", ("IC6", 1), "IC3", "IC4", "R1", "R2", "R3", "R4", "SV6",
      "LED2", "R18", "LED3", "R17"], None,
     "U1 holds -RESET low after power-up and for the S1 / SV1 push-button. When it lets go, the 74LS123 (IC5) fires a pulse\n"
     "on -RUN (open collector, IC6A). IC3 and IC4 (74LS20) are set/reset latches on WAIT and CLEAR, set and cleared by the\n"
     "open-collector command lines -RESET, -RUN, -PAUSE, -LOAD (10k pull-ups); the front panel header SV6 shares them."),
    ("boot", "Boot", "A8-A15 LATCH, BOOT EPROM, 4K WINDOW, BOOT FLIP-FLOP AND -VMA",
     ["IC1", "IC2", "IC9", "SV2", "SV4", ("IC8", 2), ("IC7", 4), "SV5", ("IC6", 2), "R13", ("IC6", 4), "LED5", "R16"], None,
     "IC1 latches A8-A15 on TPA (a 74LS374 on the built card). IC9 decodes A12-A14 into eight 4K banks, A15 enabling it\n"
     "through SV2 (H/L); SV4 picks the EPROM's bank (bank 7: F000). IC8B, cleared by -RESET, ends the boot map; SV5 picks\n"
     "Boot only / Boot+REMAP / No ROM. IC7D and IC6 (open collector) make -VMA and the EPROM's -CE (R13 pull-up)."),
    ("flags", "Flags", "EF ROUTING (JP1-JP4), THE 1861 RIBBON, INTERRUPT, DMA, Q LED",
     ["JP1", "JP2", "JP3", "JP4", "SV3", "R7", "R11", "R12", ("IC6", 6), "LED4", "R15"], None,
     "JP1 routes the bus -EF line, JP2 the front panel's flag (FEF), JP3 the 1861's (VEF), JP4 the keyboard's over the\n"
     "ribbon (KEF) to one of EF1-EF4 (Ken's card: JP1 row 3, bus -EF -> EF3). SV3 carries SC0, SC1, DMA OUT, LCLK, KEF\n"
     "and VEF to the IO card. -INT, DMA IN and DMA OUT have pull-ups."),
    ("power", "Power", "POWER, DECOUPLING, LED", ["LED1", "R14"], None, "One 0.1 uF per IC. LED1: power."),
]
