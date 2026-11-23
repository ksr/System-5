# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-01 (memory-mapped 2026-11-17)
"""netlist.py - VIDEO-G 1.0 TEXT: THE single source of the board's circuit.

make_schematic.py and make_board.py read this module; nothing else defines the circuit. Design:
hardware/video-g/DESIGN.md. The video core is YACC1's Video V2.0 (~/Developer/YACC1-D/hardware/cards/video/kicad/v2.0/
v20_netlist.py: copied, never modified) at 8 dots, with V2.0's net names where a net is kept; the bus side is
System-5's: everything memory-mapped in the card's block, no I/O ports (Ken, 2026-11-17; N0-N2 are not used).

  * memory: 74HCT373 latches A8-A15 on TPA; 74LS85 compares A12-A15 with the BLOCK jumper (block 7) while -VMA is low
    -> BOARDSEL; A11 = 0 -> the IDT7134 text RAM (7000-77FF); A11 = 1 -> UPPER (7800-7FFF), in which A10 = 1 -> WSEL,
    the GFX window (7C00-7FFF), and A10 = 0 -> the registers (7800-7BFF), decoded from A1-A2 (each pair repeating):
        IC5  the 6845's -CS at 7800/7801 (RS = A0)
        IC6  read enables while -MRD is low: 7800 the 6845, 7802 key (IC9), 7804 status (IC8), 7806 mouse (GFX)
        IC7  write strobes while -MRW is low and TPB high (C = NOT TPB): 7800 the 6845, 7804 control, 7806 Y (GFX)
    The 6845: E = NAND(-RDCRTC, -WRCRTC) (IC21C), the whole -MRD time on a read (the 1802 wants the data held up to
    200 ns past 7.5 T, so E ends with -MRD) and TPB within -MRW on a write; R/-W comes from IC24A, set while -MRD is
    low and cleared while -MRW is low, so it keeps its level between cycles and never changes while E is high
  * display: 12 MHz, IC15 counts 8-15 (8 dots), QC clocks the 6845; IDT7134 left port -> 7-bit code latch IC11 ->
    28C64 IC12 (A0-A2 = RA0-RA2) -> shifter IC13; IC14 delays reverse/cursor and DE two characters; the combine:
    dot = (text AND TEXT-ON) OR GDOT, or the XOR of the two when XORM; 7416 to the RCA composite and the DE-9.
    TEXT-ON, XORM and GDOT come from GFX (its control register); alone, RN2/RN3 hold text on, XOR off, GDOT low
  * keyboard: ATmega328P IC10 loads IC9 (LDDATA) and sets KEY-READY (IC24B); a read of 7802 clears it at TPB. KEY-READY
    also pulls one bus flag line low (IC23D, open collector): JP3 picks -EF1, -EF2, -EF3 or -EF (Ken, 2026-11-18), the
    first three on the 36-pin connector's positions 31-33
  * J6: the 40-pin ribbon to GFX (common/ribbon.py, shared with the GFX netlist)

Pin numbers are the physical DIP pins and match the KiCad symbols (checked by check()). Active-low nets start with '-'.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "common"))
import symlib
import ribbon

CARD = "VIDEO-G 1.0 TEXT"
PROJ = "video-g-text"
REV = "1.0"
DATE = "2026-11-18"
SUBTITLE = "64 x 25 / 64 x 32 text, memory-mapped at 7000-7FFF, PS/2 keyboard; with the GFX board: 512 x 200 / 512 x 256 graphics"
FLAG_NETS = ("PS2VCC",)
SCH_NOTES = [
    "VIDEO-G 1.0 TEXT (hardware/video-g/DESIGN.md): the System-5 text card of VIDEO-G; works alone, or with the GFX board on the J6 ribbon.",
    "Memory-mapped, no I/O ports (2026-11-17). Block jumper SV1: 1-2 only = block 7. 7000-77FF text RAM (IDT7134); 7C00-7FFF the GFX window (WSEL).",
    "Registers (7800-7BFF, pairs repeating): 7800/7801 the 6845 (RS = A0); 7802 key (+ a bus flag line while KEY-READY: JP3 picks -EF1, -EF2, -EF3 or -EF); 7804 status / control (GFX); 7806 mouse / Y (GFX).",
    "Status: 0 KEY-READY 1 MOUSE-READY 2 VSYNC 3 DE 4 MONITOR 5 GFX-PRESENT, 7-6 = 10. Reads while -MRD is low; writes while -MRW is low during TPB.",
    "6845: E = the -MRD time on a read, TPB within -MRW on a write; R/-W from IC24A, set by -MRD and cleared by -MRW, steady while E is high.",
]

DIP = {n: "Package_DIP:DIP-%d_W7.62mm_Socket" % n for n in (14, 16, 20, 28)}
DIPW = {n: "Package_DIP:DIP-%d_W15.24mm_Socket" % n for n in (28, 40, 48)}
FP_R = "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P2.54mm_Vertical"   # standing resistors save board
FP_C = "video-g-local:C025-050X050"                        # 0.1" lead spacing: Ken's bypass-cap rule
FP_CP = "Capacitor_THT:CP_Radial_D6.3mm_P2.50mm"
FP_H = "Connector_PinHeader_2.54mm:PinHeader_1x%02d_P2.54mm_Vertical"
LOC = "video-g-local"

# ---- parts: reference -> (value, symbol lib:name, footprint lib:name, what it does) ------------------------------------
PARTS = {
    "J1":   ("System-5 bus (36)", "Connector_Generic:Conn_01x36", LOC + ":C36", "36-pin bus connector (positions from GND)"),
    "IC1":  ("74HCT373", "74xx:74LS373", DIP[20], "A8-A15 latch, transparent while TPA is high"),
    "IC2":  ("74LS85", "74xx:74LS85", DIP[16], "block decode: A12-A15 = BLOCK jumper, enabled by VMA"),
    "IC3":  ("IDT7134", LOC + ":IDT7134", DIPW[48], "text RAM, dual port: bus 7000-77FF on the right, 6845 on the left"),
    "IC4":  ("HD68B45SP", "GPU:MC6845", DIPW[40], "CRTC at 7800 (address register) and 7801 (data)"),
    "IC5":  ("74HCT138", "74xx:74LS138", DIP[16], "the 6845's -CS: 7800/7801 (A1-A2)"),
    "IC6":  ("74HCT138", "74xx:74LS138", DIP[16], "read enables, 7800-7806, while -MRD is low"),
    "IC7":  ("74HCT138", "74xx:74LS138", DIP[16], "write strobes, 7800-7806, while -MRW is low and TPB high"),
    "IC8":  ("74LS244", "74xx:74LS244", DIP[20], "status, read at 7804"),
    "IC9":  ("74HCT374", "74xx:74LS374", DIP[20], "key latch, read at 7802"),
    "IC10": ("ATmega328P-PU", "MCU_Microchip_ATmega:ATmega328P-P", DIP[28], "PS/2 keyboard controller"),
    "IC11": ("74LS374", "74xx:74LS374", DIP[20], "character code latch, 7 bits"),
    "IC12": ("AT28C64B-15", "Memory_EEPROM:KM28C64A", DIPW[28], "character ROM: 128 characters of 8 x 8"),
    "IC13": ("74LS166", "74xx:74LS166", DIP[16], "text dot shifter"),
    "IC14": ("74LS175", "74xx:74LS175", DIP[16], "reverse/cursor and DE delays (two characters)"),
    "IC15": ("74F163A", "74xx:74LS163", DIP[16], "character counter: loads 8 on the carry"),
    "IC16": ("74LS04", "74xx:74LS04", DIP[14], "12 MHz oscillator, VMA, CHARCLOCK"),
    "IC17": ("74LS04", "74xx:74LS04", DIP[14], "TPB inverted, -BOARDSEL, -VSYNC"),
    "IC18": ("74HCT08", "74xx:74LS08", DIP[14], "VSYNC buffer, -RESET buffer, UPPER (7800-7FFF)"),
    "IC19": ("74LS08", "74xx:74LS08", DIP[14], "text dot gate, KEY-READY clear, HSYNC buffer, WSEL (the window)"),
    "IC20": ("74LS32", "74xx:74LS32", DIP[14], "dot OR, QC OR RCO, key read at TPB, text RAM -CE"),
    "IC21": ("74LS10", "74xx:74LS10", DIP[14], "XOR term, video NAND, 6845 E"),
    "IC22": ("74LS86", "74xx:74LS86", DIP[14], "cursor/reverse XORs, the GFX -WE phase"),
    "IC23": ("7416", "74xx:74LS05", DIP[14], "open collector: video, syncs, -EF, ATmega reset"),
    "IC24": ("74HCT74", "74xx:74LS74", DIP[14], "the 6845's R/-W latch, KEY-READY"),
    "Y1":   ("12MHz", "Device:Crystal", "Crystal:Crystal_HC49-U_Vertical", "dot clock"),
    "Y2":   ("16MHz", "Device:Crystal", "Crystal:Crystal_HC49-U_Vertical", "ATmega clock"),
    "J2":   ("RCA", LOC + ":RCA", LOC + ":RCA", "composite video"),
    "J3":   ("DE-9 F", LOC + ":DE9_SHIELD", LOC + ":F09HP", "TTL video: 7 video, 8 HSYNC, 9 VSYNC (JP2), 1 2 GND"),
    "J4":   ("KEYBOARD", LOC + ":MINIDIN6", LOC + ":MiniDIN6_MD-60SM", "PS/2 keyboard (Same Sky MD-60SM)"),
    "J5":   ("FTDI", "Connector_Generic:Conn_01x06", FP_H % 6, "GND CTS VCC(nc) TXD RXD DTR: ATmega bootloader"),
    "J6":   ("TO GFX", "Connector_Generic:Conn_02x20_Odd_Even", "Connector_IDC:IDC-Header_2x20_P2.54mm_Vertical",
             "40-pin ribbon to the GFX board"),
    "SV1":  ("BLOCK", "Connector_Generic:Conn_02x04_Odd_Even", "Connector_PinHeader_2.54mm:PinHeader_2x04_P2.54mm_Vertical",
             "card block: fitted = 0; 1-2 only = block 7 (7000)"),
    "JP1":  ("MONITOR", "Connector_Generic:Conn_01x03", FP_H % 3, "1-2 NTSC (64 x 25), 2-3 MDA / IBM 5151 (64 x 32)"),
    "JP2":  ("VSYNC", "Connector_Generic:Conn_01x03", FP_H % 3, "DE-9 pin 9: 1-2 +VSYNC, 2-3 -VSYNC (5151)"),
    "JP3":  ("KBD FLAG", "Connector_Generic:Conn_02x04_Odd_Even", "Connector_PinHeader_2.54mm:PinHeader_2x04_P2.54mm_Vertical",
             "one shunt: KEY-READY onto -EF1, -EF2, -EF3 or -EF (set to -EF)"),
    "F1":   ("0.5A PTC", "Device:Polyfuse", "Fuse:Fuse_Bourns_MF-RHT050", "keyboard +5 V"),
    "LED1": ("PWR", "Device:LED", "LED_THT:LED_D5.0mm", "power"),
    "RN1":  ("10k x4", "Device:R_Network04", "Resistor_THT:R_Array_SIP5", "BLOCK pull-ups (bussed, pin 1 common)"),
    "RN2":  ("10k x5", "Device:R_Network05", "Resistor_THT:R_Array_SIP6",
             "pull-ups: bus -EF, -VMA, -RESET (the 2009 bus has none), LDDATA, TEXT-ON (GFX absent: text on)"),
    "RN3":  ("10k x5", "Device:R_Network05", "Resistor_THT:R_Array_SIP6",
             "pull-downs: MONITOR (open = NTSC), and GDOT, MOUSE-READY, GFX-PRESENT, XORM for GFX absent"),
    "R1":   ("1k", "Device:R", FP_R, "oscillator bias"),
    "R2":   ("1k", "Device:R", FP_R, "oscillator bias"),
    "R3":   ("1k", "Device:R", FP_R, "counter enables / clears high"),
    "R4":   ("33", "Device:R", FP_R, "video to the sync node"),
    "R5":   ("270", "Device:R", FP_R, "sync node pull-up"),
    "R6":   ("330", "Device:R", FP_R, "PWR LED"),
    "R7":   ("10k", "Device:R", FP_R, "ATmega reset pull-up"),
    "R8":   ("4.7k", "Device:R", FP_R, "RESETH pull-up"),
    "R9":   ("4.7k", "Device:R", FP_R, "keyboard clock pull-up"),
    "R10":  ("4.7k", "Device:R", FP_R, "keyboard data pull-up"),
    "R11":  ("33", "Device:R", FP_R, "ribbon DOTCLOCK series"),
    "R12":  ("33", "Device:R", FP_R, "ribbon CHARCLOCK series"),
    "R13":  ("33", "Device:R", FP_R, "ribbon QC series"),
    "C26":  ("47u 16V", "Device:C_Polarized", FP_CP, "bulk"),
    "C27":  ("100n", "Device:C", FP_C, "FTDI DTR auto-reset"),
    "C28":  ("22p", "Device:C", FP_C, "Y2 load"),
    "C29":  ("22p", "Device:C", FP_C, "Y2 load"),
}
DECOUPLE = {"C%d" % n: "IC%d" % n for n in range(1, 25)}
DECOUPLE["C25"] = "IC10"                                    # the ATmega's AVCC
for cap, ic in DECOUPLE.items():
    PARTS[cap] = ("100n", "Device:C", FP_C, "%s bypass" % ic)

NETS = {}
def c(net, *pins):
    """connect pins ("REF.PIN") to net"""
    for p in pins:
        ref, pin = p.rsplit(".", 1)
        NETS.setdefault(net, []).append((ref, pin))

# ---- power -----------------------------------------------------------------------------------------------------------
POWER = {"IC1": (20, 10), "IC2": (16, 8), "IC3": (48, 24), "IC4": (20, 1), "IC5": (16, 8), "IC6": (16, 8), "IC7": (16, 8),
         "IC8": (20, 10), "IC9": (20, 10), "IC11": (20, 10), "IC12": (28, 14), "IC13": (16, 8), "IC14": (16, 8),
         "IC15": (16, 8)}
for n in range(16, 25):
    POWER["IC%d" % n] = (14, 7)
for ref, (v, g) in POWER.items():
    c("+5V", "%s.%d" % (ref, v)); c("GND", "%s.%d" % (ref, g))
c("+5V", "IC10.7", "IC10.20"); c("GND", "IC10.8", "IC10.22")
for cap in DECOUPLE:
    c("+5V", cap + ".1"); c("GND", cap + ".2")
c("+5V", "C26.1"); c("GND", "C26.2")

# ---- the bus (J1) ----------------------------------------------------------------------------------------------------
# The 36-pin connector since 2026-11-18 (Ken: "on video change keyboard to ef to be a select of 1 of 4 efs": -EF1 to -EF3
# are on the slot's positions beyond +5V, which a 30-pin card does not reach). BUS: the 30-pin bus as a 30-pin card
# numbers it; POS: the slot's 36 positions counted from GND, as the bus Rev D has them (its gen/netlist.py)
BUS = {1: "+5V", 2: "D0", 3: "D1", 4: "D2", 5: "D3", 6: "D4", 7: "D5", 8: "D6", 9: "D7", 10: "Q", 11: "TPA", 12: "TPB",
       13: "-MRD", 14: "-MRW", 15: "A0", 16: "A1", 17: "A2", 18: "A3", 19: "A4", 20: "A5", 21: "A6", 22: "A7", 23: "-INT",
       24: "N2", 25: "-EF", 26: "-VMA", 27: "-RESET", 28: "N1", 29: "N0", 30: "GND"}
POS = [BUS[i] for i in range(30, 0, -1)] + ["-EF1", "-EF2", "-EF3", "-DMAIN", "SC0", "-PAUSE"]   # position 1..36, from GND
UNUSED = {"Q", "-INT", "N0", "N1", "N2", "-DMAIN", "SC0", "-PAUSE"}      # N0-N2: no I/O ports; the rest: not this card's
for i, net in enumerate(POS):
    if net not in UNUSED:
        c(net, "J1.%d" % (i + 1))
c("+5V", "RN2.1")                                          # RN2 pull-ups (the 2009 bus has none on these)
for k, net in enumerate(("-EF", "-VMA", "-RESET", "LDDATA", "TEXTON")):
    c(net, "RN2.%d" % (2 + k))
c("GND", "RN3.1")                                          # RN3 pull-downs
for k, net in enumerate(("MONITOR", "GDOT", "MREADY", "GFXPRES", "XORM")):
    c(net, "RN3.%d" % (2 + k))

# ---- memory decode: IC1 latch, IC2 block compare, SV1 + RN1 ---------------------------------------------------------
L373 = ((3, 2), (4, 5), (7, 6), (8, 9), (13, 12), (14, 15), (17, 16), (18, 19))       # (D, Q) of bits 0..7 (373/374)
c("GND", "IC1.1"); c("TPA", "IC1.11")
for i, (d, q) in enumerate(L373):
    c("A%d" % i, "IC1.%d" % d); c("A%d" % (8 + i), "IC1.%d" % q)
c("A12", "IC2.9"); c("A13", "IC2.11"); c("A14", "IC2.14"); c("A15", "IC2.1")
for i, (a_pin, sv, rn) in enumerate(((10, 7, 2), (12, 5, 3), (13, 3, 4), (15, 1, 5))):
    c("SEL%d" % i, "IC2.%d" % a_pin, "SV1.%d" % sv, "RN1.%d" % rn)
c("GND", "SV1.2", "SV1.4", "SV1.6", "SV1.8", "IC2.2", "IC2.4"); c("+5V", "RN1.1")
c("VMA", "IC2.3"); c("BOARDSEL", "IC2.6")
c("-VMA", "IC16.9"); c("VMA", "IC16.8")                                    # IC16D
c("BOARDSEL", "IC17.5"); c("-BOARDSEL", "IC17.6")                          # IC17C
c("-BOARDSEL", "IC20.12"); c("A11", "IC20.13"); c("-TXTCE", "IC20.11")     # IC20D: -CE = NOT BOARDSEL OR A11
c("BOARDSEL", "IC18.12"); c("A11", "IC18.13"); c("UPPER", "IC18.11")       # IC18D: 7800-7FFF
c("UPPER", "IC19.12"); c("A10", "IC19.13"); c("WSEL", "IC19.11")           # IC19D: the GFX window, 7C00-7FFF

# ---- text RAM IC3 (IDT7134) ------------------------------------------------------------------------------------------
c("GND", "IC3.1", "IC3.5", "IC3.45"); c("+5V", "IC3.2")                    # -CEL, -OEL low, R/-WL high; A11R low
for i, pin in enumerate((42, 41, 40, 39, 38, 37, 36, 35)):
    c("A%d" % i, "IC3.%d" % pin)
c("A8", "IC3.34"); c("A9", "IC3.33"); c("A10", "IC3.44")
for i in range(8):
    c("D%d" % i, "IC3.%d" % (25 + i))
c("-MRD", "IC3.43"); c("-MRW", "IC3.46"); c("-TXTCE", "IC3.47")
for i, pin in enumerate((6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 4, 3)):
    c("MA%d" % i, "IC3.%d" % pin, "IC4.%d" % (4 + i))
for i in range(8):
    c("VD%d" % i, "IC3.%d" % (16 + i))

# ---- 6845 IC4 at 7800/7801 ------------------------------------------------------------------------------------------
c("-RESET", "IC4.2"); c("GND", "IC4.3")                                    # LPSTB low
c("DE", "IC4.18"); c("CURSOR", "IC4.19"); c("CRTCCLK", "IC4.21")
c("CRTCRW", "IC4.22"); c("CRTCE", "IC4.23"); c("A0", "IC4.24"); c("-CRTCCS", "IC4.25")
for i in range(8):
    c("D%d" % i, "IC4.%d" % (33 - i))
c("RA2", "IC4.36"); c("RA1", "IC4.37"); c("RA0", "IC4.38"); c("HSYNC", "IC4.39"); c("VSYNC", "IC4.40")
c("GND", "IC18.9", "IC18.10")                                              # IC18C spare
c("-RDCRTC", "IC21.9"); c("-WRCRTC", "IC21.10"); c("+5V", "IC21.11"); c("CRTCE", "IC21.8")   # IC21C: E

# ---- register decode IC5/IC6/IC7 (A1-A2 within 7800-7BFF), the 6845's R/-W latch (IC24A) ----------------------------
for ref in ("IC5", "IC6", "IC7"):                                          # G1 = UPPER, -G2A = A10: 7800-7BFF
    c("A1", ref + ".1"); c("A2", ref + ".2"); c("A10", ref + ".4"); c("UPPER", ref + ".6")
c("GND", "IC5.3", "IC5.5", "IC6.3"); c("-CRTCCS", "IC5.15")                # IC5: the 6845's -CS, 7800/7801
c("-MRD", "IC6.5")                                                         # IC6: reads while -MRD is low
c("-RDCRTC", "IC6.15"); c("-RDKEY", "IC6.14"); c("-RDSTAT", "IC6.13"); c("-RDMOUSE", "IC6.12")
c("TPBN", "IC7.3"); c("-MRW", "IC7.5")                                     # IC7: writes while -MRW low, TPB high
c("-WRCRTC", "IC7.15"); c("-WRCTL", "IC7.13"); c("-WRY", "IC7.12")
c("GND", "IC16.11")                                                        # IC16E spare
c("GND", "IC17.1"); c("TPB", "IC17.3"); c("TPBN", "IC17.4")                # IC17A spare; IC17B: NOT TPB
c("-MRW", "IC24.1"); c("-MRD", "IC24.4"); c("GND", "IC24.2", "IC24.3")     # IC24A: -PRE = -MRD sets R/-W (read),
c("CRTCRW", "IC24.5")                                                      # -CLR = -MRW clears it (write)

# ---- status IC8 (INP 4) ----------------------------------------------------------------------------------------------
c("-RDSTAT", "IC8.1", "IC8.19")
for i, (a, y) in enumerate(((2, 18), (4, 16), (6, 14), (8, 12), (11, 9), (13, 7), (15, 5), (17, 3))):
    c("D%d" % i, "IC8.%d" % y)
    c(("KREADY", "MREADY", "VSYNC", "DE", "MONITOR", "GFXPRES", "GND", "+5V")[i], "IC8.%d" % a)   # ID bits 7..6 = 10
c("GND", "JP1.1"); c("MONITOR", "JP1.2"); c("+5V", "JP1.3")

# ---- clocks: Y1, IC16 oscillator, IC15 counter, CHARCLOCK (IC16F) ---------------------------------------------------
c("OSCIN", "Y1.1", "R1.1", "IC16.1"); c("OSCMID", "IC16.2", "IC16.3", "R1.2", "R2.1")
c("OSCOUT", "IC16.4", "IC16.5", "Y1.2", "R2.2"); c("DOTCLK", "IC16.6")
c("DOTCLK", "IC15.2", "IC13.7")
c("+5V", "IC15.1", "IC15.6"); c("GND", "IC15.3", "IC15.4", "IC15.5")       # load D C B A = 1 0 0 0 = 8
c("CNTEN", "IC15.7", "IC15.10", "R3.1", "IC14.1", "IC13.9"); c("+5V", "R3.2")
c("CHARCLOCK", "IC15.9", "IC14.9", "IC11.11", "IC13.15")
c("RCO", "IC15.15", "IC16.13"); c("CHARCLOCK", "IC16.12")                 # IC16F: CHARCLOCK = NOT RCO
c("CRTCCLK", "IC15.12"); c("CNTQB", "IC15.13"); c("CNTQA", "IC15.14")
c("CRTCCLK", "IC20.4"); c("RCO", "IC20.5"); c("QCR", "IC20.6")            # IC20B: QC OR RCO (GFX mux select)
c("CNTQA", "IC22.12"); c("CNTQB", "IC22.13"); c("WEPH", "IC22.11")        # IC22D: counts 9-10 (GFX -WE phase)

# ---- text pipeline: IC11 code latch, IC12 ROM, IC13 shifter, IC14 delays, IC22 XORs ----------------------------------
c("GND", "IC11.1", "IC11.18")                                              # -OE low; D7 unused
ROM_A = (7, 6, 5, 4, 3, 25, 24)                                            # 28C64 A3..A9
for i, (d, q) in enumerate(L373[:7]):
    c("VD%d" % i, "IC11.%d" % d); c("CA%d" % (3 + i), "IC11.%d" % q, "IC12.%d" % ROM_A[i])
c("RA2", "IC12.8"); c("RA1", "IC12.9"); c("RA0", "IC12.10")
c("GND", "IC12.20", "IC12.22", "IC12.21", "IC12.23", "IC12.2"); c("+5V", "IC12.27")   # -CE -OE low, A10-A12 low, -WE high
for k, (o, s) in enumerate(((11, 2), (12, 3), (13, 4), (15, 5), (16, 10), (17, 11), (18, 12), (19, 14))):
    c("CG%d" % k, "IC12.%d" % o, "IC13.%d" % s)                            # H (bit 7) shifts out first: leftmost dot
c("GND", "IC13.1", "IC13.6"); c("TDOT", "IC13.13")
c("CURSOR", "IC22.1"); c("VD7", "IC22.2"); c("ATTR1", "IC22.3", "IC14.4")
c("ATTR2", "IC14.2", "IC14.5"); c("ATTR3", "IC14.7", "IC22.4"); c("TDOT", "IC22.5"); c("TD", "IC22.6")
c("DE", "IC14.12"); c("DE2", "IC14.10", "IC14.13"); c("DE3", "IC14.15")
c("GND", "IC22.9", "IC22.10")                                              # IC22C spare

# ---- combine and video out ------------------------------------------------------------------------------------------
c("TD", "IC19.1"); c("TEXTON", "IC19.2"); c("TDG", "IC19.3")               # IC19A
c("TDG", "IC20.1", "IC21.1"); c("GDOT", "IC20.2", "IC21.2"); c("GOR", "IC20.3", "IC21.3")    # IC20A, IC21A/B
c("XORM", "IC21.13"); c("NBOTH", "IC21.12", "IC21.4"); c("DE3", "IC21.5"); c("VIDN", "IC21.6")
c("HSYNC", "IC19.9", "IC19.10"); c("HSBUF", "IC19.8")                      # IC19C: HSYNC buffer (unloads the 6845)
c("VSYNC", "IC18.1", "IC18.2"); c("VSBUF", "IC18.3")                       # IC18A: VSYNC buffer (HCT input)
c("VSBUF", "IC17.9"); c("NVSYNC", "IC17.8")                                # IC17D
c("GND", "IC17.11", "IC17.13")                                             # IC17E, F spare
c("VIDN", "IC23.1"); c("VIDEO", "IC23.2", "R4.2", "J3.7")
c("VSBUF", "IC23.3"); c("HSBUF", "IC23.5", "J3.8")
c("SYNC", "IC23.4", "IC23.6", "R4.1", "R5.2", "J2.C1"); c("+5V", "R5.1")
c("VSBUF", "JP2.1"); c("DE9VS", "JP2.2", "J3.9"); c("NVSYNC", "JP2.3")
c("GND", "J3.1", "J3.2", "J3.G1", "J3.G2", "J2.S1", "J2.S2", "J2.S3")
c("PWRLED", "R6.1", "LED1.2"); c("+5V", "R6.2"); c("GND", "LED1.1")       # LED: 1 = K, 2 = A

# ---- keyboard: IC10 ATmega328P, Y2, reset, FTDI, IC9 latch, KEY-READY (IC24B), -EF ----------------------------------
c("-RESET", "IC18.4"); c("+5V", "IC18.5"); c("RESETB", "IC18.6")          # IC18B: -RESET buffer for the 7416 input
c("RESETB", "IC23.11"); c("RESETH", "IC23.10", "R8.1", "IC23.13"); c("+5V", "R8.2")
c("MRST", "IC10.1", "R7.1", "C27.2", "IC23.12"); c("+5V", "R7.2")
c("FTX", "IC10.2", "J5.4"); c("FRX", "IC10.3", "J5.5"); c("FDTR", "J5.6", "C27.1"); c("GND", "J5.1", "J5.2")
c("KCLK", "IC10.4", "R9.1", "J4.5"); c("KDAT", "IC10.6", "R10.1", "J4.1"); c("+5V", "R9.2", "R10.2", "F1.1")
c("PS2VCC", "F1.2", "J4.4"); c("GND", "J4.3", "J4.S")
c("XT1", "IC10.9", "Y2.1", "C28.1"); c("XT2", "IC10.10", "Y2.2", "C29.1"); c("GND", "C28.2", "C29.2")
c("LDDATA", "IC10.12", "IC9.11", "IC24.11")
for i, pin in enumerate((23, 24, 25, 26, 27, 28, 14, 15)):
    c("MD%d" % i, "IC10.%d" % pin)
c("KREADY", "IC10.16")
c("-RDKEY", "IC9.1")
for i, (d, q) in enumerate(L373):
    c("MD%d" % i, "IC9.%d" % d); c("D%d" % i, "IC9.%d" % q)
c("+5V", "IC24.12", "IC24.10"); c("KCLR", "IC24.13"); c("KREADY", "IC24.9")
c("-RDKEY", "IC20.9"); c("TPBN", "IC20.10"); c("KRDT", "IC20.8")           # IC20C: low while 7802 is read, at TPB
c("KRDT", "IC19.4"); c("-RESET", "IC19.5"); c("KCLR", "IC19.6")           # IC19B: ... or -RESET
c("KREADY", "IC23.9"); c("EFOC", "IC23.8", "JP3.2", "JP3.4", "JP3.6", "JP3.8")   # IC23D, open collector: low while a key
c("-EF1", "JP3.1"); c("-EF2", "JP3.3"); c("-EF3", "JP3.5"); c("-EF", "JP3.7")    # waits, on the flag line JP3's shunt picks

# ---- J6: the ribbon to GFX (pin map in common/ribbon.py) -------------------------------------------------------------
c("DOTCLK", "R11.1"); c("RDOTCLK", "R11.2")
c("CHARCLOCK", "R12.1"); c("RCHARCLK", "R12.2")
c("CRTCCLK", "R13.1"); c("RQC", "R13.2")
for pin, sig in ribbon.PINS.items():
    c(ribbon.TEXT_NET.get(sig, sig), "J6.%d" % pin)

# ---- pins left open (a no-connect flag each) -------------------------------------------------------------------------
NO_CONNECT = {
    "J1": [i + 1 for i, n in enumerate(POS) if n in UNUSED], "IC2": [5, 7], "IC4": [16, 17, 34, 35], "IC5": [14, 13, 12, 11, 10, 9, 7],
    "IC6": [11, 10, 9, 7], "IC7": [14, 11, 10, 9, 7], "IC11": [19], "IC12": [1, 26], "IC14": [3, 6, 11, 14],
    "IC15": [11], "IC16": [10], "IC17": [2, 10, 12], "IC18": [8], "IC22": [8], "IC24": [6, 8],
    "IC10": [5, 11, 13, 17, 18, 19, 21],
    "J3": [3, 4, 5, 6], "J4": [2, 6], "J5": [3],
}
NO_CONNECT = {r: [str(p) for p in ps] for r, ps in NO_CONNECT.items()}

# ---- what to buy: the parts whose exact type matters (BOM.md) -------------------------------------------------------
BUY = {
    "IC3": "IDT7134SA or LA, 55-90 ns, DIP-48 (600 mil); the 6845 card's chip also fits",
    "IC4": "HD68B45SP (Hitachi) or MC68B45P (Motorola): the 2 MHz grade is needed, for the write E pulse (284 ns at 1.76 MHz, DESIGN.md section 4); the 6845 card's 1 MHz HD6845 is too slow for it",
    "IC10": "ATmega328P-PU with the Arduino Uno bootloader burned (ISP) before fitting",
    "IC12": "AT28C64B-15PU (Microchip), burned on the T48 with firmware/video-g-chargen/video-g-chargen.bin",
    "IC15": "74F163A or 74ALS163B (V2.0 review R3-1: CHARCLOCK set-up to the 166's SH/-LD); keep a spare",
    "IC1": "74HCT373 (CMOS inputs: no load on the 1802's address lines)",
    "IC5": "74HCT138 (CMOS inputs on the bus address)", "IC6": "74HCT138 (CMOS inputs on the bus address)",
    "IC7": "74HCT138 (CMOS inputs on the bus address)",
    "RN1": "10k x4 BUSSED, pin 1 common, 5-pin SIP (e.g. Bourns 4605X-101-103LF)",
    "RN2": "10k x5 BUSSED, pin 1 common, 6-pin SIP (e.g. Bourns 4606X-101-103LF)",
    "RN3": "10k x5 BUSSED, pin 1 common, 6-pin SIP (e.g. Bourns 4606X-101-103LF)",
    "J1": "1 x 36 right-angle pin header, 2.54 mm, single row (cut from a 1 x 40): its plastic body lies between the pads and the card edge, the pins out past the edge",
    "J2": "RCA jack, right-angle PCB mount (YACC1 V1.0 card's footprint)",
    "J3": "DE-9 female, right-angle PCB mount (F09HP footprint: 2.74 mm pitch, 2.54 mm between rows)",
    "J4": "Same Sky (CUI Devices) MD-60SM, date code after 2022-03-03",
    "J6": "2 x 20 shrouded box header, 2.54 mm; 40-way IDC ribbon (two 2 x 20 IDC sockets, about 10 cm)",
    "J5": "1 x 6 pin header, 2.54 mm (an FTDI cable programs the ATmega)",
    "SV1": "2 x 4 pin header + 1 shunt on 1-2 (block 7, 7000); each fitted shunt is a 0 bit",
    "JP1": "1 x 3 pin header + shunt: 1-2 NTSC, 2-3 IBM 5151", "JP2": "1 x 3 pin header + shunt: 1-2 +VSYNC, 2-3 -VSYNC (5151)",
    "JP3": "2 x 4 pin header + 1 shunt: the keyboard flag on -EF1, -EF2, -EF3 or -EF (set to -EF, the fourth pair)",
    "F1": "Bourns MF-RHT050 (0.5 A hold, radial)",
    "Y1": "12 MHz, HC-49/U", "Y2": "16 MHz, HC-49/U, 18-20 pF load",
    "C26": "47 uF electrolytic, 16 V or more, radial 6.3 mm, 2.5 mm pitch",
}
for _r, _p in PARTS.items():
    if _p[0] == "100n": BUY.setdefault(_r, "ceramic X7R, 50 V, 0.1 in (2.54 mm) lead spacing")
    elif _p[0] == "22p": BUY.setdefault(_r, "ceramic C0G (NP0), 50 V, 0.1 in lead spacing")
    elif _r.startswith("R") and not _r.startswith("RN"): BUY.setdefault(_r, "1/4 W metal film, mounted standing")


def check():
    """-> problems: unknown parts or pins, a pin on two nets, a pin both connected and no-connect, one-pin nets, and
    symbol pins left neither connected nor no-connect"""
    probs, seen = [], {}
    for net, conns in NETS.items():
        for ref, pin in conns:
            if ref not in PARTS:
                probs.append("%s: unknown part %s" % (net, ref)); continue
            if pin not in symlib.pins(PARTS[ref][1]):
                probs.append("%s: %s has no pin %s" % (net, ref, pin))
            if (ref, pin) in seen and seen[(ref, pin)] != net:
                probs.append("%s.%s on %s and %s" % (ref, pin, seen[(ref, pin)], net))
            seen[(ref, pin)] = net
        if len(set(conns)) < 2:
            probs.append("%s: one pin only %s" % (net, conns))
    for ref, ps in NO_CONNECT.items():
        for p in ps:
            if p not in symlib.pins(PARTS[ref][1]): probs.append("%s.%s: no-connect on a pin the symbol lacks" % (ref, p))
            if (ref, p) in seen: probs.append("%s.%s is a no-connect and on %s" % (ref, p, seen[(ref, p)]))
    for ref, (val, lib_id, fp, note) in PARTS.items():
        for num in symlib.pins(lib_id):
            if (ref, num) not in seen and num not in NO_CONNECT.get(ref, []):
                probs.append("%s.%s (%s) unconnected" % (ref, num, symlib.pins(lib_id)[num].name))
    return probs


def pinmap():
    """{ref: {pin: net or None}} for the generators"""
    out = {ref: {} for ref in PARTS}
    for net, conns in NETS.items():
        for ref, pin in conns: out[ref][pin] = net
    for ref, ps in NO_CONNECT.items():
        for p in ps: out[ref][p] = None
    return out


if __name__ == "__main__":
    p = check()
    print("\n".join(p) or "%s: %d parts, %d nets, %d connections - OK" % (
        CARD, len(PARTS), len(NETS), sum(len(set(v)) for v in NETS.values())))
