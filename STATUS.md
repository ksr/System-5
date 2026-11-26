# System-5: where things stand

A summary written on **2026-11-14** (the machine's software brought up to date on 2026-11-15, VIDEO-G and the decisions below on 2026-11-17, the IO panel's clock and the new slot order on 2026-11-18, the cards' bus header on 2026-11-19, the two new 6845 cards on 2026-11-20, the IO panel's serial port on 2026-11-20, the CPU card's RAM LED and the bus driver's short finder on 2026-11-21, the front panel and the boot reset on 2026-11-22, the IO card's RESET button on 2026-11-23) from the repository's own records: `hardware/FABRICATED.md`, `BACKLOG.md`, the
bring-up reports, the design notes and the `elfos-v5` branch. It is a snapshot. Where it and those records differ,
the records are right.

## In short

- **The machine works.** Five cards on the 2009 backplane boot HBIOS, take keys from a PS/2 keyboard and boot
  ELF/OS 0.2.6 from a CompactFlash card (2026-11-01 and 2026-11-04), and since 2026-11-15 Mike Riley's Elf/OS v5.1.1.
  The clock is 500 kHz as the machine stands today.
- **Two boards made in 2026 are in use:** the memory card MEM3-E and the bus driver card BUSDRV-B, both live and
  running (Ken, 2026-11-14). Two earlier 2026 boards were scrap.
- **Five new boards are designed and pass the older pre-order check, and none is ordered:** the bus backplane Rev D, CPU
  Rev D, the IO panel, and the two VIDEO-G boards. `pcb-check`, the check before an order since 2026-11-06, passes the
  two VIDEO-G boards (2026-11-17, reworked to be memory-mapped; no failures), CPU Rev D (2026-11-17, after its
  silkscreen and +5V fixes; no failures), the bus Rev D, and the IO panel (2026-11-18, with its real-time clock: no
  failures). All five were checked again on 2026-11-18 with their tests. **That evening the 36-pin slot changed**
  (Ken): the 30-pin bus flush with the slot's GND end, the six extra lines beyond +5V, the slot counted from GND
  (`docs/manual/bus.md`). The bus Rev D, CPU Rev D, the IO panel and the bus driver Rev C were redone for it (the bus
  with a wider last gap, another power switch and 2 mm more height), and **all four passed `pcb-check` again at elf
  `31c54a8`**: the bus Rev D and CPU Rev D with no failures and no warnings, the IO panel and the bus driver Rev C with
  no failures and the two warnings each had before. Three of the four decisions that held the orders were settled on
  2026-11-17 (section 2).
- **Found the night of 2026-11-18, on every new card: silkscreen text under the bus connector.** A card's bus connector
  is a right-angle pin header whose plastic body lies between the pads and the card edge. Its footprint drew the pads
  and no body, so the label placer put text in that strip and `pcb-check` could not see it: `J1 BUS` on all six cards
  (VIDEO-G TEXT and GFX, CPU Rev D, the IO panel, the bus driver Rev C, memory Rev F), and on memory Rev F all thirty
  bus pin names. The footprints now draw the header (with its 3D model, so the renders
  show it) and the labels stand clear of it. Silkscreen only: on every card the copper is the same, track for track.
  **All six passed `pcb-check` again on 2026-11-19 as they are now** (section 3): VIDEO-G TEXT and GFX, CPU Rev D and
  memory Rev F with no failures and no warnings, the IO panel and the bus driver Rev C with no failures and the
  warnings they had before. The bus Rev D, the backplane, is not affected.
- **The software on the machine is HBIOS 1.0.6 and Elf/OS 5.1.1** (2026-11-15). HBIOS 1.0.6 is 1.0.5 with the disk
  calls always in LBA mode, which v5 needs on a real card (`firmware/hbios/v1.0.6/README.md`). The 16 MB card holds
  v5.1.1 with Mike Riley's base tools, MINIMON and Rc/Basic Level 2; every command tried works (Ken). ELF/OS 0.2.6's
  card image is kept on the Mac (`~/s5-cf.img`).

## 1. Production boards: the machine today

| Card | Revision | Made | State |
|---|---|---|---|
| Backplane | the 2009 PCB | 2009 | In use. Six 36-pin slots, every pin bussed, no regulator, no pull-ups on the data lines |
| CPU | Rev A, reworked | Jan 2005 | In use. CDP1802, 4K boot EPROM (2732) with HBIOS 1.0.6 since 2026-11-15 (the 1.0.5 and 1.0.4 chips are spares). A clock-select jumper was added 2026-11-01: crystal, or a stepped clock from the bus driver |
| Memory | **Rev E (MEM3-E)** | JLCPCB, Oct 2026, 4 layers | In use since 2026-10-31. RAM 0000-6FFF, EPROM 8000-EFFF (since 2026-11-15 Mike Riley's Elf/OS v5 installer with the System-5 kernel patch, whose `@8000` wipes the card at once; the ELF/OS 0.2.6 install ROM is kept), 7000 left for the video card and F000 for the CPU's EPROM. RAM and EPROM both passed the bus driver's tests |
| 6845 video | Rev B | Apr 2005 | In use. 64 x 16 text, video RAM at 7000, CRTC at 7800, composite out |
| IO (1861 + keyboard) | Rev A | Jan 2005 | In use for the keyboard: PS/2 through a PAK-VI and a PIC16F84 into a CDP1852 on port 1. The 1861 has never been tested |
| IDE / CF | Rev A | Feb 2005 | In use. Ports 2 and 3, a 16 MB CF card in an IDE adapter |
| Bus driver | **Rev B (BUSDRV-B)** | JLCPCB, Oct 2026, 2 layers | Test equipment, working since 2026-10-30. An Arduino Nano and two MCP23017s run bus cycles in place of the CPU, or step and trace the CPU. Its sketch has a short finder since 2026-11-21 (one bus line driven alone: `software/busdrv/BRINGUP.md`, "shorts"), simulated only and not yet loaded on the card |

Earlier boards, no longer in the machine: Memory Rev B (reworked; replaced by MEM3-E), 6845 Rev A (stripped for
Rev B's chips). Scrap: BUSDRV-A and MEM3-D, made on 2026-10-09 from zips holding 2 of their 4 copper layers.

Known faults on the cards in use (none stops the machine):

- **CPU Rev A resets only at power-on.** The reset button and bus -RESET do nothing (bench, 2026-10-31).
- **CPU Rev A, timing finding T1:** the high-address latch clocks on TPA's rising edge with no guaranteed setup.
  It works on a typical 1802, but it is a race. The fix is to clock it from inverted TPA.
- **6845 Rev B has no bypass capacitors fitted**, and its CRTC writes end with a brief bus fight (T2, seen on the
  hardware, harmless).
- **The backplane's power connector** reaches GND only on the copper; how +5V gets in is not recorded.
- **Still not on record:** the crystal's marking, R13's value on the CPU card, and which wire is which in the two
  CPU reworks (`BACKLOG.md`, questions 1, 2, 4 and 5).

## 2. Boards in development

All of these are KiCad designs generated from a netlist script, with a schematic in the book
(`docs/manual/pdf/system5-schematics.pdf`). "Check passed" means `tools/preorder_check.py`. Since 2026-11-06 the
check before any order is `~/Developer/pcb-check/pcb-check`, so each board must pass that before it goes to JLCPCB.

| Board | What it is | State | Open before an order |
|---|---|---|---|
| Bus backplane **Rev D (S5BUS-D)** | 8 slots of 36 pins; power (2026-11-18) from a 7-15 V adapter on a centre-positive barrel jack, a Schottky against a reversed plug and a TRACO TSR 3-2450N regulator (5 V 3 A), or from an external regulated 5 V on two screw terminals (J10), picked by one jumper (JP1: REG or EXT), then the power switch; no fuse; pull-ups and pull-downs so every line idles off | **Changed again on 2026-11-18** (Ken): the 30-pin bus flush with each slot's GND end and the slot counted from GND (GND 1 … +5V 30, then -EF1, -EF2, -EF3, -DMAIN, SC0, -PAUSE 36); 1.25 in between slots 7 and 8; RN2 clear of slot 1; 244.35 × 116 mm; `pcb-check` passed at `31c54a8` (no failures, 0 warnings). **Then the power switch an M9040P**, the upright toggle of the IO panel's data switches (Ken; first a 9070-1W that day): **`pcb-check` passed again** at `4b24853` (no failures, 0 warnings), and at `e5322e4` with the switch's body drawn full size on the fab layer (Ken, 2026-11-19; a drawing only: no failures, 0 warnings); 2 layers. Not ordered | SW1's contact rating against the bus current (up to 3 A: the standard 9040-series toggles are listed at about 4 A DC, the low-level ones at 0.4 VA; check the part fitted) and its ON direction; where the card supports go (a 30-pin card now sits 7.6 mm towards the GND end of a 36-pin card); the cards' total current (U1 gives 3 A); socket height against the card guides; Ken's look at the pictures |
| **CPU Rev D** | The 36-pin CPU card: 2 MHz from a 4 MHz oscillator or an external clock, DS1813 reset, RESET/RUN switch, LOADED flag with its RAM LED, 2732 at F000 | **Routed again on 2026-11-18** for the new slot order (its J1 counted from GND: GND 1, +5V 30, -EF1..-EF3 31-33, -DMAIN 34, SC0 35, -PAUSE 36); `pcb-check` passed at `31c54a8` (no failures, 0 warnings); **then three moves at Ken's word** (JP1 between the oscillator and the DEBUG header, the EF blocks 1.5 in nearer the bus, SW1 the YACC1 toggle, a Marquardt 9070-1W): **`pcb-check` passed again** at `26337ba` (no failures, 0 warnings). **Then `J1 BUS` moved out from under the bus header** (silkscreen only, `ec13f1e`): **`pcb-check` passed again** at `59d911e` (2026-11-19: no failures, 0 warnings). **A sixth LED, RAM, on 2026-11-21** (Ken: lit while the LOADED flag is set, that is while a reset starts the 1802 in RAM and not in HBIOS; with R8 on the flip-flop's spare output; the board built again, `8bcae5d`; its label START / FROM / RAM on three lines under the LED, Ken the same day, silkscreen only, `735f80f`): **`pcb-check` passed again** at `735f80f` (no failures, 0 warnings); **A boot reset on the bus, 2026-11-22** (Ken, for the front panel: "all can come from io"): -RESET and -DMAIN low with -PAUSE high clears LOADED, whoever makes it; the card's own switch and power-on make it through a 74HC03 (U11) and a second DS1813 (U12) in place of the diode and the 1 uF; the 1802's DMA input is armed only in pause, once -DMAIN has been high (U8B); the board built again on seed 1 (51 parts, 1143 segments, 40 vias), **`pcb-check --tests` at `9c0e767`: no failures, 0 warnings** (drawn on the branch `front-panel`, in `main` since 2026-11-23). 2 layers. Not ordered. Runs HBIOS and ELF/OS in the emulator | The card-guide fit of a 4.00 inch card; it needs the bus Rev D's 36-pin slots, and no longer fits the 2009 backplane |
| **IO panel Rev A** | The front panel as a card: 8 toggles, 8 LEDs, two TIL311 hex displays, Q LED, INPUT button, ELF-style RUN/LOAD; IN and OUT ports and INPUT's EF line on jumpers; a DS12885 real-time clock with a CR2032 (2026-11-18); the bus address on four more TIL311s, latched at TPA and TPB (2026-11-18); 5.75 x 4.00 in since that evening, each display's label under it, the front panel labelled by function; **a serial port (Ken, 2026-11-20): a 16C550 UART on the clock's port pair, a MAX232 and a DE-9 socket on the side edge, the card 7.50 x 4.00 in for it**; **a header for the front panel (Ken, 2026-11-22): J3, a keyed 2x25 at the front edge, the card 8.00 x 4.00 in for it, pull-downs on the data lines; and its DMA request put right** (as first drawn it lasted past the 1802's sample at clock 7: every byte would have loaded twice; now -DMAIN = NAND(REQ, SC0), U9 a 74HC03); **its own RESET button (Ken, 2026-11-23), a boot reset for a machine with no front panel, and the serial port's settings spelled out on the silkscreen** | **Routed again on 2026-11-18** for the new slot order (J1 counted from GND, as CPU Rev D's); `pcb-check` passed at `31c54a8` (no failures, 2 warnings); **then JP5**, a jumper from the clock's RCLR to GND, Ken's ruling on the first of those warnings (a shunt clears the clock's RAM with the power off): **`pcb-check` passed again** at `e0dcd53` (no failures; 1 warning left, the DS12885 not in pcb-check's footprint table). **Then `J1 BUS` moved out from under the bus header** (silkscreen only, the same route, `a8ca67a`): **`pcb-check` passed again** at `a330195` (2026-11-19: no failures, the same 1 warning). **Then a `+` on the silkscreen at the battery holder's positive end** (Ken, 2026-11-19; `593e18c`, silkscreen only, the same route): **`pcb-check` passed again** at `bb0b711`, and at `e5322e4` with the toggles' bodies drawn full size on the fab layer (Ken, 2026-11-19; a drawing only), each time with no failures and the same 1 warning. **Then the serial port** (2026-11-20; drawn on a test branch and merged; routed again, 2,609 segments and 118 vias): **`pcb-check --tests` passed** at `eebc2ed` with no failures and no warnings; 2 layers. Not ordered: Ken means to order it. Runs in the emulator (HBIOS v1.0.8 reads its clock; a test program echoes its serial line) **Built again on 2026-11-22** with J3, RN3 and the DMA fix (seed 2: 3107 segments, 135 vias; the older check passes); **`pcb-check --tests` at `9c0e767`: no failures, 1 warning**, a new one for Ken: J2, the DE-9, which he put on the side edge, is 65.6 mm from the front edge by the check's measure (the near side of its courtyard; 52.9 mm before) now that the card is longer, over the check's 60 mm reach (drawn on the branch `front-panel`, in `main` since 2026-11-23). **Built again on 2026-11-23** with the RESET button (SW12, a second 74HC03, U23) and the serial legend (seed 3: 3253 segments, 164 vias; the older check passes); `pcb-check --tests` at `bf641d1`: no failures, 1 warning (the DE-9 on the side edge, accepted by Ken on 2026-11-23). | It stays two layers while it routes on two (Ken, 2026-11-18), which takes a seed search at each change; M9040P toggles' availability and lever direction (the footprint is the YACC1 IO card's, pad for pad); the Keystone 103 holder and the DS12885+ in stock; Ken's look at the pictures |
| **Front panel Rev A** | New, 2026-11-22 (Ken: a front panel "if system is ever put in a case"): a board that mounts as the front of a case, 7.50 x 3.50 in, on one 50-way ribbon from the IO panel card's J3. Six TIL311s (address and data), eight bit LEDs, six status LEDs (PWR, Q, PAUSE, RESET, ROM, START FROM RAM), eight data toggles, RUN, LOAD, INPUT, and a RESET button that boots the EPROM by a boot reset on the bus | Drawn and routed on 2026-11-22 (62 parts, seed 0: 1047 segments, 31 vias); the older check passes; from its netlist in the emulator with CPU Rev D and the IO panel (`tests/test_front_panel.py`, 11 tests); **`pcb-check --tests` at `9c0e767`: no failures, 0 warnings** (drawn on the branch `front-panel`, in `main` since 2026-11-23). 2 layers. Not ordered | Ken's look at the board (the ribbon header's solder joints and the logic row are on the front); how it is held in a case; the TIL311s are new-old stock only |
| **VIDEO-G 1.0 TEXT** | 6845 text, 64 x 25 (NTSC) or 64 x 32 (IBM 5151), PS/2 keyboard on an ATmega, RCA and DE-9; everything memory-mapped (2026-11-17). Works alone. Since 2026-11-18 its keyboard flag goes to any of the four bus flag lines (JP3 KBD FLAG: -EF1, -EF2, -EF3 or -EF), so it has the **36-pin bus connector** and is 188 x 106.6 mm | `pcb-check` passed on 2026-11-17 as a 30-pin card. **Changed on 2026-11-18** (Ken): the 36-pin connector and the flag block, SV1's label, the LED by `PWR` alone; routed again; and its labels moved out from under the bus header (`77257f1`). **`pcb-check` passed** at `77257f1`, at `688e6ed` (its four KBD FLAG names moved off the jumper block's outline), at `b4692e9` (the RCA jack's body drawn, for pcb-check's new BODIES line) and at `b2252b7` (the DE-9's whole body drawn), each time with no failures and 0 warnings (2026-11-19; the 36 bus pins on J1); 4 layers. **Its 6845 write-only since 2026-11-24** (Ken's choice, 2026-11-24; seven pins moved, no part added; routed again, seed 0) and `C22 100n` moved clear of IC22; **`pcb-check --tests` passed at `38fc4d0`** (QA, 2026-11-25: no failures, 0 warnings; `qa.py full` OK). Not ordered | It needs the bus Rev D now, like the other 36-pin cards (it does not fit the 2009 backplane); Ken's look at the renders, the pictures and the fab's viewer (188 mm tall: Ken keeps it) |
| **VIDEO-G 1.0 GFX** | Graphics, 512 x 200 or 512 x 256 in two pages, PS/2 mouse. Joins TEXT by a 40-pin ribbon. A 30-pin card still | `pcb-check` passed on 2026-11-17 (with its own PWR LED). **Changed on 2026-11-18** (Ken), silkscreen only: the note about the modes is off the board, the LED by `PWR` alone; `J1 BUS` moved out from under the bus header and the bus pins named as the backplane names them (`77257f1`). **`pcb-check` passed** at `77257f1` (2026-11-19: no failures, 0 warnings); 4 layers. Not ordered | Ken's look at the renders, the pictures and the fab's viewer |
| Memory **Rev F (MEM3-F)** | MEM3-E with **EEPROM sockets** and its silkscreen fixed (2026-11-18): each EPROM socket takes a 27C256 or a 28C256 that the 1802 can rewrite (JP1 / JP2, R6 / R7 47k); every text upright with the card standing (270), every chip's label beside it, not under it; J1, SV1-SV4 and the name with Rev F and cottageworker.com on the silk; Rev E's copper but for the sockets' A14 (1,078 of its 1,084 tracks and vias kept, 75 segments and 1 via added); 4 layers | `pcb-check` passed on 2026-11-18 (the EEPROM version at elf `644a51a`), **but with its thirty bus pin names under the bus header**, which nothing could see then. **Put right that night** (silkscreen only, `a330195`): the names on the board side of the pads, as Rev E has them. **`pcb-check` passed again** at `d1df002` and, with every part's body drawn on the fab layer, at `b4692e9` and `b2252b7`, and at `bb0b711` with its `RAM HI` label 0.5 mm further from R3 (2026-11-19, with its tests: no failures, 0 warnings each time); 4 layers. Not ordered (Ken: not today) | Ken's look at the pictures; the software to rewrite the EEPROM (`BACKLOG.md`) |
| 6845 Rev B, order master | A re-make of the 2005 card | Order files ready. **On hold** (Ken, 2026-10-09) | Whether to make it at all, now that VIDEO-G exists |
| 6845 **Rev B-Clean** | Rev B cleaned up (Ken, 2026-11-20): its circuit and copper without the DE-9 (composite only), the 6845's light-pen input tied to ground, every part drawn, the silkscreen redone | Drawn 2026-11-20; `pcb-check`: no failures. **Not to be ordered** (Ken, the same day: only the version with the keyboard) | None: it is the base the keyboard card is made from |
| 6845 **Rev B-Clean-Keyboard** | Rev B-Clean with a PS/2 keyboard on the card (Ken, 2026-11-20): VIDEO-G TEXT's keyboard section, the key at 7802 and the status at 7804 as on VIDEO-G, a KBD FLAG jumper, the 36-pin connector, the video and keyboard jacks together at the front edge; 190.5 x 106.6 mm, 2 layers, Rev B's copper kept | Drawn 2026-11-20; **its 6845 made write-only on 2026-11-24** (Ken; it ends T2's bus fight, and any grade of 6845 will do at 2 MHz); the VIDEO-G HBIOS and Elf/OS 5.1.1 run on it in both emulators; `pcb-check --tests` at `db65312` (2026-11-24): no failures, 1 warning (Rev B's 0.25 mm supply tracks, which Ken accepted). On the order list (row 12) | Ken's look at the pictures and the fab's viewer; nothing of it has run on hardware (`BACKLOG.md`) |

