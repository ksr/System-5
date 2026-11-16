# memory-rev-c — KiCad conversion

Generated 2026-10-05 by `tools/eagle_to_kicad_all.py` from the Fusion XML export of the Eagle design `mem3-c` in `hardware/memory/eagle/rev-c/fusion-export/`. **The Eagle files are the record of what was designed and built; this KiCad project is derived from them and is regenerated from scratch on every run of the tool** (hand edits here will be lost - once a card is edited in KiCad, remove it from the tool's list). This revision was never fabricated (or its build status is unknown, see `hardware/FABRICATED.md`).

## Files

| File | What it is |
|---|---|
| `memory-rev-c.kicad_pro` | project; DRC uses OSH Park rules (6 mil track, 5 mil clearance, 10 mil drill, 4 mil annular) as a modern-fab check, not the 2005 fab's rules |
| `memory-rev-c.kicad_sch` | root sheet; 1 sub-sheet(s) `memory-rev-c-sheetN.kicad_sch` mirror the Eagle sheets |
| `memory-rev-c-eagle.kicad_sym` | project symbol library generated from the Eagle libraries used (units = Eagle gates) |
| `memory-rev-c.kicad_pcb` | the board: 4 copper layers, 50 footprints, 1630 track segments, 165 vias |
| `memory-rev-c-eagle.pretty/` | project footprint library extracted from the imported board |
| `reports/` | ERC (`erc.json`), DRC (`drc.json`), schematic PDF, board renders (`-top.png`, `-bottom.png`), netlist + `netlist-compare.txt` |

## Proof

Schematic-vs-board netlist comparison (`tools/kicad/compare_netlists.py`: every (reference, pad) partition must be identical): **MATCH (92/92 nets)**

```
  same connectivity, different net name: [('/Sheet 1/BUFFADDR0', 'BUFFADDR0'), ('/Sheet 1/BUFFADDR1', 'BUFFADDR1'), ('/Sheet 1/BUFFADDR2', 'BUFFADDR2'), ('/Sheet 1/BUFFADDR3', 'BUFFADDR3'), ('/Sheet 1/BUFFADDR4', 'BUFFADDR4'), ('/Sheet 1/BUFFADDR5', 'BUFFADDR5'), ('/Sheet 1/BUFFADDR6', 'BUFFADDR6'), ('/Sheet 1/BUFFADDR7', 'BUFFADDR7'), ('/Sheet 1/BUFFADDR8', 'BUFFADDR8'), ('/Sheet 1/BUFFADDR9', 'BUFFADDR9'), ('/Sheet 1/BUFFADDR10', 'BUFFADDR10'), ('/Sheet 1/BUFFADDR11', 'BUFFADDR11'), ('/Sheet 1/BUFFADDR12', 'BUFFADDR12'), ('/Sheet 1/BUFFADDR13', 'BUFFADDR13'), ('/Sheet 1/BUFFADDR14', 'BUFFADDR14'), ('/Sheet 1/BUFFADDR15', 'BUFFADDR15'), ('/Sheet 1/BUSDATA0', 'BUSDATA0'), ('/Sheet 1/BUSDATA1', 'BUSDATA1'), ('/Sheet 1/BUSDATA2', 'BUSDATA2'), ('/Sheet 1/BUSDATA3', 'BUSDATA3'), ('/Sheet 1/BUSDATA4', 'BUSDATA4'), ('/Sheet 1/BUSDATA5', 'BUSDATA5'), ('/Sheet 1/BUSDATA6', 'BUSDATA6'), ('/Sheet 1/BUSDATA7', 'BUSDATA7'), ('/Sheet 1/RD', 'RD'), ('/Sheet 1/WR', 'WR'), ('Net-(IC1-~{CE})', 'N$35'), ('Net-(IC2-D0)', 'N$18'), ('Net-(IC2-D1)', 'N$17'), ('Net-(IC2-D2)', 'N$16'), ('Net-(IC2-D3)', 'N$15'), ('Net-(IC2-D4)', 'N$6'), ('Net-(IC2-D5)', 'N$4'), ('Net-(IC2-D6)', 'N$3'), ('Net-(IC2-D7)', 'N$2'), ('Net-(IC4-D0)', 'N$33'), ('Net-(IC4-D1)', 'N$30'), ('Net-(IC4-D2)', 'N$29'), ('Net-(IC4-D3)', 'N$28'), ('Net-(IC4-D4)', 'N$24'), ('Net-(IC4-D5)', 'N$23'), ('Net-(IC4-D6)', 'N$22'), ('Net-(IC4-D7)', 'N$21'), ('Net-(IC6-CLK)', 'N$5'), ('Net-(IC7A-I)', 'N$7'), ('Net-(IC7B-I)', 'N$8'), ('Net-(IC7C-I)', 'N$9'), ('Net-(IC7D-I)', 'N$10'), ('Net-(IC7E-I)', 'N$11'), ('Net-(IC7F-I)', 'N$12'), ('Net-(IC8A-I)', 'N$13'), ('Net-(IC8B-I)', 'N$14'), ('Net-(IC8C-I)', 'N$26'), ('Net-(IC8D-I)', 'N$25'), ('Net-(IC10A-I0)', 'N$34'), ('Net-(IC10A-O)', 'N$58'), ('Net-(IC10B-I0)', 'N$51'), ('Net-(IC10B-O)', 'N$62'), ('Net-(IC10C-I0)', 'N$44'), ('Net-(IC10C-O)', 'N$19'), ('Net-(IC10D-I0)', 'N$37'), ('Net-(IC10D-O)', 'N$57'), ('Net-(IC11-~{CE})', 'N$47'), ('Net-(IC12A-I1)', 'N$20'), ('Net-(IC12B-I0)', 'N$49'), ('Net-(IC13-D0)', 'N$46'), ('Net-(IC13-D1)', 'N$43'), ('Net-(IC13-D2)', 'N$42'), ('Net-(IC13-D3)', 'N$41'), ('Net-(IC13-D4)', 'N$40'), ('Net-(IC13-D5)', 'N$39'), ('Net-(IC13-D6)', 'N$38'), ('Net-(IC13-D7)', 'N$45'), ('Net-(IC14A-I0)', 'N$27'), ('Net-(IC14A-O)', 'N$31'), ('Net-(IC14B-I1)', 'N$50'), ('Net-(IC14D-I0)', 'N$36'), ('Net-(IC15-D0)', 'N$68'), ('Net-(IC15-D1)', 'N$67'), ('Net-(IC15-D2)', 'N$66'), ('Net-(IC15-D3)', 'N$65'), ('Net-(IC15-D4)', 'N$64'), ('Net-(IC15-D5)', 'N$63'), ('Net-(IC15-D6)', 'N$60'), ('Net-(IC15-D7)', 'N$55'), ('Net-(LED1-C)', 'N$1'), ('Net-(LED2-C)', 'N$59'), ('Net-(LED3-C)', 'N$61'), ('Net-(LED4-C)', 'N$32'), ('Net-(LED5-C)', 'N$56')]
```

## Readability

`tools/kicad/sch_overlaps.py` over every sheet: text over text 24, text over a symbol body 4, text crossed by a line 1, items off the drawing frame or on the title block 0. What is left is mostly the Eagle drawing itself (parts placed that close in Eagle) or KiCad drawing pin numbers centred on short pins.

## Residual ERC / DRC

ERC by type: endpoint_off_grid 33, unconnected_wire_endpoint 21.
`isolated_pin_label` = the converter's per-net global labels (cosmetic); `power_pin_not_driven` / unused-unit notes are the same ones KiCad's own Eagle importer leaves. `unconnected_wire_endpoint` / `pin_not_connected` = wire stubs Eagle leaves bare (mostly net wires ending on a bus, which is drawn as graphics here); since 2026-09-23 the converter no longer hangs a label on every such end (that was most of the label clutter), so they show as KiCad warnings.

DRC by type: silk_over_copper 199, silk_overlap 181; unconnected items 0; schematic parity 0.
Silk-over-pad and clearance notes reflect the Eagle design as drawn; unconnected items are Eagle airwires (parts the design left unrouted).

Converter: converted: 89 symbols, 532 wires, 151 labels, 119 junctions, 18 bus lines, 27 no-connects
