# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-26
"""S5BUS-D: the System-5 backplane, a fresh design (2026-10-26). The circuit is defined once here; make_schematic.py and
make_board.py both use it.

Derived from the cards that plug in (all six agree on the 30-pin pinout: docs/manual/bus.md) and from the board Ken built
in 2009 (hardware/bus/kicad/rev-2009: six 36-pin slots on a 1.0" pitch). Ken's choices (2026-10-26): 36-pin slots, 8
slots, a power LED + bulk and per-slot bypass capacitors, 10k pull-ups on D0-D7 and on
the open-collector lines -EF, -EF1-3, -PAUSE, -DMAIN (and -INT, -RESET: Ken 2026-10-31, after a floating -RESET held the
6845 in reset with the CPU card out); 10k pull-downs on N0-N2, TPA, TPB and pull-ups on -VMA, -MRD, -MRW (Ken,
2026-11-01: every enabling line idles off with no master on the bus); mounting holes, four along each long edge.
Power (Ken, 2026-11-18, in place of the 2026-10-27 screw terminal, polyfuse and P-MOSFET): J9, a centre-positive
barrel jack for any 7-15 V adapter -> D2, a 5 A Schottky (a reversed plug leaves it off, so nothing reaches the cards)
-> U1, a TRACO TSR 3-2450N switching regulator (5 V at 3 A from 6.5-36 V, 92 %, a 7805-pinout SIP-3). No fuse (the
regulator limits its output current and recovers by itself from a short). C10 47 uF on the regulator's input side.
Or an external regulated 5 V supply on J10, two screw terminals (Ken, 2026-11-18). JP1, one 3-pin jumper, picks the
source: REG (U1's output) or EXT (J10) onto 5V_SEL; one shunt cannot tie the two supplies together (Ken's choice). SW1,
the power switch (an M9040P, the upright Marquardt SPDT toggle of the IO panel's data switches: Ken, 2026-11-18; that
day first a 9070-1W, and until then an E-Switch 100 series, 5 A at 28 VDC), then switches 5V_SEL onto the bus +5V,
whichever source is picked (Ken's choice). C1 220 uF bulk and the PWR LED on the switched +5V (the regulator takes up to
820 uF of load capacitance; eight cards add about 100 uF).

Slot pins are numbered by POSITION along the 36-pin socket, counted from the GND end (the socket itself is an
unnumbered strip: the numbers are these drawings'). Since 2026-11-18 (Ken: "looking at the bus from the power supply end
I want the right most pin to be gnd followed by the next original pin order all the way to +5v/vcc, then EF1, EF2, EF3,
-DMAin, SC0", -PAUSE kept, at the far end; and "start counting at gnd as pin 1, there +5v is 30 and then the pins beyond
5v") the 30-pin bus ends flush at the slot's GND end, and the six extension lines all lie beyond +5V:
  positions 1-30  the System-5 bus from its GND end: GND 1, N0 2, N1 3, -RESET 4 ... D0 29, +5V 30, so the 30-pin bus's
                  own pin n (+5V 1 ... GND 30, as every 30-pin card's connector is numbered) is position 31 - n. A
                  30-pin card plugs into these, flush with the GND end (the rightmost, seen from the power connector)
  positions 31-36 -EF1, -EF2, -EF3, -DMAIN, SC0, -PAUSE  (-EF1 next to +5V, -PAUSE at the far end)
Until then the slot was counted from the other end with the 30-pin bus in the middle, as on the 2009 board: 1-3 -EF1,
-EF2, -EF3, 4-33 the bus (+5V at 4, GND at 33), 34-36 -PAUSE, -DMAIN, SC0 (the 2009 board's -INP, -OUT, EXP, unused); so
a 36-pin card made since does not fit the 2009 backplane (its +5V would meet D2 there).
"""
BUS = {1: "+5V", 2: "D0", 3: "D1", 4: "D2", 5: "D3", 6: "D4", 7: "D5", 8: "D6", 9: "D7", 10: "Q", 11: "TPA", 12: "TPB",
       13: "-MRD", 14: "-MRW", 15: "A0", 16: "A1", 17: "A2", 18: "A3", 19: "A4", 20: "A5", 21: "A6", 22: "A7", 23: "-INT",
       24: "N2", 25: "-EF", 26: "-VMA", 27: "-RESET", 28: "N1", 29: "N0", 30: "GND"}
