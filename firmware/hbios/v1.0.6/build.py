#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-15
"""Build HBIOS v1.0.6: v1.0.5 (the monitor commands H, B, D, Q1 / Q0 and the IO panel demo) plus the disk routines
always in LBA mode.

  python3 firmware/hbios/v1.0.6/build.py

Why: the routine at FBC1 that loads the drive's registers for a read (FB72) or a write (FB33) writes R8.1, as the
caller gives it, to the drive/head register (6). ELF/OS 0.2.6 and the boot loaders pass E0 (LBA mode, drive 0); the
Elf/OS v5 kernels pass 00, which a real card takes as a CHS address: its first read, "sector 0", is invalid, the card
reports an error, HBIOS refuses every call after it, and v5 hangs before its first message (found 2026-11-15 on the
real machine; s5emu's IDE model ignored bit 6, so v5 booted there). Mike Riley's later BIOS sets LBA mode itself.

The fix leaves the caller's R8 alone and ORs E0 into the two bytes the routine pushes for register 6: at FBC1 (the
first three bytes, STXD / LDI 07h, become LBR FC31) and at FBDF (GHI R8 / STXD / LDI, becomes LBR FC3C). The code at
FC31-FC44, free in the BIOS, does what the replaced bytes did, with ORI 0E0h after each GHI R8, and jumps back.
Bits 0-4 (LBA 24-27 and the drive) pass through unchanged.

Everything else is v1.0.5, built the same way (sec1.asm unchanged; the hook at F941 / F9EB-F9ED); each patched byte
is checked for the value it replaces, and the ROM for differences from v1.0.4 outside the new code, the hook and this
patch. Writes sec1.lst, sec1.img, sec1.hex and sec1.rom here, and software/s5emu/roms/hbios-1.0.6.rom (+ .hex).
"""
import os, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools")); sys.path.insert(0, os.path.join(ROOT, "software", "s5emu"))
import asm1802
from s5emu.machine import load_image

V104 = os.path.join(ROOT, "software/s5emu/roms/hbios-1.0.4.rom")    # = the T48 read of the burned EPROM

# the disk routines in LBA mode: address -> (the byte there in v1.0.5, the new byte)
LBA = {0xFBC1: (0x73, 0xC0), 0xFBC2: (0xF8, 0xFC), 0xFBC3: (0x07, 0x31),      # LBR FC31 (was STXD; LDI 07h)
       0xFBDF: (0x98, 0xC0), 0xFBE0: (0x73, 0xFC), 0xFBE1: (0xF8, 0x3C)}      # LBR FC3C (was GHI R8; STXD; LDI)
LBA_CODE = (0xFC31, bytes([
    0x73,                    # FC31 STXD          the command, as at FBC1
    0xF8, 0x07,              # FC32 LDI 07h       register 7
    0x73,                    # FC34 STXD
    0x98,                    # FC35 GHI R8        drive/head as the caller gives it
    0xF9, 0xE0,              # FC36 ORI 0E0h      LBA mode, drive 0 (bits 0-4 unchanged)
    0x73,                    # FC38 STXD
    0xC0, 0xFB, 0xC7,        # FC39 LBR FBC7      back: LDI 06h; STXD; GLO R8 ...
    0x98,                    # FC3C GHI R8        the second copy, sent first, before the other registers
    0xF9, 0xE0,              # FC3D ORI 0E0h
    0x73,                    # FC3F STXD
    0xF8, 0x06,              # FC40 LDI 06h       register 6 (the LDI the LBR at FBDF replaced)
    0xC0, 0xFB, 0xE3]))      # FC42 LBR FBE3      back: STR R2; LDI 07h; the OUT 2 / OUT 3 loop


