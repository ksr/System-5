# CPU card: theory of operation

The CPU card carries the CDP1802 and everything the processor needs to run: the clock, power-on reset and run control, the latch for the high address byte, a 4K boot EPROM with its remap circuit, and the -VMA signal that tells the bus cards when an address is theirs.
It passes the 1802's signals to the bus **unbuffered**.

- Board in the machine: **Rev A, reworked** (ordered 2005-01-03, Sierra Proto Express NoTouch 17545-iNTJ).
- KiCad (converted from the 2005 Eagle files, netlist proven, copper = the 2005 order gerbers): `hardware/cpu/kicad/rev-a/`.
- Rework as built, read from photos: `hardware/cpu/eagle/rev-a/rework/README.md`. The emulator models both the drawing (`--cpu-rev A`) and the board as built (`A-built`, the default).
- The 2005 description: `hardware/cpu/eagle/rev-a/ops.html`. Rev B (drawn, never built) adds JP5, a reset-only / reset-and-run choice.

## Parts

| Ref | Part | Job |
|---|---|---|
| U$1 | CDP1802 | the processor |
| Q1, IC7 (74LS00), IC8A (74LS74) | crystal, three NANDs, ÷2 | the clock |
| U1 | CM1232 (DS1232 fitted) | power-on reset and the reset push-button |
| IC5 | 74LS123 | one-shot: a RUN pulse after reset |
| IC3, IC4 | 74LS20 | two set/reset latches that drive the 1802's WAIT and CLEAR |
| IC1 | 74LS373 drawn, **74LS374 fitted** | the high-address latch (A8–A15) |
| IC9 | 74LS138 | picks the boot EPROM's 4K window |
| IC2 | 2732 (MBM2732A-30) | 4K boot EPROM: HBIOS |
| IC8B | 74LS74 | the boot flip-flop |
| IC6 | 74LS05 | open-collector inverters: RUN pulse, -VMA, EPROM enable, LEDs |
| JP1–JP4 | 4-way jumper blocks | route the external flags to EF1–EF4 |
| SV1, SV3, SV6 | headers | external reset; IO card ribbon (1861); front panel |
| SV2, SV4, SV5 | jumper blocks | EPROM half, EPROM bank, VMA mode |
| LED1–LED5 | | PWR, WAIT, CLEAR, Q, VMA |

## Clock

Three gates of IC7 (74LS00) and the crystal Q1 make an oscillator; IC8A (74LS74) divides it by two to drive the 1802's CLOCK input. IC8A's other output, LCLK, the inverted CPU clock, goes to the IO card (SV3) for the 1861.
The crystal's marking cannot be read in the photos. The timing review assumes 3.52 MHz (1.76 MHz to the 1802), the usual 1861 frequency.

## Reset and run control

The 1802's mode is set by its CLEAR and WAIT inputs: CLEAR low with WAIT high = reset, both high = run, CLEAR high with WAIT low = pause, both low = load.
On this card two 74LS20 four-input NAND pairs, IC3 and IC4, are wired as set/reset latches, one driving WAIT and one CLEAR. Four active-low, open-collector command lines set and clear them, each with a 10 kΩ pull-up:

| Command (low pulse) | WAIT (IC3) | CLEAR (IC4) | 1802 mode |
|---|---|---|---|
| -RESET | high | low | reset |
| -RUN | high | high | run |
| -PAUSE | low | high | pause (wait) |
| -LOAD | low | low | load |

The lines are open collector so several sources can drive them: this card, the front panel header (SV6) and the bus -RESET.

