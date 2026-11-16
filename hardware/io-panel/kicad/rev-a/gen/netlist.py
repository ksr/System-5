# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-30
"""IO panel card Rev A: System-5's front panel on the 36-pin bus (design notes: ../DESIGN.md; the bus: docs/manual/bus.md).
The circuit is defined once here; make_schematic.py (and later make_board.py) use it.

Blocks:
  decode    U1 74HCT138 on N0-N2 (always enabled): PORT4_L is low through the execute cycle of an INP 4 / OUT 4 (N is 0
            otherwise). Y4_H and MRD_H (= -MRD inverted, high in an OUT) from U4.
  output    OUT 4: U2 74HCT374 clocked by OUTCLK = NAND(Y4_H, MRD_H, TPB) (U5A): it falls at TPB's rise and rises at TPB's
            fall, so the byte from memory is latched as TPB ends (as a CDP1852 in output mode does). Its outputs drive the
            eight LEDs (D1-D8 through R1-R8, sourcing) and the two TIL311s (U7 bits 7-4, U8 bits 3-0; latch strobe low =
            transparent, blanking low = on).
  input     INP 4: U3 74HCT244 puts the eight switches on D0-D7 while OE244_L is low:
            OE244_L = NAND(-MRD, ANY_H) with ANY_H = NAND(PORT4_L, DRIVE_L) = port 4 or this card's DMA (U6). DRIVE
            (U11A) is preset by REQ and cleared by -MRD low, so in a DMA IN the switches stay on the bus until -MRD falls
            in the next cycle, past the memory card's write (its WE is -MWR through a CD4050B, up to 140 ns late).
            -MRD is high in an INP and in a DMA IN cycle, low in IDLE and in every memory read, so the switches never
            fight a memory read. Eight SPDT toggles SW1-SW8 (Ken, 2026-10-30; M9040P, as on the YACC1 IO card): common = the bit, on = +5V = 1.
  INPUT     SW9 (push-button to GND), R9/C1 and U4's Schmitt inverter: INPUT_H, debounced, high while pressed.
            -EF1 (open collector, U9) low while pressed: B1 / BN1 in a program.
  LOAD      ELF-style toggles straight onto the open-collector bus lines: SW10 RUN/RESET grounds -RESET, SW11 LOAD grounds
            -PAUSE; LOAD mode = both low. LOAD_H = NOT(NAND(NOT -RESET, NOT -PAUSE)) (U4, U6) is high in LOAD mode,
            whichever card made it.
            One DMA request per press (U10): REQ (U10A) is clocked by INPUT_H rising with D = LOAD_H; it drives -DMAIN
            (open collector, U9). ACK (U10B) is clocked by -MRW rising (the DMA IN write has ended) with D = REQ; its
            !Q clears REQ. ACK is held clear while the button is up (!CLR = INPUT_H), so a held button loads one byte.
  Q         the Q LED (D9) sinks into U9 (open collector): on while Q is high.
  pull-ups  none on the bus lines (the CPU card and the bus Rev D have them); the SPDT toggles drive the bits both ways.
"""
BUS = {1: "+5V", 2: "D0", 3: "D1", 4: "D2", 5: "D3", 6: "D4", 7: "D5", 8: "D6", 9: "D7", 10: "Q", 11: "TPA", 12: "TPB",
       13: "-MRD", 14: "-MRW", 15: "A0", 16: "A1", 17: "A2", 18: "A3", 19: "A4", 20: "A5", 21: "A6", 22: "A7", 23: "-INT",
       24: "N2", 25: "-EF", 26: "-VMA", 27: "-RESET", 28: "N1", 29: "N0", 30: "GND"}
POS = ["-EF1", "-EF2", "-EF3"] + [BUS[i] for i in range(1, 31)] + ["-PAUSE", "-DMAIN", "SC0"]   # position 1..36
USED = {"+5V", "GND", "-EF1", "-RESET", "-PAUSE", "-DMAIN", "N0", "N1", "N2", "-MRD", "-MRW", "TPB", "Q",
        "D0", "D1", "D2", "D3", "D4", "D5", "D6", "D7"}

