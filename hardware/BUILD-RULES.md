# Build rules for System-5 boards

The rules the System-5 boards follow, gathered in one place from the documents and board files that state them, with
every known exception. Nothing here is new: each rule names its source, and where two files disagree both are listed
at the end. When a rule changes, change its source and this page together.

## Scope

- **Rules for new boards** (section 1) are for future work only. They do not apply to any board already built or
  ordered (MEM3-E and BUSDRV-B, ordered 2026-10-20, are built and in use). When it is not clear whether a board counts as future work,
  ask Ken before applying them. The 6845 Rev B stays the 2005 card; the rules are applied on Rev B-Clean
  (2026-11-20) and on VIDEO-G.
- **Always ask Ken before changing a board that might be built, ordered or in production**, for any change at all.
- The other sections describe how the boards were built: the 2005 rules from Ken's board notes, and the 2026 rules
  for the KiCad boards.

Source: [`CLAUDE.md`](../CLAUDE.md) (standing rules).

## 1. Rules for new boards (2026-10-24, all of Ken's systems)

- Switches, buttons, LEDs and the connectors for outside cables (video, D-subs, USB, network) go on the **front
  edge**, the edge farthest from the bus connector.
- Cable connectors point outwards: a right-angle part with its mating face at the board edge, so a cable plugs
  straight in.
- Jumper blocks and cable headers (ribbons, probes, ICSP) go near a board edge, never in the middle of the board.
- A plug-in module (Nano, Pico, ...) goes at an edge other than the bus connector's, where possible, with its USB
  port facing that edge.
- Every reference (U12, R3, ...) stays readable with the parts fitted: printed outside the part, never under a chip,
  socket or module. ICs get their type printed beside it.
- Every switch, button and LED is labelled with its function, and each switch position with what it selects.
- Placement drawings (PDF) show the outline and the parts in one orientation, on a sheet shaped like the board.

## 2. Every board, every system: bypass caps and the order check

- **Every 0.1 µF bypass cap has 0.1" (2.54 mm) lead spacing**, never 0.2" (5 mm) discs. Memory Rev D's
  `C025-050X050` is the example (Ken, 2026-10-19; [`CLAUDE.md`](../CLAUDE.md)).