The four decisions that held the orders (`BACKLOG.md`, "Questions for Ken"), three of them settled by Ken on 2026-11-17:

1. **Port 4 was wanted twice**, by the IO panel and by VIDEO-G's control register. Settled: VIDEO-G is memory-mapped
   (everything in its own block at 7000-7FFF, no I/O ports), so port 4 is the IO panel's.
2. **The keyboard flag.** VIDEO-G signals on bus -EF, which reaches EF3 through CPU Rev A's jumper; CPU Rev D sends
   -EF to EF4, and HBIOS reads EF3. Settled for VIDEO-G: its HBIOS polls KEY-READY in the status register (7804), so
   it works with either CPU card. And the IO card's keyboard works with CPU Rev D too: its EF3 jumper block (JP4)
   on -EF puts the IO card's flag on EF3 (2026-11-17).
3. **TEXT's height**, 188 mm. Settled: it stays (Ken).
4. **The ELF/OS boot loader writes port 4**, which left the port version of VIDEO-G showing graphics noise after
   `@FF00`. Settled with 1: VIDEO-G answers no port.

Ken orders from JLCPCB and groups boards into one order to share the shipping.

## 3. Software in production

On the machine:

| Where | What | Version |
|---|---|---|
| CPU card, 2732 | **HBIOS**: Ken's 6845 and keyboard drivers on Mike Riley's BIOS and monitor, with the monitor commands Ken added (`H`, `B`, `D`, `Q1` / `Q0`) | 1.0.6, burned 2026-11-15 (the 1.0.5 and 1.0.4 chips are spares) |
| CF card, 16 MB | **Elf/OS v5**, Mike Riley's later operating system, with his base tools, MINIMON and Rc/Basic Level 2 | 5.1.1, kernel build 229, since 2026-11-15. The card image of ELF/OS 0.2.6 (kernel build 135, built on the Mac with `mkelfos.py`, 2026-11-04) is kept on the Mac (`~/s5-cf.img`) |
| MEM3-E, IC5 | Mike Riley's Elf/OS v5 installer, with the System-5 change to its kernel | Burned 2026-11-15. **`@8000` wipes the card at once.** It leaves kernel 5.0.2 and five programs; the full card comes from the Mac's image. The ELF/OS 0.2.6 install ROM (the 2005 image) is kept |
| IO card | PS/2 firmware in the PIC16F84, behind a PAK-VI | 2005 |
| 6845 card | Character generator EPROM | 2005 |
| Bus driver, Nano | `s5-bus-driver` | Banner `blocks-1 io-2 clk-1 2026-10-31` |

