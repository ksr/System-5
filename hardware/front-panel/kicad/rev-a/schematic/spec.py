# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-22
"""Front panel Rev A, redrawn by tools/kicad/sch/gen_schematic.py from ../reports/netlist.net. Design: ../DESIGN.md."""
PROJ = "front-panel-rev-a-schematic"
TITLE = "System-5 front panel Rev A"
SUBTITLE = ("The hand controls and displays on a board that mounts as the front of a case: six TIL311s, bit and status "
            "LEDs, data toggles, RUN, LOAD, INPUT, and a RESET button that boots the EPROM; a 50-way ribbon to the IO "
            "panel card")
THEORY = "Design: hardware/front-panel/kicad/rev-a/DESIGN.md; the ribbon: tools/s5panel.py; a boot reset: docs/manual/bus.md"
DATE = "2026-11-22"
REV = "A"
BUSREF = "J1"
POWER = ("+5V", "GND")
ROOT_NOTE = "Redrawn from the board netlist; proven pin for pin against it (gen_schematic.py)."
VALUES = {"U7": "74HCT14", "U8": "74HCT10", "U9": "74HCT74", "U10": "74HC03"}
SHEETS = [
    ("displays", "Displays", "THE BUS ADDRESS AND THE OUTPUT PORT: SIX TIL311S AND EIGHT LEDS",
     ["U1", "U2", "U3", "U4", "U5", "U6", "RN1"] + ["LED%d" % k for k in range(1, 9)], (["J1"], "left"),
     "J1 is the ribbon from the IO panel card's J3, pin n to pin n. U1-U4 show ADR15-ADR0, the bus address as that card's\n"
     "two 74HCT573s hold it; U5 / U6 and LED1-LED8 (through RN1, 1k x8) show OUT7-OUT0, its output port (TIL311 strobe\n"
     "low = transparent, blanking low = on)."),
    ("controls", "Controls", "DATA TOGGLES, INPUT, RUN AND LOAD, AND THE RESET BUTTON'S BOOT RESET",
     ["SW%d" % k for k in range(1, 9)] + ["RN2", "SW11", "SW9", "SW10", "SW12", "R7", "C1", ("U7", 4), ("U7", 2), ("U7", 5),
                                           ("U10", 1), ("U10", 2)], None,
     "SW1-SW8 switch SW0-SW7 to +5V through RN2 (1k) or leave them open (the IO card's RN3 pulls them down). SW11 INPUT\n"
     "grounds INPUT_L (the IO card debounces it). SW9 RUN/RESET grounds -RESET, SW10 LOAD grounds -PAUSE: the bus lines,\n"
     "open collector. SW12 RESET, debounced by R7 / C1 and U7D: U10A and U10B (74HC03, open drain) pull -RESET and -DMAIN\n"
     "low together, a boot reset: the CPU card clears LOADED and the machine starts in the EPROM. Not while -PAUSE is low\n"
     "(PAUSE_N): -DMAIN low in LOAD mode would be a DMA request."),
    ("status", "Status", "SIX STATUS LEDS, AND THE COPY OF THE CPU CARD'S LOADED FLAG",
     ["LED9", "R1", "LED10", "R2", "LED11", "R3", "LED12", "R4", "LED13", "R5", "LED14", "R6", ("U7", 1), ("U7", 3),
      ("U7", 6), ("U8", 1), ("U8", 2), ("U9", 1)], None,
     "Each LED from +5V through 1k, sunk by its line: PWR to ground; Q and ROM by the IO card (Q_LED_L, ROM_LED_L); PAUSE\n"
     "and RESET by PAUSE_N (U7E) and RESET_N (U7F), low while the bus line is; START FROM RAM by !Q of U9A, a copy of the CPU card's LOADED\n"
     "flag made from the same bus lines by the same gates: set by LOAD mode (LOAD_L, U8A), cleared by a boot reset\n"
     "(BOOT_L = NAND(RESET_H, DMAIN_H, PAUSE_N), U8B). The CPU card's power-on reset is a boot reset: the two agree."),
    ("power", "Power", "POWER, DECOUPLING, MOUNTING HOLES", ["C2", "H1", "H2", "H3", "H4"], None,
     "+5V on four of the ribbon's wires and ground on eight. One 0.1 uF (0.1\" leads) per chip; C2 47 uF. Spare gate\n"
     "inputs to GND. Four M3 holes."),
]
