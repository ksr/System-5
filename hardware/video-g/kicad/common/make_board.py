#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-01
"""make_board.py BOARD_DIR - build a VIDEO-G board (unrouted) with KiCad's Python (pcbnew).

  1. the System-5 card: the bus edge at x = 10.025 with the 30-pin connector where every System-5 card has it
     (J1 at 15.735, 58.12, -90: bus-driver Rev B), 96.19 mm along the backplane, gen/place.py's LENGTH from the bus
     edge to the front edge; the card-guide keep-outs (3.00" x 0.15" at both sides, from the bus edge)
  2. KiCad stock footprints (and kicad/lib/video-g-local) for every part in gen/netlist.py at gen/place.py's PLACE;
     nets and symbol links from reports/netlist.net (the exported schematic netlist), so DRC's parity check works
  3. 4 layers: F.Cu / B.Cu signals, In1.Cu a solid GND plane, In2.Cu a solid +5V plane (Ken's MEM3-E stack-up)
  4. silkscreen (Ken's rules, 2026-10-24 / 10-31): every reference outside its part's outline with the IC type beside
     it ("IC5 74HCT138"), jumpers, jacks and LEDs labelled by what they do (place.LABELS), the board name and
     cottageworker.com
  5. JLCPCB rules; a courtyard overlap check
Run: <KiCad python> make_board.py BOARD_DIR   ->   BOARD_DIR/<PROJ>.kicad_pcb
"""
import os, sys, re, json, importlib.util
import pcbnew
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import symlib

board_dir = os.path.abspath(sys.argv[1])
def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(board_dir, "gen", name + ".py"))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
N = load("netlist"); P = load("place")
PROJ = N.PROJ
MM = pcbnew.FromMM; V = lambda x, y: pcbnew.VECTOR2I(MM(x), MM(y)); TO = pcbnew.ToMM
FPLIB = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"
NET = os.path.join(board_dir, "reports", "netlist.net")
X0, Y0, W = 10.025, 10.025, 96.19
X1, Y1 = X0 + P.LENGTH, Y0 + W
GUIDE = (76.2, 3.81)                       # card-guide keep-out: 3.00" from the bus edge, 0.15" in from each side

out = os.path.join(board_dir, PROJ + ".kicad_pcb")
b = pcbnew.NewBoard(out)
b.SetCopperLayerCount(4)
for lname in ("In1.Cu", "In2.Cu"):
    b.SetLayerType(b.GetLayerID(lname), pcbnew.LT_POWER)

# ---- 1. outline and keep-outs ------------------------------------------------------------------------------------------
def seg(x1, y1, x2, y2, layer=pcbnew.Edge_Cuts, w=0.1):
    s = pcbnew.PCB_SHAPE(b); s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetStart(V(x1, y1)); s.SetEnd(V(x2, y2))
    s.SetLayer(layer); s.SetWidth(MM(w)); b.Add(s)
for (a, c) in (((X0, Y0), (X1, Y0)), ((X1, Y0), (X1, Y1)), ((X1, Y1), (X0, Y1)), ((X0, Y1), (X0, Y0))):
    seg(a[0], a[1], c[0], c[1])
for yy in ((Y0, Y0 + GUIDE[1]), (Y1 - GUIDE[1], Y1)):
    z = pcbnew.ZONE(b); z.SetIsRuleArea(True); z.SetZoneName("card guide")
    ls = pcbnew.LSET(); [ls.AddLayer(l) for l in (pcbnew.F_Cu, pcbnew.B_Cu, b.GetLayerID("In1.Cu"), b.GetLayerID("In2.Cu"))]
    z.SetLayerSet(ls)
    z.SetDoNotAllowTracks(True); z.SetDoNotAllowVias(True); z.SetDoNotAllowPads(True); z.SetDoNotAllowFootprints(True)
    z.SetDoNotAllowZoneFills(False)
    o = z.Outline(); o.NewOutline()
    for x, y in ((X0, yy[0]), (X0 + GUIDE[0], yy[0]), (X0 + GUIDE[0], yy[1]), (X0, yy[1])):
        o.Append(MM(x), MM(y))
    b.Add(z)

# ---- 2. footprints, nets, links ---------------------------------------------------------------------------------------
PLACE = dict(P.PLACE); PLACE["J1"] = (15.735, 58.12, -90)
missing = [r for r in N.PARTS if r not in PLACE]
if missing: sys.exit("place.py: no position for %s" % ", ".join(missing))
for ref, (value, lib_id, fpid, note) in N.PARTS.items():
    lib, name = fpid.split(":")
    path = symlib.LOCAL_FP if lib == symlib.LOCAL_NAME else os.path.join(FPLIB, lib + ".pretty")
    fp = pcbnew.FootprintLoad(path, name)
    if fp is None: sys.exit("footprint %s not found" % fpid)
    fp.SetFPIDAsString(fpid); fp.SetReference(ref); fp.SetValue(value)
    x, y, rot = PLACE[ref]
    fp.SetOrientationDegrees(rot); fp.SetPosition(V(x, y))
    b.Add(fp)

