#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-06
"""Make a bootable ELF/OS disk image for the emulator (or a CF card).

  python3 tools/mkelfos.py OUT.img [--mb 16]

1. FSGEN: a straight port of disktool's command_fsgen (main.c; boot loader in sector 0, the lump allocation
   table from sector 17, master directory after it). disktool itself cannot do this step on a blank image: it opens the
   master directory before running any command and loops forever on an all-zero disk.
2. SYS: kernel.bin (8 KB) into sectors 1-16, as disktool's SYS does; the boot loader reads them to 0300 and jumps there.
3. disktool (compiled from its main.c) then copies Mike Riley's ELF/OS programs into / and /BIN
   (the 2005 kernel.bin runs programs from the current directory; later kernels search /BIN).

ELF/OS 0.2.6, its programs and disktool are Mike Riley's (2004-05) and carry no permission to publish them, so they are
not in this repository: they are in the private repository private-resources (github.com/ksr/private-resources), cloned
beside this one, at the paths they had here until 2026-11-15 (software/disktool/, reference/mike-riley/). Without them
this program says what is missing and stops, and the emulator runs without an ELF/OS disk.
"""
import os, re, sys, subprocess, tempfile, argparse

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
PRIVATE = os.path.abspath(os.path.join(ROOT, "..", "private-resources", "elf"))
DT_SRC = os.path.join(PRIVATE, "software/disktool/main.c")
KERNEL = os.path.join(PRIVATE, "software/disktool/kernel.bin")
BIN = os.path.join(PRIVATE, "reference/mike-riley/elfos-programs/bin")


def missing():
    """the files an ELF/OS 0.2.6 disk is made from that are not here (an empty list when it can be made)"""
    return [p for p in (DT_SRC, KERNEL, BIN) if not os.path.exists(p)]


def boot_loader():
    src = open(DT_SRC).read()
    body = re.search(r"byte boot\[256\] = \{(.*?)\};", src, re.S).group(1)
    b = bytes(int(x, 16) for x in re.findall(r"0x[0-9a-fA-F]+", body)); assert len(b) == 256
    return b


def fsgen(img, size):
    disk = bytearray(512 * size)
    lumps = size // 8
    lumpsec = lumps // 256 + 1
    lumpsec = lumpsec // 8 + 1 if lumpsec & 7 else lumpsec // 8
    dirsec = lumpsec * 8 + 16
    if dirsec & 7: dirsec = (dirsec // 8) * 8 + 8
    def wl(l, v): o = (17 + l // 256) * 512 + (l % 256) * 2; disk[o] = v >> 8; disk[o + 1] = v & 0xFF
    disk[17 * 512:(17 + lumpsec * 8) * 512] = b"\xff" * (lumpsec * 8 * 512)
    for l in range(dirsec // 8, lumps): wl(l, 0)
    wl(dirsec // 8, 0xFEFE)
    s0 = bytearray(512); s0[:256] = boot_loader()
    s0[256:260] = size.to_bytes(4, "big"); s0[260] = 1; s0[261], s0[262] = dirsec >> 8, dirsec & 0xFF
    s0[266] = 8; s0[267], s0[268] = lumps >> 8, lumps & 0xFF
    s0[302], s0[303] = (dirsec // 8) >> 8, (dirsec // 8) & 0xFF; s0[312:315] = b"MD0"
    disk[0:512] = s0
    k = open(KERNEL, "rb").read().ljust(16 * 512, b"\0")[:16 * 512]
    disk[512:17 * 512] = k
    open(img, "wb").write(disk)
    return lumps, dirsec


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("out"); ap.add_argument("--mb", type=int, default=16)
    a = ap.parse_args()
    if missing():
        sys.exit("mkelfos.py: ELF/OS 0.2.6 is Mike Riley's and not in this repository. Not found:\n  "
                 + "\n  ".join(missing()) + "\n(they are in github.com/ksr/private-resources, a private repository)")
    size = a.mb * 2048
    lumps, dirsec = fsgen(a.out, size)
    print("FSGEN %d sectors (%d MB), %d lumps, master directory at sector %d; kernel in sectors 1-16" % (size, a.mb, lumps, dirsec))
    dt = os.path.join(tempfile.gettempdir(), "s5emu-disktool")
    if not os.path.exists(dt) or os.path.getmtime(dt) < os.path.getmtime(DT_SRC):
        subprocess.run(["cc", "-std=gnu89", "-w", "-o", dt, DT_SRC], check=True)
    progs = [f for f in sorted(os.listdir(BIN)) if f.lower() != "kernel.bin" and not os.path.isdir(os.path.join(BIN, f))]
    # the 2005 kernel.bin runs programs from the current directory only (later kernels also search /BIN): both
    cmds = ["md BIN", "cd BIN"] + ["copy [%s] %s" % (os.path.join(BIN, f), f) for f in progs]
    cmds += ["cd /"] + ["copy [%s] %s" % (os.path.join(BIN, f), f) for f in progs] + ["dir", "stat", "quit"]
    out = subprocess.run([dt, a.out], input="\n".join(cmds) + "\n", capture_output=True, text=True, timeout=120).stdout
    print("\n".join(l for l in out.splitlines() if l.strip() and not l.startswith("Copying"))[-1500:])


if __name__ == "__main__":
    main()
