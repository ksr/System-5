# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-06
"""BUSDRV-B: the System-5 bus driver card (Rev A, ordered 2026-10-09, was routed on 4 layers and is scrap). The netlist is defined once here; make_schematic.py and make_board.py both use it.

An Arduino Nano (USB serial console) drives two MCP23017 I2C expanders whose 32 pins go straight onto the 30-pin bus
(28 signals; +5V and GND are power). MCP23017 GPA7/GPB7 are output-only on current silicon, so they carry the four
spare outputs (J2); every bus signal sits on a bidirectional pin, readable when monitoring.
Power: the Nano runs from its USB; the expanders, I2C pull-ups and reset pull-up from bus +5V, so a powered-down
System-5 is never fed from USB. A0 senses bus +5V (10k/100k) so the firmware knows when the bus is up.
"""
BUS = {1: "+5V", 2: "D0", 3: "D1", 4: "D2", 5: "D3", 6: "D4", 7: "D5", 8: "D6", 9: "D7", 10: "Q", 11: "TPA", 12: "TPB",
       13: "-MRD", 14: "-MRW", 15: "A0", 16: "A1", 17: "A2", 18: "A3", 19: "A4", 20: "A5", 21: "A6", 22: "A7", 23: "-INT",
       24: "N2", 25: "-EF", 26: "-VMA", 27: "-RESET", 28: "N1", 29: "N0", 30: "GND"}

def mcp(gpa, gpb, addr):
    """MCP23017 (SP/SO numbering): GPB0-7 = 1-8, VDD 9, VSS 10, SCK 12, SDA 13, A0-A2 15-17, RESET 18, INTB 19, INTA 20,
    GPA0-7 = 21-28; 11 and 14 are NC"""
    p = {9: "+5V", 10: "GND", 12: "SCL", 13: "SDA", 18: "XRST", 19: None, 11: None, 14: None}
    for i, n in enumerate(gpa): p[21 + i] = n
    for i, n in enumerate(gpb): p[1 + i] = n
    for i, bit in enumerate(addr): p[15 + i] = "+5V" if bit else "GND"
    return p

U1 = mcp(["D0", "D1", "D2", "D3", "D4", "D5", "D6", "SPARE1"], ["A0", "A1", "A2", "A3", "A4", "A5", "A6", "SPARE2"], (0, 0, 0))
U1[20] = "INT_U1"
U2 = mcp(["D7", "A7", "TPA", "TPB", "-MRD", "-MRW", "-VMA", "SPARE3"], ["Q", "-RESET", "-INT", "-EF", "N0", "N1", "N2", "SPARE4"], (1, 0, 0))
U2[20] = "INT_U2"
NANO = {4: "GND", 29: "GND", 5: "INT_U1", 6: "INT_U2", 7: "XRST", 19: "BUS_SENSE", 23: "SDA", 24: "SCL"}
NANO.update({k: None for k in range(1, 31) if k not in NANO})       # everything else unconnected (USB serial is internal)

# ref: (lib_id, value, footprint, {pin: net or None})
PARTS = {
    "J1": ("Connector_Generic:Conn_01x30", "System-5 bus", "busdrv:C30", dict(BUS)),
    "U1": ("Interface_Expansion:MCP23017x-x-SP", "MCP23017", "Package_DIP:DIP-28_W7.62mm", U1),
    "U2": ("Interface_Expansion:MCP23017x-x-SP", "MCP23017", "Package_DIP:DIP-28_W7.62mm", U2),
    "A1": ("MCU_Module:Arduino_Nano_v3.x", "Arduino Nano", "Module:Arduino_Nano", NANO),
    "J2": ("Connector_Generic:Conn_01x06", "SPARE", "Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical",
           {1: "SPARE1", 2: "SPARE2", 3: "SPARE3", 4: "SPARE4", 5: "+5V", 6: "GND"}),
    "R1": ("Device:R", "4.7k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal", {1: "+5V", 2: "SDA"}),
    "R2": ("Device:R", "4.7k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal", {1: "+5V", 2: "SCL"}),
    "R3": ("Device:R", "10k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal", {1: "+5V", 2: "XRST"}),
    "R4": ("Device:R", "10k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal", {1: "+5V", 2: "BUS_SENSE"}),
    "R5": ("Device:R", "100k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal", {1: "BUS_SENSE", 2: "GND"}),
    "R6": ("Device:R", "470", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal", {1: "+5V", 2: "LED_PWR"}),
    "D1": ("Device:LED", "PWR", "LED_THT:LED_D5.0mm", {1: "GND", 2: "LED_PWR"}),          # LED: 1 = K, 2 = A
    "C1": ("Device:C", "0.1uF", "busdrv:C025-050X050", {1: "+5V", 2: "GND"}),
    "C2": ("Device:C", "0.1uF", "busdrv:C025-050X050", {1: "+5V", 2: "GND"}),
    "C3": ("Device:C_Polarized", "10uF", "Capacitor_THT:CP_Radial_D5.0mm_P2.00mm", {1: "+5V", 2: "GND"}),
}
LABELS = {   # silkscreen: ref -> (line 1, line 2)
    "U1": ("U1 MCP23017 @0x20", "D0-D6 A0-A6"), "U2": ("U2 MCP23017 @0x21", "D7 A7 CONTROL"),
    "A1": ("A1 ARDUINO NANO", "USB SERIAL"),
}
