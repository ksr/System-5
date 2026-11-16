#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-30
"""Build the CPU Rev D board (unrouted) with KiCad's Python (pcbnew), from gen/netlist.py and the schematic's netlist.

  * a 36-pin card: 5.50 x 4.00 in (139.7 x 101.6 mm; Ken 2026-10-30: 0.25 in taller than the 30-pin cards, so the 36-pin
    connector clears the 0.15 in card-support strips), the bus connector J1 (s5cpu:C36) down the left edge, 5.7 mm in, as
    on the 30-pin cards, centred; the 3.00 x 0.15 in support strips along the top and bottom edges are copper keep-outs
  * the board layout rules (Ken, 2026-10-24): the front edge is the right edge (farthest from the bus): the RESET/RUN
    toggle, the LEDs and the DEBUG header J2 are there; the jumper blocks JP1-JP3 sit at the bottom edge outside the
    support strip; references and IC types on the silkscreen outside the parts; switch positions and LEDs labelled
  * 2 copper layers (Ken: 2 if at all possible), GND pours on both sides; routed afterwards by Freerouting
    (tools/kicad/kicad_route.py export_dsn / import_ses)
Writes ../cpu-rev-d.kicad_pcb."""
import os, sys, re
import pcbnew
HERE = os.path.dirname(os.path.abspath(__file__)); DEST = os.path.dirname(HERE); sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(DEST, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "kicad")); import kicad_route
import netlist as N
MM = pcbnew.FromMM; V = lambda x, y: pcbnew.VECTOR2I(MM(x), MM(y))
FPLIB = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"
BASE = os.path.join(ROOT, "hardware/bus/kicad/rev-d/s5bus-d.kicad_pcb")       # for its JLCPCB design rules only
NET = os.path.join(DEST, "reports", "netlist.net"); PROJ = "cpu-rev-d"

X0, Y0, W, H = 10.0, 10.0, 139.7, 101.6
XR, YB = X0 + W, Y0 + H                                     # the front (right) edge, the bottom edge
CY = Y0 + H / 2                                              # J1's centre line

# 1. base: the bus Rev D's board setup (rules, layers), none of its items
forms = kicad_route.top_forms(open(BASE).read())
keep = lambda f: not f.startswith(("(segment", "(via", "(arc", "(zone", "(gr_", "(net ", "(footprint", "(group", "(dimension"))
raw = os.path.join(DEST, "_base.kicad_pcb")
open(raw, "w").write("(kicad_pcb\n\t" + "\n\t".join(f for f in forms if keep(f)) + "\n)\n")
b = pcbnew.LoadBoard(raw); os.remove(raw)
b.SetCopperLayerCount(2)
r = pcbnew.PCB_SHAPE(b); r.SetShape(pcbnew.SHAPE_T_RECT); r.SetStart(V(X0, Y0)); r.SetEnd(V(XR, YB))
r.SetLayer(pcbnew.Edge_Cuts); r.SetWidth(MM(0.1)); b.Add(r)

# 2. parts: (x, y, rotation) of the footprint origin (a DIP's pin 1), mm
PLACE = {
    "J1": (X0 + 5.705, CY, -90),
    "U1": (24.0, 26.0, 0),                       # 1802, beside the bus: D0-D7 on its left row, A0-A7 on its right
    "U3": (48.0, 26.0, 0), "U2": (48.0, 66.0, 0),
    "U4": (70.0, 26.0, 0), "U5": (84.0, 26.0, 0), "U6": (98.0, 26.0, 0), "X1": (112.0, 26.0, 0),
    "U7": (70.0, 58.0, 0), "U8": (84.0, 58.0, 0), "U9": (98.0, 58.0, 0), "U10": (112.0, 80.0, 0),
    "RN1": (62.0, 92.0, 0), "RN2": (88.0, 92.0, 0),
    "C1": (34.0, 17.0, 0), "C12": (119.0, 87.0, 0), "R1": (104.0, 87.0, 0), "R2": (124.0, 38.0, 0), "D1": (104.0, 93.0, 0),
    "SW1": (XR - 15.2, 88.0, 180),               # bracket legs 2.5 mm in from the front edge, lever off the board
    "J2": (XR - 3.5, 22.0, 0),                   # DEBUG header at the front edge
    "JP1": (98.0, YB - 4.0, 90), "JP2": (114.0, YB - 6.5, 90), "JP3": (134.0, YB - 4.0, 90),
}
for k, ref in enumerate(("D2", "D3", "D4", "D5", "D6")):                  # LEDs down the front edge, below J2
    PLACE[ref] = (XR - 4.0, 46.0 + 6.0 * k, 90)
    PLACE["R%d" % (k + 3)] = (XR - 30.0, 46.0 + 6.0 * k, 0)
