# System-5 front panel, Rev A

Drawn 2026-11-22. Not ordered, not built.

A board that mounts as the front of a case and carries the machine's hand controls and displays. One 50-way ribbon
joins it to the IO panel card; nothing goes to the CPU card.

## What Ken asked for

Ken, 2026-11-22:

> I want to add ability to have a front panel if system is ever put in a case. This will mean bringing all IO
> switches, LEDs, and TIL311 signals out to a ribbon cable connector. It will also mean bring the CPU reset out to a
> connector. Then create a front panel card that would mate with these 2 connectors and could be mounted as a front
> panel

and, while it was being worked out: "dont forget q line"; "and cpu status leds for mode"; "unless the IO panel via
the bus can do what the cpu card reset can do then we dont need line from cpu card all can come from io".

Asked, he chose:

| Question | His choice |
|---|---|
| The connector on the IO panel card | lengthen the card to 8.00 in, one 50-pin header at the front edge |
| The panel's shape | landscape, about 7.5 x 3.5 in, laid out as sketched |
| The CPU's reset on the panel | a push-button RESET |
| How that reset reaches the CPU card | a boot reset on the bus, one ribbon (no cable to the CPU card) |

## What is on it

As the board is drawn, which is as it is seen from the front:

| Where | What | Shows or does |
|---|---|---|
| top left | ADDRESS, four TIL311s | the bus address, A15-A12 to A3-A0 |
| top middle | DATA, two TIL311s | the IO panel card's output port, D7-D4 and D3-D0 |
| top right | STATUS, six LEDs | PWR, Q, PAUSE, RESET, ROM, START FROM RAM |
| middle | eight LEDs, 7 to 0 | the output port again, bit by bit |
| under them | eight toggles | the data byte: up is 1 |
| right of them | RUN / RESET, LOAD / OFF | the two ELF-style toggles: up is RUN, up is LOAD |
| far right | INPUT, RESET | two push-buttons |
| a row below | U7-U10, RN1, RN2, C2 | the logic |
| bottom left | the board's name | `System-5 front panel  Rev A  2026`, `cottageworker.com` |
| bottom middle, on the back | J1 | the ribbon's header |

The board is 190.5 x 88.9 mm (7.50 x 3.50 in), two layers, with an M3 hole 5 mm in from each corner. Every text is
at angle 0: the board hangs as drawn, it does not stand in the bus. That is Ken's rule read for this board (text
reads upright as the board is used); the cards' texts are at 270 for the same reason.

J1 is the one part on the back, so the ribbon leaves behind the panel. Its fifty solder joints show on the front,
along the bottom edge. Pin 1 is at the left as seen from the front.

## The ribbon

`tools/s5panel.py` is the one definition of the fifty pins; the IO panel card's J3 and this board's J1 both take
their pins from it, and `tests/test_front_panel.py` checks both netlists against it. A straight ribbon joins pin n to
pin n.

| Pins | Lines | From, to |
|---|---|---|
| 1, 2, 49, 50 | +5V | four wires |
| 3, 20, 29, 38, 41, 43, 45, 47 | ground | eight wires |
| 4-19 | ADR15 ... ADR0 | the IO card's two address latches, to the four address displays |
| 21-28 | OUT7 ... OUT0 | the IO card's output latch, to the data displays and bit LEDs |
| 30-37 | SW7 ... SW0 | the data toggles, to the IO card's input buffer |
| 39 | Q LED | sunk by the IO card while Q is high |
| 40 | ROM LED | sunk by the IO card while the CPU card's EPROM answers |
| 42 | INPUT | the INPUT button, to ground; the IO card debounces it |
| 44, 46, 48 | -RESET, -PAUSE, -DMAIN | the bus lines themselves, open collector |

The three bus lines have a ground wire on each side: they are the ones a spike could matter on.

Six TIL311s take about 1.1 A. Four supply wires carry 0.28 A each. If the IO panel card has its own six displays
fitted as well, the two sets take 2.2 A of the backplane regulator's 3 A: fit the displays on one board.

## The controls

**Data toggles.** Each switches its line to +5V through 1k (RN2) or leaves it open; the IO panel card's RN3 (10k)
pulls an open line down. The resistor is there so that nothing can be shorted if the IO card's own toggles are fitted
too: those sit between +5V and ground, and with both fitted the IO card's win and nothing is harmed. A card built
for the front panel leaves its own data toggles out.

