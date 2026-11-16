# Memory Rev D (MEM3-D): KiCad master

> **AS ORDERED 2026-10-09 (JLCPCB 2000765A-Y54): SCRAP. Kept as the record of what was made; do not order from it.**
> This board has four copper layers: Freerouting put 1,116 of its 1,227 track segments on In1/In2, but the zip held only the top and bottom copper and was ordered as 2 layers, so the made boards have little more than GND, VCC and a few signals. `tools/check_order_zip.py` fails this zip. Found 2026-10-19.
> **The replacement is Rev E (MEM3-E), `../rev-e/`:** the same circuit and routing, ordered as a 4-layer board.

> **Building it (2026-10-08):** the board can be ordered as it is; both open points are part choices, not layout changes.
> - **Fit 74HCT151 for all four muxes (IC2, IC4, IC13, IC15), not 74LS151.** Each CD4042B output (IC9 Q0-Q2 = A12-A14) drives the select inputs of all four muxes. Four LS inputs sink up to 1.6 mA, and a CD4042B is rated for about 0.5 mA at a valid low, so the address lines may not reach a TTL low. The 74HCT151 is pin-compatible and its inputs draw about 1 µA.
> - **Keep the CD4050B buffers.** A faster 74HC4050 makes the start-of-cycle contention (finding C1 in `hardware/TIMING-REVIEW.md`) slightly worse, 241 ns against 228 ns: it turns -MRD (the chips' output enable) on sooner, while the CD4042B still settles the chip enable late. C1 is noise only (reads are not corrupted); removing it needs a faster address latch, which is a layout change for a later revision.
> The schematic, board silkscreen and parts list say 74HCT151 (changed 2026-10-08; copper unchanged).

A System-5 64K RAM/EPROM card. It is Rev C plus three fixes from `../../REVIEW.md`, routed from scratch for JLCPCB, with every chip named on the silkscreen.
**This KiCad project is the master.** Edit it in KiCad. The Eagle files are reference only.

## What changed from Rev C

| Change | Why |
|---|---|
| EPROM VPP (IC3, IC5 pin 1) goes to +5V instead of GND | The AT27C256R wants VPP at 5 V in read mode. |
| IC10 (74LS00 LED driver) and its bypass cap C3 are removed | Each LED now runs +5V → LED → 470 Ω → its chip's gated `!CE`. It lights only while that chip is enabled, and at full brightness because the 74LS32 sinks the current. One chip fewer. |
| C2 moved 1.27 mm right, in line with the other bypass caps | In Rev C its body overlapped IC6's socket. |
| C5 moved 2.54 mm down | Its outline covered the HI block's F000 address label. |
| RN1–RN4 valued 4.7k | Pull-ups; the value was not recorded in the Eagle files. |
| Values written out | 0.1uF, 10uF, 74HCT151, 74LS32, CD4042, CD4050, LED 5mm, headers. Eagle had ".1", "10.0" and blank. The board and schematic values match (DRC schematic parity 0). |
| The chip-select nets are named | RAM_LO_CE (IC1), RAM_HI_CE (IC11), EPROM_LO_CE (IC3), EPROM_HI_CE (IC5). |

The chip-select fix from Rev C is kept: each `!CE` = 74HCT151 `Y` OR bank-select. The circuit is otherwise Rev C, net for net.
`gen/make_schematic.py` applied the edits. They were checked against the Rev C netlist: nothing changed except the items above.

## Schematic

`gen/clean_schematic.py` tidied the converted drawing (2026-10-05). The netlist is identical before and after.
- The hidden power pins are on the 1.27 mm grid, inside each symbol body.
- 28 duplicate wire pieces are removed (short wires lying inside longer ones).
- 14 wires that ran from a labelled data line on to Eagle's graphic bus lines are removed, along with 3 bus lines left touching nothing.
- The LED section is redrawn as four rows (VCC → LED → 470 → chip-select label) in the empty strip at the bottom of the sheet.
- The title block names Rev D.

ERC left: 6 warnings. Each is a wire carrying its label (RD, WR, BUFFADDR10, BUFFADDR11, BUSDATA4) that runs on to a graphic bus line. The label makes the connection, so the warnings are cosmetic.

## Board

- **Size:** 140.95 × 96.19 mm, 2 layers. Same outline, bus connector position and part placement as Rev C, so it fits the System-5 card cage.
- **Routing:** from scratch with Freerouting; 1227 track segments and 5 vias (Rev C had 165).
  - Signals: 0.25 mm tracks, 0.2 mm clearance.
  - VCC/GND: 0.6 mm.
  - GND pour on both sides.
- **Silkscreen:** every IC is labelled `<ref> <part>` with its function, e.g. "IC13 74HCT151 / EPROM HI 4K SEL", inside its outline. Open-frame sockets leave the label visible. The board title is `MEM3-D`.
  - Jumper blocks: each row is labelled ROM / GND / RAM, and each column carries its 4K start address (0000–7000 under LO 32K, 8000–F000 under HI 32K).
  - The header and LED references and the header pin numbers are hidden, so they don't cover those labels.
  - Resistors, capacitors and resistor networks show reference and value, e.g. "C16 0.1uF", "R2 470", "RN1 4.7k".
  - All silk text has at least a 0.15 mm stroke.
- **Checks, 2026-10-05:**
  - Netlist proof: schematic vs board MATCH, 88/88 nets.
  - DRC against JLCPCB 2-layer rules: 0 errors, 0 unconnected, schematic parity 0.
  - What remains are silkscreen warnings from the 2005 Eagle footprints: outlines crossing pads (JLCPCB clips silk off copper) and touching header outlines.

## Files

| File | What it is |
|---|---|
| `memory-rev-d.kicad_pro/.kicad_sch/.kicad_pcb` | The project. Rules: JLCPCB 2-layer. Net classes: Default and Power. |
| `memory-rev-d-eagle.kicad_sym`, `memory-rev-d-eagle.pretty/` | Project symbol and footprint libraries, carried over from the Eagle conversion. |
| `memory-rev-d-gerbers.zip` (and `gerbers/`) | **Upload this to JLCPCB.** Copper, mask, silk and outline gerbers plus the Excellon drill file. |
| `memory-rev-d-bom.csv` | Parts list. |
| `memory-rev-d-schematic.pdf`, `-placement.pdf`, `-render-top.png`, `-render-bottom.png` | Prints and pictures. |
| `reports/` | Netlist, DRC, ERC. |
| `gen/` | The one-off scripts that made this from Rev C: `make_schematic.py`, `clean_schematic.py`, `make_board.py`, `fix_silk.py` (silk thickness, hidden header/LED references, value labels, label positions). Kept as the record. |

## Ordering at JLCPCB

Upload `memory-rev-d-gerbers.zip`. Settings:

| Setting | Value |
|---|---|
| Layers | 2 |
| Thickness | 1.6 mm |
| Size | about 141 × 96 mm (detected from the zip) |
| Surface finish | HASL is fine (all parts are through-hole) |
| Silkscreen | white |

Over 100 × 100 mm costs more than JLCPCB's cheapest tier, but stays inexpensive for 5 boards.

**Parts, all through-hole:**
- 2× 62256 (32K × 8 SRAM), 2× 27256/27C256 EPROM
- 4× 74HCT151 (not 74LS151: see the top), 2× 74LS32, 2× CD4042, 2× CD4050 (keep the CD4050: see the top)
- 14× 0.1 µF, 1× 10 µF, 5× 5 mm LED, 5× 470 Ω
- 4× 4.7k 10-pin SIL resistor networks (bussed, common pin 1)
- Pin headers: 2× 2×8, 2× 1×8, plus a 30-pin right-angle bus connector

**Jumpers:** each column is one 4K block, labelled with its start address. A jumper from GND (middle row) up to ROM or down to RAM enables that block in the EPROM or the RAM. Leave a column open to leave that 4K empty.
