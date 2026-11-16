#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-26
"""Build the S5BUS-D board with KiCad's Python (pcbnew), from gen/netlist.py and the schematic's netlist.

  * eight PinSocket_1x36 slots on the 2009 board's 1.0" (25.4 mm) pitch, positions on 2.54 mm
  * every bus line is one straight, locked track on B.Cu from the leftmost part on it to slot 8 (the 2009 board did the
    same); +5V and GND rows 1.5 mm, the rest 0.8 mm. RN1 stands in line with positions 4-12 (+5V, D0-D7), so its pins
    sit on those tracks with no routing at all
  * the power area at the left end (Ken's board-layout rules for new boards): the screw terminal J9 at the left edge with
    its wire entry facing out, the power LED D1 at the same edge, C1 bulk, RN2 (the open-collector pull-ups), R1
  * a 0.1 uF capacitor (0.1" leads) above each slot, eight M3 holes: four along each long edge, between slots, each
    with a 4 mm-radius copper keep-out (a metal screw head or washer touches only bare board, never a track)
  * the power switch SW1 (an E-Switch 100-series right-angle SPDT toggle, 5 A at 28 VDC; Ken, 2026-10-27) at the left
    edge between J9 and the power LED: its support bracket 2.5 mm in from the edge, bushing and lever over it; labelled
    POWER with ON / OFF at its ends
  * the supply path J9 -> SW1 -> F1 (4 A polyfuse) -> Q1 (P-MOSFET, reverse-polarity protection) -> +5V on locked B.Cu
    tracks, 2.0 mm up to Q1's drain (the last stretch on F.Cu) and a 2.5 mm riser from Q1's source into the +5V row;
    Q1 lies flat, tab down, with no top copper under it and none round its screw hole; GND on F.Cu from J9 down past
    SW1 and R1 to the GND row (2.5 mm, inside the GND pour); J9's GND pin is also connected solidly (no thermal spokes)
    to the pour
  * silkscreen text at least 1.0 mm tall with a 0.18 mm stroke (JLCPCB's minimum is 1.0 mm / 0.153 mm)
  * each slot's 30-pin window (positions 4-33) is bracketed on the silkscreen, with a triangle at the +5V end, so a
    card cannot be plugged in shifted or turned round by mistake; an arrow under each slot shows the cards' component
    side, towards the power connector (Ken, 2026-10-27)
  * GND pour on F.Cu; the rest (J9, C1, RN2, R1, D1 and the bypass capacitors) is routed by Freerouting afterwards:
    tools/kicad/kicad_route.py export_dsn / import_ses (the locked bus tracks are fixed for it)
Writes ../s5bus-d.kicad_pcb."""
import os, sys, re, json, math
import pcbnew
HERE = os.path.dirname(os.path.abspath(__file__)); DEST = os.path.dirname(HERE); sys.path.insert(0, HERE)
import netlist as N
MM = pcbnew.FromMM; V = lambda x, y: pcbnew.VECTOR2I(MM(x), MM(y))
FPLIB = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"
NET = os.path.join(DEST, "reports", "netlist.net"); PROJ = "s5bus-d"

# geometry (mm), origin at the board's top-left corner
X0, PITCH, Y0, STEP = 46.0, 25.4, 15.0, 2.54        # slot 1's column; slot pitch; position 1's row; position pitch
W, H = 238.0, 114.0                                  # 114: the bottom holes' keep-outs clear the SC0 row (position 36)
SLOTX = [X0 + PITCH * k for k in range(N.NSLOTS)]
ROW = lambda p: Y0 + STEP * (p - 1)                  # slot position p (1..36) -> y
QX, QY = 35.08, 59.0                                 # Q1's gate pin
RN1X = 38.0                                          # RN1 in line with positions 4..12
HOLES = [(5.0, 4.5), (X0 + 1.5 * PITCH, 4.5), (X0 + 4.5 * PITCH, 4.5), (W - 5.0, 4.5),
         (5.0, H - 4.5), (X0 + 1.5 * PITCH, H - 4.5), (X0 + 4.5 * PITCH, H - 4.5), (W - 5.0, H - 4.5)]

