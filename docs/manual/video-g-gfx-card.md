# VIDEO-G GFX card: theory of operation

The GFX board is the graphics half of VIDEO-G: a one-bit graphics layer of 512 × 200 (NTSC) or 512 × 256 (IBM 5151) in two pages, the control register that mixes it with the text, and a PS/2 mouse.
It does not work alone. It stands in the slot next to the TEXT board and takes the display timing and every address decode from it over the 40-way ribbon.
The TEXT chapter, [video-g-text-card.md](video-g-text-card.md), has what the two boards share: the address map, the status register, the display formats and the ribbon's pin map.
The circuit is the graphics layer of YACC1's Video V2.0, without its direct mode and with its plane register replaced by a Y register.

- **VIDEO-G 1.0 GFX**: drawn 2026-11-01, made memory-mapped and routed 2026-11-17 (with its PWR LED that evening). `pcb-check --tests` passed at `38fc4d0` (2026-11-25: no failures, 0 warnings). **Not ordered, not built** (`hardware/FABRICATED.md`).
- KiCad: `hardware/video-g/kicad/gfx-1.0/`, generated from `gen/netlist.py` and `gen/place.py` by `hardware/video-g/kicad/common/build.sh`; parts list `BOM.md`.
- The design record: `hardware/video-g/DESIGN.md`, sections 3, 5 and 6.
- The standard 141 × 96 mm card, 4 layers (In1 GND, In2 +5V), 19 ICs, the **30-pin** bus connector.

## Parts

