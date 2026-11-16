# ide-cf-rev-a — KiCad conversion

Generated 2026-10-06 by `tools/eagle_to_kicad_all.py` from the Fusion XML export of the Eagle design `ide1-a` in `hardware/ide-cf/eagle/rev-a/fusion-export/`. **The Eagle files are the record of what was designed and built; this KiCad project is derived from them and is regenerated from scratch on every run of the tool** (hand edits here will be lost - once a card is edited in KiCad, remove it from the tool's list). This revision was FABRICATED (see `hardware/FABRICATED.md`).

## Files

| File | What it is |
|---|---|
| `ide-cf-rev-a.kicad_pro` | project; DRC uses OSH Park rules (6 mil track, 5 mil clearance, 10 mil drill, 4 mil annular) as a modern-fab check, not the 2005 fab's rules |
| `ide-cf-rev-a.kicad_sch` | root sheet; 1 sub-sheet(s) `ide-cf-rev-a-sheetN.kicad_sch` mirror the Eagle sheets |
| `ide-cf-rev-a-eagle.kicad_sym` | project symbol library generated from the Eagle libraries used (units = Eagle gates) |
| `ide-cf-rev-a.kicad_pcb` | the board: 4 copper layers, 24 footprints, 717 track segments, 115 vias; 2 items on unmapped Eagle layers dropped |
| `ide-cf-rev-a-eagle.pretty/` | project footprint library extracted from the imported board |
| `reports/` | ERC (`erc.json`), DRC (`drc.json`), schematic PDF, board renders (`-top.png`, `-bottom.png`), netlist + `netlist-compare.txt` |

## Proof

Schematic-vs-board netlist comparison (`tools/kicad/compare_netlists.py`: every (reference, pad) partition must be identical): **MATCH (49/49 nets)**

```
  same connectivity, different net name: [('/Sheet 1/D0', 'D0'), ('/Sheet 1/D1', 'D1'), ('/Sheet 1/D2', 'D2'), ('/Sheet 1/D3', 'D3'), ('/Sheet 1/D4', 'D4'), ('/Sheet 1/D5', 'D5'), ('/Sheet 1/D6', 'D6'), ('/Sheet 1/D7', 'D7'), ('/Sheet 1/IDERW', 'IDERW'), ('/Sheet 1/IDESEL', 'IDESEL'), ('/Sheet 1/INP', 'INP'), ('/Sheet 1/MRD', 'MRD'), ('/Sheet 1/N0', 'N0'), ('/Sheet 1/N1', 'N1'), ('/Sheet 1/N2', 'N2'), ('/Sheet 1/OUT', 'OUT'), ('/Sheet 1/PORT1', 'PORT1'), ('/Sheet 1/PORT2', 'PORT2'), ('/Sheet 1/PORT3', 'PORT3'), ('/Sheet 1/PORT4', 'PORT4'), ('/Sheet 1/PORT5', 'PORT5'), ('/Sheet 1/PORT6', 'PORT6'), ('/Sheet 1/PORT7', 'PORT7'), ('/Sheet 1/TPA', 'TPA'), ('/Sheet 1/TPB', 'TPB'), ('Net-(IC1A-I)', 'N$6'), ('Net-(IC1A-O)', 'N$7'), ('Net-(IC1B-I)', 'N$15'), ('Net-(IC1B-O)', 'N$23'), ('Net-(IC1C-O)', 'N$10'), ('Net-(IC1D-O)', 'N$12'), ('Net-(IC1E-I)', 'N$17'), ('Net-(IC1E-O)', 'N$13'), ('Net-(IC2A-I1)', 'N$11'), ('Net-(IC2A-O)', 'N$8'), ('Net-(IC2C-O)', 'N$14'), ('Net-(IC2D-O)', 'N$16'), ('Net-(IC5A-O)', 'N$9'), ('Net-(IC6B-O)', 'N$29'), ('Net-(IC6C-O)', 'N$30'), ('Net-(IC7-Q1)', 'N$24'), ('Net-(IC7-Q2)', 'N$25'), ('Net-(IC7-Q3)', 'N$26'), ('Net-(IC7-Q4)', 'N$27'), ('Net-(IC7-~{Q4})', 'N$28'), ('Net-(LED1-C)', 'N$22'), ('Net-(U$1--RESET)', 'RESET')]
```

## Readability

`tools/kicad/sch_overlaps.py` over every sheet: text over text 0, text over a symbol body 42, text crossed by a line 16, items off the drawing frame or on the title block 0. What is left is mostly the Eagle drawing itself (parts placed that close in Eagle) or KiCad drawing pin numbers centred on short pins.

## Residual ERC / DRC

ERC by type: endpoint_off_grid 24, unconnected_wire_endpoint 2.
`isolated_pin_label` = the converter's per-net global labels (cosmetic); `power_pin_not_driven` / unused-unit notes are the same ones KiCad's own Eagle importer leaves. `unconnected_wire_endpoint` / `pin_not_connected` = wire stubs Eagle leaves bare (mostly net wires ending on a bus, which is drawn as graphics here); since 2026-09-23 the converter no longer hangs a label on every such end (that was most of the label clutter), so they show as KiCad warnings.

DRC by type: silk_over_copper 116, silk_overlap 10; unconnected items 0; schematic parity 0.
Silk-over-pad and clearance notes reflect the Eagle design as drawn; unconnected items are Eagle airwires (parts the design left unrouted).

Converter: converted: 45 symbols, 318 wires, 35 labels, 69 junctions, 0 bus lines, 40 no-connects
