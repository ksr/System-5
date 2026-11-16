# HBIOS v1.0.5

HBIOS v1.0.4 plus four monitor commands and an IO panel demo, made 2026-11-12. **Burned 2026-11-15** on a Fujitsu
MBM2732A and booted on System-5 (Ken); the v1.0.4 chip (`hardware/cpu/eagle/rev-a/rom/`) is kept as the spare.
Tested in the emulator first. **Replaced in the machine the same evening by v1.0.6** (`../v1.0.6/`), which adds the
disk calls in LBA mode that Elf/OS v5 needs; this chip is now a spare.

| Command | Does |
|---|---|
| `H` | lists the monitor's commands |
| `B` | boots the OS from the CF card, as `@FF00` |
| `D start:end` | disassembles from `start` to `end`, 14 lines a screen: at `-- more --` any key goes on, and Esc, Q or Ctrl-C stops. `D start` alone shows one screenful. The range can be written `D F000:F020`, `DF000:F020`, `D F000-F020` or `D F000 F020` |
| `Q1` / `Q0` | turns the 1802's Q output on (`SEQ`, 7B) / off (`REQ`, 7A); any number but 0 is on |
| `@F1C0` | the IO panel demo: over and over, reads the toggles (`INP 4`), shows them on the LEDs (`OUT 4`), and sets Q while INPUT (EF1) is held. Reset ends it. It keeps one byte at 00F0 for `INP` / `OUT` (the monitor's workspace) |

Lower case works too (`h`, `b`, `d`, `q1`). The monitor's own commands are unchanged: `?addr`, `!addr bb bb ..`,
`=src dst count`, `@addr`; anything else still just gives the prompt again.

## How it is done

Mike Riley's monitor (F900, in his BIOS) reads a line, keeps the first character in RC.1 and the hex number after it
in RA, and checks for `!`, `=`, `?` and `@`. For anything else it branches back to its prompt (F940: `BNZ F913`).
`build.py` points that branch at F9EB, free bytes on the same page, and puts `LBR monext` there. `monext`, at the
end of `sec1.asm` in the free space after F20C, handles `H`, `B`, `D` and `Q` and goes back to the prompt for anything else. F200-F7FF is nearly full, so `Q` and
the last two lines of the `H` list are in the other free block of HBIOS's half, at F11C after the keyboard code;
`H` types its list in two parts.

`D` builds each line in the monitor's input buffer (0003) and types it with `f_msg`: the address and the bytes with
Mike's `f_hexout4` / `f_hexout2`, the mnemonic from five small tables. The lines read exactly as the emulator's
disassembler writes them (`software/s5emu/s5emu/disasm.py`, `CALL` and `RETN` for the SCRT calls included), so the
two can be compared line for line. The pause waits for a key itself (port 1, not echoed).

| | Bytes |
|---|---|
| New code, the help text and the disassembler's tables | F20C-F7CC (1,473 bytes; the disassembler is about 1,050 of them) and F11C-F19F (`Q` and the end of the `H` list), F1C0-F1D1 (the panel demo, 18 bytes) |
| The hook in the BIOS | F941 (13 -> EB), F9EB-F9ED (`C0 F2 0C`) |
| Everything else | as v1.0.4, byte for byte: `build.py` refuses to write the ROM otherwise, and the new code may only fill bytes v1.0.4 leaves empty (FF) |
| Still free | about 540 bytes: F1D2-F1FF (46), F1A0-F1BF (32), F7CD-F7FF (51), F0EC-F0FF (20), and about 300 in small gaps in Mike's BIOS |

## Build

    python3 firmware/hbios/v1.0.5/build.py

It assembles `sec1.asm` with `tools/asm1802.py` (which rebuilds v1.0.4 with 0 bytes different), merges Mike's BIOS
as v1.0.4 uses it (`../v1.0.4/orig_bios/bios.img`), adds the hook, and writes `sec1.rom` (4096 bytes, F000-FFFF),
`sec1.hex`, `sec1.lst` and `sec1.img` here, and `software/s5emu/roms/hbios-1.0.5.rom` for the emulator.

## Try it

In the emulator: `python3 -m s5emu --rom roms/hbios-1.0.5.rom` in `software/s5emu`, or in the browser
`S5_ROM=software/s5emu/roms/hbios-1.0.5.rom software/s5emu/web-start.sh` (also in a Codespace). Tests:
`tests/test_machine.py` (`test_hbios_105_*`: H, Q1 / Q0, the panel demo, B, the four old commands, every opcode through `D`, the stop key, one
screenful, and that only the new code and the hook differ from v1.0.4). `check_disasm.py` here runs `D F000:FFFF`
through all its pauses and compares every line with the emulator's disassembler, with the other forms and keys
(about 7 minutes).

## Burning it (Ken, at the T48)

The ROM is a 2732A at F000. Use a blank or UV-erased chip. minipro's own settings for 2732A parts (18 V, 200 us
pulses) are too weak; what worked on 2026-11-15, on a Fujitsu MBM2732A (the write takes about 7 minutes):

    minipro -p "MBM2732A@DIP24" -b                                                   # blank?
    minipro -p "MBM2732A@DIP24" --vpp 21 --pulse 50000 --vdd 5 -w firmware/hbios/v1.0.5/sec1.rom
    minipro -p "MBM2732A@DIP24" --vcc 4.5 -m firmware/hbios/v1.0.5/sec1.rom          # and again with --vcc 5.5

The chip then reads md5 `d9ba51e245b1be4b118f4c4c9986a8c8`, the same as `sec1.rom`. A National NMC27C32Q (no B) took
not one bit at 18 V or 21 V: it seems to need 25 V, more than minipro offers. Keep the v1.0.4 chip as the spare.
