# VIDEO-G 1.0 - KiCad

The two boards of VIDEO-G (design: [`../DESIGN.md`](../DESIGN.md)). **Generated, not hand-edited:** each board's
circuit is `gen/netlist.py`, its placement `gen/place.py`; `common/build.sh` makes everything else from them. Not
ordered; not built.

| Folder | Board | Size | ICs | Parts list |
|---|---|---|---|---|
| `text-1.0/` | VIDEO-G 1.0 TEXT: 6845 + IDT7134 text, status port, PS/2 keyboard, RCA + DB9, every decode | **188 x 96 mm** (47 mm taller than a standard card: Ken to approve) | 24 | [`text-1.0/BOM.md`](text-1.0/BOM.md) |
| `gfx-1.0/` | VIDEO-G 1.0 GFX: 62256 graphics (two pages), Y and control registers, PS/2 mouse | 141 x 96 mm (standard) | 19 | [`gfx-1.0/BOM.md`](gfx-1.0/BOM.md) |

Both: 4 layers (F.Cu / B.Cu signals, In1.Cu a solid GND plane, In2.Cu a solid VCC plane: MEM3-E's stack-up), the
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

`common/`: `symlib.py` (symbol pins from the KiCad libraries), `ribbon.py`, `make_schematic.py`, `checknet.py` (the
exported netlist = `netlist.py`), `make_board.py`, `route.py` (Freerouting in and out, the inner layers as planes),
`route_leftovers.py` (the few connections Freerouting leaves; copied from MEM3-E's), `bom.py`, `build.sh`.
`lib/video-g-local`: IDT7134, Mini-DIN, RCA and DB9 from YACC1's Video V2.0 (copied), System-5's C30 bus connector and
0.1" bypass-cap footprints (the C30 labels' stroke raised to 0.15 mm for the fab).

## Rebuild

```sh
hardware/video-g/kicad/common/build.sh hardware/video-g/kicad/gfx-1.0
hardware/video-g/kicad/common/build.sh hardware/video-g/kicad/text-1.0
```

KiCad 10 and Freerouting 1.9 (`~/freerouting/freerouting.jar`). It runs: the netlist check, the schematic and ERC,
the netlist proof, the unrouted board, Freerouting (`MP` passes, default 60), the leftover router, DRC with the zones
refilled and schematic parity, the order files, and `tools/preorder_check.py --layers 4`. Then
`python3 common/bom.py <board>` and, for the book, `python3 tools/kicad/sch/gen_schematic.py <board>/schematic` and
`python3 tools/kicad/sch/make_book.py`.

## Before ordering

Ken: the TEXT height (188 mm; `../DESIGN.md` section 9 has the ways down), a look at the renders and at `check-*.png`,
the fab's gerber viewer, **4 layers** on the order form, and the ELF/OS boot loader's `OUT 4` (`../DESIGN.md` section
8). Both boards pass `tools/preorder_check.py --layers 4` (2026-11-02). The firmware is written and has run only in
the emulator: the character ROM (`firmware/video-g-chargen`), the ATmega keyboard/mouse firmware
(`embedded/video-g-ps2`), HBIOS's VIDEO-G build (`firmware/hbios/video-g`) and GBASIC (`software/gbasic`).
