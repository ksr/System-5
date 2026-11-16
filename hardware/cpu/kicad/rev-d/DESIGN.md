# CPU Rev D: design notes (draft)

A new System-5 CPU card for the 36-pin bus: the CDP1802, its clock, reset and run control, and a 4K boot EPROM with the boot remap.
Nothing else: no 1861 video, no ribbon to an IO card. Started 2026-10-30 (Ken). Nothing is drawn yet; this file collects the decisions
and the proposals still to agree. The Rev A card (`../rev-a/`, `docs/manual/cpu-card.md`) is the reference.

## Decided (Ken, 2026-10-30)

| Item | Decision |
|---|---|
| Scope | CPU, clock, reset/run, boot EPROM and its remap circuit. No 1861, no IO-card ribbon (SV3), no LCLK/SC/DMA OUT for it. |
| Bus | The 36-pin interface of the bus Rev D: positions 1-3 -EF1..-EF3, 4-33 the 30-pin bus, 34-36 -PAUSE, -DMAIN (LOAD mode only), EXP = SC0; see `docs/manual/bus.md`, "The 36-pin extension". |
| Internal clock | A 4 MHz canned oscillator, divided by 2 (74HCT74): **2 MHz at the 1802**. The old cards' 1.79 MHz was for the 1861. |
| External clock | An **EXT CLK header pin** on the card, wired from a debug board (the bus driver's J2 spare) with a jumper wire; not on the bus (EXP stays free, Ken 2026-10-30). A jumper picks **INT / EXT**. The 1802 is static, so the debug board can run it slowly or step it edge by edge. |
| Boot EPROM | A **4K 2732** at F000-FFFF, as on Rev A, so today's HBIOS 1.0.4 chip moves across. |
| Layout | The board layout rules (front-edge switches and LEDs, labels, readable references, IC types), `cottageworker.com` and the board name/revision on the silkscreen, 0.1" bypass caps. |
| Layers | **2 copper layers if at all possible** (Ken, 2026-10-30): cheaper and quicker to check; preorder_check `--layers 2`. Go to 4 only if routing truly fails, and ask first. |

## Proposed (to agree with Ken)

1. **Clock select.** A 3-pin jumper CLK: INT (the ÷2 output) / EXT (the EXT CLK header pin through a 74HCT14 Schmitt buffer, with a 10k pull-down so an
   unconnected pin holds the clock low rather than floating). The 1802's CLOCK pin is driven by one or the other, never both; XTAL left open.
   A test pin for the 1802 clock. The EXT CLK pin goes at a board edge (header rule) with a GND pin beside it. The bus lines' meanings
   are drafted in `docs/manual/bus.md`, "The 36-pin extension"; EXP (position 36) = SC0 (Ken, 2026-10-30), driven by the CPU card through a buffer (`bus.md`); -DMAIN is LOAD mode only.
2. **High address latch.** Fix finding T1: a 74HCT373 (transparent while TPA is high, as Rev A was drawn) instead of the 374 fitted on
   Rev A, so the high byte is caught before TPA falls.
3. **Boot remap.** Rev A as built (A-built): the boot flip-flop's D and PRE high, clocked by latched A15, cleared by -RESET; the EPROM
   answers everywhere until the first access with A15 high, then only at F000-FFFF, and -VMA is low everywhere else. **No window
   or VMA-mode jumpers** (Ken, 2026-10-30): Rev A's SV2/SV4 (window) and SV5 (Boot/REMAP, Boot only, No ROM) are dropped; the card
   is always Boot/REMAP with the EPROM at F000-FFFF.
4. **Debug control: -PAUSE and -DMAIN** (Ken, 2026-10-30; replaces CPU-generated -INP/-OUT: I/O cards keep their own decode).
   Position 34 -PAUSE (open collector, a level): while low the card holds the 1802's WAIT low. Position 35 -DMAIN (open collector) to
   the 1802's DMA IN. With -RESET also low, -PAUSE puts the 1802 in LOAD mode, and each -DMAIN writes the bus byte to M(R0), R0 + 1.
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
6. **Reset and run** (Ken, 2026-10-30): a front-edge **RESET / RUN switch**, a two-position toggle labelled RESET and RUN at its ends:
   RESET holds -RESET low, RUN releases it and the 1802 runs (the RUN pulse after reset, as on Rev A). Keep the CM1232/DS1232 power-on
   reset. **A debug board drives it too**: -RESET on the bus is open collector, so the bus driver (it already drives -RESET) or a
   jumper wire pulls it low alongside the switch, and -PAUSE (item 4) pauses and, with -RESET, gives LOAD. With the switch on RUN
   the debug board is in control; on RESET the switch wins. **PAUSE and LOAD are not on this card** (Ken, 2026-10-30, option B): the
   CPU card only listens to -PAUSE and -DMAIN; the new IO card (switches, by hand) and the debug board (from the Mac) drive them,
   either one alone or both together (open collector). A PAUSE LED on this card shows the mode.
7. **LEDs (front edge, labelled):** PWR, Q, WAIT, CLEAR, VMA, and CLK EXT (on while the external clock is selected).
8. **Timing.** Rerun `python3 -m s5emu.timing 2` and `contention()` at 2 MHz; Rev A's review was at an assumed 1.76 MHz. Watch T6
   (IDE card, `BACKLOG.md`): INP 3 into RAM fails worst case from about 2.2 MHz, so 2 MHz leaves little margin.
9. **Folder.** `hardware/cpu/kicad/rev-d/` with `gen/netlist.py`, `make_schematic.py`, `make_board.py`, as for the bus Rev D; a
   `schematic/spec.py` and lines in `build_all.sh` / `make_book.py` for the schematic book.

## Netlist (2026-10-30): `gen/netlist.py`, `gen/make_schematic.py`

The circuit is written; ERC 0 (`reports/erc.rpt`), 87 nets, none with a single pin. Board not started. Choices made while
writing it (for Ken to review):

- **No run latches, no one-shot.** -RESET and -PAUSE are levels now, so CLEAR = -RESET and WAIT = -PAUSE through two Schmitt
  inverters each (U7): reset, run, pause and load follow directly. Rev A's two 74LS20 latches and the 74LS123 are gone.
- **DS1813, not CM1232/DS1232.** Rev A's CM1232 has a watchdog strobed by TPA; TPA stops in PAUSE, in LOAD and with the external
  clock stopped, so it would reset a paused or stepped machine within a second. The DS1813 (TO-92) is power-on reset and a
  debounced push-button input on one open-drain pin, which sits on the bus -RESET; no watchdog.
- **SW1 RESET/RUN** grounds SW_RST: through D1 (BAT85) that pulls -RESET (the DS1813 then holds it 150 ms after release), and it
  clears LOADED. C12 on SW_RST clears LOADED at power-on.
- **LOADED (U8A)** decides what a reset boots: set by LOAD mode, cleared by SW1 and power-on. While it is set the boot map stays
  off, so after loading a program at 0000 the ELF sequence LOAD → RESET → RUN runs it from RAM; SW1 (or power-on) boots HBIOS.
  A reset from the bus (the debug board, the IO card) leaves LOADED as it is. Checked as a gate-level walk-through of power-on,
  boot, bus reset, LOAD → RESET → RUN, PAUSE and SW1.
- **Consequence for the IO panel card:** its hand controls become the COSMAC ELF's **RUN** and **LOAD** toggles (RUN off pulls
  -RESET, LOAD on pulls -PAUSE; LOAD mode = RUN off + LOAD on), not PAUSE and LOAD; PAUSE is RUN on + LOAD on.
