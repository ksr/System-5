#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-19
"""Make MEM3-E a proper 4-layer board: signals on F.Cu/B.Cu, In1.Cu = solid GND plane, In2.Cu = solid VCC plane (Ken).
Rev E started as Rev D's routing (signals on the inner layers, GND pours outside). This strips every track, via and
pour, adds the two planes, and writes a DSN for Freerouting in which the inner layers are power layers and GND/VCC
are not routed at all: every GND and VCC pin is a through-hole pad, so it lands in its plane.
Run with KiCad's Python:   <KiCad python> gen/make_planes.py        -> ../memory-rev-e.kicad_pcb (unrouted) + .dsn
then:  java -jar ~/freerouting/freerouting.jar -de memory-rev-e.dsn -do memory-rev-e.ses -mt 1
       <KiCad python> ../../../../tools/kicad/kicad_route.py import_ses memory-rev-e.kicad_pcb memory-rev-e.ses"""
import os, sys, re
import pcbnew
HERE = os.path.dirname(os.path.abspath(__file__)); DEST = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(DEST, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "kicad")); import kicad_route
MM = pcbnew.FromMM; PCB = os.path.join(DEST, "memory-rev-e.kicad_pcb"); PLANES = (("In1.Cu", "GND"), ("In2.Cu", "VCC"))

# 1. strip copper at the text level (pcbnew's Remove() breaks iteration in KiCad 10)
forms = kicad_route.top_forms(open(PCB).read())
keep = [f for f in forms if not f.startswith(("(segment", "(via", "(arc")) and not (f.startswith("(zone") and "(keepout" not in f)]
open(PCB, "w").write("(kicad_pcb\n\t" + "\n\t".join(keep) + "\n)\n")

# 2. the planes
b = pcbnew.LoadBoard(PCB); ebb = b.GetBoardEdgesBoundingBox(); i = MM(0.5)
for lname, net in PLANES:
    L = b.GetLayerID(lname); b.SetLayerType(L, pcbnew.LT_POWER)
    z = pcbnew.ZONE(b); z.SetLayer(L); z.SetNet(b.FindNet(net)); o = z.Outline(); o.NewOutline()
    for x, y in ((ebb.GetLeft() + i, ebb.GetTop() + i), (ebb.GetRight() - i, ebb.GetTop() + i),
                 (ebb.GetRight() - i, ebb.GetBottom() - i), (ebb.GetLeft() + i, ebb.GetBottom() - i)):
        o.Append(x, y)
    z.SetLocalClearance(MM(0.3)); z.SetMinThickness(MM(0.25)); z.SetThermalReliefGap(MM(0.3))
    z.SetThermalReliefSpokeWidth(MM(0.4)); z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL); z.SetZoneName(net + " plane")
    b.Add(z)
pcbnew.ZONE_FILLER(b).Fill(b.Zones()); pcbnew.SaveBoard(PCB, b)

# 3. DSN: inner layers are power layers, GND/VCC not routed
kicad_route.export_dsn(PCB)
dsn = PCB[:-len(".kicad_pcb")] + ".dsn"; t = open(dsn).read()
for lname, _ in PLANES:
    t = re.sub(r'(\(layer %s\s*\(type )signal' % re.escape(lname), r'\1power', t)
for _, net in PLANES:
    t = re.sub(r'\n\s*\(net %s\s*\(pins[^)]*\)\s*\)' % re.escape(net), '', t)      # the net's pin list
    t = re.sub(r'(\(class [^\n]*?) %s(?=[ )\n])' % re.escape(net), r'\1', t)        # and its class membership
t = re.sub(r'\n\s*\(class Power\s*\(circuit\s*\(use_via [^)]*\)\s*\)\s*\(rule\s*\(width \d+\)\s*\(clearance \d+\)\s*\)\s*\)', '', t)   # now empty
open(dsn, "w").write(t)
print("planes:", ", ".join("%s = %s" % p for p in PLANES), "| DSN layers:",
      re.findall(r'\(layer (\S+)\s*\(type (\w+)', t), "| GND/VCC left in DSN network:",
      bool(re.search(r'\(net (GND|VCC)\s*\(pins', t)))
sys.stdout.flush(); os._exit(0)
