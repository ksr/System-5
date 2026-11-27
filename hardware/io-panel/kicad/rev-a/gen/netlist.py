# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-30
"""IO panel card Rev A: System-5's front panel on the 36-pin bus (design notes: ../DESIGN.md; the bus: docs/manual/bus.md).
The circuit is defined once here; make_schematic.py (and later make_board.py) use it.

Blocks:
  decode    U1 74HCT138 on N0-N2 (always enabled): Y1_L-Y7_L, each low through the execute cycle of an INP n / OUT n (N
            is 0 otherwise), to the jumper blocks JP1 IN PORT and JP2 OUT PORT: a jumper across row n makes port n the
            card's input or output port (Ken, 2026-11-17; it was port 4, fixed). RN1 holds PORTIN_L / PORTOUT_L high
            with no jumper (no port). POUT_H (from PORTOUT_L) and MRD_H (= -MRD inverted, high in an OUT) from U4.
  output    OUT n: U2 74HCT374 clocked by OUTCLK = NAND(POUT_H, MRD_H, TPB) (U5A): it falls at TPB's rise and rises at TPB's
            fall, so the byte from memory is latched as TPB ends (as a CDP1852 in output mode does). Its outputs drive the
            eight LEDs (LED1-LED8 through RN2, an isolated 1k x 8 DIP-16 array, sourcing; Ken, 2026-11-18) and the two
            TIL311s (U7 bits 7-4, U8 bits 3-0; latch strobe low = transparent, blanking low = on).
  address   the 16-bit address on the bus (Ken, 2026-11-18: "add 4 TIL-311 to IO card that shows current address being put
            on bus, it will help during load and also debugging"). The 1802 puts the high byte on A0-A7 during TPA and
            the low byte after it: U18 74HCT573 holds the high byte (LE = TPA: it follows A0-A7 while TPA is high and
            keeps them as TPA falls, as the CPU card's own 74HCT373 does), U19 74HCT573 the low byte (LE = TPB, at the end
            of the cycle). Their outputs ADR15-ADR8 and ADR7-ADR0 drive four TIL311s (U14 A15-A12, U15 A11-A8, U16 A7-A4,
            U17 A3-A0; strobe low, so transparent, as U7 and U8). The display shows the last machine cycle's address and
            holds it while the clock is stopped; in LOAD mode the 1802 idles on R0, so it shows where the next byte
            goes. The latches keep the bus to HCT inputs: the 1802 drives A0-A7 straight from its pins on CPU Rev D,
            too weakly for the TIL311s' TTL inputs.
  input     INP n: U3 74HCT244 puts the eight switches on D0-D7 while OE244_L is low:
            OE244_L = NAND(-MRD, ANY_H) with ANY_H = NAND(PORTIN_L, DRVL_L) = the IN port or this card's DMA (U6);
            DRVL_L = NAND(DRIVE, LOAD_H) (U9D, open drain, R6), so a DMA drives only in LOAD mode. DRIVE
            (U11A) is preset by REQ and cleared by -MRD low, so in a DMA IN the switches stay on the bus until -MRD falls
            in the next cycle, past the memory card's write (its WE is -MWR through a CD4050B, up to 140 ns late).
            -MRD is high in an INP and in a DMA IN cycle, low in IDLE and in every memory read, so the switches never
            fight a memory read. Eight SPDT toggles SW1-SW8 (Ken, 2026-10-30; M9040P, as on the YACC1 IO card): common = the bit, on = +5V = 1.
  INPUT     SW9 (push-button to GND), R1/C1 and U4's Schmitt inverter: INPUT_H, debounced, high while pressed.
            EFOUT (open collector, U9) low while pressed, to the EF block JP3: a jumper across a row puts it on -EF1, -EF2,
            -EF3 or -EF (Ken, 2026-11-17; it was -EF1), B1 / BN1 ... in a program; RN1 holds EFOUT high with no jumper.
  LOAD      ELF-style toggles straight onto the open-collector bus lines: SW10 RUN/RESET grounds -RESET, SW11 LOAD grounds
            -PAUSE; LOAD mode = both low. LOAD_H = NOT(NAND(NOT -RESET, NOT -PAUSE)) (U4, U6) is high in LOAD mode,
            whichever card made it.
            One DMA request per press (U10): REQ (U10A) is clocked by INPUT_H rising with D = LOAD_H. The bus line is
            -DMAIN = NAND(REQ, SC0) (U9B, open drain): low while REQ is set and the 1802 is not yet in the DMA cycle.
            The 1802 samples its DMA input at clock 7 of every cycle (data sheet, figure 4), before -MWR rises, so
            the request has to be gone early in the DMA cycle itself or a second one follows (figure 12): SC0 falls
            as that cycle (S2) starts and lets -DMAIN go, as the COSMAC ELF does with SC1. (Until 2026-11-22 -DMAIN
            was REQ alone, which lasted until -MWR rose: two bytes for a press on a real 1802. The emulator ran one
            cycle a press and did not show it.) ACK (U10B) is clocked by -MRW rising (the DMA IN write has ended)
            with D = REQ; its !Q clears REQ, which is over well before SC0 rises again. ACK is held clear while the
            button is up (!CLR = INPUT_H), so a held button loads one byte. RN1 holds SC0 high with no CPU card.
            REQ's clear is REQCLR_L (Ken, 2026-11-25: "fix both power-up faults in one new route"): low while ACK is set
            (D1, a Schottky, its cathode on ACK_L) and outside LOAD mode (U9C, open drain, NAND(LOAD_L, LOAD_L)), with R5.
            Until then ACK_L alone cleared REQ, which had no state at power-up: up as 1 it set DRIVE in every write
            cycle, and the toggles fought the 1802 for the bus. DRIVE's LOAD gate (U9D) does the same for DRIVE up as 1.
  Q         the Q LED (LED9) sinks into U5B = NAND(Q, 1, 1), push-pull: on while Q is high (it was U9, open collector,
            which pcb-check took for an output with no pull-up; the LED and its resistor were its load, and the
            check knows an LED only by the word LED in its value, as the pcb-check session found on 2026-11-22).
  panel     J3 (Ken, 2026-11-22: "I want to add ability to have a front panel if system is ever put in a case. This
            will mean bringing all IO switches, LEDs, and TIL311 signals out to a ribbon cable connector"; "dont
            forget q line"; "and cpu status leds for mode"): a keyed 2x25 header at the front edge, a straight 50-way
            ribbon to the front panel card (hardware/front-panel), pin n to pin n; the one pin map for both boards
            is tools/s5panel.py. On it: ADR15-ADR0 and OUT7-OUT0 (the displays and bit LEDs), SW7-SW0 (the data
            toggles), LED_Q_K (the Q LED), ROM_LED_L, INPUT_RC (the INPUT button), and the bus lines -RESET, -PAUSE
            and -DMAIN themselves (RUN, LOAD, the RESET button, the mode LEDs), with +5V and ground.
            ROM_LED_L = NAND(-VMA, -VMA) (U23D, open drain): low while the CPU card's EPROM answers (-VMA high), to
            sink the front panel's ROM LED. RN3 (10k x8) pulls SW0-SW7 down: the front panel's toggles switch each
            line to +5V through 1k and leave it open otherwise, and the '244's inputs do not float with neither
            the card's own toggles nor a front panel fitted. This card's own toggles are SPDT between +5V and
            ground: fitted, they win over the front panel's (nothing is harmed); a card built for a front panel
            leaves SW1-SW8 out. RUN, LOAD and INPUT on the two boards work together (either pulls its line low).
  RESET     SW12 (Ken, 2026-11-23: "the IO card also needs a reset in case front panel is not installed"): a
            push-button for a boot reset, as the front panel's. Pressed, it puts +5V on BTN_H (R4 holds it low
            otherwise), and U23 (74HCT03, open drain) pulls -RESET (U23A) and -DMAIN (U23B) low together: the CPU card
            clears LOADED, so the machine starts in the EPROM when the button is let go (docs/manual/bus.md). Both
            gates take the bus line -PAUSE as their other input, so the button does nothing while -PAUSE is low: in
            LOAD mode a low -DMAIN would be a DMA request. No debounce: a bouncing boot reset is a boot reset, and
            the CPU card's DS1813 holds -RESET for 150 ms after the last release. (RUN/RESET, the toggle, is another
            thing: it holds -RESET alone, a plain reset, which starts again whatever ran before.)
  rtc       U13 DS12885+ (Ken, 2026-11-18): clock, calendar, 114 bytes of battery-backed RAM; Intel timing (MOT low), CS
            tied low, RESET tied high (the datasheet's typical connection); Y1 32.768 kHz (6 pF), BT1 a CR2032 in a flat
            holder (Keystone 103: an upright one stands taller than the room between cards), straight on VBAT. Its two
            ports are a jumper-picked pair, JP4: the address register on 2, 4 or 6, the data on 3, 5 or 7 (set to 6 and
            7). OSTB_L = NAND(MRD_H, TPB) (U6D) is low in TPB of every memory read, so of every OUT. An OUT to the address
            port strobes AS = NOR(its select, OSTB_L) (U12A): the address is latched as TPB ends. An OUT to the data port
            writes it: R/W = NOT NOR(its select, OSTB_L) (U12B, U12C); an INP of it reads it: DS = NOT NOR(its select,
            MRD_H) (U12D, U5C), low through the whole INP. IRQ (open drain) reaches the bus -INT through JP4's last row
            (off). RN1 holds the jumper selects and IRQ high.
  serial    (Ken, 2026-11-20: "for io card create a test branch for adding serial io and db 9 to board, ok to lengthen
            board"; his choices: a 16C550 as on his YACC1 I/O card, the DE-9 on the side edge. Drawn on the branch
            io-panel-serial and merged the same day.) U20 16C550 UART (DIP-40: XR16C550, TL16C550C, PC16550D) with its own clock X1, a 1.8432 MHz can
            (divisor 12 = 9600 baud, 3 = 38400), -BAUDOUT to RCLK; U21 MAX232 with four 1 uF capacitors; J2 a DE-9
            socket at the side edge, 2 and 3 through the null-modem block JP6 (1-3 and 2-4: the card sends on pin 2;
            3-5 and 4-6: on pin 3), 5 = GND. The modem inputs are tied off (-CTS, -DSR, -DCD, -RI high), as on the YACC1 card.
            It shares the RTC's port pair (JP4, set to 6 and 7), told apart by bit 7 of the byte written to the address
            port: U22 (74HCT573, LE = RTC_AS, so it holds that byte as the DS12885 does, as TPB ends) keeps bit 7 as
            SEL_UART and bits 2-0 as UA2-UA0. 00-7F: the DS12885's register, as before (its CS, tied low until now, is
            SEL_UART: low = selected). 80-87: the UART's register 0-7 (its CS0 = SEL_UART). An OUT to the data port
            writes the chip selected (the UART's WR = RTC_WR, high in TPB of that OUT); an INP of it reads it.
            The UART's read strobe is not the RTC's. The 1802 puts N on the bus from the start of an OUT's cycle but
            takes -MRD low only 1.5 clocks later (data sheet, figure 11), so "this port and -MRD high" (RTC_RD, the
            DS12885's DS) is also true at the start of every OUT to the data port. A DS12885 does not mind a read
            there; a 16550 does: writing a character (THR, register 0) would first read register 0 (RBR) and so throw
            a received character away. So the UART's -RD is UART_RD_L, the !Q of U11B (the spare flip-flop): preset
            by -MWR (bus -MRW) going low, which happens only in an INP's cycle (clock 5 to 7, the 1802 writing the
            byte to memory), and held clear whenever RTC_RD is low; with both low !Q is high, so a memory write
            elsewhere does nothing. -RD is low from clock 5 of an INP of the data port to the end of that cycle.
            MR = RESET_H. INTR, inverted by U23C (open drain; RN1 pulls it up), reaches -INT
            through JP7 (off).
  pull-ups  RN1 (10k x8, common pin 1 on +5V) pulls one bus line directly: SC0 (pin 9, its eighth resistor), so it
            rests high with no CPU card. Three more reach the bus only through a jumper: EFOUT (pin 4) on the flag line
            JP3 picks (-EF1 as set), UIRQ_L (pin 8) on -INT with JP7 fitted, RTC_IRQ (pin 7) on -INT with JP4's row 7
            fitted. The bus lines' own pull-ups are on the CPU card and the bus Rev D. The SPDT toggles drive the bits
            both ways.
"""
BUS = {1: "+5V", 2: "D0", 3: "D1", 4: "D2", 5: "D3", 6: "D4", 7: "D5", 8: "D6", 9: "D7", 10: "Q", 11: "TPA", 12: "TPB",
       13: "-MRD", 14: "-MRW", 15: "A0", 16: "A1", 17: "A2", 18: "A3", 19: "A4", 20: "A5", 21: "A6", 22: "A7", 23: "-INT",
       24: "N2", 25: "-EF", 26: "-VMA", 27: "-RESET", 28: "N1", 29: "N0", 30: "GND"}