for k, u in enumerate(("U1", "U2", "U3", "U4", "U5", "U6", "U7", "U8", "U9", "X1")):   # 0.1 uF above each chip's pin 1
    x, y, _ = PLACE[u]; PLACE["C%d" % (k + 2)] = (x + 2.0, y + 7.5, 0) if u == "X1" else (x + 2.0, y - 4.5, 0)

for ref, (lib_id, value, fpid, pinmap) in N.PARTS.items():
    lib, name = fpid.split(":")
    fp = pcbnew.FootprintLoad(os.path.join(DEST if lib == "s5cpu" else FPLIB, lib + ".pretty"), name)
    fp.SetFPIDAsString(fpid); fp.SetReference(ref); fp.SetValue(value)
    x, y, rot = PLACE[ref]; fp.SetPosition(V(x, y)); fp.SetOrientationDegrees(rot)
    b.Add(fp)

# nets from the schematic netlist, and the symbol links for DRC's schematic parity
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
        if n: p.SetNet(netitem(n))
        else: p.SetNetCode(0)
for block in re.split(r'\n\t\t\(comp\s', s)[1:]:
    ref = re.search(r'\(ref "([^"]+)"\)', block); sp = re.search(r'\(sheetpath\s+\(names "[^"]*"\)\s+\(tstamps "([^"]+)"\)', block)
    ts = re.search(r'\n\t\t\t\(tstamps "([^"]+)"', block)
    fp = b.FindFootprintByReference(ref.group(1)) if ref else None
    if fp and sp and ts: fp.SetPath(pcbnew.KIID_PATH(sp.group(1).rstrip("/") + "/" + ts.group(1)))

# 3. keep-outs: the card-support strips (3.00 x 0.15 in along the top and bottom edges, from the bus edge)
def keepout(pts, layers):
    k = pcbnew.ZONE(b); k.SetIsRuleArea(True); k.SetLayerSet(layers)
    k.SetDoNotAllowTracks(True); k.SetDoNotAllowVias(True); k.SetDoNotAllowZoneFills(True)
    k.SetDoNotAllowPads(False); k.SetDoNotAllowFootprints(False)
    o = k.Outline(); o.NewOutline()
    for x, y in pts: o.Append(MM(x), MM(y))
    b.Add(k)
for ya, yb in ((Y0, Y0 + 3.81), (YB - 3.81, YB)):
    keepout([(X0, ya), (X0 + 76.2, ya), (X0 + 76.2, yb), (X0, yb)], pcbnew.LSET.AllCuMask())

# GND pours, both sides
for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
    z = pcbnew.ZONE(b); z.SetLayer(layer); z.SetNet(netitem("GND")); z.SetLocalClearance(MM(0.3))
    z.SetMinThickness(MM(0.25)); z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    o = z.Outline(); o.NewOutline()
    for x, y in ((X0 + 0.5, Y0 + 0.5), (XR - 0.5, Y0 + 0.5), (XR - 0.5, YB - 0.5), (X0 + 0.5, YB - 0.5)): o.Append(MM(x), MM(y))
    b.Add(z)

