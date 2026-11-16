# HBIOS v1.0.6

HBIOS v1.0.5 (the monitor commands H, B, D, Q1 / Q0 and the IO panel demo) with the disk calls always in LBA mode,
made 2026-11-15 so that Elf/OS v5 runs on the real machine. **Burned the same day** on a Fujitsu MBM2732A and in the
CPU card since: Elf/OS 5.1.1 boots from the 16 MB card and every command tried works, MINIMON and Rc/Basic Level 2
included (Ken). The v1.0.5 and v1.0.4 chips are spares.

## Why

`f_ideread` (FB72) and `f_idewrt` (FB33) load the drive's registers in one routine at FBC1, which writes R8.1, as
the caller gives it, to the drive/head register (6). ELF/OS 0.2.6, the boot loaders and HBIOS's own `f_boot` pass
E0h there (LBA mode, drive 0). Elf/OS v5 passes 00h: Mike Riley's later BIOS sets LBA mode itself, and the older
BIOS 1.0.4 that HBIOS is built on does not. With bit 6 clear a real card reads the address as cylinder, head and
sector; the kernel's first read, "sector 0", is no sector at all (CHS sectors start at 1), the card answers with an
error, HBIOS refuses every disk call after that (its ready check sees the error bit), and v5 hangs after its kernel
is loaded, before its first message. That is what the real machine did on 2026-11-15, with 5.0.2 and 5.1.1 alike.

The emulator booted v5 all along: s5emu's IDE model ignored bit 6. Since the same day it honours it, as the real card
does (`software/s5emu/s5emu/machine.py`, `IDE`: CHS in the geometry it reports, and ERR with ID not found for an
address off the card, for a write as for a read). Now v5 hangs in the emulator on 1.0.4 and 1.0.5 as on the machine,
and boots on 1.0.6; ELF/OS 0.2.6 boots on all three (`software/s5emu/tests/test_machine.py`:
`test_elfos_v5_boots_from_disk`, and `test_hbios_106_reads_in_lba_mode`, which needs no private image).

## The change

26 bytes differ from v1.0.5; everything else is v1.0.5 byte for byte. The routine pushes register/value pairs on the
stack and then sends them; R8.1 is pushed twice (for register 6 first, to select the drive, and again just before
the command). Both copies get E0h ORed in; the caller's R8 is not changed. Bits 0-4 (LBA 24-27 and the drive) pass
through.

| At | Was | Now |
|---|---|---|
| FBC1-FBC3 | `STXD` / `LDI 07h` | `LBR FC31` |
| FBDF-FBE1 | `GHI R8` / `STXD` / `LDI` | `LBR FC3C` |
| FC31-FC44 (free in v1.0.5) | FF | `STXD`, `LDI 07h`, `STXD`, `GHI R8`, `ORI 0E0h`, `STXD`, `LBR FBC7`; `GHI R8`, `ORI 0E0h`, `STXD`, `LDI 06h`, `LBR FBE3` |

Nothing branches into the bytes the two LBRs replace (checked across the ROM). FBC1 is called only from FB3E (write)
and FB7D (read).

## Build

    python3 firmware/hbios/v1.0.6/build.py

`sec1.asm` is v1.0.5's, unchanged. `build.py` is v1.0.5's plus the patch above: it checks every patched byte for the
value it replaces and refuses any other difference from v1.0.4. It writes `sec1.lst`, `sec1.img`, `sec1.hex`,
`sec1.rom` (4096 bytes, F000-FFFF, md5 `4ecfeb80ee772857e0084eaa7c794087`) here, and
`software/s5emu/roms/hbios-1.0.6.rom` (+ `.hex`) for the emulator.

## Tested

In s5emu on 2026-11-15, with the card model that honours the LBA bit: Elf/OS 5.1.1 boots and runs `ver`, `free`,
`dir`, `mkdir`, `copy`, `del` and `rmdir` with no card error; the 5.0.2 card made by the v5 install ROM boots; a
fresh install from that ROM boots; ELF/OS 0.2.6 boots. On HBIOS 1.0.5 the same v5 cards hang after one card error.

## Burning it (Ken, at the T48)

As v1.0.5 (its README): a blank or UV-erased 2732A, seated exactly as a chip that reads correctly (a chip shifted in
the socket reads a steady FF, as if blank, and takes nothing; one turned round makes the T48 report
"Overcurrent protection!"), then

    minipro -p "MBM2732A@DIP24" -b
    minipro -p "MBM2732A@DIP24" --vpp 21 --pulse 50000 --vdd 5 -w firmware/hbios/v1.0.6/sec1.rom
    minipro -p "MBM2732A@DIP24" --vcc 4.5 -m firmware/hbios/v1.0.6/sec1.rom          # and again with --vcc 5.5

The write takes about 7 minutes. The chip burned on 2026-11-15 read back as the md5 above and verified at 4.5, 5
and 5.5 V.
