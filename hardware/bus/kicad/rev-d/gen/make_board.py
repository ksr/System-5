#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-26
"""Build the S5BUS-D board with KiCad's Python (pcbnew), from gen/netlist.py and the schematic's netlist.

  * eight PinSocket_1x36 slots on the 2009 board's 1.0" (25.4 mm) pitch, but 1.25" (31.75 mm) between slots 7 and 8, the
    two farthest from the power connector (Ken, 2026-11-18: "only that one space"), so slot 8's card has 6.35 mm more
    room for its components; positions on 2.54 mm
  * every bus line is one straight, locked track on B.Cu from the leftmost part on it to slot 8 (the 2009 board did the
    same); +5V and GND rows 1.5 mm, the rest 0.8 mm. RN1 stands in line with the +5V and D0-D7 rows (positions 30-22), so
    its pins sit on those tracks with no routing at all. The slot order (gen/netlist.py, Ken 2026-11-18), counted from
    GND, position 1, at the bottom end as drawn: the 30-pin bus up to +5V at 30, then -EF1 31, -EF2, -EF3, -DMAIN, SC0 and
    -PAUSE, 36, at the top. Each socket is turned so that its pin 1 (KiCad's square pad) is that GND end
  * the power area at the left end (Ken's board-layout rules for new boards): the barrel jack J9 at the left edge with
    its opening facing out, the power LED D1 at the same edge, C1 bulk, RN2 (the open-collector pull-ups), R1
  * a 0.1 uF capacitor (0.1" leads) above each slot, eight M3 holes: four along each long edge, between slots, each
    with a 4 mm-radius copper keep-out (a metal screw head or washer touches only bare board, never a track)
  * the power switch SW1 at the left end between J10 and C1: an M9040P, the upright Marquardt SPDT toggle of the IO
    panel's data switches (Ken, 2026-11-18: "bus change on off switch to same toggle used on IO card data 1-8"; that
    day first a right-angle 9070-1W, and from 2026-10-27 an E-Switch 100 series), standing on the board, its lever
    moving along the left edge; labelled POWER with ON / OFF at its ends
  * the supply path (Ken, 2026-11-18) J9 -> D2 (Schottky) -> U1 (TSR 3-2450N regulator) -> JP1 pin 1 (REG); J10, two
    screw terminals for an external regulated 5 V, at the left edge with their wire entry facing out -> JP1 pin 3 (EXT);
    JP1, one shunt, picks the source onto its pin 2 -> SW1 (switching either source) -> +5V. Down the left end in that
    order, so no supply track crosses another: locked B.Cu tracks, 2.0 mm, and a 2.0 mm riser from SW1 into the +5V row
    with C1 at its foot. The parts that stand tall (J9, C10, U1, J10, SW1, C1: about 11 mm) are all left of x = 23.7 mm
    (JP1, 8.5 mm with its shunt, to 24.2), clear of the card in slot 1, whose components face this way (up to 21.3 mm
    from it). No track or via under U1's body (TRACO: avoid routing traces under the converter). GND on F.Cu from J9
    past C10 into U1's GND, and from J10 under SW1 to C1 and down to the GND row (2.5 mm, inside the GND pour), each of
    those GND pins joined solidly (no thermal spokes) to the pour
  * silkscreen text at least 1.0 mm tall with a 0.18 mm stroke (JLCPCB's minimum is 1.0 mm / 0.153 mm)
  * each slot's 30-pin window (positions 1-30, flush with the GND end) is bracketed on the silkscreen, with a triangle
    at the +5V end, so a card cannot be plugged in shifted or turned round by mistake; an arrow under each slot shows the cards' component
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
GAP78 = 1.25 * 25.4                                  # slots 7 and 8 (Ken, 2026-11-18); every other pair PITCH apart
W, H = 238.0 + GAP78 - PITCH, 116.0                  # 116 (Ken, 2026-11-18, 2 mm more at the GND end): a 30-pin card, plugged in
                                                     # flush with the GND end, reaches 11.3 mm past the GND row; the board 12.1
SLOTX = [X0 + PITCH * k for k in range(N.NSLOTS - 1)]
SLOTX.append(SLOTX[-1] + GAP78)
ROW = lambda p: Y0 + STEP * (36 - p)                 # slot position p (1..36, counted from GND at the bottom) -> y
PN = lambda name: N.POS.index(name) + 1              # a bus line's position
P5V, PGND = PN("+5V"), PN("GND")                     # the 30-pin window: GND at 1, +5V at 30
RN1ROWS = [PN(n) for n in ("+5V", "D0", "D1", "D2", "D3", "D4", "D5", "D6", "D7")]
RN1X = 38.0                                          # RN1 in line with the +5V and D0-D7 rows
HOLES = [(5.0, 4.5), (X0 + 1.5 * PITCH, 4.5), (X0 + 4.5 * PITCH, 4.5), (W - 5.0, 4.5),
         (5.0, H - 4.5), (X0 + 1.5 * PITCH, H - 4.5), (X0 + 4.5 * PITCH, H - 4.5), (W - 5.0, H - 4.5)]

b = pcbnew.BOARD()
b.SetCopperLayerCount(2)
for (x1, y1, x2, y2) in ((0, 0, W, 0), (W, 0, W, H), (W, H, 0, H), (0, H, 0, 0)):
    s = pcbnew.PCB_SHAPE(b); s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetLayer(pcbnew.Edge_Cuts)
    s.SetStart(V(x1, y1)); s.SetEnd(V(x2, y2)); s.SetWidth(MM(0.1)); b.Add(s)

# parts: (x, y, rotation) of the footprint origin
PLACE = {"J%d" % (k + 1): (SLOTX[k], ROW(1), 180) for k in range(N.NSLOTS)}   # pin 1 (GND) at the bottom, the pins up from it
PLACE.update({"C%d" % (k + 2): (SLOTX[k] + 3.0, 8.5, 0) for k in range(N.NSLOTS)})
PLACE.update({"H%d" % (k + 1): (x, y, 0) for k, (x, y) in enumerate(HOLES)})
PLACE.update({
    "RN1": (RN1X, ROW(P5V), -90),        # pin 1 (common, +5V) on the +5V row (30), pins 2-9 on the D0-D7 rows (29-22)
    "J9": (12.5, 18.0, 270),             # barrel jack, its opening (the footprint's +y face) flush with the left edge: pad 1
                                         # (the centre pin, +) here, pad 2 (the sleeve, GND) 6 mm nearer the edge
    "D2": (19.5, 33.24, 90),             # Schottky lying along y: cathode (pad 1) here, anode (pad 2) 15.24 above, by J9
    "C10": (12.0, 32.5, 180),            # + here, - 2.5 left
    "U1": (11.0, 40.5, 90),              # TSR 3-2450N upright: Vin here, GND and Vout 2.54 and 5.08 right, body below them
    "J10": (7.0, 51.0, 270),             # screw terminals, their wire entry (the footprint's +y face) to the left edge: pin 1
                                         # (EXT 5V) here, pin 2 (GND) 5.08 below
    "JP1": (22.4, 51.0, 270),            # the source jumper across under U1: pin 1 (REG) here, pin 2 (to SW1) and pin 3 (EXT)
                                         # 2.54 and 5.08 left, towards J10
    "SW1": (15.2, 68.0, 0),              # the upright toggle below J10: origin on pin 2 (the common), pins 1 and 3 4.7 mm
                                         # above and below it; its body 8.6 x 13.4 mm, 10.9 mm in from the edge
    "C1": (20.0, 79.0, 270),             # + here, - 2.5 below
    "RN2": (31.0, 70.0, -90),            # left of slot 1, about 12 mm clear of its socket (Ken, 2026-11-18: "rn2 is too close
                                         # to the connector"; it stood at x 40, 2.6 mm from it)
    "RN3": (27.5, 14.0, 0),              # the idle-state networks (low parts) in the corner above RN1 and the +5V
    "RN4": (27.5, 21.5, 0),              # feed (below RN1 since the 2026-11-18 order); Freerouting joins them to the rows
    "R1": (6.0, 86.5, 0),
    "D1": (4.5, 94.0, 90),
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
    y = ROW(pos); x1 = RN1X if pos in RN1ROWS else X0
    t = pcbnew.PCB_TRACK(b); t.SetStart(V(x1, y)); t.SetEnd(V(SLOTX[-1], y)); t.SetLayer(pcbnew.B_Cu)
    t.SetWidth(MM(1.5 if N.POS[pos - 1] in ("+5V", "GND") else 0.8)); t.SetNet(netitem(netname(pos))); t.SetLocked(True)
    b.Add(t)

# the supply path, on locked tracks (Freerouting routes the rest round them)
def feed(net, pts, w=2.5, layer=pcbnew.B_Cu):
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(b); t.SetStart(V(x1, y1)); t.SetEnd(V(x2, y2)); t.SetLayer(layer)
        t.SetWidth(MM(w)); t.SetNet(netitem(net)); t.SetLocked(True); b.Add(t)
SWX, SWY, SWP = 15.2, 68.0, 4.699                                                   # SW1's pin column; pin 2 (common); pin pitch
UX, UY = 11.0, 40.5                                                                 # U1's Vin; GND and Vout 2.54, 5.08 right
JX, JY = 22.4, 51.0                                                                 # JP1 pin 1 (REG); 2 and 3 2.54, 5.08 left
RX = 25.0                                                                           # the +5V riser
feed("/VIN", [(12.5, 18.0), (19.5, 18.0)], 2.0)                                      # J9's centre pin to D2's anode
feed("/VIN_D", [(19.5, 33.24), (19.5, 36.5), (12.0, 36.5)], 2.0)                     # D2's cathode across to C10 +
feed("/VIN_D", [(12.0, 32.5), (12.0, 38.0), (UX, 39.0), (UX, UY)], 2.0)             # C10 + down into U1's Vin
feed("/5V_REG", [(UX + 5.08, UY), (JX, UY), (JX, JY)], 2.0)                          # U1's Vout, out above its body, round it to JP1 pin 1
feed("/5V_EXT", [(7.0, JY), (JX - 5.08, JY)], 2.0)                                   # J10 pin 1 straight across to JP1 pin 3
feed("/5V_SEL", [(JX - 2.54, JY), (JX - 2.54, SWY - 1.5), (JX - 4.04, SWY), (SWX, SWY)], 2.0)   # JP1 pin 2 down to SW1's common
feed("+5V", [(SWX, SWY + SWP), (RX, SWY + SWP), (RX, ROW(P5V)), (RN1X, ROW(P5V))], 2.0)   # SW1 pin 3 (ON): the riser into the +5V row
feed("+5V", [(RX, SWY + SWP), (RX, 79.0), (20.0, 79.0)], 2.0)                        # C1 + at the riser's foot
feed("GND", [(6.5, 18.0), (6.5, 28.0), (9.0, 30.5), (9.0, 36.5), (UX + 2.54, 36.5), (UX + 2.54, UY)], 2.5,
     pcbnew.F_Cu)                                                                    # J9's sleeve past C10 - into U1's GND, top side
feed("GND", [(7.0, JY + 5.08), (9.0, JY + 7.08), (9.0, 78.0), (12.5, 81.5), (20.0, 81.5)], 2.5,
     pcbnew.F_Cu)                                                                    # J10 pin 2 under SW1 to C1 -, top side
feed("GND", [(20.0, 81.5), (23.0, 84.5), (23.0, ROW(PGND) - 4.8), (27.8, ROW(PGND)), (X0, ROW(PGND))],
     2.5, pcbnew.F_Cu)                                                               # C1 - down to the slots' GND row, top side
for ref, pads in (("J9", ("2", "MP")), ("U1", ("2",)), ("C1", ("2",)), ("C10", ("2",)), ("J10", ("2",))):
    for p in b.FindFootprintByReference(ref).Pads():
        if p.GetNumber() in pads: p.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)

# a copper keep-out around each mounting hole, both layers
for (hx, hy) in HOLES:
    k = pcbnew.ZONE(b); k.SetIsRuleArea(True); k.SetLayerSet(pcbnew.LSET.AllCuMask())
    k.SetDoNotAllowTracks(True); k.SetDoNotAllowVias(True); k.SetDoNotAllowZoneFills(True)
    k.SetDoNotAllowPads(False); k.SetDoNotAllowFootprints(False)
    o = k.Outline(); o.NewOutline()
    for a in range(32):
        o.Append(MM(hx + 4.0 * math.cos(a * math.pi / 16)), MM(hy + 4.0 * math.sin(a * math.pi / 16)))
    b.Add(k)

# under U1's body, below its pins: no track or via on either side (TRACO: avoid routing traces under the converter);
# the GND pour may fill it
def keepout(pts, layers, fill=False):
    k = pcbnew.ZONE(b); k.SetIsRuleArea(True); k.SetLayerSet(layers)
    k.SetDoNotAllowTracks(True); k.SetDoNotAllowVias(True); k.SetDoNotAllowZoneFills(not fill)
    k.SetDoNotAllowPads(False); k.SetDoNotAllowFootprints(False)
    o = k.Outline(); o.NewOutline()
    for x, y in pts: o.Append(MM(x), MM(y))
    b.Add(k)
keepout([(UX - 4.46, UY + 1.3), (UX + 9.54, UY + 1.3), (UX + 9.54, UY + 6.16), (UX - 4.46, UY + 6.16)], pcbnew.LSET.AllCuMask(),
        fill=True)

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
    ay = ROW(PGND) + 4.7
    s = pcbnew.PCB_SHAPE(b); s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetLayer(pcbnew.F_SilkS)
    s.SetStart(V(x + 1.0, ay)); s.SetEnd(V(x - 6.0, ay)); s.SetWidth(MM(0.3)); b.Add(s)
    s = pcbnew.PCB_SHAPE(b); s.SetShape(pcbnew.SHAPE_T_POLY); s.SetLayer(pcbnew.F_SilkS); s.SetFilled(True); s.SetWidth(MM(0.1))
    s.SetPolyPoints([V(x - 7.6, ay), V(x - 5.9, ay - 0.9), V(x - 5.9, ay + 0.9)]); b.Add(s)
    silk("COMPONENT SIDE", x - 3.3, ay - 1.8, 1.0)
for k, x in enumerate(SLOTX):
    for pos in range(1, 37):
        silk(N.POS[pos - 1], x + 1.4, ROW(pos), 1.0, just="left")
    silk("J%d  SLOT %d" % (k + 1, k + 1), x - 3.6, (ROW(1) + ROW(36)) / 2, 1.2, 90)
    # the 30-pin card's window, positions 1-30 (flush with the GND end): a bracket left of the socket, a filled
    # triangle at the +5V end
    bx, top, bot = x - 2.3, ROW(P5V) - 1.27, ROW(PGND) + 1.27
    for (x1, y1, x2, y2) in ((bx, top, bx, bot), (bx, top, x - 1.8, top), (bx, bot, x - 1.8, bot)):
        s = pcbnew.PCB_SHAPE(b); s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetLayer(pcbnew.F_SilkS)
        s.SetStart(V(x1, y1)); s.SetEnd(V(x2, y2)); s.SetWidth(MM(0.3)); b.Add(s)
    s = pcbnew.PCB_SHAPE(b); s.SetShape(pcbnew.SHAPE_T_POLY); s.SetLayer(pcbnew.F_SilkS); s.SetFilled(True); s.SetWidth(MM(0.1))
    s.SetPolyPoints([V(bx - 0.5, top - 2.4), V(bx - 1.5, top - 0.7), V(bx + 0.5, top - 0.7)]); b.Add(s)
    card_side(x)
    silk("C%d 0.1uF" % (k + 2), x - 0.3, 8.5, 1.0, just="right")
silk("RN1 10k  D0-D7 PULL-UPS", RN1X - 2.3, (ROW(P5V) + ROW(PN("D7"))) / 2, 1.0, 90)
r = b.FindFootprintByReference("RN2"); bb = r.GetBoundingBox(False, False)
silk("RN2 10k  OPEN-COLL PULL-UPS", pcbnew.ToMM(bb.GetRight()) + 1.1, pcbnew.ToMM(bb.GetCenter().y) + 2.0, 1.0, 90)   # right of RN2
for ref, l1, l2 in (("RN3", "RN3 10k PULL-DOWN", "N0-N2 TPA TPB"), ("RN4", "RN4 10k PULL-UP", "-VMA -MRD -MRW")):
    r = b.FindFootprintByReference(ref); bb = r.GetBoundingBox(False, False)      # below the part, never under it
    x, y = pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetBottom())
    silk(l1, x, y + 1.2, 1.0, just="left"); silk(l2, x, y + 2.6, 1.0, just="left")
j9 = b.FindFootprintByReference("J9"); jb = j9.GetBoundingBox(False, False)
silk("J9 POWER IN", pcbnew.ToMM(jb.GetCenter().x), pcbnew.ToMM(jb.GetTop()) - 1.2, 1.2)
silk("7-15V DC", pcbnew.ToMM(jb.GetCenter().x), pcbnew.ToMM(jb.GetBottom()) + 1.7, 1.0)      # the adapter it takes
silk("CENTER +", pcbnew.ToMM(jb.GetCenter().x), pcbnew.ToMM(jb.GetBottom()) + 3.2, 1.0)
silk("D2 SB540", 15.6, 25.6, 1.0, 90)                                                       # between J9 / C10 and D2
c10 = b.FindFootprintByReference("C10"); cb = c10.GetBoundingBox(False, False)
silk("C10 47uF 35V", pcbnew.ToMM(cb.GetCenter().x), pcbnew.ToMM(cb.GetBottom()) + 1.2, 1.0)
silk("U1 TSR 3-2450N", UX - 6.8, UY + 0.5, 1.0, 90)                                          # left of U1
# J10: what each terminal takes, beside it (the wires go in from the edge, the screws on top); JP1: REG and EXT at its
# ends, the shunt on pins 1-2 (REG) or 2-3 (EXT), its name below
silk("J10", 12.6, JY - 2.4, 1.0, just="left")
silk("+5V", 12.6, JY, 1.0, just="left"); silk("GND", 12.6, JY + 5.08, 1.0, just="left")
silk("REG", JX, JY + 3.0, 1.0); silk("EXT", JX - 5.08, JY + 3.0, 1.0)
silk("JP1 5V SOURCE", 19.0, JY + 7.0, 1.0)
# SW1: a toggle closes the contact on the side away from its lever, so lever up (towards pin 1 and J9) joins common to
# pin 3 = ON; lever down = OFF (pin 1, unconnected). To check against a real switch before an order. Its name and its
# two positions left of it, each position level with the end the lever is at
silk("ON", SWX - 5.0, SWY - SWP, 1.0, just="right")
silk("SW1 POWER", SWX - 5.0, SWY, 1.0, just="right")
silk("OFF", SWX - 5.0, SWY + SWP, 1.0, just="right")
c1 = b.FindFootprintByReference("C1"); cb = c1.GetBoundingBox(False, False)
silk("C1 220uF 16V", pcbnew.ToMM(cb.GetCenter().x), pcbnew.ToMM(cb.GetBottom()) + 1.2, 1.0)
r1 = b.FindFootprintByReference("R1"); rb = r1.GetBoundingBox(False, False)
silk("R1 470", pcbnew.ToMM(rb.GetCenter().x), pcbnew.ToMM(rb.GetTop()) - 0.9, 1.0)
d1 = b.FindFootprintByReference("D1"); db = d1.GetBoundingBox(False, False)
silk("D1 PWR", pcbnew.ToMM(db.GetRight()) + 1.0, pcbnew.ToMM(db.GetCenter().y), 1.2, just="left")
# (no "S5BUS-D" on the silkscreen: Ken, 2026-11-18, "remove S5BUS-D from bus board"; the name line below says it)
silk("System-5 bus  Rev D  2026", 18.0, H - 13.0, 1.5)       # (where they were before the board grew 2 mm: clear of the
silk("cottageworker.com", 18.0, H - 10.6, 1.5)               # corner hole's screw head)

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
p["net_settings"]["netclass_patterns"] = [{"netclass": "Power", "pattern": "+5V"}, {"netclass": "Power", "pattern": "/VIN"}, {"netclass": "Power", "pattern": "/VIN_D"}, {"netclass": "Power", "pattern": "/5V_REG"}, {"netclass": "Power", "pattern": "/5V_EXT"}, {"netclass": "Power", "pattern": "/5V_SEL"}, {"netclass": "Power", "pattern": "GND"}]
p["board"]["design_settings"]["rules"].update(min_clearance=0.15, min_track_width=0.15, min_via_diameter=0.5, min_via_annular_width=0.13,
    min_through_hole_diameter=0.3, min_hole_clearance=0.25, min_hole_to_hole=0.5, min_copper_edge_clearance=0.5, min_text_height=0.8, min_text_thickness=0.12)
json.dump(p, open(pf, "w"), indent=2)
print("wrote", out, len(fps), "footprints"); sys.stdout.flush(); os._exit(0)
