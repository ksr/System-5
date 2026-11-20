# 6845 video card Rev B-Clean-Keyboard: KiCad master (2026-11-20)

> **Hand-maintained since 2026-11-20** (`MASTER`), made by `gen/build.sh` from Rev B-Clean's files each run.
> **Not ordered, not built.** Ken, 2026-11-20: "now i want to add keyboard support to Rev B Clean, Call it
> Rev-b-clean-keyboard. Look at video-g for keyboard section only. Expand bus to the 36 pin bus and add jumpers
> required to access keyboard. Rev-b-clean-keyboard and Video-g will never be used at the same time." Asked how the
> CPU should read the keyboard: "Memory-mapped, as VIDEO-G". Later the same day: "ok to grow card if needed", and "it
> is messy to have keyboard and video connector on different edges. Need to move together. Less of an issue for FTDI."
> And: "I would prefer for the power LED to be in the corner like most/all other boards."

Rev B-Clean (`../rev-b-clean/`) is Rev B, the 6845 video card in Ken's machine since 2005, cleaned up for a new order.
This card is Rev B-Clean with a **PS/2 keyboard** on it, so that one card is the whole console: the video as Rev B has
it, and the keyboard section of VIDEO-G TEXT (`hardware/video-g/DESIGN.md`), read the way VIDEO-G's is. It takes the
place of the 2005 IO card's keyboard path (PAK-VI, PIC, CDP1852).

| | Rev B-Clean | Rev B-Clean-Keyboard |
|---|---|---|
| Board | 141.0 x 96.2 mm, 2 layers | **190.5 x 106.565 mm** (7.50 in, the IO panel's length; VIDEO-G TEXT's height), 2 layers: 49.5 mm longer at the front edge for the keyboard section, 10.3 mm more at the +5V end of the bus edge for the six more bus pins |
| Bus connector | 30 pins | **36 pins** (J1): the 30 where they were, then -EF1, -EF2, -EF3, -DMAIN, SC0, -PAUSE |
| The 6845 | answers all of 7800-7FFF (the pair 7800 / 7801, repeated) | **7800 / 7801**, repeated every 8 addresses through 7BFF only |
| Keyboard | none | **PS/2**: an ATmega328P, the key at **7802**, the status at **7804**, KEY-READY also on a bus flag line picked by **JP1** |
| Video jack | RCA on a side edge, where 2005 put it | **RCA at the front edge, under the PS/2 jack** |
| Copper | Rev B's, track for track | Rev B's kept and locked, but for three places (below); the keyboard section's tracks added round it |

## The map (block 7, SV1 as on Rev B)

| Address | Read | Write |
|---|---|---|
| 7000-77FF | the text RAM | the text RAM |
| 7800 / 7801 | the 6845 (7801: R14-R17) | the 6845's address register / data |
| 7802 | **the key**; the read clears KEY-READY (at TPB) | nothing |
| 7804 | **status**: bit 0 KEY-READY, bit 2 VSYNC, bit 3 DE, bit 7 = 1, the rest 0 | nothing |
| 7806, 7C00-7FFF | nothing (VIDEO-G has its mouse, Y register and graphics window there) | nothing |

7800-7807 repeat every 8 addresses through 7BFF. The key and the status are where VIDEO-G TEXT has them, with the same
bits, so **the VIDEO-G HBIOS runs on this card as it is** (`firmware/hbios/video-g`: it polls 7804 and reads 7802). Its
6845 table (64 x 25, eight lines a row, a 1.5 MHz character clock) fits Rev B's hardware too: 9 MHz divided by 6 is
1.5 MHz, and Rev B's character ROM has eight lines a character. In the emulator the monitor comes up on 25 rows and
Elf/OS 5.1.1 boots (below). The machine's own HBIOS (v1.0.x) would show the video but look for keys on port 1.

## Jumpers and connectors