I, O, T, P, B, OC, NC = "input", "output", "tri_state", "power_in", "bidirectional", "open_collector", "no_connect"
_TYPES = {"I": I, "O": O, "T": T, "P": P, "B": B, "OC": OC, "N": NC}
def _p(spec):
    """'pin:name:type ...' -> {pin: (name, KiCad type)}; type is a code (I, O, T, P, B, OC, N)"""
    return {int(n): (nm, _TYPES.get(ty, ty)) for n, nm, ty in (s.split(":") for s in spec.split())}

# project symbols (one unit each, DIP pin order), pin names as the emulator's models read them (software/s5emu/s5emu/logic.py)
DIP14, DIP20 = "Package_DIP:DIP-14_W7.62mm", "Package_DIP:DIP-20_W7.62mm"
CHIPS = {
    "74HCT138": ("Package_DIP:DIP-16_W7.62mm", _p(
        "1:A:I 2:B:I 3:C:I 4:G2A:I 5:G2B:I 6:G1:I 7:Y7:O 8:GND:P 9:Y6:O 10:Y5:O 11:Y4:O 12:Y3:O 13:Y2:O 14:Y1:O 15:Y0:O 16:VCC:P")),
    "74HCT374": (DIP20, _p(
        "1:OC:I 2:1Q:T 3:1D:I 4:2D:I 5:2Q:T 6:3Q:T 7:3D:I 8:4D:I 9:4Q:T 10:GND:P 11:ENC:I 12:5Q:T 13:5D:I 14:6D:I "
        "15:6Q:T 16:7Q:T 17:7D:I 18:8D:I 19:8Q:T 20:VCC:P")),
    "74HCT244": (DIP20, _p(
        "1:1OE:I 2:1A1:I 3:2Y4:T 4:1A2:I 5:2Y3:T 6:1A3:I 7:2Y2:T 8:1A4:I 9:2Y1:T 10:GND:P 11:2A1:I 12:1Y4:T 13:2A2:I "
        "14:1Y3:T 15:2A3:I 16:1Y2:T 17:2A4:I 18:1Y1:T 19:2OE:I 20:VCC:P")),
    "74HCT14": (DIP14, _p("1:I:I 2:O:O 3:I:I 4:O:O 5:I:I 6:O:O 7:GND:P 8:O:O 9:I:I 10:O:O 11:I:I 12:O:O 13:I:I 14:VCC:P")),
    "74HCT10": (DIP14, _p("1:I0:I 2:I1:I 3:I0:I 4:I1:I 5:I2:I 6:O:O 7:GND:P 8:O:O 9:I0:I 10:I1:I 11:I2:I 12:O:O 13:I2:I 14:VCC:P")),
    "74HCT00": (DIP14, _p("1:I0:I 2:I1:I 3:O:O 4:I0:I 5:I1:I 6:O:O 7:GND:P 8:O:O 9:I0:I 10:I1:I 11:O:O 12:I0:I 13:I1:I 14:VCC:P")),
    "74HC05": (DIP14, _p("1:I:I 2:O:OC 3:I:I 4:O:OC 5:I:I 6:O:OC 7:GND:P 8:O:OC 9:I:I 10:O:OC 11:I:I 12:O:OC 13:I:I 14:VCC:P")),
    "74HCT74": (DIP14, _p("1:CLR:I 2:D:I 3:CLK:I 4:PRE:I 5:Q:O 6:~{Q}:O 7:GND:P 8:~{Q}:O 9:Q:O 10:PRE:I 11:CLK:I 12:D:I 13:CLR:I 14:VCC:P")),
    # TIL311 hex display with latch and decoder: pinout and footprint (HTIL311A, 0.3 in rows) as on Ken's built YACC1 IO card
    # (YACC1-D hardware/cards/io/kicad/v1.1: 3/2/13/12 = data A-D, 5 strobe and 8 blanking to GND, 1 LED supply to +5V)
    "TIL311": ("s5io:HTIL311A", _p(
        "1:LED_VCC:P 2:B:I 3:A:I 4:DP_L:P 5:STROBE:I 7:GND:P 8:BLANK:I 10:DP_R:P 12:D:I 13:C:I 14:VCC:P")),
}

