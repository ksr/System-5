# HBIOS for VIDEO-G 1.0

HBIOS for the VIDEO-G card (`hardware/video-g/DESIGN.md`): made 2026-11-01 from v1.0.4 for the emulator
(`python3 -m s5emu --video g`), and **on v1.0.8 since 2026-11-20** (Ken: "a VIDEO-G HBIOS built on v1.0.8"), which
makes it the ROM for the new card set: CPU Rev D, the IO panel and VIDEO-G. **Not burned; VIDEO-G is not built yet.**
It is also the ROM for the 6845 card **Rev B-Clean-Keyboard** (`hardware/video-6845/kicad/rev-b-clean-keyboard`,
2026-11-20, not built), which has its key and status where VIDEO-G has them (7802, 7804) and whose 6845 takes this
ROM's 64 x 25 table as it is (a 1.5 MHz character clock and eight lines a row on both cards): in both emulators the
monitor and Elf/OS 5.1.1 run on it (`software/s5emu/tests/test_hw_videokbd.py`).
`firmware/hbios/v1.0.4/` and `v1.0.8/` are unchanged.

## On v1.0.8 (2026-11-20)

Until then this ROM was v1.0.4 with the VIDEO-G driver and the disk fix: no clock driver, so Elf/OS's `sysinfo` said
`RTC : No` with the IO panel fitted, and none of the monitor's added commands (Elf/OS booted with `@FF00`). Now it has
what `firmware/hbios/v1.0.8/` has, from the same source lines:

| From | What | Where in this ROM |
|---|---|---|
| v1.0.5 | the monitor's `H`, `B`, `D start:end` and `Q1` / `Q0`, and the IO panel demo `@F1C0` | F20C-F7CB; the rest of the `H` list F129-F1AD; `Q` F1E3-F1FA; the demo F1C0-F1D1, where v1.0.8 has it |
| v1.0.6 | the disk calls always in LBA mode (it had this already) | FBC1, FBDF, FC31-FC44 |
| v1.0.8 | the IO panel's clock behind `f_gettod` and `f_settod`; `f_getdev` says there is one | FC92-FCEB and F7CD-F7FF: v1.0.8's bytes at v1.0.8's addresses |

- **`D`'s `-- more --` key comes from VIDEO-G's keyboard**: a small routine (`rawkey`, F1AE) waits on KEY-READY at
  7804 and reads the key at 7802, with no echo, where v1.0.8 waits on EF3 and reads port 1.
- **Not here: v1.0.7's key codes at `@F1E0`.** That routine is written for the 6845 card and the old keyboard port.
  `@F1E0` restarts HBIOS in this ROM, so that typing it from habit does no harm.
- **The line feed's copy is smaller and a little slower**, to make room: twelve bytes a pass of a loop (69 bytes of
  code at FC45, after the disk fix) where it was a whole row unrolled (226 bytes at F300). A line feed takes 49.7 ms
  at 1.76 MHz (it was 47; 43.7 at CPU Rev D's 2 MHz).
- **The pieces sit in the EPROM's free runs**, with little to spare: the driver F000-F0D6, `brk` after it
  (F0D7-F0FB), `inchar` at F100. 267 of the 4096 bytes are still FF, in runs of 25 or fewer. `build.py` stops if a
  piece runs into the next one, and checks that the clock driver, the panel demo and the disk fix are v1.0.8's bytes.

Tried in the emulator (`software/s5emu/tests/test_newset.py`, `Rom` and `System`): `H`, `Q1` / `Q0`, `D` against the
emulator's own disassembler for every opcode, the panel demo, `B`; Elf/OS 5.1.1's `sysinfo` says
`RTC : Yes (11/20/2026 09:30:00)` and its `date` sets the clock. The 18 VIDEO-G tests and GBASIC's 35 pass as before.

**2026-11-17: VIDEO-G is memory-mapped** (Ken; DESIGN.md section 3): no I/O ports. The 6845 is back at 7800/7801, as
on the 6845 card; the key is read at 7802 and KEY-READY polled in the status register (7804 bit 0) instead of EF3, so
the ROM works with either CPU card (CPU Rev D takes the bus -EF on EF4); the control register is written at 7804.
`inchar` and `brk` keep every register but D. `build.py` also gives it v1.0.6's disk fix (LBA mode at FBC1, FBDF and
FC31-FC44, byte for byte), without which Elf/OS v5 hangs on the real card.

## What changed from v1.0.4

Only the video driver in `sec1.asm`; Mike Riley's BIOS is v1.0.4's `orig_bios/bios.img`, used as it is.

