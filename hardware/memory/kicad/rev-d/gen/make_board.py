#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-05
"""One-off: start the Memory Rev D board from the Rev C board, ready for routing from scratch.

Run with KiCad's Python (pcbnew). Steps:
  1. import the Rev C board (Fusion export) through KiCad's Eagle importer: outline, bus connector, placement, keepouts
  2. drop all copper (tracks, vias, pours) and the parts Rev D removes (IC10, C3)
  3. give every pad its Rev D net from the schematic netlist (gen/../reports/netlist.net)
  4. tools/kicad/finish_board.py: project footprint library, symbol links; then JLCPCB 2-layer rules
  5. silkscreen: each IC labelled "<ref> <part>" and its function, inside its outline; board title MEM3-D
  6. GND pours on both layers (filled after routing)
Writes ../memory-rev-d.kicad_pcb (unrouted).
"""
import os, sys, re
import pcbnew
HERE = os.path.dirname(os.path.abspath(__file__)); DEST = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(DEST, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "kicad")); import finish_board
SRC = os.path.join(ROOT, "hardware/memory/eagle/rev-c/fusion-export/mem3-c.brd")
NET = os.path.join(DEST, "reports", "netlist.net"); PROJ = "memory-rev-d"
MM = pcbnew.FromMM

LABELS = {   # ref: (part, function)
    "IC1": ("62256", "RAM LO 0000-7FFF"), "IC11": ("62256", "RAM HI 8000-FFFF"),
    "IC3": ("27256", "EPROM LO 0000-7FFF"), "IC5": ("27256", "EPROM HI 8000-FFFF"),
    "IC2": ("74HCT151", "RAM LO 4K SEL"), "IC4": ("74HCT151", "RAM HI 4K SEL"),
    "IC15": ("74HCT151", "EPROM LO 4K SEL"), "IC13": ("74HCT151", "EPROM HI 4K SEL"),
    "IC6": ("4042", "A8-A11 LATCH"), "IC9": ("4042", "A12-A15 LATCH"),
    "IC7": ("4050", "A0-A5 BUFFER"), "IC8": ("4050", "A6 A7 RD WR BUF"),
    "IC14": ("74LS32", "BANK + LO CE"), "IC12": ("74LS32", "HI CE"),
}

# 1. import (pcbnew: Add/Move only - in KiCad 10's SWIG layer containers stop iterating after a Remove())
b = pcbnew.PCB_IO_MGR.Load(pcbnew.PCB_IO_MGR.EAGLE, SRC)
bb = b.GetBoundingBox(); mv = pcbnew.VECTOR2I(MM(10) - bb.GetX(), MM(10) - bb.GetY())
for coll in (b.GetFootprints(), b.GetDrawings(), b.Zones(), b.GetTracks()):
    for it in list(coll): it.Move(mv)
raw = os.path.join(DEST, "_import.kicad_pcb"); pcbnew.PCB_IO_KICAD_SEXPR().SaveBoard(raw, b)
# 2. copper and removed parts, at the text level: drop tracks/vias/arcs, copper pours (keep keepout rule areas),
#    IC10 and C3, and anything on a layer KiCad could not map
import kicad_route
text = open(raw).read(); forms = kicad_route.top_forms(text)
def keep(f):
    if f.startswith(("(segment", "(via", "(arc")): return False
    if f.startswith("(zone") and "(keepout" not in f: return False
    if f.startswith("(footprint") and re.search(r'\(property "Reference" "(IC10|C3)"', f): return False
    return True
kept = [f for f in forms if keep(f)]
open(raw, "w").write("(kicad_pcb\n\t" + "\n\t".join(kept) + "\n)\n")
print("import: %d top-level items, kept %d" % (len(forms), len(kept)))
b = pcbnew.LoadBoard(raw); os.remove(raw)
# 3. nets from the Rev D schematic
s = open(NET).read(); padnet = {}
for name, body in re.findall(r'\(net\s+\(code "\d+"\)\s+\(name "([^"]+)"\)(.*?)(?=\n\t\t\(net\s|\n\t\)\n\))', s, re.S):
    for ref, pad in re.findall(r'\(node\s+\(ref "([^"]+)"\)\s+\(pin "([^"]+)"\)', body):
        padnet[(ref, pad)] = name
