# VIDEO-G 1.0 - design

The next System-5 video card (Ken, 2026-11-01): 64-column text plus a one-bit graphics layer, a PS/2 keyboard and
mouse, on **two boards** joined by a short ribbon. It replaces the 6845 card (Rev B) and the IO card (its keyboard; the
1861 comes out). Status: **both boards drawn, reworked to the memory map and routed (2026-11-17), not ordered**;
both pass `pcb-check`, Ken's check before an order on every system since 2026-11-06 (TEXT no failures, 0 warnings;
GFX no failures, 1 warning: no power LED, which TEXT has; [`kicad/README.md`](kicad/README.md#before-ordering),
"Before ordering"). KiCad masters in `kicad/text-1.0` and `kicad/gfx-1.0`, generated from each board's `gen/netlist.py`
and `gen/place.py` by `kicad/common/build.sh` ([README.md in `kicad/`](kicad/README.md)).

**Decided 2026-11-17 (Ken): everything memory-mapped, no I/O ports.** The 6845, the keyboard, the status and control
registers, the mouse and the Y register moved from ports 1 and 4-7 into the card's own block, beside the text RAM
(section 3); KEY-READY is also on the bus -EF (EF3 on CPU Rev A), and the VIDEO-G HBIOS polls it in the status
register, so either CPU card will do. VIDEO-G uses no port at all: port 4 is free for the IO panel card, and the
ELF/OS boot loader's `OUT 4` is harmless. HBIOS backwards compatibility is not a concern (Ken). The boards, the
VIDEO-G HBIOS, s5emu's model and GBASIC were all reworked the same day; the port version is in the git history.

It is YACC1's Video V2.0 (`~/Developer/YACC1-D/hardware/cards/video/kicad/v2.0/v20_netlist.py`, theory
`docs/cards/video-v2.md`, PS/2 firmware `embedded/video-ps2`; copied, never modified) moved onto the System-5 bus and
cut down, so the parts below keep V2.0's circuit wherever the text says nothing else.

## 1. The two boards

| Board | Silkscreen | What is on it | Works alone? |
|---|---|---|---|
| **TEXT** | VIDEO-G 1.0 TEXT | bus decode (every register is memory-mapped), 6845, text RAM, character ROM, dot clock, the status register, PS/2 **keyboard**, the dot combine and both video outputs | **yes**: a 64-column text card with a keyboard (text always on) |
| **GFX** | VIDEO-G 1.0 GFX | graphics RAM (two pages), its address multiplexers and slot logic, the Y register, the graphics shifter, the **control register (7804)**, PS/2 **mouse** | no: it takes the display timing and every decode from TEXT |

Both are System-5 cards (the 30-pin connector where every card has it), 4 layers (In1 GND, In2 +5V), in
neighbouring slots. **GFX is the standard 141 x 96 mm card; TEXT is 188 x 96 mm** - the same width along the
backplane, bus edge, connector and card-guide corners, 47 mm taller. Its 24 ICs (four 600-mil or 28-pin) and the DB9
(21 mm deep at the front edge) need about 11,000 mm2 of socket cells, against the standard card's ~9,000 usable; even
with the keyboard moved off it would need ~167 mm. **Approved by Ken, 2026-11-17: 188 mm fits.** A **40-pin ribbon
(2 x 20 IDC, about 10 cm)** joins them: both headers lie along the same side edge, 88-148 mm from the bus edge, so
the cable goes straight across between the slots. Board-layout rules
of 2026-10-24 apply (jacks, LEDs and jumpers labelled; references outside parts; IC types beside them), and
`cottageworker.com` beside the board name.

### The bus: the existing 30 pins only (Ken, 2026-11-01)

Both boards work on **today's 30-pin bus**: the standard 30-pin connector, in the 2009 backplane (or bus Rev D) next to
the CPU, memory and IDE cards. They use nothing from slot pins 31-36 (-EF1-3, -PAUSE, -DMAIN, SC0) and need no other card
changed except the CPU EPROM's video driver (section 8).

