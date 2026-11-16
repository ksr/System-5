# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-26
"""S5BUS-D: the System-5 backplane, a fresh design (2026-10-26). The circuit is defined once here; make_schematic.py and
make_board.py both use it.

Derived from the cards that plug in (all six agree on the 30-pin pinout: docs/manual/bus.md) and from the board Ken built
in 2009 (hardware/bus/kicad/rev-2009: six 36-pin slots on a 1.0" pitch). Ken's choices (2026-10-26): 36-pin slots, 8
slots, a screw terminal + power LED + bulk and per-slot bypass capacitors (no regulator), 10k pull-ups on D0-D7 and on
the open-collector lines -EF, -EF1-3, -PAUSE, -DMAIN (and -INT, -RESET: Ken 2026-10-31, after a floating -RESET held the
6845 in reset with the CPU card out); 10k pull-downs on N0-N2, TPA, TPB and pull-ups on -VMA, -MRD, -MRW (Ken,
2026-11-01: every enabling line idles off with no master on the bus); mounting holes, four along each long edge.
After the 2026-10-27 reviews (Ken): J9 -> SW1 -> F1 -> Q1 -> +5V. SW1 a power switch, an E-Switch 100-series
right-angle SPDT toggle rated 5 A at 28 VDC; F1 a 4 A resettable fuse (polyfuse); Q1 a P-channel MOSFET for
reverse-polarity protection (drain to the supply, source to the cards, gate to GND through R2: a supply wired
backwards leaves Q1 off and its body diode reverse-biased, so nothing negative reaches the cards); C1 in the common
6.3 mm can.

Slot pins are numbered by POSITION along the 36-pin socket (KiCad's PinSocket_1x36), not by Eagle's 2009 numbers:
  positions 1-3   -EF1, -EF2, -EF3    (the outer end; -EF3 next to +5V, as both the 2005 and 2009 silkscreens say;
                                      the 2009 copper wired them in the opposite order)
  positions 4-33  System-5 bus pins 1-30, in order (+5V at position 4, GND at 33): a 30-pin card plugs into these
  positions 34-36 -PAUSE, -DMAIN, SC0 (the 36-pin extension, docs/manual/bus.md; Ken 2026-10-30: the 2009 drawing named them
                  -INP, -OUT, EXP, unused until then)
"""
BUS = {1: "+5V", 2: "D0", 3: "D1", 4: "D2", 5: "D3", 6: "D4", 7: "D5", 8: "D6", 9: "D7", 10: "Q", 11: "TPA", 12: "TPB",
       13: "-MRD", 14: "-MRW", 15: "A0", 16: "A1", 17: "A2", 18: "A3", 19: "A4", 20: "A5", 21: "A6", 22: "A7", 23: "-INT",
       24: "N2", 25: "-EF", 26: "-VMA", 27: "-RESET", 28: "N1", 29: "N0", 30: "GND"}
POS = ["-EF1", "-EF2", "-EF3"] + [BUS[i] for i in range(1, 31)] + ["-PAUSE", "-DMAIN", "SC0"]      # slot position 1..36
NSLOTS = 8
R = "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal"

PARTS = {}      # ref: (lib_id, value, footprint, {pin: net})
for k in range(1, NSLOTS + 1):
    PARTS["J%d" % k] = ("Connector_Generic:Conn_01x36", "SLOT %d" % k,
                        "Connector_PinSocket_2.54mm:PinSocket_1x36_P2.54mm_Vertical", {i + 1: n for i, n in enumerate(POS)})
    PARTS["C%d" % (k + 1)] = ("Device:C", "0.1uF", "s5bus:C025-050X050", {1: "+5V", 2: "GND"})       # one per slot
PARTS.update({
    "J9": ("Connector:Screw_Terminal_01x02", "POWER IN", "TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal",
           {1: "+5V_IN", 2: "GND"}),
    "SW1": ("Switch:SW_SPDT", "POWER", "s5bus:SW_Toggle_SPDT_E-Switch_100_M6", {2: "+5V_IN", 3: "+5V_SW"}),  # 2 common; 1 open
    "F1": ("Device:Polyfuse", "4A", "Fuse:Fuse_Bourns_MF-RHT400", {1: "+5V_SW", 2: "+5V_FUSED"}),  # 4 A hold, 7.5 A trip
    "Q1": ("Transistor_FET:IRF9540N", "IPP80P03P4L-04", "Package_TO_SOT_THT:TO-220-3_Horizontal_TabDown",   # 1 G, 2 D, 3 S
           {1: "Q1_GATE", 2: "+5V_FUSED", 3: "+5V"}),
    "R2": ("Device:R", "10k", R, {1: "Q1_GATE", 2: "GND"}),
    "C1": ("Device:C_Polarized", "220uF 16V", "Capacitor_THT:CP_Radial_D6.3mm_P2.50mm", {1: "+5V", 2: "GND"}),
    "R1": ("Device:R", "470", R, {1: "+5V", 2: "LED_PWR"}),
    "D1": ("Device:LED", "PWR", "LED_THT:LED_D5.0mm", {1: "GND", 2: "LED_PWR"}),          # LED: 1 = K, 2 = A
    "RN1": ("Device:R_Network08", "10k", "Resistor_THT:R_Array_SIP9",
            {1: "+5V", 2: "D0", 3: "D1", 4: "D2", 5: "D3", 6: "D4", 7: "D5", 8: "D6", 9: "D7"}),
    "RN2": ("Device:R_Network08", "10k", "Resistor_THT:R_Array_SIP9",
            {1: "+5V", 2: "-EF", 3: "-EF1", 4: "-EF2", 5: "-EF3", 6: "-PAUSE", 7: "-DMAIN", 8: "-INT", 9: "-RESET"}),
    # idle states when no master drives the bus (Ken, 2026-11-01): N = 0 (no I/O port), TPA/TPB low, and the strobes
    # and -VMA high, so no card drives the data lines or writes memory
    "RN3": ("Device:R_Network05", "10k", "Resistor_THT:R_Array_SIP6",
            {1: "GND", 2: "N0", 3: "N1", 4: "N2", 5: "TPA", 6: "TPB"}),
    "RN4": ("Device:R_Network03", "10k", "Resistor_THT:R_Array_SIP4",
            {1: "+5V", 2: "-VMA", 3: "-MRD", 4: "-MRW"}),
}
)
# parts drawn with a stand-in library symbol: the real part's data sheet and description, so the BOM names the right one
DOCS = {"Q1": ("https://www.infineon.com/dgdl/Infineon-I80P03P4L_04-DS-v01_01-en.pdf?fileId=db3a30431ddc9372011e07e95eb827d7",
               "IPP80P03P4L-04: P-channel MOSFET, -30 V, -80 A, RDS(on) under 7 mOhm at VGS -4.5 V, TO-220 (drawn with the IRF9540N symbol: same pinout)")}

for k in range(1, 9):
    PARTS["H%d" % k] = ("Mechanical:MountingHole", "M3", "MountingHole:MountingHole_3.2mm_M3", {})
