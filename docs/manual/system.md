# System-5: the system and how it works

System-5 is an RCA 1802 computer, designed in 2004–05 to run Mike Riley's ELF/OS.
It is a card system: a passive backplane carries a 30-pin bus, and each function is a card plugged into it.
The bus is the one defined for the wire-wrapped System-4 (1979–82), so old wire-wrap cards and new PCB cards could share the backplane while the system was rebuilt a card at a time.

This document is the overview: the cards, how a bus cycle flows through them, the memory and I/O maps, and how the machine starts.
The bus itself is in [bus.md](bus.md); each card has its own chapter; programming is in [programmers-guide.md](programmers-guide.md).

## The cards

| Card | Revision in the machine | What it does | Chapter |
|---|---|---|---|
| Backplane | the 2009 PCB: six 36-pin slots, no regulator (System-4's was Vero board) | the 30-pin bus (plus -EF1-3, -INP, -OUT, -IOM on the 36-pin slots), power | [bus.md](bus.md) |
| CPU | Rev A, reworked | CDP1802, clock, reset and run control, the high-address latch, the 4K boot EPROM and its remap, -VMA | [cpu-card.md](cpu-card.md) |
| Memory | Rev E (MEM3-E), built 2026-10-31 | 32K RAM + 32K EPROM sockets; each 4K block can be RAM, EPROM or empty | [memory-card.md](memory-card.md) |
| 6845 video | Rev B | 64 × 16 text display from BYTE (May 1979): dual-port video RAM at 7000, CRTC at 7800, composite out | [video-6845-card.md](video-6845-card.md) |
| IO (1861 + keyboard) | Rev A | PS/2 keyboard through a PAK-VI decoder and a PIC16F84 into a CDP1852 port; a CDP1861 graphics chip (not used) | [io-card.md](io-card.md) |
| IDE/CF | Rev A | Mike Riley's 8-bit IDE interface: a CompactFlash card in an IDE adapter holds ELF/OS | [ide-cf-card.md](ide-cf-card.md) |
| Bus driver | Rev B (BUSDRV-B), working since 2026-10-30; plugged in for tests | test card: an Arduino Nano runs bus cycles in place of the CPU, to bring up the other cards, or steps the CPU's clock and traces it | [bus-driver-card.md](bus-driver-card.md) |
| Breadboard prototype, front panel | Rev A design only / never designed | | [other-cards.md](other-cards.md) |

Which revisions were ordered, built or only drawn is recorded in `hardware/FABRICATED.md`.

## Block diagram

```
                       +----------------------------------------------------------------+
   crystal ─┐          |                     the 30-pin System-5 bus                    |
            v          |  +5V GND  D0-D7  A0-A7  TPA TPB  -MRD -MRW  -VMA  N0-N2  Q     |
   +-------------+     |  -EF  -INT  -RESET                                             |
   |  CPU card   |<===>+----+-----------+---------------+---------------+-------------+-+
   | 1802, boot  |          |           |               |               |             |
   | EPROM, -VMA |     +---------+ +-----------+   +-----------+   +-----------+  +-----------+
   +------+------+     | memory  | | 6845      |   | IO card   |   | IDE/CF    |  | bus       |
          |            | 32K RAM | | video RAM |   | keyboard  |   | 8-bit IDE |  | driver    |
          | SV3 ribbon | 32K ROM | | 7000-7FFF |   | port, 1861|   | ports 2/3 |  | (test)    |
          +----------->+---------+ +-----+-----+   +-----+-----+   +-----+-----+  +-----------+
           (1861 clock, DMA, SC0/1,      |               |               |
            EF lines: CPU <-> IO card)   composite       PS/2           CF card in an
                                         video           keyboard        IDE adapter
```

The CPU card and the IO card are also joined by a ribbon (CPU SV3 to IO SV3) that carries the 1861's clock, DMA request, state code and flags. Those signals are not on the bus.

## A bus cycle

The 1802 multiplexes its address: it puts the high byte on A0–A7 first, then the low byte. Every card that needs the high byte latches it itself.

1. **High address.** The 1802 drives A8–A15 on its A0–A7 pins and raises **TPA**. The CPU card latches it (IC1, the high-address latch) for its own decode; the memory card (CD4042s) and the 6845 card (74LS373) latch it too.
2. **Low address.** TPA falls; the 1802 drives A0–A7.
3. **-VMA.** The CPU card drives **-VMA** low when the address belongs to the bus, and high while its own boot EPROM is answering. Memory cards and the 6845 card decode only while -VMA is low.
4. **Read or write.** For a read, **-MRD** goes low early in the cycle and the selected chip drives D0–D7. For a write, the 1802 drives D0–D7 and pulses **-MRW** late in the cycle.
5. **TPB** marks the end of the cycle. The 6845 uses it as its E clock; the I/O cards use it to time their strobes.

I/O instructions add the **N0–N2** lines: `OUT n` and `INP n` put n on N0–N2 for the execute cycle. An I/O card decodes N with a 74LS138, takes the direction from -MRD (an `OUT` is a memory read: the byte goes from memory to the port; an `INP` writes the port's byte into memory), and times its strobe with TPA and TPB.

Timing figures are in [bus.md](bus.md) and `hardware/TIMING-REVIEW.md`.

## Memory map

As the machine is set up (CPU card SV2 = H, SV4 = bank 7, SV5 = Boot/REMAP; memory card Rev E jumpers `RRRRRRR-EEEEEEE-`; 6845 SV1 = block 7):

| Address | What answers | Notes |
|---|---|---|
| 0000–6FFF | memory card RAM (IC1) | 28K. ELF/OS and its programs live here; the stack starts at 00FF in the monitor |
| 7000–77FF | 6845 card: video RAM (IDT7134, bus port) | 64 × 16 = 1024 characters at 7000–73FF; HBIOS keeps its cursor position in 77FE–77FF |
| 7800–7FFF | 6845 card: the CRTC | 7800 = address register, 7801 = data register; repeats every 2 bytes through 7FFF |
| 8000–EFFF | memory card EPROM (IC5) | 28K; e.g. the ELF/OS install ROM (`../private-resources/elf/firmware/elfos-install-rom`) |
| F000–FFFF | CPU card boot EPROM (2732) | HBIOS: the System-5 video and keyboard code (F000–F2FF) and Mike Riley's BIOS (F300–FFFF, entry table at FF00) |

After a reset, until the first access with A15 high, the CPU card's EPROM answers at **every** address (that is how the 1802, which starts at 0000, reaches the boot code); see "Starting up" below.

**The memory card in the machine is Rev E (MEM3-E)**, built and brought up on 2026-10-31. It decodes by jumper and leaves block 7000 to the 6845 card and block F000 to the CPU card's boot EPROM, so every address has one driver. The bus driver's tests found its RAM good over all of 0000–6FFF and its EPROM reading back correctly over all of 8000–EFFF (`hardware/memory/kicad/rev-e/bringup/README.md`). The reworked Rev B card it replaced is described in [memory-card.md](memory-card.md).

## I/O map

| Port (N) | `OUT n` | `INP n` | Card |
|---|---|---|---|
| 1 | — | keyboard: the last character | IO card (SV2 = port 1); the character-ready flag is EF3 |
| 2 | IDE register select | — | IDE card (SV1 = port 2) |
| 3 | IDE register write | IDE register read | IDE card (SV2 = port 3) |
| 4 | (1861 DISPLAY OFF, if SV6 is fitted) | (1861 DISPLAY ON, if SV6 is fitted) | IO card: SV6 is empty on the built card |
| 5–7 | free | free | |

| Flag | Source |
|---|---|
| Q | the 1802's Q output: on the bus, and the CPU card's Q LED |
| EF3 | the bus -EF line (CPU card JP1, row 3): the keyboard's character-ready flag (IO card SV1 2-3) |
| EF1, EF2, EF4 | not connected on the built card (JP2–JP4 empty); they can carry the front panel, the 1861 and the keyboard flag over the ribbons |
| -INT | the bus -INT line: only the 1861 can drive it |

## Starting up

1. **Power on.** The CPU card's CM1232 (U1) holds -RESET low, then releases it; a 74LS123 one-shot then pulses -RUN, so the 1802 leaves reset and runs (the 1802's CLEAR and WAIT lines are driven by two 74LS20 set/reset latches; see [cpu-card.md](cpu-card.md)).
2. **The boot map.** -RESET has cleared the CPU card's boot flip-flop. While it is clear, the 4K boot EPROM answers every memory read (A0–A11 select the byte) and -VMA is held high, so no bus card answers. The 1802 starts at 0000 and so runs the EPROM's first bytes.
3. **The jump.** HBIOS's first instructions (`boot:` at F000) load R0.1 with F0 (`LDI high boot` / `PHI R0`). R0 is the program counter, so the next fetch is from F0xx: the first access with A15 high. On the reworked card that rising A15 clocks the flip-flop set. From then on the EPROM answers only in its 4K window (F000–FFFF) and -VMA is low everywhere else: the bus cards appear.
4. **The video.** HBIOS loads the 6845's 16 registers from `vtable` (BYTE's 16 × 64 timing), clears the screen to spaces, stores the cursor position, and jumps to Mike Riley's monitor.
5. **The monitor.** It sets up the stack (R2 = 00FF) and the standard call and return routines (SCRT), and prompts. `@FF00` boots ELF/OS from the CF card.

## Where the details are

- The bus: [bus.md](bus.md).
- Each card: its chapter here, its KiCad project under `hardware/<card>/kicad/<rev>/` and its README.
- Timing: `hardware/TIMING-REVIEW.md` (the 1802's bus timing against every card).
- Software: [programmers-guide.md](programmers-guide.md); HBIOS source in `firmware/hbios/v1.0.4/`.
- The emulator, which runs the cards from their netlists: `software/s5emu/` (`python3 -m s5emu --hw`).
- Bringing up a card without the CPU: `software/busdrv/BRINGUP.md`.
