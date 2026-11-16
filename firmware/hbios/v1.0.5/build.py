#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-12
"""Build HBIOS v1.0.5: v1.0.4 plus the monitor commands H (list the commands) and B (boot the OS).

  python3 firmware/hbios/v1.0.5/build.py

As firmware/hbios/video-g/build.py: cpp -P sec1.asm, assemble with tools/asm1802.py, merge with Mike Riley's BIOS
as built for System-5 (../v1.0.4/orig_bios/bios.img, unchanged), fill F000-FFFF with FF. Then the hook: the monitor
goes back to its prompt for a command it does not know (F940 BNZ F913); that branch is pointed at F9EB, free in the
BIOS and on the same page, where an LBR goes on to monext in sec1.asm. Each patched byte is checked for the value it
replaces, and the finished ROM is checked against v1.0.4: nothing may differ but the new code and the hook.

Writes sec1.lst, sec1.img (this part only), sec1.hex and sec1.rom (4096 bytes, F000-FFFF) here, and copies the ROM
to software/s5emu/roms/hbios-1.0.5.rom (+ .hex) for the emulator (--rom).
"""
import os, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools")); sys.path.insert(0, os.path.join(ROOT, "software", "s5emu"))
import asm1802
from s5emu.machine import load_image

V104 = os.path.join(ROOT, "software/s5emu/roms/hbios-1.0.4.rom")    # = the T48 read of the burned EPROM


def main():
    pre = subprocess.run(["cpp", "-P", os.path.join(HERE, "sec1.asm")], capture_output=True, text=True)
    if pre.returncode: print(pre.stderr); return 1
    tmp = os.path.join(tempfile.mkdtemp(), "hbios-1.0.5-temp.asm")
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
    for ad, (old, new) in hook.items():
        if rom[ad - 0xF000] != old:
            print("hook: %04X holds %02X, expected %02X - not the BIOS this was written for" % (ad, rom[ad - 0xF000], old))
            return 1
        rom[ad - 0xF000] = new

    with open(V104, "rb") as f: old = f.read()
    new_code = {ad for ad in mem if mem[ad] != old[ad - 0xF000]}
    overwritten = sorted(ad for ad in new_code if old[ad - 0xF000] != 0xFF)
    if overwritten:                                    # new code goes only where v1.0.4 has nothing (FF)
        print("new code overwrites v1.0.4's bytes at: " + " ".join("%04X" % x for x in overwritten[:16]))
        return 1
    unexpected = [0xF000 + i for i in range(4096) if rom[i] != old[i] and 0xF000 + i not in new_code and 0xF000 + i not in hook]
    if unexpected:
        print("differs from v1.0.4 outside the new code and the hook: " + " ".join("%04X" % x for x in unexpected[:16]))
        return 1

    full = {0xF000 + i: b for i, b in enumerate(rom)}
    with open(os.path.join(HERE, "sec1.rom"), "wb") as f: f.write(rom)
    with open(os.path.join(HERE, "sec1.hex"), "w") as f: f.write(asm1802.to_intel_hex(full))
    emu = os.path.join(ROOT, "software/s5emu/roms/hbios-1.0.5")
    with open(emu + ".rom", "wb") as f: f.write(rom)
    with open(emu + ".hex", "w") as f: f.write(asm1802.to_intel_hex(full))
    blocks = []                                        # the new code as runs of addresses
    for ad in sorted(new_code):
        if blocks and ad <= blocks[-1][1] + 8: blocks[-1][1] = ad
        else: blocks.append([ad, ad])
    free = rom.count(0xFF)
    print("HBIOS v1.0.5: new code %s, hook at F941 and F9EB-F9ED; everything else as v1.0.4"
          % ", ".join("%04X-%04X (%d bytes)" % (a, b, b - a + 1) for a, b in blocks))
    print("  -> %s.rom; about %d bytes of the 4096 still FF" % (os.path.relpath(emu, ROOT), free))
    return 0


if __name__ == "__main__":
    sys.exit(main())
