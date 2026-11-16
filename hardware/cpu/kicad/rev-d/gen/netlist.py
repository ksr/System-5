# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-30
"""CPU Rev D: the System-5 CPU card for the 36-pin bus (design notes: ../DESIGN.md; the bus: docs/manual/bus.md).
The circuit is defined once here; make_schematic.py (and later make_board.py) use it.

Blocks:
  CPU       U1 CDP1802ACE, unbuffered onto the bus as on Rev A (D0-D7, A0-A7, TPA, TPB, -MRD, -MRW, Q, N0-N2)
  clock     X1 4 MHz oscillator, U4A divides by 2 -> CLK_INT (2 MHz); JP1 picks INT or EXT for the 1802's CLOCK;
            EXT_CLK comes in on J2 (the debug header, a jumper wire from a debug board), pulled down by R2, through U7A
            (a Schmitt inverter: an external clock's polarity does not matter)
  control   no run latches: CLEAR = -RESET and WAIT = -PAUSE, each through two Schmitt inverters (U7). The four 1802
            modes follow directly: reset (-RESET low), run, pause (-PAUSE low), load (both low). DMA_IN = -DMAIN, the same.
  reset     U10 DS1813 (power-on reset and push-button debounce, open drain, no watchdog: Rev A's CM1232 watchdog, fed by
            TPA, would reset a paused or stepped machine) on the bus -RESET. SW1 RESET/RUN: RESET grounds SW_RST, which
            pulls -RESET through D1 (the DS1813 then holds it 150 ms after release) and clears LOADED.
  boot      U2 latches A8-A15 on TPA (a 74HCT373, transparent while TPA is high: timing finding T1 fixed). U3 2732 at
            F000-FFFF. Boot map (the EPROM at every address, -VMA high) after a reset, until the first access with A15
            high (U4B, as Rev A built) -- unless LOADED (U8A) is set: LOAD mode sets it, and SW1 or power-on clears it,
            so a program loaded at 0000 runs from RAM after LOAD -> RESET -> RUN (ELF-style), while SW1 boots HBIOS.
            WIN_L = A12.A13.A14.A15 (U6A); -VMA = ROM_SEL_H = BOOTMAP + WIN (U5B); the EPROM's !CE = ROM_SEL_L.
  flags     JP2 routes -EF1, -EF2, -EF3, -EF straight across to EF1-EF4; JP3 puts -EF on EF3 for the old IO card
            (with JP2's EF3 and EF4 jumpers off). RN2 holds unjumpered EF inputs high.
  debug     J2: EXT_CLK, GND, CLOCK, SC0, SC1, GND. SC0 is also driven onto the bus (position 36), through U9D/U9E.
  pull-ups  RN1 10k on -RESET, -INT, -PAUSE, -DMAIN, -EF, -EF1-3 (the 2009 backplane has none; the bus Rev D's add to them)
  LEDs      PWR, Q, PAUSE (WAIT low), RESET (CLEAR low), ROM (the EPROM selected)
"""
# --- the 36-pin bus, by socket position (as the bus Rev D, ../../../bus/kicad/rev-d/gen/netlist.py) ---
BUS = {1: "+5V", 2: "D0", 3: "D1", 4: "D2", 5: "D3", 6: "D4", 7: "D5", 8: "D6", 9: "D7", 10: "Q", 11: "TPA", 12: "TPB",
       13: "-MRD", 14: "-MRW", 15: "A0", 16: "A1", 17: "A2", 18: "A3", 19: "A4", 20: "A5", 21: "A6", 22: "A7", 23: "-INT",
       24: "N2", 25: "-EF", 26: "-VMA", 27: "-RESET", 28: "N1", 29: "N0", 30: "GND"}
POS = ["-EF1", "-EF2", "-EF3"] + [BUS[i] for i in range(1, 31)] + ["-PAUSE", "-DMAIN", "SC0"]   # position 1..36

