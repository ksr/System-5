# io-1861-keyboard-rev-a — KiCad conversion

Generated 2026-10-06 by `tools/eagle_to_kicad_all.py` from the Fusion XML export of the Eagle design `Video` in `hardware/io-1861-keyboard/eagle/rev-a/fusion-export/`. **The Eagle files are the record of what was designed and built; this KiCad project is derived from them and is regenerated from scratch on every run of the tool** (hand edits here will be lost - once a card is edited in KiCad, remove it from the tool's list). This revision was FABRICATED (see `hardware/FABRICATED.md`).

## Files

| File | What it is |
|---|---|
| `io-1861-keyboard-rev-a.kicad_pro` | project; DRC uses OSH Park rules (6 mil track, 5 mil clearance, 10 mil drill, 4 mil annular) as a modern-fab check, not the 2005 fab's rules |
| `io-1861-keyboard-rev-a.kicad_sch` | root sheet; 1 sub-sheet(s) `io-1861-keyboard-rev-a-sheetN.kicad_sch` mirror the Eagle sheets |
| `io-1861-keyboard-rev-a-eagle.kicad_sym` | project symbol library generated from the Eagle libraries used (units = Eagle gates) |
| `io-1861-keyboard-rev-a.kicad_pcb` | the board: 4 copper layers, 47 footprints, 999 track segments, 112 vias; 4 items on unmapped Eagle layers dropped |
| `io-1861-keyboard-rev-a-eagle.pretty/` | project footprint library extracted from the imported board |
| `reports/` | ERC (`erc.json`), DRC (`drc.json`), schematic PDF, board renders (`-top.png`, `-bottom.png`), netlist + `netlist-compare.txt` |

## Proof

Schematic-vs-board netlist comparison (`tools/kicad/compare_netlists.py`: every (reference, pad) partition must be identical): **MATCH (79/79 nets)**

```
  same connectivity, different net name: [('/Sheet 1/-INT', '-INT'), ('/Sheet 1/-MRD', '-MRD'), ('/Sheet 1/CLK', 'CLK'), ('/Sheet 1/DATA', 'DATA'), ('/Sheet 1/DATA0', 'DATA0'), ('/Sheet 1/DATA1', 'DATA1'), ('/Sheet 1/DATA2', 'DATA2'), ('/Sheet 1/DATA3', 'DATA3'), ('/Sheet 1/DATA4', 'DATA4'), ('/Sheet 1/DATA5', 'DATA5'), ('/Sheet 1/DATA6', 'DATA6'), ('/Sheet 1/DATA7', 'DATA7'), ('/Sheet 1/DMA_OUT', 'DMA_OUT'), ('/Sheet 1/EFK', 'EFK'), ('/Sheet 1/EFV', 'EFV'), ('/Sheet 1/IN', 'IN'), ('/Sheet 1/KD0', 'KD0'), ('/Sheet 1/KD1', 'KD1'), ('/Sheet 1/KD2', 'KD2'), ('/Sheet 1/KD3', 'KD3'), ('/Sheet 1/KD4', 'KD4'), ('/Sheet 1/KD5', 'KD5'), ('/Sheet 1/KD6', 'KD6'), ('/Sheet 1/KD7', 'KD7'), ('/Sheet 1/LCLK', 'LCLK'), ('/Sheet 1/N0', 'N0'), ('/Sheet 1/N1', 'N1'), ('/Sheet 1/N2', 'N2'), ('/Sheet 1/OUT', 'OUT'), ('/Sheet 1/PORT1', 'PORT1'), ('/Sheet 1/PORT2', 'PORT2'), ('/Sheet 1/PORT3', 'PORT3'), ('/Sheet 1/PORT4', 'PORT4'), ('/Sheet 1/PORT5', 'PORT5'), ('/Sheet 1/PORT6', 'PORT6'), ('/Sheet 1/PORT7', 'PORT7'), ('/Sheet 1/RESET', 'RESET'), ('/Sheet 1/SC0', 'SC0'), ('/Sheet 1/SC1', 'SC1'), ('/Sheet 1/TPA', 'TPA'), ('/Sheet 1/TPB', 'TPB'), ('Net-(IC1-OSC1)', 'N$19'), ('Net-(IC1-OSC2)', 'N$21'), ('Net-(IC1-RA0)', 'N$3'), ('Net-(IC1-RA1)', 'N$6'), ('Net-(IC1-RA2)', 'N$15'), ('Net-(IC2A-~{Q})', 'N$24'), ('Net-(IC11A-I)', 'N$5'), ('Net-(IC11A-O)', 'N$10'), ('Net-(IC11C-O)', 'N$28'), ('Net-(IC11D-O)', 'N$14'), ('Net-(IC11E-I)', 'N$41'), ('Net-(IC11E-O)', 'N$40'), ('Net-(IC11F-I)', 'N$20'), ('Net-(IC11F-O)', 'N$18'), ('Net-(IC13A-O)', 'N$11'), ('Net-(IC14A-I1)', 'N$13'), ('Net-(IC14A-O)', 'N$12'), ('Net-(IC14C-O)', 'N$26'), ('Net-(IC14D-O)', 'N$39'), ('Net-(IC16A-I1)', 'N$42'), ('Net-(IC16A-O)', 'N$43'), ('Net-(IC16B-O)', 'N$44'), ('Net-(LED1-C)', 'N$22'), ('Net-(LED2-C)', 'N$23'), ('Net-(LED3-C)', 'N$4'), ('Net-(LED4-C)', 'N$25'), ('Net-(LED5-C)', 'N$29'), ('Net-(R13-Pad1)', 'N$9'), ('Net-(U$1-SR)', 'N$16'), ('Net-(U$2--EF4)', 'N$17'), ('Net-(U$3-SYNC)', 'N$7'), ('Net-(U$3-VIDEO)', 'N$8'), ('Net-(U$5-DA)', 'N$27'), ('Net-(U$5-RES1)', 'N$1'), ('Net-(U$5-RES2)', 'N$2'), ('Net-(X1-PE1)', 'N$30')]
```

## Readability

`tools/kicad/sch_overlaps.py` over every sheet: text over text 3, text over a symbol body 6, text crossed by a line 2, items off the drawing frame or on the title block 0. What is left is mostly the Eagle drawing itself (parts placed that close in Eagle) or KiCad drawing pin numbers centred on short pins.

## Residual ERC / DRC

ERC by type: endpoint_off_grid 19, missing_input_pin 4, missing_power_pin 4, missing_unit 4, power_pin_not_driven 1, unconnected_wire_endpoint 17.
`isolated_pin_label` = the converter's per-net global labels (cosmetic); `power_pin_not_driven` / unused-unit notes are the same ones KiCad's own Eagle importer leaves. `unconnected_wire_endpoint` / `pin_not_connected` = wire stubs Eagle leaves bare (mostly net wires ending on a bus, which is drawn as graphics here); since 2026-09-23 the converter no longer hangs a label on every such end (that was most of the label clutter), so they show as KiCad warnings.

DRC by type: lib_footprint_mismatch 2, silk_edge_clearance 1, silk_over_copper 199, silk_overlap 22, text_height 6, text_thickness 6; unconnected items 0; schematic parity 0.
Silk-over-pad and clearance notes reflect the Eagle design as drawn; unconnected items are Eagle airwires (parts the design left unrouted).

Converter: converted: 80 symbols, 408 wires, 85 labels, 79 junctions, 5 bus lines, 27 no-connects
