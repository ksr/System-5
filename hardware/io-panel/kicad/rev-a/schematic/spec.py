# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-30 (ports and INPUT's EF line on jumpers, the RTC: 2026-11-18;
# the serial port: 2026-11-20)
"""IO panel card Rev A, redrawn by tools/kicad/sch/gen_schematic.py from ../reports/netlist.net. Design: ../DESIGN.md."""
PROJ = "io-panel-rev-a-schematic"
TITLE = "System-5 IO panel card Rev A"
SUBTITLE = ("The front panel: LEDs, TIL311s and switches on jumper-picked ports; the bus address on four TIL311s; INPUT "
            "on a jumper-picked EF line; ELF-style RUN and LOAD with DMA loading; a DS12885 real-time clock; a 16C550 "
            "serial port; 36-pin bus")
THEORY = "Design: hardware/io-panel/kicad/rev-a/DESIGN.md; the bus: docs/manual/bus.md (the 36-pin extension)"
DATE = "2026-11-20"
REV = "A"
BUSREF = "J1"
POWER = ("+5V", "GND")
ROOT_NOTE = "Redrawn from the board netlist; proven pin for pin against it (gen_schematic.py)."
VALUES = {"U1": "74HCT138", "U2": "74HCT374", "U3": "74HCT244", "U4": "74HCT14", "U5": "74HCT10", "U6": "74HCT00",
          "U9": "74HC05", "U10": "74HCT74", "U11": "74HCT74", "U12": "74HCT02", "U13": "DS12885+", "U18": "74HCT573",
          "U19": "74HCT573", "U20": "16C550", "U21": "MAX232", "U22": "74HCT573", "X1": "1.8432MHz"}