# --- project symbols (one unit each, DIP pin order): name: (footprint, {pin: (name, type)}) ---
# types: KiCad pin electrical types. Pinouts from the data sheets (74HCT: TI; 2732: Intel/Fujitsu; DS1813: Maxim TO-92).
I, O, T, P, B, OC, NC = "input", "output", "tri_state", "power_in", "bidirectional", "open_collector", "no_connect"
_TYPES = {"I": I, "O": O, "T": T, "P": P, "B": B, "OC": OC, "N": NC}
def _p(spec):
    """'pin:name:type ...' -> {pin: (name, KiCad type)}; type is a code (I, O, T, P, B, OC, N) or a full KiCad type"""
    return {int(n): (nm, _TYPES.get(ty, ty)) for n, nm, ty in (s.split(":") for s in spec.split())}
CHIPS = {      # pin names as the emulator's models read them (software/s5emu/s5emu/logic.py, from the 2005 Eagle symbols)
    "74HCT373": ("Package_DIP:DIP-20_W7.62mm", _p(
        "1:OC:I 2:1Q:T 3:1D:I 4:2D:I 5:2Q:T 6:3Q:T 7:3D:I 8:4D:I 9:4Q:T 10:GND:P 11:ENC:I 12:5Q:T 13:5D:I 14:6D:I "
        "15:6Q:T 16:7Q:T 17:7D:I 18:8D:I 19:8Q:T 20:VCC:P")),
    "2732": ("Package_DIP:DIP-24_W15.24mm", _p(
        ("1:A7:I 2:A6:I 3:A5:I 4:A4:I 5:A3:I 6:A2:I 7:A1:I 8:A0:I 9:O0:T 10:O1:T 11:O2:T 12:GND:P 13:O3:T 14:O4:T 15:O5:T "
         "16:O6:T 17:O7:T 18:~{CE}:I 19:A10:I 20:~{OE}/VPP:I 21:A11:I 22:A9:I 23:A8:I 24:VCC:P"))),
    "74HCT74": ("Package_DIP:DIP-14_W7.62mm", _p(
        ("1:CLR:I 2:D:I 3:CLK:I 4:PRE:I 5:Q:O 6:~{Q}:O 7:GND:P 8:~{Q}:O 9:Q:O 10:PRE:I 11:CLK:I "
         "12:D:I 13:CLR:I 14:VCC:P"))),
    "74HCT00": ("Package_DIP:DIP-14_W7.62mm", _p(
        ("1:I0:I 2:I1:I 3:O:O 4:I0:I 5:I1:I 6:O:O 7:GND:P 8:O:O 9:I0:I 10:I1:I 11:O:O 12:I0:I 13:I1:I 14:VCC:P"))),
    "74HCT20": ("Package_DIP:DIP-14_W7.62mm", _p(
        ("1:I0:I 2:I1:I 4:I2:I 5:I3:I 6:O:O 7:GND:P 8:O:O 9:I0:I 10:I1:I 12:I2:I 13:I3:I 14:VCC:P"))),
    "74HCT14": ("Package_DIP:DIP-14_W7.62mm", _p(
        ("1:I:I 2:O:O 3:I:I 4:O:O 5:I:I 6:O:O 7:GND:P 8:O:O 9:I:I 10:O:O 11:I:I 12:O:O 13:I:I 14:VCC:P"))),
    "DS1813": ("Package_TO_SOT_THT:TO-92_Inline", _p("1:~{RST}:%s 2:VCC:%s 3:GND:%s" % (OC, P, P))),
    "OSC_DIP8": ("Oscillator:Oscillator_DIP-8", _p("1:EN:%s 4:GND:%s 5:OUT:%s 8:VCC:%s" % (I, P, O, P))),
}

R = "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal"
CAP = "s5cpu:C025-050X050"                    # 0.1 uF with 0.1" leads (Ken's rule; the memory card's footprint)
DIP14 = "Package_DIP:DIP-14_W7.62mm"

PARTS = {}      # ref: (lib_id, value, footprint, {pin: net})
def chip(ref, name, value, pins):
    PARTS[ref] = ("s5cpu:" + name, value, CHIPS[name][0], pins)

