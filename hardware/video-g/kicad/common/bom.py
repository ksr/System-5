#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-01
"""bom.py BOARD_DIR - write BOARD_DIR/BOM.md from gen/netlist.py (PARTS, BUY): parts grouped by value and footprint,
with references and what to buy, then the IC sockets."""
import os, re, sys, importlib.util, collections

board = os.path.abspath(sys.argv[1])
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("netlist", os.path.join(board, "gen", "netlist.py"))
N = importlib.util.module_from_spec(spec); spec.loader.exec_module(N)


def refkey(r):
    m = re.match(r"([A-Z]+)(\d+)", r)
    return (m.group(1), int(m.group(2))) if m else (r, 0)


ORDER = ["IC", "Y", "J", "SV", "JP", "F", "LED", "RN", "R", "C"]
groups = collections.OrderedDict()
for ref in sorted(N.PARTS, key=lambda r: (ORDER.index(refkey(r)[0]) if refkey(r)[0] in ORDER else 99, refkey(r))):
    value, lib_id, fp, note = N.PARTS[ref]
    buy = N.BUY.get(ref, "")
    groups.setdefault((refkey(ref)[0], value, fp, buy), []).append(ref)

lines = ["# %s - bill of materials" % N.CARD, "",
         "Written by `hardware/video-g/kicad/common/bom.py` from `gen/netlist.py` (%s). Every IC goes in a socket." % N.DATE,
         "", "| Qty | Value | Footprint | References | What to buy |", "|---|---|---|---|---|"]
for (kind, value, fp, buy), refs in groups.items():
    lines.append("| %d | %s | %s | %s | %s |" % (len(refs), value, fp.split(":")[1], ", ".join(refs), buy))
sockets = collections.Counter()
for ref, (value, lib_id, fp, note) in N.PARTS.items():
    m = re.search(r"DIP-(\d+)_W([\d.]+)mm", fp)
    if m and ref.startswith("IC"):
        sockets["DIP-%s, %s mil" % (m.group(1), "600" if m.group(2) == "15.24" else "300")] += 1
lines += ["", "**IC sockets:** " + ", ".join("%d x %s" % (n, s) for s, n in sorted(sockets.items(),
                                                                                    key=lambda kv: int(kv[0][4:6])))]
jumpers = sorted((r for r in N.PARTS if refkey(r)[0] in ("SV", "JP")), key=refkey)
if jumpers:
    lines += ["", "**Jumper shunts:** %d x 2.54 mm, one each for %s." % (len(jumpers), ", ".join(jumpers))]
lines += ["", "Totals: %d ICs, %d parts." % (sum(1 for r in N.PARTS if r.startswith("IC")), len(N.PARTS))]
open(os.path.join(board, "BOM.md"), "w").write("\n".join(lines) + "\n")
print("BOM.md: %d lines, %d parts" % (len(groups), len(N.PARTS)))
