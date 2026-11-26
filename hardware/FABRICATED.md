# Fabricated boards

Which System-5 boards were sent to a PCB fab, judged from the files.

Sources of evidence:
- **Production zip:** a gerber zip in `fab/` whose `readme.txt` carries an order number.
  BoardNotes says the order number was written into that readme before upload, so these zips are what was sent.
- **CAM run:** photoplotter/drill info files (`.gpi`/`.dri`) record when gerbers were generated.
- **DESCRIPTION:** the note Ken kept in each revision folder.
- **Website:** "Production Date" columns on the 2005 1802 website (last updated Oct–Nov 2005; a copy is in `docs/website-2005/`).

"NoTouch" is Sierra Proto Express's no-touch order service. `cpu/eagle/rev-a/DESCRIPTION` names Sierra Proto Express for the CPU order.

## How the gerbers are checked

`tools/verify_fab_vs_brd.py <fusion-export .brd> <fab zip>` compares a board with the gerbers that were sent.
- It finds the whole-board offset by itself: Eagle 4's CAM output does not share the board's origin, and each layer has its own few-mil offset.
- It also detects a mirrored solder side: the 2005 `.sol` files are mirrored in X.

## Ordered: order number on file

| Board | Rev | CAM run | Order | Other evidence |
|---|---|---|---|---|
| CPU | A | 2005-01-03 | NoTouch **17545-iNTJ** (`fab/cpu2a.zip`) | DESCRIPTION: "Sent for production Jan 3 2005 to Sierra Proto Express". Website: produced Jan 11 2005. Needed pin lifting, double sockets and rewiring. |
| IO: 1861 video + keyboard | A | 2005-01-04 | NoTouch **17593-iNTJ** (`fab/Video1a.zip`) | DESCRIPTION: "Sent to production Jan 4/05". Website: Jan 12 2005, with a photo. The 1861 circuit was never tested. |
| Memory (mem3) | B | 2005-04-07 | **FXA5474ED07** (`fab/mem3b.zip`). **Verified 2026-10-05:** the Fusion export of `mem3-b.brd` matches the gerbers in this zip: 606/606 holes, 918/918 top and 629/629 bottom tracks (`fab/verify-fab-vs-brd.txt`). | The fab was PCB Fab Express: the board's underside silkscreen reads "PcbFabEx FXA5474" (photo 2026-10-05). It was built and works, with the chip-select rework described in `memory/REVIEW.md`. The Nov 2005 website still says "not yet produced", but its note "(FIX test with new PCB and picture)" suggests the board had arrived and was untested. |

## Ordered 2026 (JLCPCB)

