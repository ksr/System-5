---
hide:
  - toc
---

<!-- Author: Claude (Anthropic) for Ken Rother, 2026. The visitor home page of the System-5 website (stage.py copies
     it to index.md). Every fact here comes from the elf repository: README.md, docs/manual/, hardware/FABRICATED.md. -->

# System-5 — an RCA 1802 card computer

**System-5 is the RCA 1802 computer I built in 2004–05 to run Mike Riley's ELF/OS.** It is a card system: a
passive backplane carries a 30-pin bus, and each function is a card plugged into it. The bus is the one I defined
for my wire-wrapped System-4 (1979–82), so old wire-wrap cards and new PCB cards could share the backplane while the
machine was rebuilt one card at a time. All the 2005 boards were designed in Eagle 4.x.

In 2026 the designs came back to life: the surviving boards converted to KiCad and proven against their schematics, a manual
written from the netlists, an emulator that runs the real ROM, and two new boards made, both live and running: the
memory card now in the machine (Rev E), and a bus driver card (Rev B) that brought the old cards up on the bench. Since
November 2026 System-5 runs Mike's later operating system, Elf/OS 5.1.1, in place of the ELF/OS 0.2.6 it was built
for. The next machine is being designed too: a 36-pin bus
with a new CPU card and a front-panel IO card ([below](#next-the-36-pin-machine)).

I'm Ken Rother. I designed and built System-5. Claude, Anthropic's AI, has been directly involved in converting the
boards, the manual, the emulator and this site.

[:material-github: Source on GitHub](https://github.com/ksr/System-5){ .md-button .md-button--primary }

## At a glance

| | |
|---|---|
| **CPU** | CDP1802, about 1.76 MHz, 4.5 µs per machine cycle |
| **Bus** | 30 pins, kept from System-4: D0–D7, multiplexed A0–A7, TPA/TPB, -MRD/-MRW, N0–N2, Q, -EF, -INT, -VMA |
| **Memory** | 28K of RAM (0000–6FFF), EPROM 8000–EFFF on the memory card, a 4K boot ROM (HBIOS) at F000 on the CPU card |
| **Display** | a 64 × 16 text screen from the 6845 card (BYTE, May 1979), composite video |
| **Keyboard** | PS/2, through a PAK-VI decoder and a PIC16F84 into a CDP1852 port |
| **Disk** | a CompactFlash card in an 8-bit IDE interface (Mike Riley's design) |
| **Software** | HBIOS: my video and keyboard code on Mike Riley's BIOS, and his monitor with commands I added (help, boot, a disassembler, Q on and off). Mike's later operating system, Elf/OS 5.1.1 (build 229), booted from the CF card |

## The cards

<div class="grid cards" markdown>

-   ![CPU card Rev A](hardware/cpu/eagle/rev-a/photos/2026-10-07-front-1.jpg)

    **[CPU](docs/manual/cpu-card.md)** — the 1802, its clock, reset and run control, and the 4K boot EPROM
    (Rev A, reworked, in the machine).

-   ![Memory card Rev E (MEM3-E)](hardware/memory/kicad/rev-e/photos/2026-11-15-front-1.jpg)

    **[Memory](docs/manual/memory-card.md)** — 32K RAM and 32K EPROM sockets, every 4K block set by a jumper
    (Rev E, in the machine since 2026-10-31).

-   ![6845 video card Rev B](hardware/video-6845/eagle/rev-b/photos/2026-10-07-front-1.jpg)

    **[6845 video](docs/manual/video-6845-card.md)** — the 64 × 16 text display from BYTE, May 1979 (Rev B, the
    working card).

-   ![IO card Rev A](hardware/io-1861-keyboard/eagle/rev-a/photos/2026-10-07-front-1.jpg)

    **[IO](docs/manual/io-card.md)** — the PS/2 keyboard port, and a CDP1861 graphics chip that was never used
    (Rev A).

-   ![The 2009 backplane, bare](hardware/bus/eagle/rev-2009/photos/2026-10-26-silkscreen-side.jpg)

    **[Backplane and bus](docs/manual/bus.md)** — the 30-pin bus on the 2009 backplane: six 36-pin slots.

-   ![Bus driver card Rev B (BUSDRV-B)](hardware/bus-driver/kicad/rev-b/photos/2026-11-15-front-1.jpg)

    **[Bus driver](docs/manual/bus-driver-card.md)** — runs bus cycles from an Arduino Nano in place of the CPU, to
    bring up the other cards (Rev B, new in 2026, in use).

</div>

**[IDE / CF](docs/manual/ide-cf-card.md)** holds the disk. Which revisions
were made, ordered or only drawn: [Boards fabricated](hardware/FABRICATED.md).

## Next: the 36-pin machine

The six spare pins of the 36-pin slots are being given jobs: the three extra 1802 flags (-EF1 to -EF3), -PAUSE and
-DMAIN for front-panel control, and SC0 to show instruction fetches ([the 36-pin extension](docs/manual/bus.md)).
New cards for it, all drawn in KiCad, none ordered yet:

- **[Backplane Rev D](hardware/bus/kicad/rev-d/notes.md)** — eight 36-pin slots, power switch, fuse and
  reverse-polarity protection.
- **[CPU Rev D](hardware/cpu/kicad/rev-d/DESIGN.md)** — just the 1802 and its 4K boot EPROM, at 2 MHz or from an
  external clock; a load-then-run flag so a program toggled in runs from RAM.
- **[IO panel](hardware/io-panel/kicad/rev-a/DESIGN.md)** — the ELF-style front panel: eight toggles, eight LEDs, two
  TIL311 hex displays, Q, INPUT, RUN and LOAD. The emulator already runs a program toggled in through it.
- **[6845 video Rev C](hardware/video-6845/kicad/rev-c/DESIGN.md)** — design notes: Rev B's display with the PS/2
  keyboard moved onto it, and a CRTC fast enough for 2 MHz.

## Where to start

- **[The system and how it works](docs/manual/system.md)** — the cards, a bus cycle, the memory and I/O maps, how
  the machine starts.
- **[Programmer's guide](docs/manual/programmers-guide.md)** — the devices, the monitor, BIOS calls, ELF/OS.
- **[The manual as PDFs](docs/manual/README.md)** — the system, the bus and every card, also as one book.
- **[Build rules](hardware/BUILD-RULES.md)** — what every System-5 board follows, and the exceptions.