- **Bus lines driven:** -VMA push-pull from U5B (only the CPU card drives it), SC0 through U9D/U9E, -RESET open drain (U10, D1).
  Unbuffered as on Rev A: D0-D7, A0-A7, TPA, TPB, -MRD, -MRW, Q, N0-N2.
- **Pull-ups on the card** (RN1, 10k): -RESET, -INT, -PAUSE, -DMAIN, -EF, -EF1-3, so the card also works on the 2009 backplane,
  which has none; RN2 holds EF1-EF4 high when a JP2 jumper is off.
- **Parts:** U1 CDP1802ACE, U2 74HCT373, U3 2732, U4/U8 74HCT74, U5 74HCT00, U6 74HCT20, U7/U9 74HCT14, U10 DS1813-10,
  X1 4 MHz DIP-8 oscillator; J1 the 36-pin bus (footprint to settle with the board: a placeholder 1×36 header), J2 DEBUG
  (EXT_CLK, GND, CLOCK, SC0, SC1, GND), JP1 CLK INT/EXT, JP2 EF (2×4), JP3 -EF TO EF3; LEDs PWR, Q, PAUSE, RESET, ROM.
  Spare: U6B (inputs tied high), U8B.
- **Symbols:** KiCad's stock 74xx symbols are one unit per gate, which the generator cannot place, so the logic uses one-unit
  project symbols (`s5cpu.kicad_sym`, written by make_schematic.py from `netlist.CHIPS`, pinouts from the data sheets). The
  readable drawing is the redrawn schematic (`tools/kicad/sch/gen_schematic.py`), still to set up (`schematic/spec.py`).

## Board (2026-10-30): `gen/make_board.py`

- **5.50 × 4.00 in** (139.7 × 101.6 mm; Ken, 2026-10-30: a 36-pin card is 0.25 in taller than the 30-pin cards so the
  connector clears the card supports). J1 = `s5cpu:C36` (the 30-pin cards' C30 with positions 1-3 and 34-36 added) down
  the left edge, centred; the 3.00 × 0.15 in support strips along the top and bottom edges are copper keep-outs.
- **2 layers**, routed by Freerouting (1090 segments, 40 vias), GND pours both sides. `preorder_check --layers 2`: **PASS**
  (ERC 0, DRC 0, parity 0, netlist 78/78 MATCH, bypass caps 0.1", schematic redrawn). Not ordered.
- Front edge (right): SW1 RESET/RUN (RESET with the lever up), LEDs PWR, Q, PAUSE, RESET, ROM, J2 DEBUG with each pin
  named; JP1 CLK (INT/EXT), JP2 EF1-4, JP3 -EF>EF3 along the bottom edge outside the support strip; every chip's reference
  and type below it; S5CPU-D, "System-5 CPU Rev D 2026", cottageworker.com.
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
- **Decided (Ken, 2026-10-30): keep 2 MHz**; the video card Rev C gets a faster CRTC grade (its DESIGN.md).
- **Still to do before an order:**
  ; check the 36-pin card in the card guides (4.00 in); Ken's look at the pictures.