| Pin | Signal | TEXT | GFX |
|---|---|---|---|
| 1, 30 | +5V, GND | yes | yes |
| 2-9 | D0-D7 | text RAM, 6845, key latch, status | window reads/writes, Y register, control register, mouse byte |
| 11 | TPA | high-address latch | - |
| 12 | TPB | write strobes, 6845 E (writes), KEY-READY clear | MOUSE-READY clear |
| 13 | -MRD | text RAM, read enables, 6845 E (reads) and R/-W | window reads |
| 14 | -MRW | text RAM, write strobes, 6845 R/-W | window writes |
| 15-22 | A0-A7 | high byte (latched), A0-A10 | A0-A5 |
| 24, 28, 29 | N2, N1, N0 | not used: no I/O ports (2026-11-17) | - |
| 25 | -EF | KEY-READY, open collector, jumper KBD-EF | - |
| 26 | -VMA | block decode | - |
| 27 | -RESET | control register, ATmega | flags, ATmega |
| 10, 23 | Q, -INT | not used | not used |

**Pull-ups TEXT carries, because the 2009 backplane has none:**
- **-EF, 10k (needed).** The CPU card has no pull-up on it either (JP1 straight to the 1802's EF3); the IO card's
  CDP1852 drove it push-pull. TEXT drives it open collector, so without a pull-up EF3 would float.
- **-VMA, 10k.** The CPU card drives it from an open-collector 74LS05 and nothing pulls it up: it works today because
  every input on it is LS (the memory card's 74LS32, the 6845 card's 74LS04), and an open LS input reads high. TEXT's
  -VMA input is LS too (74LS85 cascade, as on the 6845 card), and the pull-up gives it a clean edge.
- **-RESET, 10k.** The CPU card pulls it up (R3), but with the CPU card out (bus-driver bring-up) it floats; a floating
  -RESET is what held the 6845 in reset on 2026-10-31.

Each is harmless in parallel with bus Rev D's 10k. The other lines (TPA, TPB, -MRD, -MRW) are always driven
push-pull by the 1802 or by the bus driver.

**The bus driver** reaches every register and the window with its memory reads and writes, as it reaches the memory
card: the card answers ordinary memory cycles only.

Dropped from V2.0: 6-dot / 80-column mode (fixed 8 dots), direct mode (the shared slots always work at the 1802's
speed: section 5), the text-only build (TEXT alone is that build), the keyboard command path and -INT (HBIOS polls;
the ATmega drives the keyboard LEDs itself), the dot-clock divider (IC21 and SV4).

## 2. Display formats

12 MHz dot clock, 8 dots a character: **1.5 MHz character clock**, the same as the 6845 card's 9 MHz / 6, so the
horizontal values barely change. The **MONITOR** jumper (status bit 4, read at 7804) tells HBIOS which table to load.

| | NTSC (RCA composite, or DB9 at TV rates) | MDA (DB9 to an IBM 5151) |
|---|---|---|
| Text | **64 x 25** | **64 x 32** |
| Graphics | **512 x 200** | **512 x 256** |
| Lines / frame | 15.79 kHz, 262 lines, 60.3 Hz | 18.52 kHz, 370 lines, 50.05 Hz |
| R0-R9 | 94, 64, 76, 8, 31, 6, 25, 28, 0, 7 | 80, 64, 68, 10, 45, 2, 32, 39, 0, 7 (YACC1's, passes its vidsim for the 5151) |
| Text RAM used | 1,600 bytes | 2,048 bytes |
| Graphics page | 12,800 bytes | 16,384 bytes |

The NTSC values are a first cut (R2/R3 to centre the picture on the bench). Cells are 8 x 8: the 28C64 character ROM
holds a 128-character font: `firmware/video-g-chargen/` (System-5's 6845-card font, 5 x 7 glyphs with lower case,
centred in the 8-dot cells; V2.0's 8-dot font has only 64 characters and HBIOS writes lower case). The 6845's VSYNC is 16 lines wide on both tables (the MC6845
ignores R3's upper half; real MDA cards used a 6845 too). The 6845's start address (R12/R13) stays 0: the graphics
layer assumes MA = 64 x row + column (section 5).

Combine (V2.0's): dot = text dot (if TEXT-ON) OR graphics dot (if GFX-ON), or XOR of the two when XOR = 1.

## 3. Address map (memory-mapped; Ken, 2026-11-17)

Everything is in the card's 4K block (block 7, the BLOCK jumper: the 6845 card's decode, 74HCT373 on TPA and 74LS85
with -VMA): VIDEO-G uses no I/O port and does not look at N0-N2. Inside the block A11 picks the text RAM (0) or the
upper half (1); in the upper half A10 picks the registers (0) or the graphics window (1), and three 74HCT138 decode
A1-A2 for the registers (A0 is the 6845's RS; each pair repeats through 7BFF). Reads happen while -MRD is low and
writes while -MRW is low, as for any memory.

| Address | Read | Write | Board |
|---|---|---|---|
| 7000-77FF | text RAM (the IDT7134's bus port, 2K, as on the 6845 card): row r, column c at 7000 + 64r + c | the same | TEXT |
| 7800 | - | **6845 address register** | TEXT |
| 7801 | **6845 data** (R14-R17) | **6845 data** | TEXT |
| 7802 | **key** (ASCII; the read clears KEY-READY at TPB) | - | TEXT |
| 7804 | **status**: 0 KEY-READY, 1 MOUSE-READY, 2 VSYNC, 3 DE, 4 MONITOR (1 = MDA), 5 GFX-PRESENT (1 = GFX fitted), 7..6 = 10 (card ID) | **control**: 0 TEXT-OFF, 1 GFX-ON, 2 XOR, 3 DPAGE, 4 CPAGE, 5 MOUSE-ON, 7..6 spare; cleared by -RESET = text on, graphics and mouse off | TEXT reads, GFX writes (decoded on TEXT) |
| 7806 | **mouse byte** (3-byte PS/2 packets; the read clears MOUSE-READY at TPB) | **Y register**: the pixel line seen at 7C00-7C3F | GFX (decoded on TEXT) |
| 7C00-7C3F | **graphics window: pixel line Y** (64 bytes, bit 7 = leftmost dot), repeated through 7FFF | the same | GFX |

7803, 7805 and 7807 repeat 7802, 7804 and 7806 (A0 is decoded only for the 6845); 7802 takes no write. KEY-READY also
pulls the bus **-EF** low (jumper KBD-EF; CPU Rev A's JP1 row 3 = EF3), so a program can wait with `BN3` and then read
7802; CPU Rev D takes -EF on EF4, so the VIDEO-G HBIOS polls status bit 0 instead. The 6845 sits where the 6845 card
has it. Ports 1 and 4-7 are free: port 4 is the IO panel's, and the ELF/OS boot loader's `OUT 4` (it shows the sector
numbers, the ELF hex-display habit) goes there, as on an ELF.

The control register is the text/graphics switch Ken asked for. Bit 0 is TEXT-OFF, as on V2.0, so the register -RESET
clears shows text (Ken, 2026-11-01: text shows at reset); graphics and the mouse start off. The register itself is on
GFX (2026-11-01, to make room on TEXT): every bit but TEXT-OFF and XOR only matters with graphics. GFX sends TEXT-ON and
XOR back on the ribbon and gates its own dots with GFX-ON; with GFX absent TEXT's resistors hold text on and XOR off,
and a write to 7804 does nothing.

**Setting a pixel:** write y (0-199 / 0-255) to 7806; then OR the mask for x & 7 (an 8-byte table, bit 7 = x mod 8 = 0)
into byte 7C00 + x/8. No multiply: the card does the address arithmetic by wiring (section 5).

The card was first drawn with ports (2026-11-01 to 11-17: the key on INP 1, status and control on port 4, the 6845 on
ports 5/6, the Y register and the mouse on port 7, the window at 7800); the git history has that version.

## 4. TEXT board

**Bus side: the memory decode** (memory-mapped, 2026-11-17). The 74HCT373 latches A8-A15 on TPA; the 74LS85
compares A12-A15 with the BLOCK jumper (kept, set to 7), gated by -VMA -> BOARDSEL. A11 = 0: the text RAM (-TXTCE).
A11 = 1: **UPPER** (7800-7FFF); with A10 = 1, **WSEL** to GFX (the window); with A10 = 0, the registers, decoded from
A1-A2 by three 74HCT138 (G1 = UPPER, -G2A = A10):

- **IC5**, the address alone: Y0 = the 6845's -CS (7800/7801); RS = A0.
- **IC6**, the read enables, -G2B = -MRD: 7800 the 6845, 7802 the key latch, 7804 the status buffer, 7806 the mouse
  latch (-RDMOUSE to GFX). They last the whole -MRD time, to the end of the cycle: the 1802 latches read data at 7.5 T
  and wants it held up to 200 ns after (`software/s5emu/s5emu/timing.py`, `din_hold`).
- **IC7**, the write strobes, -G2B = -MRW and C = NOT TPB: low while -MRW is low and TPB is high (6.5 T to 7 T), so a
  register latches on the strobe's rise at 7 T, with the 1802's data valid; 7800 the 6845, 7804 the control register
  (-WRCTL to GFX), 7806 the Y register (-WRY to GFX). (Qualified by -MRW, a strobe never fires in a cycle that only
  puts an address on the bus.)
- **Side effects of a read** (clearing KEY-READY / MOUSE-READY) happen at TPB of the read: by then -MRD is final.

**The 6845 at 7800/7801.** -CS from IC5, **RS = A0**, **E = NAND(-RDCRTC, -WRCRTC)**: the whole -MRD time on a read
(the 6845 drives its data until the cycle ends) and TPB within -MRW on a write (6.5 T to 7 T: 284 ns at 1.76 MHz,
250 ns at 2 MHz, against the HD68B45's 220 ns, so the B grade is needed). **R/-W comes from a 74HCT74 half used as a
latch**: -PRE = -MRD sets it (read), -CLR = -MRW clears it (write), and it keeps its level between cycles. So R/-W is
already high when a read's E rises (the instruction fetch before every read is a read too) and stays high after E
falls when -MRD rises at the end; on a write it falls at 5 T, 1.5 T before E, and stays low after E falls at 7 T. It
never changes while E is high, which also ends the 6845 card's timing finding T2.

**Text RAM: the IDT7134** (4K x 8 dual port, as on the 6845 card and V2.0; kept by Ken on 2026-11-01 after weighing
an ordinary 62256 shared in slots, which needed six more chips and a bigger card). The bus on the right port (A0-A10,
A11 low; CE from TSEL, -OE = -MRD, R/-W = -MRW), the 6845 on the left (MA0-MA11, always reading). No snow, no waiting.

**Display.** V2.0's text path at 8 dots: the 12 MHz oscillator (74LS04), IC28 74LS163 loading 8 on every carry
(counts 8-15; QC = the 6845's clock, RCO -> CHARCLOCK), the code latch (74LS374: **7 code bits**, 128 characters,
because HBIOS writes lower case - V2.0's font has 64), 28C64 (a 128-character 8 x 8 font), 74LS166 shifter, 74LS175
delays, 74LS86 cursor/reverse XORs (bit 7 = reverse, as now), combine gates, 7416 open-collector outputs.

**Outputs, front edge:** RCA composite (video + composite sync through R11/R12, as now); DB9 TTL (1, 2 GND, 7 video,
8 HSYNC, 9 VSYNC through the **VSYNC +/-** jumper: + for TV-rate monitors, - for the 5151).

**Keyboard.** An ATmega328P (16 MHz, Arduino Uno bootloader; firmware `embedded/video-g-ps2`, one sketch for both
boards, keyboard mode with PD7 open) loads a 74HCT374 (read at 7802) and sets **KEY-READY** (74HCT74 half). A read
of 7802 clears it at TPB. Codes as the old PAK-VI keyboard sent them: ASCII with Enter $0D, Backspace $08, Esc $1B, Ctrl-C $03, Delete
$7F; F1-F12 $80-$8B, the editing and arrow keys $90-$9A, Shift + those +$40 (single bytes: HBIOS echoes and stores
every byte, so VT100 sequences would show; `#define KEYS_VT100 1` gives V2.0's). Caps Lock and its LED in the firmware.
Ready about 1.5 s after a bus reset (bootloader, then the keyboard's self-test). KEY-READY drives the bus **-EF** low through a 7416 gate, with a jumper **KBD-EF** (off: the card
leaves -EF alone, e.g. with the IO card still in). The ATmega's reset comes from the bus -RESET (open collector, as on
V2.0); FTDI header for its bootloader. PS/2 jack (Mini-DIN-6, MD-60SM) on the front edge, +5 V through a 0.5 A PTC.

**Jumpers:** BLOCK (2 x 4, 7 = 7000), MONITOR (NTSC / MDA), VSYNC +/-, KBD-EF. **Bus pull-ups:** 10k on -EF,
-VMA and -RESET (section 1, "The bus").

**Chips (24, `kicad/text-1.0/BOM.md`):** IDT7134, HD68B45, AT28C64B, ATmega328P, 74HCT373, 74LS85, 3 x 74HCT138,
74LS244 (status), 74HCT374 (key), 74LS374 (code), 74LS166, 74LS175, 74F163A, 2 x 74LS04, 74HCT08, 74LS08, 74LS32,
74LS10, 74LS86, 7416, 74HCT74. CMOS-input (HCT) parts wherever a chip listens to the 1802's address lines.
**Board: 188 x 96 mm** (section 1).

## 5. GFX board

V2.0's graphics layer, with the plane register replaced by the **Y register** and direct mode removed.

**Graphics RAM:** one 62256 (55 ns), **two pages** of 16K (DPAGE shown, CPAGE written: draw on one, show the other).

**Address.** The display reads **{DPAGE, RA2..RA0, MA10..MA0}**: plane n (2K) holds scan line n of every character
row - the RA:MA layout, which needs no counter of its own. The CPU's address is the same layout made from y and x:
y = 8 x row + scan line, so **{CPAGE, Y2..Y0, Y7..Y3, A5..A0}** - pure wiring, linear in y, and 64 bytes a line.
Four 74LS157 choose between them:

| RAM address | GA14 | GA13-GA11 | GA10-GA6 | GA5-GA0 |
|---|---|---|---|---|
| display | DPAGE | RA2-RA0 | MA10-MA6 | MA5-MA0 |
| CPU | CPAGE | Y2-Y0 | Y7-Y3 | A5-A0 (bus) |

**Slots.** V2.0's: in each character time (8 dot clocks, 667 ns) the first half is the CPU's, the second the
display's (mux select = QC OR RCO, from TEXT). Reads: a 74HCT374 loads the CPU-half byte on every QC rise and drives
D0-D7 while the window is read (WSEL AND -MRD low). Writes: WRQ (74LS74) samples WSEL AND -MRW low on CHARCLOCK's rise;
-WE pulses at counts 9-10 (167 ns) with a 74HCT244 driving the byte onto the RAM. Display: a 74LS374 latches the
display-half byte, a 74LS166 shifts it out at the dot clock -> GDOT to TEXT.

**Why slots always work here:** the 1802's -MRW is low 5 T-7 T (1.1 us at 1.76 MHz) and -MRD from 1.5 T to the end
(3.7 us), against a 667 ns slot, so every write gets one slot and every read is latched long before 7.5 T. The limit is
about a **2.1 MHz** 1802 clock: a write that just misses a slot start waits up to 667 ns for the next one and then
needs counts 8-10 (250 ns), 917 ns in all, inside -MRW's 2 T (1.14 us at 1.76 MHz).

**Y register:** a 74HCT374, clocked by -WRY (a write to 7806) from TEXT.

**Mouse.** A second ATmega328P (the same firmware in mouse mode: PD7 low through R6, 4.7k) loads a 74HCT374 (read at
7806) and sets **MOUSE-READY** (the WRQ 74HCT74's other half; cleared at TPB of that read), which goes to TEXT's
status register. MOUSE-ON (control bit 5) rising: the firmware resets the mouse and enables reporting; falling:
reporting off and the queue flushed. 3-byte packets, queued whole. **Driver rule:** before setting MOUSE-ON, read 7806
once if 7804 bit 1 is already set - a byte left in the latch when MOUSE-ON last fell stays there.
Mini-DIN-6 on the front edge, its own 0.5 A PTC, FTDI header.

**Control register:** a 74HCT273 loaded by a write to 7804 (-WRCTL from TEXT), cleared by -RESET: TEXT-ON (inverted bit 0) and
XOR go to TEXT, GFX-ON gates the dots here, DPAGE / CPAGE drive the multiplexers, MOUSE-ON the ATmega.

**Chips (19, `kicad/gfx-1.0/BOM.md`):** AS6C62256-55, 4 x 74HCT157 (CMOS inputs on the bus address), 74HCT374 x 3
(read latch, Y, mouse), 74LS374 (display latch), 74HCT244 (write buffer), 74HCT273 (control), 74LS166, ATmega328P,
74HCT74, 74LS04, 74LS05, 74LS08, 74LS20, 74LS32. **Board: the standard 141 x 96 mm.**

## 6. The ribbon (40-pin, TEXT J6 to GFX J4, pin for pin)

The pin map is `kicad/common/ribbon.py`, which both netlists import. A straight 40-way flat cable: conductor n is pin
n at both ends; odd pins on one row of each header, even on the other; every fast clock has a ground on both sides.

| Pins | Signals | Direction |
|---|---|---|
| 1, 16, 18, 20, 22, 25, 32, 34, 37-40 | GND | |
| 2-12 | MA0-MA10 | TEXT -> GFX |
| 13-15 | RA0-RA2 | TEXT -> GFX |
| 17 | DOTCLOCK (12 MHz, 33 ohm series on TEXT) | TEXT -> GFX |
| 19 | CHARCLOCK (33 ohm series) | TEXT -> GFX |
| 21 | QC (read-latch clock, 33 ohm series) | TEXT -> GFX |
| 23 | QCR = QC OR RCO (mux select) | TEXT -> GFX |
| 24 | WEPH = QA XOR QB (-WE phase) | TEXT -> GFX |
| 26 | -WRCTL (a write to 7804: the control register) | TEXT -> GFX |
| 27 | TEXT-ON (TEXT pulls it up) | GFX -> TEXT |
| 28 | XOR (TEXT pulls it down) | GFX -> TEXT |
| 29 | WSEL (7C00-7FFF: the window) | TEXT -> GFX |
| 30 | -WRY (a write to 7806: the Y register) | TEXT -> GFX |
| 31 | -RDMOUSE (a read of 7806: the mouse latch) | TEXT -> GFX |
| 33 | GDOT (graphics dots, gated by GFX-ON) | GFX -> TEXT |
| 35 | MOUSE-READY | GFX -> TEXT |
| 36 | GFX-PRESENT (tied high on GFX) | GFX -> TEXT |

With GFX absent, TEXT's RN2/RN3 hold TEXT-ON high and GDOT, XOR, MOUSE-READY, GFX-PRESENT low.

## 7. Timing to check before drawing

- The register cycles against the 1802's Figure 4 at 1.76 MHz and 2 MHz (section 4): the read enables and the
  6845's read E hold the data to the end of -MRD (the 1802 wants 200 ns past 7.5 T); the write strobes rise at 7 T with
  the data valid; the 6845's write E is TPB within -MRW (284 ns at 1.76 MHz, 250 ns at 2 MHz, against the HD68B45's
  220 ns); R/-W steady while E is high (the latch). In `s5emu.timing` once it models these boards' netlists.
- The 6845's read E lasts the whole -MRD time, up to 3.7 us at 1.76 MHz (within its 10 us cycle limit).
- The slot logic: V2.0's review findings (V2-4, V2-5, R3-1: a 74F163 / 74ALS163 for IC28) carry over; the ribbon adds
  about 5 ns to MA/RA and the clocks, which `tests/video/v20_timing.py` margins absorb - to recheck with the System-5
  numbers.
- The loads on D0-D7: the IDT7134's bus port and the 6845 (directly, as on the 6845 card), and the port, latch and
  buffer pins of both boards; the 62256 is behind its read latch and write buffer.

## 8. Software

- **HBIOS for VIDEO-G** (`firmware/hbios/video-g`, 2026-11-01, emulator-tested, not burned): the video driver - the
  6845 at 7800/7801, the 64 x 25 NTSC table, the bottom row at row 24, the control register (7804) = 00 at start, a
  24-row scroll (a line feed 47 ms instead of 168 ms at 1.76 MHz), and no echo for the special keys ($80 and up) - and
  (2026-11-17) the key read at 7802 with KEY-READY polled at 7804 (any CPU card), and v1.0.6's disk fix.
  Still to do: the IBM 5151 table (64 x 32, IN 4 bit 4). Built with `tools/asm1802.py` (a Python 1802 assembler that
  rebuilds the original HBIOS byte for byte).
- **s5emu:** `python3 -m s5emu --video g` models VIDEO-G behaviourally (text, the registers at 7800-7807, the 7C00
  window and the Y register, two pages, VSYNC/DE, `--monitor mda`, `--no-gfx`; no port answers; shell commands `png`,
  `vg`); gate level from the netlists later, as the other cards.
- **GBASIC** (`software/gbasic`, 2026-11-01): a new integer BASIC for ELF/OS with VIDEO-G graphics - GRAPHICS, TEXT,
  MIX OR/XOR, PAGE, PEN (draw / erase / invert), PSET, LINE, BOX, CIRCLE, ELLIPSE (filled or not), ERASE, POINT;
  SAVE/LOAD as ASCII files; 12.5K; 35 tests (pixel-exact against Python models). Emulator only so far. Memory-mapped
  since 2026-11-17 (the key at 7802 when VIDEO-G is there, the IO card's INP 1 on the 6845 card's machine).
- **ATmega firmware** `embedded/video-g-ps2` (2026-11-01): written, compiles (6.3K flash), 42 checks pass in its
  host simulation (`sim/run.sh`); not yet run on a chip.
- **Bring-up from the bus driver:** register and window tests with its memory reads and writes, as for the memory
  card. The ATmega firmware loads the next byte 1 ms after the CPU's read (the bus driver holds TPB high for ~0.3 ms).
- **Found in the emulator: the ELF/OS boot loader writes port 4** (sector 0's loader shows each kernel sector number
  there, the ELF hex-display habit), which left the port version's control register at 0Eh. Settled 2026-11-17 by the
  memory-mapped card, which answers no port.

## 9. Decisions

Settled (Ken, 2026-11-01): the existing 30-pin bus; the name VIDEO-G 1.0; keyboard on TEXT, mouse on GFX; no
80-column mode; DB9 kept for an IBM 5151; text shows at reset (TEXT-OFF bit); the BLOCK jumper kept; GFX in the slot
next to TEXT; the IDT7134 dual-port RAM kept for text (after weighing a 62256 shared in slots).

Made while drawing (2026-11-01, for Ken to confirm): **TEXT is 188 mm tall** (section 1); the **control register moved
to GFX** (section 3); standing resistors and two resistor networks on TEXT to save room; HCT parts on the 1802's
address and N lines (no extra load on the CPU's outputs).

Settled 2026-11-17 (Ken): **everything memory-mapped** (section 3), which also settles **port 4 and the ELF/OS boot
loader** (section 8): VIDEO-G no longer uses port 4, so the loader's `OUT 4` needs no patch, and port 4 is the IO
panel's. HBIOS backwards compatibility is not a concern.

Settled 2026-11-17 (Ken): **TEXT stays 188 mm tall** (it fits the card cage); the **right-angle DB9 stays on the
board** for the IBM 5151; and the **2026-11-02 silkscreen rule applies** (every part's value beside its reference,
outside the part: the bypass capacitors' 100n too), although the boards were drawn just before it.

The character ROM image: `firmware/video-g-chargen/video-g-chargen.bin` (System-5's own 6845-card font, 128 characters
with lower case, centred in the 8-dot cells; a wider 8 x 8 font can replace it later).
