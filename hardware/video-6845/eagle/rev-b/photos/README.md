# 6845 Rev B photos

`2026-10-07-*.jpg`: Ken's working, populated 6845 card. It is **Rev B** (found 2026-10-08; see `hardware/FABRICATED.md`).
They match Rev B's 2005 silkscreen gerber (`../fab/v6845-b.plc`):
- IC10 (74LS174) and IC13 (74LS86) lie sideways in the middle row, and IC14 (7416) sits on its own by the RCA jack;
- there are no SV2–SV4 jumper headers;
- IC7 is a 74LS174 and IC8 a 74LS163 (the design says 74HC160 at IC8).

The board has no rework. Its chips came from the Rev A card (`../../rev-a/photos/README.md`: same date codes as the March 2005 website photo).

## Board file against this card (2026-10-08)

The Fusion export of `v6845-b.brd` (`../fusion-export/`) was checked against these photos part by part. It also matches the April 2005 CAM files (`../fab/verify-fab-vs-brd.txt`).
Every footprint is where the photos show a part, with the same package and orientation. The photo is rotated against Eagle: the bus edge (U$1) is at the bottom, and Eagle's +y is to the left.

| Ref | Design | Fitted |
|---|---|---|
| Q1, R2, R3 | crystal, 1K, 1K | as designed (top left) |
| IC6 | 74LS04N | SN74LS04N |
| IC7 | 74LS174N | HD74LS174P |
| IC11 | 74LS166N | SN74LS166N |
| IC8 | 74HC160N | **SN74LS163AN**: the right part; the drawn '160 would divide by 5 (`../../../BYTE-COMPARISON.md`) |
| IC9 | 74LS175N | **SN74AS175N** (pin-compatible, faster) |
| U$4, X1 | RCA jack, DB9 | both fitted |
| IC12 | 2732 | MBM2732A |
| IC14 | 7416N | 7416N |
| RN1, SV1 | resistor network, 2×4 header | fitted; SV1 1-2 (block 7) |
| IC10, IC13 | 74LS174N, 74LS86N | HD74LS174P, HD74LS86P |
| R4, R5, R6 | 1K, 33, 270 | fitted |
| IC4 | 74S85N | **74LS85PC** (slower than the S part, in the -VMA/address decode) |
| IC5, IC3 | 74LS00N, 6845 | SN74LS00N, HD46505RP (HD6845P) |
| IC2, IC1 | 74LS373N, IDT7134 | fitted, IDT7134SA35P |
| **LED1, R1** | LED, 470 | **not fitted** (top right corner, above the RCA jack: empty pads) |
| **C1-C7, C9-C15** | 0.1 µF bypass | **not fitted**: the pad pairs beside each chip are empty on both sides |
| **C8** | 10 µF | **not fitted** (bottom left) |

All chips are socketed.
