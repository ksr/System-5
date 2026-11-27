# VIDEO-G 1.0 - KiCad

The two boards of VIDEO-G (design: [`../DESIGN.md`](../DESIGN.md)). **Generated, not hand-edited:** each board's
circuit is `gen/netlist.py`, its placement `gen/place.py`; `common/build.sh` makes everything else from them. Not
ordered; not built.

| Folder | Board | Size | ICs | Parts list |
|---|---|---|---|---|
| `text-1.0/` | VIDEO-G 1.0 TEXT: 6845 + IDT7134 text, status register, PS/2 keyboard, RCA + DE-9, every decode (all memory-mapped, 7000-7FFF) | **188 x 106.6 mm** (47 mm longer than a standard card: Ken keeps it, 2026-11-17; and since 2026-11-18 10.4 mm more at the +5V end, for the 36-pin bus connector) | 24 | [`text-1.0/BOM.md`](text-1.0/BOM.md) |
| `gfx-1.0/` | VIDEO-G 1.0 GFX: 62256 graphics (two pages), Y and control registers, PS/2 mouse, PWR LED | 141 x 96 mm (standard) | 19 | [`gfx-1.0/BOM.md`](gfx-1.0/BOM.md) |

Both: 4 layers (F.Cu / B.Cu signals, In1.Cu a solid GND plane, In2.Cu a solid +5V plane: MEM3-E's stack-up), the
System-5 bus connector (GFX the 30-pin one; TEXT the 36-pin one since 2026-11-18, for its keyboard flag's choice of four
EF lines: its positions 1-30 where the 30-pin connector's pins were, the board grown at the +5V end) and card-guide
keep-outs where every card has them, the 2 x 20 ribbon header along the same
side edge 78-138 mm from the bus edge (pins 83.6-131.9 mm) (TEXT J6, GFX J4: a straight 40-way cable between neighbouring slots; pin map
`common/ribbon.py`). Silkscreen per Ken's rules: every reference outside its part with the IC type beside it, jacks,
jumpers and the LED labelled by function, the board name and cottageworker.com. **Since 2026-11-18 every text reads
upright with the card standing in the bus, connector down** (Ken's rule for every board; he asked for it on TEXT and
GFX that day): KiCad angle 270, each label at the first spot clear of every pad, part, other text and the card-guide
strips, under its part with the card standing first (`common/silk.py` with `tools/kicad/silk270.py`); the bus pins'
names in two staggered columns (the backplane's names on both boards: `+5V`, `-RESET`); the jumpers' settings at their
ends (TEXT's JP1 NTSC / 5151, JP2 + / -); the name line alone at angle 0 along the bottom edge as drawn, just above the
guide strip (up the right-hand side standing). The copper did not change: `common/silk.py <board>` rewrote the
silkscreen of the routed boards, every track, via, pad and zone checked the same.

**The bus connector is drawn as the part it is since the night of 2026-11-18.** J1 is a single-row right-angle pin
header: its plastic body lies on the board between the pads and the card edge, 1.5 to 4.0 mm from the pads, and its
pins run on past the edge (the photos of the built MEM3-E and BUSDRV-B show it). The C30 and C36 footprints had pads
and a courtyard round them and nothing else, so the label placer and `pcb-check` both took that strip for free board:
`J1 BUS` was printed there on both boards, part of it under the header, and half of TEXT's JP1 label with it. Both
footprints now carry the body (F.Fab), a courtyard round body and pads, and KiCad's 3D model of the header, so the
renders show the connector and the placer keeps every label off it. `J1 BUS` stands past the header's +5V end on GFX
and beside the pin names, between IC1 and IC2, on TEXT; TEXT's `JP1 MONITOR` is under its jumper in the corner past
the header's GND end, `NTSC` and `5151` at the jumper's ends. Silkscreen only, again: `common/silk.py <board>` brings
J1's drawing up to its library file (`tools/kicad/fp_update.py`) and places the labels afresh, and it and
`common/make_board.py` now stop with an error when a label finds no room (the label had been left out without a word).

## Files (per board)

| File | What |
|---|---|
| `gen/netlist.py` | THE circuit: parts, nets, no-connects, what to buy; `python3 gen/netlist.py` checks every symbol pin |
| `gen/place.py` | the placement, silkscreen labels and texts |
| `<board>.kicad_sch` | the working schematic (one sheet, net labels): ERC, the board's parity |
| `<board>.kicad_pcb` | the routed board |
| `schematic/` | the readable schematic, redrawn and proven by `tools/kicad/sch/gen_schematic.py` (in the book `docs/manual/pdf/system5-schematics.pdf`) |
| `reports/` | ERC, DRC, the exported netlist |
| `<board>-gerbers.zip`, `gerbers/`, `check-*.png` | the order files and one picture per copper layer from them |
| `BOM.md` | the parts list (`common/bom.py`) |
| `pcb-check.ini` | `pcb-check`'s settings: name, rev, size, slot pitch, the bus edge, the bus pin list (`tools/s5bus.py`, the bus Rev D's pin names), the system's tests |

`common/`: `symlib.py` (symbol pins from the KiCad libraries), `ribbon.py`, `make_schematic.py`, `checknet.py` (the
exported netlist = `netlist.py`), `make_board.py`, `route.py` (Freerouting in and out, the inner layers as planes),
`route_leftovers.py` (the few connections Freerouting leaves; copied from MEM3-E's), `silk.py` (every label, also on
a routed board: `<KiCad python> common/silk.py <board>` changes the silkscreen only), `bom.py`, `build.sh`.
`lib/video-g-local`: IDT7134, Mini-DIN, RCA and DE-9 from YACC1's Video V2.0 (copied), System-5's C30 bus connector
(GFX), the 36-pin C36 (TEXT; the other 36-pin cards' footprint) and 0.1" bypass-cap footprints (the C30 labels'
stroke raised to 0.15 mm for the fab; 2026-11-17: a courtyard on both and an F.Fab body, 4.0 x 2.5 mm, on the cap, so
that `pcb-check` knows where they are and finds each cap's "100n"; 2026-11-18: the right-angle header's body, a
courtyard round it and its 3D model on C30 and C36, above; 2026-11-19: the RCA jack's body on F.Fab, the outline its
silkscreen has, for `pcb-check`'s new BODIES line, which names a part with nothing drawn on the fab layer: TEXT's J2
was the one. `J2 RCA COMPOSITE` moved 0.15 mm with it, the label placer going by the body where it had gone by the
courtyard). The DE-9, Eagle's F09HP, had only its nine pins' tails on the fab layer, 11 x 3.6 mm of a 31 x 14 mm
connector, which `pcb-check` took for the whole part (its BODIES line names such a drawing since its `0e99e19`): the
connector's outer line is on F.Fab now, and `J3 DE-9 TTL 5151` keeps its place by a spot of its own in `place.py`, the
1.5 mm between the DE-9's back and R4's lead being narrower than the placer's steps. `common/silk.py <board>` brings
the drawing of every part from this library up to its file before it places the labels.

## Rebuild

```sh
hardware/video-g/kicad/common/build.sh hardware/video-g/kicad/gfx-1.0
hardware/video-g/kicad/common/build.sh hardware/video-g/kicad/text-1.0
```

KiCad 10 and Freerouting 1.9 (`~/freerouting/freerouting.jar`). It runs: the netlist check, the schematic and ERC,
the netlist proof, the unrouted board, Freerouting (`MP` passes at most, default 100), the leftover router, DRC with the zones
refilled and schematic parity, the order files, and `tools/preorder_check.py --layers 4`.

**The routing is reproducible since 2026-11-17.** `route.py` writes Freerouting's input in a fixed order and without
the parts' drawn outlines: KiCad lists components, images and pins in a different order on every build (new UUIDs),
and Freerouting's result follows that order and even the outlines (adding two courtyards turned a complete route into
one that stalled), so one build of TEXT left VMA open where the build before had routed everything. Now the same
`gen/` files give the same board. `ROUTE_SEED` in `gen/place.py` shuffles the order reproducibly when one leaves a
net open: TEXT used 7 to 2026-11-24 (seeds 0-10 tried in 2026-11-17's form: nine routed every net, 7 soonest), 0 since. GFX uses 0, the sorted order: rebuilt
the evening of 2026-11-17 with its power LED, it routed every net at once (1697 track segments, 97 vias). The ordering
code is `tools/kicad/dsn_order.py` since then, shared with CPU Rev D (`route.py` gives the same input as before).

**TEXT was routed again on 2026-11-18**, for the 36-pin connector and the 2 x 4 KBD FLAG block: seed 7 still routes
every net (2616 track segments, 133 vias; 3 minutes of routing, then 72 minutes of Freerouting's optimization, so a
full build of TEXT takes about an hour and a quarter). The silkscreen work after it did not need another: a new build
gives Freerouting the same input, byte for byte but for the file's own path, and the same silkscreen to the micrometre
(checked in a copy of the tree).

**TEXT was routed again on 2026-11-24**, with its 6845 write-only (`DESIGN.md`, section 4: seven pins moved, no part and no
silkscreen text changed): seed 0, 2483 track segments and 152 vias. Freerouting routed every net in 4 minutes and then
shortened the tracks for 70; the leftover router had nothing to do; DRC 0 errors and 0 warnings. (Seed 7 routed every net too, but
the track the leftover router made beside J1's pins broke the 0.20 mm clearance in six places.) The 83 parts stand where they
stood, and of the 133 silkscreen texts one moved: `C22 100n`, 0.5 mm, at its size (`place.SPOTS`, `SIZES`; Ken: "move the C22
label clear of IC22"). A 14-pin chip is 19.3 mm long, 0.65 mm past each end of the socket the placer goes by, and the label's
end had been 0.15 mm under it; it is 0.35 mm clear now. Silkscreen only: copper, masks, outline and drills as routed.

After a build: `python3 common/bom.py <board>` and, for the book, `python3 tools/kicad/sch/gen_schematic.py <board>/schematic` and
`python3 tools/kicad/sch/make_book.py`.

## Before ordering

**The latest result, of both boards as they are now (TEXT routed again with its 6845 write-only, 2026-11-24): QA's
run of 2026-11-25 at elf `38fc4d0`, `pcb-check --tests`: TEXT no failures, 0 warnings (netlist 160 of 160; the copper
rebuilt from the gerbers by two methods, which agree; 16 of 16 faults planted in copies of the zip noticed); GFX no
failures, 0 warnings (124 of 124; 16 of 16). The same NOTE on TEXT's EFOC as below. `tools/qa.py full` at `38fc4d0`:
OK.** The results below are of TEXT before that route.

**`pcb-check`, the check before an order (Ken, every system, since 2026-11-06; `hardware/BUILD-RULES.md`, section 2):
both boards as they were before TEXT's route of 2026-11-24, with `--tests`, 2026-11-19: GFX at elf `77257f1` (run by the pcb-check session); TEXT at
`77257f1` (the same), at `688e6ed` after its four KBD FLAG names moved 0.5 mm off JP3's outline, at `b4692e9`
(pcb-check `bd032dd`, with its new BODIES line) after the RCA jack's body went on the fab layer, and at `b2252b7`
(pcb-check `0b45f65`) after the DE-9's; GFX again at `b2252b7` without its tests, the board unchanged:**

```sh
~/Developer/pcb-check/pcb-check hardware/video-g/kicad/text-1.0/video-g-text.kicad_pcb hardware/video-g/kicad/text-1.0/video-g-text-gerbers.zip --layers 4 --tests
~/Developer/pcb-check/pcb-check hardware/video-g/kicad/gfx-1.0/video-g-gfx.kicad_pcb hardware/video-g/kicad/gfx-1.0/video-g-gfx-gerbers.zip --layers 4 --tests
```

| Board | Result | For Ken's eye |
|---|---|---|
| TEXT | **no failures, 0 warnings** (the 36 bus pins on J1 as the bus definition has them; fit 188.1 x 106.7 mm; netlist 162 of 162; J1's body on F.Fab and no text under it or under any other part; BODIES: every part drawn with its body) | NOTE: EFOC, the 7416's open-collector keyboard flag, is pulled up on "another board": it reaches a bus flag line through JP3, and -EF has RN2 on TEXT and the backplane's pull-ups; -EF1 to -EF3 have the bus Rev D's only |
| GFX | **no failures, 0 warnings** (the 30 bus pins on J1; netlist 124 of 124; no text under J1's body or any other part) | - |

Every other line passes on both: the copper rebuilt from the gerbers against the schematic, the design review, the
silkscreen (name and rev, `cottageworker.com`, every reference and value, none under a part), polarity, footprints,
fit, the layout rules (with `bus_edge = left` in `pcb-check.ini`: pcb-check finds a bus connector only by a DIN 41612
name), the bus pins against the bus Rev D's names (`tools/s5bus.py`), the fab's limits, the zip, a committed tree, one
rev, and the system's tests (s5emu's VIDEO-G tests, GBASIC's). Both also pass `tools/preorder_check.py --layers 4`, the
older check that `build.sh` ends with (DRC 0 errors and 0 warnings). Their earlier passes (2026-11-17: TEXT at
`fb6ef67` and `0341f8a`, GFX after its power LED; 2026-11-18 at `e4d2fd5`, the silkscreen at 270) were of the 30-pin
TEXT, and of boards with `J1 BUS` partly under the bus header, which `pcb-check` could not see then.

Still Ken's, before an order (settled 2026-11-17: TEXT stays 188 mm, the DE-9 stays, every part's value on the
silkscreen, and the card is memory-mapped, which settles the ELF/OS boot loader's `OUT 4`): a look at the renders and
at `check-*.png`, the fab's gerber viewer, and **4 layers** on the order form; then `pcb-check ... --archive --fab F
--order NUMBER` (it stores what was sent beside the board) and the order in `hardware/FABRICATED.md`. The firmware is
written and has run only in the emulator: the character ROM (`firmware/video-g-chargen`), the ATmega keyboard/mouse
firmware (`embedded/video-g-ps2`), HBIOS's VIDEO-G build (`firmware/hbios/video-g`) and GBASIC (`software/gbasic`).
