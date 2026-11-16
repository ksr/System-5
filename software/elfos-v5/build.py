#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-14
"""Build the System-5 programs for Elf/OS v5: python3 software/elfos-v5/build.py [--check]

Assembles each program with tools/asm1802.py and writes, beside its source, the Elf/OS program (a 6-byte header:
load address, size, start address; then the code) and a listing. --check writes nothing and says whether the
programs in the repository are what the sources assemble to (exit code 1 if not).
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import asm1802                                                                # noqa: E402

PROGRAMS = ["cls"]                         # each is <name>/<name>.asm -> <name>/<name>


def assemble(name):
    """-> (the Elf/OS program, the listing)"""
    a = asm1802.assemble_file(os.path.join(HERE, name, name + ".asm"))
    if a.errors: raise SystemExit("%s: %s" % (name, "; ".join(str(e) for e in a.errors[:10])))
    mem = a.image(); lo, hi = min(mem), max(mem)
    code = bytes(mem.get(x, 0) for x in range(lo, hi + 1))
    return bytes([lo >> 8, lo & 0xFF, len(code) >> 8, len(code) & 0xFF, lo >> 8, lo & 0xFF]) + code, a.listing()


def main(argv):
    check = "--check" in argv; ok = True
    for name in PROGRAMS:
        prog, lst = assemble(name); path = os.path.join(HERE, name, name)
        if check:
            same = os.path.exists(path) and open(path, "rb").read() == prog; ok = ok and same
            print("%s: %d bytes, %s" % (name, len(prog), "as built from its source" if same else "NOT what its source assembles to"))
        else:
            with open(path, "wb") as f: f.write(prog)
            with open(path + ".lst", "w") as f: f.write(lst)
            print("%s: %d bytes (%d of code at %04X)" % (name, len(prog), len(prog) - 6, int.from_bytes(prog[0:2], "big")))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
