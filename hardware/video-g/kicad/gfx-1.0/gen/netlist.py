# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-01
"""netlist.py - VIDEO-G 1.0 GFX: THE single source of the board's circuit.

make_schematic.py and make_board.py read this module. Design: hardware/video-g/DESIGN.md, section 5. The graphics
layer is YACC1's Video V2.0 (~/Developer/YACC1-D/hardware/cards/video/kicad/v2.0/v20_netlist.py: copied, never
modified) without direct mode, with the plane register replaced by the Y register:

  * graphics RAM IC1 (62256): two pages of 16K. The display reads {DPAGE, RA2-RA0, MA10-MA0} (plane n = scan line n of
    every character row), the CPU {CPAGE, Y2-Y0, Y7-Y3, A5-A0}: the same layout, so pixel line y, byte x/8 is plain
    wiring. Four 74HCT157 (IC2-IC5) choose on NMUX = NOT(QC OR RCO): the CPU's in the first half of each character
    time (counts 8-11), the display's in the second (12-15)
  * CPU read: IC6 loads the CPU-half byte on every QC rise and drives D0-D7 while GSEL AND -MRD low
  * CPU write: WRQ (IC13A) = GSEL AND -MRW low, sampled on CHARCLOCK's rise; -WE = NAND(WRQ, NMUX, WEPH, GWR) = counts
    9-10; IC7 drives the byte onto the RAM only while -WE is low; the RAM's -OE is off through that CPU half
  * display: IC8 latches the display-half byte on CHARCLOCK's rise, IC9 shifts it out at the dot clock -> GDOT
  * Y register IC10, loaded by OUT 7 (-WR7 from TEXT); control register IC19, loaded by OUT 4 (-WR4 from TEXT):
    0 TEXT-OFF (TEXT-ON to TEXT), 1 GFX-ON (gates GDOT here), 2 XOR (to TEXT), 3 DPAGE, 4 CPAGE, 5 MOUSE-ON
  * mouse: ATmega328P IC11 (the keyboard firmware in mouse mode: PD7 strapped low) loads IC12 (INP 7, -RD7 from TEXT)
    and sets MOUSE-READY (IC13B); INP 7 clears it at TPB; it reports only while MOUSE-ON (control bit 5)
  * J4: the 40-pin ribbon from TEXT (common/ribbon.py). Every decode is on TEXT; GFX uses only D0-D7, A0-A5, -MRD,
    -MRW, TPB, -RESET from the bus.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "common"))
import symlib
import ribbon

CARD = "VIDEO-G 1.0 GFX"
PROJ = "video-g-gfx"
REV = "1.0"
DATE = "2026-11-01"
SUBTITLE = "512 x 200 / 512 x 256 graphics in two pages, Y register (OUT 7), PS/2 mouse (INP 7); needs the TEXT board"
FLAG_NETS = ("PS2VCC",)
SCH_NOTES = [
    "VIDEO-G 1.0 GFX (hardware/video-g/DESIGN.md): the graphics board of VIDEO-G, on the J4 ribbon from TEXT (which decodes everything).",
    "CPU window 7800-783F = pixel line Y (OUT 7), bit 7 of byte 0 = leftmost dot. Pages: DPAGE shown, CPAGE written (OUT 4 bits 3, 4).",
    "RAM address: display {DPAGE, RA2-RA0, MA10-MA0}, CPU {CPAGE, Y2-Y0, Y7-Y3, A5-A0}; the RAM is shared per character time (no snow).",
    "Mouse: INP 7 = the next byte of the 3-byte PS/2 packets; MOUSE-READY on TEXT's status bit 1; reports only while MOUSE-ON.",
]

DIP = {n: "Package_DIP:DIP-%d_W7.62mm_Socket" % n for n in (14, 16, 20, 28)}
DIPW = {n: "Package_DIP:DIP-%d_W15.24mm_Socket" % n for n in (28,)}
FP_R = "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P2.54mm_Vertical"   # standing resistors save board
FP_C = "video-g-local:C025-050X050"
FP_CP = "Capacitor_THT:CP_Radial_D6.3mm_P2.50mm"
FP_H = "Connector_PinHeader_2.54mm:PinHeader_1x%02d_P2.54mm_Vertical"
LOC = "video-g-local"

PARTS = {
    "J1":   ("System-5 bus", "Connector_Generic:Conn_01x30", LOC + ":C30", "30-pin bus connector"),
    "IC1":  ("AS6C62256-55", "Memory_RAM:KM62256CLP", DIPW[28], "graphics RAM: two 16K pages, shared per character time"),
    "IC2":  ("74HCT157", "74xx:74LS157", DIP[16], "RAM address GA0-GA3: A0-A3 / MA0-MA3"),
    "IC3":  ("74HCT157", "74xx:74LS157", DIP[16], "RAM address GA4-GA7: A4 A5 Y3 Y4 / MA4-MA7"),
    "IC4":  ("74HCT157", "74xx:74LS157", DIP[16], "RAM address GA8-GA11: Y5 Y6 Y7 Y0 / MA8-MA10 RA0"),
    "IC5":  ("74HCT157", "74xx:74LS157", DIP[16], "RAM address GA12-GA14: Y1 Y2 CPAGE / RA1 RA2 DPAGE"),
    "IC6":  ("74HCT374", "74xx:74LS374", DIP[20], "CPU read latch (loads on QC's rise)"),
    "IC7":  ("74HCT244", "74xx:74LS244", DIP[20], "write buffer D0-D7 -> RAM (while -WE)"),
    "IC8":  ("74LS374", "74xx:74LS374", DIP[20], "display latch (CHARCLOCK)"),
    "IC9":  ("74LS166", "74xx:74LS166", DIP[16], "graphics dot shifter"),
    "IC10": ("74HCT374", "74xx:74LS374", DIP[20], "Y register, OUT 7"),
    "IC11": ("ATmega328P-PU", "MCU_Microchip_ATmega:ATmega328P-P", DIP[28], "PS/2 mouse controller"),
    "IC12": ("74HCT374", "74xx:74LS374", DIP[20], "mouse latch, INP 7"),
    "IC13": ("74HCT74", "74xx:74LS74", DIP[14], "WRQ, MOUSE-READY"),
    "IC14": ("74LS04", "74xx:74LS04", DIP[14], "NMUX, MEMRD, MEMWR, TPB inverted"),
    "IC15": ("74LS05", "74xx:74LS05", DIP[14], "open collector: ATmega reset"),
    "IC16": ("74LS08", "74xx:74LS08", DIP[14], "GWR, RAM -OE, MOUSE-READY clear"),
    "IC17": ("74LS20", "74xx:74LS20", DIP[14], "RAM -WE, read latch enable"),
    "IC18": ("74LS32", "74xx:74LS32", DIP[14], "INP 7 at TPB"),
    "IC19": ("74HCT273", "74xx:74LS273", DIP[20], "control register, OUT 4 (-WR4 decoded on TEXT)"),
    "Y1":   ("16MHz", "Device:Crystal", "Crystal:Crystal_HC49-U_Vertical", "ATmega clock"),
    "J2":   ("MOUSE", LOC + ":MINIDIN6", LOC + ":MiniDIN6_MD-60SM", "PS/2 mouse (Same Sky MD-60SM)"),
    "J3":   ("FTDI", "Connector_Generic:Conn_01x06", FP_H % 6, "GND CTS VCC(nc) TXD RXD DTR: ATmega bootloader"),
    "J4":   ("FROM TEXT", "Connector_Generic:Conn_02x20_Odd_Even", "Connector_IDC:IDC-Header_2x20_P2.54mm_Vertical",
             "40-pin ribbon from the TEXT board"),
    "F1":   ("0.5A PTC", "Device:Polyfuse", "Fuse:Fuse_Bourns_MF-RHT050", "mouse +5 V"),
    "RN1":  ("10k x8", "Device:R_Network08", "Resistor_THT:R_Array_SIP9", "GD0-GD7 pull-ups (bussed, pin 1 common)"),
    "R1":   ("10k", "Device:R", FP_R, "ATmega reset pull-up"),
    "R2":   ("4.7k", "Device:R", FP_R, "RESETH pull-up"),
    "R3":   ("10k", "Device:R", FP_R, "LDDATA pull-up"),
    "R4":   ("4.7k", "Device:R", FP_R, "mouse clock pull-up"),
    "R5":   ("4.7k", "Device:R", FP_R, "mouse data pull-up"),
    "R6":   ("4.7k", "Device:R", FP_R, "PD7 strap: low = mouse mode (4.7k: a solid low against the AVR's 20-50k pull-up)"),
    "C21":  ("100n", "Device:C", FP_C, "FTDI DTR auto-reset"),
    "C22":  ("47u 16V", "Device:C_Polarized", FP_CP, "bulk"),
    "C23":  ("22p", "Device:C", FP_C, "Y1 load"),
    "C24":  ("22p", "Device:C", FP_C, "Y1 load"),
}
DECOUPLE = {"C%d" % n: "IC%d" % n for n in range(1, 20)}
DECOUPLE["C20"] = "IC11"                                    # the ATmega's AVCC
for cap, ic in DECOUPLE.items():
    PARTS[cap] = ("100n", "Device:C", FP_C, "%s bypass" % ic)

NETS = {}
def c(net, *pins):
    for p in pins:
        ref, pin = p.rsplit(".", 1)
        NETS.setdefault(net, []).append((ref, pin))

# ---- power -----------------------------------------------------------------------------------------------------------
POWER = {"IC1": (28, 14)}
for n in range(2, 20):
    if n == 11: continue
    POWER["IC%d" % n] = (20, 10) if n in (6, 7, 8, 10, 12, 19) else (16, 8) if n in (2, 3, 4, 5, 9) else (14, 7)
for ref, (v, g) in POWER.items():
    c("VCC", "%s.%d" % (ref, v)); c("GND", "%s.%d" % (ref, g))
c("VCC", "IC11.7", "IC11.20"); c("GND", "IC11.8", "IC11.22")
for cap in DECOUPLE:
    c("VCC", cap + ".1"); c("GND", cap + ".2")
c("VCC", "C22.1"); c("GND", "C22.2")

# ---- the bus (J1): only what GFX uses --------------------------------------------------------------------------------
BUS = {1: "VCC", 2: "D0", 3: "D1", 4: "D2", 5: "D3", 6: "D4", 7: "D5", 8: "D6", 9: "D7", 12: "TPB", 13: "-MRD",
       14: "-MRW", 15: "BA0", 16: "BA1", 17: "BA2", 18: "BA3", 19: "BA4", 20: "BA5", 27: "-RESET", 30: "GND"}
for pin, net in BUS.items():
    c(net, "J1.%d" % pin)

# ---- the ribbon (J4) -------------------------------------------------------------------------------------------------
for pin, sig in ribbon.PINS.items():
    c("VCC" if sig == "GFXPRES" else ribbon.GFX_NET.get(sig, sig), "J4.%d" % pin)

# ---- address muxes IC2-IC5 (S = NMUX: 1 = CPU on I1, 0 = display on I0) ----------------------------------------------
MUX = [("IC2", ("BA0", "MA0"), ("BA1", "MA1"), ("BA2", "MA2"), ("BA3", "MA3")),
       ("IC3", ("BA4", "MA4"), ("BA5", "MA5"), ("Y3", "MA6"), ("Y4", "MA7")),
       ("IC4", ("Y5", "MA8"), ("Y6", "MA9"), ("Y7", "MA10"), ("Y0", "RA0")),
       ("IC5", ("Y1", "RA1"), ("Y2", "RA2"), ("CPAGE", "DPAGE"), ("GND", "GND"))]
SECTIONS = ((3, 2, 4), (6, 5, 7), (10, 11, 9), (13, 14, 12))        # (I1 = CPU, I0 = display, Z) of sections a-d
for k, (ref, *sections) in enumerate(MUX):
    c("NMUX", ref + ".1"); c("GND", ref + ".15")
    for j, ((cpu, disp), (i1, i0, z)) in enumerate(zip(sections, SECTIONS)):
        c(cpu, "%s.%d" % (ref, i1)); c(disp, "%s.%d" % (ref, i0))
        if k * 4 + j < 15: c("GA%d" % (k * 4 + j), "%s.%d" % (ref, z))

# ---- graphics RAM IC1 -----------------------------------------------------------------------------------------------
for i, pin in enumerate((10, 9, 8, 7, 6, 5, 4, 3, 25, 24, 21, 23, 2, 26, 1)):
    c("GA%d" % i, "IC1.%d" % pin)
GDP = (11, 12, 13, 15, 16, 17, 18, 19)
for i, pin in enumerate(GDP):
    c("GD%d" % i, "IC1.%d" % pin, "RN1.%d" % (2 + i))
c("VCC", "RN1.1"); c("GND", "IC1.20"); c("RAMOE", "IC1.22"); c("GWE", "IC1.27")

# ---- read latch IC6, write buffer IC7, display latch IC8, shifter IC9 ------------------------------------------------
L374 = ((3, 2), (4, 5), (7, 6), (8, 9), (13, 12), (14, 15), (17, 16), (18, 19))       # (D, Q) of bits 0..7
for i, (d, q) in enumerate(L374):
    c("GD%d" % i, "IC6.%d" % d, "IC8.%d" % d); c("D%d" % i, "IC6.%d" % q); c("GL%d" % i, "IC8.%d" % q)
c("SRDOE", "IC6.1"); c("QC", "IC6.11"); c("GND", "IC8.1"); c("CHARCLOCK", "IC8.11")
for i, (a, y) in enumerate(((2, 18), (4, 16), (6, 14), (8, 12), (11, 9), (13, 7), (15, 5), (17, 3))):
    c("D%d" % i, "IC7.%d" % a); c("GD%d" % i, "IC7.%d" % y)
c("GWE", "IC7.1", "IC7.19")
for i, pin in enumerate((2, 3, 4, 5, 10, 11, 12, 14)):               # H (bit 7) shifts out first: leftmost dot
    c("GL%d" % i, "IC9.%d" % pin)
c("GND", "IC9.1", "IC9.6"); c("DOTCLK", "IC9.7"); c("VCC", "IC9.9"); c("GDOTRAW", "IC9.13"); c("CHARCLOCK", "IC9.15")
c("GDOTRAW", "IC16.12"); c("GFXON", "IC16.13"); c("GDOT", "IC16.11")        # IC16D: dots only while GFX-ON

# ---- control register IC19 (OUT 4): TEXT-OFF and XOR go back to TEXT, GFX-ON gates GDOT here ----------------------
c("-RESET", "IC19.1"); c("-WR4", "IC19.11")
for i, (d, q) in enumerate(L374):
    c("D%d" % i, "IC19.%d" % d)
    if i < 6: c(("TEXTOFF", "GFXON", "XORM", "DPAGE", "CPAGE", "MOUSEON")[i], "IC19.%d" % q)

# ---- Y register IC10 ------------------------------------------------------------------------------------------------
c("GND", "IC10.1"); c("-WR7", "IC10.11")
for i, (d, q) in enumerate(L374):
    c("D%d" % i, "IC10.%d" % d); c("Y%d" % i, "IC10.%d" % q)

# ---- slot logic: IC13A WRQ, IC14 inverters, IC16 ANDs, IC17 NAND4s --------------------------------------------------
c("-RESET", "IC13.1"); c("GWR", "IC13.2"); c("CHARCLOCK", "IC13.3"); c("VCC", "IC13.4"); c("WRQ", "IC13.5")
c("QCR", "IC14.1"); c("NMUX", "IC14.2"); c("-MRD", "IC14.3"); c("MEMRD", "IC14.4")
c("-MRW", "IC14.5"); c("MEMWR", "IC14.6"); c("TPB", "IC14.9"); c("TPBN", "IC14.8")
c("TEXTOFF", "IC14.11"); c("TEXTON", "IC14.10")                           # IC14E: TEXT-ON to TEXT (ribbon)
c("GND", "IC14.13")                                                        # IC14F spare
c("GSEL", "IC16.1"); c("MEMWR", "IC16.2"); c("GWR", "IC16.3")              # IC16A: a window write
c("WRQ", "IC16.4"); c("NMUX", "IC16.5"); c("RAMOE", "IC16.6")              # IC16B: RAM -OE off in a write slot
c("WRQ", "IC17.1"); c("NMUX", "IC17.2"); c("WEPH", "IC17.4"); c("GWR", "IC17.5"); c("GWE", "IC17.6")   # IC17A: -WE
c("GSEL", "IC17.9"); c("MEMRD", "IC17.10"); c("VCC", "IC17.12", "IC17.13"); c("SRDOE", "IC17.8")       # IC17B

# ---- mouse: IC11 ATmega328P, Y1, reset, FTDI, IC12 latch, MOUSE-READY (IC13B) ---------------------------------------
c("-RESET", "IC15.1"); c("RESETH", "IC15.2", "R2.1", "IC15.3"); c("VCC", "R2.2")   # IC15A, B: open collector
c("MRST", "IC11.1", "R1.1", "C21.2", "IC15.4"); c("VCC", "R1.2")
c("GND", "IC15.5", "IC15.9", "IC15.11", "IC15.13")                        # IC15C-F spare
c("FTX", "IC11.2", "J3.4"); c("FRX", "IC11.3", "J3.5"); c("FDTR", "J3.6", "C21.1"); c("GND", "J3.1", "J3.2")
c("MCLK", "IC11.4", "R4.1", "J2.5"); c("MDAT", "IC11.6", "R5.1", "J2.1"); c("VCC", "R4.2", "R5.2", "F1.1")
c("PS2VCC", "F1.2", "J2.4"); c("GND", "J2.3", "J2.S")
c("MSTRAP", "IC11.13", "R6.1"); c("GND", "R6.2")                          # PD7 low = mouse mode (TEXT: open = keyboard)
c("MOUSEON", "IC11.17")
c("XT1", "IC11.9", "Y1.1", "C23.1"); c("XT2", "IC11.10", "Y1.2", "C24.1"); c("GND", "C23.2", "C24.2")
c("LDDATA", "IC11.12", "IC12.11", "IC13.11", "R3.1"); c("VCC", "R3.2")
for i, pin in enumerate((23, 24, 25, 26, 27, 28, 14, 15)):
    c("MD%d" % i, "IC11.%d" % pin)
c("MREADY", "IC11.16")
c("-RD7", "IC12.1")
for i, (d, q) in enumerate(L374):
    c("MD%d" % i, "IC12.%d" % d); c("D%d" % i, "IC12.%d" % q)
c("VCC", "IC13.12", "IC13.10"); c("MCLR", "IC13.13"); c("MREADY", "IC13.9")
c("-RD7", "IC18.1"); c("TPBN", "IC18.2"); c("MCLRT", "IC18.3")             # IC18A: low while INP 7 and TPB
c("MCLRT", "IC16.9"); c("-RESET", "IC16.10"); c("MCLR", "IC16.8")          # IC16C: ... or -RESET
c("GND", "IC18.4", "IC18.5", "IC18.9", "IC18.10", "IC18.12", "IC18.13")   # spares

NO_CONNECT = {
    "J1": [10, 11, 21, 22, 23, 24, 25, 26, 28, 29], "IC5": [12], "IC13": [6, 8], "IC14": [12], "IC19": [16, 19], "IC15": [6, 8, 10, 12],
    "IC18": [6, 8, 11], "IC11": [5, 11, 18, 19, 21], "J2": [2, 6], "J3": [3],
}
NO_CONNECT = {r: [str(p) for p in ps] for r, ps in NO_CONNECT.items()}

BUY = {
    "IC1": "AS6C62256-55PCN (Alliance, 55 ns, 600-mil DIP-28); not a 300-mil 'skinny' 62256",
    "IC2": "74HCT157 (CMOS inputs: no load on the 1802's address lines)",
    "IC11": "ATmega328P-PU with the Arduino Uno bootloader burned (ISP) before fitting",
    "RN1": "10k x8 BUSSED, pin 1 common, 9-pin SIP (e.g. Bourns 4609X-101-103LF)",
    "J2": "Same Sky (CUI Devices) MD-60SM, date code after 2022-03-03",
    "J3": "1 x 6 pin header, 2.54 mm (an FTDI cable programs the ATmega)",
    "J4": "2 x 20 shrouded box header, 2.54 mm (the ribbon comes with the TEXT board's)",
    "F1": "Bourns MF-RHT050 (0.5 A hold, radial)", "Y1": "16 MHz, HC-49/U, 18-20 pF load",
    "C22": "47 uF electrolytic, 16 V or more, radial 6.3 mm, 2.5 mm pitch",
}
for _r in ("IC3", "IC4", "IC5"):
    BUY[_r] = BUY["IC2"]
for _r, _p in PARTS.items():
    if _p[0] == "100n": BUY.setdefault(_r, "ceramic X7R, 50 V, 0.1 in (2.54 mm) lead spacing")
    elif _p[0] == "22p": BUY.setdefault(_r, "ceramic C0G (NP0), 50 V, 0.1 in lead spacing")
    elif _r.startswith("R") and not _r.startswith("RN"): BUY.setdefault(_r, "1/4 W metal film, mounted standing")


def check():
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
            if (ref, p) in seen: probs.append("%s.%s is a no-connect and on %s" % (ref, p, seen[(ref, p)]))
    for ref, (val, lib_id, fp, note) in PARTS.items():
        for num in symlib.pins(lib_id):
            if (ref, num) not in seen and num not in NO_CONNECT.get(ref, []):
                probs.append("%s.%s (%s) unconnected" % (ref, num, symlib.pins(lib_id)[num].name))
    return probs


def pinmap():
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
