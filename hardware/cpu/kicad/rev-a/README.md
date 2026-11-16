# cpu-rev-a — KiCad conversion

Generated 2026-10-06 by `tools/eagle_to_kicad_all.py` from the Fusion XML export of the Eagle design `cpu2-a` in `hardware/cpu/eagle/rev-a/fusion-export/`. **The Eagle files are the record of what was designed and built; this KiCad project is derived from them and is regenerated from scratch on every run of the tool** (hand edits here will be lost - once a card is edited in KiCad, remove it from the tool's list). This revision was FABRICATED (see `hardware/FABRICATED.md`).

## Files

| File | What it is |
|---|---|
| `cpu-rev-a.kicad_pro` | project; DRC uses OSH Park rules (6 mil track, 5 mil clearance, 10 mil drill, 4 mil annular) as a modern-fab check, not the 2005 fab's rules |
| `cpu-rev-a.kicad_sch` | root sheet; 1 sub-sheet(s) `cpu-rev-a-sheetN.kicad_sch` mirror the Eagle sheets |
| `cpu-rev-a-eagle.kicad_sym` | project symbol library generated from the Eagle libraries used (units = Eagle gates) |
| `cpu-rev-a.kicad_pcb` | the board: 4 copper layers, 61 footprints, 1465 track segments, 291 vias; 2 items on unmapped Eagle layers dropped |
| `cpu-rev-a-eagle.pretty/` | project footprint library extracted from the imported board |
| `reports/` | ERC (`erc.json`), DRC (`drc.json`), schematic PDF, board renders (`-top.png`, `-bottom.png`), netlist + `netlist-compare.txt` |

## Proof

Schematic-vs-board netlist comparison (`tools/kicad/compare_netlists.py`: every (reference, pad) partition must be identical): **MATCH (88/88 nets)**

```
  same connectivity, different net name: [('/Sheet 1/-EF4', '-EF4'), ('/Sheet 1/-INT', '-INT'), ('/Sheet 1/-LOAD', '-LOAD'), ('/Sheet 1/-MRD', '-MRD'), ('/Sheet 1/-MRW', '-MRW'), ('/Sheet 1/-PAUSE', '-PAUSE'), ('/Sheet 1/-RESET', '-RESET'), ('/Sheet 1/-RUN', '-RUN'), ('/Sheet 1/-VMA', '-VMA'), ('/Sheet 1/ADDR0', 'ADDR0'), ('/Sheet 1/ADDR1', 'ADDR1'), ('/Sheet 1/ADDR2', 'ADDR2'), ('/Sheet 1/ADDR3', 'ADDR3'), ('/Sheet 1/ADDR4', 'ADDR4'), ('/Sheet 1/ADDR5', 'ADDR5'), ('/Sheet 1/ADDR6', 'ADDR6'), ('/Sheet 1/ADDR7', 'ADDR7'), ('/Sheet 1/ADDR8', 'ADDR8'), ('/Sheet 1/ADDR9', 'ADDR9'), ('/Sheet 1/ADDR10', 'ADDR10'), ('/Sheet 1/ADDR11', 'ADDR11'), ('/Sheet 1/ADDR12', 'ADDR12'), ('/Sheet 1/ADDR13', 'ADDR13'), ('/Sheet 1/ADDR14', 'ADDR14'), ('/Sheet 1/ADDR15', 'ADDR15'), ('/Sheet 1/CLEAR', 'CLEAR'), ('/Sheet 1/DATA0', 'DATA0'), ('/Sheet 1/DATA1', 'DATA1'), ('/Sheet 1/DATA2', 'DATA2'), ('/Sheet 1/DATA3', 'DATA3'), ('/Sheet 1/DATA4', 'DATA4'), ('/Sheet 1/DATA5', 'DATA5'), ('/Sheet 1/DATA6', 'DATA6'), ('/Sheet 1/DATA7', 'DATA7'), ('/Sheet 1/DMA_IN', 'DMA_IN'), ('/Sheet 1/DMA_OUT', 'DMA_OUT'), ('/Sheet 1/EF1', 'EF1'), ('/Sheet 1/EF2', 'EF2'), ('/Sheet 1/EF3', 'EF3'), ('/Sheet 1/EF4', 'EF4'), ('/Sheet 1/FEF', 'FEF'), ('/Sheet 1/KEF', 'KEF'), ('/Sheet 1/LCLK', 'LCLK'), ('/Sheet 1/Q', 'Q'), ('/Sheet 1/SC0', 'SC0'), ('/Sheet 1/SC1', 'SC1'), ('/Sheet 1/TPA', 'TPA'), ('/Sheet 1/TPB', 'TPB'), ('/Sheet 1/VEF', 'VEF'), ('/Sheet 1/WAIT', 'WAIT'), ('Net-(IC2-~{CE})', 'N$3'), ('Net-(IC3A-I3)', 'N$22'), ('Net-(IC4A-I3)', 'N$24'), ('Net-(IC5A-C)', 'N$19'), ('Net-(IC5A-R{slash}C)', 'N$17'), ('Net-(IC5A-~{Q})', 'N$15'), ('Net-(IC6D-O)', 'N$25'), ('Net-(IC6F-O)', 'N$7'), ('Net-(IC7A-I0)', 'N$16'), ('Net-(IC7A-O)', 'N$18'), ('Net-(IC7B-O)', 'N$23'), ('Net-(IC7C-I0)', 'N$21'), ('Net-(IC7D-I0)', 'N$37'), ('Net-(IC7D-I1)', 'N$4'), ('Net-(IC7D-O)', 'N$1'), ('Net-(IC8A-Q)', 'N$27'), ('Net-(IC8B-~{Q})', 'N$6'), ('Net-(IC9-G1)', 'N$38'), ('Net-(IC9-G2A)', 'N$20'), ('Net-(IC9-Y0)', 'N$29'), ('Net-(IC9-Y1)', 'N$30'), ('Net-(IC9-Y2)', 'N$31'), ('Net-(IC9-Y3)', 'N$32'), ('Net-(IC9-Y4)', 'N$33'), ('Net-(IC9-Y5)', 'N$34'), ('Net-(IC9-Y6)', 'N$35'), ('Net-(IC9-Y7)', 'N$36'), ('Net-(LED1-C)', 'N$5'), ('Net-(LED2-C)', 'N$10'), ('Net-(LED3-C)', 'N$9'), ('Net-(LED4-PadA)', 'N$8'), ('Net-(LED5-PadA)', 'N$13'), ('Net-(S1-S1)', 'N$2'), ('Net-(U$1-N0)', 'N0'), ('Net-(U$1-N1)', 'N1'), ('Net-(U$1-N2)', 'N2')]
```

## Readability

`tools/kicad/sch_overlaps.py` over every sheet: text over text 5, text over a symbol body 12, text crossed by a line 11, items off the drawing frame or on the title block 0. What is left is mostly the Eagle drawing itself (parts placed that close in Eagle) or KiCad drawing pin numbers centred on short pins.

## Residual ERC / DRC

ERC by type: endpoint_off_grid 26, missing_input_pin 1, missing_power_pin 1, missing_unit 1, unconnected_wire_endpoint 11.
`isolated_pin_label` = the converter's per-net global labels (cosmetic); `power_pin_not_driven` / unused-unit notes are the same ones KiCad's own Eagle importer leaves. `unconnected_wire_endpoint` / `pin_not_connected` = wire stubs Eagle leaves bare (mostly net wires ending on a bus, which is drawn as graphics here); since 2026-09-23 the converter no longer hangs a label on every such end (that was most of the label clutter), so they show as KiCad warnings.

DRC by type: lib_footprint_mismatch 1, silk_edge_clearance 1, silk_over_copper 199, silk_overlap 28; unconnected items 0; schematic parity 0.
Silk-over-pad and clearance notes reflect the Eagle design as drawn; unconnected items are Eagle airwires (parts the design left unrouted).

Converter: converted: 88 symbols, 478 wires, 136 labels, 119 junctions, 12 bus lines, 12 no-connects