def main():
    pre = subprocess.run(["cpp", "-P", os.path.join(HERE, "sec1.asm")], capture_output=True, text=True)
    if pre.returncode: print(pre.stderr); return 1
    tmp = os.path.join(tempfile.mkdtemp(), "hbios-1.0.6-temp.asm")
    with open(tmp, "w") as f: f.write(pre.stdout)
    a = asm1802.assemble_file(tmp); os.remove(tmp)
    if a.errors: print("\n".join(a.errors)); return 1
    with open(os.path.join(HERE, "sec1.lst"), "w") as f: f.write(a.listing())
    mem = a.image()
    with open(os.path.join(HERE, "sec1.img"), "w") as f: f.write(asm1802.to_intel_hex(mem))

    rom = bytearray(b"\xff" * 4096)
    for ad, b in load_image(os.path.join(ROOT, "firmware/hbios/v1.0.4/orig_bios/bios.img")).items():
        if 0xF000 <= ad <= 0xFFFF: rom[ad - 0xF000] = b
    for ad, b in mem.items():
        if not 0xF000 <= ad <= 0xFFFF: print("HBIOS byte outside F000-FFFF at %04X" % ad); return 1
        if rom[ad - 0xF000] != 0xFF: print("HBIOS overlaps the BIOS at %04X" % ad); return 1
        rom[ad - 0xF000] = b

    monext = a.symbols["MONEXT"]
    hook = {0xF941: (0x13, 0xEB),                       # BNZ F913 -> BNZ F9EB: an unknown command goes on to F9EB
            0xF9EB: (0xFF, 0xC0),                       # LBR monext, in bytes the BIOS leaves free
            0xF9EC: (0xFF, monext >> 8),
            0xF9ED: (0xFF, monext & 0xFF)}
    at, code = LBA_CODE
    patch = dict(hook); patch.update(LBA)
    patch.update({at + i: (0xFF, b) for i, b in enumerate(code)})
    for ad, (old, new) in patch.items():
        if rom[ad - 0xF000] != old:
            print("patch: %04X holds %02X, expected %02X - not the BIOS this was written for" % (ad, rom[ad - 0xF000], old))
            return 1
        rom[ad - 0xF000] = new

    with open(V104, "rb") as f: old = f.read()
    new_code = {ad for ad in mem if mem[ad] != old[ad - 0xF000]}
    overwritten = sorted(ad for ad in new_code if old[ad - 0xF000] != 0xFF)
    if overwritten:                                    # new code goes only where v1.0.4 has nothing (FF)
        print("new code overwrites v1.0.4's bytes at: " + " ".join("%04X" % x for x in overwritten[:16]))
        return 1
    unexpected = [0xF000 + i for i in range(4096) if rom[i] != old[i] and 0xF000 + i not in new_code and 0xF000 + i not in patch]
    if unexpected:
        print("differs from v1.0.4 outside the new code and the patches: " + " ".join("%04X" % x for x in unexpected[:16]))
        return 1

    full = {0xF000 + i: b for i, b in enumerate(rom)}
    with open(os.path.join(HERE, "sec1.rom"), "wb") as f: f.write(rom)
    with open(os.path.join(HERE, "sec1.hex"), "w") as f: f.write(asm1802.to_intel_hex(full))
    emu = os.path.join(ROOT, "software/s5emu/roms/hbios-1.0.6")
    with open(emu + ".rom", "wb") as f: f.write(rom)
    with open(emu + ".hex", "w") as f: f.write(asm1802.to_intel_hex(full))
    blocks = []                                        # the new code as runs of addresses
    for ad in sorted(new_code):
        if blocks and ad <= blocks[-1][1] + 8: blocks[-1][1] = ad
        else: blocks.append([ad, ad])
    print("HBIOS v1.0.6: new code %s, hook at F941 and F9EB-F9ED, LBA mode at FBC1-FBC3, FBDF-FBE1 and FC31-FC44;"
          " everything else as v1.0.4" % ", ".join("%04X-%04X (%d bytes)" % (a, b, b - a + 1) for a, b in blocks))
    print("  -> %s.rom; about %d bytes of the 4096 still FF" % (os.path.relpath(emu, ROOT), rom.count(0xFF)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
