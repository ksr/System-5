# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-18 (from BUSDRV-B's gen/netlist.py and the IO panel's)
"""BUSDRV-C: the System-5 bus driver card for the 36-pin bus (design notes: ../DESIGN.md; BUSDRV-B, the 30-pin card it
grows from: ../../rev-b). The circuit is defined once here; make_schematic.py and make_board.py use it.

An Arduino Nano (USB serial console) drives three MCP23017 I2C expanders whose pins go straight onto all 36 positions
of the bus Rev D's slots (34 signals; +5V and GND are power). U1 and U2 are BUSDRV-B's, pin for pin, so its firmware,
fwsim.py and backplane.py stay valid; U3 (0x22) takes the 36-pin extension: -EF1..-EF3, -PAUSE, -DMAIN (driven low or
let float, open collector, as BUSDRV-B does -RESET, -INT and -EF) and SC0 (read only). MCP23017 GPA7/GPB7 are output-
only on current silicon, so they carry spare outputs; every bus signal sits on a bidirectional pin.

LOAD mode by the clock (option B, Ken 2026-11-17): the Nano's Timer 1 output (D9) is CLK OUT, through R7, on J2 and on
the DEBUG header J4, cabled to CPU Rev D's J2 (a keyed 2x3 with the same six signals in the same order, Ken 2026-11-18:
EXT CLK, GND, CLOCK, SC0, SC1, GND), the CPU card's JP1 on EXT; J4's CLOCK, SC0 and SC1 come back to U3's spare pins.
Probes: PROBE1 through R8 to D8 (Timer 1's input capture), PROBE2 through R9 to A1 (pin change), both on J2.
Power: the Nano runs from its USB; the expanders, I2C pull-ups and reset pull-up from bus +5V, so a powered-down
System-5 is never fed from USB. A0 senses bus +5V (R4 10k / R5 100k) so the firmware knows when the bus is up; D4 holds
the expanders in reset (XRST) until it is.
"""
BUS = {1: "+5V", 2: "D0", 3: "D1", 4: "D2", 5: "D3", 6: "D4", 7: "D5", 8: "D6", 9: "D7", 10: "Q", 11: "TPA", 12: "TPB",
       13: "-MRD", 14: "-MRW", 15: "A0", 16: "A1", 17: "A2", 18: "A3", 19: "A4", 20: "A5", 21: "A6", 22: "A7", 23: "-INT",
       24: "N2", 25: "-EF", 26: "-VMA", 27: "-RESET", 28: "N1", 29: "N0", 30: "GND"}
POS = [BUS[i] for i in range(30, 0, -1)] + ["-EF1", "-EF2", "-EF3", "-DMAIN", "SC0", "-PAUSE"]   # position 1..36, counted from GND
# (Ken, 2026-11-18: GND 1 ... +5V 30, then -EF1 31, -EF2 32, -EF3 33, -DMAIN 34, SC0 35, -PAUSE 36; bus pin n = position 31 - n)


def mcp(gpa, gpb, addr, inta):
    """MCP23017 (SP numbering): GPB0-7 = 1-8, VDD 9, VSS 10, SCK 12, SDA 13, A0-A2 15-17, RESET 18, INTB 19, INTA 20,
    GPA0-7 = 21-28; 11 and 14 are NC"""
    p = {9: "+5V", 10: "GND", 12: "SCL", 13: "SDA", 18: "XRST", 19: None, 11: None, 14: None, 20: inta}
    for i, n in enumerate(gpa): p[21 + i] = n
    for i, n in enumerate(gpb): p[1 + i] = n
    for i, bit in enumerate(addr): p[15 + i] = "+5V" if bit else "GND"
    return p


U1 = mcp(["D0", "D1", "D2", "D3", "D4", "D5", "D6", "SPARE1"], ["A0", "A1", "A2", "A3", "A4", "A5", "A6", "SPARE2"], (0, 0, 0), "INT_U1")
U2 = mcp(["D7", "A7", "TPA", "TPB", "-MRD", "-MRW", "-VMA", "SPARE3"], ["Q", "-RESET", "-INT", "-EF", "N0", "N1", "N2", "SPARE4"],
         (1, 0, 0), "INT_U2")
U3 = mcp(["-EF1", "-EF2", "-EF3", "-PAUSE", "-DMAIN", "SC0", "SPARE5", "SPARE10"],                 # GPA7: output only
         ["DBG_CLOCK", "DBG_SC0", "DBG_SC1", "SPARE6", "SPARE7", "SPARE8", "SPARE9", "SPARE11"],   # GPB7: output only
         (0, 1, 0), "INT_U3")
