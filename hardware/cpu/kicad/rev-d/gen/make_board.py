#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-30
"""Build the CPU Rev D board (unrouted) with KiCad's Python (pcbnew), from gen/netlist.py and the schematic's netlist.

  * a 36-pin card: 5.50 x 4.00 in (139.7 x 101.6 mm; Ken 2026-10-30: 0.25 in taller than the 30-pin cards, so the 36-pin
    connector clears the 0.15 in card-support strips), the bus connector J1 (s5cpu:C36) down the left edge, 5.7 mm in, as
    on the 30-pin cards, centred; the 3.00 x 0.15 in support strips along the top and bottom edges are copper keep-outs
  * the board layout rules (Ken, 2026-10-24): the front edge is the right edge (farthest from the bus): the RESET/RUN
    toggle (a Marquardt 9070-1W, YACC1's, since 2026-11-18), the LEDs and the DEBUG header J2 are there; the EF blocks
    JP2-JP5 sit along the bottom edge, 1.5 in from the front corner since 2026-11-18 and clear of the support strip;
    JP1 (CLK INT/EXT) at the top edge between the oscillator and J2 since then (Ken: "move the jp1 between osc and
    jp2", read as J2); references and IC types on the silkscreen outside the parts; switch positions and LEDs labelled
  * 2 copper layers (Ken: 2 if at all possible), GND pours on both sides; routed afterwards by Freerouting, from gen/build.sh:
    gen/route.py writes its input in a fixed order (tools/kicad/dsn_order.py), so the board routes the same way every
    time, and the project's Power class (cpu-rev-d.kicad_pro) routes +5V 0.5 mm wide (2026-11-17)
  * the silkscreen (gen/silk.py; every text at 270 since 2026-11-18, upright with the card standing in the bus); every
    reference and value on it (pcb-check, 2026-11-17): "J1 BUS" along the bus edge; the LEDs are
    LED1-LED5, not D2-D6, labelled by their function alone (Ken, 2026-11-18: PWR, Q, PAUSE, RESET, ROM; pcb-check.ini
    exempts their references), and D1 carries its own reference field, because J1's pin labels name the data lines
    D0-D7 and pcb-check took those for the parts' references
Writes ../cpu-rev-d.kicad_pcb."""
import os, sys, re, json
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
EFX, EFY = 120.0 - 38.1, 98.4                                 # the EF blocks: first block's pin 1. 1.5 in nearer the bus
#   than at first (Ken, 2026-11-18: "move 4 ef jumpers down about 1.5 inches", down with the card standing), and 2 mm
#   further from the bottom edge, so that JP2's last row and its name stay out of the card-support strip (to x 86.2)
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
    "J1": (X0 + 5.705, CY, 90),
    "U1": (24.0, 26.0, 0),                       # 1802, beside the bus: D0-D7 on its left row, A0-A7 on its right
    "U3": (48.0, 26.0, 0), "U2": (48.0, 66.0, 0),
    "U4": (70.0, 26.0, 0), "U5": (84.0, 26.0, 0), "U6": (98.0, 26.0, 0), "X1": (112.0, 26.0, 0),
    "U7": (70.0, 58.0, 0), "U8": (84.0, 58.0, 0), "U9": (98.0, 58.0, 0), "U10": (112.0, 80.0, 0),
    "RN1": (62.0, 92.0, 0), "RN2": (88.0, 92.0, 0),
    "C1": (34.0, 17.0, 0), "C12": (119.0, 87.0, 0), "R1": (104.0, 87.0, 0), "R2": (124.0, 38.0, 0), "D1": (104.0, 93.0, 0),
    "SW1": (XR - 11.7, 88.0, 180),               # a Marquardt 9070-1W, YACC1's RESET/RUN toggle (Ken, 2026-11-18): origin on
                                                 # the common, the body flush with the front edge, bushing and lever past it
    "J2": (XR - 6.7, 20.0, 0),                   # DEBUG, the keyed 2x3 header (pin 1), at the front edge
    "JP1": (128.0, 17.0, 0),                     # CLK INT/EXT, between the oscillator X1 and the DEBUG header J2, whose
                                                 # EXT CLK it picks, at the top edge (Ken, 2026-11-18; it was at the bottom edge)
    # JP2-JP5: the EF blocks, one per 1802 flag input, upright (rows = -EF1, -EF2, -EF3, -EF) in a row below SW1
    **{"JP%d" % (k + 2): (EFX + 8.0 * k, EFY, 0) for k in range(4)},
}
for k, ref in enumerate(("LED1", "LED2", "LED3", "LED4", "LED5")):        # LEDs down the front edge, below J2
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

# 4. silkscreen (gen/silk.py): every reference and value outside its part, the LEDs, switch, jumpers and debug header by
#    function, and every text at 270, upright with the card standing in the bus (Ken, 2026-11-18)
import silk
if not silk.add(b).report():                    # every label placed, or the build stops (2026-11-18: J1's
    raise SystemExit("make_board: silkscreen labels left out")   # -PAUSE had been left out unnoticed)

pcbnew.SaveBoard(os.path.join(DEST, PROJ + ".kicad_pcb"), b)

# the Power net class, written into the project after SaveBoard (which rewrites the project file): +5V 0.5 mm wide
# (pcb-check wants power on planes or on tracks of 0.5 mm or more; 2026-11-17). Not GND: its pours on both sides count
# as a plane, and 0.5 mm GND tracks as well left Freerouting no way past the EPROM's address pins (A0-A2 at U3)
pf = os.path.join(DEST, PROJ + ".kicad_pro"); pj = json.load(open(pf))
c = pj["net_settings"]["classes"][0]
pw = dict(c); pw.update(name="Power", track_width=0.5, priority=0)
pj["net_settings"]["classes"] = [c, pw]
pj["net_settings"]["netclass_patterns"] = [{"netclass": "Power", "pattern": "+5V"}]
json.dump(pj, open(pf, "w"), indent=2)
print("board: %d footprints, %d nets" % (len(b.GetFootprints()), len(nets)))
