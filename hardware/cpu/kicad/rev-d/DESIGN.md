# CPU Rev D: design notes

A new System-5 CPU card for the 36-pin bus: the CDP1802, its clock, reset and run control, and a 4K boot EPROM with the boot remap.
Nothing else: no 1861 video, no ribbon to an IO card. Started 2026-10-30 (Ken) and drawn the same day; this file collected the decisions
and the proposals as they were made. **Status (2026-11-21): a sixth LED, RAM, for the LOADED flag (the last section); passes `pcb-check` so; not ordered** (Board, below). The Rev A card (`../rev-a/`, `docs/manual/cpu-card.md`) is the reference.

## Decided (Ken, 2026-10-30)

| Item | Decision |
|---|---|
| Scope | CPU, clock, reset/run, boot EPROM and its remap circuit. No 1861, no IO-card ribbon (SV3), no LCLK/SC/DMA OUT for it. |
| Bus | The 36-pin interface of the bus Rev D, in the order of 2026-11-18 (Ken), counted from GND: positions 1-30 the 30-pin bus (GND at 1, the slot's end pin, +5V at 30), 31-33 -EF1..-EF3, 34 -DMAIN (LOAD mode only), 35 SC0, 36 -PAUSE; until then, counted from the other end, 1-3 -EF1..-EF3, 4-33 the bus, 34-36 -PAUSE, -DMAIN, EXP = SC0. See `docs/manual/bus.md`, "The 36-pin extension". |
| Internal clock | A 4 MHz canned oscillator, divided by 2 (74HCT74): **2 MHz at the 1802**. The old cards' 1.79 MHz was for the 1861. |
| External clock | An **EXT CLK header pin** on the card, wired from a debug board (the bus driver's J2 spare) with a jumper wire; not on the bus (EXP stays free, Ken 2026-10-30). A jumper picks **INT / EXT**. The 1802 is static, so the debug board can run it slowly or step it edge by edge. |
| Boot EPROM | A **4K 2732** at F000-FFFF, as on Rev A, so today's HBIOS 1.0.4 chip moves across. |
| Layout | The board layout rules (front-edge switches and LEDs, labels, readable references, IC types), `cottageworker.com` and the board name/revision on the silkscreen, 0.1" bypass caps. |
| Layers | **2 copper layers if at all possible** (Ken, 2026-10-30): cheaper and quicker to check; `pcb-check --layers 2`. Go to 4 only if routing truly fails, and ask first. |

## Proposed (to agree with Ken)

1. **Clock select.** A 3-pin jumper CLK: INT (the ÷2 output) / EXT (the EXT CLK header pin through a 74HCT14 Schmitt buffer, with a 10k pull-down so an
   unconnected pin holds the clock low rather than floating). The 1802's CLOCK pin is driven by one or the other, never both; XTAL left open.
   A test pin for the 1802 clock. The EXT CLK pin goes at a board edge (header rule) with a GND pin beside it. The bus lines' meanings
   are drafted in `docs/manual/bus.md`, "The 36-pin extension"; EXP = SC0 (Ken, 2026-10-30; position 35 since 2026-11-18), driven by the CPU card through a buffer (`bus.md`); -DMAIN is LOAD mode only.
2. **High address latch.** Fix finding T1: a 74HCT373 (transparent while TPA is high, as Rev A was drawn) instead of the 374 fitted on
   Rev A, so the high byte is caught before TPA falls.
3. **Boot remap.** Rev A as built (A-built): the boot flip-flop's D and PRE high, clocked by latched A15, cleared by -RESET; the EPROM
   answers everywhere until the first access with A15 high, then only at F000-FFFF, and -VMA is low everywhere else. **No window
   or VMA-mode jumpers** (Ken, 2026-10-30): Rev A's SV2/SV4 (window) and SV5 (Boot/REMAP, Boot only, No ROM) are dropped; the card
   is always Boot/REMAP with the EPROM at F000-FFFF.
4. **Debug control: -PAUSE and -DMAIN** (Ken, 2026-10-30; replaces CPU-generated -INP/-OUT: I/O cards keep their own decode).
   Position 36 -PAUSE (open collector, a level; 34 when this was proposed, before the slot order of 2026-11-18): while low the
   card holds the 1802's WAIT low. Position 34 -DMAIN (open collector; 35 when proposed) to the 1802's DMA IN, through the DMA
   interlock since 2026-11-22 (DMA_ARMED: the 1802 takes it only when paused). With -RESET also low, -PAUSE puts the 1802 in LOAD mode, and each -DMAIN writes the bus byte to M(R0), R0 + 1.
   The debug board drives the data bus only while -MRD is high (the DMA IN cycle; in IDLE memory drives M(R0)); no SC0/SC1 needed.
   - **The boot remap must be off in LOAD mode.** -RESET clears the boot flip-flop, and while it is clear the EPROM answers at every
     address and -VMA keeps the memory cards off, so DMA writes from R0 = 0000 would go nowhere. Set the flip-flop (boot map off)
     whenever WAIT and CLEAR are both low, or on the first DMA IN; check it in the emulator.
   - **The run latches take levels, not only pulses:** -PAUSE from the bus holds WAIT low for as long as it is low, alongside the card's
     own buttons and the RUN-after-reset pulse.
   - **SC0 on EXP (Ken, 2026-10-30):** a debug board stops at each instruction fetch (SC0 low while no DMA runs). SC1 to a test pin only.
5. **EF inputs: straight across, with jumpers** (Ken, 2026-10-30). Default EF1 = -EF1, EF2 = -EF2, EF3 = -EF3, EF4 = bus -EF (the
   2005 schematics' -EF4). The keyboard flag moves to -EF3 on the new video card, so HBIOS (which waits on EF3) needs no change.
   One jumper block per EF input picks its line; for the old 30-pin IO card, whose keyboard flag can only reach -EF, set EF3 = -EF.
   The IDE card uses no flag (the BIOS polls its status). All with pull-ups on the bus Rev D already.
   **Drawn 2026-11-17** (Ken: "have EF selectable from all EF lines"): JP2-JP5, one 2x4 block per input (EF1-EF4), each
   row a bus flag line (-EF1, -EF2, -EF3, -EF), a jumper across a row puts that line on the block's input. The board
   first had only JP2 (straight across) and JP3 (-EF to EF3).
6. **Reset and run** (Ken, 2026-10-30): a front-edge **RESET / RUN switch**, a two-position toggle labelled RESET and RUN at its ends:
   RESET holds -RESET low, RUN releases it and the 1802 runs (the RUN pulse after reset, as on Rev A). Keep the CM1232/DS1232 power-on
   reset. **A debug board drives it too**: -RESET on the bus is open collector, so the bus driver (it already drives -RESET) or a
   jumper wire pulls it low alongside the switch, and -PAUSE (item 4) pauses and, with -RESET, gives LOAD. With the switch on RUN
   the debug board is in control; on RESET the switch wins. **PAUSE and LOAD are not on this card** (Ken, 2026-10-30, option B): the
   CPU card only listens to -PAUSE and -DMAIN; the new IO card (switches, by hand) and the debug board (from the Mac) drive them,
   either one alone or both together (open collector). A PAUSE LED on this card shows the mode.
7. **LEDs (front edge, labelled):** PWR, Q, WAIT, CLEAR, VMA, and CLK EXT (on while the external clock is selected). As drawn:
   LED1 PWR, LED2 Q, LED3 PAUSE (WAIT low), LED4 RESET (CLEAR low), LED5 ROM and LED6 START FROM RAM; no VMA or CLK EXT LED.
8. **Timing.** Rerun `python3 -m s5emu.timing 2` and `contention()` at 2 MHz; Rev A's review was at an assumed 1.76 MHz. Watch T6
   (IDE card, `BACKLOG.md`): INP 3 into RAM fails worst case from about 2.2 MHz, so 2 MHz leaves little margin.
9. **Folder.** `hardware/cpu/kicad/rev-d/` with `gen/netlist.py`, `make_schematic.py`, `make_board.py`, as for the bus Rev D; a
   `schematic/spec.py` and lines in `build_all.sh` / `make_book.py` for the schematic book.

## Netlist (2026-10-30): `gen/netlist.py`, `gen/make_schematic.py`

The circuit is written; ERC 0 (`reports/erc.rpt`), 87 nets, none with a single pin. Board not started. Choices made while
writing it (for Ken to review):

(This section is the record of 2026-10-30. Where the boot reset of 2026-11-22 changed it, the change is marked
**[2026-11-22]**; "A boot reset on the bus, and the DMA interlock", below, has the whole of it.)

- **No run latches, no one-shot.** -RESET and -PAUSE are levels now, so CLEAR = -RESET and WAIT = -PAUSE through two Schmitt
  inverters each (U7): reset, run, pause and load follow directly. Rev A's two 74LS20 latches and the 74LS123 are gone.
- **DS1813, not CM1232/DS1232.** Rev A's CM1232 has a watchdog strobed by TPA; TPA stops in PAUSE, in LOAD and with the external
  clock stopped, so it would reset a paused or stepped machine within a second. The DS1813 (TO-92) is power-on reset and a
  debounced push-button input on one open-drain pin, which sits on the bus -RESET; no watchdog.
- **SW1 RESET/RUN** grounds SW_RST: through D1 (BAT85) that pulls -RESET (the DS1813 then holds it 150 ms after release), and it
  clears LOADED. C12 on SW_RST clears LOADED at power-on. **[2026-11-22]** D1 and the 1 uF C12 are gone: a second DS1813,
  U12, holds SW_RST low at power-on and for 150 ms after SW1; U11 (74HC03, open drain) puts it on the bus, -RESET (U11A)
  and -DMAIN (U11B, not while paused), a boot reset, and LOADED is cleared by any boot reset on the bus (BOOT_L =
  NAND(RST_H, DMAIN_H, WAIT), U6B). C12 is U11's 0.1 uF now.
- **LOADED (U8A)** decides what a reset boots: set by LOAD mode, cleared by SW1 and power-on. While it is set the boot map stays
  off, so after loading a program at 0000 the ELF sequence LOAD → RESET → RUN runs it from RAM; SW1 (or power-on) boots HBIOS.
  A reset from the bus (the debug board, the IO card) leaves LOADED as it is. **[2026-11-22]** A plain reset (-RESET alone)
  still does; a boot reset (-RESET and -DMAIN low together, -PAUSE high), from SW1, the front panel's or the IO card's
  RESET button or the bus driver's `MODE:4#`, clears it. Checked as a gate-level walk-through of power-on,
  boot, bus reset, LOAD → RESET → RUN, PAUSE and SW1.
- **Consequence for the IO panel card:** its hand controls become the COSMAC ELF's **RUN** and **LOAD** toggles (RUN off pulls
  -RESET, LOAD on pulls -PAUSE; LOAD mode = RUN off + LOAD on), not PAUSE and LOAD; PAUSE is RUN on + LOAD on.
- **Bus lines driven:** -VMA push-pull from U5B (only the CPU card drives it), SC0 through U9D/U9E, -RESET open drain (U10, D1).
  Unbuffered as on Rev A: D0-D7, A0-A7, TPA, TPB, -MRD, -MRW, Q, N0-N2.
- **Pull-ups on the card** (RN1, 10k): -RESET, -INT, -PAUSE, -DMAIN, -EF, -EF1-3, so the card also worked on the 2009
  backplane, which has none (since the slot order of 2026-11-18 it no longer fits that backplane: there its +5V pin
  would meet D2); RN2 holds EF1-EF4 high when an EF block has no jumper.
- **Parts:** U1 CDP1802ACE, U2 74HCT373, U3 2732, U4/U8 74HCT74, U5 74HCT00, U6 74HCT20, U7/U9 74HCT14, U10 DS1813-10,
  X1 4 MHz DIP-8 oscillator; J1 the 36-pin bus (footprint to settle with the board: a placeholder 1×36 header), J2 DEBUG
  (a keyed 2×3 since 2026-11-18: EXT_CLK, GND, CLOCK, SC0, SC1, GND), JP1 CLK INT/EXT, JP2-JP5 the EF blocks (2×4 each); LEDs PWR, Q, PAUSE, RESET, ROM,
  and RAM since 2026-11-21 (the last section). Spare: U9C (input on ground); U6B and U8B, spare when this was written, are the boot reset's
  BOOT_L and DMA_ARMED since 2026-11-22.
- **Symbols:** KiCad's stock 74xx symbols are one unit per gate, which the generator cannot place, so the logic uses one-unit
  project symbols (`s5cpu.kicad_sym`, written by make_schematic.py from `netlist.CHIPS`, pinouts from the data sheets). The
  readable drawing is the redrawn schematic (`tools/kicad/sch/gen_schematic.py`), still to set up (`schematic/spec.py`).

## Board (2026-10-30): `gen/make_board.py`

- **5.50 × 4.00 in** (139.7 × 101.6 mm; Ken, 2026-10-30: a 36-pin card is 0.25 in taller than the 30-pin cards so the
  connector clears the card supports). J1 = `s5cpu:C36` (the 30-pin cards' C30 with three positions added at each end) down
  the left edge, centred (since 2026-11-18 its positions 1-30, from the GND end, carry the 30-pin bus, so a 30-pin card in the same
  slot sits 7.6 mm towards the GND end; the footprint is turned end for end so that its pad 1 is GND); the 3.00 × 0.15 in support strips along the top and bottom edges are copper keep-outs.
- **2 layers**, GND pours both sides. **Built by `gen/build.sh`** since 2026-11-17 (schematic, ERC, netlist, board,
  Freerouting, DRC, order files, `tools/preorder_check.py --layers 2`): Freerouting's input in a fixed order
  (`gen/route.py`, `tools/kicad/dsn_order.py`, as VIDEO-G's), so the board routes the same way every time; +5V 0.5 mm
  wide (the project's Power class; pcb-check wants power on planes or on tracks of 0.5 mm or more, and GND has its
  pours: GND 0.5 mm too left no way past U3's address pins). 1020 segments, 37 vias (routing seed 1, with the slot order of 2026-11-18: below); DRC 0, parity 0, netlist 78/78
  MATCH. **`pcb-check` (2026-11-17, `--tests`): no failures, 0 warnings** (before an order on every system since
  2026-11-06; `hardware/BUILD-RULES.md`, section 2). Its footprint check took the 1802 from a table entry that
  pcb-check had not yet committed that evening; the older check, `tools/preorder_check.py`, passes too.
- Front edge (right): SW1 RESET/RUN (RESET with the lever up; a Marquardt 9070-1W since 2026-11-18, below), LEDs labelled PWR, Q, PAUSE, RESET, ROM, and **J2 DEBUG, a keyed 2×3 header**
  (Ken, 2026-11-18) for a 6-way ribbon to the bus driver BUSDRV-C's matching header (wire n = pin n), its rows
  named "EXT CLK  GND", "CLOCK  SC0", "SC1  GND"; JP1 CLK (INT/EXT) and the EF blocks JP2-JP5 ("JP2 EF1" ... "JP5 EF4", the bus lines named by the rows) along
  the bottom edge outside the support strip, below SW1; every chip's reference
  and type below it; "System-5 CPU Rev D 2026", cottageworker.com (until 2026-11-18 "S5CPU-D" over them).
- **Bus labels:** every J1 pin named on the silkscreen beside its pad (-EF1 … SC0, as on the bus slots).
- **Emulator (2026-10-30):** `python3 -m s5emu --hw --cpu-rev D` runs the card from its netlist (s5emu: the 74HCT parts
  use the 2005 models, the symbols carry the same pin names; a new 4-input NAND model; the bus read by net name from the
  stock 36-pin connector; the CPU card class tracks the boot flip-flop and LOADED). HBIOS boots and echoes keys, ELF/OS
  boots from the CF image and runs FREE, with no bus events; LOAD → RESET → RUN runs RAM, a bus reset keeps LOADED, the
  RESET/RUN switch boots HBIOS (tests/test_hw.py: `CPURevD` 4 tests, `Boot` 1; all 26 pass).
- **Timing at 2 MHz (2026-10-30, `python3 -m s5emu.timing --cpu D 2`, `hardware/TIMING-REVIEW.md`):** the CPU card is
  clean (T1 gone with the 74HCT373; -VMA +608 ns, EPROM data +1825 ns). The limits are elsewhere: **the 6845 card's E high
  time fails above ~1.9 MHz** with its 1 MHz-grade HD46505RP (T3, -50 ns at 2 MHz), and T6 (IDE INP into RAM) is down to
  +15 ns. Either fit a faster CRTC grade on the video card or run at 1.79 MHz with a 3.579545 MHz can in X1's socket.
- **Decided (Ken, 2026-10-30): keep 2 MHz**; the video card that runs with it gets a faster CRTC grade (VIDEO-G: an HD68B45,
  `hardware/video-g/DESIGN.md`).
- **Silkscreen for pcb-check (2026-11-17):** "J1 BUS" along the bus edge; the LEDs are LED1-LED5 in the netlist, not D2-D6
  (J1's pin labels name the data lines D0-D7, and pcb-check took them for the LEDs' references), and **labelled by
  their function alone** (Ken, 2026-11-18: PWR, Q, PAUSE, RESET, ROM; `pcb-check.ini` `exempt_labels` lets their
  references go, and pcb-check names them in a NOTE); D1 by its own reference
  field; the 0.1 uF footprint has a courtyard and a body (as VIDEO-G's), so pcb-check finds each value.
  `pcb-check.ini` beside the board: the bus on the left edge (pcb-check finds bus connectors only by DIN 41612 names),
  the 36 positions from `tools/s5bus.py --positions 36`, the emulator's CPU Rev D tests.
- **Silkscreen at 270 (2026-11-18):** Ken's rule that every text reads upright with the card standing in the bus,
  connector down (he asked for it on this card that day, through the pcb-check session): the labels moved from
  `make_board.py` into `gen/silk.py` (which `make_board.py` calls, and which rewrites the routed board's silkscreen with
  its copper untouched), on `tools/kicad/silk270.py`, the placer VIDEO-G uses: every label at KiCad 270, at the first spot
  clear of every pad, part, other text, the edge and the two card-support strips, under its part with the card standing
  first. J1's pins named in two staggered columns; the switch's RESET and RUN at its ends; JP1's INT and EXT at its
  ends; the EF blocks' rows (-EF1 ... -EF) staggered under JP2; the DEBUG header's pins in a legend under it ("J2 DEBUG
  / 2 GND 4 SC0 6 GND / 1 EXT CLK 3 CLOCK 5 SC1"); D1's own field at 270 with "BAT85" after it, and its "K". The name
  line alone at 0 along the bottom edge as drawn, just above the strip ("System-5 CPU  Rev D  2026", cottageworker.com
  beside it; Ken that evening: one naming for every card, no code like S5CPU-D). 91 texts at 270 and 2 at 0 (was 95 at 0, 1 at 90); copper unchanged, every track, via,
  pad and zone compared; `tools/preorder_check.py --layers 2` PASS, DRC 0 errors and 0 warnings.
- **The slot order of 2026-11-18** (Ken: "looking at the bus from the power supply end I want the right most pin to be
  gnd followed by the next original pin order all the way to +5v/vcc, then EF1, EF2, EF3, -DMAin, SC0"; -PAUSE kept, at
  the far end; and the slot counted from GND, "start counting at gnd as pin 1"): J1's positions 1-30 the 30-pin bus
  (GND at 1, +5V at 30), 31-33 -EF1..-EF3, 34 -DMAIN, 35 SC0, 36 -PAUSE, from `gen/netlist.py`'s `POS`, as the bus Rev
  D's; the C36 footprint is turned end for end, so that its pad 1 is the GND end. The circuit is unchanged; J1's
  signals moved, so the board was routed again: seed 1 (of seeds 0-11, 1 and 2 route every net with the renumbered
  connector; 1020 segments, 37 vias; DRC 0 errors and 0 warnings, 0 unconnected, parity 0, the netlist proof 78 of 78;
  `tools/preorder_check.py --layers 2` PASS; `pcb-check --tests` at elf `31c54a8` (pcb-check `60fd275`, 2026-11-18): **no failures, 0 warnings**, the 36 bus
  pins on J1 as defined, the emulator's CPU Rev D tests and the HBIOS boot test passing). J1's pin names follow `POS`.
  The card no longer fits the 2009 backplane. **"-PAUSE" had no label:** at position 1 its name, 0.8 mm tall, came 0.01 mm
  into the card-support strip, and `silk270`'s placer left it out without a word (`make_board.py` did not ask it what it
  had missed). Now `pin_names` tries one column further out and 0.5 or 1.0 mm towards the connector's middle before it
  gives up ("-PAUSE" sits 0.5 mm below its pin, in a third column), and `make_board.py` stops the build if any label is
  left out.
- **Three moves at the front (Ken, 2026-11-18: "on cpu card move the jp1 between osc and jp2, move 4 ef jumpers down
  about 1.5 inches, change reset to same on yacc1"):**
  - **JP1 CLK INT/EXT** from the bottom edge to the top edge, between the oscillator X1 and the DEBUG header J2 (read
    "jp2" as J2: JP1 picks between the oscillator's clock and the EXT CLK that comes in on J2), INT at the end nearer
    the top edge, EXT at the other.
  - **The four EF blocks JP2-JP5** 1.5 in (38.1 mm) nearer the bus along the bottom edge ("down" with the card standing),
    and 2 mm further from that edge, so that JP2's last row and its name stay out of the card-support strip, which
    ends at 3.00 in from the bus edge.
  - **SW1 RESET/RUN a Marquardt 9070-1W**, the RESET/RUN toggle of Ken's YACC1 (its sequencer-logic card), as the bus
    Rev D's power switch that day: the footprint `s5cpu.pretty/SW_Toggle_SPDT_Marquardt_9070-1W` (YACC1-D's, its
    origin on the common), three terminals on 2.54 mm and two bracket legs, the body flush with the front edge, bushing
    and lever past it. Common (pin 2) to GND, pin 3 SW_RST: RESET with the lever up as drawn, towards the top edge, as
    before (a toggle closes the contact away from its lever: to check against a real part); pin 1, RUN, open. In place
    of the E-Switch 100 series. Its contacts only carry the reset line's milliamp.
  Routed again on seed 0 (the sorted order): 1029 segments, 35 vias; DRC 0 errors and 0 warnings, 0 unconnected, parity
  0, the netlist proof 78 of 78; `tools/preorder_check.py --layers 2` PASS; the emulator's CPU Rev D tests pass.
  `pcb-check --tests` at elf `26337ba` (2026-11-18, by the pcb-check session): **no failures, 0 warnings**. `cpu-rev-d-1to1.pdf` is the board at full size on a Letter sheet, to lay the switch and
  the other parts on (`tools/kicad/print_1to1.py`; `gen/build.sh` remakes it).
- **The DEBUG header and the bus driver's:** J2's pin 1 is 6.7 mm in from the front edge and 10 mm from the top edge;
  BUSDRV-C's J4 pin 1 is 7.7 mm and 8 mm (Ken, 2026-11-18: "debug connector approx same place on driver card?"): 1 mm
  and 2 mm apart, which a 6-way ribbon between neighbouring slots takes; left so.
- **The bus header drawn as the part it is; "J1 BUS" out from under it (the night of 2026-11-18).** J1 is a single-row
  right-angle pin header: its plastic body lies on the board between the pads and the card edge, 1.5 to 4.0 mm from the
  pads, and its pins run on past the edge (the photos of the built MEM3-E and BUSDRV-B show it). The C36 footprint had
  pads and a courtyard round them and no body, so the label placer and `pcb-check` took that strip for free board, and
  `J1 BUS` was printed in it, at the connector's middle: under the header on a built card. Found on VIDEO-G (its
  `kicad/README.md`). The footprint (`s5cpu.pretty/C36`) now carries the body (F.Fab), a courtyard round body and pads,
  and KiCad's 3D model of the header, so the render shows the connector; `J1 BUS` stands on the board side of the pin
  names, at the connector's middle beside U1 (`tools/kicad/silk270.py`, `bus_label`). Silkscreen only: `gen/silk.py`
  brought J1's drawing up to the footprint (`tools/kicad/fp_update.py`) and placed the labels again; no other label
  moved, every track, via, pad and zone is the same, and a new build gives Freerouting the same input. DRC 0 errors and
  0 warnings; `tools/preorder_check.py --layers 2` PASS. `pcb-check --tests` at elf `59d911e` (2026-11-19, by the
  pcb-check session): **no failures, 0 warnings**; its earlier passes had the label under the header, which it could not
  see.
- **Still to do before an order:** check the 36-pin card in the card guides (4.00 in); Ken's look at the pictures
  (`check-*.png`, the render) and the fab's gerber viewer; order it with the bus Rev D, whose 36-pin slots it needs.

## What a reset boots, and the RAM LED (Ken, 2026-11-21)

Ken, 2026-11-21: "if from either io or debug ram is loaded with program at 0000 how will it run after a reset since
that then forces rom to 0000, do we need a switch on cpu to specify run from boot rom or ram after reset". No switch is
needed: the card decides it by itself, with the LOADED flag (U8A; "Netlist", above). Both loaders, the IO panel's
LOAD toggle and the bus driver's `MODE` LOAD, use the 1802's LOAD mode, and LOAD mode sets the flag.

| What is done | LOADED | The next RUN starts in |
|---|---|---|
| Power on, or this card's RESET/RUN switch (SW1); since 2026-11-22 any boot reset (the front panel's RESET, the bus driver's `MODE:4#`: the next section) | cleared | the EPROM: HBIOS |
| LOAD mode: -RESET and -PAUSE both low (IO panel: RUN off and LOAD on; bus driver: `MODE` LOAD) | set | RAM at 0000 |
| A reset from the bus alone (IO panel: RUN off, then on; bus driver: `MODE` RESET, RUN) | as it was | whichever it was |
| PAUSE alone (-PAUSE low) | as it was | |

So LOAD, RESET, RUN runs what was loaded, a reset from the bus runs it again, and SW1 brings HBIOS back. The EPROM
still answers at F000-FFFF while the flag is set, so a loaded program can call HBIOS or jump to it (`C0 F0 00` at 0000
boots HBIOS without a hand on the card: the bus driver could not clear the flag until 2026-11-22; its `MODE:4#` does
now). Checked on the card's netlist
(`software/s5emu/tests/test_hw.py`, `CPURevD`) and, with the 1802's pins, in the bus driver's simulator
(`software/busdrv`, the `load` plan).

Three things the flag does that a user has to know:

- **It is set by LOAD mode itself, not by a byte being loaded.** Useful: pass through LOAD and a program already in RAM
  runs after the next reset. A trap: leave PAUSE (RUN on, LOAD on) by taking RUN off before LOAD, and both lines are low
  for a moment: LOAD mode, the flag set, and the next RUN starts at 0000 in RAM, not in HBIOS. SW1 puts it right.
- **SW1 clears it only if the bus is out of LOAD mode when SW1 goes back to RUN** (LOAD mode's preset is still held
  otherwise).
- **Nothing showed it.** With the machine held in reset the ROM LED was a guide (lit: the EPROM will boot) but for one
  case: the flag set and the last address before the reset in F000-FFFF, where the latch still holds F and the LED is
  lit although RAM will run.

Ken: "yes" to an LED for it. **LED6 RAM, with R8 (1k):** on the flip-flop's own Q output (U8 pin 5, the net `LOADED`,
unused until then), which sources the LED through R8 to its anode, the cathode on GND: **lit while LOADED is set**,
that is while a reset starts the 1802 in RAM. The five older LEDs sink into their signal; this one is on the spare
output, so that NOT_LOADED, the output that gates the boot map, carries no LED current. At the front edge under ROM,
6 mm on, above the RESET/RUN switch, R8 under R7; labelled by its function, as the others
(`pcb-check.ini`: `exempt_labels` takes LED6 too): first `RAM`, and the same day `START` / `FROM` / `RAM` (below).

The board was built again by `gen/build.sh` on seed 0, as before: 48 parts, 1024 segments, 32 vias; ERC 0, DRC 0
errors and 0 warnings, 0 unconnected, parity 0, the netlist proof 80 of 80; the redrawn schematic's Control sheet has
LED6 and R8, and the book was rebuilt; `tools/preorder_check.py --layers 2` PASS. The emulator's `CPURevD` tests have
`test_the_ram_led_shows_loaded` (the netlist's LOADED net through LOAD, RESET, RUN, a bus reset and SW1).
**`pcb-check --tests` on the committed files (2026-11-21, the board of elf `8bcae5d`, run at `7d529b4` with pcb-check
`4f59df7`): no failures, 0 warnings** (38 lines pass; its one note names the six LEDs labelled by function).

**The label: START / FROM / RAM** (Ken, the same day, when asked whether it should say `RAM` or `LOADED`: "change RAM
to Start From RAM, 3 lines each with one word under LED"). Three lines, a word each, under the LED with the card
standing in the bus (off its left side as drawn), level with it, the first word next to the LED; in capitals and at
0.8 mm, as the five other LED labels beside it (the capitals are the card's way with every function label; his words
were "Start From RAM"). `gen/silk.py`: `LED6_LABEL`, placed at the height the other five got and only at spots level
with the LED (the placer's nearest spot for three lines was beside the LED, 4 mm along the edge). The LED's value in
the netlist and the schematic stays `RAM`. **Silkscreen only:** `gen/silk.py` on the routed board; every segment, via,
zone, pad and part position the same as before, the copper, mask, outline and drill files changed only in their dates;
94 of the 95 texts where they were. DRC 0 errors and 0 warnings; `tools/preorder_check.py --layers 2` PASS.
**`pcb-check --tests` on the committed files (elf `735f80f`, pcb-check `f8c7489`): no failures, 0 warnings** (38 lines
pass; LABELS: every text clear of the parts).

## A boot reset on the bus, and the DMA interlock (Ken, 2026-11-22)

Ken asked for a front panel for a cased machine, with the CPU's reset on it, and then: "unless the IO panel via the
bus can do what the cpu card reset can do then we dont need line from cpu card all can come from io". Asked, he chose
"Boot reset on the bus, one ribbon". So what this card's RESET/RUN switch does had to become something any card can
do over the bus.

### What it was, and what was missing

SW1 did two things: it pulled the bus -RESET low through a diode (D1), and it cleared LOADED by a line of its own
(POR_L), with a capacitor (C12) to do the same at power-on. A reset from the bus could do the first and not the
second: once LOADED was set, nothing but a hand on this card brought HBIOS back.

### A boot reset is a state of the bus

**-RESET and -DMAIN low together, while -PAUSE is high, is a boot reset: reset, and start in the EPROM.**

-DMAIN is the line to mark it with because nothing else uses it outside LOAD mode, and LOAD mode needs -PAUSE low.
The card decodes the state and clears LOADED with it:

    BOOT_L = NAND(RST_H, DMAIN_H, WAIT)        U6B, the 74HCT20's spare half; WAIT is high while -PAUSE is high
    LOADED: set by LOAD_L (as before), cleared by BOOT_L        U8A

The card's own switch now makes that state on the bus, like any other source:

| Part | What it does |
|---|---|
| U12, DS1813-10 | on SW_RST: holds it low for 150 ms after power comes up and after SW1 is let go. In place of C12 |
| U11A, U11B (74HC03, open drain) | while SW_RST is low: U11A pulls -RESET; U11B pulls -DMAIN, unless -PAUSE is low. In place of D1 |
| U10, DS1813-10 | as before, on -RESET: holds it low 150 ms after whatever pulled it lets go, so -RESET outlasts -DMAIN |

With -PAUSE low SW1 pulls -RESET alone. That is LOAD mode, as it was before.

The DS1813's data sheet (Dallas, 111999) wants its pin under 0.4 V to take a pull for a push-button. The diode left
-RESET a diode drop above ground, which was marginal. An open-drain gate does not.

### The DMA interlock

A low -DMAIN must never reach the 1802 as a DMA request by mistake: that writes a byte at R(0) and moves R(0) on.
There are two ways it could.

- **While the machine is not paused.** A boot reset holds -DMAIN low then. So the 1802's DMA IN is closed whenever
  -PAUSE is high. System-5 makes DMA requests in LOAD mode only (`docs/manual/bus.md`), so nothing is lost.
- **At the moment LOAD is switched on with a boot reset held.** A source lets -DMAIN go when it sees -PAUSE fall,
  but that takes about a microsecond (the gates, then the line rising on its pull-ups), and for that microsecond the
  bus shows LOAD mode with -DMAIN low. About one time in five the 1802 would take it.

One flip-flop closes both (U8B, spare until now):

    DMA_ARMED: cleared while -PAUSE is high; set once -DMAIN is seen high with -PAUSE low
        ARM_L = NAND(PAUSE_H, DMAIN_N)         U11D, open drain, with R10; DMAIN_N from U9A
    DMA IN (the 1802's pin 38) = NAND(DMAIN_H, DMA_ARMED)        U11C, open drain, with R9

So a request counts only if the line was high first. It is logic, with no time constant in it, and the emulator
tests it (`CPURevD.test_dma_reaches_the_1802_only_in_pause_and_once_dmain_was_high`).

One thing follows for a card that loads by DMA: its request must start after LOAD mode has begun. The IO panel's and
the bus driver's do.

### Parts

In: U11 (74HC03), U12 (DS1813-10), R9 and R10 (10k), C12 (0.1 uF, U11's). Out: D1 (BAT85), the old C12 (1 uF).
U6B, U8B and U9A, spare until now, are used; U9C is spare. 51 parts.

U11 stands in a fourth column beside U9, and the LEDs' resistors R3-R8 moved 7 mm towards the LEDs to make the room.
U12 is where the 1 uF stood, between R1 and SW1. R9 and R10 are in the band under U8 and U9.

### What the bus driver saw of it

A -DMAIN stuck low used to make DMA cycles without end. Now the card ignores a line that has not been high in LOAD
mode, so the bus driver's loader reports "-DMAIN is low before the request" (firmware `mode-2`).

