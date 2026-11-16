# Fusion export checklist

Eagle 4.13 binary files → Eagle XML, so KiCad can import them.

## How

For each row:
1. In Fusion, open the `.sch` from this repo (File → Open → Open from my computer…).
   Fusion should pick up the `.brd` with the same name in the same folder.
2. Export the schematic as an Eagle `.sch`, and export the board as an Eagle `.brd`.
3. Save both into a `fusion-export/` folder inside that revision, **with the same file names**.
   For example: `hardware/cpu/eagle/rev-a/fusion-export/cpu2-a.sch` and `cpu2-a.brd`.

Leave the original binary files where they are; they remain the record of the 2005 design.
Saving Fusion's own `.fsch` / `.fbrd` files (for example `ide1-a-export.fsch` in the revision folder) works too: they are zips with the Eagle XML inside, and
`python3 tools/extract_fusion.py hardware/<board>/eagle/<rev>/*-export.f*` writes it into `fusion-export/` under the plain names.

If Fusion complains about a file or changes something (missing libraries, renamed parts, a DRC prompt), note it in the last column and carry on.
Then run `hardware/check-exports.sh` to see what's done.

## Files

| # | Folder (`hardware/…`) | Schematic | Board | Ordered? | Note |
|---|---|---|---|---|---|
| 1 | `cpu/eagle/rev-a` | cpu2-a.sch | cpu2-a.brd | **yes** | |
| 2 | `io-1861-keyboard/eagle/rev-a` | Video.sch | Video.brd | **yes** | |
| 3 | `memory/eagle/rev-a` | mem3.sch | mem3.brd | **yes** | |
| 4 | `memory/eagle/rev-b` | mem3-b.sch | mem3-b.brd | **yes** | |
| 5 | `video-6845/eagle/rev-b` | v6845-b.sch | v6845-b.brd | **yes** | the working card; done 2026-10-08 |
| 5a | `video-6845/eagle/rev-a` | v6845-a.sch | v6845-a.brd | **yes** | the first working card; done 2026-10-06 |
| 6 | `ide-cf/eagle/rev-a` | ide1-a.sch | ide1-a.brd | **yes** | |
| 8 | `cpu/eagle/rev-b` | cpu2-b.sch | cpu2-b.brd | no | |
| 9 | `cpu/eagle/rev-c` | cpu2-c.sch | cpu2-c.brd | no | copies of the newest backups |
| 10 | `memory/eagle/rev-c` | mem3-c.sch | mem3-c.brd | no | |
| 11 | `memory/eagle/mem2-16k-6116` | mem2.sch | mem2.brd | no | |
| 12 | `memory/eagle/mem1-24k-6116` | mem1.sch | mem1.brd | no | unrouted |
| 13 | `cpu/eagle/cpu1-prototype` | cpu1.sch | cpu1.brd | no | unrouted |
| 14 | `proto-breadboard/eagle/rev-a` | proto1-a.sch | proto1-a.brd | no | |
| 14b | `bus/eagle/rev-2009` | bus.sch | bus.brd | **yes** | **the only surviving bus board** (6 slots, 36 pins), from Eagle's 2009 backups `bus.s##` / `bus.b##` (`elf-2/ksrcad/Bus/`, copied 2026-10-26) |
| 15 | `bus/eagle/rev-c` | bus.sch | — | no | schematic only |
| 16 | `bus/eagle/rev-b` | bus.sch | — | no | schematic only |
| 17 | `bus/eagle/rev-a` | bus.sch | — | no | schematic only; its file header differs from the rest, so it may be an older format |
| 18 | `circuits/eagle` | IOBOARD.sch, kio.sch | — | no | sub-circuits, optional |

Rows 1–6 matter most. Those are the boards that were made, and their KiCad conversions can be checked against the 2005 production gerbers in `fab/`.

Not needed:
- `memory/eagle/rev-c-mill/mem3-c.brd` is already XML.
- The `website-copy/` duplicates of memory Rev B and 6845 Rev B are optional. Export them only if you want to see how they differ.
