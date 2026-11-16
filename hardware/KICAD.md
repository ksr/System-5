# KiCad conversions

Generated 2026-10-05 by `tools/eagle_to_kicad_all.py`: every System-5 Eagle design with a Fusion XML export (`eagle/<rev>/fusion-export/`) converted to a KiCad 10 project in the matching `kicad/<rev>/` folder. The Eagle files remain the record of what was built; these projects are derived and regenerated from scratch by the tool. **Proof** = the schematic netlist extracted by KiCad compared pad-for-pad with the netlist embedded in the imported Eagle board (`tools/kicad/compare_netlists.py`). Each project's README has the details and the residual ERC/DRC counts.

**Overlaps** = `tools/kicad/sch_overlaps.py` over all sheets: text/text + text/body + text/line collisions, and items off the drawing frame.

| Eagle design | KiCad project | Built | Proof | ERC | DRC | Overlaps | Off frame | Status |
|---|---|---|---|---|---|---|---|---|
| `bus/eagle/rev-2009/bus` | [`bus-rev-2009`](bus/kicad/rev-2009/) | no | MATCH (36/36 nets) | 62 | 12 + 0 unconnected | 6 | 0 | ok |
| `cpu/eagle/rev-a/cpu2-a` | [`cpu-rev-a`](cpu/kicad/rev-a/) | yes | MATCH (88/88 nets) | 40 | 229 + 0 unconnected | 28 | 0 | ok |
| `ide-cf/eagle/rev-a/ide1-a` | [`ide-cf-rev-a`](ide-cf/kicad/rev-a/) | yes | MATCH (49/49 nets) | 26 | 126 + 0 unconnected | 58 | 0 | ok |
| `io-1861-keyboard/eagle/rev-a/Video` | [`io-1861-keyboard-rev-a`](io-1861-keyboard/kicad/rev-a/) | yes | MATCH (79/79 nets) | 49 | 236 + 0 unconnected | 11 | 0 | ok |
| `memory/eagle/rev-b/mem3-b` | [`memory-rev-b`](memory/kicad/rev-b/) | yes | MATCH (88/88 nets) | 62 | 373 + 0 unconnected | 21 | 0 | ok |
| `memory/eagle/rev-c/mem3-c` | [`memory-rev-c`](memory/kicad/rev-c/) | no | MATCH (92/92 nets) | 54 | 380 + 0 unconnected | 29 | 0 | ok |

## Redrawn schematics (2026-10-26)

Every card in the machine (and the 2026 boards) also has a readable, block-by-block schematic drawn from its proven board netlist, in `<card>/kicad/<rev>/schematic/`: its own KiCad project and PDF, proven pin for pin against the board netlist. The boards are untouched. Tool and status: `tools/kicad/sch/README.md`.

## New boards

- **Bus backplane Rev D (S5BUS-D)**, 2026-10-26: `bus/kicad/rev-d/`, generated (`gen/`), not converted from Eagle.

## Hand-maintained masters (not generated; `MASTER` marker file)

- [`memory/kicad/rev-e`](memory/kicad/rev-e/) — Rev D as a 4-layer board (MEM3-E): built 2026-10-31, the memory card in the machine; see its README. `memory/kicad/rev-d` = the scrap boards as ordered 2026-10-09
- [`video-6845/kicad/rev-b`](video-6845/kicad/rev-b/) — Ken's working card (2005 Rev B), set to 2 layers, part values (IC8 = 74LS163), labels and JLCPCB order files (2026-10-08)
