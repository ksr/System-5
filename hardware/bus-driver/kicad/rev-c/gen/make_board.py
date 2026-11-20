#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-18 (from the IO panel's make_board.py)
"""Build the BUSDRV-C board (unrouted) with KiCad's Python (pcbnew), from gen/netlist.py and the schematic's netlist.

  * a 36-pin card like CPU Rev D and the IO panel: 5.50 x 4.00 in (139.7 x 101.6 mm), J1 (s5bd:C36) down the left edge,
    centred, the 3.00 x 0.15 in card-support strips along the top and bottom edges as copper keep-outs
  * the three MCP23017s in a column beside the bus connector, each with its 0.1 uF; the Nano at the front (right) edge
    with its USB facing out; the cable headers at the front edge: J4 DEBUG (the keyed 2x3 that matches CPU Rev D's J2),
    J2 (CLK OUT, the probes, SPARE1-4, +5V, GND) and J3 (SPARE5-11, GND), every pin named on the silkscreen; the PWR LED
    at the front, labelled by its function (the board layout rules)
  * 2 copper layers, GND pours on both sides; routed afterwards by Freerouting
Writes ../busdrv-c.kicad_pcb."""
import os, sys, re, json
import pcbnew
HERE = os.path.dirname(os.path.abspath(__file__)); DEST = os.path.dirname(HERE); sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(DEST, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "kicad")); import kicad_route
import netlist as N
MM = pcbnew.FromMM; V = lambda x, y: pcbnew.VECTOR2I(MM(x), MM(y))
FPLIB = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"
BASE = os.path.join(ROOT, "hardware/bus/kicad/rev-d/s5bus-d.kicad_pcb")       # for its JLCPCB design rules only
NET = os.path.join(DEST, "reports", "netlist.net"); PROJ = "busdrv-c"

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
PLACE = {"J1": (X0 + 5.705, CY, 90),
         # the expanders on end (pin 1 at the left, GPB0-7 and VDD/VSS along the bottom row, GPA7-0 along the top)
         "U1": (30.0, 32.0, 90), "U2": (30.0, 57.0, 90), "U3": (30.0, 82.0, 90),
         "C1": (51.6, 35.5, 0), "C2": (51.6, 60.5, 0), "C3": (51.6, 85.5, 0), "C4": (26.0, 17.0, 0),
         # the Nano at the front edge, USB out (its pin 15 / 16 end): pins 1-15 along y = 52, 30-16 along y = 36.76
         "U4": (107.24, 52.0, 90),
         # the I2C pull-ups, the expanders' reset pull-up and the bus sense divider between the expanders and the Nano
         "R1": (72.0, 30.0, 0), "R2": (72.0, 36.0, 0), "R3": (72.0, 42.0, 0), "R4": (72.0, 48.0, 0), "R5": (72.0, 54.0, 0),
         # CLK OUT's series resistor and the probes' 1k, under the Nano by D8 / D9 / A1
         "R7": (118.0, 60.0, 0), "R8": (118.0, 66.0, 0), "R9": (118.0, 72.0, 0),
         # the front edge, top to bottom: the PWR LED, the DEBUG header, J2, J3
         "R6": (112.0, 14.0, 0), "LED1": (126.0, 14.0, 0),
         "J4": (142.0, 18.0, 0), "J2": (146.0, 59.0, 0), "J3": (146.0, 86.0, 0)}

for ref, (lib_id, value, fpid, pinmap) in N.PARTS.items():
    lib, name = fpid.split(":")
    fp = pcbnew.FootprintLoad(os.path.join(DEST if lib == "s5bd" else FPLIB, lib + ".pretty"), name)
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

def keepout(pts, layers, fill=False):
    k = pcbnew.ZONE(b); k.SetIsRuleArea(True); k.SetLayerSet(layers)
    k.SetDoNotAllowTracks(True); k.SetDoNotAllowVias(True); k.SetDoNotAllowZoneFills(not fill)
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

# silkscreen (gen/silk.py): every reference and value outside its part, the LED, headers and debug header by function,
# and every text at 270, upright with the card standing in the bus (Ken, 2026-11-18)
import silk
if not silk.add(b).report():                    # every label placed, or the build stops (2026-11-18: J1's
    raise SystemExit("make_board: silkscreen labels left out")   # -PAUSE had been left out unnoticed)

def overlaps(b):
    """pairs of parts whose courtyards overlap (the board must have none)"""
    cy = []
    for fp in b.GetFootprints():
        c = fp.GetCourtyard(pcbnew.F_CrtYd)
        if c.OutlineCount(): cy.append((fp.GetReference(), c.BBox()))
    return [(a, bb) for i, (a, ba) in enumerate(cy) for bb_, (bb, bbx) in enumerate(cy[i + 1:]) if ba.Intersects(bbx)]
ov = overlaps(b)
print("courtyard overlaps:", ", ".join("%s/%s" % pr for pr in ov) if ov else "none")
pcbnew.SaveBoard(os.path.join(DEST, PROJ + ".kicad_pcb"), b)

# the Power net class, written into the project after SaveBoard (which rewrites the project file): +5V 0.5 mm wide, as
# CPU Rev D's and the IO panel's (pcb-check wants power on planes or on tracks of 0.5 mm or more; GND has its pours)
pf = os.path.join(DEST, PROJ + ".kicad_pro"); pj = json.load(open(pf))
c = pj["net_settings"]["classes"][0]
pw = dict(c); pw.update(name="Power", track_width=0.5, priority=0)
pj["net_settings"]["classes"] = [c, pw]
pj["net_settings"]["netclass_patterns"] = [{"netclass": "Power", "pattern": "+5V"}]
json.dump(pj, open(pf, "w"), indent=2)
print("board: %d footprints, %d nets" % (len(b.GetFootprints()), len(nets)))
