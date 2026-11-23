# 6845 video card: theory of operation

The 6845 card puts 16 lines of 64 characters on a composite monitor.
Its video side is the circuit from "Single Chip Video Controller" by Bob Haas, BYTE, May 1979, almost gate for gate.
Its bus side is my own: one dual-port RAM in place of BYTE's multiplexed 21L02s, and a 1802-style decode.

- **In the machine: Rev B**, built 2005 (its chips came from the Rev A card). KiCad master with order files: `hardware/video-6845/kicad/rev-b/` (order on hold since 2026-10-09).
- Rev A (the first working card, early 2005) is in `hardware/video-6845/eagle/rev-a/`.
- Comparison with the BYTE article, part by part: `hardware/video-6845/BYTE-COMPARISON.md`.
- The next revision is to add a PS/2 keyboard connector (`BACKLOG.md`).

## Parts (Rev B)

| Ref | Part | Job |
|---|---|---|
| IC2 | 74LS373 | latches A8–A15 from A0–A7 on TPA |
| IC4 | 74LS85 (74S85 drawn) | compares A12–A15 with the block jumper SV1, enabled by -VMA |
| IC1 | IDT7134 | 4K × 8 dual-port RAM: the bus on the right port, the display on the left |
| IC3 | HD6845 (HD46505) | CRT controller: timing, sync, refresh addresses, cursor |
| Q1, IC6 | crystal, 74LS04 | the dot-clock oscillator (9 MHz in BYTE) |
| IC8 | **74LS163** (74HC160 drawn) | divides the dot clock by 6: the character clock |
| IC10 | 74LS174 | latches character bits 0–5 from the video RAM (EPROM A3–A8) |
| IC7 | 74LS174 | latches character bit 6 (EPROM A9); on Rev A this position was a 74LS90 dot-clock divider |
| IC12 | 2732 | character generator ("goodfont") |
| IC11 | 74LS166 | shift register: the dots out |
| IC9 | 74LS175 | delays reverse/cursor and display enable by two characters |
| IC13 | 74LS86 | reverse video: data bit 7 XOR the cursor, then XOR into the dots |
| IC5 | 74LS00 | character-clock decode (÷6), display-enable gate |
| IC14 | 7416 | open-collector drivers: video, sync |
| R5, R6 | 33 Ω, 270 Ω | the composite mix |
| U$4 | RCA jack | composite out |
| X1 | DE-9 | video, HSYNC, VSYNC separately, for a monitor that takes them |
| SV1 | 2 × 4 header | the card's 4K block |

## The bus side

**Decode.** IC2 (74LS373) latches the high address byte while TPA is high. IC4 (74LS85) compares the latched A12–A15 with the block set on SV1; its cascade inputs enable it only while -VMA is low. So the card answers in one 4K block: SV1 1-2 = block 7, **7000–7FFF**, where HBIOS expects it.
Within the block, A11 picks the device:

