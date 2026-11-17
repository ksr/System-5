# System-5: where things stand

A summary written on **2026-11-14** (the machine's software brought up to date on 2026-11-15, VIDEO-G and the decisions below on 2026-11-17) from the repository's own records: `hardware/FABRICATED.md`, `BACKLOG.md`, the
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
  two VIDEO-G boards (2026-11-17, reworked to be memory-mapped; no failures) and the bus Rev D; CPU Rev D and the IO
  panel have still to go through it. Three of the four decisions that held the orders were settled on 2026-11-17
  (section 2).
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
| Bus driver | **Rev B (BUSDRV-B)** | JLCPCB, Oct 2026, 2 layers | Test equipment, working since 2026-10-30. An Arduino Nano and two MCP23017s run bus cycles in place of the CPU, or step and trace the CPU |

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
| Bus backplane **Rev D (S5BUS-D)** | 8 slots of 36 pins, power switch, 4 A polyfuse, reverse-polarity MOSFET, pull-ups and pull-downs so every line idles off | Check passed (2 layers). Not ordered | Where the card supports go; SW1's ON direction; the cards' total current; socket height against the card guides; Ken's look at the pictures |
| **CPU Rev D** | The 36-pin CPU card: 2 MHz from a 4 MHz oscillator or an external clock, DS1813 reset, RESET/RUN switch, LOADED flag, 2732 at F000 | Check passed (2 layers). Not ordered. Runs HBIOS and ELF/OS in the emulator | The keyboard flag (below); the card-guide fit of a 4.00 inch card |
| **IO panel Rev A** | The front panel as a card: 8 toggles, 8 LEDs, two TIL311 hex displays, Q LED, INPUT button, ELF-style RUN/LOAD | Check passed (2 layers). Not ordered. Runs in the emulator and on the web page | M9040P toggles' availability and lever direction; Ken's look at the pictures (port 4 is its own since VIDEO-G went memory-mapped, 2026-11-17) |
| **VIDEO-G 1.0 TEXT** | 6845 text, 64 x 25 (NTSC) or 64 x 32 (IBM 5151), PS/2 keyboard on an ATmega, RCA and DB9; everything memory-mapped (2026-11-17). Works alone | **`pcb-check` passed** (2026-11-17: no failures, 0 warnings; 4 layers). Not ordered | Ken's look at the renders, the pictures and the fab's viewer (188 mm tall: Ken keeps it) |
| **VIDEO-G 1.0 GFX** | Graphics, 512 x 200 or 512 x 256 in two pages, PS/2 mouse. Joins TEXT by a 40-pin ribbon | **`pcb-check` passed** (2026-11-17: no failures, 1 warning, no power LED: TEXT has it; 4 layers). Not ordered | As TEXT |
| 6845 Rev B, order master | A re-make of the 2005 card | Order files ready. **On hold** (Ken, 2026-10-09) | Whether to make it at all, now that VIDEO-G exists |
| 6845 Rev C | Rev B plus the PS/2 keyboard, 36-pin bus | Design notes only | Looks superseded by VIDEO-G: retire it if Ken agrees |

The four decisions that held the orders (`BACKLOG.md`, "Questions for Ken"), three of them settled by Ken on 2026-11-17:

1. **Port 4 was wanted twice**, by the IO panel and by VIDEO-G's control register. Settled: VIDEO-G is memory-mapped
   (everything in its own block at 7000-7FFF, no I/O ports), so port 4 is the IO panel's.
2. **The keyboard flag.** VIDEO-G signals on bus -EF, which reaches EF3 through CPU Rev A's jumper; CPU Rev D sends
   -EF to EF4, and HBIOS reads EF3. Settled for VIDEO-G: its HBIOS polls KEY-READY in the status register (7804), so
   it works with either CPU card. Still open for the IO card's keyboard with CPU Rev D.
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
- **For VIDEO-G:** the 64 x 32 table for the IBM 5151 (the boot loader's port 4 no longer matters: VIDEO-G is memory-mapped).
- **CF card tools:** a `mkelfos.py --card` helper that checks the image and prints the `dd` line; a manual section
  on the CF card.
- **Emulator:** the 6845's real character generator and the PIC keyboard path; an IDE write past the end of the
  card should fail; an "E" memory revision and a 74HCT151 part for the timing analyser.

## 5. New ideas in the backlog

Hardware:

- **Bus driver Rev C (BUSDRV-C):** reach all 36 bus positions with a third MCP23017 and a clock output, so the bus
  driver can pause, step and load memory with the CPU card in place.
- **Memory, next revision:** 28C256 EEPROM sockets with a WRITE ENABLE jumper, so the 1802 can rewrite its own ROM;
  and a faster address latch than the CD4042B (timing finding C1).
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
