# BUSDRV-C (bus driver Rev C): design notes

The next bus driver: BUSDRV-B's job (an Arduino Nano you talk to over USB, reaching every bus line through MCP23017 I²C
expanders, for bring-up, memory tests and CPU tracing) on **all 36 bus positions**, so that **with the CPU card in place
it can pause, step and load memory** (LOAD mode and DMA IN), plus a **clock output** and **probe inputs** on the Nano's
own pins. Started 2026-11-17 (Ken: "update bus driver to 36 pin so among other things it can drive load mode"; the
backlog item of 2026-10-30). **The board is drawn (2026-11-18, section "Board"); the firmware and host tools are
written (2026-11-20, section "Firmware and tools" at the end) and have run only in the simulator: there is no
BUSDRV-C, bus Rev D or CPU Rev D to run them on.** This file collects the decisions and the proposals still to agree.
BUSDRV-B (`../rev-b/README.md`) is the reference: what is not said here stays as there.

## Decided (Ken)

| | |
|---|---|
| Bus | All 36 positions of the bus Rev D's slots (`hardware/bus/kicad/rev-d`, `docs/manual/bus.md`): 34 signals, SC0 (position 36) read only (2026-10-30) |
| Expanders | A third MCP23017 for the six extension lines (2026-10-30) |
| Open collector | -EF1..-EF3, -PAUSE and -DMAIN driven low or left floating, as BUSDRV-B does -RESET, -INT and -EF (2026-10-30) |
| Clock | An EXT CLK output from a Nano timer, wired to the CPU card's EXT CLK pin (CPU Rev D: J2 pin 1, JP1 = EXT): run the 1802 at a set rate as well as step it, faster than through I²C (2026-10-30) |
| LOAD mode | The main reason for this revision: with the CPU card in place, LOAD mode and DMA IN fill RAM (2026-10-30, 2026-11-17). **By the clock, no extra chips** (option B below; Ken, 2026-11-17) |
| Probe | Spare pins to sense a probe (2026-11-17) |
| Layout | The board layout rules: the Nano at an edge other than the bus's, its USB facing out; headers at an edge; every reference and value on the silkscreen |

## How LOAD mode fills RAM (CPU Rev D)

After a reset CPU Rev D's boot map puts the EPROM at every address (it holds -VMA high, so the memory cards stay off)
until the first access with A15 high, unless its LOADED flag (U8A) is set. **LOAD mode sets LOADED:** the moment
-RESET and -PAUSE are both low, U5D's LOAD_L presets U8A and the boot map is off, so 0000-EFFF is RAM. LOADED stays
set through bus resets; only the RESET/RUN switch or power-on clears it (and brings the HBIOS boot back). The bus
driver then:

1. pulls -RESET low (the 1802 resets: R0 = 0000), then -PAUSE low too: LOAD mode;
2. for each byte: puts it on D0-D7 and requests one DMA IN (-DMAIN low): the 1802 puts R0 on the address bus, the
   memory writes the byte on -MRW, and R0 counts up;
3. releases -PAUSE (reset), then -RESET: RUN. The 1802 starts at 0000, in RAM, and runs what was loaded.

The emulator already runs this for CPU Rev D (`python3 -m s5emu --hw --cpu-rev D`; `tests/test_hw.py`, `CPURevD`).
Today's CPU Rev A has no LOADED flag: its boot overlay would take the writes.

**Two hazards**, which the IO panel card solves in hardware for its INPUT button (`hardware/io-panel/kicad/rev-a/gen/netlist.py`)
and BUSDRV-C by the clock (option B, below):

- **One write per byte.** While -DMAIN is low the 1802 makes a DMA write every machine cycle (4 us at 2 MHz); an
  expander pin takes about 100 us to change over I²C, far too slow to let go in time.
- **The data lines only during the DMA write.** In LOAD mode the idle 1802 keeps reading M(R0) (-MRD low), so the
  memory card drives D0-D7 between the DMA writes; BUSDRV-B's expanders drive D0-D7 straight, and would fight it.

## Proposed (to agree with Ken)

1. **Pins: BUSDRV-B's U1 and U2 unchanged**, so its firmware, `fwsim.py` and `backplane.py` stay valid:
   U1 (0x20) GPA0-6 D0-D6, GPB0-6 A0-A6; U2 (0x21) GPA0-6 D7, A7, TPA, TPB, -MRD, -MRW, -VMA, GPB0-6 Q, -RESET, -INT,
   -EF, N0-N2. **U3 (0x22)**: GPA0-5 -EF1, -EF2, -EF3, -PAUSE, -DMAIN, SC0 (read only); GPA6 and GPB0-6 eight spare
   pins, in or out (SPARE5-12). GPA7/GPB7 are output-only on every MCP23017 (as on BUSDRV-B): SPARE1-4 on U1 and U2,
   SPARE13-14 on U3.