POS = [BUS[i] for i in range(30, 0, -1)] + ["-EF1", "-EF2", "-EF3", "-DMAIN", "SC0", "-PAUSE"]   # position 1..36, counted from GND
# (Ken, 2026-11-18: GND 1 ... +5V 30, then -EF1 31, -EF2 32, -EF3 33, -DMAIN 34, SC0 35, -PAUSE 36; bus pin n = position 31 - n)
USED = {"+5V", "GND", "-EF1", "-EF2", "-EF3", "-EF", "-INT", "-RESET", "-PAUSE", "-DMAIN", "N0", "N1", "N2", "-MRD", "-MRW", "TPB", "Q",
        "D0", "D1", "D2", "D3", "D4", "D5", "D6", "D7", "TPA", "A0", "A1", "A2", "A3", "A4", "A5", "A6", "A7",
        "SC0", "-VMA"}        # (2026-11-22: SC0 ends the DMA request, -VMA lights the front panel's ROM LED)
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "..", "tools"))
import s5panel                # the front panel ribbon's pin map, shared with hardware/front-panel

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
    # 74HCT573 octal transparent latch, the 373's names (the emulator's Latch373): OC = !OE, ENC = LE, nD -> nQ
    "74HCT573": (DIP20, _p(
        "1:OC:I 2:1D:I 3:2D:I 4:3D:I 5:4D:I 6:5D:I 7:6D:I 8:7D:I 9:8D:I 10:GND:P 11:ENC:I 12:8Q:T 13:7Q:T 14:6Q:T 15:5Q:T "
        "16:4Q:T 17:3Q:T 18:2Q:T 19:1Q:T 20:VCC:P")),
    "74HCT244": (DIP20, _p(
        "1:1OE:I 2:1A1:I 3:2Y4:T 4:1A2:I 5:2Y3:T 6:1A3:I 7:2Y2:T 8:1A4:I 9:2Y1:T 10:GND:P 11:2A1:I 12:1Y4:T 13:2A2:I "
        "14:1Y3:T 15:2A3:I 16:1Y2:T 17:2A4:I 18:1Y1:T 19:2OE:I 20:VCC:P")),
    "74HCT14": (DIP14, _p("1:I:I 2:O:O 3:I:I 4:O:O 5:I:I 6:O:O 7:GND:P 8:O:O 9:I:I 10:O:O 11:I:I 12:O:O 13:I:I 14:VCC:P")),
    "74HCT10": (DIP14, _p("1:I0:I 2:I1:I 3:I0:I 4:I1:I 5:I2:I 6:O:O 7:GND:P 8:O:O 9:I0:I 10:I1:I 11:I2:I 12:O:O 13:I2:I 14:VCC:P")),
    "74HCT02": (DIP14, _p("1:O:O 2:I0:I 3:I1:I 4:O:O 5:I0:I 6:I1:I 7:GND:P 8:I0:I 9:I1:I 10:O:O 11:I0:I 12:I1:I 13:O:O 14:VCC:P")),
    "74HCT00": (DIP14, _p("1:I0:I 2:I1:I 3:O:O 4:I0:I 5:I1:I 6:O:O 7:GND:P 8:O:O 9:I0:I 10:I1:I 11:O:O 12:I0:I 13:I1:I 14:VCC:P")),
    # 74HC03: quad 2-input NAND with open-drain outputs (the 74HC00's pins); U9 was a 74HC05 until 2026-11-22
    "74HC03": (DIP14, _p("1:I0:I 2:I1:I 3:O:OC 4:I0:I 5:I1:I 6:O:OC 7:GND:P 8:O:OC 9:I0:I 10:I1:I 11:O:OC 12:I0:I 13:I1:I 14:VCC:P")),
    # 74HCT03: the 74HC03 with TTL input levels (VIH 2.0 V, against 3.15 V at 4.5 V), the same pins (TI CD74HCT03, SCHS414)
    "74HCT03": (DIP14, _p("1:I0:I 2:I1:I 3:O:OC 4:I0:I 5:I1:I 6:O:OC 7:GND:P 8:O:OC 9:I0:I 10:I1:I 11:O:OC 12:I0:I 13:I1:I 14:VCC:P")),
    "74HCT74": (DIP14, _p("1:CLR:I 2:D:I 3:CLK:I 4:PRE:I 5:Q:O 6:~{Q}:O 7:GND:P 8:~{Q}:O 9:Q:O 10:PRE:I 11:CLK:I 12:D:I 13:CLR:I 14:VCC:P")),
    # DS12885 RTC, 24-pin PDIP (Maxim datasheet Rev 3, 2/07, pin description, read on 2026-11-18 from two copies):
    # 12 and 16 are both GND on the PDIP; 22 is the only N.C.; RCLR has an internal pull-up (no external one)
    "DS12885": ("Package_DIP:DIP-24_W15.24mm", _p(
        "1:MOT:I 2:X1:passive 3:X2:passive 4:AD0:B 5:AD1:B 6:AD2:B 7:AD3:B 8:AD4:B 9:AD5:B 10:AD6:B 11:AD7:B 12:GND:P "
        "13:~{CS}:I 14:AS:I 15:R/~{W}:I 16:GND:P 17:DS:I 18:~{RESET}:I 19:~{IRQ}:OC 20:VBAT:passive 21:~{RCLR}:I 22:NC:N "
        "23:SQW:O 24:VCC:P")),
    # TIL311 hex display with latch and decoder: pinout and footprint (HTIL311A, 0.3 in rows) as on Ken's built YACC1 IO card
    # (YACC1-D hardware/cards/io/kicad/v1.1: 3/2/13/12 = data A-D, 5 strobe and 8 blanking to GND, 1 LED supply to +5V)
    "TIL311": ("s5io:HTIL311A", _p(
        "1:LED_VCC:P 2:B:I 3:A:I 4:DP_L:P 5:STROBE:I 7:GND:P 8:BLANK:I 10:DP_R:P 12:D:I 13:C:I 14:VCC:P")),
    # a clock oscillator in a half-size (8-pin DIP) can, as CPU Rev D's X1: pin 1 its enable (on when high) or nothing
    "OSC_DIP8": ("Oscillator:Oscillator_DIP-8", _p("1:EN:I 4:GND:P 5:OUT:O 8:VCC:P")),
}

