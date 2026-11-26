#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-22 (after the IO panel card's make_board.py)
"""Build the front panel Rev A board (unrouted) with KiCad's Python (pcbnew), from gen/netlist.py and the schematic's
netlist.

  * 7.50 x 3.50 in (190.5 x 88.9 mm), landscape, as Ken chose (2026-11-22): the board is the front of a case, seen from
    its parts side. An M3 hole in each corner, 5 mm in.
  * across the top: the four ADDRESS displays, the two DATA displays, then the six status LEDs (PWR, Q, PAUSE, RESET,
    ROM, START FROM RAM), each with its label under it and its 1k under that
  * below the displays: the eight bit LEDs, BIT 7 on the left, each over its data toggle; then RUN/RESET and LOAD, and
    the INPUT push-button at the right (the RESET button at the top right, beside START FROM RAM: Ken, 2026-11-26). Toggles 0.5 in apart. A data toggle is up for a 1; RUN and LOAD
    are up for RUN and for LOAD
  * the logic in a row under the toggles: C2, U7-U10 (each with its 0.1 uF at its pin 14 end), RN1 (the bit LEDs'
    resistors), RN2 (the toggles' 1k to +5V), and the RESET button's R7 / C1 by the button
  * J1, the ribbon's header, on the BACK of the board along the bottom edge, pin 1 at the left as seen from the
    front (the address lines' end, under the displays): the ribbon leaves behind the panel. Its name is on the back
    silkscreen and, with "(ON THE BACK)", on the front beside its pins
  * every text at angle 0: the board hangs as drawn, it does not stand in the bus (Ken's rule is that text reads
    upright as the board is used)
  * 2 copper layers, GND pours on both sides, +5V 0.5 mm wide; routed afterwards by Freerouting (gen/route.py)
Writes ../front-panel-rev-a.kicad_pcb."""
import os, sys, re, json
import pcbnew
HERE = os.path.dirname(os.path.abspath(__file__)); DEST = os.path.dirname(HERE); sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(DEST, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "kicad")); import kicad_route, silk270
import netlist as N
MM = pcbnew.FromMM; T = pcbnew.ToMM; V = lambda x, y: pcbnew.VECTOR2I(MM(x), MM(y))
FPLIB = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"
BASE = os.path.join(ROOT, "hardware/bus/kicad/rev-d/s5bus-d.kicad_pcb")       # for its JLCPCB design rules only
NET = os.path.join(DEST, "reports", "netlist.net"); PROJ = "front-panel-rev-a"

X0, Y0, W, H = 10.0, 10.0, 190.5, 88.9
XR, YB = X0 + W, Y0 + H; XC = X0 + W / 2
Y = lambda off: Y0 + off                                # a height measured down from the top edge

forms = kicad_route.top_forms(open(BASE).read())
keep = lambda f: not f.startswith(("(segment", "(via", "(arc", "(zone", "(gr_", "(net ", "(footprint", "(group", "(dimension"))
raw = os.path.join(DEST, "_base.kicad_pcb")
open(raw, "w").write("(kicad_pcb\n\t" + "\n\t".join(f for f in forms if keep(f)) + "\n)\n")
b = pcbnew.LoadBoard(raw); os.remove(raw)
b.SetCopperLayerCount(2)
r = pcbnew.PCB_SHAPE(b); r.SetShape(pcbnew.SHAPE_T_RECT); r.SetStart(V(X0, Y0)); r.SetEnd(V(XR, YB))
r.SetLayer(pcbnew.Edge_Cuts); r.SetWidth(MM(0.1)); b.Add(r)

