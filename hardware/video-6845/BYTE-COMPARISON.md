# The System-5 6845 card against the BYTE design

Compared 2026-10-08. The reference is "Single Chip Video Controller" by Bob Haas, BYTE, May 1979: Figure 4 (schematic), Table 2 (CRTC values) and Table 4 (parts). Ken's copy is `~/Documents/Reads & Books/https-www.worldradiohistory.com-Archive-Byte-70s-Byte-1979-05.pdf` (the same file as YACC1-D's `hardware/cards/video/docs/BYTE 6845.pdf`).
The first two tables describe Rev A, from its netlist (Rev A's Eagle files are in `eagle/rev-a/`; its KiCad conversion is in git history). Ken's working card is Rev B, which keeps all of it except the rows in the last section.

**In short:** the video side is BYTE's circuit almost gate for gate. The bus side is Ken's own: a dual-port RAM and a 1802-style decode replace BYTE's multiplexed 21L02s and 6800/6502 bus interface.

## Same as BYTE

| Function | BYTE | System-5 Rev A |
|---|---|---|
| Dot clock oscillator | 9 MHz crystal, three 7404 sections, 1 kΩ feedback resistors | the same: IC6 74LS04, Q1, R2/R3 1K |
| Character clock | 74163 counts 0-5 (÷6), reloaded from a 7400 decode | 74163 (V1) cleared by a 7400 decode (IC5C) of QA·QC: ÷6. SV3 also allows ÷7 |
| 6845 clock | the 74163's C output (high for 2 dot times) | the same (CRTCCLOCK = V1 QC) |
| Character latch | 74174, 6 bits | 74LS174 (IC10), 6 bits (VDATA0-5) |
| Character generator | 2513 (5 × 7, 64 characters; needs −5 V and −12 V) | 2732 EPROM (IC12, +5 V only), the same 64 characters × 8 rows, 5 dot outputs |
| Dot shift register | 74166, D-H from the character generator, A-C grounded | the same (IC11) |
| Two-character pipeline | 74175 delays CURSOR and DISP ENAB by two character times | the same (IC9; the photo shows a 74AS175) |
| Reverse video and cursor | 7486: data bit 7 and the cursor each invert the video | the same (IC13): bit 7 XOR cursor, delayed, then XOR the dots |
| Video output | 7416 open collectors; 33 Ω / 270 Ω mixing of video, H and V sync | the same (IC14, R5 33, R6 270) into the composite RCA jack |
| 6845 register select | RS = address line 0 | the same (RS = A0) |
| CRTC values (16 × 64) | Table 2: 94, 64, 77, 8, 28, 2, 16, 22, 0, 8, 64, 8, 0, 0 | HBIOS `vtable` loads exactly these, which assumes the 9 MHz crystal and ÷6 |

## Different from BYTE

| Function | BYTE | System-5 Rev A | Effect |
|---|---|---|---|
| Refresh RAM | 8 × 21L02-1 (1K × 1, 500 ns), shared by the CPU and the 6845 through three 74157 multiplexers and two 74LS367 buffers | one IDT7134 dual-port RAM (4K × 8, 35 ns): the 6845 reads the left port, the CPU the right | No multiplexers or buffers; the CPU can access the screen at any time, with no contention with the display |
| RAM size the 6845 sees | 1K: only 10 of 14 refresh lines are connected, so addresses wrap at 1K (the article's scrolling scheme relies on it) | 4K: MA0-MA11 reach the 7134's left port, but the CPU's right port has A11 tied low, so the CPU writes only 2K | Harmless with HBIOS, which keeps the start address at 0 and scrolls by copying. Hardware scrolling past 2K would display RAM the CPU cannot write; tying the left port's A11 low would make it wrap at 2K |
| Address decode | 74LS138s: an 8K segment, a 1K block for RAM and a whole 1K block for the 6845 | 74LS373 latch (TPA) + 74LS85 compare against SV1, gated by -VMA: a 4K block; A11 = 0 is the 2K RAM, A11 = 1 is the 6845 (mirrored) | A 1802 bus: the high address is latched on TPA |
| 6845 E, R/W | 6800/6502 φ2 and R/W | E = TPB, R/W = -MRW | See timing findings T2-T5 in `hardware/TIMING-REVIEW.md` |
| Dot clock choice | fixed 9 MHz | SV2: the crystal, or ÷2 through a 7490 (IC7) | Ken's 2005 to-do: "remove divide 6 or 7 dot clock jumper", "remove … 7490" |
| Character divider choice | fixed ÷6 | SV3: ÷6 or ÷7 | |
| 74163 power | normal | through jumpers on SV4: the library symbol's power pins are named +UB/-UB, not VCC/GND | Ken's 2005 to-do: "fix schematic 74163" |
| Character generator addressing | 2513 | 2732 with A11 tied **high** and A10, A9 low: the font must be at 800h-9FFh | Ken's 2005 to-do: "A11 should be tied low" (he fixed it with a double socket) |
| Light pen, interlace | not used | not used | |

## Jumpers for HBIOS (16 × 64, BYTE's timing)

| Header | Setting | Why |
|---|---|---|
| SV1 | 1-2 | the card at 7000 |
| SV2 | 1-2 | dot clock = the crystal (9 MHz) |
| SV3 | 1-2 | character clock ÷6 (QA), as Table 2 assumes |
| SV4 | 1-2 and 3-4 | power for the 74163 |

The crystal on Ken's card is not legible in the photos; HBIOS's values assume 9 MHz, as BYTE's do.

## Rev B (the working card) against Rev A and BYTE

Compared 2026-10-08 from the Rev B schematic as exported from Fusion (`eagle/rev-b/fusion-export/v6845-b.sch`, the newest of the seven saved Rev B versions; the website copy and the backups are earlier).
Rev B keeps everything in the tables above except the rows below. The bus side, the dual-port RAM, the 6845 hookup, the 74166/74175/7486 video path and the 33 Ω / 270 Ω composite mix are unchanged.

| Function | BYTE | Rev A | Rev B | Effect |
|---|---|---|---|---|
| Dot clock | 9 MHz crystal | crystal, or ÷2 through a 7490 (SV2) | the crystal only: IC6C's output is DOTCLOCK | Back to BYTE. The 7490 and SV2 are gone (Ken's Rev A to-do) |
| Character divider | 74163, ÷6 | 74163, ÷6 or ÷7 (SV3), powered through SV4 | **74HC160** (IC8) as drawn, CLR from the same 7400 decode of QA·QC; SV3 and SV4 gone | See the next section: as drawn this divides by 5, not 6. Ken's card has a **74LS163** fitted, which is BYTE's part and divides by 6 |
| Character code width | 6 bits (64 characters) | 6 bits | **7 bits (128 characters)**: a second 74LS174 (IC7) latches VDATA6 on CHARCLOCK, with IC10's latch, and drives the 2732's A9. Its other five flip-flops have their D inputs grounded | Upper and lower case. Bit 7 is still reverse video |
| Character generator addressing | 2513 | 2732, A11 tied high: font at 800h-9FFh | 2732, A11 and A10 tied low, A9 = bit 6: the font is 1K at 000h-3FFh, character × 8 + row | Ken's Rev A to-do ("A11 should be tied low") is fixed. `firmware/char-rom-fonts/2513_combined` (1K, the lower-case and upper-case 2513 images) is the likely image; its order against bit 6 has not been checked |
| Monitor connector | composite only | composite on the RCA jack | RCA jack, plus a DB9 (X1): pin 7 = the 7416's video output (before R5), pin 8 = the 6845's HSYNC, pin 9 = VSYNC, pin 1 = GND | Separate drive for a monitor such as the Electrohome. HSYNC and VSYNC are the 6845's own, active high, unbuffered |
| Unused gates | — | inputs left open | inputs of IC6D, IC13C/D and IC14D/E/F tied to GND | Tidier; no effect on function |

### The character divider: 74HC160 as drawn, 74LS163 as built

The decode is the same in all three designs. A 7400 gate (IC5C) NANDs the counter's QA and QC, and its output, CHARCLOCK, drives the counter's CLR.
- **74163 (BYTE, Rev A, Ken's card):** its clear is *synchronous*. When the count reaches 5, CLR goes low and the *next* dot clock loads 0. The count runs 0-5, so the divide is ÷6. CHARCLOCK is low for one dot time; CRTCCLOCK = QC is high for two dot times (counts 4 and 5).
- **74HC160 (Rev B as drawn):** its clear is *asynchronous*, like the 74161's. The moment the count reaches 5, CLR clears it to 0. Count 5 lasts only as long as the gate and counter delays (tens of ns), so the divide is ÷5.
  CHARCLOCK becomes a runt pulse that may be too short to load the 74166 and clock the 74174s and 74175. The character clock rises from 1.5 to 1.8 MHz, so HBIOS's BYTE values (94 characters per line) would give a line rate of about 19 kHz instead of 16 kHz.
  Also, a 74HC input clocked from a 74LS04 output has no guaranteed high level.
  (The 160 being a decade counter, not binary, does not matter here: the count never passes 5.)

So the 74LS163 on Ken's card is the right part, and Rev B's schematic is wrong at IC8. A probable reason: Eagle's standard library has a 74160 with normal power pins, and it is pin-compatible with the 74163. Rev A used a 74163 symbol whose power pins came out as +UB/-UB, which needed the SV4 jumpers.
Any new Rev B board should say **74LS163** at IC8 (Rev B-Clean does). An HCT part (74HCT163) also works, but it must be a '163.