R = "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal"
CAP = "s5io:C025-050X050"                     # 0.1 uF with 0.1" leads (Ken's rule)
PARTS = {}
def chip(ref, name, value, pins):
    PARTS[ref] = ("s5io:" + name, value, CHIPS[name][0], pins)

PARTS["J1"] = ("Connector_Generic:Conn_01x36", "System-5 bus (36)", "s5io:C36",
               {i + 1: (n if n in USED else None) for i, n in enumerate(POS)})
chip("U1", "74HCT138", "74HCT138", {1: "N0", 2: "N1", 3: "N2", 6: "+5V", 4: "GND", 5: "GND", 15: None,   # Y0: no port
     14: "Y1_L", 13: "Y2_L", 12: "Y3_L", 11: "Y4_L", 10: "Y5_L", 9: "Y6_L", 7: "Y7_L", 8: "GND", 16: "+5V"})
chip("U2", "74HCT374", "74HCT374", {1: "GND", 11: "OUTCLK", 10: "GND", 20: "+5V",
     3: "D0", 2: "OUT0", 4: "D1", 5: "OUT1", 7: "D2", 6: "OUT2", 8: "D3", 9: "OUT3",
     13: "D4", 12: "OUT4", 14: "D5", 15: "OUT5", 17: "D6", 16: "OUT6", 18: "D7", 19: "OUT7"})