- **Before any order, `~/Developer/pcb-check/pcb-check <board.kicad_pcb> <order.zip> --layers N` must show no FAIL,
  and Ken must have seen the result** (Ken, 2026-11-05, for every system). `pcb-check` is Ken's one check for the
  boards of all his systems, in a repository of its own (private). Since 2026-11-06 it is the check before an order,
  in place of this repository's `tools/preorder_check.py` (Ken's first rule, of 2026-10-19). It is for new boards
  only: it is never run on a board already ordered or built.
    - **It runs the older check first**, from its own copy: the layer count ordered, the board's copper layers and
      the zip's copper files agree; ERC; DRC with zones refilled; unconnected pads; schematic parity; that the zip is
      fresh from the board and reads back with every copper layer; the bypass-cap rule; the netlist proof; one-piece
      planes on 4-layer boards with no tracks on them; and a picture of each copper layer.
    - **Then its own checks:** the copper rebuilt from the gerbers and the drill file alone and proved against the
      schematic (the one check of what will really be made); a design review (unpowered parts, floating inputs, two
      drivers on a net, too few bypass caps); the silkscreen (the card's name and rev, `cottageworker.com`, every
      part's reference and value); polarity; footprints against the real parts; the board's fit; the fab's limits;
      the bus connector's pins; a committed tree; and one rev on the silkscreen, the schematic and the zip's name.
    - **FAIL blocks an order; WARN needs Ken's eye.** Then Ken looks at the pictures and the fab's gerber viewer.
      DRC alone is not enough: it checks the board file, not the zip.
    - **When a board is set for order**, `--archive --fab F --order NUMBER` stores what was sent beside the board
      (the zip, the schematic and layout PDFs, the pictures, the report and a parts list), and the order goes into
      [`FABRICATED.md`](FABRICATED.md).
    - **`tools/preorder_check.py` is still in this repository as a build step**, no longer as the check before an
      order: VIDEO-G's `kicad/common/build.sh` ends with it, and it redraws a card's schematic PDF. `pcb-check`
      writes nothing in the repository, so the schematic PDFs are redrawn before it runs.

## 3. The 2005 board notes

From Ken's notes, [`board-notes/BoardNotes.txt`](board-notes/BoardNotes.txt) (and the `.html` copy):

| Rule | |
|---|---|
| Board size | 5.50 × 3.75 in |
| Bus connector | centre at 0.2 × 1.875 in (place on a 0.025 grid, then back to 0.05) |
| Card supports | keep-out polygons 3.00 × 0.15 on Eagle layers 41/42 at the left and right bottom corners |
| LEDs | at X = 5.2 in: Power at Y = 0.3, Aux 1–4 at 1.0, 1.7, 2.4, 3.1; flat side (cathode) toward the bus connector; PWR label at 5.4 × .45 |
| Parts | 5 mm LEDs, 207/7 resistors, `C025-050x050` bypass caps; the tantalum at .45 × 3.45 with + nearer VCC |
| Silk title | `KSR -- XXX#-A` (board name, design variant, revision), text .05 × .05; all writing on layer 25 |
| Power | check that GND and VCC connect at the bus |
| Before fab | ERC, the gerb274x and excellon CAM jobs, the doc script, the order number in `readme.txt` |

The 2005 boards went to Sierra Proto Express (NoTouch) and PCB Fab Express ([`FABRICATED.md`](FABRICATED.md)).

## 4. Bus

| Rule | Source |
|---|---|
| 30 pins, the System-4 bus kept | [`README.md`](../README.md) |
| 1 +5V, 2–9 D0–D7, 10 Q, 11 TPA, 12 TPB, 13 -MRD, 14 -MRW, 15–22 A0–A7, 23 -INT, 24 N2, 25 -EF, 26 -VMA, 27 -RESET, 28 N1, 29 N0, 30 GND; pin 1 at the left on the component side | BoardNotes |
| Bus Rev B (Dec 2005) dropped ±12 V and added N1/N2 | `README.md` |
| **36-pin slots (Ken, 2026-11-18), counted from GND:** position 1 GND, the slot's end pin (the rightmost seen from the power connector), then the 30-pin bus up to +5V at 30 (a 30-pin card's own pin *n*, +5V 1 … GND 30, is position 31 − *n*), then 31 -EF1, 32 -EF2, 33 -EF3, 34 -DMAIN, 35 SC0, 36 -PAUSE; a 30-pin card plugs in flush with the GND end. The socket is an unnumbered strip: the numbers are the drawings'. Until then the 2009 order, counted from the other end (1–3 -EF1 to -EF3, the 30-pin bus in the middle, 4–33, then -PAUSE, -DMAIN, SC0); a 36-pin card for the new order does not fit the 2009 backplane. The definition: `hardware/bus/kicad/rev-d/gen/netlist.py` (`POS`), read by `tools/s5bus.py` | [`docs/manual/bus.md`](../docs/manual/bus.md), "The 36-pin extension" |
| The bus itself is Vero board, never a PCB | `FABRICATED.md`, [`BACKLOG.md`](../BACKLOG.md) |
| New boards copy the outline and connector position (J1, footprint C30) from Memory Rev D, so they fit the System-5 card cage | memory Rev D and bus-driver Rev B READMEs |

## 5. The 2026 KiCad boards