| Board | Rev | Ordered | Files sent | Note |
|---|---|---|---|---|
| Bus driver (BUSDRV-B) | B | 2026-10-20, JLCPCB **2000765A-Y56** | `bus-driver/kicad/rev-b/busdrv-b-gerbers.zip` | **In use: the test card, live and running** (Ken, 2026-11-14). **Received, built and working (2026-10-30):** first bring-up with the reworked Memory Rev B: bus master, all data and address lines, RAM read and write verified (`memory/eagle/rev-b/bringup/README.md`). In use since as the test card: it brought up the IDE card (2026-10-30) and MEM3-E (2026-10-31), and steps and traces the CPU card (`cpu/eagle/rev-a/bringup/README.md`). Firmware banner `blocks-1 io-2 clk-1 2026-10-31`. **2 layers**, 1.6 mm, HASL: Rev A's circuit re-routed as a true 2-layer board, C1/C2 0.1"; passed `tools/preorder_check.py --layers 2` on 2026-10-19. JLCPCB shows it as Y56-2000765A. |
| Bus driver (BUSDRV-A) | A | 2026-10-09, JLCPCB **2000765A-Y53** | `bus-driver/kicad/rev-a/busdrv-a-gerbers.zip` | **SCRAP: the zip held only 2 of the board's 4 copper layers; 234 of 247 track segments are missing from the made boards (found 2026-10-19).** Replaced by Rev B (BUSDRV-B, `bus-driver/kicad/rev-b/`), a true 2-layer re-route, ordered 2026-10-20 (2000765A-Y56). 2 layers, 1.6 mm, HASL. JLCPCB shows it as Y53-2000765A. **Received** (Ken, 2026-11-14: the scrap boards arrived). Zip re-verified against the board that day (every layer and the drill file); DRC 0, schematic parity 0. |
| Memory (MEM3-E) | E | 2026-10-20, JLCPCB **2000765A-Y55** | `memory/kicad/rev-e/memory-rev-e-gerbers.zip` | **In use: the memory card in the machine, live and running** (Ken, 2026-11-14). **4 layers**, 1.6 mm, HASL: Rev D's circuit (identical netlist) re-routed with signals on F.Cu/B.Cu and GND/VCC planes on In1/In2; passed `tools/preorder_check.py --layers 4` on 2026-10-19. JLCPCB shows it as Y55-2000765A. Reviewed before building (`memory/kicad/rev-e/REVIEW-2026-10-30.md`, `REVIEW-2026-10-31-independent.md`): no blockers. **Received, built and brought up on 2026-10-31 (Ken); the memory card in the machine since.** From the bus driver, RAM 0000-6FFF and EPROM 8000-EFFF both pass (`memory/kicad/rev-e/bringup/README.md`): one bad 74HCT151 (IC2) was replaced, and IC5 is a Toshiba TC57256D programmed on the T48 with the ELF/OS install ROM. Fitted for the System-5 map only: IC1 and IC5 with 74HCT151 muxes (IC2, IC13); IC3, IC11, IC4, IC15, RN2 and RN3 are not fitted. The whole system ran with it on 2026-11-01: HBIOS boots and takes keys (`cpu/eagle/rev-a/bringup/README.md`, "Whole system"). |
| Memory (MEM3-D) | D | 2026-10-09, JLCPCB **2000765A-Y54** | `memory/kicad/rev-d/memory-rev-d-gerbers.zip` | **SCRAP: the zip held only 2 of the board's 4 copper layers; 1,116 of 1,227 track segments are missing from the made boards (found 2026-10-19).** Replaced by Rev E (MEM3-E, `memory/kicad/rev-e/`): the same circuit as a proper 4-layer board (GND/VCC planes), ordered 2026-10-20 (2000765A-Y55). 2 layers, 1.6 mm, HASL. JLCPCB shows it as Y54-2000765A. **Received** (Ken, 2026-11-14: the scrap boards arrived). Zip re-verified against the board that day (every layer and the drill file); DRC 0, schematic parity 0. Build with 74HCT151 muxes. |

Ordered in one JLCPCB order with YACC1-D's memory card v2.0 (2000765A-Y52). The 6845 Rev B order files are ready but on hold (`BACKLOG.md`).

## Ordered: no order number, but strong evidence

