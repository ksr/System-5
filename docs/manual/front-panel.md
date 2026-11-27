# Front panel: theory of operation

The front panel is a 2026 board for a System-5 in a case. It does not stand in the bus: it mounts as the front of the case and carries the machine's hand controls and displays. One 50-way ribbon joins it to the [IO panel card](io-panel.md)'s J3; nothing goes to the CPU card.
It has six TIL311 hex displays (the bus address and the output port), eight bit LEDs, six status LEDs, eight data toggles, RUN/RESET and LOAD, INPUT, and a RESET button that boots the EPROM.

- **Rev A**, `hardware/front-panel/kicad/rev-a/`, generated from `gen/netlist.py` (`gen/build.sh` makes the schematic, board, route and order files): 190.5 x 88.9 mm (7.50 x 3.50 in), two layers, 62 parts, an M3 hole in each corner. Drawn 2026-11-22, routed; **not ordered, not built**. `pcb-check --tests` at `803c3a8` (2026-11-26): no failures, 0 warnings.
- The ribbon's fifty pins are defined once, in `tools/s5panel.py`, which both boards' generators read.
- The design record: the board's `DESIGN.md`. The boot reset it makes is in [bus.md](bus.md).

## Parts

| Ref | Part | Job |
|---|---|---|
| J1 | keyed 2x25 header, on the back | the ribbon from the IO panel card's J3 |
| U1-U4 | TIL311 | ADDRESS: A15-A12, A11-A8, A7-A4, A3-A0 |
| U5, U6 | TIL311 | DATA: the output port, D7-D4 and D3-D0 |
| LED1-LED8, RN1 | LEDs, 1k x8 isolated | BIT 0-7, the output port bit by bit |
| SW1-SW8, RN2 | Marquardt M9040P toggles, 1k x8 bussed | BIT 0-7: the data byte, up = 1 |
| SW9, SW10 | M9040P toggles | RUN/RESET (grounds -RESET), LOAD (grounds -PAUSE) |
| SW11 | push-button | INPUT |
| SW12, R7, C1 | push-button, 10k, 470 nF | RESET, debounced |
| U7 | 74HCT14 | Schmitt inverters: the bus lines read, the button debounced |
| U8 | 74HCT10 | LOAD_L and BOOT_L, the CPU card's two gates copied |
| U9 | 74HCT74 | U9A: the START FROM RAM flag |
| U10 | 74HC03 (open drain) | U10A, U10B: the RESET button's -RESET and -DMAIN |
| LED9-LED14, R1-R6 | LEDs, 1k each | PWR, Q, PAUSE, RESET, ROM, START FROM RAM |
| C2, C3-C12 | 47 uF, 0.1 uF | bulk and one bypass per chip |
| H1-H4 | M3 holes | mounting |

Spare gates: U8C, U9B and U10C, U10D, their inputs tied.

## The ribbon

A straight 50-way ribbon joins J1 to the IO panel card's J3, pin n to pin n.

| Pins | Lines | What they do |
|---|---|---|
| 1, 2, 49, 50 | +5V | four supply wires |
| 3, 20, 29, 38, 41, 43, 45, 47 | ground | eight wires |
| 4-19 | ADR15 ... ADR0 | from the IO card's address latches (U18, U19) to U1-U4 |
| 21-28 | OUT7 ... OUT0 | from the IO card's output latch (U2) to U5, U6 and the bit LEDs |
| 30-37 | SW7 ... SW0 | the data toggles, to the IO card's 74HCT244 |
| 39 | Q_LED_L | sunk by the IO card's U5B while Q is high |
| 40 | ROM_LED_L | sunk by the IO card's U23D while the CPU card's EPROM answers |
| 42 | INPUT_L | the INPUT button, to ground |
| 44, 46, 48 | -RESET, -PAUSE, -DMAIN | the bus lines themselves, open collector |

-RESET (44) and -PAUSE (46) each have a ground wire on both sides; -DMAIN (48) lies between GND (47) and +5V (49). The six TIL311s take about 1.1 A, 0.28 A on each supply wire. With the IO card's own six displays fitted too, the twelve take about 2.2 A of the backplane regulator's 3 A, so fit the displays on one board.

J1 is the only part on the back, so the ribbon leaves behind the panel. With the IO card's parts side facing the panel's back the ribbon lies without a twist (`DESIGN.md`, "The cable"); it has not been tried with a cable. Allow about 20 mm behind the board.

## Displays and bit LEDs