On the Mac, all in use:

- **Bus driver tools** (`software/busdrv/`): `s5busdrv.py` (peek, poke, load, memory test), `bringup.py` (the
  bring-up plans for memory, CF and video) and `cputrace.py` (step the CPU and compare each bus cycle with the
  emulator).
- **The emulator s5emu** (`software/s5emu/`): a fast model that boots the real HBIOS ROM and ELF/OS; a gate-level
  model of every card from its KiCad netlist (`--hw`); a timing analyser; a browser page with Machine and Debugger
  tabs; and a GitHub Codespace that runs the page with nothing to install.
- **Card and program tools:** `mkelfos.py` (builds a CF card image), `disktool`, `tools/asm1802.py` (the Python
  1802 assembler that builds HBIOS 1.0.5 and 1.0.6, GBASIC and the VIDEO-G HBIOS).
- **Board tools:** the Eagle-to-KiCad converter with its netlist proof, the schematic generator and book, the
  older pre-order check (`tools/preorder_check.py`; the check before an order is `pcb-check`, a repository of its
  own).
- **Documents:** the System-5 manual (`docs/manual/`, 13 PDFs) and the website (`website/`), which is built from
  the repository's documents on every push to `main`. It has been published at `system5.cottageworker.com` since
  2026-11-13 (GitHub Pages).

