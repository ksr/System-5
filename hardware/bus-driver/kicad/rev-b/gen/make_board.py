#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-06
"""Build the BUSDRV-B board (unrouted) with KiCad's Python (pcbnew).
  1. start from the Memory Rev D board, kept only for the System-5 card outline and the 30-pin bus connector (same
     position on every System-5 card); everything else is dropped at the text level
  2. place KiCad stock footprints for every part in gen/netlist.py; nets from the schematic netlist
  3. JLCPCB 2-layer rules (copper layer count forced to 2), GND pours both sides, silkscreen labels and title
Writes ../busdrv-b.kicad_pcb; route afterwards with tools/kicad/kicad_route.py + Freerouting."""
import os, sys, re, json
import pcbnew
HERE = os.path.dirname(os.path.abspath(__file__)); DEST = os.path.dirname(HERE); sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(DEST, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "kicad")); import kicad_route
import netlist as N
MM = pcbnew.FromMM; V = lambda x, y: pcbnew.VECTOR2I(MM(x), MM(y))
FPLIB = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"
BASE = os.path.join(ROOT, "hardware/memory/kicad/rev-d/memory-rev-d.kicad_pcb")
NET = os.path.join(DEST, "reports", "netlist.net"); PROJ = "busdrv-b"

# 1. base: outline + bus connector only
forms = kicad_route.top_forms(open(BASE).read())
def keep(f):
    if f.startswith(("(segment", "(via", "(arc", "(zone", "(gr_text", "(net ")): return False
    if f.startswith("(footprint"): return bool(re.search(r'\(property "Reference" "U\$1"', f))
    if f.startswith(("(gr_line", "(gr_rect", "(gr_arc", "(gr_poly", "(gr_circle")): return '(layer "Edge.Cuts")' in f
    return True
raw = os.path.join(DEST, "_base.kicad_pcb")
open(raw, "w").write("(kicad_pcb\n\t" + "\n\t".join(f for f in forms if keep(f)) + "\n)\n")
b = pcbnew.LoadBoard(raw); os.remove(raw)
b.SetCopperLayerCount(2)          # the base board is a 4-layer Eagle import: without this, Freerouting used In1/In2 (Rev A as ordered 2026-10-09)
j1 = b.FindFootprintByReference("U$1"); j1.SetReference("J1"); j1.SetFPIDAsString("busdrv:C30"); j1.SetValue("System-5 bus")

# 2. parts: (x, y, rotation) of the footprint origin, mm; tuned so nothing overlaps (checked below)
PLACE = {
    "U1": (40.0, 30.0, 90), "U2": (40.0, 66.0, 90),
    "C1": (77.0, 25.0, 90), "C2": (77.0, 61.0, 90), "C3": (23.36, 15.57, 0),
    "A1": (108.3, 46.8, 90),
    "R1": (94.0, 60.0, 0), "R2": (94.0, 66.0, 0), "R3": (94.0, 72.0, 0), "R4": (110.0, 60.0, 0), "R5": (110.0, 66.0, 0),
    "J2": (98.0, 84.0, 90),
    "R6": (130.03, 96.86, 0), "D1": (141.47, 96.86, 0),
}
for ref, (lib_id, value, fpid, pinmap) in N.PARTS.items():
    if ref == "J1": continue
    lib, name = fpid.split(":")
    fp = pcbnew.FootprintLoad(os.path.join(DEST if lib == "busdrv" else FPLIB, lib + ".pretty"), name)
    fp.SetFPIDAsString(fpid); fp.SetReference(ref); fp.SetValue(value)
    x, y, rot = PLACE[ref]; fp.SetPosition(V(x, y)); fp.SetOrientationDegrees(rot)
    b.Add(fp)

# nets from the schematic netlist
s = open(NET).read(); padnet = {}
for name, body in re.findall(r'\(net\s+\(code "\d+"\)\s+\(name "([^"]+)"\)(.*?)(?=\n\t\t\(net\s|\n\t\)\n\))', s, re.S):
    for ref, pad in re.findall(r'\(node\s+\(ref "([^"]+)"\)\s+\(pin "([^"]+)"\)', body): padnet[(ref, pad)] = name
nets = {}
def netitem(n):
    if n not in nets: ni = pcbnew.NETINFO_ITEM(b, n); b.Add(ni); nets[n] = ni
    return nets[n]
for fp in b.GetFootprints():
    for p in fp.Pads():
        n = padnet.get((fp.GetReference(), p.GetNumber()))
        if n: p.SetNet(netitem(n))          # unused pins keep the schematic's "unconnected-(...)" net, as KiCad expects
        else: p.SetNetCode(0)
# symbol links (sheet path + symbol uuid) so DRC's schematic parity works
for block in re.split(r'\n\t\t\(comp\s', s)[1:]:
    ref = re.search(r'\(ref "([^"]+)"\)', block); sp = re.search(r'\(sheetpath\s+\(names "[^"]*"\)\s+\(tstamps "([^"]+)"\)', block)
    ts = re.search(r'\n\t\t\t\(tstamps "([^"]+)"', block)
    fp = b.FindFootprintByReference(ref.group(1)) if ref else None
    if fp and sp and ts: fp.SetPath(pcbnew.KIID_PATH(sp.group(1).rstrip("/") + "/" + ts.group(1)))

# 3. silkscreen
def silk(txt, x, y, h=1.0, angle=0):
    t = pcbnew.PCB_TEXT(b); t.SetText(txt); t.SetLayer(pcbnew.F_SilkS); t.SetTextSize(V(h, h))
    t.SetTextThickness(MM(max(0.15, 0.15 * h))); t.SetPosition(V(x, y))
    if angle: t.SetTextAngleDegrees(angle)
    b.Add(t)