chip("U3", "74HCT244", "74HCT244", {1: "OE244_L", 19: "OE244_L", 10: "GND", 20: "+5V",
     2: "SW0", 18: "D0", 4: "SW1", 16: "D1", 6: "SW2", 14: "D2", 8: "SW3", 12: "D3",
     11: "SW4", 9: "D4", 13: "SW5", 7: "D5", 15: "SW6", 5: "D6", 17: "SW7", 3: "D7"})
chip("U4", "74HCT14", "74HCT14", {1: "INPUT_RC", 2: "INPUT_H", 3: "PORTOUT_L", 4: "POUT_H", 5: "-MRD", 6: "MRD_H",
     9: "-RESET", 8: "RESET_H", 11: "-PAUSE", 10: "PAUSE_H", 13: "LOAD_L", 12: "LOAD_H", 7: "GND", 14: "+5V"})
chip("U5", "74HCT10", "74HCT10", {1: "POUT_H", 2: "MRD_H", 13: "TPB", 12: "OUTCLK",
     3: "Q", 4: "+5V", 5: "+5V", 6: "LED_Q_K",                  # B: the Q LED, push-pull (NAND(Q, 1, 1) sinks it while Q is high)
     9: "RTC_RD", 10: "RTC_RD", 11: "RTC_RD", 8: "RTC_RD_L",   # C: the RTC's read strobe DS, low through an INP of its data port
     7: "GND", 14: "+5V"})
