# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-22
"""Front panel Rev A: System-5's hand controls and displays on a board that mounts as the front of a case, joined to
the IO panel card by one 50-way ribbon (design notes: ../DESIGN.md; the ribbon's pins: tools/s5panel.py; the bus lines
it carries and a boot reset: docs/manual/bus.md). The circuit is defined once here; make_schematic.py and
make_board.py use it.

Ken, 2026-11-22: "I want to add ability to have a front panel if system is ever put in a case. This will mean bringing
all IO switches, LEDs, and TIL311 signals out to a ribbon cable connector. It will also mean bring the CPU reset out
to a connector. Then create a front panel card that would mate with these 2 connectors and could be mounted as a
front panel"; "dont forget q line"; "and cpu status leds for mode"; "unless the IO panel via the bus can do what the
cpu card reset can do then we dont need line from cpu card all can come from io". His choices: one ribbon from the IO
card, no cable to the CPU card (a boot reset is made on the bus); a push-button RESET; landscape, about 7.5 x 3.5 in.

Blocks:
  ribbon    J1, a keyed 2x25 header on the back of the board: pin n = the IO panel card's J3 pin n.
  address   U1-U4 TIL311: ADR15-ADR0, the bus address as the IO card's two 74HCT573s hold it (strobe low = transparent,
            blanking low = on, as on the IO card).
  data      U5, U6 TIL311: OUT7-OUT0, the IO card's output port; LED1-LED8 show the same byte bit by bit, sourced by
            the IO card's 74HCT374 through RN1 (1k x8, isolated).
  toggles   SW1-SW8, the data byte: each switches its line SWn to +5V through RN2 (1k x8, bussed) or leaves it open;
            the IO card's RN3 (10k) pulls an open line down. Through 1k so that nothing can be shorted if the IO
            card's own toggles (SPDT between +5V and ground) are fitted as well: those then win.
  INPUT     SW11, a push-button to ground on INPUT_L: the IO card's R1 / C1 and Schmitt inverter debounce it, as its
            own button.
  RUN, LOAD SW9 RUN/RESET grounds -RESET, SW10 LOAD grounds -PAUSE: the bus lines themselves, open collector, as the
            IO card's own two toggles (either board's pulls the line).
  RESET     SW12, a push-button: a boot reset. R7 / C1 and a Schmitt inverter (U7D) debounce it (BTN_H, high while
            pressed); U10A and U10B (74HC03, open drain) then pull -RESET and -DMAIN low together, which is a boot
            reset on the bus: the CPU card clears its LOADED flag, so the machine starts in the EPROM (HBIOS) when
            the button is let go, 150 ms later (the CPU card's DS1813 holds -RESET that long, after -DMAIN has gone
            high again). Not while -PAUSE is low (PAUSE_N in both gates): -DMAIN low in LOAD mode would be a DMA
            request, so the button does nothing while LOAD is on.
  status    six LEDs, each from +5V through 1k, sunk by the line that lights it:
              PWR    to ground
              Q      Q_LED_L, the IO card's U5B
              PAUSE  PAUSE_N (U7E), low while -PAUSE is low
              RESET  RESET_N (U7F), low while -RESET is low (push-pull, both, as the CPU card's two sink into WAIT
                     and CLEAR. Two of U10's open-drain gates sank them at first, which is a sound circuit: the LED
                     and its 1k are the load. pcb-check's DESIGN line took them for outputs with no pull-up, because
                     it knows an LED by the word LED in its value and these carry their function; the pcb-check
                     session found that on 2026-11-22. The spare push-pull gates stay)
              ROM    ROM_LED_L, the IO card's U9D: lit while the CPU card's EPROM answers
              START FROM RAM   !Q of U9A, a copy of the CPU card's LOADED flag made from the same three bus lines by
                     the same two gates: set by LOAD mode (LOAD_L = NAND(RESET_H, PAUSE_H), U8A), cleared by a boot
                     reset (BOOT_L = NAND(RESET_H, DMAIN_H, PAUSE_N), U8B). The CPU card's power-on reset is a boot
                     reset, so the two agree from power-on.
  power     +5V and ground from the ribbon (four and eight wires); C2 bulk, one 0.1 uF (0.1 in leads) per chip.
  holes     H1-H4, M3, one in each corner.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "..", "tools"))
import s5panel                # the ribbon's pin map, shared with the IO panel card's J3

I, O, T, P, B, OC, NC = "input", "output", "tri_state", "power_in", "bidirectional", "open_collector", "no_connect"
_TYPES = {"I": I, "O": O, "T": T, "P": P, "B": B, "OC": OC, "N": NC}
def _p(spec):
    """'pin:name:type ...' -> {pin: (name, KiCad type)}; type is a code (I, O, T, P, B, OC, N)"""
    return {int(n): (nm, _TYPES.get(ty, ty)) for n, nm, ty in (s.split(":") for s in spec.split())}

# project symbols (one unit each, DIP pin order), pin names as the emulator's models read them (software/s5emu/s5emu/logic.py)
DIP14 = "Package_DIP:DIP-14_W7.62mm"
CHIPS = {
    "74HCT14": (DIP14, _p("1:I:I 2:O:O 3:I:I 4:O:O 5:I:I 6:O:O 7:GND:P 8:O:O 9:I:I 10:O:O 11:I:I 12:O:O 13:I:I 14:VCC:P")),
    "74HCT10": (DIP14, _p("1:I0:I 2:I1:I 3:I0:I 4:I1:I 5:I2:I 6:O:O 7:GND:P 8:O:O 9:I0:I 10:I1:I 11:I2:I 12:O:O 13:I2:I 14:VCC:P")),
    "74HCT74": (DIP14, _p("1:CLR:I 2:D:I 3:CLK:I 4:PRE:I 5:Q:O 6:~{Q}:O 7:GND:P 8:~{Q}:O 9:Q:O 10:PRE:I 11:CLK:I 12:D:I 13:CLR:I 14:VCC:P")),
    # 74HC03: quad 2-input NAND with open-drain outputs (the 74HC00's pins)
    "74HC03": (DIP14, _p("1:I0:I 2:I1:I 3:O:OC 4:I0:I 5:I1:I 6:O:OC 7:GND:P 8:O:OC 9:I0:I 10:I1:I 11:O:OC 12:I0:I 13:I1:I 14:VCC:P")),
    # TIL311 hex display with latch and decoder: pinout and footprint (HTIL311A) as on the IO panel card and Ken's YACC1
    # IO card: 3/2/13/12 = data A-D, 5 strobe and 8 blanking to GND, 1 LED supply to +5V
    "TIL311": ("s5fp:HTIL311A", _p(
        "1:LED_VCC:P 2:B:I 3:A:I 4:DP_L:P 5:STROBE:I 7:GND:P 8:BLANK:I 10:DP_R:P 12:D:I 13:C:I 14:VCC:P")),
}

R = "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal"
CAP = "s5fp:C025-050X050"                     # 0.1 uF with 0.1" leads (Ken's rule)
TOGGLE = "s5fp:M9040P"                        # Marquardt M9040P upright SPDT toggle, as on the IO panel card
PUSH = "Button_Switch_THT:SW_PUSH_6mm"
PARTS = {}
def chip(ref, name, value, pins):
    PARTS[ref] = ("s5fp:" + name, value, CHIPS[name][0], pins)

PARTS["J1"] = ("Connector_Generic:Conn_02x25_Odd_Even", "IO PANEL", "Connector_IDC:IDC-Header_2x25_P2.54mm_Vertical",
               s5panel.panel_pins())
# the displays: A15-A12 ... A3-A0, then the output port's two halves, left to right
DISPLAYS = (("U1", "ADR", 12), ("U2", "ADR", 8), ("U3", "ADR", 4), ("U4", "ADR", 0), ("U5", "OUT", 4), ("U6", "OUT", 0))
for ref, bus, n in DISPLAYS:
    chip(ref, "TIL311", "TIL311", {1: "+5V", 3: "%s%d" % (bus, n), 2: "%s%d" % (bus, n + 1), 13: "%s%d" % (bus, n + 2),
                                   12: "%s%d" % (bus, n + 3), 5: "GND", 8: "GND", 4: None, 10: None, 7: "GND", 14: "+5V"})
for k in range(8):                                                  # the bit LEDs, sourced by the IO card's '374
    PARTS["LED%d" % (k + 1)] = ("Device:LED", "BIT %d" % k, "LED_THT:LED_D3.0mm", {1: "GND", 2: "LEDA%d" % k})   # 1 K, 2 A
PARTS["RN1"] = ("Device:R_Pack08", "1k x8", "Package_DIP:DIP-16_W7.62mm",       # isolated: resistor k+1 = pins k+1 and 16-k
                dict([(k + 1, "OUT%d" % k) for k in range(8)] + [(16 - k, "LEDA%d" % k) for k in range(8)]))
for k in range(8):               # the data toggles: on = the line to +5V through RN2, off = open (the IO card pulls it down)
    PARTS["SW%d" % (k + 1)] = ("Switch:SW_SPDT", "BIT %d" % k, TOGGLE, {1: "SWP%d" % k, 2: "SW%d" % k, 3: None})
PARTS["RN2"] = ("Device:R_Network08", "1k", "Resistor_THT:R_Array_SIP9",
                dict([(1, "+5V")] + [(k + 2, "SWP%d" % k) for k in range(8)]))
PARTS["SW9"] = ("Switch:SW_SPDT", "RUN/RESET", TOGGLE, {2: "GND", 1: "-RESET", 3: None})
PARTS["SW10"] = ("Switch:SW_SPDT", "LOAD", TOGGLE, {2: "GND", 1: "-PAUSE", 3: None})
PARTS["SW11"] = ("Switch:SW_Push", "INPUT", PUSH, {1: "INPUT_L", 2: "GND"})
PARTS["SW12"] = ("Switch:SW_Push", "RESET", PUSH, {1: "BTN_RC", 2: "GND"})
PARTS["R7"] = ("Device:R", "10k", R, {1: "+5V", 2: "BTN_RC"})
PARTS["C1"] = ("Device:C", "470nF", "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P2.50mm", {1: "BTN_RC", 2: "GND"})   # ~5 ms, as the IO card's INPUT
chip("U7", "74HCT14", "74HCT14", {1: "-RESET", 2: "RESET_H", 3: "-PAUSE", 4: "PAUSE_H", 5: "-DMAIN", 6: "DMAIN_H",
     9: "BTN_RC", 8: "BTN_H", 11: "PAUSE_H", 10: "PAUSE_N", 13: "RESET_H", 12: "RESET_N", 7: "GND", 14: "+5V"})
chip("U8", "74HCT10", "74HCT10", {1: "RESET_H", 2: "PAUSE_H", 13: "+5V", 12: "LOAD_L",                         # A: LOAD mode
     3: "RESET_H", 4: "DMAIN_H", 5: "PAUSE_N", 6: "BOOT_L",                                                    # B: a boot reset
     9: "GND", 10: "GND", 11: "GND", 8: None, 7: "GND", 14: "+5V"})                                            # C: spare
chip("U9", "74HCT74", "74HCT74", {1: "BOOT_L", 2: "GND", 3: "GND", 4: "LOAD_L", 5: None, 6: "LED_RAM_K",       # A: LOADED's copy
     13: "+5V", 12: "GND", 11: "GND", 10: "+5V", 9: None, 8: None, 7: "GND", 14: "+5V"})                       # B: spare
chip("U10", "74HC03", "74HC03", {1: "BTN_H", 2: "PAUSE_N", 3: "-RESET",          # A, B: the RESET button's boot reset,
     4: "BTN_H", 5: "PAUSE_N", 6: "-DMAIN",                                      #       not while -PAUSE is low
     9: "GND", 10: "GND", 8: None, 12: "GND", 13: "GND", 11: None, 7: "GND", 14: "+5V"})   # C, D: spare
# the status LEDs: LEDn 1 = K (the sink), 2 = A; each with a 1k from +5V
STATUS = (("LED9", "PWR", "GND"), ("LED10", "Q", "Q_LED_L"), ("LED11", "PAUSE", "PAUSE_N"),
          ("LED12", "RESET", "RESET_N"), ("LED13", "ROM", "ROM_LED_L"), ("LED14", "RAM", "LED_RAM_K"))
for k, (ref, label, sink) in enumerate(STATUS):
    PARTS[ref] = ("Device:LED", label, "LED_THT:LED_D3.0mm", {1: sink, 2: "LED_%s_A" % label})
    PARTS["R%d" % (k + 1)] = ("Device:R", "1k", R, {1: "+5V", 2: "LED_%s_A" % label})
PARTS["C2"] = ("Device:C_Polarized", "47uF", "Capacitor_THT:CP_Radial_D6.3mm_P2.50mm", {1: "+5V", 2: "GND"})
BYPASSED = ("U1", "U2", "U3", "U4", "U5", "U6", "U7", "U8", "U9", "U10")        # C3 ... C12, in this order
for k, u in enumerate(BYPASSED):
    PARTS["C%d" % (k + 3)] = ("Device:C", "0.1uF", CAP, {1: "+5V", 2: "GND"})
for k in range(1, 5):                                                             # one M3 hole in each corner
    PARTS["H%d" % k] = ("Mechanical:MountingHole", "M3", "MountingHole:MountingHole_3.2mm_M3", {})
DOCS = {}