# ---- placement: (x, y, rotation) of each footprint's origin, mm
P = 12.7                                                # the toggles' pitch
XL = 32.1                                               # BIT 7's column
BITX = [XL + P * (7 - k) for k in range(8)]             # BIT k's column: BIT 7 at the left
RUNX, LOADX, INX = BITX[0] + 16.0, BITX[0] + 16.0 + P, BITX[0] + 32.0 + P
DISPX = [XL, XL + P, XL + 2 * P, XL + 3 * P, 90.0, 90.0 + P]             # U1-U4 the address, U5 / U6 the data
STATX = [126.0 + 11.0 * k for k in range(6)]            # the status LEDs
YDISP, YSTAT, YSRES, YLED, YSW, YROW = Y(18.0), Y(12.0), Y(25.0), Y(39.0), Y(53.0), Y(75.5)
# the RESET button at the top right, beside START FROM RAM, away from INPUT (Ken, 2026-11-26: "it will be too easy to hit
# when pushing input button, move it to the top right beside start from ram led"); 2 mm below the status row, clear of H2
RSTX, RSTY = 190.0, YSTAT + 2.0
PLACE = {}
for (ref, _, _), x in zip(N.DISPLAYS, DISPX): PLACE[ref] = (x, YDISP, 0)                 # origin at the display's centre
for k in range(8):
    PLACE["LED%d" % (k + 1)] = (BITX[k] - 1.27, YLED, 0)                                 # origin at pin 1 (K): centred
    PLACE["SW%d" % (k + 1)] = (BITX[k], YSW, 180)       # turned: pin 3 up, so the lever up joins the line to pin 1 (+5V): a 1
PLACE["SW9"] = (RUNX, YSW, 0)                           # RUN/RESET: lever up = pin 1's end = -RESET let go = RUN
PLACE["SW10"] = (LOADX, YSW, 180)                       # LOAD: lever up = pin 3's end = -PAUSE grounded = LOAD
PLACE["SW11"] = (INX - 3.25, YSW - 2.25, 0)             # the push-buttons: origin at pin 1, the button's centre on the row
PLACE["SW12"] = (RSTX - 3.25, RSTY - 2.25, 0)
for k, (ref, label, sink) in enumerate(N.STATUS):
    PLACE[ref] = (STATX[k] - 1.27, YSTAT, 0)
    PLACE["R%d" % (k + 1)] = (STATX[k] - 3.81, YSRES, 0)
# the logic row: each chip lies along the row (turned 90: pin 1 at the bottom left, pin 14 above it), its 0.1 uF upright
# at that end
ROWX = {"U7": 30.0, "U8": 52.0, "U9": 74.0, "U10": 96.0}
for u, x in ROWX.items(): PLACE[u] = (x, YROW, 90)
PLACE["RN1"] = (118.0, YROW, 90)                        # DIP-16: 17.78 long
PLACE["RN2"] = (142.0, YROW - 3.8, 0)                   # SIP-9, 20.32 long
PLACE["R7"] = (168.0, YROW - 7.0, 0); PLACE["C1"] = (171.0, YROW - 2.0, 0)   # the RESET button's pull-up and capacitor
PLACE["C2"] = (19.5, YROW - 3.8, 90)
for k, u in enumerate(N.BYPASSED):
    if u in ROWX: PLACE["C%d" % (k + 3)] = (ROWX[u] - 3.2, YROW - 3.81, 90)
    else: PLACE["C%d" % (k + 3)] = (PLACE[u][0], YDISP + 12.2, 0)             # a display's: under it
PLACE["J1"] = (XC - 30.48, Y(82.2), 0)                  # (turned and put on the back below)
for k, (hx, hy) in enumerate(((X0 + 5, Y0 + 5), (XR - 5, Y0 + 5), (X0 + 5, YB - 5), (XR - 5, YB - 5))):
    PLACE["H%d" % (k + 1)] = (hx, hy, 0)

for ref, (lib_id, value, fpid, pinmap) in N.PARTS.items():
    lib, name = fpid.split(":")
    fp = pcbnew.FootprintLoad(os.path.join(DEST if lib == "s5fp" else FPLIB, lib + ".pretty"), name)
    fp.SetFPIDAsString(fpid); fp.SetReference(ref); fp.SetValue(value)
    x, y, rot = PLACE[ref]; fp.SetPosition(V(x, y)); fp.SetOrientationDegrees(rot)
    b.Add(fp)
# J1 on the back, along the bottom edge: its pin 1 at the left as seen from the front, its two rows one above the other
j1 = b.FindFootprintByReference("J1")
j1.SetOrientationDegrees(90); j1.Flip(j1.GetPosition(), False)
def pad_at(ref, n):
    c = b.FindFootprintByReference(ref).FindPadByNumber(n).GetPosition(); return T(c.x), T(c.y)
