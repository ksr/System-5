#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-01
"""Build the VIDEO-G HBIOS ROM, as the Makefile does but with tools/asm1802.py in place of rcasm.

  python3 firmware/hbios/video-g/build.py

cpp -P sec1.asm (BIOS and VIDEOLOWER defined in the source), assemble, then merge with Mike Riley's BIOS 1.0.4 as
built for System-5 (../v1.0.4/orig_bios/bios.img, unchanged) and fill F000-FFFF with FF. Writes sec1.lst, sec1.img
(this part only), sec1.hex and sec1.rom (4096 bytes, F000-FFFF) here, and copies the ROM to
software/s5emu/roms/hbios-video-g.rom (+ .hex) for the emulator's --video g.
rcasm gives the same bytes (checked 2026-11-01 with rcasm built from ../private-resources/elf/software/rcasm-mac-build/rcasm.tgz).

2026-11-17: VIDEO-G memory-mapped (sec1.asm's header), and v1.0.6's disk fix: the routine at FBC1 sent the caller's
R8.1 to the drive/head register, which Elf/OS v5 passes as 00 (a CHS address the card refuses); the same 26 bytes as
firmware/hbios/v1.0.6/build.py (LBR FC31 at FBC1, LBR FC3C at FBDF, the code at FC31-FC44), each checked for the
byte it replaces.
"""
import os, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools")); sys.path.insert(0, os.path.join(ROOT, "software", "s5emu"))
import asm1802
from s5emu.machine import load_image


# v1.0.6's disk fix (firmware/hbios/v1.0.6/build.py): address -> (the byte there in v1.0.4, the new byte)
LBA = {0xFBC1: (0x73, 0xC0), 0xFBC2: (0xF8, 0xFC), 0xFBC3: (0x07, 0x31),      # LBR FC31 (was STXD; LDI 07h)
       0xFBDF: (0x98, 0xC0), 0xFBE0: (0x73, 0xFC), 0xFBE1: (0xF8, 0x3C)}      # LBR FC3C (was GHI R8; STXD; LDI)
LBA_CODE = (0xFC31, bytes([0x73, 0xF8, 0x07, 0x73, 0x98, 0xF9, 0xE0, 0x73, 0xC0, 0xFB, 0xC7,
                           0x98, 0xF9, 0xE0, 0x73, 0xF8, 0x06, 0xC0, 0xFB, 0xE3]))


def main():
    pre = subprocess.run(["cpp", "-P", os.path.join(HERE, "sec1.asm")], capture_output=True, text=True)
    if pre.returncode: print(pre.stderr); return 1
    tmp = os.path.join(tempfile.gettempdir(), "hbios-video-g-temp.asm")
    open(tmp, "w").write(pre.stdout)
    a = asm1802.assemble_file(tmp); os.remove(tmp)
    if a.errors: print("\n".join(a.errors)); return 1
    open(os.path.join(HERE, "sec1.lst"), "w").write(a.listing())
    mem = a.image()
    open(os.path.join(HERE, "sec1.img"), "w").write(asm1802.to_intel_hex(mem))
    rom = bytearray(b"\xff" * 4096)
    for ad, b in load_image(os.path.join(ROOT, "firmware/hbios/v1.0.4/orig_bios/bios.img")).items():
        if 0xF000 <= ad <= 0xFFFF: rom[ad - 0xF000] = b
    for ad, b in mem.items():
        if not 0xF000 <= ad <= 0xFFFF: print("HBIOS byte outside F000-FFFF at %04X" % ad); return 1
        if rom[ad - 0xF000] != 0xFF: print("HBIOS overlaps the BIOS at %04X" % ad); return 1
        rom[ad - 0xF000] = b
    for ad, (old, new) in list(LBA.items()) + [(LBA_CODE[0] + i, (0xFF, b)) for i, b in enumerate(LBA_CODE[1])]:
        if rom[ad - 0xF000] != old:
            print("LBA patch: %04X holds %02X, expected %02X" % (ad, rom[ad - 0xF000], old)); return 1
        rom[ad - 0xF000] = new
    full = {0xF000 + i: b for i, b in enumerate(rom)}
    open(os.path.join(HERE, "sec1.rom"), "wb").write(rom)
    open(os.path.join(HERE, "sec1.hex"), "w").write(asm1802.to_intel_hex(full))
    emu = os.path.join(ROOT, "software/s5emu/roms/hbios-video-g")
    open(emu + ".rom", "wb").write(rom); open(emu + ".hex", "w").write(asm1802.to_intel_hex(full))
    print("HBIOS (VIDEO-G) %d bytes at F000-F3FF + BIOS 1.0.4 + v1.0.6's LBA fix -> sec1.rom, %s.rom" % (len(mem), os.path.relpath(emu, ROOT)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