R = "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal"
CAP = "s5io:C025-050X050"                     # 0.1 uF with 0.1" leads (Ken's rule)
PARTS = {}
def chip(ref, name, value, pins):
    PARTS[ref] = ("s5io:" + name, value, CHIPS[name][0], pins)

PARTS["J1"] = ("Connector_Generic:Conn_01x36", "System-5 bus (36)", "s5io:C36",
               {i + 1: (n if n in USED else None) for i, n in enumerate(POS)})
chip("U1", "74HCT138", "74HCT138", {1: "N0", 2: "N1", 3: "N2", 6: "+5V", 4: "GND", 5: "GND", 11: "PORT4_L",
     15: None, 14: None, 13: None, 12: None, 10: None, 9: None, 7: None, 8: "GND", 16: "+5V"})
chip("U2", "74HCT374", "74HCT374", {1: "GND", 11: "OUTCLK", 10: "GND", 20: "+5V",
     3: "D0", 2: "OUT0", 4: "D1", 5: "OUT1", 7: "D2", 6: "OUT2", 8: "D3", 9: "OUT3",
     13: "D4", 12: "OUT4", 14: "D5", 15: "OUT5", 17: "D6", 16: "OUT6", 18: "D7", 19: "OUT7"})
chip("U3", "74HCT244", "74HCT244", {1: "OE244_L", 19: "OE244_L", 10: "GND", 20: "+5V",
     2: "SW0", 18: "D0", 4: "SW1", 16: "D1", 6: "SW2", 14: "D2", 8: "SW3", 12: "D3",
     11: "SW4", 9: "D4", 13: "SW5", 7: "D5", 15: "SW6", 5: "D6", 17: "SW7", 3: "D7"})
chip("U4", "74HCT14", "74HCT14", {1: "INPUT_RC", 2: "INPUT_H", 3: "PORT4_L", 4: "Y4_H", 5: "-MRD", 6: "MRD_H",
     9: "-RESET", 8: "RESET_H", 11: "-PAUSE", 10: "PAUSE_H", 13: "LOAD_L", 12: "LOAD_H", 7: "GND", 14: "+5V"})
chip("U5", "74HCT10", "74HCT10", {1: "Y4_H", 2: "MRD_H", 13: "TPB", 12: "OUTCLK",
     3: "GND", 4: "GND", 5: "GND", 6: None, 9: "GND", 10: "GND", 11: "GND", 8: None, 7: "GND", 14: "+5V"})   # B, C spare
chip("U6", "74HCT00", "74HCT00", {1: "PORT4_L", 2: "DRIVE_L", 3: "ANY_H", 4: "-MRD", 5: "ANY_H", 6: "OE244_L",
     9: "RESET_H", 10: "PAUSE_H", 8: "LOAD_L", 12: "GND", 13: "GND", 11: None, 7: "GND", 14: "+5V"})          # D spare
chip("U9", "74HC05", "74HC05", {1: "INPUT_H", 2: "-EF1", 3: "REQ", 4: "-DMAIN", 5: "Q", 6: "LED_Q_K",
     9: "GND", 8: None, 11: "GND", 10: None, 13: "GND", 12: None, 7: "GND", 14: "+5V"})                       # 3 spare
