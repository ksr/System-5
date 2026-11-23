#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-23
"""silkdiff.py - every silkscreen text a rebuild added, left out or moved.

    python3 tools/kicad/silkdiff.py BOARD.kicad_pcb [REV]      against the board as committed at REV (default HEAD)
    python3 tools/kicad/silkdiff.py OLD.kicad_pcb NEW.kicad_pcb

Why (2026-11-23): the IO panel's RESET button took the corner where "J3 FRONT PANEL" stood. The label placer moved
that label to the header's other end, where the "1" at pin 1 had been, and the "1", an optional label, was left out
without a word. Three texts had changed that the report of the rebuild did not list; the pcb-check session found them
by comparing the two boards. Run this after every rebuild and put all it prints in the report.

It reads the board files as text and needs no KiCad. It lists the board's own texts (gr_text on a silkscreen layer):
the labels the gen/ scripts place. A text inside a footprint moves with its part and is not listed.
Exit status 0; the last line is the count, "no silkscreen text changed" when nothing did.
"""
import os, re, subprocess, sys
from collections import defaultdict


def texts(src):
    """[(text, x, y, angle, layer)] for every gr_text on a silkscreen layer in a .kicad_pcb's text"""
    out = []
    for m in re.finditer(r'\(gr_text\s+"((?:[^"\\]|\\.)*)"', src):
        head = src[m.end():m.end() + 400]
        at = re.search(r'\(at\s+(-?[\d.]+)\s+(-?[\d.]+)(?:\s+(-?[\d.]+))?\)', head)
        layer = re.search(r'\(layer\s+"([^"]+)"', head)
        if at and layer and "Silk" in layer.group(1):
            out.append((m.group(1).replace("\\n", " / "), float(at.group(1)), float(at.group(2)), float(at.group(3) or 0),
                        layer.group(1)))
    return out


def compare(old, new):
    """the lines to print for two lists from texts()"""
    o, n, lines = defaultdict(list), defaultdict(list), []
    for t in old: o[(t[0], t[4])].append(t)
    for t in new: n[(t[0], t[4])].append(t)
    same = lambda p, q: abs(p[1] - q[1]) < 0.005 and abs(p[2] - q[2]) < 0.005 and p[3] == q[3]
    for key in sorted(set(o) | set(n)):
        a = [p for p in o.get(key, []) if not any(same(p, q) for q in n.get(key, []))]     # no longer where they were
        b = [q for q in n.get(key, []) if not any(same(p, q) for p in o.get(key, []))]     # not there before
        name = "%r%s" % (key[0] if len(key[0]) < 60 else key[0][:57] + "...", "" if key[1] == "F.SilkS" else " (%s)" % key[1])
        while a and b:                                  # the same text gone from one place and new at another: moved
            p = a.pop(0); q = min(b, key=lambda r: (r[1] - p[1]) ** 2 + (r[2] - p[2]) ** 2); b.remove(q)
            d = ((p[1] - q[1]) ** 2 + (p[2] - q[2]) ** 2) ** 0.5
            lines.append("  moved %5.1f mm  %s  (%.2f, %.2f) -> (%.2f, %.2f)%s" % (
                d, name, p[1], p[2], q[1], q[2], "" if p[3] == q[3] else ", angle %g -> %g" % (p[3], q[3])))
        lines += ["  LEFT OUT        %s  was at (%.2f, %.2f)" % (name, p[1], p[2]) for p in a]
        lines += ["  new             %s  at (%.2f, %.2f)" % (name, q[1], q[2]) for q in b]
    return lines


def main(argv):
    if len(argv) == 2 and argv[1].endswith(".kicad_pcb"):
        a, b, was = open(argv[0]).read(), open(argv[1]).read(), argv[0]
    elif len(argv) in (1, 2):
        rev = argv[1] if len(argv) == 2 else "HEAD"; path = os.path.abspath(argv[0])
        root = subprocess.run(["git", "-C", os.path.dirname(path), "rev-parse", "--show-toplevel"],
                              capture_output=True, text=True, check=True).stdout.strip()
        a = subprocess.run(["git", "-C", root, "show", "%s:%s" % (rev, os.path.relpath(path, root))],
                           capture_output=True, text=True, check=True).stdout
        b, was = open(path).read(), rev
    else:
        sys.exit(__doc__)
    old, new = texts(a), texts(b); lines = compare(old, new)
    print("silkscreen texts: %d at %s, %d now" % (len(old), was, len(new)))
    for line in lines: print(line)
    print("%d text(s) changed" % len(lines) if lines else "no silkscreen text changed")


if __name__ == "__main__":
    main(sys.argv[1:])