POS = [BUS[i] for i in range(30, 0, -1)] + ["-EF1", "-EF2", "-EF3", "-DMAIN", "SC0", "-PAUSE"]      # slot position 1..36, from GND
NSLOTS = 8
R = "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal"

PARTS = {}      # ref: (lib_id, value, footprint, {pin: net})
for k in range(1, NSLOTS + 1):
    PARTS["J%d" % k] = ("Connector_Generic:Conn_01x36", "SLOT %d" % k,
                        "Connector_PinSocket_2.54mm:PinSocket_1x36_P2.54mm_Vertical", {i + 1: n for i, n in enumerate(POS)})
    PARTS["C%d" % (k + 1)] = ("Device:C", "0.1uF", "s5bus:C025-050X050", {1: "+5V", 2: "GND"})       # one per slot
PARTS.update({
    # 1 = the centre pin (+), 2 = the sleeve; MP = the jack's two kinked support legs, soldered to GND
    "J9": ("Connector:Barrel_Jack_MountingPin", "POWER IN", "Connector_BarrelJack:BarrelJack_CUI_PJ-063AH_Horizontal",
           {1: "VIN", 2: "GND", "MP": "GND"}),
    "D2": ("Device:D_Schottky", "SB540", "Diode_THT:D_DO-201AD_P15.24mm_Horizontal", {1: "VIN_D", 2: "VIN"}),  # 1 K, 2 A
    "C10": ("Device:C_Polarized", "47uF 35V", "Capacitor_THT:CP_Radial_D6.3mm_P2.50mm", {1: "VIN_D", 2: "GND"}),
    "U1": ("Converter_DCDC:TSR3-2450N", "TSR 3-2450N", "Converter_DCDC:Converter_DCDC_TRACO_TSR2-24xxN_TSR2-24xxxN_THT",
           {1: "VIN_D", 2: "GND", 3: "5V_REG"}),                                                     # 1 Vin, 2 GND, 3 Vout
    # an external regulated 5 V on two screw terminals, and the source jumper: 1 REG, 2 the switch's common, 3 EXT
    "J10": ("Connector:Screw_Terminal_01x02", "EXT 5V", "TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal",
            {1: "5V_EXT", 2: "GND"}),
    "JP1": ("Connector_Generic:Conn_01x03", "5V SOURCE", "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical",
            {1: "5V_REG", 2: "5V_SEL", 3: "5V_EXT"}),
    # an M9040P, the upright Marquardt toggle of the IO panel's data switches (Ken, 2026-11-18: "bus change on off switch
    # to same toggle used on IO card data 1-8"; that day first a 9070-1W, YACC1's RESET/RUN toggle; before, an E-Switch 100)
    "SW1": ("Switch:SW_SPDT", "POWER", "s5bus:M9040P", {2: "5V_SEL", 3: "+5V"}),   # 2 common; 1 open
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
# the real parts' data sheets and descriptions, so the schematic and the BOM name them
DOCS = {"J9": ("https://www.sameskydevices.com/product/resource/pj-063ah.pdf",
               "PJ-063AH (Same Sky, formerly CUI): DC power jack, right angle, 2.0 mm centre pin for 5.5 x 2.1 mm plugs, 8 A, 24 V; centre positive here"),
        "D2": ("https://www.vishay.com/docs/88721/sb520.pdf",
               "SB540-E3/54 (Vishay): Schottky rectifier, 40 V, 5 A, DO-201AD; in series with the supply so a reversed plug reaches nothing"),
        "U1": ("https://www.tracopower.com/tsr3n-datasheet",
               "TRACO TSR 3-2450N: switching regulator (buck), 5 V 3 A from 6.5-36 V, 92 %, SIP-3 with a 7805's pinout; at most 820 uF on its output")}

for k in range(1, 9):
    PARTS["H%d" % k] = ("Mechanical:MountingHole", "M3", "MountingHole:MountingHole_3.2mm_M3", {})
