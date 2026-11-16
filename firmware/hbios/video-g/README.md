# HBIOS for VIDEO-G 1.0

A build of HBIOS v1.0.4 for the VIDEO-G card (`hardware/video-g/DESIGN.md`), made 2026-11-01 for the emulator
(`python3 -m s5emu --video g`). **Not burned; VIDEO-G is not built yet.** `firmware/hbios/v1.0.4/` is unchanged.

## What changed from v1.0.4

Only the video driver in `sec1.asm`; Mike Riley's BIOS is v1.0.4's `orig_bios/bios.img`, used as it is.

| | v1.0.4 (6845 card) | VIDEO-G |
|---|---|---|
| 6845 registers | memory 7800 (address) / 7801 (data) | **OUT 5** (address) / **OUT 6** (data): 7800-783F is now the graphics window |
| Table (R0-R9) | 94, 64, 77, 8, 28, 2, 16, 22, 0, 8 (64 x 16, 9 lines) | **94, 64, 76, 8, 31, 6, 25, 28, 0, 7** (64 x 25 NTSC, 8 x 8 cells; DESIGN.md section 2) |
| Cursor (R10/R11) | rows 0-8, blinking | rows 0-7, blinking |
| Bottom row (CR goes there) | row 15, 73C0 | **row 24, 7600** |
| Control register | - | **OUT 4 = 00** at start: text on, graphics, XOR and mouse off, page 0 (the register is on the GFX board since 2026-11-02; same port and bits) |
| Line feed | copies all of 7040-77FF, blanks 73C0-77FF: **168 ms** at 1.76 MHz | copies rows 1-24 only (an unrolled LDA/STR/INC row loop at F300) and blanks row 24: **47 ms** |
| R14/R15 (cursor) | RC's high byte AND 3F (0x33C0 for row 15: past the 6845's 2K count) | the 6845's own address, RC - 7000 |
| Keys 80h and up | - | returned by `inchar` but **not echoed** (2026-11-02): the VIDEO-G keyboard sends F1-F12 as 80-8B and Home, Up, PgUp, Left, keypad 5, Right, End, Down, PgDn, Ins, Del as 90-9A (with Shift + 40h, C0-DA); `outchar` strips bit 7, so an echo printed junk (F9 = a backspace, F11 = a line feed) |

Unchanged: the keyboard port (INP 1, EF3), the break check (Esc), the jump table at F200 (in, out, break, cold entry),
the cursor kept in text RAM at 77FE/77FF (not on the screen at 25 rows), the minimon prompt `test>`.
The section between F300 and F3E1 is new (the scroll); F000-F7FF was free in v1.0.4's ROM.

Not done: the IBM 5151 table (64 x 32, MONITOR jumper = 1). At 32 rows the text fills all of 7000-77FF, so the cursor
would have to move out of 77FE/77FF first (into the 6845: R14/R15 can be read on port 6). And, as in v1.0.4, a
character typed past column 63 goes off the screen (HBIOS does not wrap; GBASIC wraps its own output).

## Building

```
python3 firmware/hbios/video-g/build.py
```

writes `sec1.lst`, `sec1.img` (this part), `sec1.hex` and `sec1.rom` (4096 bytes, F000-FFFF, with the BIOS) here and
copies the ROM to `software/s5emu/roms/hbios-video-g.rom`. It uses `tools/asm1802.py`. The `Makefile` is v1.0.4's
(cpp, rcasm, srec_cat) with the BIOS taken from `../v1.0.4/orig_bios`; rcasm built from
`../private-resources/elf/software/rcasm-mac-build/rcasm.tgz` gives the same bytes (checked 2026-11-01). The source keeps to rcasm's syntax
(port numbers as digits, `.0`/`.1` where rcasm has no LOW/HIGH form).

## Found while testing: ELF/OS's boot loader writes port 4

The boot loader in sector 0 of an ELF/OS disk (disktool's `boot[]`, written by `mkelfos.py`, SETBOOT and the
installer) shows each sector number on port 4 as it loads the kernel (`SEX 2 / GLO 7 / STR 2 / OUT 4`, the ELF
hex-display habit). On VIDEO-G that is the control register: after `@FF00` it is left at **0E** (graphics on, XOR,
page 1), so the screen shows graphics noise XORed over the text until a program writes OUT 4. Seen in the emulator.
GBASIC writes OUT 4 = 00 when it starts. To fix it for everything: patch the loader's `OUT 4` (byte 64h at offset
24h of sector 0) to `IRX` (60h), which keeps the stack the same, or move VIDEO-G's control register off port 4.
