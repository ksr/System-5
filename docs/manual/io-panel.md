# IO panel card: theory of operation

The IO panel is the 2026 IO card for the 36-pin bus: the machine's hand controls and displays on a card that stands in the bus. Eight toggles sit on an input port; eight LEDs and two TIL311 hex digits on an output port; four more TIL311s show the bus address. There are a Q LED, an INPUT button on an EF line, and the ELF's RUN/RESET and LOAD toggles for toggling a program into memory.
It also has a DS12885 real-time clock, a 16C550 serial port, a RESET button that boots the EPROM, and a header for the [front panel](front-panel.md). It replaces the 2005 IO card ([io-card.md](io-card.md)).

- **Rev A**, `hardware/io-panel/kicad/rev-a/`, generated from `gen/netlist.py` by `gen/build.sh`: 8.00 x 4.00 in, two layers, 94 parts. Drawn and routed; **not ordered, not built**. `pcb-check --tests` at `6f4359d` (2026-11-26): no failures, one warning that Ken accepted on 2026-11-23 (the DE-9 on the side edge).
- It needs the bus Rev D and CPU Rev D: it uses -EF1, -DMAIN, SC0 and -PAUSE ([bus.md](bus.md), "The 36-pin extension").
- The full record: the card's `DESIGN.md` ("Programming the card": every port, flag and register).

## Parts

| Ref | Part | Job |
|---|---|---|
| U1 | 74HCT138 | N0-N2 to Y1_L-Y7_L, one per port |
| JP1, JP2, JP3 | 2x7, 2x7, 2x4 jumper blocks | IN PORT, OUT PORT, INPUT EF |
| U2 | 74HCT374 | output latch, OUT7-OUT0 |
| LED1-LED8, RN2 | LEDs, 1k x8 isolated | BIT 0-7 |
| U7, U8 | TIL311 | OUT D7-D4, OUT D3-D0 |
| U3 | 74HCT244 | the toggles onto D0-D7 |
| SW1-SW8 | Marquardt M9040P SPDT toggles | BIT 0-7 |
| U18, U19 | 74HCT573 | address latches (TPA, TPB) |
| U14-U17 | TIL311 | A15-A12 ... A3-A0 |
| SW9, R1, C1 | push-button, 10k, 470 nF | INPUT |
| SW10, SW11 | M9040P toggles | RUN/RESET, LOAD |
| U10, U11 | 74HCT74 | REQ, ACK, DRIVE; U11B the UART's read strobe |
| D1, R5, R6 | BAT85, 3.3k, 3.3k | REQ and DRIVE cleared outside LOAD mode |
| SW12, R4 | push-button, 10k | RESET |
| U4, U5, U6, U12 | 74HCT14, 74HCT10, 74HCT00, 74HCT02 | glue and the clock's strobes |
| U9 | 74HC03, open drain | INPUT's flag, -DMAIN, REQCLR_L, DRVL_L |
| U23 | 74HCT03, open drain | the RESET button's -RESET and -DMAIN, the UART's interrupt, the ROM LED |
| U13, Y1, BT1, JP5 | DS12885+, 32.768 kHz, CR2032 (flat Keystone 103), header | the clock; RAM CLR |
| JP4 | 2x7 jumper block | RTC + UART port pair; the clock's IRQ to -INT |
| U20, X1, U22 | 16C550, 1.8432 MHz oscillator, 74HCT573 | the UART and the shared select latch |
| U21, C22-C25 | MAX232, 1 uF x4 | RS-232 levels |
| J2, JP6, JP7 | DE-9 socket, 2x3, 1x2 | RS-232; TX/RX; UART INT |
| LED9, LED10, R2, R3 | LEDs, 1k | Q, PWR |
| J3, RN3 | keyed 2x25 header, 10k x8 | FRONT PANEL; data-line pull-downs |
| RN1 | 10k x8 | pull-ups: jumper commons, EFOUT, the IRQs, SC0 |
| J1, C2-C21, C26 | 36-pin bus connector, 10 uF, 0.1 uF | |