| | v1.0.4 (6845 card) | VIDEO-G |
|---|---|---|
| 6845 registers | memory 7800 (address) / 7801 (data) | the same (memory-mapped VIDEO-G, 2026-11-17; from 2026-11-01 to 11-17 it used OUT 5 / OUT 6) |
| Table (R0-R9) | 94, 64, 77, 8, 28, 2, 16, 22, 0, 8 (64 x 16, 9 lines) | **94, 64, 76, 8, 31, 6, 25, 28, 0, 7** (64 x 25 NTSC, 8 x 8 cells; DESIGN.md section 2) |
| Cursor (R10/R11) | rows 0-8, blinking | rows 0-7, blinking |
| Bottom row (CR goes there) | row 15, 73C0 | **row 24, 7600** |
| Control register | - | **7804 = 00** at start: text on, graphics, XOR and mouse off, page 0 (the register is on the GFX board since 2026-11-02) |
| Keyboard | INP 1, waiting on EF3 | the key at **7802**, waiting on **KEY-READY (7804 bit 0)**; RF kept on the stack (2026-11-17) |
| Disk calls | LBA mode only when the caller asks | **always LBA mode**: v1.0.6's fix (2026-11-17) |
| Line feed | copies all of 7040-77FF, blanks 73C0-77FF: **168 ms** at 1.76 MHz | copies rows 1-24 only (twelve bytes a pass of a loop at FC45; until 2026-11-20 a row unrolled at F300, 47 ms) and blanks row 24: **50 ms** |
| R14/R15 (cursor) | RC's high byte AND 3F (0x33C0 for row 15: past the 6845's 2K count) | the 6845's own address, RC - 7000 |
| Keys 80h and up | - | returned by `inchar` but **not echoed** (2026-11-02): the VIDEO-G keyboard sends F1-F12 as 80-8B and Home, Up, PgUp, Left, keypad 5, Right, End, Down, PgDn, Ins, Del as 90-9A (with Shift + 40h, C0-DA); `outchar` strips bit 7, so an echo printed junk (F9 = a backspace, F11 = a line feed) |

Unchanged: the break check (Esc; it reads the key at 7802 now), the jump table at F200 (in, out, break, cold entry),
the cursor kept in text RAM at 77FE/77FF (not on the screen at 25 rows), the minimon prompt `test>`.
The scroll is new (at FC45 since 2026-11-20; at F300-F3E1 before).

Not done: the IBM 5151 table (64 x 32, MONITOR jumper = 1). At 32 rows the text fills all of 7000-77FF, so the cursor
would have to move out of 77FE/77FF first, to another place still to be chosen: **not into the 6845's R14/R15, which cannot
be read back** (VIDEO-G TEXT's 6845 is write-only since 2026-11-24, as Rev B-Clean-Keyboard's is). And, as in v1.0.4, a
character typed past column 63 goes off the screen (HBIOS does not wrap; GBASIC wraps its own output).

## Building

```
python3 firmware/hbios/video-g/build.py
```

writes `sec1.lst`, `sec1.img` (this part), `sec1.hex` and `sec1.rom` (4096 bytes, F000-FFFF, with the BIOS) here and
copies the ROM to `software/s5emu/roms/hbios-video-g.rom`. It uses `tools/asm1802.py`, and it is the only way to
build this ROM since 2026-11-20: it also patches Mike Riley's monitor, the disk routine and the clock vectors, as
`firmware/hbios/v1.0.8/build.py` does. The `Makefile` is v1.0.4's (cpp, rcasm, srec_cat) and makes none of those
patches; it gave the same bytes as `build.py` for the 2026-11-01 ROM (checked then with rcasm built from
`../private-resources/elf/software/rcasm-mac-build/rcasm.tgz`) and is kept for the record only.

## Found while testing: ELF/OS's boot loader writes port 4 (settled 2026-11-17)

Settled by the memory-mapped card: VIDEO-G answers no port, so the loader's `OUT 4` goes to the IO panel's display,
if there is one, as on an ELF. What was found:

The boot loader in sector 0 of an ELF/OS disk (disktool's `boot[]`, written by `mkelfos.py`, SETBOOT and the
installer) shows each sector number on port 4 as it loads the kernel (`SEX 2 / GLO 7 / STR 2 / OUT 4`, the ELF
hex-display habit). On VIDEO-G that is the control register: after `@FF00` it is left at **0E** (graphics on, XOR,
page 1), so the screen shows graphics noise XORed over the text until a program writes OUT 4. Seen in the emulator.
GBASIC wrote OUT 4 = 00 when it started. The fixes weighed: patch the loader's `OUT 4` (byte 64h at offset 24h of
sector 0) to `IRX` (60h), or move VIDEO-G's control register off port 4; Ken chose to move all of VIDEO-G into memory.
