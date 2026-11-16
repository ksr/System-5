#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-01
"""checknet.py BOARD_DIR - the exported reports/netlist.net must have exactly gen/netlist.py's nets (pin partition)."""
import os, re, sys, importlib.util
board = os.path.abspath(sys.argv[1])
spec = importlib.util.spec_from_file_location("netlist", os.path.join(board, "gen", "netlist.py"))
N = importlib.util.module_from_spec(spec); spec.loader.exec_module(N)
t = open(os.path.join(board, "reports", "netlist.net")).read()
got = {}
for blk in re.split(r'\(net\s', t)[1:]:
    name = re.search(r'\(name "([^"]*)"', blk).group(1).lstrip("/")
    nodes = frozenset(re.findall(r'\(ref "([^"]+)"\)\s*\(pin "([^"]+)"\)', blk))
    if name.startswith("unconnected-"): continue
    got[name] = nodes
want = {n: frozenset(v) for n, v in N.NETS.items()}
bad = [n for n in sorted(set(got) | set(want)) if got.get(n) != want.get(n)]
for n in bad[:20]:
    print("MISMATCH %s: schematic %s / netlist.py %s" % (n, sorted(got.get(n, []))[:6], sorted(want.get(n, []))[:6]))
print("checknet %s: %d nets, %s" % (N.PROJ, len(want), "MATCH" if not bad else "%d MISMATCHES" % len(bad)))
sys.exit(1 if bad else 0)