- **SV1 ADDRESS BLOCK**, as on Rev B: one shunt on A15 (pins 1-2) puts the card at 7000.
- **JP1 KBD FLAG** (2 x 4, at the top edge as drawn, by the bus connector's new pins): one shunt picks the bus line
  that KEY-READY pulls low, **-EF1, -EF2, -EF3 or -EF**, or none. The VIDEO-G HBIOS does not need it (it reads the
  status register); a program that tests a flag does. On CPU Rev D the line then goes to whichever of EF1-EF4 that
  card's own jumpers give it.
- **J3**, PS/2 keyboard (Mini-DIN-6), and **J2**, composite video (RCA), side by side at the front edge, mouths at the
  edge. **J4**, the FTDI header for the ATmega's bootloader, lies along the bottom edge as drawn, near the front
  (pin 1 GND at the bus end ... pin 6 DTR, both named on the board).
- **Which backplane:** the 36-pin connector is for the bus Rev D (`hardware/bus/kicad/rev-d`), whose slots have the
  six more positions and pull-ups on -EF1 to -EF3. Pads 1-30 are on Rev B's holes, so with a 30-pin header fitted
  there instead the card is a 30-pin card, flag on -EF only (R11 pulls -EF up on the card). That has not been tried,
  and the card is 10 mm taller than Rev B at that end.

## The keyboard section

It is VIDEO-G TEXT's, part for part and pin for pin (`gen/keyboard.py` has the list), so the ATmega's firmware is the
same sketch, `embedded/video-g-ps2`, in its keyboard mode (PD7 open):

- **IC21 ATmega328P** (Y1 16 MHz) reads the PS/2 keyboard and puts each key's code on MD0-MD7; its LDDATA edge clocks
  the code into **IC19** (74HCT374, the key latch) and sets KEY-READY (**IC18**, half a 74HCT74).
- **IC15** (74HCT138) is the one new decoder: enabled by Rev B's upper-half select (the net that was the 6845's -CS,
  now -UPPER) and A10 low, it picks by A1-A2 the 6845, the key or the status. **IC16** (74HCT32) makes the two read
  enables with -MRD, and the key-read strobe at TPB; **IC17** (74HCT00) inverts TPB and -RESET and makes the
  KEY-READY clear. **IC20** (74HCT244) puts the status on the bus.
- **IC22 is a second 7416** (open-collector inverters), for the two jobs VIDEO-G TEXT gives to its 7416, on the same
  gates: one pulls the flag line low while KEY-READY, one pulls the ATmega's reset low while the bus -RESET is low.
  The other four gates' inputs are on ground. Rev B's own 7416 (IC14) has three spare gates, but their inputs are
  tied to ground by copper that carries ground on to other parts, so using them would have meant cutting Rev B's
  ground. The card was first drawn with two 2N7000 transistors there; Ken, 2026-11-20: "swap". A 7406, a 7405 or a
  74HC05 has the same pins and does the same in this socket.
- F1 (0.5 A PTC) feeds the keyboard's +5 V; R8, R9 (4.7k) pull up its clock and data.

Like VIDEO-G TEXT's decoder, IC15 sees the high address byte on A1-A2 early in each cycle. For the addresses the
software uses (7800-7807) that early pick is the 6845, whose E (TPB) is still low; KEY-READY is cleared only at TPB.

## Where Rev B's copper was touched

Of Rev B-Clean's 1,415 tracks and vias, 1,390 are where 2005 put them, locked, and `gen/make_board.py` stops if any
pad of Rev B's would change its net. The other 25:

1. **The 6845's select** (5 pieces). Rev B's track from IC5 pin 3 to IC3 pin 25 is cut at IC5: the pin now drives
   -UPPER to the new decoder, and the decoder's output joins the rest of the old track to the 6845. The piece
   between the cut and the join is taken off.
2. **One corner of the A2 track** (2 pieces), which ran through where bus pin 31 (-EF1) now is: it turns in between pins 31 and
   32 instead, 1.9 mm further up.
3. **The RCA jack**, moved to the front edge (13 pieces): the branch of Rev B's video track that ran to the old jack
   and the ground chain through its old pads, both left hanging, are taken off; a new track runs to the jack.