## Ports

During the execute cycle of `OUT n` or `INP n` the 1802 puts n on N0-N2, so U1 (always enabled) holds Y(n)_L low for that cycle. JP1 and JP2 each join one Y line to PORTIN_L or PORTOUT_L; with no jumper RN1 holds the line high and the card has no such port. As set:

| Port | `OUT n` | `INP n` | Jumper |
|---|---|---|---|
| 4 | BIT 7-0 LEDs and the OUT digits | the toggles, up = 1 | JP2, JP1 (any of 1-7) |
| 6 | select: `00`-`7F` a clock register, `80`-`87` UART register 0-7 | nothing | JP4: 2/3, 4/5 or 6/7 |
| 7 | writes the register selected | reads it | JP4 |

The machine's whole map is in [programmers-guide.md](programmers-guide.md).

**Output.** In an `OUT` the byte comes from memory, so -MRD is low (MRD_H high). OUTCLK = NAND(POUT_H, MRD_H, TPB) (U5A) rises as TPB falls, so U2 latches the byte as TPB ends, as a CDP1852 does. The TIL311s' strobe and blanking are tied low: they show their inputs.

**Input.** U3 drives the bus while OE244_L = NAND(-MRD, ANY_H) is low, where ANY_H = NAND(PORTIN_L, DRVL_L) (U6): the IN port or this card's DMA. -MRD is low in every memory read, so the toggles never fight one.

## The address display

The 1802 puts the high address byte on A0-A7 during TPA and the low byte after it. U18 latches the high byte as TPA falls, U19 the low byte as TPB falls; ADR15-ADR0 drive U14-U17. The display holds the last cycle's address while the clock is stopped. In LOAD mode the 1802 leaves TPA out of its idle cycles, so the left two digits change only when a byte is loaded (after 00FF the display reads 0000 until the next byte). Known, not changed.

## INPUT, RUN, LOAD and toggling a program in

**INPUT.** SW9 grounds INPUT_RC; R1, C1 (about 5 ms) and a Schmitt inverter of U4 give INPUT_H, high while pressed. EFOUT (U9A, open drain) is low while pressed; JP3 puts it on -EF1, -EF2, -EF3 or -EF (set: -EF1, so `B1` branches while it is down).

**RUN/RESET and LOAD** ground the open-collector bus lines directly: SW10 at RESET grounds -RESET, SW11 at LOAD grounds -PAUSE. Up is RUN, up is LOAD. Both lines low is LOAD mode; LOAD_H (U4, U6) is high then, whichever card made it.

**One DMA IN per press.** In LOAD mode INPUT_H rising sets REQ (U10A). The bus line is -DMAIN = NAND(REQ, SC0) (U9B): low until SC0 falls at the start of the DMA cycle. The 1802 samples its DMA input at clock 7 of every cycle, the DMA cycle's own too, so the request must be gone by then. DRIVE (U11A), set by REQ, keeps the toggles on the bus through the 1802's write and is cleared by the next fall of -MRD. ACK (U10B), clocked by -MRW rising, clears REQ; ACK is held clear while the button is up, so a held button loads one byte. Each byte goes to M(R0) and R0 steps.

To load: RUN/RESET at RESET, LOAD on; for each byte set the toggles and press INPUT; LOAD off; RUN. The program runs from 0000. Power up with LOAD off ([bus.md](bus.md)).

**Power-up (2026-11-25).** A 74HCT74 comes up in either state; REQ up as 1 would have put the toggles on the bus in every memory write. REQ's clear is now REQCLR_L, low outside LOAD mode (U9C) or while ACK is set (D1), with R5 to +5V; and DRIVE reaches U6 only as DRVL_L = NAND(DRIVE, LOAD_H) (U9D, R6). `DESIGN.md` has the voltage margins.

## RESET

Two controls are called RESET, and they differ (Ken kept both names, 2026-11-23):

| Control | Lines | What starts afterwards |
|---|---|---|
| RUN/RESET toggle at RESET | -RESET | what ran before: a loaded program, or HBIOS |
| SW12 RESET button | -RESET and -DMAIN | HBIOS, always |

