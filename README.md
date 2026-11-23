# System-5 — a PCB-based 1802 ELF

System-5 is a printed-circuit-board 1802 computer built in 2004–2005 to run
Mike Riley's **ELF/OS**. It replaced the wire-wrapped System-4 (1979–1982) one
card at a time while keeping the System-4 30-pin bus, so old wire-wrap cards and
new PCB cards could be mixed. All the 2005 boards were designed in **Eagle 4.x**;
the boards of 2026 are **KiCad** designs.

Original write-up: the 2005 1802 website, no longer online; a copy is in `docs/website-2005/`.

The project's website is <https://system5.cottageworker.com>. This repository is public as
<https://github.com/ksr/System-5>, a copy made from Ken's working repository (`tools/public/README.md`).

## The system

| Card | Folder | Summary |
|---|---|---|
| Bus | `hardware/bus` | The 30-pin bus kept from System-4: Rev A 1982, Rev B Dec 2005 (dropped ±12V, added N1/N2); pinout in `hardware/board-notes/BoardNotes.txt`. **In the machine: the 2009 PCB backplane**, six 36-pin slots, no regulator, no pull-ups (System-4's backplane was Vero board). **Rev D** (S5BUS-D, 2026, `kicad/rev-d/`): eight 36-pin slots, power switch, fuse, pull-ups and pull-downs. Designed, not ordered. |
| CPU | `hardware/cpu` | CDP1802, clock, CM1232 power-on reset/auto-run, mode control (run/load/wait/reset), 4K EPROM, VMA reset-address remap, EF jumpers, aux connectors for the front panel and 1861 card. **In the machine: Rev A** (Jan 2005, reworked). Rev B/C are unbuilt fixes; `eagle/cpu1-prototype` = first unrouted cut with the 1861 on board. **Rev D** (2026, `kicad/rev-d/`): a new CPU card for the 36-pin bus, 2 MHz or an external clock, RESET/RUN switch, a flag that lets a loaded program run from RAM after a reset, with a RAM LED to show it (2026-11-21). Designed, not ordered. |
| Memory | `hardware/memory` | 2× 62256 RAM + 2× 27256 EPROM, every 4K block jumper-enabled. **In the machine: Rev E** (MEM3-E, `kicad/rev-e/`; JLCPCB, 4 layers, built 2026-10-31): the 2005 Rev C circuit with three fixes. Before it: Rev A (2004, the first card built) → B (2005; reworked, in the machine until 2026) → C, and a 2014 `rev-c-mill` variant for PCB milling. Rev D (2026) is scrap. `mem1`/`mem2` are earlier 6116-based designs. |
| IO: 1861 video + keyboard | `hardware/io-1861-keyboard` | CDP1861 video, CDP1852 input port, I/O decode (from Mike Riley's ELF). PS/2 keyboard → **PAK-VI** (AWC Electronics PS/2-to-ASCII) → **PIC16F84** (serial→parallel, `pic-ps2-firmware/keyboard.c`) → 1852. **In the machine: Rev A** (Jan 2005), for the keyboard; the 1861 has never been tested. |
| 6845 video | `hardware/video-6845` | 6845 alphanumeric video card based on **BYTE, May 1979**. Composite + Electrohome drive outputs. Rev A Feb 2005 (the first working card, later stripped; `eagle/rev-a/`). **In the machine: Rev B** (lower case, simplified clocking, Apr 2005): the 2005 Eagle source in `eagle/rev-b/` and the KiCad order master in `kicad/rev-b/`. **Rev B-Clean** (2026, `kicad/rev-b-clean/`): Rev B's circuit and copper without the DE-9 (composite only) and with the 6845's light-pen input tied to ground, every part drawn and the silkscreen redone. Designed, not ordered. **Rev B-Clean-Keyboard** (2026, `kicad/rev-b-clean-keyboard/`): Rev B-Clean with a PS/2 keyboard on the card (VIDEO-G TEXT's keyboard section: the key at 7802, the status at 7804), the 36-pin bus connector, and the video and keyboard jacks together at the front edge; it runs the VIDEO-G HBIOS. Designed, not ordered. |
| CF disk (IDE) | `hardware/ide-cf` | Mike Riley's 8-bit IDE interface plus port-select jumpers; used with a CF-to-IDE adapter and a 16MB CF card. **In the machine: Rev A** (Feb 2005). |
| Breadboard proto | `hardware/proto-breadboard` | Solderless-breadboard prototyping card. Drawn in 2005, never made. |
| Bus driver | `hardware/bus-driver` | New, 2026: Arduino Nano and 2× MCP23017 on the bus, a test card after the YACC1 bus tester. It runs bus cycles in place of the CPU, or steps and traces the CPU. **Rev B** (BUSDRV-B, `kicad/rev-b/`; JLCPCB, 2 layers) is built and working since 2026-10-30. Rev A is scrap: routed on 4 layers, ordered from a 2-layer zip. **Rev C** (BUSDRV-C, `kicad/rev-c/`, drawn 2026-11-18, not ordered): all 36 bus positions with a third MCP23017, LOAD mode by the clock, CLK OUT and probes on the Nano, a DEBUG header cabled to CPU Rev D's. The firmware has a **short finder** for either card since 2026-11-21: one bus line driven alone, every other watched (`python3 bringup.py shorts`, `software/busdrv/BRINGUP.md`); tried in the simulator only. |
| IO panel | `hardware/io-panel` | New, 2026: the front panel as a card on the 36-pin bus. 8 toggles, 8 LEDs, six TIL311 hex displays (the data byte and the bus address), Q LED, INPUT button, ELF-style RUN/LOAD, a real-time clock and, since 2026-11-20, a serial port (16C550, DE-9). Since 2026-11-22 a 50-pin header at its front edge for the front panel's ribbon (the card is 8.00 in long), and its DMA request put right: as first drawn it would have loaded every byte twice. Since 2026-11-23 its own RESET button, which boots the EPROM (the RUN/RESET toggle restarts what ran before), and the serial port's settings on the silkscreen. Rev A (`kicad/rev-a/`) designed, not ordered. No front panel was designed in 2005: the System-4 wire-wrap panel was used via the CPU card header. |
| Front panel | `hardware/front-panel` | New, 2026-11-22: a board that mounts as the front of a case, on a 50-way ribbon from the IO panel card. Six TIL311s (the bus address and the data byte), bit and status LEDs (PWR, Q, PAUSE, RESET, ROM, START FROM RAM), eight data toggles, RUN and LOAD, INPUT, and a RESET button that boots the EPROM. Nothing goes to the CPU card: a boot reset is a state of the bus (`docs/manual/bus.md`). Rev A (`kicad/rev-a/`) designed, not ordered. |
| VIDEO-G | `hardware/video-g` | New, 2026: the next video card, two boards joined by a 40-pin ribbon. **TEXT**: 6845 text, 64 × 25 or 64 × 32, with a PS/2 keyboard. **GFX**: graphics, 512 × 200 or 512 × 256, with a PS/2 mouse. All memory-mapped in its own block, no I/O ports (2026-11-17). Version 1.0 (`kicad/`) designed, not ordered. |

The machine today (2026-11-14) is the 2009 backplane with CPU Rev A, memory Rev E, 6845 Rev B, IO Rev A and IDE Rev A. The five new boards (bus Rev D, CPU Rev D, the IO panel and the two VIDEO-G boards) pass the older check, `tools/preorder_check.py`, and none is ordered. Before an order each has to pass `pcb-check`, Ken's check for the boards of all his systems since 2026-11-06 (`hardware/BUILD-RULES.md`, section 2): all five have, as they are now: the bus Rev D on 2026-11-18, the other four on 2026-11-19, after their labels were moved out from under the bus connector (and VIDEO-G TEXT got the 36-pin connector); the IO panel again on 2026-11-20, with its serial port; CPU Rev D again on 2026-11-21, with its RAM LED. On 2026-11-22 CPU Rev D and the IO panel were changed and a sixth board, the front panel, was drawn (a boot reset on the bus; the IO panel's header and its DMA request): all three pass `pcb-check --tests` (last on 2026-11-23, at `26e17ea`: CPU Rev D and the front panel with no failures and no warnings, the IO panel with no failures and one warning, which Ken accepted that day: its DE-9 begins 65.6 mm from the front edge, where the check allows 60). They were drawn on the branch `front-panel` and are in `main` since 2026-11-23 (Ken: "merge everything"). None is ordered. `STATUS.md` has every board's state.

Board conventions (size 5.50" × 3.75", LED positions, labelling `KSR -- XXX#-A`,
CAM jobs) are in `hardware/board-notes/`.

Each board has an `eagle/<rev>/` tree (production gerbers in `fab/`) and, once converted, a `kicad/<rev>/` tree. Which boards were ordered: `hardware/FABRICATED.md`. Open work: `BACKLOG.md`. A summary of where everything stands (2026-11-14): `STATUS.md`.

Where both the Eagle working folder and the published website had a file with
the same name but different content, the website version is kept in a
`website-copy/` subfolder. Eagle's numbered backups (`*.b#1`, `*.s##`, …) are in
`eagle-backups/` subfolders.

## Firmware (Ken's)

- `firmware/hbios/` — **HBIOS**: 6845 video and keyboard drivers layered on Mike
  Riley's ELF/OS BIOS (changes marked `#define KSR`); boots into the BIOS's
  monitor, `minimon`, which is Mike's. `v1.0.6` is current, in the machine since 2026-11-15 (v1.0.4 plus the commands
  Ken added to that monitor, `H`, `B`, `D` and `Q1` / `Q0`, and the disk calls
  always in LBA mode, which Elf/OS v5 needs; built by its `build.py`); `v1.0.5`, `v1.0.4`, `v0.9` and `old/` are
  earlier builds. `v1.0.7` (2026-11-17, burned that day, not yet in the machine) adds `@F1E0`: the code of each key pressed, as `0x31`, on the
  bottom line of the screen, until Reset. `v1.0.8` (2026-11-18, emulator only) adds a driver for the IO panel's real-time
  clock (a DS12885 on ports 6/7) behind `f_gettod` / `f_settod`, and `f_getdev` bit 4. v1.0.4 builds with `rcasm` + `srec_cat` into a ROM
  at `0xF000`. `video-g/` is a build for the VIDEO-G card (everything
  memory-mapped: the 6845 at 7800/7801, the key at 7802; 64 x 25, a faster scroll; for the emulator, not burned).
  Mike Riley's BIOS comes under his notice (`firmware/hbios/NOTICE.md`: free to use and share with the notice kept,
  not for commercial use without his permission).
