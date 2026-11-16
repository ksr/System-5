#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-02
"""plane_islands.py BOARD.kicad_pcb - set the GND / VCC planes of a routed board to make_board.py's plane settings
(remove islands; 0.25 mm clearance, 0.2 mm minimum width, so the copper between two pin rows stays joined) and refill (make_board.py does this for new boards; this fixes a board routed before it did). Run with KiCad's Python."""
import sys, os
import pcbnew
b = pcbnew.LoadBoard(sys.argv[1]); n = 0
for z in b.Zones():
    if not z.GetIsRuleArea() and z.GetZoneName().endswith(" plane"):
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS); n += 1
        z.SetLocalClearance(pcbnew.FromMM(0.25)); z.SetMinThickness(pcbnew.FromMM(0.2))   # links between pin rows
pcbnew.ZONE_FILLER(b).Fill(b.Zones()); pcbnew.SaveBoard(sys.argv[1], b)
print("planes set to remove islands:", n); sys.stdout.flush(); os._exit(0)