b = pcbnew.BOARD()
b.SetCopperLayerCount(2)
for (x1, y1, x2, y2) in ((0, 0, W, 0), (W, 0, W, H), (W, H, 0, H), (0, H, 0, 0)):
    s = pcbnew.PCB_SHAPE(b); s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetLayer(pcbnew.Edge_Cuts)
    s.SetStart(V(x1, y1)); s.SetEnd(V(x2, y2)); s.SetWidth(MM(0.1)); b.Add(s)

# parts: (x, y, rotation) of the footprint origin
PLACE = {"J%d" % (k + 1): (SLOTX[k], ROW(1), 0) for k in range(N.NSLOTS)}
PLACE.update({"C%d" % (k + 2): (SLOTX[k] + 3.0, 8.5, 0) for k in range(N.NSLOTS)})
PLACE.update({"H%d" % (k + 1): (x, y, 0) for k, (x, y) in enumerate(HOLES)})
PLACE.update({
    "RN1": (RN1X, ROW(4), -90),          # pin 1 (common, +5V) on position 4, pins 2-9 on positions 5-12 (D0-D7)
    "J9": (7.0, 30.0, 270),              # screw terminal: its wire entry (the footprint's +y face) to the left edge
    "SW1": (15.2, 50.0, 0),              # toggle between J9 and D1: origin on pin 2; support legs 12.7 left, 2.5 from the edge
    "F1": (22.0, 54.7, 0),               # polyfuse: pad 1 (+5V_SW) on SW1 pin 3's row, pad 2 (+5V_FUSED) at +5.1, +1.2
    "Q1": (QX, QY, 180),                 # TO-220 P-MOSFET lying flat, tab down (Ken, 2026-10-28: an upright one stood ~19 mm
                                         # tall beside slot 1): pins in a row, G here, D 2.54 left, S 5.08 left; body below
    "R2": (36.6, 56.0, 90),              # gate to GND, above Q1's gate
    "C1": (24.0, 30.0, 0),
    "RN2": (40.0, 70.0, -90),            # below the "J1 SLOT 1" label
    "RN3": (3.8, 64.0, 0),               # idle-state networks in the free space below SW1, left of the GND feed at x = 19
    "RN4": (3.8, 71.0, 0),               # (no bus track crosses here); Freerouting joins them to the bus rows
    "R1": (8.0, 82.0, 0),
    "D1": (4.5, 92.0, 90),
})
for ref, (lib_id, value, fpid, pinmap) in N.PARTS.items():
    lib, name = fpid.split(":")
    fp = pcbnew.FootprintLoad(os.path.join(DEST if lib == "s5bus" else FPLIB, lib + ".pretty"), name)
    fp.SetFPIDAsString(fpid); fp.SetReference(ref); fp.SetValue(value)
    if ref in N.DOCS:
        fp.GetField(pcbnew.FIELD_T_DATASHEET).SetText(N.DOCS[ref][0]); fp.GetField(pcbnew.FIELD_T_DESCRIPTION).SetText(N.DOCS[ref][1])
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
        if n: p.SetNet(netitem(n))
        else: p.SetNetCode(0)
for block in re.split(r'\n\t\t\(comp\s', s)[1:]:
    ref = re.search(r'\(ref "([^"]+)"\)', block); sp = re.search(r'\(sheetpath\s+\(names "[^"]*"\)\s+\(tstamps "([^"]+)"\)', block)
    ts = re.search(r'\n\t\t\t\(tstamps "([^"]+)"', block)
    fp = b.FindFootprintByReference(ref.group(1)) if ref else None
    if fp and sp and ts: fp.SetPath(pcbnew.KIID_PATH(sp.group(1).rstrip("/") + "/" + ts.group(1)))

# the bus: one locked B.Cu track per slot position, from the leftmost pad on it to slot 8
def netname(pos):
    n = N.POS[pos - 1]
    return n if n in ("+5V", "GND") else "/" + n
for pos in range(1, 37):
    y = ROW(pos); x1 = RN1X if 4 <= pos <= 12 else X0
    t = pcbnew.PCB_TRACK(b); t.SetStart(V(x1, y)); t.SetEnd(V(SLOTX[-1], y)); t.SetLayer(pcbnew.B_Cu)
    t.SetWidth(MM(1.5 if N.POS[pos - 1] in ("+5V", "GND") else 0.8)); t.SetNet(netitem(netname(pos))); t.SetLocked(True)
    b.Add(t)