2. **LOAD mode by the clock: decided, option B (Ken, 2026-11-17).** The Nano runs the 1802's clock (CLK OUT, item 3,
   wired to the CPU card's EXT CLK with JP1 on EXT) and steps it through each DMA write, with the expanders read and set
   between edges: -DMAIN low until the 1802 has taken the request (it samples DMA requests at TPB; the next cycle is the
   DMA cycle, SC0 low in LOAD mode), then high again so that only one DMA cycle follows; D0-D7 turned to outputs with
   the byte only while -MRD is high in that cycle, and back to inputs once -MRW has risen, before the idle cycle's
   memory read. No more chips; every clock edge waits for I²C, so about 5-10 minutes for 28K. (Option A, not taken:
   the IO panel's REQ/ACK flip-flops and a 74HCT244 gated by -MRD, at the CPU card's own clock: a few seconds, two
   more chips.)
3. **Clock: Nano D9** (Timer 1, OC1A) through a series resistor to **CLK OUT** on the front header: a steady clock at
   16 MHz / 2n (8 MHz down), or single edges; wired to the CPU card's EXT CLK. Replaces BUSDRV-B's stepping from SPARE1
   (an expander pin, about 100 us an edge; `CLK:n`).
4. **Probes: two inputs on the front header**, each through 1k to a Nano pin, high impedance otherwise: **PROBE1 on D8**
   (Timer 1's input capture: the time of each edge, to 62.5 ns) and **PROBE2 on A1** (a pin-change interrupt). With
   CLK OUT they make a small logic probe and counter for any line on any card.
5. **Nano pins:** D2, D3 INTA of U1, U2 (as BUSDRV-B); D4 XRST; D5 INTA of U3; D8 PROBE1; D9 CLK OUT; A0 BUS_SENSE
   (as BUSDRV-B); A1 PROBE2; A4/A5 I²C. Free: D6, D7, D10-D13, A2, A3 (A6, A7 analog in only).
6. **Headers at the front edge, each pin named on the silkscreen:** J2 CLK OUT, PROBE1, PROBE2, SPARE1-4 (outputs),
   +5V, GND; J3 SPARE5-12 (in or out), SPARE13-14 (outputs), GND.
7. **Board:** a 36-pin card, 5.50 x 4.00 in as CPU Rev D (the 36-pin connector clears the card supports), J1 = CPU Rev
   D's `C36` down the left edge; 2 layers; generated from `gen/netlist.py` with the fixed-order routing
   (`tools/kicad/dsn_order.py`) like CPU Rev D; `pcb-check` before an order.
8. **Firmware and host tools:** commands for the new lines (-EF1..3, -PAUSE, -DMAIN, SC0), the modes (RESET, RUN,
   PAUSE, LOAD), a DMA byte and a DMA block from the host (`LOADBLK`), the clock (rate, stop, step) and the probes (read,
   count, time an edge); `software/busdrv` (`s5busdrv.py`, `bringup.py`, `fwsim.py`, `backplane.py`) to match.
   **Written 2026-11-20** (Ken: do it), taking proposals 1-8 as the specification: "Firmware and tools", at the end.

## Board (2026-11-18): `gen/netlist.py`, `gen/make_schematic.py`, `gen/make_board.py`, `gen/build.sh`

Drawn from proposals 1, 3-7 above and the DEBUG cable (Ken, 2026-11-18: "can we make cpu debug header 2x3 with match
header on debug card going to non bus 32017 pins?"); nothing here is ordered or agreed beyond what the table says.

- **Expanders:** U1 (0x20) and U2 (0x21) as BUSDRV-B, pin for pin. U3 (0x22): GPA0-5 -EF1, -EF2, -EF3, -PAUSE, -DMAIN,
  SC0; GPA6 SPARE5; **GPB0-2 the DEBUG cable's CLOCK, SC0 and SC1** (DBG_CLOCK, DBG_SC0, DBG_SC1: the "non-bus
  MCP23017 pins"); GPB3-6 SPARE6-9; GPA7 / GPB7 SPARE10-11 (output only). The spares are numbered SPARE5-9 (in or out)
  and SPARE10-11 (out) now, where proposal 1 had SPARE5-12 and SPARE13-14, since the DEBUG cable takes three.
- **J4 DEBUG:** a keyed 2x3 box header (`Connector_IDC:IDC-Header_2x03_P2.54mm_Vertical`), CPU Rev D's J2 signals in the
  same order: 1 CLK OUT (to the CPU's EXT CLK), 2 GND, 3 CLOCK, 4 SC0, 5 SC1, 6 GND; a straight 6-way ribbon joins the
  two. Its rows are named on the silkscreen as on the CPU card ("CLK OUT  GND", "CLOCK  SC0", "SC1  GND").
- **Nano (U4**, not A1 as on BUSDRV-B: J1's pin label A1 would read as its reference): D2, D3, D5 the three INTAs; D4 XRST; D8 PROBE1 and A1 PROBE2, each through 1k (R8, R9) from J2; D9 CLK OUT
  through 100 ohm (R7) to J2 and J4; A0 BUS_SENSE (R4 / R5); A4 / A5 I2C (R1, R2 4.7k to bus +5V); R3 10k XRST's
  pull-up. Its own +5V pin is not connected: it runs from its USB, as on BUSDRV-B.
- **J2** (1x9): CLK OUT, PROBE1, PROBE2, SPARE1-4, +5V, GND. **J3** (1x8): SPARE5-11, GND. Every pin named.
- **Layout:** 5.50 x 4.00 in, J1 (`s5bd:C36`, the IO panel's) down the left edge with its pins named; U1-U3 on end in
  a column beside it, each with its 0.1 uF; the Nano at the front edge with its USB facing out; J4 at the top front
  corner, J2 and J3 down the front edge; the PWR LED at the front, labelled by its function (`pcb-check.ini` exempts
  LED1 from the reference rule, as on CPU Rev D and the IO panel); the card-support strips kept free.
- 2 layers, GND pours both sides, +5V 0.5 mm (the Power class), Freerouting on the fixed-order input (`gen/route.py`).
- **Silkscreen at 270 (Ken, 2026-11-18: "yes convert bus driver silk to 270"):** every text reads upright with the card
  standing in the bus, connector down. The labels moved from `make_board.py` into `gen/silk.py` (which `make_board.py`
  calls, and which rewrites the routed board's silkscreen with its copper untouched), on `tools/kicad/silk270.py`, as on
  CPU Rev D: each at the first spot clear of every pad, part, other text, the edge and the card-support strips. J1's pins
  in two staggered columns, J2's and J3's in three (their names run to seven letters); the DEBUG header's pins in a legend
  under it; the expanders with what each carries; the name line alone at 0 along the bottom edge as drawn, "System-5 bus
  driver  Rev C  2026" with cottageworker.com (no BUSDRV-C on the silk: one naming for every card, Ken, the same day).
  75 texts at 270 and 2 at 0 (all were at 0 or 90); copper unchanged; `tools/preorder_check.py --layers 2` PASS.
- **The slot order of 2026-11-18** (Ken: "looking at the bus from the power supply end I want the right most pin to be
  gnd followed by the next original pin order all the way to +5v/vcc, then EF1, EF2, EF3, -DMAin, SC0", -PAUSE kept at
  the far end, and the slot counted from GND: "start counting at gnd as pin 1, there +5v is 30 and then the pins beyond
  5v"): J1's positions 1-30 the 30-pin bus from GND (1) to +5V (30), 31-33 -EF1..-EF3, 34 -DMAIN, 35 SC0, 36 -PAUSE,
  from `gen/netlist.py`'s `POS`, as the bus Rev D's; the C36 footprint turned end for end, so its pad 1 is the GND end.
  U1-U3 keep every pin (the firmware's port map is BUSDRV-B's still): only the tracks between them and J1 moved, so the
  board was routed again, on seed 7 (`gen/route.py`; of seeds 0-11, eight route every net). J1's pin names follow
  `POS`; "-PAUSE", at the end pin beside the card-support strip, sits one column further out and 0.5 mm towards the
  middle (`tools/kicad/silk270.py`'s `pin_names`: it had been left out without a word), and `make_board.py` now stops
  if any label finds no room. The card no longer fits the 2009 backplane: it needs the bus Rev D.
  `tools/preorder_check.py --layers 2` PASS; `pcb-check` at elf `31c54a8` (pcb-check `60fd275`; no tests of its own
  yet): **no failures, the same 2 warnings** (the Nano's AREF and two RESET pins left open: the module sees to them; the
  MCP23017 not in pcb-check's footprint table), the 36 bus pins on J1 as defined.
- **The bus header drawn as the part it is; "J1 BUS" out from under it (the night of 2026-11-18).** J1 is a single-row
  right-angle pin header: its plastic body lies on the board between the pads and the card edge, 1.5 to 4.0 mm from the
  pads, and its pins run on past the edge (the photos of the built MEM3-E and BUSDRV-B show it). The C36 footprint had
  pads and a courtyard round them and no body, so the label placer and `pcb-check` took that strip for free board, and
  `J1 BUS` was printed in it, at the connector's middle: under the header on a built card. Found on VIDEO-G (its
  `kicad/README.md`). The footprint (`s5bd.pretty/C36`) now carries the body (F.Fab), a courtyard round body and pads,
  and KiCad's 3D model of the header, so the render shows the connector; `J1 BUS` stands on the board side of the pin
  names, at the connector's middle (`tools/kicad/silk270.py`, `bus_label`). Silkscreen only: `gen/silk.py`
  brought J1's drawing up to the footprint (`tools/kicad/fp_update.py`) and placed the labels again; no other label
  moved, every track, via, pad and zone is the same, and a new build gives Freerouting the same input. DRC 0 errors and
  0 warnings; `tools/preorder_check.py --layers 2` PASS. `pcb-check` at elf `d1df002` (2026-11-19, pcb-check `71c4bef`):
  **no failures, the same 2 warnings** (the Nano's AREF and two RESET pins open; the MCP23017 not in its footprint
  table); LABELS: every reference and value clear of the parts. The same at elf `b4692e9` with pcb-check `bd032dd`,
  whose new BODIES line passes (every part drawn with its body), and at `b2252b7` with pcb-check `0b45f65`.
- **Still to do:** Ken's review of the board (with the three points under "For the board's review" below); then
  `pcb-check` before any order. The firmware and `software/busdrv` are written (next section); what is left of them is
  to run them on real cards.

## Firmware and tools (2026-11-20)

Ken, 2026-11-20: do the firmware, host tools, simulators and emulator model. Proposals 1-8 above were taken as the
specification, on the board as drawn. **Nothing here has run on hardware.** The sketch compiles; its bus steps were
tried against the cards' netlists in the simulator.

- **One sketch for both boards** (`embedded/bus-driver/s5-bus-driver`): when the bus has power it looks for U3 at
  0x22 and says `BUSDRV-B` or `BUSDRV-C` in its banner. U1 and U2 being the same pin for pin, every BUSDRV-B command
  makes the same port writes as before; the new commands answer "needs BUSDRV-C" on a Rev B. 21,226 bytes of flash
  (69%) and 1,091 of RAM (53%) on the Nano, 0 warnings from the sketch. Its header has the command list.
- **The new commands**, all in MONITOR mode with the CPU card in place: the five open-collector lines by name
  (`-EF1:1#` ...), `MODE:0..3#` (RUN, RESET, PAUSE, LOAD), `DMA:val#`, `LOADBLK:count,hh..#`, `CLKHZ:hz#`,
  `CLKSTOP:0#`, `CLK:n#` (n edges on D9), `DBG:0|1#` (the cable's inputs; does CLK OUT reach the 1802?), `PROBE`,
  `PCOUNT:ms#`, `PTIME:ms#`, `PDELAY:e#`, `SPDIR:mask#`, `SPIN:0#`; `SPARE`, `SNAP`, `STATUS` and `WATCH` take in U3.
- **LOAD mode by the clock, as run** (option B): SC0 high (idle); -DMAIN low; one clock edge at a time until SC0
  falls (the DMA cycle has begun); -DMAIN let go at once; -MRD seen high; the byte on D0-D7; edges until -MRW has
  gone low and come back; D0-D7 let go; edges until SC0 is high again. The address of each write is read off the bus
  (high byte during TPA, low byte during -MRW) and must run on by one. 47 expander transactions a byte (counted in
  the simulator); at about 0.15 ms each, which is an estimate, that is some 7 ms a byte and 28K in a little over
  three minutes (the estimate above was 5-10).
- **Host tool** (`software/busdrv/s5busdrv.py`): `mode`, `dmaload`, `loadrun` (a hex or binary file into RAM through
  LOAD mode, then RUN at the card's clock), `clkhz`, `clkstop`, `clk`, `dbg`, `clktest`, `line`, `probe`, `pcount`,
  `ptime`, `pdelay`, `spdir`, `spin`. **Bring-up plans** (`bringup.py`, `BRINGUP.md`): `bus36` (the bus Rev D's pull
  resistors and the eight open-collector lines, CPU card out) and `load` (the cable, the modes, a program loaded by
  DMA IN and read back by running it, -PAUSE, a bus reset).
- **Simulators:** `fwsim.py` is the sketch in Python for either board; `backplane.Backplane36` is the bus Rev D with
  a memory card and CPU Rev D from their netlists; `cpupins.py` is the 1802's pins one clock edge at a time. That pin
  model was run beside the real 1802 (the clock-stepped trace of CPU Rev A, 2026-10-31): the same TPA, TPB, -MRD,
  -MRW, N, Q and address bytes on every edge of 25,280 machine cycles. RESET, PAUSE, LOAD and the DMA cycle are not in
  that trace: they are from the data sheet, and `cpupins.py` lists each assumption. The one that matters most: **when
  the 1802 looks at DMA IN.** The data sheet says between TPB's leading edge and TPA's; the model takes TPB's
  trailing edge, and the tests pass with its leading edge too, since the firmware lets -DMAIN go at the first edge of
  the DMA cycle either way. The first real card will show.
- **Emulator:** `python3 -m s5emu --hw --cpu-rev D --buslink` answers as BUSDRV-C (the modes, LOAD mode with LOADED,
  the flag lines); it has no clock edges, so the clock and probe commands are stand-ins there.
- **Tests:** `software/busdrv/test_busdrv_c.py` (32) and `software/s5emu/tests/test_buslink_c.py` (9), with the 26
  older ones unchanged and passing.

### Choices made beyond the proposals

- `MODE` lets one line go before it pulls the other in every change but LOAD, so LOADED is set only on purpose; LOAD
  always passes through RESET; with the clock stopped, RESET and LOAD give the 1802 32 clock edges.
- `MASTER:1#` on BUSDRV-C is refused while its clock runs and when the DEBUG cable shows a CPU card (the test costs
  that CPU eight clock edges). BUSDRV-B could not tell a stopped CPU card from an empty slot.
- CLK OUT is limited to 2 MHz (Timer 1 could make 8): the cards are timed for 2.
- `CLK:n#` trace lines carry U3's two ports on BUSDRV-C, with the cable's CLOCK bit left out (it changes on every
  edge); `cputrace.py` reads both kinds of line and shows the state code.
- The probes: `PCOUNT` counts with pin-change interrupts (good to some tens of kHz: the interrupt's own time sets
  the limit, not measured); `PTIME` and `PDELAY` need the steady clock
  stopped, because Timer 1 makes it. `PDELAY` (a clock edge to PROBE1's next edge) is the "logic probe with CLK OUT"
  of proposal 4; with PROBE1 on CLK OUT it measures its own offset.
- SPARE5-9 are inputs until `SPDIR` makes them outputs; U3's pull-ups are on for the three DEBUG inputs only, so no
  cable reads 1 1 1.
- A file for `loadrun` that does not start at 0000 gets zeros below it and a long branch at 0000.

### For the board's review (not changed: the board is as drawn)

1. **CLK OUT can feed an unpowered CPU card.** The header of `gen/netlist.py` says a powered-down System-5 is never
   fed from USB. CLK OUT is the one line that goes from the Nano (USB power) straight to another card: D9, R7 100
   ohm, the cable, the CPU card's U7A input. D9 high with the bus off would push about 40 mA through that input's
   protection diode. The firmware makes D9 an input whenever A0 says the bus is off, and D9 starts as an input; but
   that is the firmware keeping a promise the board does not. **R7 at 1k** would keep it by itself (4 mA) and is still
   fast enough for 2 MHz into a 6-way ribbon and one HCT input.
2. **-RESET let go is not -RESET high.** CPU Rev D's DS1813 holds the bus -RESET low for 150 ms after anything
   that pulled it lets go. A bus driver that released -RESET and pulled -PAUSE straight after (RESET to PAUSE) would
   have both low for 150 ms: LOAD mode, and LOADED set, by accident. The firmware waits to see -RESET high before
   it pulls -PAUSE, and refuses if it never comes. Nothing to change on either board; the IO panel's RUN and LOAD
   toggles can do the same thing by hand.
3. **SC1 is on the cable only**, SC0 on the bus as well. The firmware needs SC0 alone (from the bus), and the
   cable's CLOCK for its test that CLK OUT arrives. So LOAD mode needs the cable for the clock, not for the state
   codes; U3's GPB1 and GPB2 (DBG_SC0, DBG_SC1) are read by `DBG` and `SNAP` and the trace, nothing more.