| Rule | Source |
|---|---|
| 2-layer boards (BUSDRV, Memory D): signal tracks 0.25 mm, +5V/GND 0.6 mm, clearance 0.2 mm, GND pour on both sides, JLCPCB 2-layer rules | bus-driver Rev B and memory Rev D READMEs |
| Netclasses: Default 0.25 track / 0.2 clearance / 0.6/0.3 via; Power 0.6 / 0.25 / 0.8/0.4 | bus-driver Rev B `gen/make_board.py`, the `.kicad_pro` files |
| Boards converted from Eagle are checked against OSH Park's rules (6 mil track, 5 mil clearance, 10 mil drill, 4 mil annular ring), a modern-fab check, not the 2005 fab's | the converted READMEs, e.g. CPU Rev A |
| Through-hole only | memory Rev D and bus-driver Rev B READMEs |
| Silk (Memory D/E): every IC `<ref> <part>` plus its function, passives reference and value, strokes at least 0.15 mm, jumper rows and columns labelled | memory Rev D README |
| Parts: Memory D/E muxes 74HCT151, not 74LS151; keep the CD4050B (not a 74HC4050); 6845 IC8 a 74LS163 or 74HCT163 | memory Rev E and 6845 Rev B READMEs |
| JLCPCB orders: 1.6 mm, HASL, white silk | `FABRICATED.md`, memory Rev D README |
| **Every footprint draws its part** (an F.Fab body, a courtyard round it, a 3D model where KiCad has one), so that the label placer, the renders and `pcb-check` see it. The card's bus connector (C30 / C36) is a single-row right-angle pin header: its plastic body lies between the pads and the card edge, 1.5 to 4.0 mm from the pads. **Nothing is printed between the bus pads and the card edge**; the pins' names go on the board side | found the night of 2026-11-18: the footprints drew pads and no body, and all six new cards had `J1 BUS` (memory Rev F its thirty pin names too) under the header; `hardware/video-g/kicad/README.md`, `tools/kicad/silk270.py` (`bus_label`), `tools/kicad/fp_update.py`. Since 2026-11-19 `pcb-check` has a line for it, **BODIES**: a warning for each part with pads and nothing drawn on the fab layer |

## 6. Folders and formats

| Rule | Source |
|---|---|
| `hardware/<board>/eagle/<rev>/` and `kicad/<rev>/`; gerbers and order zips in `eagle/<rev>/fab/`; numbered backups in `eagle-backups/` | `CLAUDE.md`, `README.md` |
| KiCad is the working format; Eagle is reference only | `CLAUDE.md` |
| A converted board that gets changed becomes a hand-maintained master: a `MASTER` file in its `kicad/<rev>/`, never regenerated by the converter | `CLAUDE.md` |
| Fusion exports in `eagle/<rev>/fusion-export/`, same file names, originals left in place | [`FUSION-EXPORT.md`](FUSION-EXPORT.md) |

Seen on every board but not written down as a rule: every KiCad outline measures 140.95 × 96.19 mm, the 2005 imports
included.

## 7. Exceptions

| Board | How it differs | Source |
|---|---|---|
| Memory Rev E | 4 layers: In1 GND plane, In2 VCC plane, no outer pours; tracks 0.25 mm, vias 0.6/0.3, Power clearance 0.2 | memory Rev E README, `.kicad_pro` |
| BUSDRV-A, Memory Rev D | Routed on 4 layers, ordered from 2-layer zips; scrap (the reason for the order check) | `FABRICATED.md`, bus-driver Rev A README |
| MEM3-D | No "KSR --" in the title (Ken) | `CLAUDE.md` |
| 6845 Rev B (as built) | No bypass caps, LED1 or R1 fitted; an LS163, LS85 and AS175 in place of the drawn parts | `BACKLOG.md`, 6845 Rev B README |
| Memory Rev D | IC10 removed; its LEDs driven from the gated !CE | memory Rev D README |
| BUSDRV | No series resistors on the bus; the Nano is not powered from the bus | bus-driver Rev B README |
| 2014 memory Rev C (mill) | Re-routed for milling, 10 mil tracks | memory `eagle/rev-c-mill` README |

## 8. Where the files disagree (to sort out)

1. **Board size:** BoardNotes says 5.50 × 3.75 in (139.7 × 95.25 mm); the boards measure 140.95 × 96.19 mm; the Rev C
   mill README says 140 × 96.
2. **Memory Rev E README:** its header says 4 layers, but further down it still says 2 layers, title MEM3-D and
   memory-rev-d file names.
3. **6845 Rev B README:** 2 layers near the top, 4 copper layers further down.
4. **Bus-driver Rev B README:** 258 segments near the top, 247 further down (copied from Rev A).
5. **74HCT151:** `BACKLOG.md` says still to change; the Rev D and Rev E READMEs say changed 2026-10-08.
6. **Bypass pitch:** `BACKLOG.md` says 2.5 mm; `CLAUDE.md` says 2.54 mm.
7. **Masters:** `KICAD.md` lists memory Rev E and 6845 Rev B; bus-driver Rev B has a `MASTER` file too.
8. **Eagle:** `README.md` says every board was designed in Eagle 4.x; the bus driver was generated in KiCad (2026).
9. **The two BoardNotes copies** differ a little: the `.txt` has "XXXX" LED labels, the `.html` names Aux 1–4.
