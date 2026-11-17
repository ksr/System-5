# The System-5 manual

Written 2026-10-26 from the cards' netlists (the KiCad conversions of the 2005 Eagle designs, each proven against its schematic and, where they survive, the 2005 order gerbers), the 2005 operating notes and website, the HBIOS source, and the emulator and timing work of October 2026.

| Document | What it covers | PDF |
|---|---|---|
| [system.md](system.md) | the cards, a bus cycle, the memory and I/O maps, how the machine starts | `pdf/system5-system.pdf` |
| [bus.md](bus.md) | the 30-pin bus: every pin, the 1802's machine cycle, -VMA, rules for a card | `pdf/system5-bus.pdf` |
| [cpu-card.md](cpu-card.md) | CPU card: clock, reset and run control, address latch, boot EPROM and remap, -VMA | `pdf/system5-cpu-card.pdf` |
| [memory-card.md](memory-card.md) | memory card: 32K RAM + 32K EPROM, 4K block jumpers, LEDs, Rev B as built | `pdf/system5-memory-card.pdf` |
| [video-6845-card.md](video-6845-card.md) | 6845 card: decode, dual-port video RAM, the BYTE video pipeline, display format | `pdf/system5-video-6845-card.pdf` |
| [io-card.md](io-card.md) | IO card: PS/2 keyboard through PAK-VI, PIC and CDP1852; the CDP1861 | `pdf/system5-io-card.pdf` |
| [ide-cf-card.md](ide-cf-card.md) | IDE/CF card: ports, register latch, strobes, registers | `pdf/system5-ide-cf-card.pdf` |
| [bus-driver-card.md](bus-driver-card.md) | bus driver card: the Nano and expanders, bus cycles, protocol | `pdf/system5-bus-driver-card.pdf` |
| [other-cards.md](other-cards.md) | the prototyping card, the front panel, earlier and planned revisions | `pdf/system5-other-cards.pdf` |
| [operators-guide.md](operators-guide.md) | using the machine: the boot monitor, Elf/OS 5.1.1 and every program on its card, ELF/OS 0.2.6, Rc/Basic, known problems | `pdf/system5-operators-guide.pdf` |
| [programmers-guide.md](programmers-guide.md) | memory and I/O maps, the devices, booting, the monitor, BIOS calls, tools | `pdf/system5-programmers-guide.pdf` |

`pdf/system5-hardware-reference.pdf` is the system, the bus and every card in one book.

`pdf/system5-schematics.pdf` is every card's schematic in one book (cover, contents, a bookmark per card and sheet), built by `tools/kicad/sch/make_book.py`; `tools/kicad/sch/build_all.sh` and `tools/preorder_check.py` rebuild it.

## Building the PDFs

```bash
python3 tools/mkpdf.py
```

Run it from the repository's root. It needs Google Chrome (headless) and nothing else; it writes `docs/manual/pdf/`. `python3 tools/mkpdf.py system5-bus` builds one book.

## Sources

- Schematics: the redrawn, block-by-block schematic of each card is `hardware/<card>/kicad/<rev>/schematic/<card>-<rev>-schematic.pdf` (drawn from the proven board netlist, `tools/kicad/sch/README.md`), and all of them together in `pdf/system5-schematics.pdf`; the 2005 drawing as converted is in `reports/`.
- Boards: `hardware/<card>/kicad/<rev>/`.
- Board history, what was ordered and built: `hardware/FABRICATED.md`.
- Timing: `hardware/TIMING-REVIEW.md`. Memory card review: `hardware/memory/REVIEW.md`. 6845 against BYTE: `hardware/video-6845/BYTE-COMPARISON.md`.
- The 2005 notes: `hardware/*/eagle/*/ops.html`, `hardware/board-notes/`, `docs/website-2005/`.