The six TIL311s are wired as the IO card's: strobe low (the internal latch transparent), blanking low (always on), so each simply shows the four lines on its inputs. The address digits behave as the IO card's, including their quirk in LOAD mode ([io-panel.md](io-panel.md)).

The bit LEDs are sourced by the IO card's 74HCT374 through RN1, cathodes to ground: lit for a 1.

## The controls

**Data toggles.** Each toggle switches its line SWn to +5V through 1k (RN2) or leaves it open; the IO card's RN3 (10k) pulls an open line down. The 1k is there because the IO card's own toggles, if fitted, sit between +5V and ground: then the IO card's win and nothing is shorted. A card built for the front panel leaves its own data toggles out.

**RUN/RESET and LOAD** pull the bus -RESET and -PAUSE straight to ground, as the IO card's own two toggles do. Up is RUN, up is LOAD. With both boards' toggles fitted either one pulls its line, so both must be at RUN for the machine to run. Both lines low is LOAD mode.

**INPUT** grounds the IO card's INPUT line, in parallel with that card's button; the IO card debounces it.

**RESET** is a boot reset. R7 and C1 (about 5 ms) and a Schmitt inverter (U7D) debounce SW12 into BTN_H, high while pressed. U10A and U10B pull -RESET and -DMAIN low together. Each gate's other input is PAUSE_N (U7E), which is low while -PAUSE is low, so the button does nothing while LOAD is on: in LOAD mode a low -DMAIN would be a DMA request. -RESET and -DMAIN low with -PAUSE high is the bus's boot reset: CPU Rev D clears its LOADED flag, and when the button is let go its DS1813 holds -RESET for 150 ms more, by which time -DMAIN is high again, and the machine starts in HBIOS.

There are two controls called RESET, and they differ (Ken kept both names, 2026-11-23):

| Control | What starts afterwards |
|---|---|
| RUN/RESET toggle at RESET | what ran before: a loaded program, or HBIOS |
| RESET button | HBIOS, always |

The IO card's button and the CPU card's switch do the same. On 2026-11-26 the button moved to the top right, beside START FROM RAM, away from INPUT, where it was too easy to hit.

## The status LEDs

Each status LED has 1k from +5V and is sunk by the line that lights it.

| LED | Sunk by | Lit while |
|---|---|---|
| PWR | ground | the panel has power |
| Q | the IO card's U5B (Q_LED_L) | Q is high |
| PAUSE | U7E (PAUSE_N) | -PAUSE is low |
| RESET | U7F (RESET_N) | -RESET is low |
| ROM | the IO card's U23D (ROM_LED_L) | the CPU card's EPROM answers (-VMA high) |
| START FROM RAM | U9A, !Q | the CPU card's LOADED flag is set |

**START FROM RAM is a copy of the flag, not the flag itself.** CPU Rev D sets LOADED in LOAD mode and clears it on a boot reset; both are states of the three bus lines on the ribbon. So the panel inverts -RESET, -PAUSE and -DMAIN (U7) and builds the same two gates as the CPU card: LOAD_L = NAND(RESET_H, PAUSE_H) (U8A) presets U9A, and BOOT_L = NAND(RESET_H, DMAIN_H, PAUSE_N) (U8B) clears it. The CPU card's power-on reset is a boot reset, so the copy and the flag agree from power-on. That is why one ribbon is enough.

## Layout

From the front: ADDRESS, DATA and STATUS (with RESET) across the top; the bit LEDs, the data toggles under them, then RUN/RESET, LOAD and INPUT; the logic below; the name and `cottageworker.com` bottom left. Every text is at angle 0: the board hangs as drawn.

## Testing it

The emulator runs the board from its netlist, hung on the IO panel card's ribbon: `python3 -m s5emu --hw --cpu-rev D --panel A --front A`; the debugger's `front` command shows it and sets the toggles, INPUT, RESET, RUN and LOAD. `software/s5emu/tests/test_front_panel.py` (in `tools/qa.py`) checks both headers against `tools/s5panel.py` pin for pin, toggles a program in and runs it, and checks that RESET boots HBIOS but not while LOAD is on, that the CPU card's switch and the bus driver's `MODE:4#` clear the copy of LOADED, and that every switch is played as the netlist wires it. The emulator joins the boards by net name, so a crossed ribbon pin is caught by the pin-for-pin test alone. Work on this board found the IO card's double-load fault, put right before either was built.

**Not proven on hardware:** all of it. Not decided: how the panel is held in a case and whether a plate goes in front of it.
