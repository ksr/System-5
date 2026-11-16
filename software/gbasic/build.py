#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-01
"""Build GBASIC: python3 software/gbasic/build.py

1. tools/gen_tables.py writes src/tables.inc (keywords, tokens, dispatch tables).
2. tools/asm1802.py (in the repo's tools/) assembles src/gbasic.asm.
Writes gbasic (the ELF/OS program: 6-byte header + code, load and run at 2000h), gbasic.bin (the bytes alone),
gbasic.lst (listing; s5emu's `sym` reads its labels) and gbasic.sym (address, name).
"""
import os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import asm1802


def main():
    subprocess.run([sys.executable, os.path.join(HERE, "tools", "gen_tables.py")], check=True)
    a = asm1802.assemble_file(os.path.join(HERE, "src", "gbasic.asm"))
    if a.errors:
        for e in a.errors[:60]: print("error:", e)
        print("%d error(s)" % len(a.errors)); return 1
    mem = a.image(); lo, hi = min(mem), max(mem)
    data = bytes(mem.get(x, 0) for x in range(lo, hi + 1))
    open(os.path.join(HERE, "gbasic.bin"), "wb").write(data)
    hdr = bytes([lo >> 8, lo & 0xFF, len(data) >> 8, len(data) & 0xFF, lo >> 8, lo & 0xFF])
    open(os.path.join(HERE, "gbasic"), "wb").write(hdr + data)
    open(os.path.join(HERE, "gbasic.lst"), "w").write(a.listing())
    with open(os.path.join(HERE, "gbasic.sym"), "w") as f:
        for k in sorted(a.symbols, key=lambda k: (a.symbols[k] & 0xFFFF, k)):
            if len(k) > 1 and not (k[0] == "R" and len(k) <= 3 and all(c in "0123456789ABCDEF" for c in k[1:])):
                f.write("%04X %s\n" % (a.symbols[k] & 0xFFFF, k))
    s = a.symbols
    nlong = sum(1 for l in a.lines if l.op in asm1802.RELAX and l.long)
    nrel = sum(1 for l in a.lines if l.op in asm1802.RELAX)
    print("GBASIC: code %04X-%04X = %d bytes (file %d with the header); RAM to %04X; program space %04X-%04X = %d bytes"
          % (lo, hi, len(data), len(data) + 6, s["PROG"], s["PROG"], s["MEMTOP"], s["MEMTOP"] - s["PROG"]))
    print("        %d of %d relaxing jumps long" % (nlong, nrel))
    return 0


if __name__ == "__main__":
    sys.exit(main())
