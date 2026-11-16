#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-30 (from CPU Rev D's make_board.py)
"""Build the IO panel Rev A board (unrouted) with KiCad's Python (pcbnew), from gen/netlist.py and the schematic's netlist.

  * a 36-pin card like CPU Rev D: 5.50 x 4.00 in (139.7 x 101.6 mm), J1 (s5io:C36) down the left edge, centred, the
    3.00 x 0.15 in card-support strips along the top and bottom edges as copper keep-outs
  * the front panel laid out as on Ken's YACC1 IO card (Ken, 2026-10-30): the LEDs in a column at the front (right) edge,
    each with its resistor, the two TIL311s at the front edge below them, a column of vertical M9040P toggles just inside
    (BIT 7 at the top ... BIT 0, then RUN/RESET and LOAD), the INPUT push-button below them; every switch position and
    LED labelled on the silkscreen (the board layout rules)
  * 2 copper layers, GND pours on both sides; routed afterwards by Freerouting
Writes ../io-panel-rev-a.kicad_pcb."""
import os, sys, re
import pcbnew
HERE = os.path.dirname(os.path.abspath(__file__)); DEST = os.path.dirname(HERE); sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(DEST, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "kicad")); import kicad_route
import netlist as N
MM = pcbnew.FromMM; V = lambda x, y: pcbnew.VECTOR2I(MM(x), MM(y))
FPLIB = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"
BASE = os.path.join(ROOT, "hardware/bus/kicad/rev-d/s5bus-d.kicad_pcb")       # for its JLCPCB design rules only
NET = os.path.join(DEST, "reports", "netlist.net"); PROJ = "io-panel-rev-a"

X0, Y0, W, H = 10.0, 10.0, 139.7, 101.6
XR, YB = X0 + W, Y0 + H
CY = Y0 + H / 2

forms = kicad_route.top_forms(open(BASE).read())
keep = lambda f: not f.startswith(("(segment", "(via", "(arc", "(zone", "(gr_", "(net ", "(footprint", "(group", "(dimension"))
raw = os.path.join(DEST, "_base.kicad_pcb")
open(raw, "w").write("(kicad_pcb\n\t" + "\n\t".join(f for f in forms if keep(f)) + "\n)\n")
b = pcbnew.LoadBoard(raw); os.remove(raw)
b.SetCopperLayerCount(2)
r = pcbnew.PCB_SHAPE(b); r.SetShape(pcbnew.SHAPE_T_RECT); r.SetStart(V(X0, Y0)); r.SetEnd(V(XR, YB))
r.SetLayer(pcbnew.Edge_Cuts); r.SetWidth(MM(0.1)); b.Add(r)

# placement: (x, y, rotation) of each footprint's origin, mm
LX, RX, TX = XR - 4.0, XR - 22.0, XR - 36.0           # LED column, LED resistor column, toggle column
PLACE = {"J1": (X0 + 5.705, CY, -90)}
for k in range(8):                                     # BIT 7 at the top, as on the YACC1 card
    PLACE["SW%d" % (k + 1)] = (TX, 20.0 + 9.0 * (7 - k), 90)                     # toggles: 9 mm pitch (bodies 8.6 mm)
    y = 16.0 + 7.0 * (7 - k)
    PLACE["D%d" % (k + 1)] = (LX, y - 1.27, 90); PLACE["R%d" % (k + 1)] = (RX, y, 0)
PLACE.update({"SW10": (TX, 20.0 + 9.0 * 8, 90), "SW11": (TX, 20.0 + 9.0 * 9, 90), "SW9": (TX - 22.0, 98.0, 0),
              "D9": (LX, 70.73, 90), "R10": (RX, 72.0, 0), "D10": (LX, 76.73, 90), "R11": (RX, 78.0, 0),
              "U7": (XR - 19.0, 100.0, 0), "U8": (XR - 6.5, 100.0, 0)})
PLACE.update({                                         # the logic, between the bus and the panel
    "U1": (24.0, 84.0, 0), "U5": (38.0, 22.0, 0), "U6": (52.0, 22.0, 0), "U4": (66.0, 22.0, 0),
    "U2": (24.0, 56.0, 0), "U3": (40.0, 56.0, 0), "U9": (56.0, 56.0, 0), "U10": (70.0, 56.0, 0),
    "U11": (84.0, 56.0, 0),
    "R9": (84.0, 22.0, 0), "C1": (84.0, 28.0, 0), "C2": (46.0, 90.0, 0)})
for k, u in enumerate(("U1", "U2", "U3", "U4", "U5", "U6", "U7", "U8", "U9", "U10", "U11")):
    x, y, _ = PLACE[u]
    PLACE["C%d" % (k + 3)] = ((x - 3.0, y - 15.5, 0) if u in ("U7", "U8") else (x + 11.0, y + 6.0, 90) if u == "U1"
                             else (x + 2.0, y - 4.5, 0))

for ref, (lib_id, value, fpid, pinmap) in N.PARTS.items():
    lib, name = fpid.split(":")
    fp = pcbnew.FootprintLoad(os.path.join(DEST if lib == "s5io" else FPLIB, lib + ".pretty"), name)
    fp.SetFPIDAsString(fpid); fp.SetReference(ref); fp.SetValue(value)
    x, y, rot = PLACE[ref]; fp.SetPosition(V(x, y)); fp.SetOrientationDegrees(rot)
    b.Add(fp)

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

def keepout(pts, layers):
    k = pcbnew.ZONE(b); k.SetIsRuleArea(True); k.SetLayerSet(layers)
    k.SetDoNotAllowTracks(True); k.SetDoNotAllowVias(True); k.SetDoNotAllowZoneFills(True)
    k.SetDoNotAllowPads(False); k.SetDoNotAllowFootprints(False)
    o = k.Outline(); o.NewOutline()
    for x, y in pts: o.Append(MM(x), MM(y))
    b.Add(k)
