#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-02
"""sync_values.py BOARD_DIR - copy every part's value from gen/netlist.py onto the routed board (a value change needs
no re-route: the footprint and its copper stay). Run with KiCad's Python, then silk.py BOARD_DIR for the labels."""
import os, sys, importlib.util
import pcbnew
board_dir = os.path.abspath(sys.argv[1])
spec = importlib.util.spec_from_file_location("netlist", os.path.join(board_dir, "gen", "netlist.py"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
N = importlib.util.module_from_spec(spec); spec.loader.exec_module(N)
pcb = os.path.join(board_dir, N.PROJ + ".kicad_pcb"); b = pcbnew.LoadBoard(pcb); changed = []
for fp in b.GetFootprints():
    want = N.PARTS.get(fp.GetReference(), (None,))[0]
    if want and fp.GetValue() != want:
        changed.append("%s %s -> %s" % (fp.GetReference(), fp.GetValue(), want)); fp.SetValue(want)
pcbnew.SaveBoard(pcb, b); print("values changed:", changed or "none"); sys.stdout.flush(); os._exit(0)
