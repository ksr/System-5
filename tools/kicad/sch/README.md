# Redrawn schematics (tools/kicad/sch)

Readable, block-structured KiCad schematics for the System-5 cards, drawn from each card's proven board netlist (2026-10-26).
The way YACC1-D draws its generated cards: a root sheet and one sheet per functional block, the parts placed by ELK (the
Eclipse Layout Kernel) and the nets between them drawn as wires, KiCad's own symbols where they fit.

| File | What it is |
|---|---|
| `gen_schematic.py` | the generator: reads `<card>/kicad/<rev>/reports/netlist.net`, picks symbols, draws the sheets from the card's `schematic/spec.py`, then proves the result |
| `sheet.py` | the sheet writer (symbols, stubs, labels, power symbols), from YACC1-D's `gen_cf.py`, made card-independent |
| `sch_wire.py`, `elk_layout.js` | ELK placement and wiring, from YACC1-D, unchanged but for the import |
| `make_system5_lib.py` → `system5.kicad_sym` | symbols KiCad lacks: the 30-pin System-5 bus, the IDT7134, the 40-pin IDE header |
| `build_all.sh` | redraws and proves every card and the bus, then runs `make_book.py` |
| `make_book.py` | binds every card's PDF into `docs/manual/pdf/system5-schematics.pdf`: a cover, a contents page and a bookmark per card and per sheet |

```bash
cd tools/kicad/sch && npm install
```
```bash
tools/kicad/sch/build_all.sh
```

## What is proven

- **The circuit is not typed in.** It comes from the board netlist, which is itself proven equal to the board (and, where they survive, the 2005 order gerbers).
- **The drawing is checked again:** KiCad's netlist of the new schematic must group every pin exactly as the board netlist does (every net of two or more pins; names may differ). The generator prints `MATCH` or the differences, and exits non-zero on a difference.
- **ERC** runs on each (errors only); the report is `<proj>-erc.json`.
- **Symbols:** KiCad's standard symbol is used only if it has every pin number the board uses; otherwise the card's own converted Eagle symbol.
- **Nothing on the board side changes.** Each schematic is its own KiCad project in `<card>/kicad/<rev>/schematic/`; the board, its project and `MASTER` are untouched.

## The cards (2026-10-26)

| Card | Folder | Sheets | Proof | ERC errors |
|---|---|---|---|---|
| IO panel Rev A (new, 2026-10-30) | `hardware/io-panel/kicad/rev-a/schematic/` | Decode, Output, Input, Control, Power | MATCH 64 | 0 |
| CPU Rev D (new, 2026-10-30) | `hardware/cpu/kicad/rev-d/schematic/` | CPU, Clock, Control, Boot, Flags, Power | MATCH 78 | 0 |
| CPU Rev A (as drawn) | `hardware/cpu/kicad/rev-a/schematic/` | CPU, Control, Boot, Flags, Power | MATCH 88 nets | 0 |
| Memory Rev E | `hardware/memory/kicad/rev-e/schematic/` | Address, RAM lo, RAM hi, EPROM lo, EPROM hi, Memory, Power | MATCH 88 | 0 |
| 6845 video Rev B | `hardware/video-6845/kicad/rev-b/schematic/` | Decode, VRAM+CRTC, Clocks, Video, Power | MATCH 99 | 0 |
| IO (1861 + keyboard) Rev A | `hardware/io-1861-keyboard/kicad/rev-a/schematic/` | Decode, Keyboard, 1861, Power | MATCH 79 | 1 (the mini-DIN's shield pin is a power input in its Eagle symbol) |
| IDE/CF Rev A | `hardware/ide-cf/kicad/rev-a/schematic/` | Decode, IDE, Power | MATCH 49 | 0 |
| Bus driver Rev B | `hardware/bus-driver/kicad/rev-b/schematic/` | Expanders, Nano, Power | MATCH 41 | 0 |
| Bus backplane 2009 | `hardware/bus/kicad/rev-2009/schematic/` | Slots, Power | MATCH 36 | 0 |
| Bus backplane Rev D (new) | `hardware/bus/kicad/rev-d/schematic/` | Slots, Pull-ups, Power | MATCH 37 | 0 |

Each folder: `spec.py` (the blocks, their notes, names for unnamed nets, symbol overrides), the `.kicad_sch` sheets and `.kicad_pro`, the PDF, KiCad's netlist of the drawing and the ERC report.

## Keeping them up to date

Ken's rule (2026-10-28): the PDFs follow the boards. After any change to a card's circuit, re-export its `reports/netlist.net`, redraw it and rebuild the book (`build_all.sh` does every card), and commit the PDFs with the change. `tools/preorder_check.py` does it too, as its SCHEMATIC check, for any board with a `schematic/spec.py`: it first proves `reports/netlist.net` against the board, so a stale netlist fails rather than giving a stale drawing.

## The sheets

- Each sheet is the smallest that holds its drawing, A4 to A0, landscape or portrait (a tall, narrow drawing goes portrait). The drawing may run below the title block's top edge where it stays left of it.
- The title block carries the sheet's place in the card, how it was drawn and the card's theory notes (`spec.py` `THEORY`), wrapped at semicolons to fit.
- Most 2005 Eagle drawings carry no values for resistors and capacitors: they show as R and C. A `VALUES` dict in `spec.py` gives real ones.

## Adding a card

Convert it first (`tools/eagle_to_kicad_all.py --only ...`), so it has `reports/netlist.net`. Then write `schematic/spec.py` (copy one), add the folder to `build_all.sh` and to `make_book.py`'s `CARDS`, run `gen_schematic.py` on the folder, look at the PDF and move parts between blocks until each sheet reads well. Spare gates (inputs on a supply, outputs open) and the chips' power units go to the Power sheet by themselves.