| Board | Rev | CAM run | Evidence |
|---|---|---|---|
| Memory (mem3) | A | none in tree | Website: produced Dec 16 2004, "the first new card built for System-5", with a photo. DESCRIPTION: "Initial Design sent to production". |
| 6845 video | A | 2005-02-09 | DESCRIPTION: "Sent to Production Feb 9/05 Bare card only". Website: produced Feb 15 2005. **Built and worked:** the Mar 2005 website photo (`docs/website-2005/images/P3070210.JPG`) is this card, and Ken still has it (photos 2026-10-09, sockets empty). It carries the double-socketed EPROM (A11 fix), a hand-wired DE-9 and what looks like a lower-case trial on IC10/IC13 (`video-6845/eagle/rev-a/photos/README.md`). Its chips later went to the Rev B card. A second, unpopulated Rev A board also survives (photos 2026-10-08). |
| IDE / CF | A | 2005-02-01 | DESCRIPTION: "Production Version". Website: produced Feb 11 2005, with a photo carrying a CF-to-IDE adapter and a 16 MB CF card. |
| Bus (backplane) | 2009 | 2009-02-04 (Eagle backup) | **Built** (Ken, 2026-10-26: "there was a PCB", without a regulator). The 2009 board: six 36-pin slots, every pin bussed, 8 mounting holes, X1 a 2-pin power connector: on the copper its pin 2 touches the GND track (Eagle never logged it) and its pin 1 reaches nothing; the +5V tracks dangle short of it (DRC of the conversion). Photos of bare boards: `bus/eagle/rev-2009/photos/`. Source: Eagle's backups `bus.b##` / `bus.s##` (`bus/eagle/rev-2009/`); KiCad `bus/kicad/rev-2009` (MATCH 36/36). No order record or gerbers survive. Open: confirm with a meter (X1.2 = GND, X1.1 open) and how +5V reached the slots (a wire to X1.1?). |
| 6845 video | B | 2005-04-05 | **Built: Ken's working card is Rev B** (found 2026-10-08). The 2026-10-07 photos match Rev B's silkscreen gerber (`v6845-b.plc`), not Rev A's: IC10 and IC13 lying sideways with IC14 on its own by the RCA jack, no SV2-SV4, a 16-pin 74LS174 at IC7 (Rev A: 14-pin 74LS90). Photos moved to `video-6845/eagle/rev-b/photos/` (2026-10-08). Fitted differently from the design: IC8 is an SN74LS163AN (the design says 74HC160N). The Nov 2005 website's "No PCB YET" was out of date. **Verified 2026-10-08:** the Fusion export of the newest `v6845-b.brd` matches the surviving April 2005 CAM files: 669/669 bottom tracks, all 556 pads and vias, and the drill tally by size (`fab/verify-fab-vs-brd.txt`; the top copper `.cmp` was not kept). Its chips came from the Rev A card (same date codes; photos 2026-10-09). As fitted (photos): IC9 74AS175, IC4 74LS85, and no bypass capacitors, C8, LED1 or R1 (`video-6845/eagle/rev-b/photos/README.md`). |

## Gerbers generated, probably not ordered

