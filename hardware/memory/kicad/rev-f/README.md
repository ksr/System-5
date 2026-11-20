# Memory Rev F (MEM3-F): KiCad master

> **Rev F (2026-11-18) is Rev E with EEPROM sockets and its silkscreen fixed.** Ken asked that morning for "the next
> version of memory card with fixed silkscreen", and that evening "yes put in Rev F but that isnt being ordered today"
> for the EEPROM sockets of `BACKLOG.md` (2026-10-30). Each EPROM socket takes a 27C256, as before, or a 28C256 EEPROM
> that the 1802 can rewrite in place. A jumper block per socket picks which (below).
>
> **Copper:** Rev E's, except where the sockets changed. 1,078 of Rev E's 1,084 track segments and vias are kept,
> identical and locked. The 6 that carried A14 through IC3's and IC5's pin 27 are gone. Freerouting added 74 segments
> and 1 via for the new connections, and a 75th, a 0.05 mm stitch inside one of Rev E's tracks (IC4's D6 net). Both planes,
> and every part but the four new ones, are where Rev E has them. Rev E (`../rev-e/README.md`) has been the card in
> the machine since 2026-10-31; its notes on building it (74HCT151 for all four muxes, the CD4050B buffers) apply to
> Rev F unchanged.
>
> **Not ordered** (Ken: not today). Before an order: `~/Developer/pcb-check/pcb-check
> hardware/memory/kicad/rev-f/memory-rev-f.kicad_pcb hardware/memory/kicad/rev-f/memory-rev-f-gerbers.zip --layers 4
> --tests` (Ken's check for every system), then Ken's look at the pictures and the fab's viewer. It is a **4-layer**
> board, as Rev E (In1 GND, In2 VCC).

## The EEPROM sockets

A 27C256 and a 28C256 have the same pins but two of them do other jobs:

| Socket pin | 27C256 (EPROM) | 28C256 (EEPROM) | Rev E |
|---|---|---|---|
| 1 | VPP: must be at VCC to read | A14 | tied to VCC |
| 27 | A14 | !WE, the write strobe | on A14 (BUFFADDR14, the CD4042B's latched A14) |

So a 28C256 in Rev E reads only its top 16K, and it takes a write whenever the CPU writes to one of its blocks with
A14 low. Rev F gives each socket's pins 1 and 27 to a 2 x 3 jumper block: **JP1 for IC5** (EPROM HI) and **JP2 for
IC3** (EPROM LO), at the top edge beyond the card guide (the layout rules: jumper blocks at an edge).

| JP pin | | JP pin | |
|---|---|---|---|
| 1 | VCC | 2 | A14 |
| 3 | the socket's pin 1 | 4 | the socket's pin 27 |
| 5 | A14 | 6 | WR, the RAMs' write strobe (-MWR through IC8, a CD4050B) |

**R6 (IC5) and R7 (IC3), 47k from pin 27 to VCC**, stand upright beside the blocks. With no shunt on 4-6 they hold a
28C256's !WE high, so it cannot be written.

### Settings

With the card standing in the bus, each block's right-hand column (pins 1, 3, 5) sets the socket's pin 1, and the
left-hand one (pins 2, 4, 6) its pin 27. The silkscreen says `27C256` at the lower end and `WRITE  28C256` at the
upper end, each word over its column.

| In the socket | Shunts | Pin 1 | Pin 27 |
|---|---|---|---|
| **27C256** (as Rev E; the default) | **1-3 and 2-4**: both at the `27C256` end | VCC (VPP) | A14 |
| **28C256, read-only** | **3-5** only: the right-hand column, at the `28C256` end | A14 | !WE held high by R6 / R7 |
| **28C256 the CPU can write** | **3-5 and 4-6**: both at the `WRITE  28C256` end | A14 | !WE on WR |

- **Never put A14 on a 27C256's pin 1** (3-5 with a 27C256): VPP low is Rev B's misread fault.
- **With a 28C256, keep 2-4 empty.** It would put !WE on A14, so a write to one of the chip's blocks with A14 low
  would change the ROM. In the read-only setting, store the spare shunt off the block or on one pin only.
- **Never fit a shunt across a row** (1-2, 3-4, 5-6). 1-2 ties A14 to VCC, 5-6 ties it to WR, and 3-4 joins pins 1
  and 27.
- The read-only setting is the one to keep. Fit 4-6 only while the 1802 rewrites the chip.
- **Writing a 28C256:** each byte (or page of up to 64 bytes) starts an internal write of up to 10 ms. Until it ends,
  a read of the chip returns bit 7 of the byte written inverted ("data polling"), so software must poll or wait before
  the next write. Some 28C256s come with software data protection on; they then take a write only after the data
  sheet's unlock sequence. The emulator lands a write at once and models neither the wait nor the protection.

### Choices behind it

- **47k, not 10k.** With a 27C256 the shunt on 2-4 puts the pull-up on A14, which a CD4042B output drives. A CD4042B
  is rated for about 0.5 mA at a valid low (the reason Rev D/E need 74HCT151 muxes: `../rev-e/README.md`). Two 10k
  pull-ups would draw 0.9 mA, two 47k draw 0.2 mA. A 28C256's !WE input leaks at most 10 uA, which is 0.5 V across 47k.
- **Upright resistors** (KiCad's `R_Axial_DIN0207_L6.3mm_D2.5mm_P2.54mm_Vertical`). A lying 0207 put R6 between JP1
  and R5 with no room for its label: it landed in JP2's legend. Upright, each label sits right under its resistor.
- **WR, not a new gate.** The EEPROM's !WE is the RAMs' write strobe. A write reaches the chip only while its !CE is
  low, so only in its own blocks.
- **Timing** (`python3 -m s5emu.timing --cpu D 2`, from the netlists, with the AT28C256-15's limits typed in from
  memory, to verify against the data sheet): at 2 MHz the write pulse is at least 815 ns long (100 ns needed). The
  data is set up 2255 ns more than the 50 ns needed, and the address and !CE settle 1015 ns before !WE falls. At
  1.76 MHz the margins are larger. A 28C256-15 reads in 150 ns, faster than the 27C256-20's 200 ns.
- **Boot:** HBIOS (v1.0.4 and v1.0.8) and Elf/OS v5 never write 8000-EFFF. Elf/OS's memory probe (`f_freemem`) stops
  below 7800, so even the writable setting keeps its ROM through a boot (checked in the emulator, below).

## What changed from Rev E: the silkscreen

Two of Ken's rules for new boards decide it: every label readable with the parts fitted, outside each part (Ken,
2026-10-31, after MEM3-E), and **all silkscreen text upright, left to right, with the card standing in the bus,
connector down** (Ken, 2026-11-18, every board on every system; MEM3-E is the rule's own example of the problem, "drawn
to be read lying flat": 77 texts at 0, 30 at 90, 4 at 180, only the 5 LED labels at 270). System-5's cards are drawn
with the bus on the left, so on Rev F **every text is at KiCad angle 270**, except the name line, which the rule lets
run up a side edge.

| | Rev E | Rev F |
|---|---|---|
| Chip labels | name, type and job in the middle of each chip's outline, **under the chip** once it is in its socket (IC2's was hidden in bring-up), at 0 | at one end of each chip, clear of its pins: `IC7 CD4050` over `A0-A5 BUFFER`, the types as the parts list has them (CD4050, not 4050); where two lines have no room, one (`IC2 74HCT151  RAM LO 4K SEL`) or the name and type alone (IC13, IC15, IC4: `IC13 74HCT151`; their jobs are in the schematic). IC3 and IC5 read `27C256/28C256`. The bottom row's four (IC7, IC8, IC9, IC6) are at 0.8 mm: they share the 6.2 mm between their pins and J1's with the bus pins' names |
| Bus connector | Eagle's `U$1`, unlabelled; its pins' names at 0, on the board side of the pads | **J1** (the schematic too); the 30 pins' names at 270 in two staggered rows (one row would not fit the 2.54 mm pitch), **on the board side of the pads**, as Rev E has them; `J1 BUS` in the margin past the header's GND end. The footprint draws the part now: a single-row right-angle pin header whose plastic body lies between the pads and the card edge (below) |
| Capacitors, resistors, networks | `C4 0.1uF` at 90 or 0 | the same, at 270, beside each; the networks' pin 1 marked; R6 and R7 on two lines under each |
| Jumper blocks | addresses at 90, ROM / GND / RAM and `HI 32K` / `LO 32K` at 0 | all at 270: each 4K block's address beside its row of pins, the three rows named under them (staggered as the bus pins), the blocks' names beyond the addresses, SV1-SV4 named; JP1 `EPROM HI` and JP2 `EPROM LO` with their `27C256` / `WRITE  28C256` legends |
| LEDs | `EPROM HI` ... `PWR` at 270 | as Rev E (the only labels that were right); `pcb-check.ini` exempts their references, as on CPU Rev D and the IO panel. `RAM HI` alone stands 0.5 mm further from R3 since 2026-11-19: Rev E has R3 1.27 mm nearer the front edge than the other LEDs' resistors, and the label's end came within 0.1 mm of the resistor's drawing (`pcb-check`, once its LABELS line read every text: "'RAM HI' under R3"; it was not hidden) |
| Name | `MEM3-E   System-5 64K RAM/EPROM   2026` | `System-5 memory  Rev F  2026` (1.2 mm; Ken, the evening of 2026-11-18: one naming for every card, no code like MEM3-F; `pcb-check.ini`'s name with it) with `cottageworker.com` (1.0 mm) right after it (Ken, 2026-10-26), along the bottom edge as drawn: up the right-hand side with the card standing. It starts where the bottom card-guide strip ends (3.00 in from the bus edge): no label is in either strip |
| Courtyards and bodies | none (the footprints came from Eagle: a silkscreen outline and pads) | a courtyard round each part's pads, 0.1 mm out, in the board and in this folder's copy of the footprint library; J1's round the header's body too. Since 2026-11-19 each chip footprint (DIL14, DIL16, DIL28, DIL28-6) also has a **body on F.Fab, the chip in its socket**: 1.33 mm past the end pins and 1.27 mm past the rows, as KiCad draws its DIP sockets |

The footprints' own texts (the old bus-pin names and passives' labels, which KiCad keeps no hidden flag for) are on
F.Fab now, off the silkscreen.

**The bus pins' names were under the header, and are not now (the night of 2026-11-18).** As first drawn that day, Rev
F had the thirty names and `J1 BUS` in the strip between J1's pads and the card edge. J1 is a right-angle pin header,
and its plastic body lies in that strip, 1.5 to 4.0 mm from the pads (the photo of the built MEM3-E shows it,
`../rev-e/photos/`): on a built card all thirty would have been hidden. Nothing caught it, because the C30 footprint
drew pads and no part, so the label placer and `pcb-check` took the strip for free board (found on VIDEO-G, where
`J1 BUS` had the same fault; `hardware/video-g/kicad/README.md`). Now this folder's `C30` draws the header: its body on
F.Fab, a courtyard round body and pads, and KiCad's 3D model, so the render shows the connector. `gen/silk.py` brings
the board's J1 up to it (`tools/kicad/fp_update.py`) and places the names on the board side, 1.84 and 3.51 mm from the
pads, with the bottom row's chip labels beside them. Silkscreen only: the copper is the same, track for track.

**The chips' bodies drawn (2026-11-19).** `pcb-check` got a line for this fault, BODIES: a warning for each part with
nothing drawn on the fab layer, since the checks cannot see such a part. Rev F's fourteen chips were of that kind
(Eagle's footprints: pads and a silkscreen outline between the rows). Each has its socket's frame on F.Fab now, and the
placer keeps labels off it: `IC12` and `IC14`'s labels had stood 0.2 mm inside the frame's end and moved 0.4 mm out;
`IC1`, `IC11` and `IC2`'s moved 0.2 mm; `C8 10uF` is under its capacitor again, at 0.8 mm. Nothing else moved, and the
copper is the same, track for track. The same day BODIES learned to name a fab-layer drawing far smaller than the
part's courtyard, a mark and not a body, and Eagle's other footprints here were of that kind: the bypass capacitors
(two lead stubs), the pin headers (their pins), the resistor networks, the resistors, C8 and the LEDs. Each has its
body on F.Fab now, as its silkscreen outline draws it (the capacitors as on the other new cards, 4.0 x 2.5 mm); no
label moved for it. The courtyards stay round the pads alone: Rev E's parts stand closer than their bodies' outlines
would allow courtyards to.

## How it is made

`gen/build.sh` (KiCad 10, Freerouting 1.9) builds and checks it all, from Rev E's files each run:

1. `gen/make_schematic.py`: Rev E's schematic with J1, the new title block and the EEPROM sockets (IC3 / IC5 pins 1
   and 27 on the jumper blocks, JP1, JP2, R6, R7 and a note). Then ERC, the netlist, the parts list
   (`memory-rev-f-bom.csv`) and the schematic PDF.
2. `gen/make_board.py`: Rev E's board with U$1 renamed J1, IC3 / IC5 pins 1 and 27 on their new nets, the A14 copper
   at pin 27 removed, the four new parts placed, every remaining track locked.
3. `gen/route.py dsn`, Freerouting, `gen/route.py import`: the new connections only, on F.Cu / B.Cu (the planes stay
   power layers), in a fixed order (`ROUTE_SEED` 1: seeds 0 and 3 leave JP2's A14 unrouted).
4. `gen/silk.py`: brings the drawing of every part from this folder's library up to its file (J1's header body,
   courtyard and 3D model; the chips' bodies in their sockets; the courtyards), removes
   Rev E's silkscreen texts (keeping the LEDs'), moves the footprints' own texts to F.Fab, adds the courtyards, and
   writes every label again at 270, each at the first spot clear of every pad (0.3 mm), part body, outline, courtyard
   and other text.
5. DRC with schematic parity, the order files, and `tools/preorder_check.py --layers 4`, which also redraws
   `schematic/` (from `spec.py`) and rebuilds the book.

## Checks (2026-11-18)

- `tools/preorder_check.py --layers 4`: **PASS**: ERC 0 errors (Rev E's 6 warnings), DRC 0 errors (311 silkscreen
  notes), 0 unconnected, schematic parity 0, the netlist proof 92 of 92, the planes (57 GND and 45 VCC pads reach
  them), the zip fresh and complete, the redrawn schematic matched.
- `pcb-check --layers 4 --tests` at elf `644a51a`: **no failures, 0 warnings** (the five LEDs labelled by function,
  as `pcb-check.ini` allows). LABELS, DESIGN (no input floating, no output fight), FOOTPRINTS and COPPER (rebuilt from
  the gerbers: no shorts or opens) pass with the new parts. **That pass was with the bus pins' names under the header**
  (above): pcb-check could not know the header's body, which the footprint did not draw. The board as it is now, with
  the names on the board side and the body in the footprint, passes `tools/preorder_check.py --layers 4` again (the
  same counts; the copper is the same track for track) and **`pcb-check --layers 4 --tests` at elf `d1df002`
  (2026-11-19, pcb-check `71c4bef`): no failures, 0 warnings**; LABELS: every reference and value on the silk, clear of
  the parts, the header's body among them now. **Again at elf `b4692e9`** with the chips' bodies drawn (pcb-check
  `bd032dd`, which has the BODIES line) and at **`b2252b7`** with every Eagle footprint's (pcb-check `0b45f65`, whose
  BODIES also names a mark that is not a body): **no failures, 0 warnings** each time; BODIES: every part drawn with
  its body. pcb-check `1525f36`, whose LABELS line reads every silkscreen text, then gave one warning at `4e2dff4`,
  "'RAM HI' under R3" (the table above); with that label 0.5 mm further from R3, at elf **`bb0b711`**: **no failures,
  0 warnings**, every text clear of the parts.
- The emulator (`software/s5emu`) runs Rev F's netlist with the shunts as netlist edits:
  - `--hw --mem-rev F`: a 27C256 in each socket, JP1 and JP2 at 1-3 and 2-4.
    `tests/test_hw.Decode.test_rev_f_is_rev_d` checks that it decodes, writes and reads as Rev D, the card of record,
    for every 4K block as RAM, EPROM or neither, down to the address inside each chip. Without the 2-4 shunts, R6 /
    R7 would hold the EPROM's A14 high. `Boot.test_rev_f_boots_clean` boots HBIOS.
  - `--mem-rev F-28C256` (JP1 3-5) and `F-28C256-W` (3-5 and 4-6): a 28C256 in IC5 (`Netlist.refit`: pin 1 A14,
    pin 27 !WE). `Decode.test_rev_f_28c256_in_ic5` checks that it reads as the 27C256 did. Read-only, it takes no
    write. Writable, the CPU writes it at the address it reads, and a RAM write reaches only the RAM.
  - `SystemV5`: the whole machine from its netlists (CPU Rev D, the IO panel, Rev F with the writable 28C256) boots
    Elf/OS v5 on HBIOS v1.0.8 and leaves the EEPROM untouched.
  - `tests/test_timing.RevDAt2MHz.test_memory_rev_f_28c256_write`: the write timing above.

## Files

| File | |
|---|---|
| `memory-rev-f.kicad_pcb` / `.kicad_sch` / `-sheet1.kicad_sch` / `.kicad_pro` | the KiCad master |
| `memory-rev-f-gerbers.zip`, `gerbers/` | the order files (4 copper layers; PTH and NPTH drills) |
| `memory-rev-f-schematic.pdf`, `schematic/memory-rev-f-schematic.pdf` | the KiCad schematic; the redrawn one |
| `memory-rev-f-placement.pdf`, `memory-rev-f-render-top.png`, `check-memory-rev-f-*.png` | placement, render, each copper layer read back from the zip |
| `memory-rev-f-bom.csv` | the parts list: Rev E's, with J1, JP1, JP2 and R6 / R7 (47k, upright); add four 2.54 mm shunts |
| `gen/` | `build.sh` and the scripts it runs (above) |
| `pcb-check.ini` | pcb-check's settings: name and rev, the bus edge, the tests, the LEDs' exemption |