# Arduino Nano v3 (KiCad's MCU_Module:Arduino_Nano_v3.x numbering): 4/29 GND, 5 D2, 6 D3, 7 D4, 8 D5, 11 D8, 12 D9,
# 19 A0, 20 A1, 23 A4 (SDA), 24 A5 (SCL); its +5V (27), VIN (30), 3V3 and the rest unconnected (USB serial is inside)
NANO = {4: "GND", 29: "GND", 5: "INT_U1", 6: "INT_U2", 7: "XRST", 8: "INT_U3", 11: "PROBE1_IN", 12: "CLK_D9",
        19: "BUS_SENSE", 20: "PROBE2_IN", 23: "SDA", 24: "SCL"}
NANO.update({k: None for k in range(1, 31) if k not in NANO})

R = "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal"
CAP = "s5bd:C025-050X050"                      # 0.1 uF with 0.1" leads (Ken's rule)
HDR = "Connector_PinHeader_2.54mm:PinHeader_1x%02d_P2.54mm_Vertical"
MCP = ("Interface_Expansion:MCP23017x-x-SP", "MCP23017", "Package_DIP:DIP-28_W7.62mm")
CHIPS = {}                                     # every symbol is KiCad's own

# ref: (lib_id, value, footprint, {pin: net or None})
PARTS = {
    "J1": ("Connector_Generic:Conn_01x36", "System-5 bus (36)", "s5bd:C36", {i + 1: n for i, n in enumerate(POS)}),
    "U1": MCP + (U1,), "U2": MCP + (U2,), "U3": MCP + (U3,),
    # the Nano is U4, not A1 as on BUSDRV-B: J1's pin label "A1" (the bus address line) would read as its reference
    "U4": ("MCU_Module:Arduino_Nano_v3.x", "Arduino Nano", "Module:Arduino_Nano", NANO),
    "R1": ("Device:R", "4.7k", R, {1: "+5V", 2: "SDA"}),
    "R2": ("Device:R", "4.7k", R, {1: "+5V", 2: "SCL"}),
    "R3": ("Device:R", "10k", R, {1: "+5V", 2: "XRST"}),
    "R4": ("Device:R", "10k", R, {1: "+5V", 2: "BUS_SENSE"}),
    "R5": ("Device:R", "100k", R, {1: "BUS_SENSE", 2: "GND"}),
    "R6": ("Device:R", "470", R, {1: "+5V", 2: "LED_PWR"}),
    "R7": ("Device:R", "100", R, {1: "CLK_D9", 2: "CLK_OUT"}),          # series resistor on the clock out
    "R8": ("Device:R", "1k", R, {1: "PROBE1", 2: "PROBE1_IN"}),         # the probes: 1k into the Nano's pins
    "R9": ("Device:R", "1k", R, {1: "PROBE2", 2: "PROBE2_IN"}),
    "LED1": ("Device:LED", "PWR", "LED_THT:LED_D3.0mm", {1: "GND", 2: "LED_PWR"}),          # LED: 1 = K, 2 = A
    "J2": ("Connector_Generic:Conn_01x09", "CLK/PROBE/SPARE", HDR % 9,
           {1: "CLK_OUT", 2: "PROBE1", 3: "PROBE2", 4: "SPARE1", 5: "SPARE2", 6: "SPARE3", 7: "SPARE4", 8: "+5V", 9: "GND"}),
    "J3": ("Connector_Generic:Conn_01x08", "SPARE", HDR % 8,
           {1: "SPARE5", 2: "SPARE6", 3: "SPARE7", 4: "SPARE8", 5: "SPARE9", 6: "SPARE10", 7: "SPARE11", 8: "GND"}),
    # DEBUG: keyed 2x3, CPU Rev D's J2 signals in the same order (a straight 6-way cable between the two)
    "J4": ("Connector_Generic:Conn_02x03_Odd_Even", "DEBUG", "Connector_IDC:IDC-Header_2x03_P2.54mm_Vertical",
           {1: "CLK_OUT", 2: "GND", 3: "DBG_CLOCK", 4: "DBG_SC0", 5: "DBG_SC1", 6: "GND"}),
    "C1": ("Device:C", "0.1uF", CAP, {1: "+5V", 2: "GND"}),
    "C2": ("Device:C", "0.1uF", CAP, {1: "+5V", 2: "GND"}),
    "C3": ("Device:C", "0.1uF", CAP, {1: "+5V", 2: "GND"}),
    "C4": ("Device:C_Polarized", "10uF", "Capacitor_THT:CP_Radial_D5.0mm_P2.00mm", {1: "+5V", 2: "GND"}),
}
DOCS = {}