## 4. Software changes planned

On the machine:

- **Elf/OS v5** (from the `elfos-v5` branch, merged into `main` on 2026-11-15): Mike Riley's 5.1.1 build 229, with a patched `fsck` and
  a `cls` written for System-5, runs on the real machine since 2026-11-15 with HBIOS 1.0.6 (v5 passes 00 for the
  drive/head register, which HBIOS 1.0.4 and 1.0.5 sent to the card as a CHS address). MINIMON (built from Mike's
  source) and Rc/Basic Level 2 are on the card too, added with `v5card.py add` (2026-11-15). A Codespace starts v5; on a
  Mac the emulator starts 0.2.6 unless `S5_OS=5`. To do: tell Mike Riley about the six `fsck` faults and the drive/head
  difference.

Made, waiting for the machine:

- **The VIDEO-G set**, which waits for the boards: the VIDEO-G build of HBIOS, the ATmega keyboard and mouse
  firmware, the character ROM, and **GBASIC 1.0**, an integer BASIC with graphics. All run in the emulator only.

Changes to make:

- **HBIOS: act on terminal (ANSI) codes such as clear screen** (Ken, 2026-11-14), so that programs written for a
  serial terminal need not be rewritten as `cls` was. A new HBIOS version and a new EPROM.
- **HBIOS: the 64-column wrap fault.** The first character after a wrap is lost, so `DIR` drops every fifth name.
  It is in the same screen routine as the item above: one new ROM could carry both, and 1.0.5's commands too.
