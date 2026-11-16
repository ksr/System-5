# bus-rev-2009 — KiCad conversion

Generated 2026-10-26 by `tools/eagle_to_kicad_all.py` from the Fusion XML export of the Eagle design `bus` in `hardware/bus/eagle/rev-2009/fusion-export/`. **The Eagle files are the record of what was designed and built; this KiCad project is derived from them and is regenerated from scratch on every run of the tool** (hand edits here will be lost - once a card is edited in KiCad, remove it from the tool's list). This revision was never fabricated (or its build status is unknown, see `hardware/FABRICATED.md`).

## Files

| File | What it is |
|---|---|
| `bus-rev-2009.kicad_pro` | project; DRC uses OSH Park rules (6 mil track, 5 mil clearance, 10 mil drill, 4 mil annular) as a modern-fab check, not the 2005 fab's rules |
| `bus-rev-2009.kicad_sch` | root sheet; 1 sub-sheet(s) `bus-rev-2009-sheetN.kicad_sch` mirror the Eagle sheets |
| `bus-rev-2009-eagle.kicad_sym` | project symbol library generated from the Eagle libraries used (units = Eagle gates) |
| `bus-rev-2009.kicad_pcb` | the board: 4 copper layers, 15 footprints, 200 track segments, 0 vias; 2 items on unmapped Eagle layers dropped |
| `bus-rev-2009-eagle.pretty/` | project footprint library extracted from the imported board |
| `reports/` | ERC (`erc.json`), DRC (`drc.json`), schematic PDF, board renders (`-top.png`, `-bottom.png`), netlist + `netlist-compare.txt` |

## Proof

Schematic-vs-board netlist comparison (`tools/kicad/compare_netlists.py`: every (reference, pad) partition must be identical): **MATCH (36/36 nets)**

```
  same connectivity, different net name: [('/Sheet 1/5V', '5V'), ('/Sheet 1/A0', 'A0'), ('/Sheet 1/A1', 'A1'), ('/Sheet 1/A2', 'A2'), ('/Sheet 1/A3', 'A3'), ('/Sheet 1/A4', 'A4'), ('/Sheet 1/A5', 'A5'), ('/Sheet 1/A6', 'A6'), ('/Sheet 1/A7', 'A7'), ('/Sheet 1/D0', 'D0'), ('/Sheet 1/D1', 'D1'), ('/Sheet 1/D2', 'D2'), ('/Sheet 1/D3', 'D3'), ('/Sheet 1/D4', 'D4'), ('/Sheet 1/D5', 'D5'), ('/Sheet 1/D6', 'D6'), ('/Sheet 1/D7', 'D7'), ('/Sheet 1/EF', 'EF'), ('/Sheet 1/EF1', 'EF1'), ('/Sheet 1/EF2', 'EF2'), ('/Sheet 1/EF3', 'EF3'), ('/Sheet 1/EXP', 'EXP'), ('/Sheet 1/INP', 'INP'), ('/Sheet 1/INT', 'INT'), ('/Sheet 1/MRD', 'MRD'), ('/Sheet 1/MRW', 'MRW'), ('/Sheet 1/N0', 'N0'), ('/Sheet 1/N1', 'N1'), ('/Sheet 1/N2', 'N2'), ('/Sheet 1/OUT', 'OUT'), ('/Sheet 1/Q', 'Q'), ('/Sheet 1/RESET', 'RESET'), ('/Sheet 1/TPA', 'TPA'), ('/Sheet 1/TPB', 'TPB'), ('/Sheet 1/VMA', 'VMA')]
```

## Readability

`tools/kicad/sch_overlaps.py` over every sheet: text over text 0, text over a symbol body 6, text crossed by a line 0, items off the drawing frame or on the title block 0. What is left is mostly the Eagle drawing itself (parts placed that close in Eagle) or KiCad drawing pin numbers centred on short pins.

## Residual ERC / DRC

ERC by type: power_pin_not_driven 2, unconnected_wire_endpoint 60.
`isolated_pin_label` = the converter's per-net global labels (cosmetic); `power_pin_not_driven` / unused-unit notes are the same ones KiCad's own Eagle importer leaves. `unconnected_wire_endpoint` / `pin_not_connected` = wire stubs Eagle leaves bare (mostly net wires ending on a bus, which is drawn as graphics here); since 2026-09-23 the converter no longer hangs a label on every such end (that was most of the label clutter), so they show as KiCad warnings.

DRC by type: shorting_items 1, silk_over_copper 7, solder_mask_bridge 1, track_dangling 3; unconnected items 0; schematic parity 0.
Silk-over-pad and clearance notes reflect the Eagle design as drawn; unconnected items are Eagle airwires (parts the design left unrouted).

Converter: converted: 8 symbols, 216 wires, 217 labels, 0 junctions, 6 bus lines, 2 no-connects