| Address | A11 | Device |
|---|---|---|
| 7000–77FF | 0 | video RAM (the IDT7134's right port) |
| 7800–7FFF | 1 | the 6845: RS = A0, so 7800 = address register, 7801 = data register, repeated every two bytes |

**Video RAM.** The IDT7134 is a true dual-port RAM: the bus and the display read it at the same time with no arbitration, so there is no "snow" and no waiting for retrace (System-4's 6116 card had both). The right port's A0–A10 come from the bus; its A11 is tied low, so the bus sees 2K. Its !OE is -MRD and its R/W is -MRW.

**The CRTC.** The 6845's E is TPB, its R/W is -MRW, RS is A0 and its RESET is the bus -RESET. Its data pins are on the bus. E = TPB is why the bus driver card must pulse TPB in its memory cycles.

## The video side

The 6845 counts characters and scan lines and puts out a refresh address (MA0–MA11) and a row address (RA0–RA2) for every character position, plus HSYNC, VSYNC, display enable and the cursor.

1. **Dot clock.** Q1 and three 74LS04 gates (IC6) oscillate at the dot rate (BYTE: 9 MHz).
2. **Character clock.** IC8 (74LS163) counts dots 0–5 and is cleared synchronously by a 7400 decode of QA·QC: ÷6, one character every 6 dots. Its QC output (high for two dot times) clocks the 6845. The '163 matters: the 74HC160 the Rev B schematic draws clears *asynchronously* and would divide by 5 (`BYTE-COMPARISON.md`).
3. **Character fetch.** MA0–MA11 address the IDT7134's left port; the byte for the current position appears on its left data pins.
4. **Character latch.** At the character clock IC10 (74LS174) latches bits 0–5 of the character onto the EPROM's A3–A8, and IC7 (another 74LS174) latches bit 6 onto A9. Bit 7 goes to the reverse-video path.
5. **Character generator.** IC12 (2732): the address is 7-bit ASCII × 8 + the row (RA0–RA2). A11 and A10 are tied low, so the font is 128 characters × 8 rows at 000–3FF. The dots are in data bits 7–3, bit 7 the leftmost.
6. **Dots out.** IC11 (74LS166) loads the five dots in parallel at the character clock (its other three inputs are grounded: the gap between characters) and shifts them out at the dot clock.
7. **Reverse and cursor.** IC13A (74LS86) XORs data bit 7 with the 6845's CURSOR output: a character with bit 7 set is reversed, and the cursor reverses its cell.
8. **Pipeline.** IC9 (74LS175) delays that reverse signal and the 6845's DISPLAY ENABLE by two character times, to line up with the dots that went through the RAM, latches and EPROM. IC13B XORs the delayed reverse signal into the dot stream, and a 74LS00 gate (IC5D) blanks the video outside display enable.
9. **Composite.** IC14 (7416, open collector) drives video, HSYNC and VSYNC into the 33 Ω / 270 Ω mixing network and the RCA jack.

## Display format

HBIOS loads the 6845 with BYTE's Table 2 values for 16 × 64 (they assume the 9 MHz crystal and ÷6):

| Register | Value | Meaning |
|---|---|---|
| R0 | 94 | horizontal total (characters − 1) |
| R1 | 64 | characters displayed per line |
| R2 | 77 | horizontal sync position |
| R3 | 8 | sync width |
| R4 | 28 | vertical total (rows − 1) |
| R5 | 2 | vertical total adjust (scan lines) |
| R6 | 16 | rows displayed |
| R7 | 22 | vertical sync position |
| R8 | 0 | non-interlaced |
| R9 | 8 | scan lines per character − 1 |
| R10 | 64 | cursor start line 0, blinking |
| R11 | 8 | cursor end line |
| R12, R13 | 0, 0 | display start address |
| R14, R15 | 03h, C0h | cursor address (row 15, column 0) |

Screen memory: row r, column c is at 7000 + 64 r + c.

## Building and fitting

- **IC8 must be a 74LS163** (or 74HCT163), as on the built card.
- **IC12:** burn `firmware/char-rom-fonts/goodfont` (1K) at 000h. HBIOS 1.0.4 (`VIDEOLOWER`, "Rev B and beyond") writes 7-bit ASCII as it is, lower case included.
- **Crystal:** 9 MHz to match HBIOS's table. The built card's crystal marking is unread.
- **SV1 1-2** (block 7). No other jumpers on Rev B.
- The 2005 card has no bypass capacitors fitted; the order master's BOM has them.

## Known points

From `hardware/TIMING-REVIEW.md` (worked out on Rev A; the bus side is unchanged):
- **T2:** a register write ends with R/W (= -MWR) rising while E (= TPB) is still high, at any clock speed; the HD6845 takes the register anyway, but the CRTC then drives the bus against the 1802 for about 250 ns.
- **T3–T5:** E width and register-read margins are tight at 1.76 MHz; register reads (R14–R17) are rare.
- Video RAM accesses are not affected: the 7134 does not use TPB.