# 4. silkscreen: references and IC types outside the parts, labels by function (the board layout rules)
def silk(txt, x, y, h=1.0, angle=0, just=None):
    t = pcbnew.PCB_TEXT(b); t.SetText(txt); t.SetLayer(pcbnew.F_SilkS); t.SetTextSize(V(h, h))
    t.SetTextThickness(MM(max(0.18, 0.15 * h))); t.SetPosition(V(x, y))
    if just == "left": t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
    if just == "right": t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_RIGHT)
    if angle: t.SetTextAngleDegrees(angle)
    b.Add(t)
for fp in b.GetFootprints():
    fp.Reference().SetVisible(False); fp.Value().SetVisible(False)
def bbox(ref):
    bb = b.FindFootprintByReference(ref).GetBoundingBox(False)
    return pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetTop()), pcbnew.ToMM(bb.GetRight()), pcbnew.ToMM(bb.GetBottom())
for ref in [r for r in N.PARTS if r.startswith(("U", "X"))]:                     # chips: "U3 2732" below the body
    l, t, rr, bt = bbox(ref)
    silk("%s %s" % (ref, N.PARTS[ref][1]), (l + rr) / 2, bt + 1.2, 1.0)
for ref in [r for r in N.PARTS if r[0] in "RC" or r.startswith("RN")]:          # passives: "R1 10k" above (C11: below)
    l, t, rr, bt = bbox(ref)
    silk("%s %s" % (ref, N.PARTS[ref][1]), (l + rr) / 2, (bt + 1.0) if ref == "C11" else (t - 0.9), 1.0)
for ref in ("D2", "D3", "D4", "D5", "D6"):                                       # LEDs: by function, to the right
    l, t, rr, bt = bbox(ref)
    silk(N.PARTS[ref][1], l - 1.0, (t + bt) / 2, 1.0, just="right")
l, t, rr, bt = bbox("D1"); silk("D1 BAT85", (l + rr) / 2, bt + 1.2, 1.0)
l, t, rr, bt = bbox("SW1"); silk("SW1", l + 3.0, t - 1.2, 1.2)
silk("RESET", XR - 6.0, t - 1.2, 1.2); silk("RUN", XR - 6.0, bt + 1.4, 1.2)    # the toggle's two positions
l, t, rr, bt = bbox("J2"); silk("J2 DEBUG", rr, t - 1.2, 1.0, just="right")
for k, name in enumerate(("EXT CLK", "GND", "CLOCK", "SC0", "SC1", "GND")):
    silk(name, l - 0.8, 22.0 + 2.54 * k, 0.9, just="right")
l, t, rr, bt = bbox("JP1"); silk("JP1 CLK", (l + rr) / 2, t - 0.9, 1.0); silk("INT", l - 0.6, YB - 4.0, 0.9, just="right")
silk("EXT", rr + 0.6, YB - 4.0, 0.9, just="left")
l, t, rr, bt = bbox("JP2"); silk("JP2 EF1-4", (l + rr) / 2, t - 0.9, 1.0)
l, t, rr, bt = bbox("JP3"); silk("JP3 -EF>EF3", (l + rr) / 2, t - 0.9, 1.0)
def bus_labels(b):
    """the bus connector's pins named on the silkscreen, beside each pad on the board side (as on the bus Rev D's slots)"""
    for p in b.FindFootprintByReference("J1").Pads():
        c = p.GetPosition()
        silk(N.POS[int(p.GetNumber()) - 1], pcbnew.ToMM(c.x) + 1.3, pcbnew.ToMM(c.y), 1.0, just="left")
bus_labels(b)
silk("S5CPU-D", 60.0, YB - 14.0, 2.0)
silk("System-5 CPU  Rev D  2026", 60.0, YB - 11.0, 1.5)
silk("cottageworker.com", 60.0, YB - 8.6, 1.5)

pcbnew.SaveBoard(os.path.join(DEST, PROJ + ".kicad_pcb"), b)
print("board: %d footprints, %d nets" % (len(b.GetFootprints()), len(nets)))