| Ref | Part | Job |
|---|---|---|
| IC1 | AS6C62256-55 | graphics RAM: two pages of 16K, shared in each character time |
| IC2–IC5 | 74HCT157 ×4 | RAM address multiplexers: the CPU's address or the display's |
| IC6 | 74HCT374 | CPU read latch (loads on QC's rise) |
| IC7 | 74HCT244 | write buffer: D0–D7 onto the RAM while -WE is low |
| IC8 | 74LS374 | display latch (CHARCLOCK) |
| IC9 | 74LS166 | graphics dot shifter |
| IC10 | 74HCT374 | Y register, written at 7806 |
| IC11 | ATmega328P | PS/2 mouse controller (16 MHz, Y1) |
| IC12 | 74HCT374 | mouse latch, read at 7806 |
| IC13 | 74HCT74 | WRQ (write request); MOUSE-READY |
| IC14–IC18 | 74LS04, 74LS05, 74LS08, 74LS20, 74LS32 | slot gates, RAM -WE and -OE, the GFX-ON gate, MOUSE-READY clear, the ATmega's reset (IC15, open collector) |
| IC19 | 74HCT273 | control register, written at 7804, cleared by -RESET |
| J1 | 1 × 30 right-angle header | the bus |
| J2, J3 | Mini-DIN-6, 1 × 6 | PS/2 mouse (+5 V through F1, 0.5 A PTC); FTDI header for the ATmega |
| J4 | 2 × 20 box header | the ribbon from TEXT's J6 |
| RN1 | 10k × 8 | pull-ups on the RAM data lines GD0–GD7 |
| R6 | 4.7k | the mouse-mode strap on PD7 |
| LED1 | LED | PWR |
| C1–C20 | 100n | one bypass per IC (C20 the ATmega's AVCC); C22 47 µF bulk |

From the bus GFX takes only D0–D7, A0–A5, -MRD, -MRW, TPB and -RESET. The rest comes on the ribbon: WSEL (7C00–7FFF), -WRY, -WRCTL and -RDMOUSE are decoded on TEXT.

## Registers

| Address | Read | Write |
|---|---|---|
| 7804 | (TEXT's status register) | **control** (IC19) |
| 7806 | **mouse byte** (IC12); clears MOUSE-READY at TPB | **Y register** (IC10): the pixel line seen in the window |
| 7C00–7C3F | **pixel line Y**: 64 bytes, bit 7 of each byte the leftmost dot; repeated through 7FFF | the same |

The control register:

| Bit | Name | Effect |
|---|---|---|
| 0 | TEXT-OFF | inverted (IC14E) to TEXT-ON on the ribbon: 0 shows the text |
| 1 | GFX-ON | gates the graphics dots here (IC16D) |
| 2 | XOR | to TEXT: text XOR graphics instead of OR |
| 3 | DPAGE | the page shown |
| 4 | CPAGE | the page the CPU reads and writes |
| 5 | MOUSE-ON | to the ATmega: mouse reporting on |
| 7–6 | – | spare |

-RESET clears it: text on, graphics and mouse off, page 0. Without GFX, TEXT's pull-ups give the same: text on, XOR off, no graphics dots, and a write to 7804 does nothing. GFX ties GFX-PRESENT (ribbon pin 36) high, so status bit 5 tells software the board is there.

## The graphics RAM and its address

One 62256 holds two pages of 16K. The display reads the RAM in the order the 6845 counts: **{DPAGE, RA2–RA0, MA10–MA0}**. Plane n (2K) holds scan line n of every character row, so the graphics needs no counter of its own; that is why the 6845's start address (R12/R13) must stay 0.

The CPU's address is the same layout built from y and the bus: **{CPAGE, Y2–Y0, Y7–Y3, A5–A0}**. Since y = 8 × row + scan line, this is pure wiring, linear in y, 64 bytes a line. The four 74HCT157s choose between them:

| RAM address | GA14 | GA13–GA11 | GA10–GA6 | GA5–GA0 |
|---|---|---|---|---|
| display | DPAGE | RA2–RA0 | MA10–MA6 | MA5–MA0 |
| CPU | CPAGE | Y2–Y0 | Y7–Y3 | A5–A0 |

**Setting a pixel** (x, y): write y (0–199, or 0–255 on the 5151) to 7806, then OR the bit for x mod 8 (80h for 0, 01h for 7) into 7C00 + x/8. Reading the byte back works the same way.

## The slots

The RAM is shared in each character time (8 dot clocks, 667 ns at 12 MHz). TEXT's counter runs 8–15. The select NMUX = NOT QCR, where QCR = QC OR RCO comes from TEXT: counts 8–11 are the CPU's half, 12–15 the display's.

- **Display.** IC8 latches the display-half byte at CHARCLOCK's rise; IC9 loads it at the next character and shifts it out at the dot clock (bit 7 first). IC16D passes the dots only while GFX-ON: that is GDOT, back to TEXT on the ribbon, where TEXT's combine and DE blanking finish the job.
- **CPU reads.** IC6 loads the CPU-half byte at every rise of QC (the end of the CPU half) and drives D0–D7 while WSEL and -MRD are both active (IC17B). A read of the window therefore needs nothing from the 1802: the byte is latched long before the 1802 samples it.
- **CPU writes.** GWR = WSEL AND MEMWR (IC16A). IC13A samples it at CHARCLOCK's rise: WRQ. -WE = NAND(WRQ, NMUX, WEPH, GWR) (IC17A) is low at counts 9–10 (WEPH = QA XOR QB from TEXT), 167 ns. IC7 drives the byte onto the RAM only while -WE is low, and IC16B holds the RAM's -OE off through that CPU half.

**Why slots always work here.** The 1802 holds -MRW low from 5 T to 7 T (1.1 µs at 1.76 MHz) and -MRD for longer still, against a 667 ns slot. A write that just misses a slot start waits up to 667 ns and then needs counts 8–10: 917 ns in all. That sets the limit at about a 2.1 MHz 1802 clock (`DESIGN.md` section 5). The netlist model agrees: 11 dot clocks of -MRW give a whole -WE from any counter phase, 10 do not.

## The mouse

IC11 runs the same firmware as TEXT's keyboard controller, `embedded/video-g-ps2`. R6 pulls PD7 low, which selects mouse mode. It loads each byte into IC12 with a pulse on LDDATA, which also sets **MOUSE-READY** (IC13B). MOUSE-READY goes to TEXT's status bit 1 on the ribbon. A read of 7806 clears it at TPB (IC18A, IC16C), and so does -RESET.

The mouse reports only while MOUSE-ON (control bit 5) is 1. When MOUSE-ON rises the firmware resets the mouse and enables reporting; when it falls it turns reporting off and empties its queue. Packets are the standard PS/2 3-byte ones (buttons and signs, X, Y), queued whole; `embedded/video-g-ps2/README.md` has the layout and a polling loop.

**Driver rule:** before setting MOUSE-ON, read 7806 once if status bit 1 is already set. A byte left in the latch when MOUSE-ON last fell stays there until it is read.

The bus -RESET resets the ATmega through IC15A/B (open collector); J3 takes an FTDI cable for its bootloader.

## Connectors and LED

J2 `MOUSE` and LED1 `PWR` are on the front edge, the LED level with TEXT's. J3 `FTDI` has its pins named `GND`, `TX`, `RX`, `DTR`. J4 `FROM TEXT (J6)` is on the side edge, 78–138 mm from the bus edge (its pins 83.6–131.9 mm), level with TEXT's J6: a straight cable of about 10 cm.

## Software

**GBASIC** (`software/gbasic`) is an integer BASIC for Elf/OS with graphics: PSET, LINE, BOX, CIRCLE, ELLIPSE, two pages, OR or XOR mixing. It sets the control register to 00 at start and clears both pages; its tests compare every pixel with Python models. `software/elfos-v5/vgdemo` is a short demonstration. The VIDEO-G HBIOS only writes 00 to the control register at start.

## Testing

- `python3 -m s5emu --video g` (in `software/s5emu`) models both boards behaviourally: the window, the Y register, two pages, the mouse; the debugger's `png` command saves the screen. Tests: `tests/test_videog.py`.
- `python3 -m s5emu --hw --video g` runs GFX from its netlist with TEXT. `tests/test_hw_videog.py` checks the multiplexer wiring, the write slot through the gates and graphics drawn by a program.
- These and GBASIC's tests (`software/gbasic/tests/test_gbasic.py`) are the board's `tests =` line in `pcb-check.ini`.

## Known points

- **Nothing of it has run on hardware**: the board, the mouse firmware and GBASIC have run only in the emulators and in the firmware's host simulation.
- **A window write can get a second, cut-short -WE.** A write that starts just before a character boundary gets its whole -WE in the first slot, and -MRW is still low when the next slot's count 9 comes. The same byte goes to the same cell, so nothing is lost (`DESIGN.md` section 10).
- The slot timing was reviewed for V2.0; the ribbon adds about 5 ns to MA, RA and the clocks, still to be checked with System-5's numbers (`DESIGN.md` section 7).