- **`visual02` at different addresses** (Ken, 2026-11-14). Mike Riley's debugger loads at 6000-704A, across the
  kernel's heap and into the video RAM, and draws for an 80 x 24 screen.
- **The install ROM:** its `EXEC` loads at 7000, which is the video RAM, and its full format cannot leave a usable
  card. Until it is fixed, do not run `EXEC` and build cards on the Mac.
- **`EDIT` with no file name hangs ELF/OS 0.2.6.** Always give a name until the kernel's error path is traced.
- **The BIOS probes for a UART and a clock on ports 2 and 3**, which on System-5 are the IDE registers. Check that
  this does no harm.
- **For VIDEO-G:** the 64 x 32 table for the IBM 5151, whose cursor needs a place outside the text RAM (not the 6845: it is write-only) (the boot loader's port 4 no longer matters: VIDEO-G is memory-mapped).
- **CF card tools:** a `mkelfos.py --card` helper that checks the image and prints the `dd` line; a manual section
  on the CF card.
- **Emulator:** the 6845's real character generator and the PIC keyboard path; an IDE write past the end of the
  card should fail; an "E" memory revision and a 74HCT151 part for the timing analyser.

## 5. New ideas in the backlog

Hardware:

- **Bus driver Rev C (BUSDRV-C):** reach all 36 bus positions with a third MCP23017 and a clock output, so the bus
  driver can pause, step and load memory with the CPU card in place.
- **Memory, next revision:** a faster address latch than the CD4042B (timing finding C1). The 28C256 EEPROM sockets are in Rev F (2026-11-18); the software to rewrite the EEPROM is still to do.
- **Move the 6845 video to E000-EFFF:** RAM becomes one piece, 0000-DFFF (56K). It needs MEM3-E's second RAM
  fitted (IC11 and its mux IC4, empty today) and its jumpers moved, one jumper on the 6845 card and a rebuilt HBIOS.
- **Repairs to the cards in use:** T1's inverted TPA on the CPU card; bypass capacitors on the 6845 card.

Software:

- **The emulator in a browser with no server** (Pyodide), so a static page, such as the System-5 website, could
  run it. Mike Riley's permission is needed for HBIOS and ELF/OS before any public page.
- **Rc/Basic Level 2 on the CF card** (FOR/NEXT, DATA, DIM, strings).
- **GBASIC:** string variables, faster SAVE and LOAD, the mouse.

Repository and website:

- **A public repository** with Ken's own work, the third-party material staying in `private-resources`. There is
  a checklist in `BACKLOG.md`; this repository itself is never made public.
- **The website's menu** does not have VIDEO-G and GBASIC yet.
- **Optional history:** the remaining Eagle exports (14 of 33 done) only document the past.

## Where the records are

| For | Read |
|---|---|
| Which boards were ordered or built | `hardware/FABRICATED.md` |
| Open work, in full | `BACKLOG.md` |
| Bring-up results | `hardware/*/*/*/bringup/README.md` |
| Timing findings | `hardware/TIMING-REVIEW.md` |
| How the system works | `docs/manual/system.md` and the card chapters |
| The emulator and the Codespace | `software/s5emu/README.md`, `software/s5emu/CODESPACE.md` |