PARTS["U1"] = ("CPU:CDP1802ACE", "CDP1802ACE", "Package_DIP:DIP-40_W15.24mm", {
    1: "CLOCK", 2: "WAIT", 3: "CLEAR", 4: "Q", 5: "SC1", 6: "SC0_RAW", 7: "-MRD",
    8: "D7", 9: "D6", 10: "D5", 11: "D4", 12: "D3", 13: "D2", 14: "D1", 15: "D0", 16: "+5V", 17: "N2", 18: "N1", 19: "N0",
    20: "GND", 21: "CPU_EF4", 22: "CPU_EF3", 23: "CPU_EF2", 24: "CPU_EF1",
    25: "A0", 26: "A1", 27: "A2", 28: "A3", 29: "A4", 30: "A5", 31: "A6", 32: "A7",
    33: "TPB", 34: "TPA", 35: "-MRW", 36: "-INT", 37: "+5V", 38: "DMA_IN", 39: None, 40: "+5V"})   # 37 DMA OUT unused
chip("U2", "74HCT373", "74HCT373", {1: "GND", 3: "A0", 2: "LA8", 4: "A1", 5: "LA9", 7: "A2", 6: "LA10", 8: "A3", 9: "LA11",
     13: "A4", 12: "LA12", 14: "A5", 15: "LA13", 17: "A6", 16: "LA14", 18: "A7", 19: "LA15", 11: "TPA", 10: "GND", 20: "+5V"})
chip("U3", "2732", "2732 HBIOS", {8: "A0", 7: "A1", 6: "A2", 5: "A3", 4: "A4", 3: "A5", 2: "A6", 1: "A7",
     23: "LA8", 22: "LA9", 19: "LA10", 21: "LA11", 9: "D0", 10: "D1", 11: "D2", 13: "D3", 14: "D4", 15: "D5", 16: "D6",
     17: "D7", 18: "ROM_SEL_L", 20: "-MRD", 12: "GND", 24: "+5V"})
chip("U4", "74HCT74", "74HCT74", {1: "+5V", 2: "CLKDIV_L", 3: "OSC", 4: "+5V", 5: "CLK_INT", 6: "CLKDIV_L",   # A: OSC / 2
     13: "CLEAR", 12: "+5V", 11: "LA15", 10: "+5V", 9: None, 8: "BOOT_PEND", 7: "GND", 14: "+5V"})        # B: boot flip-flop
chip("U5", "74HCT00", "74HCT00", {1: "BOOT_PEND", 2: "NOT_LOADED", 3: "BOOTMAP_L",
     4: "BOOTMAP_L", 5: "WIN_L", 6: "-VMA",                      # -VMA = ROM_SEL_H: high while the EPROM answers
     9: "-VMA", 10: "-VMA", 8: "ROM_SEL_L",
     12: "RST_H", 13: "PAUSE_H", 11: "LOAD_L", 7: "GND", 14: "+5V"})
chip("U6", "74HCT20", "74HCT20", {1: "LA12", 2: "LA13", 4: "LA14", 5: "LA15", 6: "WIN_L",
     9: "+5V", 10: "+5V", 12: "+5V", 13: "+5V", 8: None, 7: "GND", 14: "+5V"})
chip("U7", "74HCT14", "74HCT14", {1: "EXT_CLK", 2: "CLK_EXT", 3: "-RESET", 4: "RST_H", 5: "RST_H", 6: "CLEAR",
     9: "-PAUSE", 8: "PAUSE_H", 11: "PAUSE_H", 10: "WAIT", 13: "-DMAIN", 12: "DMAIN_H", 7: "GND", 14: "+5V"})
chip("U8", "74HCT74", "74HCT74", {1: "POR_L", 2: "GND", 3: "GND", 4: "LOAD_L", 5: None, 6: "NOT_LOADED",   # A: LOADED
     13: "+5V", 12: "GND", 11: "GND", 10: "+5V", 9: None, 8: None, 7: "GND", 14: "+5V"})                   # B: spare
chip("U9", "74HCT14", "74HCT14", {1: "DMAIN_H", 2: "DMA_IN", 3: "SW_RST", 4: "SWRST_H", 5: "SWRST_H", 6: "POR_L",
     9: "SC0_RAW", 8: "SC0_L", 11: "SC0_L", 10: "SC0", 13: "Q", 12: "Q_L", 7: "GND", 14: "+5V"})
