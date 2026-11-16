#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-06
"""Build the CPU-card EPROM image HBIOS + Mike Riley's BIOS 1.0.4, as firmware/hbios/v1.0.4/Makefile would
(srec_cat of orig_bios/bios.img and sec1.img, filled with FF, cropped to F000-FFFF).
The 2005 tree never got a v1.0.4 sec1 build (its sec1.lst is empty), but sec1.asm is identical in v0.9 and v1.0.4,
so the assembled HBIOS from firmware/hbios/v0.9/sec1.img is used with v1.0.4's bios.img (assembled with KSR: type/read
go to HBIOS at F203/F200).  ELF/OS 0.2.6 needs this BIOS: the v0.9 ROM has no f_isalnum vector at FF78.
  python3 tools/mkrom.py   -> roms/hbios-1.0.4.rom (4096 bytes, F000-FFFF) and .hex"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(HERE, "..")); from s5emu.machine import load_image
parts = [os.path.join(ROOT, "firmware/hbios/v1.0.4/orig_bios/bios.img"), os.path.join(ROOT, "firmware/hbios/v0.9/sec1.img")]
rom = bytearray(b"\xff" * 4096)
for p in parts:
    for a, b in load_image(p).items():
        if 0xF000 <= a <= 0xFFFF: rom[a - 0xF000] = b
out = os.path.join(HERE, "..", "roms", "hbios-1.0.4")
open(out + ".rom", "wb").write(rom)
with open(out + ".hex", "w") as f:
    for i in range(0, 4096, 32):
        rec = bytes([32, (0xF000 + i) >> 8, (0xF000 + i) & 0xFF, 0]) + rom[i:i + 32]
        f.write(":%s%02X\n" % (rec.hex().upper(), (-sum(rec)) & 0xFF))
    f.write(":00000001FF\n")
print("wrote", out + ".rom", "and .hex")
