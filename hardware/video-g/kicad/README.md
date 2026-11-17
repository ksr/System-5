# VIDEO-G 1.0 - KiCad

The two boards of VIDEO-G (design: [`../DESIGN.md`](../DESIGN.md)). **Generated, not hand-edited:** each board's
circuit is `gen/netlist.py`, its placement `gen/place.py`; `common/build.sh` makes everything else from them. Not
ordered; not built.

| Folder | Board | Size | ICs | Parts list |
|---|---|---|---|---|
| `text-1.0/` | VIDEO-G 1.0 TEXT: 6845 + IDT7134 text, status register, PS/2 keyboard, RCA + DB9, every decode (all memory-mapped, 7000-7FFF) | **188 x 96 mm** (47 mm taller than a standard card: Ken keeps it, 2026-11-17) | 24 | [`text-1.0/BOM.md`](text-1.0/BOM.md) |
| `gfx-1.0/` | VIDEO-G 1.0 GFX: 62256 graphics (two pages), Y and control registers, PS/2 mouse | 141 x 96 mm (standard) | 19 | [`gfx-1.0/BOM.md`](gfx-1.0/BOM.md) |

Both: 4 layers (F.Cu / B.Cu signals, In1.Cu a solid GND plane, In2.Cu a solid +5V plane: MEM3-E's stack-up), the
System-5 30-pin connector and card-guide keep-outs where every card has them, the 2 x 20 ribbon header along the same
side edge 88-148 mm from the bus edge (TEXT J6, GFX J4: a straight 40-way cable between neighbouring slots; pin map
`common/ribbon.py`). Silkscreen per Ken's rules: every reference outside its part with the IC type beside it, jacks,
jumpers and the LED labelled by function, the board name and cottageworker.com.

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
`lib/video-g-local`: IDT7134, Mini-DIN, RCA and DB9 from YACC1's Video V2.0 (copied), System-5's C30 bus connector and
0.1" bypass-cap footprints (the C30 labels' stroke raised to 0.15 mm for the fab; 2026-11-17: a courtyard on both and
an F.Fab body, 4.0 x 2.5 mm, on the cap, so that `pcb-check` knows where they are and finds each cap's "100n").

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
net open: TEXT uses 7 (seeds 0-10 tried: nine routed every net, 7 soonest). GFX has none (0); **its routed board is
the 2026-11-17 build's from before the fixed order**, updated in place since (silkscreen and courtyards: copper
untouched), so `build.sh` would route GFX afresh.

After a build: `python3 common/bom.py <board>` and, for the book, `python3 tools/kicad/sch/gen_schematic.py <board>/schematic` and
`python3 tools/kicad/sch/make_book.py`.

## Before ordering

**`pcb-check`, the check before an order (Ken, every system, since 2026-11-06; `hardware/BUILD-RULES.md`, section 2),
2026-11-17 at commit `fb6ef67`, both boards with `--tests`:**

```sh
~/Developer/pcb-check/pcb-check hardware/video-g/kicad/text-1.0/video-g-text.kicad_pcb hardware/video-g/kicad/text-1.0/video-g-text-gerbers.zip --layers 4 --tests
~/Developer/pcb-check/pcb-check hardware/video-g/kicad/gfx-1.0/video-g-gfx.kicad_pcb hardware/video-g/kicad/gfx-1.0/video-g-gfx-gerbers.zip --layers 4 --tests
```

| Board | Result | For Ken's eye |
|---|---|---|
| TEXT | **no failures, 0 warnings** | NOTE: EFOC, the 7416's open-collector keyboard flag, is pulled up on "another board": it reaches the bus -EF through the KBD-EF jumper JP3, and -EF has RN2 on TEXT and the backplane's pull-ups |
| GFX | **no failures, 1 warning** | WARN: no power LED (GFX has none; TEXT carries the PWR LED) |

Every other line passes on both: the copper rebuilt from the gerbers against the schematic, the design review, the
silkscreen (name and rev, `cottageworker.com`, every reference and value, none under a part), polarity, footprints,
fit, the layout rules (with `bus_edge = left` in `pcb-check.ini`: pcb-check finds a bus connector only by a DIN 41612
name), the bus pins against the bus Rev D's names (`tools/s5bus.py`), the fab's limits, the zip, a committed tree, one
rev, and the system's tests (s5emu's VIDEO-G tests, GBASIC's). Both also pass `tools/preorder_check.py --layers 4`, the
older check that `build.sh` ends with.

Still Ken's, before an order (settled 2026-11-17: TEXT stays 188 mm, the DB9 stays, every part's value on the
silkscreen, and the card is memory-mapped, which settles the ELF/OS boot loader's `OUT 4`): a look at the renders and
at `check-*.png`, the fab's gerber viewer, and **4 layers** on the order form; then `pcb-check ... --archive --fab F
--order NUMBER` (it stores what was sent beside the board) and the order in `hardware/FABRICATED.md`. The firmware is
written and has run only in the emulator: the character ROM (`firmware/video-g-chargen`), the ATmega keyboard/mouse
firmware (`embedded/video-g-ps2`), HBIOS's VIDEO-G build (`firmware/hbios/video-g`) and GBASIC (`software/gbasic`).
