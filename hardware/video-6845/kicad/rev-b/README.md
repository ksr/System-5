# 6845 video card Rev B: KiCad master (order files 2026-10-08)

> **Hand-maintained since 2026-10-08** (`MASTER`). This is the board of **Ken's working 6845 card** (`hardware/FABRICATED.md`).
> - **Proven:** converted from the newest 2005 Eagle files (Fusion export in `eagle/rev-b/fusion-export/`), netlist MATCH 99/99.
>   The Eagle board matches the surviving April 2005 CAM files (`eagle/rev-b/fab/verify-fab-vs-brd.txt`).
>   The order files below carry exactly the Eagle board's copper: all 596 top and 669 bottom tracks and all 556 holes (positions and sizes) were matched one to one on 2026-10-08.
> - **Changed for the order** (`gen/make_master.py`): 2 copper layers (KiCad's Eagle import made it 4, with empty inner layers); real part values in the schematic and board; silkscreen labels with each chip's part number and job and each passive's value. Copper and placement are untouched.
> - **Order files** (`gen/make_orders.sh`): `video-6845-rev-b-gerbers.zip` (gerbers + Excellon drill), `video-6845-rev-b-render-top.png`, `video-6845-rev-b-placement.pdf`, `video-6845-rev-b-bom.csv`.
>
> **Ordering at JLCPCB:** upload `video-6845-rev-b-gerbers.zip`. 2 layers, about 141 × 96 mm, 1.6 mm FR-4, 1 oz, HASL, no assembly: the same settings as memory Rev D and the bus driver.
>
> **Building it:**
> - **IC8 must be a 74LS163** (or a 74HCT163), not the 74HC160 the 2005 schematic drew. The '160 clears asynchronously and would divide the dot clock by 5; the '163 divides by 6, as BYTE does and as Ken's working card has (`../../BYTE-COMPARISON.md`). The value here is already 74LS163, and the silkscreen says "(163!)".
> - **Character EPROM (IC12, 2732):** A11 and A10 are tied low, and A9 is character bit 6. The font is 128 characters × 8 rows at **000h-3FFh**: address = 7-bit ASCII × 8 + row. Burn **`firmware/char-rom-fonts/goodfont`** (1K) at 000h. It is `makerom.c`'s output from `2513_combined`, byte for byte, and was checked against this wiring on 2026-10-08: ASCII order with lower case at 60h-7Fh, dots in data bits 7-3 (the 74166 takes O3-O7, and O7 is the leftmost dot), row 0 blank. HBIOS 1.0.4 defines `VIDEOLOWER` ("REV B and beyond"), so it writes 7-bit ASCII unchanged. Do **not** burn `2513_combined` itself: it is in 2513 order with the dots in bits 4-0.
> - **Crystal (Q1):** the BOM says 9 MHz, because HBIOS loads BYTE's 16 × 64 CRTC values, which assume 9 MHz and ÷6. The crystal on Ken's card is not legible in the photos.
> - **Jumper:** SV1 1-2 puts the card at 7000 (block 7), where HBIOS expects it. Rev B has no other jumpers.
> - **Video out:** composite on the RCA jack. The DB9 (X1) carries the 7416's video (pin 7) and the 6845's own HSYNC (pin 8) and VSYNC (pin 9), active high, for a monitor that takes separate drive. Fit either or both.
> - **Fit the bypass capacitors** (C1-C7, C9-C15, 0.1 µF; C8, 10 µF). Ken's 2005 card has none, and it works, but they are cheap insurance.
> - Ken's card has a 74LS85 at IC4 (the design says 74S85) and a 74AS175 at IC9. Either part works in each place; the BOM says 74LS85.
> - DRC: silkscreen warnings only, 0 unconnected. The schematic-parity notes are net names (`/Sheet 1/X` against `X`) and pins left unconnected on purpose; the connectivity is proven by the netlist comparison.
> - Timing findings T2-T5 (`hardware/TIMING-REVIEW.md`) were worked out on Rev A; the bus side is the same on Rev B.

## The original conversion notes

Generated 2026-10-08 by `tools/eagle_to_kicad_all.py` from the Fusion XML export of the Eagle design `v6845-b` in `hardware/video-6845/eagle/rev-b/fusion-export/`. **The Eagle files are the record of what was designed and built; this KiCad project is derived from them and is regenerated from scratch on every run of the tool** (hand edits here will be lost - once a card is edited in KiCad, remove it from the tool's list). This revision was FABRICATED (see `hardware/FABRICATED.md`).

## Files

| File | What it is |
|---|---|
| `video-6845-rev-b.kicad_pro` | project; DRC uses OSH Park rules (6 mil track, 5 mil clearance, 10 mil drill, 4 mil annular) as a modern-fab check, not the 2005 fab's rules |
| `video-6845-rev-b.kicad_sch` | root sheet; 1 sub-sheet(s) `video-6845-rev-b-sheetN.kicad_sch` mirror the Eagle sheets |
| `video-6845-rev-b-eagle.kicad_sym` | project symbol library generated from the Eagle libraries used (units = Eagle gates) |
| `video-6845-rev-b.kicad_pcb` | the board: 4 copper layers, 42 footprints, 1265 track segments, 168 vias; 2 items on unmapped Eagle layers dropped |
| `video-6845-rev-b-eagle.pretty/` | project footprint library extracted from the imported board |
| `reports/` | ERC (`erc.json`), DRC (`drc.json`), schematic PDF, board renders (`-top.png`, `-bottom.png`), netlist + `netlist-compare.txt` |

## Proof

Schematic-vs-board netlist comparison (`tools/kicad/compare_netlists.py`: every (reference, pad) partition must be identical): **MATCH (99/99 nets)**

```
  same connectivity, different net name: [('/Sheet 1/-MRW', '-MRW'), ('/Sheet 1/-RESET', '-RESET'), ('/Sheet 1/ADDR0', 'ADDR0'), ('/Sheet 1/ADDR1', 'ADDR1'), ('/Sheet 1/ADDR2', 'ADDR2'), ('/Sheet 1/ADDR3', 'ADDR3'), ('/Sheet 1/ADDR4', 'ADDR4'), ('/Sheet 1/ADDR5', 'ADDR5'), ('/Sheet 1/ADDR6', 'ADDR6'), ('/Sheet 1/ADDR7', 'ADDR7'), ('/Sheet 1/ADDR8', 'ADDR8'), ('/Sheet 1/ADDR9', 'ADDR9'), ('/Sheet 1/ADDR10', 'ADDR10'), ('/Sheet 1/ADDR11', 'ADDR11'), ('/Sheet 1/ADDR12', 'ADDR12'), ('/Sheet 1/ADDR13', 'ADDR13'), ('/Sheet 1/ADDR14', 'ADDR14'), ('/Sheet 1/ADDR15', 'ADDR15'), ('/Sheet 1/CHARCLOCK', 'CHARCLOCK'), ('/Sheet 1/CPUDATA0', 'CPUDATA0'), ('/Sheet 1/CPUDATA1', 'CPUDATA1'), ('/Sheet 1/CPUDATA2', 'CPUDATA2'), ('/Sheet 1/CPUDATA3', 'CPUDATA3'), ('/Sheet 1/CPUDATA4', 'CPUDATA4'), ('/Sheet 1/CPUDATA5', 'CPUDATA5'), ('/Sheet 1/CPUDATA6', 'CPUDATA6'), ('/Sheet 1/CPUDATA7', 'CPUDATA7'), ('/Sheet 1/CRTCCLOCK', 'CRTCCLOCK'), ('/Sheet 1/DOTCLOCK', 'DOTCLOCK'), ('/Sheet 1/TPB', 'TPB'), ('/Sheet 1/VADDR0', 'VADDR0'), ('/Sheet 1/VADDR1', 'VADDR1'), ('/Sheet 1/VADDR2', 'VADDR2'), ('/Sheet 1/VADDR3', 'VADDR3'), ('/Sheet 1/VADDR4', 'VADDR4'), ('/Sheet 1/VADDR5', 'VADDR5'), ('/Sheet 1/VADDR6', 'VADDR6'), ('/Sheet 1/VADDR7', 'VADDR7'), ('/Sheet 1/VADDR8', 'VADDR8'), ('/Sheet 1/VADDR9', 'VADDR9'), ('/Sheet 1/VADDR10', 'VADDR10'), ('/Sheet 1/VADDR11', 'VADDR11'), ('/Sheet 1/VDATA0', 'VDATA0'), ('/Sheet 1/VDATA1', 'VDATA1'), ('/Sheet 1/VDATA2', 'VDATA2'), ('/Sheet 1/VDATA3', 'VDATA3'), ('/Sheet 1/VDATA4', 'VDATA4'), ('/Sheet 1/VDATA5', 'VDATA5'), ('/Sheet 1/VDATA6', 'VDATA6'), ('/Sheet 1/VDATA7', 'VDATA7'), ('/Sheet 1/VROWS0', 'VROWS0'), ('/Sheet 1/VROWS1', 'VROWS1'), ('/Sheet 1/VROWS2', 'VROWS2'), ('Net-(IC1-~{CER})', 'N$9'), ('Net-(IC1-~{OER})', 'N$1'), ('Net-(IC2-ENC)', 'TPA'), ('Net-(IC3-CS)', 'N$3'), ('Net-(IC3-DE)', 'N$38'), ('Net-(IC4-A0)', 'N$4'), ('Net-(IC4-A1)', 'N$5'), ('Net-(IC4-A2)', 'N$6'), ('Net-(IC4-A3)', 'N$7'), ('Net-(IC4-A=B_I)', 'N$8'), ('Net-(IC4-A=B_O)', 'N$46'), ('Net-(IC5B-I1)', 'N$2'), ('Net-(IC5C-I0)', 'N$20'), ('Net-(IC5D-I1)', 'N$40'), ('Net-(IC6A-I)', 'N$12'), ('Net-(IC6A-O)', 'N$14'), ('Net-(IC6B-O)', 'N$11'), ('Net-(IC6F-I)', 'N$47'), ('Net-(IC9-D2)', 'N$23'), ('Net-(IC9-D4)', 'N$37'), ('Net-(IC10-CLR)', 'N$10'), ('Net-(IC10-Q1)', 'N$29'), ('Net-(IC10-Q2)', 'N$30'), ('Net-(IC10-Q3)', 'N$31'), ('Net-(IC10-Q4)', 'N$32'), ('Net-(IC10-Q5)', 'N$33'), ('Net-(IC10-Q6)', 'N$34'), ('Net-(IC11-D)', 'N$24'), ('Net-(IC11-E)', 'N$25'), ('Net-(IC11-F)', 'N$26'), ('Net-(IC11-G)', 'N$27'), ('Net-(IC11-H)', 'N$28'), ('Net-(IC11-QH)', 'N$36'), ('Net-(IC12-A9)', 'N$13'), ('Net-(IC13A-I0)', 'N$17'), ('Net-(IC13A-O)', 'N$21'), ('Net-(IC13B-I0)', 'N$35'), ('Net-(IC13B-O)', 'N$39'), ('Net-(IC14A-I)', 'N$43'), ('Net-(IC14A-O)', 'N$45'), ('Net-(IC14B-I)', 'N$41'), ('Net-(IC14B-O)', 'N$44'), ('Net-(IC14C-I)', 'N$42'), ('Net-(LED1-C)', 'N$22')]
```

## Readability

`tools/kicad/sch_overlaps.py` over every sheet: text over text 0, text over a symbol body 5, text crossed by a line 0, items off the drawing frame or on the title block 0. What is left is mostly the Eagle drawing itself (parts placed that close in Eagle) or KiCad drawing pin numbers centred on short pins.

## Residual ERC / DRC

ERC by type: endpoint_off_grid 32, unconnected_wire_endpoint 57.
`isolated_pin_label` = the converter's per-net global labels (cosmetic); `power_pin_not_driven` / unused-unit notes are the same ones KiCad's own Eagle importer leaves. `unconnected_wire_endpoint` / `pin_not_connected` = wire stubs Eagle leaves bare (mostly net wires ending on a bus, which is drawn as graphics here); since 2026-09-23 the converter no longer hangs a label on every such end (that was most of the label clutter), so they show as KiCad warnings.

DRC by type: lib_footprint_mismatch 1, silk_edge_clearance 3, silk_over_copper 199, silk_overlap 42; unconnected items 0; schematic parity 0.
Silk-over-pad and clearance notes reflect the Eagle design as drawn; unconnected items are Eagle airwires (parts the design left unrouted).

Converter: converted: 86 symbols, 462 wires, 123 labels, 88 junctions, 14 bus lines, 39 no-connects