(ax, ay), (bx, by), (cx, cy_) = pad_at("J1", "1"), pad_at("J1", "49"), pad_at("J1", "2")
if abs(ay - by) > 0.01 or ax > bx:                      # the rows must run along x, pin 1 at the left: turn it until they do
    for rot in (0, 90, 180, 270):
        j1.SetOrientationDegrees(rot)
        (ax, ay), (bx, by) = pad_at("J1", "1"), pad_at("J1", "49")
        if abs(ay - by) < 0.01 and ax < bx: break
(ax, ay), (cx, cy_) = pad_at("J1", "1"), pad_at("J1", "2")
j1.SetPosition(V(T(j1.GetPosition().x) + (XC - 30.48 - ax), T(j1.GetPosition().y) + (Y(82.2) - min(ay, cy_))))

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

# GND pours, both sides
for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
    z = pcbnew.ZONE(b); z.SetLayer(layer); z.SetNet(netitem("GND")); z.SetLocalClearance(MM(0.3))
    z.SetMinThickness(MM(0.25)); z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    o = z.Outline(); o.NewOutline()
    for x, y in ((X0 + 0.5, Y0 + 0.5), (XR - 0.5, Y0 + 0.5), (XR - 0.5, YB - 0.5), (X0 + 0.5, YB - 0.5)): o.Append(MM(x), MM(y))
    b.Add(z)

# ---- silkscreen: every text at angle 0, each at the first spot clear of every pad, part and other text (silk270.Silk)
for fp in b.GetFootprints():                            # the parts' own reference and value texts are not used
    fp.Reference().SetVisible(False); fp.Value().SetVisible(False)
sk = silk270.Silk(b, stroke=0.18)
def lab(variants, spots, need=True):
    return sk.place(variants, spots, angle=0, need=need)
def box(ref): return sk.bbox(ref)
def under(ref, d0=1.2, n=10, dx=(0.0, 0.5, -0.5, 1.0, -1.0)):
    l, t, r_, bt = box(ref); return [((l + r_) / 2 + x, bt + d0 + 0.2 * k) for k in range(n) for x in dx]
def over(ref, d0=1.2, n=10, dx=(0.0, 0.5, -0.5, 1.0, -1.0)):
    l, t, r_, bt = box(ref); return [((l + r_) / 2 + x, t - d0 - 0.2 * k) for k in range(n) for x in dx]
# 1. the name, with cottageworker.com under it, at the bottom left
sk.put("System-5 front panel  Rev A  2026", 21.0, Y(82.0), 1.4, 0, "left")
sk.put("cottageworker.com", 21.0, Y(85.2), 1.1, 0, "left")
# 2. the displays: what each group shows over it, each display's digits under it (by function alone: pcb-check.ini)
sk.put("ADDRESS", (DISPX[0] + DISPX[3]) / 2, Y(5.0), 1.5, 0); sk.put("DATA", (DISPX[4] + DISPX[5]) / 2, Y(5.0), 1.5, 0)
for (ref, bus, n), x in zip(N.DISPLAYS, DISPX):
    what = "%s%d-%s%d" % ("A" if bus == "ADR" else "D", n + 3, "A" if bus == "ADR" else "D", n)
    lab([(what, 1.0), (what, 0.8)], [(x, YDISP + 14.6 + 0.2 * k) for k in range(8)])
# 3. the status LEDs: each by what it shows, under it; the last a word a line (Ken, 2026-11-21, on the CPU card)
for k, (ref, label, sink) in enumerate(N.STATUS):
    txt = "START\nFROM\nRAM" if label == "RAM" else label
    lab([(txt, 1.0), (txt, 0.8)], [(STATX[k], YSTAT + (5.6 if label == "RAM" else 3.8) + 0.2 * j) for j in range(6)])
sk.put("STATUS", (STATX[0] + STATX[5]) / 2, Y(5.0), 1.5, 0)
# 4. the bit LEDs by their bit number, over each; the data toggles' two positions; RUN / RESET and LOAD / OFF; the buttons
for k in range(8):
    lab([("%d" % k, 1.2), ("%d" % k, 1.0)], [(BITX[k], YLED - 3.6 - 0.2 * j) for j in range(6)])
    lab([("1", 0.9)], [(BITX[k], YSW - 8.0), (BITX[k] + 3.0, YSW - 8.0)]); lab([("0", 0.9)], [(BITX[k], YSW + 8.0), (BITX[k] + 3.0, YSW + 8.0)])