chip("U10", "DS1813", "DS1813-10", {1: "-RESET", 2: "+5V", 3: "GND"})
chip("X1", "OSC_DIP8", "4MHz", {1: "+5V", 4: "GND", 5: "OSC", 8: "+5V"})

PARTS["J1"] = ("Connector_Generic:Conn_01x36", "System-5 bus (36)", "s5cpu:C36",
               {i + 1: n for i, n in enumerate(POS)})
PARTS["J2"] = ("Connector_Generic:Conn_01x06", "DEBUG", "Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical",
               {1: "EXT_CLK", 2: "GND", 3: "CLOCK", 4: "SC0", 5: "SC1", 6: "GND"})
PARTS["JP1"] = ("Connector_Generic:Conn_01x03", "CLK INT/EXT", "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical",
                {1: "CLK_INT", 2: "CLOCK", 3: "CLK_EXT"})
PARTS["JP2"] = ("Connector_Generic:Conn_02x04_Odd_Even", "EF", "Connector_PinHeader_2.54mm:PinHeader_2x04_P2.54mm_Vertical",
                {1: "-EF1", 2: "CPU_EF1", 3: "-EF2", 4: "CPU_EF2", 5: "-EF3", 6: "CPU_EF3", 7: "-EF", 8: "CPU_EF4"})
PARTS["JP3"] = ("Connector_Generic:Conn_01x02", "-EF TO EF3", "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
                {1: "-EF", 2: "CPU_EF3"})
PARTS["SW1"] = ("Switch:SW_SPDT", "RESET/RUN", "s5cpu:SW_Toggle_SPDT_E-Switch_100_M6", {2: "GND", 1: "SW_RST", 3: None})  # 1 RESET, 3 RUN
PARTS["D1"] = ("Device:D_Schottky", "BAT85", "Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal", {1: "SW_RST", 2: "-RESET"})   # 1 K, 2 A
PARTS["R1"] = ("Device:R", "10k", R, {1: "+5V", 2: "SW_RST"})
PARTS["C12"] = ("Device:C", "1uF", "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P2.50mm", {1: "SW_RST", 2: "GND"})  # power-on clear of LOADED
PARTS["R2"] = ("Device:R", "10k", R, {1: "EXT_CLK", 2: "GND"})
PARTS["RN1"] = ("Device:R_Network08", "10k", "Resistor_THT:R_Array_SIP9",
                {1: "+5V", 2: "-RESET", 3: "-INT", 4: "-PAUSE", 5: "-DMAIN", 6: "-EF", 7: "-EF1", 8: "-EF2", 9: "-EF3"})
PARTS["RN2"] = ("Device:R_Network04", "10k", "Resistor_THT:R_Array_SIP5",
                {1: "+5V", 2: "CPU_EF1", 3: "CPU_EF2", 4: "CPU_EF3", 5: "CPU_EF4"})
for ref, label, sink, k in (("D2", "PWR", "GND", 3), ("D3", "Q", "Q_L", 4), ("D4", "PAUSE", "WAIT", 5),
                            ("D5", "RESET", "CLEAR", 6), ("D6", "ROM", "ROM_SEL_L", 7)):
    PARTS[ref] = ("Device:LED", label, "LED_THT:LED_D3.0mm", {1: sink, 2: "LED_" + label})          # 1 = K, 2 = A
    PARTS["R%d" % k] = ("Device:R", "1k", R, {1: "+5V", 2: "LED_" + label})
PARTS["C1"] = ("Device:C_Polarized", "10uF", "Capacitor_THT:CP_Radial_D5.0mm_P2.00mm", {1: "+5V", 2: "GND"})
for k, u in enumerate(("U1", "U2", "U3", "U4", "U5", "U6", "U7", "U8", "U9", "X1")):
    PARTS["C%d" % (k + 2)] = ("Device:C", "0.1uF", CAP, {1: "+5V", 2: "GND"})                        # one per chip
DOCS = {}