**RUN and LOAD** pull the bus -RESET and -PAUSE to ground, as the IO card's own two toggles do. With both boards'
toggles fitted either one pulls its line, so both must be at RUN for the machine to run.

**INPUT** grounds the IO card's INPUT line, in parallel with that card's own button.

**RESET** is a boot reset: it starts the machine in the EPROM, whatever was loaded. R7, C1 and a Schmitt inverter
debounce the button. Two open-drain gates (U10A, U10B) then pull -RESET and -DMAIN low together. The CPU card
decodes that pair of lines, with -PAUSE high, as "reset and boot the EPROM", and clears its LOADED flag
(`docs/manual/bus.md`, and the CPU card's `DESIGN.md`). When the button is let go both lines are let go; the CPU
card's reset chip holds -RESET low for 150 ms more, by which time -DMAIN is high again, and the machine starts.

The button does nothing while LOAD is on. In LOAD mode a low -DMAIN is a DMA request, so both gates are held off
while -PAUSE is low.

The IO panel card has the same button of its own since 2026-11-23, for a machine without this panel. Either one
works; so does the CPU card's switch.

The button and the RUN / RESET toggle's lower position are both called RESET, and they differ: the toggle starts
again what ran before, the button always boots the EPROM. Ken, 2026-11-23, asked whether the button should have
another name: both keep RESET.

## The status LEDs

Each LED has 1k from +5V and is sunk by the line that lights it.

| LED | Sunk by | Lit while |
|---|---|---|
| PWR | ground | the panel has power |
| Q | the IO card's U5B | Q is high |
| PAUSE | U7E (PAUSE_N) | -PAUSE is low |
| RESET | U7F (RESET_N) | -RESET is low |
| ROM | the IO card's U9D | the CPU card's EPROM answers (-VMA high) |
| START FROM RAM | U9A, !Q | the CPU card's LOADED flag is set |

START FROM RAM is a copy of the flag, not the flag itself. The CPU card's flag is set by LOAD mode and cleared by a
boot reset; both are states of three bus lines, and all three are on the ribbon. So the panel makes its own copy with
the same two gates the CPU card uses (U8A, U8B) and a flip-flop (U9A). The CPU card's power-on reset is a boot reset,
so the two agree from power-on. This is what makes one ribbon enough.

## What the emulator showed

`software/s5emu/tests/test_front_panel.py` runs the board from its netlist, alone and with CPU Rev D and the IO panel
card from theirs:

- the two headers follow `tools/s5panel.py` pin for pin;
- a program toggled in from the front panel lands in memory one byte a press and runs, the displays following it;
- RESET clears the flag and its copy, and the machine comes up in HBIOS;
- RESET does nothing while LOAD is on;
- the CPU card's own switch and the bus driver's `MODE:4#` clear the copy too;
- every toggle and button is played as the netlist wires it (2026-11-23, `hw.switch_contact`), and the IO panel card
  is given what this board's own nets put on the ribbon: a switch wired to the wrong place fails the tests as it
  would fail on the bench (the toggles' resistors to ground, a button to +5V, a toggle off its line: each tried).

Work on this board found a fault in the IO panel card as it was drawn: its DMA request lasted too long and would
have loaded every byte twice on a real 1802. It is put right there (`hardware/io-panel/kicad/rev-a/DESIGN.md`).

## A thing to know: the address display in LOAD mode

The 1802's data sheet says that TPA is left out of the idle cycles of LOAD mode. The address displays' high byte is
latched by TPA, so in LOAD mode the two left digits change only when a byte is loaded, and show the page of that
byte; the two right digits follow R(0) all the time. After loading the byte at 00FF the display reads 0000, not 0100,
until the next byte goes in. The IO panel card's own displays do the same. It is how the latches are clocked, on the
IO card; nothing on this board could change it.

## Building it

`gen/build.sh` makes everything from `gen/netlist.py`: the schematic, the board (`gen/make_board.py`), the route
(`gen/route.py` and Freerouting), the checks and the order files. Before an order the board must pass `pcb-check`
and Ken must have seen the result.

## Open

- How the panel is held in a case, and whether a plate goes in front of it, is not decided. The toggles are the IO
  card's Marquardt M9040P, 0.5 in apart.
- J1's solder joints on the front, and the logic row on the front: Ken has not seen the board yet.
