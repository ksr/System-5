# VIDEO-G TEXT card: theory of operation

VIDEO-G is the next System-5 video card: 64-column text, a one-bit graphics layer, a PS/2 keyboard and a PS/2 mouse, on two boards joined by a 40-way ribbon.
The TEXT board works alone. It has the 6845, a dual-port text RAM, the character ROM, the keyboard, every address decode of both boards, and both video outputs.
The GFX board adds the graphics and the mouse ([video-g-gfx-card.md](video-g-gfx-card.md)).
The circuit is YACC1's Video V2.0, moved onto the System-5 bus and cut down. Everything is memory-mapped in the card's 4K block.
VIDEO-G is to replace the 6845 card ([video-6845-card.md](video-6845-card.md)) and the IO card's keyboard.

- **VIDEO-G 1.0 TEXT**: drawn 2026-11-01, made memory-mapped and routed 2026-11-17, its 6845 made write-only and routed again 2026-11-24. `pcb-check --tests` passed at `38fc4d0` (2026-11-25: no failures, 0 warnings). **Not ordered, not built** (`hardware/FABRICATED.md`).
- KiCad: `hardware/video-g/kicad/text-1.0/`, generated from `gen/netlist.py` (the circuit) and `gen/place.py` by `hardware/video-g/kicad/common/build.sh`; parts list `BOM.md`; the boards' README `hardware/video-g/kicad/README.md`.
- The design record, every decision with its date: `hardware/video-g/DESIGN.md`.
- 188 × 106.6 mm, 4 layers (In1 GND plane, In2 +5V plane), 24 ICs. It has the **36-pin bus connector**, so it needs the bus Rev D ([bus.md](bus.md)) and does not fit the 2009 backplane.

## Parts

