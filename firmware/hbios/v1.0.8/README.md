# HBIOS v1.0.8

HBIOS v1.0.7 (v1.0.6, the machine's ROM since 2026-11-15, plus `@F1E0`) with a driver for the **IO panel card's
real-time clock** behind the BIOS calls ELF/OS already makes (Ken, 2026-11-18: "rtc as planned"). Built and tried in
the emulator only; **not burned**: the IO panel card is not built yet (`hardware/io-panel/kicad/rev-a/DESIGN.md`).

## The clock

The IO panel's DS12885 answers on two ports, as the card's JP4 is set (6 and 7): `OUT 6` latches a register number
(the chip's AS), `OUT 7` writes that register, `INP 7` reads it.

| Call | v1.0.4-v1.0.7 | v1.0.8 |
|---|---|---|
| `f_gettod` (F815) | `LBR F9E8`: the BIOS's error return (DF = 1) | `LBR FC92`: read the clock |
| `f_settod` (F818) | `LBR F9E8` | `LBR F7CD`: set the clock |
| `f_getdev` (FF81 → FEDB) | 0005h | 0015h: bit 4, an RTC |

The calls are Mike Riley's, answered as his BIOS answers them for the ELF2000's DS1287 (`v1.0.4/orig_bios/bios.asm`,
`e2k_gtod` / `e2k_stod`):

- **RF** points at six bytes: **month, day, year, hour, minute, second**, binary. The year is ELF/OS's, years since
  1972, kept in the clock's year register as it is: 28 years is a whole number of leap cycles, so the clock's leap
  years stay right (2026 is 54).
- **f_gettod** first checks that the clock runs (register A's DV bits 010) in binary 24-hour mode (register B's DM and
  24/12 bits), then waits while an update is in progress (UIP), then reads the six registers into the buffer. DF = 0:
  done, RF after the six bytes. DF = 1, D = 1: the clock is not set, or not there at all (an `INP` of a port nobody
  drives reads FF, which does not pass the check). ELF/OS then uses the date it keeps itself, as before.
- **f_settod** starts the oscillator (register A = 20h: DV 010, no square wave; a new DS12885 comes with it off),
  stops the count (register B = 86h: SET, binary, 24-hour), writes the six registers, and lets it count (register B =
  06h). Daylight saving is off (Mike's sets it on; the chip knows only the old US rules).
- Called through SCRT (R4 / R5), so X = 2 and R2 is the stack: each byte goes out from M(R2) (`STR R2`, `OUT n`,
  `DEC R2`). Only D, DF and RF change.

ELF/OS 0.2.6's kernel calls `f_getdev`, and `f_gettod` when bit 4 is set, for the date it puts on a file it writes
(`gettmdt` in Mike's kernel source).

## The change

All in `sec1.asm` (at the end), assembled by `build.py`:

| At | |
|---|---|
| FC92-FCDC | `f_gettod`: the checks, the UIP wait, the six reads |
| FCDD-FCE2 | `rtcrd`: D = the register named by the byte after the call (`OUT 6`, `INP 7`) |
| FCE3-FCEB | `rtcwr`: D into that register (`OUT 6`, `OUT 7`) |
| F7CD-F7FF | `f_settod` (51 bytes, which fill that free run) |
| F816-F817, F819-F81A | the two jumps |
| FEDC | `f_getdev`'s `LDI 05h` becomes `LDI 15h` |

Everything else is v1.0.7 byte for byte; `build.py` checks it, and that each patched byte held what it replaces.
`sec1.rom` md5 `374c4bd5b30fc5d26121ef1f11c410c5`.

## Build

    python3 firmware/hbios/v1.0.8/build.py

writes `sec1.lst`, `sec1.img`, `sec1.hex` and `sec1.rom` here, and `software/s5emu/roms/hbios-1.0.8.rom` (+ `.hex`).

## Tests (`software/s5emu`)

- `tests/test_machine.py`, `test_hbios_108_clock_on_the_io_panel`: on the fast machine with the IO panel's clock
  (`s5emu/rtc.py`): a new chip reads as not set; `f_settod` starts it in binary 24-hour mode; a minute later
  `f_gettod` reads the time back; `f_getdev` answers 0015h; with no IO panel, `f_gettod` returns DF = 1.
- `tests/test_hw.py`, `IOPanel.test_hbios_108_sets_and_reads_the_clock_on_the_netlist_cards`: the same from the
  netlists: CPU Rev D runs v1.0.8, whose calls reach the DS12885 through the IO panel's decoder, jumpers and gates.
- `tests/test_machine.py`, `test_elfos_v5_reads_and_sets_the_io_panels_clock` (needs the v5 image from
  private-resources): **Elf/OS v5 finds the clock**: `sysinfo` shows `RTC : Yes (11/18/2026 02:30:00)` where it said
  No; `date` prints the time; `date 12/31/2026 23:59:50` sets the clock through `f_settod` (it then holds 54 as the
  year, binary, 24-hour, running) and, 15 seconds on, `date` shows `1/1/2027 0:0:5`.
- `tests/test_hw.py`, `SystemV5` (also needs the v5 image; about 80 s): the whole machine from its netlists, CPU Rev D
  and the IO panel with the memory, 6845, IDE and IO cards: v1.0.8 boots Elf/OS v5, whose `sysinfo` finds the clock
  and whose `date` sets it through the panel's gates; no bus fights.

## In the emulator

    S5_ROM=software/s5emu/roms/hbios-1.0.8.rom software/s5emu/web-start.sh

The web emulator fits the IO panel unless `S5_PANEL=none`, and its clock starts at the host's time, as if it had been
set before. The emulator still starts with v1.0.6, the machine's ROM, by default.

## Burning

As v1.0.7, when the IO panel is built (2732A-type, `firmware/hbios/v1.0.7/README.md`).