- `firmware/rom-tests/` — test ROM (`sec2`).
- `firmware/char-rom-fonts/` — 2513 character-generator ROM images and C tools
  to build/view font EPROMs for the 6845 card.

## Software (Ken's host tools)

- `software/s5emu/` — System-5 emulator and debugger (terminal + browser; in a browser tab on a Mac or in a GitHub Codespace: `software/s5emu/CODESPACE.md`, `.devcontainer/`): runs the real HBIOS ROM and boots ELF/OS from a disk image; 1861, IDE/CF, 6845, keyboard, memory jumpers, bus-driver link; `--video g` models the VIDEO-G card.

- `software/gbasic/` — **GBASIC**, an integer BASIC for ELF/OS with VIDEO-G graphics (1802 assembly, 2026-11-01): the source, the built program, its language reference (`README.md`) and tests in the emulator.

- `tools/asm1802.py` — a Python 1802 assembler (rcasm syntax, short-branch page check, relaxing jumps, macros); builds GBASIC and the VIDEO-G HBIOS.

- `software/busdrv/` — `s5busdrv.py`, the host tool for the bus driver card (peek/poke/dump, hex load with verify, memtest, I/O, bus watch); firmware in `embedded/bus-driver/`.

- `software/elfos-v5/` — System-5 programs for Mike Riley's Elf/OS v5 (`cls`) and `v5card.py`, which reads and
  changes a v5 card image (`ls`, `get`, `put`, `add`).