**Power on.** U1 (CM1232) holds -RESET low for its reset time after +5 V is good, and also takes the push-button S1 (or SV1 pin 1, for the old front panel's reset switch). When -RESET is released, IC5 (74LS123) fires a one-shot whose pulse reaches -RUN through an open-collector inverter (IC6A), so the 1802 runs by itself after every reset. -RESET also goes to the bus, resetting the 6845, the IO card's chips and the CF drive.

## The high address latch

IC1 latches A8–A15 from the multiplexed A0–A7 on TPA. The drawing has a 74LS373, transparent while TPA is high; the board has a **74LS374**, which loads on TPA's rising edge. The datasheet guarantees the high byte only before TPA *falls*, so the 374 is a race that a typical 1802 wins (timing finding T1: −102 ns worst case, +148 ns typical). The fix, if it is ever needed, is to clock the 374 from inverted TPA through a spare 74LS05 gate with a 1 kΩ pull-up.

The latched A8–A11 address the EPROM; A12–A14 go to IC9; A15 goes to SV2 and (reworked) the boot flip-flop.

## The boot EPROM and its remap

The 1802 starts at address 0000, but the boot code belongs at the top of memory, out of the way of programs. The card solves this with a flip-flop and -VMA.

**The window.** IC9 (74LS138) decodes A12–A14 into eight 4K banks; A15 enables it on G1 or G2A, chosen by SV2 (H = upper 32K, L = lower 32K). SV4 picks one of the eight outputs as the EPROM's window. As built: SV2 = H, SV4 = bank 7, so the window is **F000–FFFF**.

**The boot flip-flop (IC8B).** -RESET clears it. As reworked, its D and PRE are tied high and its clock is the latched A15, so **the first rising edge of A15 after reset sets it** (the drawing presets it from the window select instead; the rework README explains why the board differs).

**VMA mode (SV5):**

| Mode | Before the flip-flop is set | After it is set |
|---|---|---|
| Boot/REMAP (as built) | EPROM answers at every address, -VMA high | EPROM answers in its window only (-VMA high there); -VMA low everywhere else |
| Boot only | as above | EPROM off, -VMA always low |
| No ROM | EPROM never answers, -VMA always low | the same |

In Boot/REMAP mode one NAND of IC7 combines the window select with the flip-flop's Q, and IC6 (74LS05) drives -VMA and the EPROM's !CE from it; R13 pulls !CE up.
HBIOS starts with `LDI high boot / PHI R0`: R0 is the program counter, so the very next fetch is at F0xx, the A15 edge that ends the boot map. From then on the EPROM is at F000–FFFF and the bus cards see every other address.

The EPROM's data pins go straight to the bus; its !OE is -MRD.

## Flags, interrupts and DMA

- **EF1–EF4.** Four jumper blocks route external flags to the 1802's EF inputs: JP1 the bus -EF line, JP2 the front panel's flag (FEF), JP3 the 1861's flag (VEF, from the IO card ribbon), JP4 the keyboard flag over the ribbon (KEF). As built: JP1 on row 3 (bus -EF → EF3); JP2–JP4 empty.
- **-INT** comes from the bus with a pull-up (R7).
- **DMA OUT** comes from the IO card ribbon (the 1861); **DMA IN** from the front panel header. Both have pull-ups.
- **SC0, SC1** (state codes) go to the ribbon for the 1861 (SC1 also to the front panel).

## Headers

| Header | Pins | What |
|---|---|---|
| SV1 | 4 | external reset (pin 1, active low, to U1's push-button input) |
| SV3 | 2 × 8 | ribbon to the IO card: SC0, SC1, DMA OUT, LCLK, KEF, VEF, power |
| SV6 | 2 × 5 | front panel: FEF, SC1, -RUN, DMA IN, -PAUSE, CLEAR, -LOAD, WAIT |

## LEDs

| LED | Shows |
|---|---|
| LED1 | power |
| LED2 | WAIT |
| LED3 | CLEAR |
| LED4 | Q |
| LED5 | -VMA (on = the bus has a valid address) |

## Known points

- T1 (above): the 374 latches on the wrong edge of TPA. Works with a typical 1802.
- Contention C2 (`hardware/TIMING-REVIEW.md`): after a boot EPROM read, the 2732 keeps driving the bus for its float time (about 28 ns) plus R13's RC time while the next card starts. R13's value is unread; 1 kΩ or less keeps it short. No read is corrupted.
- Open questions for the board: which wire is which on the boot flip-flop (derived, not seen), the reset rework (IC5 pins 1/3, U1 pin 7), the crystal frequency, and which ROM image is in IC2.