| Board | Rev | CAM run | Evidence |
|---|---|---|---|
| Bus | B | 2005-10-22 | A PCB backplane: 6 slots of 36 pins (the 30-pin System-5 bus with -EF1-3 above and -INP, -OUT, -IOM below), a 7805-style regulator, power connector, LED, 6 mounting holes, 6.30 x 3.94 in. Known from its CAM files: the silkscreen (`bus/eagle/rev-b/fab/bus.plc`, drawn as `bus-rev-b-silkscreen.png`) and the drill report (218 x 0.040", 6 x 0.126", 11 x 0.032"); its `.brd` is lost. **Not the board Ken built** (Ken, 2026-10-26: the built bus PCB has no regulator; it is the 2009 board). |

## Design only

| Board | Rev | Why |
|---|---|---|
| Bus (backplane) | D (S5BUS-D) | Designed 2026-10-26 in KiCad (`bus/kicad/rev-d/`): 8 slots of 36 pins, pull-ups; reviewed and fixed 2026-10-26 (hole keep-outs, 2.5 mm supply feeds, card-window brackets); independent reviews 2026-10-27: 5 A power switch, 4 A polyfuse, P-MOSFET reverse protection, 6.3 mm C1, 1.0 mm silkscreen; idle-state resistor networks 2026-11-01 (RN3 pulls N0-N2, TPA and TPB down, RN4 pulls -VMA, -MRD and -MRW up); power redone 2026-11-18 (a barrel jack for a 7-15 V adapter, a Schottky, the switch and a 5 V 3 A switching regulator in place of the screw terminal, polyfuse and MOSFET; then an external regulated 5 V on two screw terminals, J10, and a source jumper, JP1, with the switch after it); passes the older check, `tools/preorder_check.py --layers 2`; it has to pass `pcb-check` before an order. Not ordered. |
| Memory (MEM3-F) | F | Designed 2026-11-18 (`memory/kicad/rev-f/`): MEM3-E (Rev E) with its silkscreen fixed: every text upright with the card standing in the bus (270), every chip's label beside it instead of under it, J1 and SV1-SV4 named, the name with Rev F and `cottageworker.com`; the copper Rev E's, unchanged. Passes the older check, `tools/preorder_check.py --layers 4`; it has to pass `pcb-check` before an order. Not ordered. |
| CPU | D | Designed 2026-10-30 in KiCad (`cpu/kicad/rev-d/`, `DESIGN.md`): the 36-pin CPU card, 2 MHz or an external clock, 2732 boot EPROM at F000, LOADED flag; passes the older check, `tools/preorder_check.py --layers 2`; it has to pass `pcb-check` before an order. Not ordered. |
| IO panel | A | Designed 2026-10-30 in KiCad (`io-panel/kicad/rev-a/`, `DESIGN.md`): 8 toggles, 8 LEDs, two TIL311s, Q LED, INPUT on -EF1, ELF-style RUN/LOAD on the 36-pin bus; passes the older check, `tools/preorder_check.py --layers 2`; it has to pass `pcb-check` before an order. Not ordered. |
| Front panel | A | Designed 2026-11-22 in KiCad (`front-panel/kicad/rev-a/`, `DESIGN.md`): a board that mounts as the front of a case, on a 50-way ribbon from the IO panel card: six TIL311s, bit and status LEDs, data toggles, RUN, LOAD, INPUT and a RESET button; passes the older check, `tools/preorder_check.py --layers 2`; it has to pass `pcb-check` before an order. Not ordered. |
| 6845 video | B-Clean | Designed 2026-11-20 in KiCad (`video-6845/kicad/rev-b-clean/`; Ken: "a clean version of current video card, no need for db9, composite only. Add bypass caps and proper silkscreen ... minimal to no changes to circuit"): Rev B's circuit and copper without the DE-9 and with the 6845's light-pen input tied to ground (Ken: "Yes tie light pen to gnd"), every part drawn, the silkscreen redone to the layout rules; passes the older check, `tools/preorder_check.py --layers 2`; `pcb-check`: no failures. **Not to be ordered** (Ken, 2026-11-20: only the version with the keyboard): it is the base Rev B-Clean-Keyboard is made from. |
| 6845 video | B-Clean-Keyboard | Designed 2026-11-20 in KiCad (`video-6845/kicad/rev-b-clean-keyboard/`; Ken: "add keyboard support to Rev B Clean, Call it Rev-b-clean-keyboard. Look at video-g for keyboard section only. Expand bus to the 36 pin bus and add jumpers required to access keyboard"): Rev B-Clean with VIDEO-G TEXT's PS/2 keyboard section, memory-mapped as VIDEO-G's (the key at 7802, the status at 7804; the 6845 at 7800 / 7801 only), a KBD FLAG jumper block, the 36-pin bus connector; the RCA jack moved to the front edge beside the PS/2 jack (Ken); 190.5 x 106.565 mm, 2 layers, Rev B's copper kept. It runs the VIDEO-G HBIOS in both emulators. The two open-collector jobs on a second 7416 (Ken: "swap", for the two 2N7000s first drawn). **`pcb-check --tests` at `808364d`: no failures, 1 warning** (Rev B's 0.25 mm supply tracks, accepted by Ken). **Its 6845 is write-only since 2026-11-24** (Ken: "Write-only": R/W on ground, E = NOT -MRW, which ends the bus fight of TIMING-REVIEW's T2; the board routed again, `pcb-check --tests` at `db65312`: no failures, the same 1 warning). Not ordered: Ken's look at the result and the pictures comes first. |
| CPU | cpu1 prototype | DESCRIPTION: "First cut with 1861 - unrouted". |
| CPU | B | Website: "NO PCB YET … UNBUILT/UNTESTED". |
| CPU | C | Eagle backups only. |
| Memory | mem1 | DESCRIPTION: "unrouted". |
| Memory | mem2 | Routed 6116 board; nothing shows it was ordered. |
| Memory (mem3) | C | Design only (2005). |
| Memory (mem3) | C mill | 2014 XML re-save set up for PCB milling. It may have been milled at home; nothing in the tree confirms it. |
| IO | B | Todo list only. |
| IDE | B | DESCRIPTION only. |
| Breadboard proto | A | Website: "No PCB has been produced yet". |
| Front panel | — | Website: "No version of this card exists yet". |