chip("U6", "74HCT00", "74HCT00", {1: "PORTIN_L", 2: "DRVL_L", 3: "ANY_H", 4: "-MRD", 5: "ANY_H", 6: "OE244_L",
     9: "RESET_H", 10: "PAUSE_H", 8: "LOAD_L", 12: "MRD_H", 13: "TPB", 11: "OSTB_L",       # D: OSTB_L, TPB of a read
     7: "GND", 14: "+5V"})
chip("U9", "74HC03", "74HC03", {1: "INPUT_H", 2: "INPUT_H", 3: "EFOUT",      # A: INPUT's flag
     4: "REQ", 5: "SC0", 6: "-DMAIN",                                          # B: the DMA request, until the DMA cycle starts
     9: "LOAD_L", 10: "LOAD_L", 8: "REQCLR_L",                                 # C: REQ cleared outside LOAD mode
     12: "DRIVE", 13: "LOAD_H", 11: "DRVL_L", 7: "GND", 14: "+5V"})            # D: DRIVE, in LOAD mode alone
# (2026-11-25: until then C and D were the UART's INTR and the ROM LED, now U23's C and D, its spares: the two new
# gates belong beside U10, U11 and U6, and J3 and the UART are nearer U23)
PARTS["D1"] = ("Device:D_Schottky", "BAT85", "Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal", {1: "ACK_L", 2: "REQCLR_L"})   # 1 K, 2 A
PARTS["R5"] = ("Device:R", "3.3k", R, {1: "+5V", 2: "REQCLR_L"})
PARTS["R6"] = ("Device:R", "3.3k", R, {1: "+5V", 2: "DRVL_L"})
chip("U10", "74HCT74", "74HCT74", {1: "REQCLR_L", 2: "LOAD_H", 3: "INPUT_H", 4: "+5V", 5: "REQ", 6: "REQ_L",    # A: REQ
     13: "INPUT_H", 12: "REQ", 11: "-MRW", 10: "+5V", 9: None, 8: "ACK_L", 7: "GND", 14: "+5V"})             # B: ACK
chip("U11", "74HCT74", "74HCT74", {4: "REQ_L", 1: "-MRD", 2: "GND", 3: "GND", 5: "DRIVE", 6: None,   # A: DRIVE
     # B: the UART's read strobe (2026-11-20): preset by -MWR low, cleared while RTC_RD is low; !Q = UART_RD_L
     13: "RTC_RD", 12: "GND", 11: "GND", 10: "-MRW", 9: None, 8: "UART_RD_L", 7: "GND", 14: "+5V"})
chip("U7", "TIL311", "TIL311", {1: "+5V", 3: "OUT4", 2: "OUT5", 13: "OUT6", 12: "OUT7", 5: "GND", 8: "GND",
     4: None, 10: None, 7: "GND", 14: "+5V"})                                                                 # bits 7-4
chip("U8", "TIL311", "TIL311", {1: "+5V", 3: "OUT0", 2: "OUT1", 13: "OUT2", 12: "OUT3", 5: "GND", 8: "GND",
     4: None, 10: None, 7: "GND", 14: "+5V"})                                                                 # bits 3-0

for k in range(8):                                                  # the output LEDs, sourced by the '374
    PARTS["LED%d" % (k + 1)] = ("Device:LED", "BIT %d" % k, "LED_THT:LED_D3.0mm", {1: "GND", 2: "LEDA%d" % k})   # 1 K, 2 A