chip("U10", "74HCT74", "74HCT74", {1: "ACK_L", 2: "LOAD_H", 3: "INPUT_H", 4: "+5V", 5: "REQ", 6: "REQ_L",    # A: REQ
     13: "INPUT_H", 12: "REQ", 11: "-MRW", 10: "+5V", 9: None, 8: "ACK_L", 7: "GND", 14: "+5V"})             # B: ACK
chip("U11", "74HCT74", "74HCT74", {4: "REQ_L", 1: "-MRD", 2: "GND", 3: "GND", 5: None, 6: "DRIVE_L",   # A: DRIVE
     13: "+5V", 12: "GND", 11: "GND", 10: "+5V", 9: None, 8: None, 7: "GND", 14: "+5V"})                     # B: spare
chip("U7", "TIL311", "TIL311", {1: "+5V", 3: "OUT4", 2: "OUT5", 13: "OUT6", 12: "OUT7", 5: "GND", 8: "GND",
     4: None, 10: None, 7: "GND", 14: "+5V"})                                                                 # bits 7-4
chip("U8", "TIL311", "TIL311", {1: "+5V", 3: "OUT0", 2: "OUT1", 13: "OUT2", 12: "OUT3", 5: "GND", 8: "GND",
     4: None, 10: None, 7: "GND", 14: "+5V"})                                                                 # bits 3-0

for k in range(8):                                                  # the output LEDs, sourced by the '374
    PARTS["D%d" % (k + 1)] = ("Device:LED", "BIT %d" % k, "LED_THT:LED_D3.0mm", {1: "GND", 2: "LED%d" % k})   # 1 K, 2 A
    PARTS["R%d" % (k + 1)] = ("Device:R", "1k", R, {1: "OUT%d" % k, 2: "LED%d" % k})
PARTS["D9"] = ("Device:LED", "Q", "LED_THT:LED_D3.0mm", {1: "LED_Q_K", 2: "LED_Q_A"})
PARTS["R10"] = ("Device:R", "1k", R, {1: "+5V", 2: "LED_Q_A"})
PARTS["D10"] = ("Device:LED", "PWR", "LED_THT:LED_D3.0mm", {1: "GND", 2: "LED_PWR"})
PARTS["R11"] = ("Device:R", "1k", R, {1: "+5V", 2: "LED_PWR"})
TOGGLE = "s5io:M9040P"           # Marquardt M9040P vertical SPDT toggle, the footprint from Ken's YACC1 IO card (M9040P)
for k in range(8):               # the data toggles, SPDT as on the YACC1 IO card: common = the bit, ends +5V and GND (no pull-ups)
    PARTS["SW%d" % (k + 1)] = ("Switch:SW_SPDT", "BIT %d" % k, TOGGLE, {1: "+5V", 2: "SW%d" % k, 3: "GND"})
PARTS["SW9"] = ("Switch:SW_Push", "INPUT", "Button_Switch_THT:SW_PUSH_6mm", {1: "INPUT_RC", 2: "GND"})
PARTS["R9"] = ("Device:R", "10k", R, {1: "+5V", 2: "INPUT_RC"})
PARTS["C1"] = ("Device:C", "470nF", "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P2.50mm", {1: "INPUT_RC", 2: "GND"})   # ~5 ms debounce
PARTS["SW10"] = ("Switch:SW_SPDT", "RUN/RESET", TOGGLE, {2: "GND", 1: "-RESET", 3: None})
PARTS["SW11"] = ("Switch:SW_SPDT", "LOAD", TOGGLE, {2: "GND", 1: "-PAUSE", 3: None})
PARTS["C2"] = ("Device:C_Polarized", "10uF", "Capacitor_THT:CP_Radial_D5.0mm_P2.00mm", {1: "+5V", 2: "GND"})
for k, u in enumerate(("U1", "U2", "U3", "U4", "U5", "U6", "U7", "U8", "U9", "U10", "U11")):
    PARTS["C%d" % (k + 3)] = ("Device:C", "0.1uF", CAP, {1: "+5V", 2: "GND"})
DOCS = {}