SHEETS = [
    ("decode", "Decode", "PORT DECODE: THE IN AND OUT PORTS ON JUMPERS, AND THE STROBES",
     ["U1", "JP1", "JP2", "RN1", ("U4", 2), ("U4", 3), ("U5", 1), ("U6", 1), ("U6", 2)], (["J1"], "left"),
     "U1 decodes N0-N2: Y1_L-Y7_L, each low through an INP n / OUT n, to JP1 (IN port) and JP2 (OUT port); a jumper across\n"
     "row n picks port n (Ken, 2026-11-18; set to 4), and RN1 holds the selects off with no jumper. OUT: OUTCLK =\n"
     "NAND(OUT port, -MRD low, TPB) (U5A) clocks the 74HCT374 as TPB ends. INP, or this card's DMA: the 74HCT244 drives\n"
     "the bus while -MRD is high (U6A, U6B)."),
    ("output", "Output", "THE OUT PORT: LATCH, EIGHT LEDS, TWO TIL311 HEX DISPLAYS",
     ["U2", "U7", "U8"] + ["LED%d" % k for k in range(1, 9)] + ["RN2"], None,
     "U2 latches the OUT byte. The LEDs show it bit by bit (sourced through RN2, 1k x 8), U7 shows bits 7-4 and U8 bits 3-0 in\n"
     "hex (TIL311 strobe low = transparent, blanking low = on). TIL311 pinout as on Ken's YACC1 IO card."),
    ("address", "Address", "THE BUS ADDRESS ON FOUR TIL311 HEX DISPLAYS",
     ["U18", "U19", "U14", "U15", "U16", "U17"], None,
     "The 1802 puts the high address byte on A0-A7 during TPA, then the low byte. U18 (74HCT573, LE = TPA) holds the high\n"
     "byte as TPA falls, U19 (LE = TPB) the low byte as TPB falls; U14-U17 show A15-A0 (strobe low = transparent). The\n"
     "display holds the last cycle's address while the clock is stopped; in LOAD mode it shows R0, where the next byte goes.\n"
     "The latches keep the bus to HCT inputs (Ken, 2026-11-18)."),
    ("input", "Input", "THE IN PORT (AND LOAD DATA): EIGHT TOGGLE SWITCHES",
     ["U3"] + ["SW%d" % k for k in range(1, 9)], None,
     "Eight SPDT toggles SW1-SW8 (as on the YACC1 IO card): common = the bit, +5V = 1, GND = 0. U3 puts them on D0-D7 for an\n"
     "INP of the IN port and, in LOAD mode, for this card's own DMA IN."),
    ("control", "Control", "INPUT BUTTON ON A JUMPER-PICKED EF LINE, RUN AND LOAD, ONE DMA IN PER PRESS, Q LED",
     ["SW9", "R1", "C1", ("U4", 1), ("U4", 4), ("U4", 5), ("U4", 6), ("U6", 3), "SW10", "SW11", "U10", ("U11", 1),
      ("U9", 1), ("U9", 2), "JP3", ("U5", 2), "LED9", "R2"], None,
     "INPUT (SW9, R1/C1 + Schmitt) drives EFOUT (open collector, U9A) to JP3: a jumper across a row puts it on -EF1, -EF2,\n"
     "-EF3 or -EF (set to -EF1); RN1 holds EFOUT high with no jumper. SW10 RUN/RESET grounds -RESET, SW11 LOAD grounds\n"
     "-PAUSE: both = LOAD mode (LOAD_H). In LOAD mode a press sets REQ (U10A: -DMAIN); the write's -MWR rise sets ACK (U10B),\n"
     "which clears REQ until the button is let go. DRIVE (U11A) keeps the switches on the bus until -MRD falls. The Q LED\n"
     "sinks into U5B = NAND(Q, 1, 1), push-pull."),
    ("rtc", "Real-time clock", "DS12885 CLOCK, CALENDAR AND NVRAM ON A JUMPER-PICKED PORT PAIR",
     ["U13", "Y1", "BT1", "JP4", "JP5", ("U6", 4), ("U12", 1), ("U12", 2), ("U12", 3), ("U12", 4), ("U5", 3)], None,
     "U13 DS12885+ (Ken, 2026-11-18): Intel timing (MOT low), RESET high, CS = SEL_UART (low: the clock is the chip the\n"
     "address port's byte picked; sheet Serial port); Y1 32.768 kHz, 6 pF; BT1 a CR2032 in a\n"
     "flat holder, on VBAT. JP4 picks the ports: address on 2, 4 or 6, data on 3, 5 or 7 (set to 6/7); its last row puts IRQ\n"
     "on -INT (off). OSTB_L = NAND(MRD_H, TPB) (U6D): TPB of a read. OUT address: AS = NOR(select, OSTB_L) (U12A); OUT\n"
     "data: R/W = NOT NOR(select, OSTB_L) (U12B, U12C); INP data: DS = NOT NOR(select, MRD_H) (U12D, U5C). RN1 pulls the\n"
     "selects and IRQ up. JP5: a shunt grounds RCLR, which clears the 114 bytes of RAM (not the clock) while the chip runs\n"
     "from its battery, the power off; open, nothing changes (RCLR has its own pull-up: no outside one)."),
    ("serial", "Serial port", "16C550 UART ON THE CLOCK'S PORT PAIR, MAX232, DE-9",
     ["U22", "U20", "X1", ("U11", 2), ("U9", 3), "JP7", "U21", "C22", "C23", "C24", "C25", "JP6", "J2"], None,
     "U20 16C550 (Ken, 2026-11-20; as on his YACC1 I/O card): X1 1.8432 MHz on XIN, -BAUDOUT to RCLK, MR = RESET_H, the\n"
     "modem inputs tied off. It shares the clock's ports (JP4): U22 (LE = RTC_AS) holds the byte written to the address\n"
     "port: bit 7 = SEL_UART (1: the UART, CS0; 0: the DS12885, its CS), bits 2-0 = the UART's register. WR = RTC_WR, high in\n"
     "TPB of an OUT to the data port. -RD = UART_RD_L from U11B, preset by -MWR low (only an INP has it) and held clear while\n"
     "RTC_RD is low: the 1802 puts N out 1.5 clocks before -MRD falls in an OUT, so RTC_RD pulses at the start of every\n"
     "OUT to the data port, and a 16550 read there would throw a received character away. INTR through U9C (open\n"
     "collector, RN1) and JP7 to -INT (off). U21 MAX232 with four 1 uF; JP6 swaps the DE-9's pins 2 and 3 (1-3 and 2-4:\n"
     "the card sends on pin 2); J2's shell to GND."),
    ("power", "Power", "POWER, DECOUPLING, POWER LED", ["LED10", "R3", "C2"], None,
     "One 0.1 uF (0.1\" leads) per chip; C2 10 uF. Spare gate inputs to GND."),
]