# their resistors in one isolated array (Ken, 2026-11-18): resistor k+1 between pins k+1 and 16-k
PARTS["RN2"] = ("Device:R_Pack08", "1k x8", "Package_DIP:DIP-16_W7.62mm",
                dict([(k + 1, "OUT%d" % k) for k in range(8)] + [(16 - k, "LEDA%d" % k) for k in range(8)]))
PARTS["LED9"] = ("Device:LED", "Q", "LED_THT:LED_D3.0mm", {1: "LED_Q_K", 2: "LED_Q_A"})
PARTS["R2"] = ("Device:R", "1k", R, {1: "+5V", 2: "LED_Q_A"})
PARTS["LED10"] = ("Device:LED", "PWR", "LED_THT:LED_D3.0mm", {1: "GND", 2: "LED_PWR"})
PARTS["R3"] = ("Device:R", "1k", R, {1: "+5V", 2: "LED_PWR"})
TOGGLE = "s5io:M9040P"           # Marquardt M9040P vertical SPDT toggle, the footprint from Ken's YACC1 IO card (M9040P)
for k in range(8):               # the data toggles, SPDT as on the YACC1 IO card: common = the bit, ends +5V and GND (no pull-ups)
    PARTS["SW%d" % (k + 1)] = ("Switch:SW_SPDT", "BIT %d" % k, TOGGLE, {1: "+5V", 2: "SW%d" % k, 3: "GND"})
