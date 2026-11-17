# HBIOS v1.0.7

HBIOS v1.0.6 (the machine's ROM since 2026-11-15) plus one routine, made 2026-11-17 (Ken): **`@F1E0` shows the code
of each key pressed**, on the screen. Built and tried in the emulator, and **burned 2026-11-17** on an M2732A
(below); not yet in the machine, which runs v1.0.6.

## @F1E0

At the monitor's `test>` prompt type `@F1E0`. From then on, until Reset:

1. wait for the keyboard's flag (EF3: the keyboard port's 1852 holds a key);
2. read the key (`INP 1`);
3. write its code as text, `0x` and two hex digits, at the start of the bottom line, over the one before: the key `1`
   shows `0x31`, `"` shows `0x22`, Esc `0x1B`.

It shows what the keyboard really sends, all 8 bits: the PAK-VI's ASCII, its 80-8B (F1-F12) and 90-9A (arrows and
editing keys), and +40 with Shift.

**Self-contained** (Ken): it calls nothing in the BIOS or HBIOS. It writes the text straight into the 6845's video RAM
(73C0, the bottom line, where the monitor leaves the cursor after the command's Enter) and, once at the start, moves
the CRTC's cursor after it (its low register, R15, to C4). Nothing else on the screen changes. The monitor's `@`
starts it with P = 0 and X = 0, so R0 is its program counter; R7 points at 00F0 (the monitor's workspace) for `INP`,
R8 at the CRTC and then at the screen.

`F1E0-F1E2` is `LBR FC50`; the routine is at `FC50-FC91` (66 bytes, free in the BIOS, after v1.0.6's LBA code at
FC31-FC44), all assembled from `sec1.asm`:

| At | | |
|---|---|---|
| FC50 | `LDI 78h` `PHI R8` `LDI 00` `PLO R8` | R8 = 7800, the CRTC's address register |
| FC56 | `LDI 0Fh` `STR R8` `INC R8` `LDI C4h` `STR R8` | the cursor (R15) after the text |
| FC5D | `LDI 00` `PHI R7` `LDI F0h` `PLO R7` `SEX R7` | R7 = 00F0, X = R7 |
| FC64 | `BN3 FC64` | wait for the keyboard's flag |
| FC66 | `INP 1` | the key to M(R7) and D |
| FC67 | `LDI 73h` `PHI R8` `LDI C0h` `PLO R8` | R8 = 73C0, the bottom line |
| FC6D | `LDI '0'` `STR R8` `INC R8` `LDI 'x'` `STR R8` `INC R8` | `0x` |
| FC75 | `LDN R7` `SHR` x4, then `SMI 0Ah` `BNF` `ADI 07h` `ADI 3Ah` `STR R8` `INC R8` | the high digit |
| FC85 | `LDN R7` `ANI 0Fh`, then the same | the low digit |
| FC90 | `BR FC64` | the next key |

## The change

Those 69 bytes; everything else is v1.0.6 byte for byte (`build.py` checks it, and
`test_hbios_107_key_codes_on_screen` too). The monitor's `H` list is unchanged: a line there would change its code.
`sec1.rom` md5 `4edfb15b1a75940791eadc16bc032874`.

A first v1.0.7 the same morning sent each key to a hex display on port 4 instead (14 bytes at F1E0-F1ED), and was
burned on a 2732A; there is no hex display on the machine (Ken), so it was replaced by this one and that chip erased.

## Build

    python3 firmware/hbios/v1.0.7/build.py

writes `sec1.lst`, `sec1.img`, `sec1.hex` and `sec1.rom` here, and `software/s5emu/roms/hbios-1.0.7.rom` (+ `.hex`).
`sec1.rom` is the 4K image for the CPU card's 2732, programmed at offset 0 (= F000).

## In the emulator

    S5_ROM=software/s5emu/roms/hbios-1.0.7.rom software/s5emu/web-start.sh

then `@F1E0` at `test>`. (The emulator's keyboard sends 7-bit ASCII; on the machine all 8 bits arrive.) The emulator
still starts with v1.0.6, the machine's ROM, by default.

## Burning

As v1.0.6 (2732A-type, `firmware/hbios/v1.0.6/README.md` and `CLAUDE.md`'s EPROM programmer notes): on a blank
2732A, `minipro -p "MBM2732A@DIP24" --vpp 21 --pulse 50000 --vdd 5 -w firmware/hbios/v1.0.7/sec1.rom`, then verify at
4.5 and 5.5 V. Read the chip first: it must be blank (all FF), and sit where a chip that read correctly sat (a chip
shifted in the socket also reads FF, and the T48 cannot contact-test this part).

Done 2026-11-17 on an M2732A, with the MBM2732A settings above (minipro's own `M2732A@DIP24` entry says 18 V and
500 us and lists only the TL866A/CS; the part's 21 V and 50 ms worked): written, verified at 4.5 V and 5.5 V, and
read back identical to `sec1.rom`. A blank MBM2732A tried first took nothing at 0000 (it read FF after the first
byte's pulses: the symptom of a chip not seated right, 2026-11-15) and was not tried again.