for ya, yb in ((Y0, Y0 + 3.81), (YB - 3.81, YB)):
    keepout([(X0, ya), (X0 + 76.2, ya), (X0 + 76.2, yb), (X0, yb)], pcbnew.LSET.AllCuMask())
for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
    z = pcbnew.ZONE(b); z.SetLayer(layer); z.SetNet(netitem("GND")); z.SetLocalClearance(MM(0.3))
    z.SetMinThickness(MM(0.25)); z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    o = z.Outline(); o.NewOutline()
    for x, y in ((X0 + 0.5, Y0 + 0.5), (XR - 0.5, Y0 + 0.5), (XR - 0.5, YB - 0.5), (X0 + 0.5, YB - 0.5)): o.Append(MM(x), MM(y))
    b.Add(z)

# silkscreen
def silk(txt, x, y, h=1.0, angle=0, just=None):
    t = pcbnew.PCB_TEXT(b); t.SetText(txt); t.SetLayer(pcbnew.F_SilkS); t.SetTextSize(V(h, h))
    t.SetTextThickness(MM(max(0.18, 0.15 * h))); t.SetPosition(V(x, y))
    if just == "left": t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
    if just == "right": t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_RIGHT)
    if angle: t.SetTextAngleDegrees(angle)
    b.Add(t)
for fp in b.GetFootprints():
    fp.Reference().SetVisible(False); fp.Value().SetVisible(False)
    for item in fp.GraphicalItems():                     # the YACC1 footprints carry their own text: hide it
        if isinstance(item, pcbnew.PCB_TEXT): item.SetVisible(False)
def bbox(ref):
    bb = b.FindFootprintByReference(ref).GetBoundingBox(False)
    return pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetTop()), pcbnew.ToMM(bb.GetRight()), pcbnew.ToMM(bb.GetBottom())
def pad(ref, n):
    c = b.FindFootprintByReference(ref).FindPadByNumber(n).GetPosition(); return pcbnew.ToMM(c.x), pcbnew.ToMM(c.y)
for ref in [r for r in N.PARTS if r.startswith("U")]:
    l, t, rr, bt = bbox(ref)
    if ref in ("U7", "U8"): continue                     # the TIL311s: labelled above their capacitors, below
    silk("%s %s" % (ref, N.PARTS[ref][1]), (l + rr) / 2, bt + 1.2, 1.0)
for ref in [r for r in N.PARTS if r[0] in "RC"]:
    l, t, rr, bt = bbox(ref)
    if ref in ("C9", "C10"): silk(ref, rr + 0.6, (t + bt) / 2, 1.0, just="left"); continue   # the TIL311s' caps: name beside
    if ref == "C3": silk("C3 0.1uF", l + 0.2, t - 0.9, 1.0, just="left"); continue          # U1's cap: label clear of U1's pins
    silk("%s %s" % (ref, N.PARTS[ref][1]), (l + rr) / 2, t - 0.9, 1.0)
for k in range(8):                                       # LEDs: BIT n beside each; toggles: the bit, 1 and 0 at its ends
    l, t, rr, bt = bbox("D%d" % (k + 1)); silk("%d" % k, l - 0.8, (t + bt) / 2, 1.0, just="right")
for ref, label in (("D9", "Q"), ("D10", "PWR")):
    l, t, rr, bt = bbox(ref); silk(label, l - 0.8, (t + bt) / 2, 1.0, just="right")
def toggle(ref, name, at1, at3):
    """a toggle closes the common to the end AWAY from its lever: label each end with what the lever there selects"""
    (x1, y1), (x3, y3) = pad(ref, "1"), pad(ref, "3")
    l, t, rr, bt = bbox(ref)
    silk(name, l - 4.2, (t + bt) / 2, 1.0, just="right")
    silk(at3, x3 + (2.2 if x3 > x1 else -2.2), y3, 0.9, just="left" if x3 > x1 else "right")      # lever at pin 3: pin 1
    silk(at1, x1 + (2.2 if x1 > x3 else -2.2), y1, 0.9, just="left" if x1 > x3 else "right")      # lever at pin 1: pin 3
for k in range(8): toggle("SW%d" % (k + 1), "BIT %d" % k, "0", "1")     # pin 1 = +5V, pin 3 = GND
toggle("SW10", "RUN/RESET", "RUN", "RESET")                              # pin 1 = -RESET: lever at pin 3 grounds it
toggle("SW11", "LOAD", "OFF", "LOAD")                                    # pin 1 = -PAUSE
l, t, rr, bt = bbox("SW9"); silk("INPUT", l - 0.8, (t + bt) / 2, 1.2, just="right")
for ref, txt in (("U7", "U7 TIL311 7-4"), ("U8", "U8 TIL311 3-0")):
    l, t, rr, bt = bbox(ref); silk(txt, (l + rr) / 2, t - 1.0, 1.0)
for p in b.FindFootprintByReference("J1").Pads():       # the bus pins named beside the connector
    c = p.GetPosition()
    silk(N.POS[int(p.GetNumber()) - 1], pcbnew.ToMM(c.x) + 1.3, pcbnew.ToMM(c.y), 1.0, just="left")
silk("S5IO-A", 60.0, YB - 14.0, 2.0)
silk("System-5 IO panel  Rev A  2026", 60.0, YB - 11.0, 1.5)
silk("cottageworker.com", 60.0, YB - 8.6, 1.5)

pcbnew.SaveBoard(os.path.join(DEST, PROJ + ".kicad_pcb"), b)
print("board: %d footprints, %d nets" % (len(b.GetFootprints()), len(nets)))