| Ref | Part | Job |
|---|---|---|
| IC1 | 74HCT373 | latches A8–A15 while TPA is high |
| IC2 | 74LS85 | A12–A15 against SV1, enabled by VMA (-VMA inverted by IC16D): BOARDSEL |
| IC3 | IDT7134 | 4K × 8 dual-port text RAM: the bus on the right port, the 6845 on the left |
| IC4 | HD68B45SP | CRTC at 7800/7801, write-only |
| IC5–IC7 | 74HCT138 ×3 | the 6845's -CS; the read enables; the write strobes |
| IC8 | 74LS244 | status register (7804) |
| IC9 | 74HCT374 | key latch (7802) |
| IC10 | ATmega328P | PS/2 keyboard controller (Y2, 16 MHz) |
| IC11 | 74LS374 | character code latch, 7 bits |
| IC12 | AT28C64B | character ROM: 128 characters of 8 × 8 |
| IC13 | 74LS166 | text dot shifter |
| IC14 | 74LS175 | reverse/cursor and DE delayed two characters |
| IC15 | 74F163A | character counter, 8–15 |
| IC16–IC22 | 74LS04 ×2, 74HCT08, 74LS08, 74LS32, 74LS10, 74LS86 | oscillator (Y1, 12 MHz), decode gates, dot combine, the 6845's E |
| IC23 | 7416 | open collector: video, syncs, keyboard flag, ATmega reset |
| IC24 | 74HCT74 | KEY-READY (one half spare) |
| J1–J6 | | bus (1 × 36); RCA; DE-9 F; PS/2 (F1, 0.5 A PTC); FTDI; 2 × 20 ribbon to GFX |
| RN1–RN3 | 10k SIPs | SV1 pull-ups; bus and ribbon pull-ups; pull-downs |
| R4, R5 | 33 Ω, 270 Ω | the composite mix |
| C1–C25 | 100n | one bypass per IC (C25 the ATmega's AVCC); C26 47 µF bulk |

## The address map

The card answers in one 4K block set on SV1 and uses no I/O port (N0–N2 are not connected). For block 7, as set:

| Address | Read | Write |
|---|---|---|
| 7000–77FF | text RAM (2K): row r, column c at 7000 + 64r + c | the same |
| 7800 / 7801 | – (reads FF) | 6845 address register / data register |
| 7802 | the key; clears KEY-READY | – |
| 7804 | status | control register (on GFX) |
| 7806 | mouse byte (on GFX); clears MOUSE-READY | Y register (on GFX) |
| 7C00–7C3F | the graphics window (on GFX), repeated to 7FFF | the same |

A0 is decoded only as the 6845's RS, so 7803, 7805 and 7807 repeat 7802, 7804 and 7806, and the eight registers repeat through 7BFF. With no GFX board its addresses do nothing.

Status (IC8, 7804): bit 0 KEY-READY, 1 MOUSE-READY, 2 VSYNC, 3 DE, 4 MONITOR (1 = IBM 5151), 5 GFX-PRESENT, bits 7–6 = 10 (the card ID).

## The bus side

**Block decode.** IC1 latches the high address byte while TPA is high. IC2 compares the latched A12–A15 with SV1 and is enabled by VMA (the bus -VMA inverted by IC16D); its output is BOARDSEL. SV1 is pulled up by RN1, and each fitted shunt makes its bit 0: one shunt on the A15 pair gives 7000, where HBIOS expects the card.

**Inside the block.** A11 = 0 selects the text RAM (-TXTCE, IC20D). A11 = 1 gives UPPER, 7800–7FFF (IC18D). There A10 = 1 gives WSEL, the graphics window, sent to GFX (IC19D), and A10 = 0 enables three 74HCT138s that decode A1–A2:

IC5 gives the 6845's -CS (7800/7801). IC6, qualified by -MRD, gives -RDKEY (7802), -RDSTAT (7804) and -RDMOUSE (7806, to GFX), each lasting the whole -MRD time so the data is held past the 1802's latch point. IC7, qualified by -MRW, gives -WRCRTC (7800), -WRCTL (7804) and -WRY (7806), the last two to GFX; each is low from 5 T to 7 T, and a register takes the byte on the rising edge.

**Text RAM.** The IDT7134 is a true dual-port RAM, as on the 6845 card. The bus has the right port: A0–A10 with A11 tied low (the bus sees 2K), -OE = -MRD, R/-W = -MRW. The 6845 reads the left port all the time. There is no arbitration, no snow and no waiting for retrace.

**The 6845 is write-only** (Ken, 2026-11-24). R/-W is on ground and E = NOT -WRCRTC (IC21C): E is high for the whole -MRW time of a write to 7800/7801, and in no other cycle. RS and -CS are steady well before E rises and after it falls, and the 6845 never drives the bus. As first drawn, E was TPB inside -MRW: as little as 75 ns at 2 MHz with the 1802's strobe delays at their limits, against the 220 ns the part needs. Now E is 2 T long, and even a 1 MHz HD6845 meets the bus timing. The cost is that R14–R17 cannot be read back. `DESIGN.md` section 4 has the margins and the other ways that were weighed.

**Bus pull-ups.** RN2 puts 10k on -EF, -VMA and -RESET: the 2009 backplane has none, and they are harmless beside the bus Rev D's.

## The video side

1. **Clocks.** Y1 and IC16 make the 12 MHz dot clock. IC15 loads 8 at every carry and counts 8–15: a character every 8 dots, a 1.5 MHz character clock, as on the 6845 card. Its QC clocks the 6845; CHARCLOCK = NOT RCO. It must be a 74F163A or 74ALS163B, for CHARCLOCK's set-up to the shifter.
2. **Fetch and latch.** The 6845's MA0–MA11 address the IDT7134's left port. IC11 latches character bits 0–6 at CHARCLOCK onto the ROM's A3–A9.
3. **Character ROM.** IC12: address = code × 8 + RA0–RA2, A10–A12 low, so the font fills the first 1K. All eight data bits are dots, bit 7 leftmost.
4. **Shifter.** IC13 loads the dots at CHARCLOCK and shifts them out at the dot clock.
5. **Reverse and cursor.** IC22A XORs character bit 7 with the 6845's CURSOR. IC14 delays that, and DE, by two characters to line up with the dots, and IC22B XORs it into them.
6. **Combine.** The text dots pass while TEXT-ON is high (IC19A). With GDOT, the graphics dots from GFX: dot = text OR graphics, or text XOR graphics when XORM is 1 (IC20A, IC21A/B), blanked outside the delayed DE. Alone, TEXT's RN2 holds TEXT-ON high and RN3 holds GDOT and XORM low: plain text.
7. **Outputs.** IC23 (open collector) drives the video and both syncs. R5 pulls the sync node up and R4 joins the video to it: composite on J2. The DE-9, J3, carries TTL signals: pins 1 and 2 GND, 7 video, 8 HSYNC, 9 VSYNC through JP2.

## Display formats

The MONITOR jumper (status bit 4) tells software which table to load:

| | NTSC | IBM 5151 |
|---|---|---|
| Text; graphics with GFX | 64 × 25; 512 × 200 | 64 × 32; 512 × 256 |
| R0–R9 | 94, 64, 76, 8, 31, 6, 25, 28, 0, 7 | 80, 64, 68, 10, 45, 2, 32, 39, 0, 7 |

The NTSC values are a first cut: R2 and R3 are to be set on the bench. R12/R13 stay 0, since the graphics layer assumes MA = 64 × row + column.

## The keyboard

IC10, an ATmega328P with the Arduino Uno bootloader, runs `embedded/video-g-ps2` in keyboard mode (PD7 open). It puts each key on MD0–MD7 and pulses LDDATA, which clocks IC9 and sets **KEY-READY** (IC24B). A read of 7802 gives the key and clears KEY-READY at TPB (IC20C, IC19B); -RESET clears it too. The firmware loads the next key no sooner than 1 ms after the clear.

KEY-READY is status bit 0, and it also pulls a bus flag line low through IC23D (open collector): JP3 picks which. The VIDEO-G HBIOS polls the status bit, so it works with either CPU card.

The codes are those the old PAK-VI keyboard sent: ASCII with Enter 0D, Backspace 08, Esc 1B; F1–F12 80–8B; editing and arrow keys 90–9A (the firmware's README has the table). The bus -RESET resets the ATmega (IC18B, IC23E/F), and the keyboard is ready about 1.5 s later.

## Jumpers, LED and connectors

| Ref | Silk | Setting |
|---|---|---|
| SV1 | `ADDRESS BLOCK`, `SHUNT = 0`, `A15 ONLY = 7000`, A15–A12 over the pairs | one shunt on A15: 7000 |
| JP1 | `MONITOR`, `NTSC` / `5151` at its ends | 1-2 (or open) NTSC; 2-3 IBM 5151 |
| JP2 | `VSYNC`, `+` / `-` | DE-9 pin 9: + for TV-rate monitors, - for the 5151 |
| JP3 | `KBD FLAG`, `-EF1 -EF2 -EF3 -EF` | one shunt, set to -EF; none leaves all four alone |
| LED1 | `PWR` | +5 V through R6 |

J2, J3 (the DE-9) and J4 (KEYBOARD) are on the front edge. J6 is on the side edge, 78–138 mm from the bus edge (its pins 83.6–131.9 mm), level with GFX's J4.

## The ribbon

J6 joins GFX's J4 pin for pin by a straight 40-way cable; `hardware/video-g/kicad/common/ribbon.py` is the map both netlists import. Each fast clock has a ground on each side.

| Pins | Signal | Direction |
|---|---|---|
| 1, 16, 18, 20, 22, 25, 32, 34, 37–40 | GND | |
| 2–12, 13–15 | MA0–MA10, RA0–RA2 | to GFX |
| 17, 19, 21 | DOTCLK, CHARCLK, QC (33 Ω series, R11–R13) | to GFX |
| 23, 24 | QCR = QC OR RCO (mux select), WEPH = QA XOR QB (write phase) | to GFX |
| 26, 29, 30, 31 | -WRCTL, WSEL, -WRY, -RDMOUSE | to GFX |
| 27, 28 | TEXT-ON (pulled up here), XORM (pulled down) | from GFX |
| 33, 35, 36 | GDOT, MOUSE-READY, GFX-PRESENT (pulled down) | from GFX |

## Firmware

The character ROM is `firmware/video-g-chargen/video-g-chargen.bin`: the 6845 card's 5 × 7 font with lower case, centred in 8-dot cells (its README has the T48 command). The keyboard sketch, `embedded/video-g-ps2`, serves both boards; it compiles with arduino-cli, `sim/run.sh` runs its host simulation, and an FTDI cable on J5 loads it. The VIDEO-G HBIOS, `firmware/hbios/video-g` (on v1.0.8, built by its `build.py`, not burned), loads the NTSC table, writes 00 to the control register and reads keys at 7802; the 5151 table is not written.

## Testing

In `software/s5emu`: `python3 -m s5emu --video g` models the card behaviourally (`--monitor mda`, `--no-gfx`; tests `tests/test_videog.py`). `python3 -m s5emu --hw --video g` runs TEXT and GFX from their netlists, each memory cycle in the 1802's order (`s5emu/hwvideog.py`, `--kbd-flag` for JP3); `tests/test_hw_videog.py` decodes every address, every SV1 setting and TEXT alone, and boots Elf/OS 5.1.1. `python3 -m s5emu.timing_videog` and `tests/test_hw_videogbus.py` check the 6845's bus timing. The board's `tests =` line in `pcb-check.ini` runs `tests.test_videog`, `tests.test_hw_videogbus`, the `Card` class of `tests.test_hw_videog` (not its Elf/OS run) and GBASIC's tests.

## Known points

- **Nothing of it has run on hardware.** The board, the keyboard firmware, the character ROM and the VIDEO-G HBIOS have run only in the emulators and simulations, which do not draw the picture's timing.
- The key latch is enabled briefly early in reads at 7Axx and 7Bxx, while A0–A7 still carry the high byte. Nothing else drives then and KEY-READY is not cleared (`DESIGN.md` section 10).
- A Motorola 6845 allows E high for 25 µs at most, which a paused or stepped CPU exceeds; a Hitachi part has no limit (`hardware/TIMING-REVIEW.md`).