for ref, (l1, l2) in N.LABELS.items():
    fp = b.FindFootprintByReference(ref); c = fp.GetBoundingBox(False).GetCenter(); cx, cy = pcbnew.ToMM(c.x), pcbnew.ToMM(c.y)
    fp.Reference().SetVisible(False); fp.Value().SetVisible(False)
    silk(l1, cx, cy - 0.75); silk(l2, cx, cy + 0.75)
for fp in b.GetFootprints():          # resistors and capacitors: "<ref> <value>" above the part; D1, J2 by their own labels
    r = fp.GetReference()
    if r[0] in "RC" or r in ("D1", "J2"):
        fp.Value().SetVisible(False); fp.Reference().SetVisible(False)
        if r[0] in "RC":
            bb = fp.GetBoundingBox(False, False)
            if fp.GetOrientationDegrees() % 180 == 0:
                silk("%s %s" % (r, fp.GetValue()), pcbnew.ToMM(bb.GetCenter().x), pcbnew.ToMM(bb.GetTop()) - 0.9, 1.0)
            else:
                silk("%s %s" % (r, fp.GetValue()), pcbnew.ToMM(bb.GetRight()) + 1.0, pcbnew.ToMM(bb.GetCenter().y), 1.0, 90)
j2 = b.FindFootprintByReference("J2"); jb = j2.GetBoundingBox(False)
silk("SPARE OUT  1  2  3  4  +5V  GND", pcbnew.ToMM(jb.GetCenter().x), pcbnew.ToMM(jb.GetTop()) - 1.5, 1.0)
d1 = b.FindFootprintByReference("D1"); silk("PWR", pcbnew.ToMM(d1.GetPosition().x) + 6.0, pcbnew.ToMM(d1.GetPosition().y), 1.5, 90)
ebb = b.GetBoardEdgesBoundingBox()
silk("BUSDRV-B   System-5 bus driver   2026", pcbnew.ToMM(ebb.GetCenter().x), pcbnew.ToMM(ebb.GetBottom()) - 1.6, 1.2)

# GND pours both sides
for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
    z = pcbnew.ZONE(b); z.SetLayer(layer); z.SetNet(netitem("GND")); o = z.Outline(); o.NewOutline(); i = MM(0.5)
    for x, y in ((ebb.GetLeft() + i, ebb.GetTop() + i), (ebb.GetRight() - i, ebb.GetTop() + i), (ebb.GetRight() - i, ebb.GetBottom() - i), (ebb.GetLeft() + i, ebb.GetBottom() - i)):
        o.Append(x, y)
    z.SetLocalClearance(MM(0.3)); z.SetMinThickness(MM(0.25)); z.SetThermalReliefGap(MM(0.3)); z.SetThermalReliefSpokeWidth(MM(0.4))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL); b.Add(z)

ds = b.GetDesignSettings()
ds.m_MinClearance = MM(0.15); ds.m_TrackMinWidth = MM(0.15); ds.m_ViasMinSize = MM(0.5); ds.m_MinThroughDrill = MM(0.3)
ds.m_ViasMinAnnularWidth = MM(0.13); ds.m_HoleClearance = MM(0.25); ds.m_HoleToHoleMin = MM(0.5); ds.m_CopperEdgeClearance = MM(0.5)
out = os.path.join(DEST, PROJ + ".kicad_pcb"); b.SetFileName(out); pcbnew.SaveBoard(out, b)

# overlap check (footprint bodies, without text) and USB direction
fps = list(b.GetFootprints()); bad = []
for i in range(len(fps)):
    for k in range(i + 1, len(fps)):
        A = fps[i].GetBoundingBox(False, False); B = fps[k].GetBoundingBox(False, False)
        if A.Intersects(B): bad.append((fps[i].GetReference(), fps[k].GetReference()))
a1 = b.FindFootprintByReference("A1"); p1 = [p for p in a1.Pads() if p.GetNumber() == "1"][0]; p15 = [p for p in a1.Pads() if p.GetNumber() == "15"][0]
print("overlaps:", bad or "none")
print("Nano: USB end (pin 15 side) at x %.1f, pin 1 at x %.1f, board edge x %.1f" % (pcbnew.ToMM(p15.GetPosition().x), pcbnew.ToMM(p1.GetPosition().x), pcbnew.ToMM(ebb.GetRight())))
ab = a1.GetBoundingBox(False, False); print("Nano body x %.1f-%.1f y %.1f-%.1f" % tuple(pcbnew.ToMM(v) for v in (ab.GetLeft(), ab.GetRight(), ab.GetTop(), ab.GetBottom())))
# project net classes
pf = os.path.join(DEST, PROJ + ".kicad_pro"); p = json.load(open(pf))
c = p["net_settings"]["classes"][0]; c.update(name="Default", clearance=0.2, track_width=0.25, via_diameter=0.6, via_drill=0.3)
pw = dict(c); pw.update(name="Power", clearance=0.25, track_width=0.6, via_diameter=0.8, via_drill=0.4, priority=0)
p["net_settings"]["classes"] = [c, pw]
p["net_settings"]["netclass_patterns"] = [{"netclass": "Power", "pattern": "+5V"}, {"netclass": "Power", "pattern": "GND"}]
p["board"]["design_settings"]["rules"].update(min_clearance=0.15, min_track_width=0.15, min_via_diameter=0.5, min_via_annular_width=0.13,
    min_through_hole_diameter=0.3, min_hole_clearance=0.25, min_hole_to_hole=0.5, min_copper_edge_clearance=0.5, min_text_height=0.8, min_text_thickness=0.15)
json.dump(p, open(pf, "w"), indent=2)
print("wrote", out, len(fps), "footprints"); sys.stdout.flush(); os._exit(0)