s = open(NET).read(); padnet = {}
for blk in re.split(r'\(net\s', s)[1:]:
    name = re.search(r'\(name "([^"]*)"', blk).group(1)
    for ref, pad in re.findall(r'\(ref "([^"]+)"\)\s*\(pin "([^"]+)"\)', blk): padnet[(ref, pad)] = name
nets = {}
def netitem(n):
    if n not in nets: ni = pcbnew.NETINFO_ITEM(b, n); b.Add(ni); nets[n] = ni
    return nets[n]
for fp in b.GetFootprints():
    for p in fp.Pads():
        n = padnet.get((fp.GetReference(), p.GetNumber()))
        if n: p.SetNet(netitem(n))
        else: p.SetNetCode(0)
for blk in re.split(r'\n\t\t\(comp\s', s)[1:]:
    ref = re.search(r'\(ref "([^"]+)"\)', blk); sp = re.search(r'\(sheetpath\s+\(names "[^"]*"\)\s+\(tstamps "([^"]+)"\)', blk)
    ts = re.search(r'\n\t\t\t\(tstamps "([^"]+)"', blk)
    fp = b.FindFootprintByReference(ref.group(1)) if ref else None
    if fp and sp and ts: fp.SetPath(pcbnew.KIID_PATH(sp.group(1).rstrip("/") + "/" + ts.group(1)))

# ---- 3. planes ----------------------------------------------------------------------------------------------------------
for lname, net in (("In1.Cu", "GND"), ("In2.Cu", "+5V")):
    z = pcbnew.ZONE(b); z.SetLayer(b.GetLayerID(lname)); z.SetNet(netitem(net)); o = z.Outline(); o.NewOutline(); i = 0.5
    for x, y in ((X0 + i, Y0 + i), (X1 - i, Y0 + i), (X1 - i, Y1 - i), (X0 + i, Y1 - i)):
        o.Append(MM(x), MM(y))
    z.SetLocalClearance(MM(0.25)); z.SetMinThickness(MM(0.2)); z.SetThermalReliefGap(MM(0.3))   # 0.34 mm links
    z.SetThermalReliefSpokeWidth(MM(0.4)); z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL); z.SetZoneName(net + " plane")
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)       # no copper slivers between clearance holes
    b.Add(z)

# ---- 4. silkscreen (common/silk.py) ----------------------------------------------------------------------------------
import silk
silk.add(b, N, P)
def court(fp): return silk.court(fp)

# ---- 5. rules, save, checks ---------------------------------------------------------------------------------------------
ds = b.GetDesignSettings()
ds.m_MinClearance = MM(0.15); ds.m_TrackMinWidth = MM(0.15); ds.m_ViasMinSize = MM(0.5); ds.m_MinThroughDrill = MM(0.3)
ds.m_ViasMinAnnularWidth = MM(0.13); ds.m_HoleClearance = MM(0.25); ds.m_HoleToHoleMin = MM(0.5)
ds.m_CopperEdgeClearance = MM(0.5)
b.SetFileName(out); pcbnew.SaveBoard(out, b)

pf = os.path.join(board_dir, PROJ + ".kicad_pro"); pj = json.load(open(pf))
c = pj["net_settings"]["classes"][0]
c.update(name="Default", clearance=0.2, track_width=0.25, via_diameter=0.6, via_drill=0.3)
pw = dict(c); pw.update(name="Power", clearance=0.2, track_width=0.5, via_diameter=0.8, via_drill=0.4, priority=0)
pj["net_settings"]["classes"] = [c, pw]
pj["net_settings"]["netclass_patterns"] = [{"netclass": "Power", "pattern": n} for n in ("+5V", "GND", "PS2VCC")]
pj["board"]["design_settings"]["rules"].update(min_clearance=0.15, min_track_width=0.15, min_via_diameter=0.5,
    min_via_annular_width=0.13, min_through_hole_diameter=0.3, min_hole_clearance=0.25, min_hole_to_hole=0.5,
    min_copper_edge_clearance=0.5, min_text_height=0.8, min_text_thickness=0.15)
json.dump(pj, open(pf, "w"), indent=2)

fps = list(b.GetFootprints()); bad = []; off = []
for i in range(len(fps)):
    A = court(fps[i])
    if TO(A.GetLeft()) < X0 - 0.01 and fps[i].GetReference() != "J1" or TO(A.GetTop()) < Y0 - 0.01 or \
       TO(A.GetBottom()) > Y1 + 0.01:
        off.append(fps[i].GetReference())
    for k in range(i + 1, len(fps)):
        if A.Intersects(court(fps[k])): bad.append((fps[i].GetReference(), fps[k].GetReference()))
print("board %s: %.2f x %.2f mm, %d footprints" % (PROJ, P.LENGTH, W, len(fps)))
print("courtyard overlaps:", bad or "none")
print("outside the card:", off or "none")
sys.stdout.flush(); os._exit(0)