nets = {}
def netitem(n):
    if n not in nets:
        ni = pcbnew.NETINFO_ITEM(b, n); b.Add(ni); nets[n] = ni
    return nets[n]
missing = []
for fp in b.GetFootprints():
    for p in fp.Pads():
        n = padnet.get((fp.GetReference(), p.GetNumber()))
        if n is None:
            p.SetNetCode(0)
            if (fp.GetReference(), p.GetNumber()) not in padnet: missing.append("%s.%s" % (fp.GetReference(), p.GetNumber()))
        else: p.SetNet(netitem(n))
for (ref, pad) in padnet:
    if not b.FindFootprintByReference(ref) and not ref.startswith("#"): print("netlist part not on board:", ref)
print("pads with no net (single-pin / unused):", len(missing))
# 4b. C2 (IC6's bypass cap) sat 1.27 mm closer than the other bypass caps and its body overlapped IC6's socket: line it up with C1
c2 = b.FindFootprintByReference("C2"); c1 = b.FindFootprintByReference("C1")
c2.SetPosition(pcbnew.VECTOR2I(c1.GetPosition().x, c2.GetPosition().y))
for rn in ("RN1", "RN2", "RN3", "RN4"): b.FindFootprintByReference(rn).SetValue("4.7k")
# C5 (IC15's bypass cap) down one grid step so its outline clears the HI block's F000 address label (Ken, 2026-10-05)
c5 = b.FindFootprintByReference("C5"); c5.SetPosition(pcbnew.VECTOR2I(c5.GetPosition().x, c5.GetPosition().y + MM(2.54)))
# 5. silkscreen
for fp in b.GetFootprints():
    ref = fp.GetReference()
    if ref not in LABELS: continue
    fp.Reference().SetVisible(False); fp.Value().SetVisible(False)
    part, func = LABELS[ref]
    c = fp.GetBoundingBox(False).GetCenter()
    for i, txt in enumerate(("%s %s" % (ref, part), func)):
        t = pcbnew.PCB_TEXT(b); t.SetText(txt); t.SetLayer(pcbnew.F_SilkS)
        t.SetTextSize(pcbnew.VECTOR2I(MM(1.0), MM(1.0))); t.SetTextThickness(MM(0.15))
        t.SetPosition(pcbnew.VECTOR2I(c.x, c.y + MM(-0.75 + 1.5 * i)))
        b.Add(t)
# jumper blocks: row names left of each row, each column's 4K start address under each block (replaces Eagle's BANK n)
def silk(txt, x, y, h=1.0, angle=0):
    t = pcbnew.PCB_TEXT(b); t.SetText(txt); t.SetLayer(pcbnew.F_SilkS)
    t.SetTextSize(pcbnew.VECTOR2I(MM(h), MM(h))); t.SetTextThickness(MM(0.15)); t.SetPosition(pcbnew.VECTOR2I(x, y))
    if angle: t.SetTextAngleDegrees(angle)
    b.Add(t); return t
bank_texts = [d for d in b.GetDrawings() if isinstance(d, pcbnew.PCB_TEXT) and re.fullmatch(r"BANK [0-7]", d.GetText())]   # Eagle's only - not "BANK + LO CE"
for d in bank_texts: d.SetText("")      # emptied, not removed (pcbnew Remove() breaks iteration); dropped below at text level
for block, (hdr2, hdr1, first) in {"LO": ("SV2", "SV3", 0x0), "HI": ("SV1", "SV4", 0x8)}.items():
    f2, f1 = b.FindFootprintByReference(hdr2), b.FindFootprintByReference(hdr1)
    rows = {}
    for f in (f2, f1):
        for p in f.Pads():
            n = p.GetNetname()
            kind = "GND" if n == "GND" else ("RAM" if any(m in n for m in ("IC2-", "IC4-")) else "ROM")
            rows.setdefault(kind, []).append(p.GetPosition())
    left = min(p.x for ps in rows.values() for p in ps)
    for kind, ps in rows.items():
        silk(kind, left - MM(2.55), ps[0].y, h=0.8)
    cols = sorted({p.x for p in rows["RAM"]})          # leftmost column = D7 = the block's 4K #7
    bottom = max(p.y for ps in rows.values() for p in ps)
    for i, x in enumerate(cols):
        silk("%X000" % (first + 7 - i), x, bottom + MM(3.6), h=1.0, angle=90)