## Kept private (third-party)

Other people's work that System-5 is built with, and that carries no permission to publish it, is not in this
repository. Since 2026-11-15 it is in Ken's private repository `private-resources` (`github.com/ksr/private-resources`),
which sits beside this one, so the paths below are written `../private-resources/elf/...`; each keeps the path it had
here.

- `reference/mike-riley/` — **ELF/OS** (kernel 135, utilities and languages,
  0.2.6 release; Elf/OS v5 and its System-5 card image), **rcasm** 2007 source, **EDTASM**, MicroElf/PicoElf boards
  and a mirror of elf-emulation.com.
- `reference/elf2000-spare-time-gizmos/` — **ELF2000** (Spare Time Gizmos /
  Bob Armstrong): manuals, EELF, ELF-Disk, STG1861, ROM v60/v87 images (with
  Ken's EPROM-split Makefiles), ElfOS-2K 0.2.8. Not part of System-5.
- `reference/tiny-basic/` — Lee Hart/TMSI 1802 Tiny BASIC; RCA Tiny BASIC (Herb Johnson).
- `reference/tools/` — A18 assembler, TASM 3.1, 1806 disassembler, srecord
  source tarballs (1.20/1.23/1.27), Macro Assembler AS manual, LCD font tool.
- `reference/datasheets/` — CDP1802 datasheet, RCA MPM-201A 1802 User Manual (1976), EPROM databook.
- `firmware/elfos-install-rom/` — the ELF/OS install image for the memory card's EPROM, and the read of the one in
  MEM3-E's IC5 (`hardware/memory/eagle/rev-b/bringup/*.bin`).
- `firmware/system4-tiny-basic-rom/` — the Tiny BASIC EPROM pulled from the System-4 wire-wrap machine, and its
  disassembly.
- `software/disktool/` — Mike Riley's 2005 disktool, which builds and writes ELF/OS disks (with `kernel.bin`).
- `software/rcasm-mac-build/` — rcasm source patched in 2017 to build on macOS (with a Mac x86_64 binary).

Without them the emulator still runs HBIOS (whose BIOS part Mike Riley allows to be shared, above), but has no ELF/OS
disk to boot, and the tests that need one are skipped.

## Licence

Ken's designs and documents are CC BY 4.0, his software MIT; HBIOS's BIOS part, the 2513 fonts and some library parts
are other people's: [`LICENSE.md`](LICENSE.md).

## Docs

- `docs/website-2005/` — "Ken's 1802 World" site (System-1, System-4, System-5,
  stand-alone projects, photos). Files that are also elsewhere in this repo
  (schematics, BIOS source, tool tarballs) were removed here (the list is
  `docs/.removed-dups.txt`, kept with Ken's working notes).
- `docs/website-older/` — earlier versions of the same site.

The visitor counter the Yahoo host added to 33 of the old pages was taken out on 2026-11-15; nothing else in them was
changed.

## Other projects

1802 work that is not System-5 (the Netronics ELF II recreation, the 2020 COSMAC ELF PCB, the ELF2000/PicoElf
ROMs, the ET-3400 EPROM reads and general 1802 documentation) is in a separate private repository since 2026-10-26,
split out of this one with its history.

## Provenance

Assembled 2026-10-04 from `~/Documents/Projects/elf-1`, `elf-2` and `1802`
(all left untouched). `elf-1` was largely a subset of `elf-2`; exact duplicates were
collapsed to one copy. Not carried over: FrontPage `_vti_*` metadata, vim swap
files, `.o` objects, extracted srecord build trees (source tarballs kept), and
2005-era Linux i386 binaries that have source alongside. Duplicate include
files inside individual ELF/OS program folders were left in place because each
program's build expects them.