# the supply feeds from J9 (pin 1 +5V at (7, 30), pin 2 GND at (7, 35.08)): locked 2.5 mm B.Cu tracks
def feed(net, pts, w=2.5, layer=pcbnew.B_Cu):
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(b); t.SetStart(V(x1, y1)); t.SetEnd(V(x2, y2)); t.SetLayer(layer)
        t.SetWidth(MM(w)); t.SetNet(netitem(net)); t.SetLocked(True); b.Add(t)
SWX, SWY = 15.2, 50.0                                                               # SW1's pin column; pin 2 (common)
feed("/+5V_IN", [(7.0, 30.0), (19.0, 30.0), (19.0, SWY), (SWX, SWY)], 2.0)           # J9 pin 1 to SW1 common, from the right
feed("/+5V_SW", [(SWX, SWY + 4.7), (22.0, SWY + 4.7)], 2.0)                          # SW1 pin 3 (ON) to F1 pad 1
feed("/+5V_FUSED", [(27.1, 55.9), (QX - 2.54, 55.9), (QX - 2.54, QY)], 2.0, pcbnew.F_Cu)  # F1 pad 2 to Q1's drain, top side
feed("+5V", [(QX - 5.08, QY), (QX - 5.08, ROW(4)), (RN1X, ROW(4))])                  # Q1's source up the riser, into the +5V row
feed("GND", [(7.0, 35.08), (12.0, 40.08), (19.0, 40.08), (19.0, ROW(33) - 4.8), (23.8, ROW(33)), (X0, ROW(33))],
     2.5, pcbnew.F_Cu)                                                               # J9 pin 2 down past SW1 and R1, top side
for ref, pad in (("J9", "2"),):
    for p in b.FindFootprintByReference(ref).Pads():
        if p.GetNumber() == pad: p.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)

# a copper keep-out around each mounting hole, both layers
for (hx, hy) in HOLES:
    k = pcbnew.ZONE(b); k.SetIsRuleArea(True); k.SetLayerSet(pcbnew.LSET.AllCuMask())
    k.SetDoNotAllowTracks(True); k.SetDoNotAllowVias(True); k.SetDoNotAllowZoneFills(True)
    k.SetDoNotAllowPads(False); k.SetDoNotAllowFootprints(False)
    o = k.Outline(); o.NewOutline()
    for a in range(32):
        o.Append(MM(hx + 4.0 * math.cos(a * math.pi / 16)), MM(hy + 4.0 * math.sin(a * math.pi / 16)))
    b.Add(k)

# under Q1's body (its tab, the drain, lies on the top side): no top copper; around its screw hole: none either side
def keepout(pts, layers):
    k = pcbnew.ZONE(b); k.SetIsRuleArea(True); k.SetLayerSet(layers)
    k.SetDoNotAllowTracks(True); k.SetDoNotAllowVias(True); k.SetDoNotAllowZoneFills(True)
    k.SetDoNotAllowPads(False); k.SetDoNotAllowFootprints(False)
    o = k.Outline(); o.NewOutline()
    for x, y in pts: o.Append(MM(x), MM(y))
    b.Add(k)
fl = pcbnew.LSET(); fl.AddLayer(pcbnew.F_Cu)
keepout([(QX - 7.9, QY + 3.5), (QX + 2.8, QY + 3.5), (QX + 2.8, QY + 19.8), (QX - 7.9, QY + 19.8)], fl)
keepout([(QX - 2.54 + 4.0 * math.cos(a * math.pi / 16), QY + 16.66 + 4.0 * math.sin(a * math.pi / 16)) for a in range(32)],
        pcbnew.LSET.AllCuMask())

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
def card_side(x):
    # the cards' components face the power connector (Ken, 2026-10-27): an arrow under the slot, pointing left
    ay = ROW(36) + 4.7
    s = pcbnew.PCB_SHAPE(b); s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetLayer(pcbnew.F_SilkS)
    s.SetStart(V(x + 1.0, ay)); s.SetEnd(V(x - 6.0, ay)); s.SetWidth(MM(0.3)); b.Add(s)
    s = pcbnew.PCB_SHAPE(b); s.SetShape(pcbnew.SHAPE_T_POLY); s.SetLayer(pcbnew.F_SilkS); s.SetFilled(True); s.SetWidth(MM(0.1))
    s.SetPolyPoints([V(x - 7.6, ay), V(x - 5.9, ay - 0.9), V(x - 5.9, ay + 0.9)]); b.Add(s)
    silk("COMPONENT SIDE", x - 3.3, ay - 1.8, 1.0)
