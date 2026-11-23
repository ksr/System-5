# 6845 video card Rev B-Clean: KiCad master (2026-11-20)

> **Hand-maintained since 2026-11-20** (`MASTER`), made by `gen/build.sh` from Rev B's files each run.
> **Not ordered, not built.** Ken, 2026-11-20: "I would [like] to order a clean version of current video card, no need
> for db9, composite only. Add bypass caps and proper silkscreen. This should be a cleanup with minimal to no changes
> to circuit. Lets call this Rev B-Clean." And the same day, on what was left open: "Yes tie light pen to gnd, dont
> worry about connector and xtal."
> **It will not be ordered by itself** (Ken, later that day, asked whether it goes on the order list beside the card
> with the keyboard: "no version with keyboard only"). It stays as the base that Rev B-Clean-Keyboard
> (`../rev-b-clean-keyboard/`) is made from: that card's `gen/build.sh` reads this folder's files.

Rev B (`../rev-b/`) is the 6845 video card in Ken's machine since 2005: 64 x 16 text after BYTE, May 1979, with an
HD6845, an IDT7134 dual-port video RAM at 7000 and a 2732 character generator
([`docs/manual/video-6845-card.md`](../../../../docs/manual/video-6845-card.md)). Rev B-Clean is that card again, to be
made as a new board:

| | Rev B (2005) | Rev B-Clean |
|---|---|---|
| Circuit | the 6845's light-pen input (IC3 pin 3, LPSTB) left open | **the same, less the DE-9, and with the light-pen input tied to ground** (Ken, 2026-11-20): the netlist is Rev B's with X1's pins taken out and IC3 pin 3 on GND, and nothing else (99 nets of two pins or more in both) |
| Video out | composite on the RCA jack, and video, HSYNC and VSYNC on a DE-9 (X1) | **composite only**: the RCA jack (J2). The DE-9 carried three signals that all go on to other parts, so no net loses anything but its DE-9 pin |
| Copper | 2 layers, 0.254 mm tracks | **Rev B's, track for track**, less the 19 track segments and 2 vias that ran only to the DE-9, plus three segments on the top copper for the light-pen tie (from pin 3 out past the pad row, round pin 2 and up to the ground track that leaves pin 1); nothing else was routed |
| Bypass capacitors | positions C1-C7 and C9-C15 (0.1 µF, one a chip) and C8 (10 µF) are on the board; Ken's card has none fitted | **the same fourteen positions and C8, to be fitted**: 0.1 µF on 0.1-inch leads (2.5 mm pitch), each named with its value on the silkscreen |
| Silkscreen | each chip's label inside the chip's outline, where the chip hides it; texts at 0 and 90 degrees; no name line | **redone to the layout rules**: every label beside its part and readable with the parts fitted, every text upright with the card standing in the bus, each reference with its type or value, the bus pins named, the name line |
| Names | the bus connector U$1, the RCA jack U$4 (Eagle's) | **J1** (bus) and **J2** (RCA); SV1's value says what it is, `ADDRESS BLOCK 2x4` |
| Footprints | Eagle's: a silkscreen outline only | **every part drawn** (a body and a courtyard): the chips in their sockets, the bus header's plastic body between the pads and the card edge |
| Net names on the board | Eagle's (`N$45`, `VADDR11`) | the schematic's (`Net-(IC14A-O)`, `/Sheet 1/VADDR11`): names only |

## What the silkscreen says

Every text is at KiCad angle 270: upright, left to right, with the card standing in the bus, connector down. The one
exception is the name line, `System-5 6845 video  Rev B-Clean  2026` with `cottageworker.com`, which runs along the
bottom edge as drawn (up the side of the standing card), ending where the DE-9 was.

- **Chips:** reference and type over the job (`IC4 74LS85` / `BLOCK SELECT`), beside the chip. IC2 and IC7 have room
  for the reference and type only.
- **Passives:** reference and value (`C1 0.1uF`, `R6 270`, `RN1 10k x4`, `Q1 9MHz`); `1` at the network's pin 1; `+` at
  the 10 µF capacitor's positive lead.
- **Bus:** the thirty pins named as the bus Rev D backplane names them (`+5V`, `D0` ... `-RESET`, `GND`; `tools/s5bus.py`)
  on the board side of the pads, and `J1 BUS`. Nothing is printed between the pads and the card edge, where the
  right-angle header's body lies.
- **SV1:** `SV1 ADDRESS BLOCK`, `A15 A14 A13 A12` at its four pairs, and `SHUNT = 0` / `7000: A15 ONLY`: a shunt makes
  that address line 0, and one shunt on A15 (pins 1-2) puts the card at 7000, where HBIOS expects it.
- **J2:** `J2 RCA` / `COMPOSITE VIDEO`. **LED1:** `PWR`, by its function (`pcb-check.ini` exempts its reference).

## What Ken decided, and what is left as Rev B has it

- **The 6845's light-pen input is tied to ground** (Ken, 2026-11-20: "Yes tie light pen to gnd"). Rev B, like BYTE's
  drawing, leaves IC3 pin 3 (LPSTB) open, and on the NMOS part an open input floats; `pcb-check` named it (DESIGN: 1
  input left floating). The one change to the circuit.
- **The connector and the crystal stay as they are** (Ken, the same day: "dont worry about connector and xtal"). The
  RCA jack is on a side edge by the front corner and SV1 is 8 mm in from the top edge, where 2005 put them, though
  the layout rules for new boards would have a cable connector at the front edge and a jumper block at an edge:
  moving either means a new route. The crystal is 9 MHz in the parts list, as HBIOS's 64 x 16 values assume with a
  divide by 6; the marking on the crystal of Ken's card has not been read.
- **Power on 0.254 mm tracks, with no plane: left as Rev B has it** (Ken, 2026-11-20, asked whether to accept them or
  widen them: "yes"). VCC and GND run on the same 10 mil tracks as every signal. It has worked since 2005 with no
  bypass capacitors at all; with the fourteen fitted it is better off than it was. `pcb-check` warns (POWER TRACKS).
  Wider supply tracks or a ground pour would be new copper.
- **The 6845's grade** is the builder's choice of part, not the board's. A 1 MHz HD6845 fails its E-high time above
  about 1.9 MHz of CPU clock ([`hardware/TIMING-REVIEW.md`](../../../TIMING-REVIEW.md), T3). The machine runs it well
  below that; with CPU Rev D at 2 MHz fit a 2 MHz part (HD68B45).

## Building the card

As Rev B (`../rev-b/README.md`), which this board's circuit is:

- **IC8 must be a 74LS163** (or 74HCT163), not the 74HC160 of the 2005 drawing.
- **Character EPROM (IC12, 2732):** burn `firmware/char-rom-fonts/goodfont` (1K) at 000h.
- **SV1:** one shunt on pins 1-2 (A15) for 7000.
- **Fit the bypass capacitors** C1-C7, C9-C15 (0.1 µF) and C8 (10 µF, + towards the bus connector, as marked).
- Ken's card has a 74LS85 at IC4 (the design says 74S85) and a 74AS175 at IC9; either part works in each place.
- The parts list is `video-6845-rev-b-clean-bom.csv`; `video-6845-rev-b-clean-1to1.pdf` is the board at full size, to
  lay the parts on before an order.

## Files

| File | What it is |
|---|---|
| `gen/build.sh` | builds and checks everything below, from Rev B's files |
| `gen/make_schematic.py` | Rev B's schematic without X1, with IC3 pin 3 on ground; the new names |
| `gen/footprints.py` | this folder's footprint library: Rev B's with every part's body and courtyard drawn (seven of them memory Rev F's files, the same Eagle parts pad for pad) |
| `gen/make_board.py` | Rev B's board without the DE-9 and the copper that ran only to it; the light-pen tie; every track locked; the nets under the schematic's names; it stops if any other pad's net is not Rev B's |
| `gen/silk.py` | the silkscreen (on `tools/kicad/silk270.py`); it can be run alone for a silkscreen-only change |
| `video-6845-rev-b-clean.kicad_sch`, `-sheet1.kicad_sch` | the schematic, Eagle's 2005 drawing converted (as Rev B's); `-schematic.pdf` is its print |
| `schematic/` | the redrawn schematic in blocks (`spec.py`), proven pin for pin against the board; in the book `docs/manual/pdf/system5-schematics.pdf` |
| `video-6845-rev-b-clean.kicad_pcb` | the board: 141.0 x 96.2 mm, 2 copper layers, 41 parts, 1,415 tracks and vias |
| `video-6845-rev-b-clean-gerbers.zip`, `gerbers/` | the order files (gerbers and drill) |
| `-placement.pdf`, `-render-top.png`, `-1to1.pdf`, `-bom.csv`, `check-*.png` | the placement drawing, the render, the full-size print, the parts list, and each copper layer drawn from the order zip |
| `pcb-check.ini` | the board's settings for `pcb-check` |