for x, up, down in ((RUNX, "RUN", "RESET"), (LOADX, "LOAD", "OFF")):
    lab([(up, 1.1), (up, 0.9)], [(x, YSW - 8.3 - 0.2 * j) for j in range(8)]); lab([(down, 1.1), (down, 0.9)], [(x, YSW + 8.3 + 0.2 * j) for j in range(8)])
for x, y, name in ((INX, YSW, "INPUT"), (RSTX, RSTY, "RESET")):
    lab([(name, 1.1), (name, 0.9)], [(x, y + 6.0 + 0.2 * j) for j in range(10)])
# 5. J1, on the back: its name there (mirrored, as the back's silkscreen is read) and on the front beside its pins
(ax, ay), (bx, by) = pad_at("J1", "1"), pad_at("J1", "50")
sk.put("J1 IO PANEL (ON THE BACK)", bx + 3.0, (ay + by) / 2, 1.0, 0, "left")
lab([("1", 0.8)], [(ax - 2.0, ay), (ax - 2.4, ay)], need=False)
for txt, x, y in (("J1 IO PANEL", (ax + bx) / 2, min(ay, by) - 5.2), ("1", ax - 7.2, ay), ("50", bx + 7.8, by)):
    t = pcbnew.PCB_TEXT(b); t.SetText(txt); t.SetLayer(pcbnew.B_SilkS); t.SetTextSize(V(1.0, 1.0)); t.SetTextThickness(MM(0.18))
    t.SetPosition(V(x, y)); t.SetMirrored(True); b.Add(t)
# 6. the chips, then the passives: reference and value beside each
def around(ref):
    l, t, r_, bt = box(ref); cx, cy = (l + r_) / 2, (t + bt) / 2
    return over(ref) + under(ref) + [(l - d, cy + dy) for d in (2.5, 3.5, 4.5) for dy in (0.0, 1.0, -1.0)] + \
        [(r_ + d, cy + dy) for d in (2.5, 3.5, 4.5) for dy in (0.0, 1.0, -1.0)]
for ref in ("U7", "U8", "U9", "U10", "RN1", "RN2"):
    v = N.PARTS[ref][1]; lab([("%s %s" % (ref, v), 1.0), ("%s %s" % (ref, v), 0.8)], over(ref) + under(ref))
for ref in sorted([r_ for r_ in N.PARTS if re.match(r"[RC]\d+$", r_)], key=lambda r_: (r_[0], int(r_[1:]))):
    v = N.PARTS[ref][1]
    lab([("%s %s" % (ref, v), 0.8), ("%s\n%s" % (ref, v), 0.8)], around(ref))
ok = sk.report()

def overlaps(b):
    cy = []
    for fp in b.GetFootprints():
        c = fp.GetCourtyard(pcbnew.B_Cu if fp.IsFlipped() else pcbnew.F_CrtYd)
        if c.OutlineCount() and not fp.IsFlipped(): cy.append((fp.GetReference(), c.BBox()))
    return [(a, bb) for i, (a, ba) in enumerate(cy) for (bb, bbx) in cy[i + 1:] if ba.Intersects(bbx)]
ov = overlaps(b)
print("courtyard overlaps:", ", ".join("%s/%s" % pr for pr in ov) if ov else "none")
print("J1 on the back: pin 1 at (%.2f, %.2f), pin 2 at (%.2f, %.2f), pin 50 at (%.2f, %.2f)" % (pad_at("J1", "1") + pad_at("J1", "2") + pad_at("J1", "50")))
pcbnew.SaveBoard(os.path.join(DEST, PROJ + ".kicad_pcb"), b)

# the Power net class, written into the project after SaveBoard (which rewrites the project file): +5V 0.5 mm wide
pf = os.path.join(DEST, PROJ + ".kicad_pro"); pj = json.load(open(pf))
c = pj["net_settings"]["classes"][0]
pw = dict(c); pw.update(name="Power", track_width=0.5, priority=0)
pj["net_settings"]["classes"] = [c, pw]
pj["net_settings"]["netclass_patterns"] = [{"netclass": "Power", "pattern": "+5V"}]
json.dump(pj, open(pf, "w"), indent=2)
print("board: %d footprints, %d nets%s" % (len(b.GetFootprints()), len(nets), "" if ok else "  (SOME LABELS LEFT OUT)"))
if not ok: raise SystemExit("make_board: silkscreen labels left out")