for k, x in enumerate(SLOTX):
    for pos in range(1, 37):
        silk(N.POS[pos - 1], x + 1.4, ROW(pos), 1.0, just="left")
    silk("J%d  SLOT %d" % (k + 1, k + 1), x - 3.6, (ROW(1) + ROW(36)) / 2, 1.2, 90)
    # the 30-pin card's window, positions 4-33: a bracket left of the socket, a filled triangle at the +5V end
    bx, top, bot = x - 2.3, ROW(4) - 1.27, ROW(33) + 1.27
    for (x1, y1, x2, y2) in ((bx, top, bx, bot), (bx, top, x - 1.8, top), (bx, bot, x - 1.8, bot)):
        s = pcbnew.PCB_SHAPE(b); s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetLayer(pcbnew.F_SilkS)
        s.SetStart(V(x1, y1)); s.SetEnd(V(x2, y2)); s.SetWidth(MM(0.3)); b.Add(s)
    s = pcbnew.PCB_SHAPE(b); s.SetShape(pcbnew.SHAPE_T_POLY); s.SetLayer(pcbnew.F_SilkS); s.SetFilled(True); s.SetWidth(MM(0.1))
    s.SetPolyPoints([V(bx - 0.5, top - 2.4), V(bx - 1.5, top - 0.7), V(bx + 0.5, top - 0.7)]); b.Add(s)
    card_side(x)
    silk("C%d" % (k + 2), x - 0.3, 8.5, 1.0, just="right")
silk("RN1 10k  D0-D7 PULL-UPS", RN1X - 2.3, (ROW(4) + ROW(12)) / 2, 1.0, 90)
r = b.FindFootprintByReference("RN2"); bb = r.GetBoundingBox(False, False)
silk("RN2 10k  OPEN-COLL PULL-UPS", pcbnew.ToMM(bb.GetRight()) + 1.1, pcbnew.ToMM(bb.GetCenter().y) + 2.0, 1.0, 90)   # right of RN2: Q1 lies to its left
for ref, l1, l2 in (("RN3", "RN3 10k PULL-DOWN", "N0-N2 TPA TPB"), ("RN4", "RN4 10k PULL-UP", "-VMA -MRD -MRW")):
    r = b.FindFootprintByReference(ref); bb = r.GetBoundingBox(False, False)      # below the part, never under it
    x, y = pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetBottom())
    silk(l1, x, y + 1.2, 1.0, just="left"); silk(l2, x, y + 2.6, 1.0, just="left")
j9 = b.FindFootprintByReference("J9"); jb = j9.GetBoundingBox(False, False)
for p in j9.Pads():
    silk("+5V" if p.GetNumber() == "1" else "GND", pcbnew.ToMM(jb.GetRight()) + 1.0, pcbnew.ToMM(p.GetPosition().y), 1.2, just="left")