## Checks (2026-11-20)

- **The circuit is Rev B's less the DE-9, with the light-pen tie:** the schematic's netlist equals Rev B's with X1's
  pins removed and IC3 pin 3 moved onto GND (132 nets, 99 of them of two pins or more); `gen/make_board.py` checks
  that every pad has the net Rev B gave it before it adds the tie.
- **ERC:** 0 errors; 89 warnings, the same 89 as Rev B (Eagle's bare wire ends and off-grid ends).
- **DRC** with schematic parity: 0 errors, 0 unconnected, parity 0. 206 warnings, all the Eagle footprints'
  silkscreen outlines over their own pads (199, as Rev B), C3's outline against IC1's (6) and the crystal's
  footprint against its library copy (1, as Rev B).
- **`tools/preorder_check.py --layers 2`: PASS** on every line (layers 2 = 2 = 2, the order zip fresh and read back,
  bypass capacitors at 2.54 mm, netlist 99 of 99, the redrawn schematic MATCH).
- **`pcb-check`** (the check before an order), run on the files before they were committed (pcb-check `a2c1e75`,
  without `--tests`): **no failures**, 35 lines PASS, among them COPPER (the gerbers' own copper against the
  schematic: no shorts or opens), DESIGN (no inputs floating, 14 capacitors for 14 chips), LABELS, BODIES, NAME +
  REV, URL, POWER LED, FIT, FAB LIMITS, LAYOUT, ONE REV. Three warnings:
  - `WARN COMMITTED` (twice): the files were not yet committed.
  - `WARN POWER TRACKS`: the supply tracks, above, for Ken's eye.

  (Earlier that day ONE REV failed: pcb-check read the revision in the zip's name, `video-6845-rev-b-clean`, as "B".
  That was the tool's reading of a name, put right in pcb-check `a20d647`; nothing on the board changed.)
- **The emulator** reads this card from its own netlist (`python3 -m s5emu --hw --video-rev B-Clean`), and a test
  compares it with Rev B's address by address, reads and writes, with and without -VMA: on the bus it is Rev B
  (`software/s5emu/tests/test_hw_videokbd.py`, `Card.test_rev_b_clean_is_rev_b_on_the_bus`; `pcb-check.ini` runs it).
- **Before an order:** `pcb-check` again on the committed files, with no FAIL, and Ken's look at the result, at
  `check-*.png` and at the fab's gerber viewer; then 2 layers on the order form, 1.6 mm, as Rev B's README says.