4. **The power LED and its resistor**, moved to the front corner (5 pieces): the short tracks that fed them where
   they stood are taken off; new ones run to the corner.

## The layout

- The keyboard section fills the 49.5 mm added at the front: the gates and the latches in two columns, the ATmega
  beside the jacks. **IC15**, the decoder, lies in the strip along the top edge instead, 20 mm from the two Rev B pins
  it serves: in the front section, 90 mm away across Rev B's copper, those two connections found no way.
- **The two jacks are together at the front edge** (Ken, 2026-11-20: "it is messy to have keyboard and video connector
  on different edges. Need to move together. Less of an issue for FTDI"): the PS/2 jack, and 16 mm below it, centre
  to centre, the RCA jack, each with its mouth at the edge.
- **The power LED is in the front corner** (Ken, the same day: "I would prefer for the power LED to be in the corner
  like most/all other boards"), 6.5 mm from the front edge and 7.4 mm from the bottom one as drawn, its resistor R1
  beside it: where memory Rev E / F and BUSDRV-B have theirs. Rev B had them in its own front corner, which on this
  longer card is 56 mm from the edge. The FTDI header, which stood in that corner, lies along the bottom edge now
  (Ken: its place matters less), and R10, a pull-up, moved to free space above IC16.
- The card was first drawn 188.0 mm long. Ken, the same day: "ok to grow card if needed". The 2.5 mm more are behind
  the PS/2 jack, so that the fuse and the two pull-ups there have their labels beside them.
- The silkscreen follows the rules of the other new cards (every text at 270 but the name line, every reference with
  its type or value, the bus pins named). Beside the 10 uF capacitor's can the bus pin names stand in two tight
  columns: there is a 2.9 mm lane there for seven names.

## The routing

Freerouting adds the keyboard section with Rev B's copper locked (`gen/route.py`, a fixed order, seed in the file).
On this board it leaves a few long connections open whatever the order or the number of passes: each has to cross 70
to 130 mm of Rev B's tracks. `gen/route_leftovers.py`, a plain maze router on Rev B's own 5 mil grid, joins those; DRC
is the judge.

## Building the card

As Rev B-Clean (`../rev-b-clean/README.md`: IC8 a 74LS163, the character EPROM, the bypass capacitors), and:

- Burn the ATmega328P with the Uno bootloader and load `embedded/video-g-ps2` through J4 (an FTDI cable).
- The CPU card's EPROM: the VIDEO-G HBIOS, `firmware/hbios/video-g`.
- A 2 MHz-grade 6845 (HD68B45) with CPU Rev D, as for Rev B-Clean.
- The parts list is `video-6845-rev-b-clean-keyboard-bom.csv`; `-1to1.pdf` is the board at full size.

## Decided, and what is left to look at

- **Power on 0.254 mm tracks** in Rev B's part of the board, as Rev B-Clean; the new section's supply tracks are 0.5 mm.
  `pcb-check` warns (POWER TRACKS). **Accepted** (Ken, 2026-11-20, asked whether to accept them as they are or widen
  them: "yes"): Rev B's supply copper stays as 2005 drew it.
- **The composite video now runs to the front edge**: about 105 mm of new track past the keyboard section, where Rev
  B's ran about 35 mm to the side edge. At this card's 9 MHz dot rate that should not show; it is the first thing to
  look at on a built card.
- **Not run on hardware:** the card, the ATmega firmware and the VIDEO-G HBIOS are all untried outside the emulator.

## Files

| File | What it is |
|---|---|
| `gen/build.sh` | builds and checks everything below, from Rev B-Clean's files (about four minutes) |
| `gen/keyboard.py` | what this card adds: the parts, their pins and nets, the placement, what moves |
| `gen/make_schematic.py` | Rev B-Clean's schematic with the 36-pin connector and the keyboard section |
| `gen/footprints.py` | Rev B-Clean's footprint library with the 36-pin header and the PS/2 jack |
| `gen/make_board.py` | Rev B-Clean's board made larger, the new parts placed, the three changes to Rev B's copper |
| `gen/route.py`, `gen/route_leftovers.py` | Freerouting in and out; the maze router for what it leaves |
| `gen/silk.py` | the silkscreen (on `tools/kicad/silk270.py`) |
| `gen/buspins.py` | J1's pads against the backplane's pin list, for `pcb-check` |
| `schematic/` | the redrawn schematic in blocks (`spec.py`), in the book `docs/manual/pdf/system5-schematics.pdf` |
| `video-6845-rev-b-clean-keyboard.kicad_pcb`, `-gerbers.zip`, `-placement.pdf`, `-render-top.png`, `-1to1.pdf`, `-bom.csv`, `check-*.png` | the board, the order files, the drawings, the parts list, each copper layer drawn from the order zip |
| `pcb-check.ini` | the board's settings for `pcb-check` |

## Checks (2026-11-20)

- **The circuit is Rev B-Clean's with what `gen/keyboard.py` says added:** `gen/make_schematic.py` proves the
  schematic's netlist against Rev B-Clean's changed by that file (133 nets of two pins or more; Rev B-Clean: 99).
- **ERC:** 0 errors; 105 warnings: Rev B's 89 (Eagle's bare wire ends and off-grid ends) and 16 where a new
  three-state output meets the 6845's data pins, which Eagle's symbol calls outputs.
- **DRC** with schematic parity: 0 errors, 0 unconnected, no difference in nets or parts (one note, as on Rev
  B-Clean: a field Eagle's converter gave RN1's symbol). 206 warnings, the same 206 as Rev B-Clean: the Eagle
  footprints' silkscreen outlines over their own pads (199), C3's outline against IC1's (6) and the crystal's
  footprint against its library copy (1). None is from the keyboard section.
- **`tools/preorder_check.py --layers 2`: PASS** on every line (layers 2 = 2 = 2, the order zip fresh and read back,
  bypass capacitors at 2.54 mm, netlist 133 of 133, the redrawn schematic MATCH).
- **`pcb-check --tests`** (the check before an order) on the committed files, elf `808364d`, pcb-check `a2c1e75`:
  **no failures, 1 warning.** 37 lines PASS, among them COPPER (the gerbers' own copper against the schematic: 133
  nets, no shorts or opens), DESIGN (no inputs floating, no output fights, 24 capacitors for 22 chips), LABELS (every
  reference and value on the silk, every text clear of the parts), BODIES, BUS PINS (all 36), LAYOUT (the panel
  parts at the front edge), FOOTPRINTS, FAB LIMITS, ONE REV, COMMITTED and TESTS (the emulator tests below).
  - `WARN POWER TRACKS`: Rev B's 0.25 mm supply tracks, accepted by Ken (above).
  - `NOTE DESIGN`: EFOC, the 7416's open-collector flag output, has its pull-up on another board. So it has: the bus
    Rev D pulls up -EF and -EF1 to -EF3, and R11 here pulls up -EF; with no shunt on JP1 the output drives nothing.

  (On the first files that day ONE REV failed: pcb-check read the revision in the zip's name as "B". That was the
  tool's reading of a name, put right in pcb-check `a20d647`.)
- **The emulators** (`software/s5emu/tests/test_hw_videokbd.py`): the card alone from its netlist, cycle by cycle
  (what answers at every address, the key and KEY-READY, each setting of JP1), and the whole machine on both
  emulators with the VIDEO-G HBIOS: the monitor's commands typed on this card's keyboard, the IO panel, Elf/OS 5.1.1
  with `cls` on 25 rows and the panel's clock. On the hardware machine (CPU Rev D, memory, IDE, the IO panel and this
  card, each from its netlist) the bus log stays empty.
- **Before an order:** Ken's look at that result, at `check-*.png` and at the fab's gerber viewer; then 2 layers on
  the order form, 1.6 mm. (A change to the board means `pcb-check --tests` again.)
