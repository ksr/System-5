#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-01; on v1.0.8 2026-11-20
"""Build the VIDEO-G HBIOS ROM: HBIOS for the VIDEO-G card on v1.0.8, the ROM for the new card set (CPU Rev D, the
IO panel, VIDEO-G).

  python3 firmware/hbios/video-g/build.py

cpp -P sec1.asm (BIOS and VIDEOLOWER defined in the source), assemble with tools/asm1802.py, then merge with Mike
Riley's BIOS 1.0.4 as built for System-5 (../v1.0.4/orig_bios/bios.img, unchanged) and fill F000-FFFF with FF. Writes
sec1.lst, sec1.img (this part only), sec1.hex and sec1.rom (4096 bytes, F000-FFFF) here, and copies the ROM to
software/s5emu/roms/hbios-video-g.rom (+ .hex) for the emulator's --video g.

2026-11-17: VIDEO-G memory-mapped (sec1.asm's header), and v1.0.6's disk fix: the routine at FBC1 sent the caller's
R8.1 to the drive/head register, which Elf/OS v5 passes as 00 (a CHS address the card refuses); the same 26 bytes as
firmware/hbios/v1.0.6/build.py (LBR FC31 at FBC1, LBR FC3C at FBDF, the code at FC31-FC44), each checked for the
byte it replaces.

2026-11-20 (Ken: a VIDEO-G HBIOS built on v1.0.8): sec1.asm now holds v1.0.5's monitor commands (H, B, D, Q1 / Q0,
the panel demo at @F1C0) and v1.0.8's driver for the IO panel's clock, and this program makes the patches that go
with them, as firmware/hbios/v1.0.8/build.py does: the hook into Mike Riley's monitor (BNZ F913 at F940 becomes BNZ
F9EB, and LBR monext goes into the free bytes at F9EB), f_gettod (F815) and f_settod (F818) to the driver, and
f_getdev's answer 0015h (bit 4 = an RTC). Each patched byte is checked for the value it replaces. It also checks
what an assembler does not: that no piece of sec1.asm runs into the next one (the pieces sit in the EPROM's free
runs, with a few bytes to spare), that the clock driver (FC92-FCEB, F7CD-F7FF), the panel demo (F1C0-F1D1) and the
disk fix are v1.0.8's bytes at v1.0.8's addresses, and that everything outside sec1.asm's own code and the patches is
v1.0.4's.
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
    sym = a.symbols
    # no piece of sec1.asm may run into the next: (the label after a piece's last byte, the address it must not pass)
    for end, limit in (("E_F0", 0xF100), ("E_F1", 0xF1C0), ("E_PDEMO", 0xF1E0), ("E_MONQ", 0xF200), ("E_MONEXT", 0xF7CD),
                       ("E_RTCSET", 0xF800), ("E_SCROLL", 0xFC92), ("E_RTC", 0xFD00)):
        if sym[end] > limit:
            print("sec1.asm: the piece ending at %s runs to %04X, past %04X" % (end.lower(), sym[end] - 1, limit - 1)); return 1
    monext = sym["MONEXT"]; get, put = sym["RTCGET"], sym["RTCSET"]
    hook = {0xF941: (0x13, 0xEB),                       # BNZ F913 -> BNZ F9EB: an unknown command goes on to F9EB
            0xF9EB: (0xFF, 0xC0),                       # LBR monext, in bytes the BIOS leaves free
            0xF9EC: (0xFF, monext >> 8),
            0xF9ED: (0xFF, monext & 0xFF)}
    rtc = {0xF816: (0xF9, get >> 8), 0xF817: (0xE8, get & 0xFF),     # f_gettod: LBR F9E8 -> LBR rtcget
           0xF819: (0xF9, put >> 8), 0xF81A: (0xE8, put & 0xFF),     # f_settod: LBR F9E8 -> LBR rtcset
           0xFEDC: (0x05, 0x15)}                                     # f_getdev: LDI 05h -> LDI 15h (bit 4, an RTC)
    patch = dict(hook); patch.update(LBA); patch.update(rtc)
    patch.update({LBA_CODE[0] + i: (0xFF, b) for i, b in enumerate(LBA_CODE[1])})
    for ad, (old, new) in patch.items():
        if rom[ad - 0xF000] != old:
            print("patch: %04X holds %02X, expected %02X - not the BIOS this was written for" % (ad, rom[ad - 0xF000], old)); return 1
        rom[ad - 0xF000] = new
    with open(os.path.join(ROOT, "software/s5emu/roms/hbios-1.0.4.rom"), "rb") as f: v104 = f.read()
    with open(os.path.join(ROOT, "software/s5emu/roms/hbios-1.0.8.rom"), "rb") as f: v108 = f.read()
    same = [(0xFC92, 0xFCEB, "the clock driver (get, read, write)"), (0xF7CD, 0xF7FF, "the clock driver (set)"),
            (0xF1C0, 0xF1D1, "the panel demo"), (0xFC31, 0xFC44, "the disk fix"), (0xF815, 0xF81A, "the clock vectors"),
            (0xFBC1, 0xFBC3, "the disk fix's first jump"), (0xFBDF, 0xFBE1, "the disk fix's second jump")]
    for lo, hi, what in same:
        if rom[lo - 0xF000:hi - 0xF000 + 1] != v108[lo - 0xF000:hi - 0xF000 + 1]:
            print("%04X-%04X, %s: not v1.0.8's bytes" % (lo, hi, what)); return 1
    other = [0xF000 + i for i in range(4096) if rom[i] != v104[i] and 0xF000 + i not in mem and 0xF000 + i not in patch]
    if other:
        print("differs from v1.0.4 outside sec1.asm's code and the patches: " + " ".join("%04X" % x for x in other[:16])); return 1
    full = {0xF000 + i: b for i, b in enumerate(rom)}
    open(os.path.join(HERE, "sec1.rom"), "wb").write(rom)
    open(os.path.join(HERE, "sec1.hex"), "w").write(asm1802.to_intel_hex(full))
    emu = os.path.join(ROOT, "software/s5emu/roms/hbios-video-g")
    open(emu + ".rom", "wb").write(rom); open(emu + ".hex", "w").write(asm1802.to_intel_hex(full))
    runs = []                                          # sec1.asm's code as runs of addresses
    for ad in sorted(mem):
        if runs and ad == runs[-1][1] + 1: runs[-1][1] = ad
        else: runs.append([ad, ad])
    print("HBIOS (VIDEO-G, on v1.0.8): %d bytes of its own at %s" % (len(mem), ", ".join("%04X-%04X" % (lo, hi) for lo, hi in runs)))
    print("  + BIOS 1.0.4, the monitor hook (F941, F9EB-F9ED), the disk fix (FBC1-FBC3, FBDF-FBE1, FC31-FC44), the clock"
          " vectors (F816-F81A, FEDC)")
    print("  -> sec1.rom, %s.rom; %d bytes of the 4096 still FF" % (os.path.relpath(emu, ROOT), rom.count(0xFF)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