SW12 puts +5V on BTN_H (R4 holds it low). U23A and U23B pull -RESET and -DMAIN low together while -PAUSE is high: a **boot reset** ([bus.md](bus.md)), which clears the CPU card's LOADED flag, so the machine starts in the EPROM. While LOAD is on the button does nothing, because a low -DMAIN would then be a DMA request. There is no debounce: the CPU card's DS1813 holds -RESET 150 ms after the last release. The button is at the left end of the front edge as the card stands in the bus, beside J3, 88.5 mm from INPUT, centre to centre (since 2026-11-26; above J3 as drawn).

## The real-time clock

U13, a DS12885+ in Intel timing, keeps time, calendar and 114 bytes of RAM on its CR2032. JP4 picks the port pair (address port 2, 4 or 6; data port 3, 5 or 7; set to 6 and 7). OSTB_L = NAND(MRD_H, TPB) (U6D) is low in TPB of every `OUT`. From it U12 makes AS (an `OUT 6` latches the register number as TPB ends) and R/W (an `OUT 7` writes); DS (U12D, U5C) is low through an `INP 7`. The chip's CS is SEL_UART (below). JP5, shorted, clears the 114 bytes while the chip is on its battery. The IRQ reaches -INT through JP4's last row, open as set.

HBIOS v1.0.8 (`firmware/hbios/v1.0.8/`) has the driver, `f_gettod` (F815) and `f_settod` (F818); tried in the emulator only, not burned.

## The serial port

U20, a 16C550, has its own 1.8432 MHz clock (divisor 12 = 9600 baud). It shares the clock's ports: U22, latched by the clock's AS, keeps bit 7 of the byte written to port 6 as SEL_UART and bits 2-0 as the register. `80`-`87` select UART register 0-7. Always write the select before using port 7: it cannot be read back, and an interrupt routine that selects in between changes it.

The UART's read strobe is not the clock's. In an `OUT` the 1802 puts N out 1.5 clocks before -MRD falls, so "port 7, -MRD high" briefly looks like a read, and a 16550 would lose a received character. Its -RD comes from U11B instead, preset by -MRW falling, which happens in every memory write; U11B's clear, held by RTC_RD, is what limits it to an `INP` of the data port.

U21 makes the RS-232 levels for J2, a DE-9 on the side edge (pin 5 ground). JP6 shunts on 1-3 and 2-4 send on pin 2 (a straight cable to a PC); on 3-5 and 4-6 on pin 3; the silkscreen draws both. Modem inputs are tied off. JP7, fitted, puts the UART's interrupt (U23C) on -INT; open as set. HBIOS has no UART driver yet.

## Q, PWR and the front panel header

LED9 (Q) sinks into U5B = NAND(Q, 1, 1); LED10 is PWR. J3 carries the address, output and data lines, the Q and ROM LED sinks, INPUT and the bus -RESET, -PAUSE and -DMAIN to the front panel, whose chapter has the pinout. ROM_LED_L = NAND(-VMA, -VMA) (U23D) is low while the CPU card's EPROM answers. RN3 pulls the data lines down for the front panel's toggles, which switch to +5V through 1k; this card's own toggles, if fitted, win, so a card for a front panel leaves SW1-SW8 out.

## Testing it

`python3 -m s5emu --hw --cpu-rev D --panel A` runs the card from its netlist. `software/s5emu/tests/test_hw.py`, class `IOPanel`, covers the ports and jumpers, one DMA IN per press (and the two cycles of the circuit as first drawn, revision `A-req`), both resets, the address display, the clock with HBIOS v1.0.8 and a serial echo program; class `SystemV5` runs Elf/OS v5 reading the clock. `tests/test_power_up.py` starts the flip-flops at 0, 1 and unknown. All run in `tools/qa.py`.

**Not proven on hardware:** all of it. Before an order: the M9040P's availability and lever direction, and stock of the DS12885+ and Keystone 103.