silk("J9 POWER IN", pcbnew.ToMM(jb.GetCenter().x), pcbnew.ToMM(jb.GetTop()) - 1.2, 1.2)
f1 = b.FindFootprintByReference("F1"); fb = f1.GetBoundingBox(False, False)
silk("F1 4A FUSE", 23.5, pcbnew.ToMM(fb.GetTop()) - 1.0, 1.0)
# SW1: a toggle closes the contact on the side away from its lever, so lever up (towards pin 1 and J9) joins common to
# pin 3 = ON; lever down = OFF (pin 1, unconnected)
silk("ON", 4.0, SWY - 7.5, 1.0)
silk("SW1 POWER", 8.5, SWY - 7.5, 1.0, just="left")
silk("OFF", 4.0, SWY + 7.6, 1.0)
silk("Q1 IPP80P03P4L-04", QX - 9.0, QY + 11.6, 1.0, 90)
silk("R2 10k", 38.9, 52.0, 1.0, 90)
c1 = b.FindFootprintByReference("C1"); cb = c1.GetBoundingBox(False, False)
silk("C1 220uF 16V", pcbnew.ToMM(cb.GetCenter().x), pcbnew.ToMM(cb.GetBottom()) + 1.2, 1.0)
r1 = b.FindFootprintByReference("R1"); rb = r1.GetBoundingBox(False, False)
silk("R1 470", pcbnew.ToMM(rb.GetCenter().x), pcbnew.ToMM(rb.GetTop()) - 0.9, 1.0)
d1 = b.FindFootprintByReference("D1"); db = d1.GetBoundingBox(False, False)
silk("D1 PWR", pcbnew.ToMM(db.GetRight()) + 1.0, pcbnew.ToMM(db.GetCenter().y), 1.2, just="left")
silk("S5BUS-D", 18.0, H - 14.0, 2.0)
silk("System-5 bus  Rev D  2026", 18.0, H - 11.0, 1.5)
silk("cottageworker.com", 18.0, H - 8.6, 1.5)

# GND pour, top side (the bottom carries the bus)
z = pcbnew.ZONE(b); z.SetLayer(pcbnew.F_Cu); z.SetNet(netitem("GND")); o = z.Outline(); o.NewOutline(); i = 0.5
for x, y in ((i, i), (W - i, i), (W - i, H - i), (i, H - i)): o.Append(MM(x), MM(y))
z.SetLocalClearance(MM(0.3)); z.SetMinThickness(MM(0.25)); z.SetThermalReliefGap(MM(0.3)); z.SetThermalReliefSpokeWidth(MM(0.4))
z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL); b.Add(z)

ds = b.GetDesignSettings()
ds.m_MinClearance = MM(0.15); ds.m_TrackMinWidth = MM(0.15); ds.m_ViasMinSize = MM(0.5); ds.m_MinThroughDrill = MM(0.3)
ds.m_ViasMinAnnularWidth = MM(0.13); ds.m_HoleClearance = MM(0.25); ds.m_HoleToHoleMin = MM(0.5); ds.m_CopperEdgeClearance = MM(0.5)
out = os.path.join(DEST, PROJ + ".kicad_pcb"); b.SetFileName(out); pcbnew.SaveBoard(out, b)

fps = list(b.GetFootprints()); bad = []
for i in range(len(fps)):
    for k in range(i + 1, len(fps)):
        A = fps[i].GetBoundingBox(False, False); B = fps[k].GetBoundingBox(False, False)
        if A.Intersects(B): bad.append((fps[i].GetReference(), fps[k].GetReference()))
print("overlaps:", bad or "none")
pf = os.path.join(DEST, PROJ + ".kicad_pro"); p = json.load(open(pf))
c = p["net_settings"]["classes"][0]; c.update(name="Default", clearance=0.2, track_width=0.4, via_diameter=0.8, via_drill=0.4)
pw = dict(c); pw.update(name="Power", clearance=0.25, track_width=1.0, via_diameter=1.0, via_drill=0.5, priority=0)
p["net_settings"]["classes"] = [c, pw]
p["net_settings"]["netclass_patterns"] = [{"netclass": "Power", "pattern": "+5V"}, {"netclass": "Power", "pattern": "/+5V_IN"}, {"netclass": "Power", "pattern": "/+5V_SW"}, {"netclass": "Power", "pattern": "/+5V_FUSED"}, {"netclass": "Power", "pattern": "GND"}]
p["board"]["design_settings"]["rules"].update(min_clearance=0.15, min_track_width=0.15, min_via_diameter=0.5, min_via_annular_width=0.13,
    min_through_hole_diameter=0.3, min_hole_clearance=0.25, min_hole_to_hole=0.5, min_copper_edge_clearance=0.5, min_text_height=0.8, min_text_thickness=0.12)
json.dump(p, open(pf, "w"), indent=2)
print("wrote", out, len(fps), "footprints"); sys.stdout.flush(); os._exit(0)