ebb = b.GetBoardEdgesBoundingBox()
title = pcbnew.PCB_TEXT(b); title.SetText("MEM3-D   System-5 64K RAM/EPROM   2026")
title.SetLayer(pcbnew.F_SilkS); title.SetTextSize(pcbnew.VECTOR2I(MM(1.2), MM(1.2))); title.SetTextThickness(MM(0.18))
title.SetPosition(pcbnew.VECTOR2I(ebb.GetCenter().x, ebb.GetBottom() - MM(1.6))); b.Add(title)
# 6. GND pours, both layers, 0.5 mm inside the edge
for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
    z = pcbnew.ZONE(b); z.SetLayer(layer); z.SetNet(netitem("GND"))
    o = z.Outline(); o.NewOutline(); inset = MM(0.5)
    for x, y in ((ebb.GetLeft() + inset, ebb.GetTop() + inset), (ebb.GetRight() - inset, ebb.GetTop() + inset),
                 (ebb.GetRight() - inset, ebb.GetBottom() - inset), (ebb.GetLeft() + inset, ebb.GetBottom() - inset)):
        o.Append(x, y)
    z.SetLocalClearance(MM(0.3)); z.SetMinThickness(MM(0.25)); z.SetThermalReliefGap(MM(0.3)); z.SetThermalReliefSpokeWidth(MM(0.4))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL); z.SetAssignedPriority(0)
    b.Add(z)
tmp = os.path.join(DEST, "_unfinished.kicad_pcb"); pcbnew.PCB_IO_KICAD_SEXPR().SaveBoard(tmp, b)
# 4. footprint library, symbol links (finish_board also sets OSH Park rules: overridden by the project's JLCPCB rules below)
finish_board.main(tmp, DEST, PROJ, NET); os.remove(tmp)
out = os.path.join(DEST, PROJ + ".kicad_pcb"); b = pcbnew.LoadBoard(out); ds = b.GetDesignSettings()
ds.m_MinClearance = MM(0.15); ds.m_TrackMinWidth = MM(0.15); ds.m_ViasMinSize = MM(0.5); ds.m_MinThroughDrill = MM(0.3)
ds.m_ViasMinAnnularWidth = MM(0.13); ds.m_HoleClearance = MM(0.25); ds.m_HoleToHoleMin = MM(0.5); ds.m_CopperEdgeClearance = MM(0.5)
pcbnew.SaveBoard(out, b)
print("wrote", out, "-", len(b.GetFootprints()), "footprints")
txt = open(out).read(); forms = kicad_route.top_forms(txt)
kept = [f for f in forms if not (f.startswith("(gr_text \"\"") or f.startswith('(gr_text ""'))]
open(out, "w").write("(kicad_pcb\n\t" + "\n\t".join(kept) + "\n)\n"); print("empty texts dropped:", len(forms) - len(kept))
# net classes and rules live in the project file; pcbnew's save wrote finish_board's OSH Park class there, so set them last
import json
pf = os.path.join(DEST, PROJ + ".kicad_pro"); p = json.load(open(pf))
c = p["net_settings"]["classes"][0]; c.update(name="Default", clearance=0.2, track_width=0.25, via_diameter=0.6, via_drill=0.3)
pw = dict(c); pw.update(name="Power", clearance=0.25, track_width=0.6, via_diameter=0.8, via_drill=0.4, priority=0)
p["net_settings"]["classes"] = [c, pw]
p["net_settings"]["netclass_patterns"] = [{"netclass": "Power", "pattern": "VCC"}, {"netclass": "Power", "pattern": "GND"}]
p["board"]["design_settings"]["rules"].update(min_clearance=0.15, min_track_width=0.15, min_via_diameter=0.5,
    min_via_annular_width=0.13, min_through_hole_diameter=0.3, min_hole_clearance=0.25, min_hole_to_hole=0.5,
    min_copper_edge_clearance=0.5, min_text_height=0.8, min_text_thickness=0.15)
json.dump(p, open(pf, "w"), indent=2)
print("project rules: JLCPCB 2-layer; net classes Default 0.25 mm / 0.2 mm, Power (VCC, GND) 0.6 mm / 0.25 mm")
sys.stdout.flush(); os._exit(0)