PARTS["SW9"] = ("Switch:SW_Push", "INPUT", "Button_Switch_THT:SW_PUSH_6mm", {1: "INPUT_RC", 2: "GND"})
PARTS["R1"] = ("Device:R", "10k", R, {1: "+5V", 2: "INPUT_RC"})
PARTS["C1"] = ("Device:C", "470nF", "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P2.50mm", {1: "INPUT_RC", 2: "GND"})   # ~5 ms debounce
PARTS["SW10"] = ("Switch:SW_SPDT", "RUN/RESET", TOGGLE, {2: "GND", 1: "-RESET", 3: None})
PARTS["SW11"] = ("Switch:SW_SPDT", "LOAD", TOGGLE, {2: "GND", 1: "-PAUSE", 3: None})
HDR = "Connector_PinHeader_2.54mm:PinHeader_2x%02d_P2.54mm_Vertical"
for ref, value, sel in (("JP1", "IN PORT", "PORTIN_L"), ("JP2", "OUT PORT", "PORTOUT_L")):   # Ken, 2026-11-17: IN and OUT
    PARTS[ref] = ("Connector_Generic:Conn_02x07_Odd_Even", value, HDR % 7,                    # on jumpers, each port 1-7:
                  {p: ("Y%d_L" % ((p + 1) // 2) if p % 2 else sel) for p in range(1, 15)})     # a jumper across row n = port n
EFLINES = ("-EF1", "-EF2", "-EF3", "-EF")
PARTS["JP3"] = ("Connector_Generic:Conn_02x04_Odd_Even", "INPUT EF", HDR % 4,                   # INPUT's flag on any bus EF line
                {p: (EFLINES[(p - 1) // 2] if p % 2 else "EFOUT") for p in range(1, 9)})
PARTS["RN1"] = ("Device:R_Network08", "10k", "Resistor_THT:R_Array_SIP9",                       # pull-ups: no jumper, no port
                {1: "+5V", 2: "PORTIN_L", 3: "PORTOUT_L", 4: "EFOUT", 5: "RTCA_L", 6: "RTCD_L", 7: "RTC_IRQ", 8: "UIRQ_L", 9: "SC0"})
# the front panel (Ken, 2026-11-22): J3, the ribbon's header (pin map: tools/s5panel.py), and RN3, pull-downs for the
# data lines, which the front panel's toggles switch to +5V through 1k
PARTS["J3"] = ("Connector_Generic:Conn_02x25_Odd_Even", "FRONT PANEL", "Connector_IDC:IDC-Header_2x25_P2.54mm_Vertical",
               s5panel.io_pins())
PARTS["RN3"] = ("Device:R_Network08", "10k", "Resistor_THT:R_Array_SIP9",
                dict([(1, "GND")] + [(k + 2, "SW%d" % k) for k in range(8)]))
# the card's own RESET button (Ken, 2026-11-23): a boot reset, -RESET and -DMAIN low together, unless -PAUSE is low
PARTS["SW12"] = ("Switch:SW_Push", "RESET", "Button_Switch_THT:SW_PUSH_6mm", {1: "+5V", 2: "BTN_H"})
PARTS["R4"] = ("Device:R", "10k", R, {1: "BTN_H", 2: "GND"})
chip("U23", "74HCT03", "74HCT03", {1: "BTN_H", 2: "-PAUSE", 3: "-RESET",          # A: -RESET
     4: "BTN_H", 5: "-PAUSE", 6: "-DMAIN",                                      # B: -DMAIN, with it
     9: "UART_INT", 10: "UART_INT", 8: "UIRQ_L",                                # C: the UART's INTR (2.4 V high is all a
     #                                          16C550's sheet promises: a 74HCT03 for it, Ken, 2026-11-25)
     12: "-VMA", 13: "-VMA", 11: "ROM_LED_L", 7: "GND", 14: "+5V"})             # D: the front panel's ROM LED
PARTS["C26"] = ("Device:C", "0.1uF", "s5io:C025-050X050", {1: "+5V", 2: "GND"})   # U23's (C22-C25 are the MAX232's)
# the real-time clock (Ken, 2026-11-18): a DS12885+ with its crystal and a CR2032 that can be replaced
chip("U13", "DS12885", "DS12885+", {1: "GND", 2: "RTC_X1", 3: "RTC_X2", 4: "D0", 5: "D1", 6: "D2", 7: "D3", 8: "D4", 9: "D5",
     10: "D6", 11: "D7", 12: "GND", 13: "SEL_UART", 14: "RTC_AS", 15: "RTC_WR_L", 16: "GND", 17: "RTC_RD_L", 18: "+5V",
     19: "RTC_IRQ", 20: "VBAT", 21: "RCLR_L", 22: None, 23: None, 24: "+5V"})     # MOT low: Intel timing; RESET high;
#                                                 CS = SEL_UART (2026-11-20: tied low until the UART shared its ports)
# JP5 (Ken, 2026-11-18: "change add jumper", for pcb-check's warning that RCLR was left open): a shunt grounds the DS12885's
# RCLR, which clears its 114 bytes of general RAM (never the clock) while the chip runs from its battery, the power off.
# Open, nothing changes: RCLR has its own pull-up inside the chip, and the data sheet forbids an outside one
PARTS["JP5"] = ("Connector_Generic:Conn_01x02", "RAM CLR", "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
                {1: "RCLR_L", 2: "GND"})
PARTS["Y1"] = ("Device:Crystal", "32.768kHz", "Crystal:Crystal_C26-LF_D2.1mm_L6.5mm_Vertical", {1: "RTC_X1", 2: "RTC_X2"})
PARTS["BT1"] = ("Device:Battery_Cell", "CR2032", "Battery:BatteryHolder_Keystone_103_1x20mm", {1: "VBAT", 2: "GND"})  # flat
chip("U12", "74HCT02", "74HCT02", {2: "RTCA_L", 3: "OSTB_L", 1: "RTC_AS",           # A: AS, an OUT to the address port
     5: "RTCD_L", 6: "OSTB_L", 4: "RTC_WR",                                          # B: an OUT to the data port
     8: "RTC_WR", 9: "RTC_WR", 10: "RTC_WR_L",                                       # C: R/W, low in its TPB
     11: "RTCD_L", 12: "MRD_H", 13: "RTC_RD", 7: "GND", 14: "+5V"})                  # D: an INP of the data port
PARTS["JP4"] = ("Connector_Generic:Conn_02x07_Odd_Even", "RTC + UART", HDR % 7,             # the RTC's port pair: one jumper in
                {p: (("Y2_L", "Y4_L", "Y6_L", "Y3_L", "Y5_L", "Y7_L", "RTC_IRQ")[(p - 1) // 2] if p % 2   # rows 1-3 (address
                     else "RTCA_L" if p <= 6 else "RTCD_L" if p <= 12 else "-INT")                   # 2, 4, 6), one in 4-6
                 for p in range(1, 15)})                                             # (data 3, 5, 7), set to 6 and 7;
#                                                                                   row 7: IRQ to -INT (off)
# the address display (Ken, 2026-11-18): U18 latches the high byte at TPA, U19 the low byte at TPB; four TIL311s show them
for ref, le, hi in (("U18", "TPA", 8), ("U19", "TPB", 0)):
    pins = {1: "GND", 10: "GND", 20: "+5V", 11: le}
    for i in range(8): pins[2 + i] = "A%d" % i; pins[19 - i] = "ADR%d" % (hi + i)
    chip(ref, "74HCT573", "74HCT573", pins)
for ref, n in (("U14", 12), ("U15", 8), ("U16", 4), ("U17", 0)):        # A15-A12 ... A3-A0, left to right when standing
    chip(ref, "TIL311", "TIL311", {1: "+5V", 3: "ADR%d" % n, 2: "ADR%d" % (n + 1), 13: "ADR%d" % (n + 2), 12: "ADR%d" % (n + 3),
                                   5: "GND", 8: "GND", 4: None, 10: None, 7: "GND", 14: "+5V"})
# the serial port (Ken, 2026-11-20): a 16C550 on the RTC's port pair, a MAX232, a DE-9 socket.
# KiCad's own symbols for the UART and the MAX232 (their pin numbers are the DIP's)
PARTS["U20"] = ("Interface_UART:16550", "16C550", "Package_DIP:DIP-40_W15.24mm", dict(
    [(1 + i, "D%d" % i) for i in range(8)] + [
     (9, "UBAUD"), (15, "UBAUD"),                  # -BAUDOUT to RCLK: the receiver on the transmitter's clock
     (10, "URX"), (11, "UTX"),                     # SIN, SOUT
     (12, "SEL_UART"), (13, "+5V"), (14, "GND"),   # CS0 = the select latch's bit 7; CS1 high, -CS2 low
     (16, "UCLK"), (17, None),                     # XIN from the oscillator; XOUT open
     (18, "+5V"), (19, "RTC_WR"),                  # -WR high (not used); WR high in TPB of an OUT to the data port
     (20, "GND"), (21, "UART_RD_L"), (22, "GND"),  # -RD from U11B; RD low (not used)
     (23, None), (24, None), (29, None),           # DDIS, -TXRDY, -RXRDY
     (25, "GND"),                                  # -ADS low: A0-A2 and the selects not latched in the chip (U22 does)
     (26, "UA2"), (27, "UA1"), (28, "UA0"),
     (30, "UART_INT"), (31, None), (32, None), (33, None), (34, None),         # INTR; -OUT2, -RTS, -DTR, -OUT1 open
     (35, "RESET_H"),                              # MR, active high
     (36, "+5V"), (37, "+5V"), (38, "+5V"), (39, "+5V"),                       # -CTS, -DSR, -DCD, -RI: tied off
     (40, "+5V")]))
chip("X1", "OSC_DIP8", "1.8432MHz", {1: "+5V", 4: "GND", 5: "UCLK", 8: "+5V"})
# the select latch: the byte written to the address port, held as the DS12885 holds it (LE = its AS)
chip("U22", "74HCT573", "74HCT573", {1: "GND", 10: "GND", 20: "+5V", 11: "RTC_AS",
     2: "D0", 19: "UA0", 3: "D1", 18: "UA1", 4: "D2", 17: "UA2", 5: "D7", 16: "SEL_UART",
     6: "GND", 7: "GND", 8: "GND", 9: "GND", 15: None, 14: None, 13: None, 12: None})                     # 4 spare
PARTS["U21"] = ("Interface_UART:MAX232", "MAX232", "Package_DIP:DIP-16_W7.62mm",
                {1: "C1P", 3: "C1M", 4: "C2P", 5: "C2M", 2: "VPLUS", 6: "VMINUS", 11: "UTX", 14: "TX_OUT", 13: "RX_IN",
                 12: "URX", 10: "GND", 8: "GND", 7: None, 9: None, 15: "GND", 16: "+5V"})   # the second channel not used:
#                              T2IN and R2IN both low (T2IN to GND, not +5V as on the YACC1 card: it sits in the middle
#                              of the chip's line side, where a 0.5 mm +5V track has no way in; T2OUT then idles high)
CPOL = "Capacitor_THT:CP_Radial_D5.0mm_P2.50mm"       # the MAX232's 1 uF capacitors, as on the YACC1 I/O card: 1 = +
PARTS["C22"] = ("Device:C_Polarized", "1uF", CPOL, {1: "C1P", 2: "C1M"})
PARTS["C23"] = ("Device:C_Polarized", "1uF", CPOL, {1: "C2P", 2: "C2M"})
PARTS["C24"] = ("Device:C_Polarized", "1uF", CPOL, {1: "VPLUS", 2: "+5V"})      # V+ (about +9 V) to +5V
PARTS["C25"] = ("Device:C_Polarized", "1uF", CPOL, {1: "GND", 2: "VMINUS"})     # V- (about -9 V): GND is its + side
# the null-modem block, as the YACC1 I/O card's JP1: 1-3 and 2-4 = the card sends on DE-9 pin 2 and hears on 3 (a
# straight cable to a PC); 3-5 and 4-6 = sends on 3, hears on 2
PARTS["JP6"] = ("Connector_Generic:Conn_02x03_Odd_Even", "TX/RX", HDR % 3,
                {1: "RX_IN", 2: "TX_OUT", 3: "DE9_3", 4: "DE9_2", 5: "TX_OUT", 6: "RX_IN"})
# the DE-9 socket: KiCad's own footprint for a right-angle socket with the pin pattern of the YACC1 I/O card's (built,
# V1.1): pins 2.77 mm apart in rows 2.84 mm apart, the mounting holes 25 mm apart and level with the middle of the
# rows; make_board.py places it as that card has it. Its shell (the two mounting holes, "SH") to GND
DE9 = "Connector_Dsub:DSUB-9_Socket_Horizontal_P2.77x2.84mm_EdgePinOffset7.70mm_Housed_MountingHolesOffset9.12mm"
PARTS["J2"] = ("Connector:DE9_Socket_MountingHoles", "RS-232", DE9,
               {1: None, 2: "DE9_2", 3: "DE9_3", 4: None, 5: "GND", 6: None, 7: None, 8: None, 9: None, "SH": "GND"})
PARTS["JP7"] = ("Connector_Generic:Conn_01x02", "UART INT", "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
                {1: "UIRQ_L", 2: "-INT"})                                       # fitted: the UART's INTR pulls -INT low
PARTS["C2"] = ("Device:C_Polarized", "10uF", "Capacitor_THT:CP_Radial_D5.0mm_P2.00mm", {1: "+5V", 2: "GND"})
BYPASSED = ("U1", "U2", "U3", "U4", "U5", "U6", "U7", "U8", "U9", "U10", "U11", "U12", "U13", "U18", "U19",
            "U20", "U21", "U22", "X1")              # C3 ... C21, in this order (make_board.py places them by it)
for k, u in enumerate(BYPASSED):
    PARTS["C%d" % (k + 3)] = ("Device:C", "0.1uF", CAP, {1: "+5V", 2: "GND"})     # C9, C10: the six TIL311s' supply rail
DOCS = {}
