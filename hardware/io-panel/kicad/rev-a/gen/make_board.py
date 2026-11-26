#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-30 (from CPU Rev D's make_board.py)
"""Build the IO panel Rev A board (unrouted) with KiCad's Python (pcbnew), from gen/netlist.py and the schematic's netlist.

  * a 36-pin card: 8.00 x 4.00 in (203.2 x 101.6 mm; CPU Rev D's 5.50 in until Ken lengthened it on 2026-11-18, so that
    each display's label fits under it, to 5.75 in; 1.75 in more on 2026-11-20 for the serial port:
    "ok to lengthen board"; 0.50 in more on 2026-11-22 for the front panel's header: he chose "Lengthen to
    8.00 in"), J1 (s5io:C36) down the left edge, centred, the 3.00 x 0.15 in card-support
    strips along the top and bottom edges as copper keep-outs
  * the front panel's header J3 (2026-11-22), a keyed 2x25, upright in the 0.5 in strip at the front edge, beyond
    the displays, which with every other part stayed where it was (XF, the edge until then); pin 1 at the top as
    drawn, so the ribbon's lines leave in the order the displays and toggles stand; RN3, the data lines' pull-downs,
    upright between the UART and the toggle column, its pins in the toggles' order
  * the card's own RESET button SW12 (Ken, 2026-11-23: "the IO card also needs a reset in case front panel is not
    installed") in the top corner of the front strip, above J3 (since 2026-11-26: away from INPUT); its 74HCT03
    (U23) upright between the toggle column and the Q and PWR LEDs' resistors, which moved 3 mm towards the LEDs for it; R4 beside the PWR LED
  * the serial port (2026-11-20) in a strip between the logic and the panel, which moved out with the front edge: the
    DE-9 socket J2 at the top edge as drawn, facing off the board (the left side with the card standing in the bus,
    seen from the parts side), the MAX232 and the null-modem block JP6 behind it, the 16C550 below them with its
    select latch and its oscillator beside it
  * the front panel (Ken, 2026-10-30, after his YACC1 IO card; 2026-11-18 with the bus address): down the front (right)
    edge six TIL311s, the address A15-A12 ... A3-A0 and then the OUT port's two digits, with Q, PWR and the INPUT
    push-button below them; a column of vertical M9040P toggles inside it (BIT 7 at the top ... BIT 0, then RUN/RESET
    and LOAD), each bit's LED between its toggle and the displays (with the card standing in the bus each LED is above
    its toggle); every switch position and LED labelled on the silkscreen (the board layout rules)
  * 2 copper layers, GND pours on both sides; routed afterwards by Freerouting
Writes ../io-panel-rev-a.kicad_pcb."""
import os, sys, re, json
import pcbnew
HERE = os.path.dirname(os.path.abspath(__file__)); DEST = os.path.dirname(HERE); sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(DEST, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "kicad")); import kicad_route
import netlist as N
MM = pcbnew.FromMM; V = lambda x, y: pcbnew.VECTOR2I(MM(x), MM(y))
FPLIB = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"
BASE = os.path.join(ROOT, "hardware/bus/kicad/rev-d/s5bus-d.kicad_pcb")       # for its JLCPCB design rules only
NET = os.path.join(DEST, "reports", "netlist.net"); PROJ = "io-panel-rev-a"

DL = 44.45                                             # the serial port's strip (2026-11-20): 1.75 in more length
FP = 12.7                                              # the front panel header's strip (2026-11-22): 0.50 in more
X0, Y0, W, H = 10.0, 10.0, 146.05 + DL + FP, 101.6
XR, YB = X0 + W, Y0 + H
XF = XR - FP                                           # where the front edge was: the panel's parts are placed from it
CY = Y0 + H / 2

forms = kicad_route.top_forms(open(BASE).read())
keep = lambda f: not f.startswith(("(segment", "(via", "(arc", "(zone", "(gr_", "(net ", "(footprint", "(group", "(dimension"))
raw = os.path.join(DEST, "_base.kicad_pcb")
open(raw, "w").write("(kicad_pcb\n\t" + "\n\t".join(f for f in forms if keep(f)) + "\n)\n")
b = pcbnew.LoadBoard(raw); os.remove(raw)
b.SetCopperLayerCount(2)
r = pcbnew.PCB_SHAPE(b); r.SetShape(pcbnew.SHAPE_T_RECT); r.SetStart(V(X0, Y0)); r.SetEnd(V(XR, YB))
r.SetLayer(pcbnew.Edge_Cuts); r.SetWidth(MM(0.1)); b.Add(r)

# placement: (x, y, rotation) of each footprint's origin, mm. The card is 0.25 in longer than it was (Ken, 2026-11-18):
# the toggles and the bit LEDs stayed where they were on the 5.50 in card (XT, its front edge) and the 6.35 mm went in
# between the bit LEDs and the displays, for each display's label under it; the displays, Q, PWR and INPUT moved with the
# front edge (XR)
XT = X0 + 139.7 + DL                                   # (and the whole panel DL further out since 2026-11-20)
LX, RX, TX = XF - 4.0, XF - 19.0, XT - 36.0           # the Q and PWR LEDs' column, their resistors (XF - 22 until
#                                                        2026-11-23: U23 stands beside them now), the toggle column
BLX = XT - 25.3                                        # the bit LEDs, between the toggles and the displays
LEDY, LEDP = 41.5, 6.2                                 # the old LED rows: Q and PWR keep rows 8 and 9
TILX, TILY, TILP, TILG = XF - 11.0, 17.3, 12.0, 2.6    # the TIL311s: column, first, pitch, the gap before the OUT digits
PLACE = {"J1": (X0 + 5.705, CY, 90)}
for k in range(8):                                     # BIT 7 at the top, as on the YACC1 card
    ty = 20.0 + 9.0 * (7 - k)
    PLACE["SW%d" % (k + 1)] = (TX, ty, 90)                                       # toggles: 9 mm pitch (bodies 8.6 mm)
    PLACE["LED%d" % (k + 1)] = (BLX - 1.27, ty, 0)     # its LED level with it (Ken, 2026-11-18): above it when standing;
                                                       # pads across the strip, so the displays' labels fit between LEDs
# RUN/RESET is turned end for end (270; Ken, 2026-11-23): up is RUN, as on the front panel (and up is LOAD and 1). The
# M9040P's origin is its middle pin, so its body stays on the 9 mm pitch and only pins 1 and 3 change places
PLACE.update({"SW10": (TX, 20.0 + 9.0 * 8, 270), "SW11": (TX, 20.0 + 9.0 * 9, 90),
              "SW9": (XF - 12.7, 102.8, 0),            # INPUT in the bottom corner of the panel
              # the front panel's header, upright in the new strip (its body 9 mm of the 12.7), centred on the card's
              # height: pin 1 (and the odd row) on the panel's side, at the top; RN3 with pin 1 (ground) at the bottom,
              # so that SW7 ... SW0 stand in the toggles' order, BIT 7 at the top
              "J3": (XF + 5.08, CY - 30.48, 0), "RN3": (142.0, 80.0, 90),
              # the card's own RESET (2026-11-23): its two gates (U23) upright between the toggles and R2 / R3, its
              # capacitor under it; R4 upright beside the PWR LED. The button itself in the strip's TOP corner, above J3,
              # the far end of the front edge from INPUT (Ken, 2026-11-26: "Yes, move it too": it was beside INPUT, too
              # easy to hit when pressing INPUT); its origin at pin 1, the button's centre at (XF + 6.35, 18.0)
              "SW12": (XF + 6.35 - 3.25, 18.0 - 2.25, 0), "U23": (168.4, 88.5, 0), "C26": (172.2, 107.6, 0), "R4": (198.0, 108.1, 90),
              "LED9": (LX, LEDY + LEDP * 8 - 1.27, 90), "R2": (RX, LEDY + LEDP * 8, 0),
              "LED10": (LX, LEDY + LEDP * 9 - 1.27, 90), "R3": (RX, LEDY + LEDP * 9, 0)})
# the TIL311s turned -90 (Ken, 2026-11-17): with the card in the cage, bus edge down, each digit stands upright, its bottom
# toward the bus connector, as on his YACC1 IO card. Down the front edge, so in the cage they read left to right: the
# address U14 (A15-A12), U15, U16, U17 (A3-A0) (Ken, 2026-11-18), then the OUT port's U7 (bits 7-4) and U8
for i, u in enumerate(("U14", "U15", "U16", "U17", "U7", "U8")):
    PLACE[u] = (TILX, TILY + TILP * i + (TILG if i >= 4 else 0.0), -90)
PLACE.update({                                         # the logic, between the bus and the panel
    # the top row: four 14-pin chips at a 12 mm pitch, then the RTC (U13, 24 pins) at the right with its crystal Y1 on
    # its left beside X1 / X2 (pins 2, 3), as the DS12885 data sheet asks: short leads
    "U5": (25.5, 22.0, 0), "U6": (37.5, 22.0, 0), "U4": (49.5, 22.0, 0), "U12": (61.5, 22.0, 0),
    "Y1": (72.1, 18.3, -90), "U13": (75.0, 15.6, 0),
    # the middle row as before; U1 at the bottom left
    "U2": (24.0, 56.0, 0), "U3": (40.0, 56.0, 0), "U9": (56.0, 56.0, 0), "U10": (70.0, 56.0, 0),
    "U11": (83.0, 56.0, 0), "U1": (26.0, 85.5, 0),
    # between the rows: the pull-ups and INPUT's RC; C2 and the RTC's battery (flat: 6 mm tall) under the middle row
    "RN1": (26.0, 45.0, 0), "R1": (51.5, 45.0, 0), "C1": (64.0, 45.0, 0), "C2": (53.6, 79.0, 0),
    "BT1": (61.65, 86.9, 0),
    # REQ's clear and DRIVE's gate (2026-11-25), upright in the gaps of the middle row: D1 between U9 and U10, R5
    # between U10 and U11, R6 between U3 and U9, each label in line with its part, below it as drawn
    "D1": (66.8, 64.0, 90), "R5": (80.3, 64.0, 90), "R6": (51.8, 64.0, 90),
    # the jumper blocks near the bottom edge, clear of the card-support strip: IN port, OUT port, INPUT's EF line;
    # the RTC's ports and IRQ (JP4) above them
    "JP1": (38.0, 105.0, 90), "JP2": (60.0, 105.0, 90), "JP3": (82.0, 105.0, 90), "JP4": (40.5, 91.0, 90),
    "JP5": (108.6, 12.0, 90),            # the RTC's RAM-clear jumper at the top edge by U13, between C16 and C10, above the
                                         # BIT 7 toggle (not shifted with the logic)
    # a column between the logic and the toggles (Ken, 2026-11-18): the address latches U18 (high byte) and U19 (low byte)
    # and RN2, the bit LEDs' resistors; their caps C16 above U18 and C17 between RN2 and U19
    "U18": (93.4, 17.0, 0), "RN2": (93.4, 46.0, 0), "U19": (93.4, 74.6, 0)})
# the serial port (2026-11-20), in the strip between the latch column and the toggles (x 101 to 148):
#   J2, the DE-9 socket, at the top edge, facing off the board: its mounting holes 10.22 mm from the edge, as on the
#   YACC1 I/O card (built), so its flange is 0.7 mm inside the edge and its shroud beyond it. KiCad's footprint has
#   its origin at pin 1 and its face towards +y: turned 180 here, pin 1 at the left. JP5 keeps its place left of it
#   U21 MAX232 lying behind J2, its line side (pins 13, 14) towards J2, its capacitor pins (1-6) away from it, the four
#   1 uF capacitors at those pins; JP6 beside it under J2's pins 2 and 3
#   U20 the 16C550 below, D0-D7 (pins 1-8) on its bus side; left of it U22, the select latch, and X1, the oscillator,
#   beside XIN (pin 16); JP7 (UART INT) at the bottom edge
SERIAL = {"J2": (131.65 - 5.54, Y0 + 10.22 + 1.42, 180), "U21": (112.0, 37.0, 90), "JP6": (134.0, 31.0, 90),
          "C22": (112.0, 43.0, 0), "C23": (119.6, 43.0, 0), "C24": (106.0, 33.2, 0), "C25": (129.7, 43.0, 180),
          "U20": (118.0, 49.0, 0), "U22": (104.0, 52.0, 0), "X1": (105.3, 92.0, 0), "JP7": (100.0, 105.5, 90)}
PLACE.update(SERIAL)
# the logic and the latch column 2 mm nearer the bus (2026-11-18, for Ken's rule that every silk text reads upright with
# the card standing in the bus, at 270 here): the bus pins' names at 270 take less room than they did at 0, and the
# latch column needs room on its toggle side for its own labels
SHIFT = -2.0
for ref in ("U5", "U6", "U4", "U12", "Y1", "U13", "U2", "U3", "U9", "U10", "U11", "U1", "RN1", "R1", "C1", "C2", "BT1", "D1", "R5", "R6",
            "JP1", "JP2", "JP3", "JP4", "U18", "RN2", "U19"):
    x, y, rot = PLACE[ref]; PLACE[ref] = (x + SHIFT, y, rot)
for k, u in enumerate(N.BYPASSED):
    x, y, _ = PLACE[u]
    PLACE["C%d" % (k + 3)] = ((TILX + 6.33, TILY + TILP * 3.5 + TILG / 2, 180) if u == "U7"   # C9: the six TIL311s'
                             else (118.0 + DL, 12.0, 180) if u == "U8"   # rail, in the gap before U7; C10 at its top
                             else (137.5, 47.5, 0) if u == "U20"         # C18: by the UART's VCC (pin 40)
                             else (113.3, 25.8, 0) if u == "U21"         # C19: over the MAX232's VCC and GND (16, 15)
                             else (107.0, 79.0, 0) if u == "X1"          # C21: over the oscillator can
                             else (37.0 + SHIFT, 97.0, 90) if u == "U1"                           # beside U1, low
                             else (89.3, 12.0, 0) if u == "U13" # by VCC (pin 24), past the card-support strip: not
                             # shifted, or its +5V pad sits in the strip's keep-out and no seed routes it
                             else (101.3 + SHIFT, 12.0, 0) if u == "U18"  # above U18
                             else (97.0 + SHIFT, 70.0, 0) if u == "U19"   # between RN2 and U19
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

def keepout(pts, layers, fill=False):
    k = pcbnew.ZONE(b); k.SetIsRuleArea(True); k.SetLayerSet(layers)
    k.SetDoNotAllowTracks(True); k.SetDoNotAllowVias(True); k.SetDoNotAllowZoneFills(not fill)
    k.SetDoNotAllowPads(False); k.SetDoNotAllowFootprints(False)
    o = k.Outline(); o.NewOutline()
    for x, y in pts: o.Append(MM(x), MM(y))
    b.Add(k)
for ya, yb in ((Y0, Y0 + 3.81), (YB - 3.81, YB)):
    keepout([(X0, ya), (X0 + 76.2, ya), (X0 + 76.2, yb), (X0, yb)], pcbnew.LSET.AllCuMask())
# the RTC's crystal (DS12885 data sheet: short leads, no other signal beside or under them): X1 and X2 drawn here, short and
# locked, on F.Cu; no other track or via under them on B.Cu (the GND pour still fills it), nor between U12 and Y1 on F.Cu
def track(a, c, net, layer=pcbnew.F_Cu, w=0.25):
    t = pcbnew.PCB_TRACK(b); t.SetStart(V(*a)); t.SetEnd(V(*c)); t.SetLayer(layer); t.SetWidth(MM(w))
    t.SetNet(netitem(net)); t.SetLocked(True); b.Add(t)
for yp, up in (("1", "2"), ("2", "3")):                 # Y1 pin 1 to U13 X1 (pin 2), Y1 pin 2 to U13 X2 (pin 3)
    pa = b.FindFootprintByReference("Y1").FindPadByNumber(yp); pb = b.FindFootprintByReference("U13").FindPadByNumber(up)
    track((pcbnew.ToMM(pa.GetPosition().x), pcbnew.ToMM(pa.GetPosition().y)),
          (pcbnew.ToMM(pb.GetPosition().x), pcbnew.ToMM(pb.GetPosition().y)), pa.GetNetname())
# +5V where Freerouting, with the 0.5 mm Power class, left gaps on every seed tried (2026-11-18): drawn here, locked, on B.Cu.
# The TIL311s' supply pins (1 and 14, the column nearest the front edge): a rail from C9 along the top margin, down that
# column and back to C10. J1's +5V (position 30 since 2026-11-18) to C7, U5's cap, past U5's left side.
def pad_at(ref, n):
    c = b.FindFootprintByReference(ref).FindPadByNumber(n).GetPosition(); return pcbnew.ToMM(c.x), pcbnew.ToMM(c.y)
def path(pts, net, layer=pcbnew.B_Cu, w=0.5):
    for a, c in zip(pts, pts[1:]): track(a, c, net, layer, w)
(c10x, c10y) = pad_at("C10", "1")
rail = sorted([pad_at(u, n) for u in ("U14", "U15", "U16", "U17", "U7", "U8") for n in ("1", "14")], key=lambda p: p[1])
path([(c10x, c10y), (c10x, Y0 + 1.2), (rail[0][0], Y0 + 1.2)] + rail, "+5V")     # C9's + pad sits on it, between U17 and U7
# the front panel's supply (2026-11-22): J3's +5V pins, 1 and 2 at the top and 49 and 50 at the bottom, from that rail:
# straight across from it at the top; from its last pad at the bottom, out past the Q LED's pads first
(p1x, p1y), (p2x, p2y), (p49x, p49y), (p50x, p50y) = (pad_at("J3", n) for n in ("1", "2", "49", "50"))
path([(rail[0][0], p1y), (p1x, p1y), (p2x, p2y)], "+5V")
path([rail[-1], (XF - 0.6, rail[-1][1]), (XF - 0.6, p49y), (p49x, p49y), (p50x, p50y)], "+5V")
(jx, jy), (c7x, c7y) = pad_at("J1", str(N.POS.index("+5V") + 1)), pad_at("C7", "1")
path([(jx, jy), (X0 + 10.5, jy), (X0 + 10.5, c7y), (c7x, c7y)], "+5V")     # clear of U5's pin 1 since the shift
# the serial line between the DE-9, the null-modem block and the MAX232 (2026-11-20): drawn here, locked. In the block
# each signal sits on two pins diagonally across the middle column, so the six links cross one another in a 5 x 8 mm
# patch; Freerouting left the DE-9's pin 2 open on two seeds of three. Front: TX_OUT from U21 to JP6 pin 2, DE9_3 down
# between the block's first two columns to pin 3, RX_IN from pin 1 round the block's end to pin 6. Back: DE9_2 to pin
# 4, RX_IN from U21 to pin 1, TX_OUT from pin 2 between the rows to pin 5
def link(pts, a, layer):
    net = b.FindFootprintByReference(a[0]).FindPadByNumber(a[1]).GetNetname()
    for p_, q_ in zip(pts, pts[1:]): track(p_, q_, net, layer, 0.25)
j = {n: pad_at("JP6", str(n)) for n in range(1, 7)}       # 1, 3, 5 on the row away from J2; 2, 4, 6 on the row towards it
(d2x, d2y), (d3x, d3y) = pad_at("J2", "2"), pad_at("J2", "3"); (t14x, t14y), (r13x, r13y) = pad_at("U21", "14"), pad_at("U21", "13")
mx, my = (j[1][0] + j[3][0]) / 2, (j[1][1] + j[2][1]) / 2  # between the first two columns; between the two rows
link([(t14x, t14y), (t14x, j[2][1] - 1.16), (j[2][0] - 1.16, j[2][1] - 1.16), j[2]], ("U21", "14"), pcbnew.F_Cu)
link([(d3x, d3y), (d3x, j[2][1] - 2.46), (mx, j[2][1] - 2.46), (mx, my), j[3]], ("J2", "3"), pcbnew.F_Cu)
link([j[1], (j[1][0] + 1.0, j[1][1] + 1.55), (j[5][0] + 1.4, j[5][1] + 1.55), (j[5][0] + 1.85, j[5][1] + 1.1),
      (j[6][0] + 1.85, j[6][1]), j[6]], ("JP6", "1"), pcbnew.F_Cu)
link([(d2x, d2y), (d2x, j[4][1] - 3.86), (j[4][0], j[4][1] - 3.86), j[4]], ("J2", "2"), pcbnew.B_Cu)
link([(r13x, r13y), (r13x, j[2][1] - 2.06), (j[1][0] - 1.7, j[2][1] - 2.06), (j[1][0] - 1.7, j[1][1]), j[1]], ("U21", "13"), pcbnew.B_Cu)
link([j[2], (mx, my), ((j[3][0] + j[5][0]) / 2, my), j[5]], ("JP6", "2"), pcbnew.B_Cu)
# the serial block's +5V (2026-11-20), drawn and locked on B.Cu like the displays' rail: with the 0.5 mm Power class
# Freerouting left one to four +5V links open on every seed tried. C19 - U21 (pin 16) - C24, down to a rail under the
# MAX232's capacitors, 3 mm above the UART: C20, U22 (pin 20), U20 (pin 40) and C18 hang from it; U20's tied-off modem
# inputs (pins 39-36) down its own pin column from pin 40; C21 and the oscillator's two pins down its left side.
# Freerouting joins these to the rest of +5V and brings it to U20's pins 13 and 18
YR = pad_at("U20", "40")[1] - 3.0
c19, u21v, c24 = pad_at("C19", "1"), pad_at("U21", "16"), pad_at("C24", "2")
path([c19, u21v, (u21v[0] - 1.9, u21v[1] + 1.9), (u21v[0] - 1.9, c24[1]), c24, (c24[0], YR)], "+5V")
c20, c18 = pad_at("C20", "1"), pad_at("C18", "1")
path([c20, (c20[0], YR), (c18[0], YR), c18], "+5V")
for ref, n in (("U22", "20"), ("U20", "40")):
    x_, y_ = pad_at(ref, n); path([(x_, YR), (x_, y_)], "+5V")
path([pad_at("U20", n) for n in ("40", "39", "38", "37", "36")], "+5V")
c21, x8, x1_ = pad_at("C21", "1"), pad_at("X1", "8"), pad_at("X1", "1")
path([c21, (x8[0], c21[1] + abs(c21[0] - x8[0])), x8, x1_], "+5V")
XA, XB, YA, YB_ = 70.0 + SHIFT, 76.6 + SHIFT, 16.6, 22.2
def one(layer): ls = pcbnew.LSET(); ls.AddLayer(layer); return ls
keepout([(XA, YA), (XB, YA), (XB, YB_), (XA, YB_)], one(pcbnew.B_Cu), fill=True)
keepout([(70.2 + SHIFT, YA), (71.45 + SHIFT, YA), (71.45 + SHIFT, YB_), (70.2 + SHIFT, YB_)], one(pcbnew.F_Cu), fill=True)
for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
    z = pcbnew.ZONE(b); z.SetLayer(layer); z.SetNet(netitem("GND")); z.SetLocalClearance(MM(0.3))
    z.SetMinThickness(MM(0.25)); z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    o = z.Outline(); o.NewOutline()
    for x, y in ((X0 + 0.5, Y0 + 0.5), (XR - 0.5, Y0 + 0.5), (XR - 0.5, YB - 0.5), (X0 + 0.5, YB - 0.5)): o.Append(MM(x), MM(y))
    b.Add(z)

# silkscreen (Ken, 2026-11-18, every board on every system): every text reads upright, left to right, with the card
# standing in the bus, connector down: KiCad angle 270 on this card (bus on the left as drawn). The name line alone may
# run up a side edge instead (angle 0 along the bottom edge as drawn), and does. The fixed labels (the toggles', the bit
# numbers, the jumper rows') go where they belong; every other label at the first spot clear of every pad (0.3 mm), part
# body and outline, other text and the board edge
UP = 270
def boxof(bb, m=0.0):
    return pcbnew.ToMM(bb.GetLeft()) - m, pcbnew.ToMM(bb.GetTop()) - m, pcbnew.ToMM(bb.GetRight()) + m, pcbnew.ToMM(bb.GetBottom()) + m
blocks = []
for fp in b.GetFootprints():
    fp.Reference().SetVisible(False); fp.Value().SetVisible(False)
    for item in fp.GraphicalItems():                     # the YACC1 footprints' own texts: off the silk (KiCad keeps no
        if isinstance(item, pcbnew.PCB_TEXT) and item.GetLayer() == pcbnew.F_SilkS:   # hidden flag for them)
            item.SetLayer(pcbnew.F_Fab)
    for p in fp.Pads():
        blocks.append(boxof(p.GetBoundingBox(), 0.3))
    fab = [g for g in fp.GraphicalItems() if g.GetLayer() == pcbnew.F_Fab and not isinstance(g, pcbnew.PCB_TEXT)]
    out = [g for g in fp.GraphicalItems() if g.GetLayer() == pcbnew.F_SilkS and not isinstance(g, pcbnew.PCB_TEXT)]
    for items in (fab, out):                             # the body (F.Fab) and the outline (F.SilkS), each as one box:
        if items:                                        # drawn as separate lines, a part's inside would look free
            bs = [boxof(g.GetBoundingBox(), 0.1) for g in items]
            blocks.append((min(c[0] for c in bs), min(c[1] for c in bs), max(c[2] for c in bs), max(c[3] for c in bs)))
    if not fab and fp.GetCourtyard(pcbnew.F_CrtYd).OutlineCount():
        blocks.append(boxof(fp.GetCourtyard(pcbnew.F_CrtYd).BBox(), 0.0))
EDGE = (X0, Y0, XR, YB)
# the card-support strips (3.00 x 0.15 in from the bus edge along the top and bottom edges): no label in them, where a
# card guide would hide it (2026-11-18: the jumper blocks' row numbers and some caps' labels first stood in them)
blocks += [(X0, Y0, X0 + 76.2, Y0 + 3.81), (X0, YB - 3.81, X0 + 76.2, YB)]
def free(box):
    if box[0] < EDGE[0] + 0.5 or box[1] < EDGE[1] + 0.5 or box[2] > EDGE[2] - 0.5 or box[3] > EDGE[3] - 0.5:
        return False
    return not any(box[0] < c[2] and c[0] < box[2] and box[1] < c[3] and c[1] < box[3] for c in blocks)
def silk(txt, x, y, h=1.0, angle=UP, just=None, add=True):
    t = pcbnew.PCB_TEXT(b); t.SetText(txt); t.SetLayer(pcbnew.F_SilkS); t.SetTextSize(V(h, h))
    t.SetTextThickness(MM(max(0.18, 0.15 * h))); t.SetPosition(V(x, y))
    if just == "left": t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
    if just == "right": t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_RIGHT)
    if angle: t.SetTextAngleDegrees(angle)
    if add:
        b.Add(t); blocks.append(boxof(t.GetBoundingBox(), 0.2))
    return t
def place(variants, spots, need=True, just=None):
    """the first variant (text, height) that fits at one of spots [(x, y)], variant by variant. just="left": the
    lines of a block start level (the spot is then the block's start, not its middle)"""
    for txt, h in variants:
        for x, y in spots:
            t = silk(txt, x, y, h, just=just, add=False)
            if free(boxof(t.GetBoundingBox())):
                b.Add(t); blocks.append(boxof(t.GetBoundingBox(), 0.2)); return x, y, txt, h
    if need:
        for x, y in spots[:2]:                         # say what is in the way
            bx = boxof(silk(variants[-1][0], x, y, variants[-1][1], add=False).GetBoundingBox())
            print("  at (%.1f, %.1f) box %s blocked by %s" % (x, y, tuple(round(v, 2) for v in bx),
                  [tuple(round(v, 2) for v in c) for c in blocks if bx[0] < c[2] and c[0] < bx[2] and bx[1] < c[3] and c[1] < bx[3]][:6]))
        raise SystemExit("silk: no room for %r near (%.1f, %.1f)" % (variants[0][0], spots[0][0], spots[0][1]))
def bbox(ref):
    bb = b.FindFootprintByReference(ref).GetBoundingBox(False)
    return pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetTop()), pcbnew.ToMM(bb.GetRight()), pcbnew.ToMM(bb.GetBottom())
def pad(ref, n):
    c = b.FindFootprintByReference(ref).FindPadByNumber(n).GetPosition(); return pcbnew.ToMM(c.x), pcbnew.ToMM(c.y)
def beside(ref, reach=6.0, dys=(0.0, 1.0, -1.0, 2.0, -2.0, 3.0, -3.0, 4.0, -4.0)):
    """spots beside a part: off its sides along x first (a 270 text runs along y), nearest first, then off its ends"""
    l, t, rr, bt = bbox(ref); cx, cy = (l + rr) / 2, (t + bt) / 2; out = []
    for k in range(int(reach / 0.2)):
        d = 0.9 + 0.2 * k
        for dy in dys:
            out += [(rr + d, cy + dy), (l - d, cy + dy)]
    for k in range(int(reach / 0.2)):
        d = 1.0 + 0.2 * k
        for dx in (0.0, 1.5, -1.5, 3.0, -3.0):
            out += [(cx + dx, bt + d), (cx + dx, t - d)]
    return out
# where a part's label goes when the spots beside() tries would not do (the serial port's block, 2026-11-20): the
# MAX232's between two of its capacitors, the oscillator's under its can, the DE-9's in the clear patch right
# of JP6 (under the DE-9 itself the connector would cover them)
SPOTS = {"U13": [(70.2 + dx, 34.0 + dy) for dy in (0.0, 1.0, 2.0, 3.0, 4.0) for dx in (0.0, 0.1, -0.1, 0.2)],   # its bus side,
         "C12": [(70.0 + dx, 45.6 + dy) for dy in (0.0, -0.3, 0.2, -0.6) for dx in (0.0, 0.2, -0.2)],   # away from U10's line
         "U21": [(116.96 + dx, 43.0 + dy) for dx in (0.0, 0.1, -0.1) for dy in (0.0, 0.5, -0.5, 1.0, -1.0)],
         "X1": [(109.0 + dx, 101.0 + dy) for dx in (0.0, 1.0, -1.0, 2.0, -2.0) for dy in (0.0, 0.3, -0.3, 0.6)],
         "D1": [(64.8 + dx, 70.6 + dy) for dy in (0.0, 0.4, 0.8, 1.2) for dx in (0.0, 0.1, -0.1)],
         "R5": [(78.3 + dx, 70.6 + dy) for dy in (0.0, 0.4, 0.8, 1.2) for dx in (0.0, 0.1, -0.1)],
         "R6": [(49.8 + dx, 70.6 + dy) for dy in (0.0, 0.4, 0.8, 1.2) for dx in (0.0, 0.1, -0.1)],
         "J2": [(145.8 + dx, 29.5 + dy) for dx in (0.0, 0.2, -0.2, -0.4) for dy in (0.0, 0.5, 1.0, 1.5, 2.0)]}
def label(ref, text, two=None):
    """a part's label beside it: one line at 1.0 or 0.8 mm, else two (reference over value)"""
    v = [(text, 1.0), (text, 0.8)] + ([(two, 1.0), (two, 0.8)] if two else [])
    if ref in SPOTS:
        got = place(v, SPOTS[ref], need=False)
        if got: return got
    return place(v, beside(ref))

# 1. the name line: along the bottom edge as drawn, up the right-hand side with the card standing (the rule's exception)
silk("System-5 IO panel  Rev A  2026", 98.5 + DL, YB - 4.2, 1.2, angle=0)      # (no "S5IO-A": Ken, 2026-11-18; 14.5 mm
silk("cottageworker.com", 98.5 + DL, YB - 2.0, 1.0, angle=0)                    # further left since 2026-11-23, for C26)
# 2. the bus: J1's pins' names beside them at 270 in two staggered rows (one row would not fit the 2.54 mm pitch), and
#    "J1 BUS" beside the names, the connector's middle first, at 1.0 mm where that fits (as tools/kicad/silk270.py's
#    bus_label places it on the other cards). Until 2026-11-18 it stood in the margin between the pads and the bus edge:
#    J1 is a right-angle header, and its plastic body lies there (on F.Fab in the C36 footprint since then)
for k, p in enumerate(sorted(b.FindFootprintByReference("J1").Pads(), key=lambda p: p.GetPosition().y)):
    x, y = pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y)
    name = N.POS[int(p.GetNumber()) - 1]
    xs = (x + 2.4, x + 4.2) if k % 2 == 0 else (x + 4.2, x + 2.4)
    # a long name at an end pin (2026-11-18: "-PAUSE" at the top end, by the card-support strip) may go one column
    # further out, or 0.5 or 1.0 mm towards the middle, before it would shrink to 0.7 mm (DRC's minimum is 0.8)
    toward = 1.0 if y < CY else -1.0
    place([(name, 0.8), (name, 0.7)], [(xx, y) for xx in xs] + [(xx, y + toward * d) for d in (0.5, 1.0) for xx in (x + 6.0,) + xs])
_x0 = pad("J1", "1")[0] + 4.2 + 1.8; _ys = [CY + sg * 0.25 * n for n in range(160) for sg in (1, -1)]
if not place([("J1 BUS", 1.0), ("J1 BUS", 0.8)], [(_x0 + 0.2 * k, y) for y in _ys for k in range(8)], need=False):
    place([("J1 BUS", 1.0), ("J1 BUS", 0.8)], [(_x0 + 0.2 * k, y) for k in range(8, 40) for y in _ys])
# the RTC's crystal first: between U12, U13 and the card-guide strip it has the least room of any part
label("Y1", "Y1 32.768kHz", "Y1\n32.768kHz")
# 3. the toggles: a toggle closes the common to the end AWAY from its lever, so each end is labelled with what the lever
#    there selects; its name below the toggle (with the card standing), within its 9 mm row. The front panel's switches
#    and displays are labelled by their function alone, as its LEDs are (Ken, 2026-11-18: no SW1 ..., no U14 TIL311 ...;
#    pcb-check.ini exempts them)
def toggle(ref, name, at1, at3):
    (x1, y1), (x3, y3) = pad(ref, "1"), pad(ref, "3")
    l, t, rr, bt = bbox(ref); cy = (t + bt) / 2
    silk(name, l - 2.75, cy, 0.8)
    silk(at3, rr + 0.85 if x3 > x1 else l - 0.85, cy, 0.8)         # lever at pin 3: pin 1
    silk(at1, rr + 0.85 if x1 > x3 else l - 0.85, cy, 0.8)         # lever at pin 1: pin 3
for k in range(8): toggle("SW%d" % (k + 1), "BIT %d" % k, "0", "1")     # pin 1 = +5V, pin 3 = GND
toggle("SW10", "RUN/RESET", "RUN", "RESET")                              # pin 1 = -RESET: lever at pin 3 grounds it
toggle("SW11", "LOAD", "OFF", "LOAD")                                    # pin 1 = -PAUSE
# 4. the bit LEDs by their bit number (Ken, 2026-11-18: LEDs by function; pcb-check.ini exempts their references),
#    between each LED and the displays: above it with the card standing
for k in range(8):
    l, t, rr, bt = bbox("LED%d" % (k + 1)); silk("%d" % k, BLX + 3.35, (t + bt) / 2, 0.8)
# 5. the TIL311s: what each shows, under each display with the card standing (Ken, 2026-11-18: the card lengthened for
#    them, as they had sat in the gaps between the bit LEDs, too close to them; by function alone, as above); C9, the
#    displays' cap in the gap between the address and the OUT digits, under it in that gap
def body(ref):
    """a part's body, its F.Fab drawing, as one box"""
    fab = [g.GetBoundingBox() for g in b.FindFootprintByReference(ref).GraphicalItems()
           if g.GetLayer() == pcbnew.F_Fab and not isinstance(g, pcbnew.PCB_TEXT)]
    return (min(pcbnew.ToMM(g.GetLeft()) for g in fab), min(pcbnew.ToMM(g.GetTop()) for g in fab),
            max(pcbnew.ToMM(g.GetRight()) for g in fab), max(pcbnew.ToMM(g.GetBottom()) for g in fab))
for ref, what in (("U14", "A15-A12"), ("U15", "A11-A8"), ("U16", "A7-A4"), ("U17", "A3-A0"),
                  ("U7", "OUT D7-D4"), ("U8", "OUT D3-D0")):
    l, t, rr, bt = body(ref)
    place([(what, 1.0), (what, 0.8)], [(l - d, (t + bt) / 2) for d in (1.6, 1.8, 2.0, 2.2, 2.4, 2.6, 2.8, 3.0)])   # (at 1.2 mm
    # the two OUT labels ran together)
l, t, rr, bt = body("C9")
place([("C9\n0.1uF", 0.8)], [(l - d, (t + bt) / 2 + dy) for d in (1.8, 2.0, 2.2, 2.6, 3.0) for dy in (0.0, 0.2, -0.2)])
# 6. the jumper blocks: each row's port or line beside its pins, the block's name at an end of it
for ref, title, cols in (("JP1", "JP1 IN PORT", "1234567"), ("JP2", "JP2 OUT PORT", "1234567"),
                         ("JP3", "JP3 INPUT EF", ("1", "2", "3", "EF")),   # -EF1..-EF3, -EF: between the battery
                         # and the card-guide strip only single characters fit under the first three columns
                         ("JP4", "JP4 RTC + UART", ("A2", "A4", "A6", "D3", "D5", "D7", "INT"))):
    for n, name in enumerate(cols):
        x, y = pad(ref, str(2 * n + 1))
        near = [(x, y + 2.9), (x, y + 1.85)] if len(name) == 1 else [(x, y + 3.6)]   # under the block as drawn, else
        place([(name, 0.8)], near + [(x, y - 2.54 - d) for d in (2.4, 2.9, 3.6, 4.2)])  # over it (the strip below)
JP_TITLES = [("JP1", "JP1 IN PORT"), ("JP2", "JP2 OUT PORT"), ("JP3", "JP3 INPUT EF"),
             ("JP4", "JP4 RTC + UART")]   # placed last:
# the caps beside the blocks have fewer places to go than the blocks' titles
# 7. the front panel's other parts, then the chips, the passives, the crystal and the battery
for ref, name in (("LED9", "Q"), ("LED10", "PWR")):
    l, t, rr, bt = bbox(ref)
    place([(name, 1.0), (name, 0.8)], [(l - d, (t + bt) / 2) for d in (0.9, 1.1, 1.3, 1.6)])
for ref in ("R2", "R3"):                               # Q's and PWR's resistors: each label under its own (with the
    l, t, rr, bt = bbox(ref); txt = "%s %s" % (ref, N.PARTS[ref][1])     # card standing), not off toward U8's
    place([(txt, 1.0), (txt, 0.8)], [(l - d, (t + bt) / 2) for d in (1.0, 1.2, 1.4, 1.6, 2.0)])
place([("INPUT", 1.0), ("INPUT", 0.8)], beside("SW9"))     # the push-button, by its function alone
place([("RESET", 1.0), ("RESET", 0.8)], beside("SW12"))    # the card's own boot reset (2026-11-23), by its function too
label("C10", "C10 %s" % N.PARTS["C10"][1], "C10\n%s" % N.PARTS["C10"][1])
# JP5, the RTC's RAM-clear jumper, in the 5 mm strip between the top edge and the BIT 7 toggle: its name under it (with
# the card standing), left of the toggle where a line may be 7 letters long, and what a shunt does over it
place([("JP5 RTC\nRAM CLR", 0.8)], [(x, y) for x in (105.1, 105.0, 105.2, 104.9) for y in (14.2, 14.4, 14.0, 14.6, 13.8)])
place([("FIT =\nCLEAR", 0.8)], [(x, y) for x in (114.1, 114.0, 114.2, 113.9, 114.3) for y in (12.9, 13.0, 12.8, 13.2)])
# (placed here since 2026-11-20, before the parts' labels: its two places are fixed, theirs are not)
# the serial port's settings, each beside its own jumper (Ken, 2026-11-23: "better silk screen" for the serial port, then
# "yes as suggested"). Nothing at the DE-9's own pins (they were numbered there for an hour: "we don't need pin 2,3 5 it is
# cluttering"). Under JP6 as drawn
# (right of it with the card standing) its two settings as pictures, the way the block stands: its outline, its six
# pins, the two shunts outlined where they go, and beside each picture what the DE-9's pins 2 and 3 then are (Ken: "it is not clear
# where jumpers go for each mode ... there is no need to show the words null modem but it should be clear how to
# configure the jumpers"). 1-3 and 2-4 (the lower two rows with the card standing): the card sends on pin 2; 3-5 and 4-6:
# on pin 3. JP7's name with what a shunt does
_y6 = bbox("JP6")[3]
def shunts(x, y, pairs, pitch=1.4):
    """a picture of a jumper block: its pins as dots, rows along x and columns along y (as JP6 lies on the board), the
    middle at (x, y), and a rounded outline round each pair of pins that a shunt joins: pairs [(row, row, column)]"""
    R = 0.475                                            # half a shunt's width
    def shape(kind, a, c, w, fill=False):
        q = pcbnew.PCB_SHAPE(b); q.SetShape(kind); q.SetLayer(pcbnew.F_SilkS); q.SetWidth(MM(w)); q.SetStart(V(*a)); q.SetEnd(V(*c))
        if fill: q.SetFilled(True)
        b.Add(q); return q
    at = lambda row, col: (x + (row - 1) * pitch, y + (col - 0.5) * pitch)
    for row in range(3):
        for col in range(2):
            cx, cy = at(row, col); shape(pcbnew.SHAPE_T_CIRCLE, (cx, cy), (cx + 0.2, cy), 0.1, True)
    for r1, r2, col in pairs:
        (ax, ay), (cx, cy) = at(r1, col), at(r2, col)
        for sg in (-1, 1):
            shape(pcbnew.SHAPE_T_SEGMENT, (ax, ay + sg * R), (cx, cy + sg * R), 0.15)
        for (ex, ey), sg in (((ax, ay), -1), ((cx, cy), 1)):
            q = pcbnew.PCB_SHAPE(b); q.SetShape(pcbnew.SHAPE_T_ARC); q.SetLayer(pcbnew.F_SilkS); q.SetWidth(MM(0.15))
            q.SetArcGeometry(V(ex, ey - R), V(ex + sg * R, ey), V(ex, ey + R)); b.Add(q)
    E = R + 0.3                                          # the block's outline round it all
    shape(pcbnew.SHAPE_T_RECT, (x - pitch - E, y - pitch / 2 - E), (x + pitch + E, y + pitch / 2 + E), 0.15)
    box = (x - pitch - E - 0.1, y - pitch / 2 - E - 0.1, x + pitch + E + 0.1, y + pitch / 2 + E + 0.1)
    if not free(box): raise SystemExit("silk: no room for a jumper picture at (%.1f, %.1f)" % (x, y))
    blocks.append((box[0] - 0.1, box[1] - 0.1, box[2] + 0.1, box[3] + 0.1))
for x_, r_, what in ((135.4, 0, "PIN 2=TX\nPIN 3=RX"), (140.15, 1, "PIN 2=RX\nPIN 3=TX")):
    shunts(x_, _y6 + 2.3, [(r_, r_ + 1, 0), (r_, r_ + 1, 1)])
    place([(what, 1.0), (what, 0.9), (what, 0.8)], [(x_ + dx, _y6 + 4.4 + dy) for dy in (0.0, 0.2, 0.4) for dx in (0.0, 0.1, -0.1)], just="left")
place([("JP7 UART INT\nFIT = -INT", 1.0), ("JP7 UART INT\nFIT = -INT", 0.8)],
      [(105.6 + dx, 105.5 + dy) for dx in (0.0, 0.2, 0.4, 0.6, 0.8) for dy in (0.0, -0.4, -0.8, -1.2, -1.6)])
place([("JP6 TX/RX", 1.0), ("JP6 TX/RX", 0.8)], [(141.9 + dx, 29.2 + dy) for dx in (0.0, -0.2, 0.2, 0.4, 0.6) for dy in (0.0, -0.3, 0.3, 0.6)])
# what is left of the block of 2026-11-23 ("can you add more detail to silkscreen for IO card settings for serial
# port") once each jumper's line stands at its jumper: how a program reaches a UART register, and the divisor for 9600
# baud with the 1.8432 MHz can, in the free patch under RN3, between the UART and the toggles, at 1.0 mm (0.8 until then)
SERIAL_NOTE = ("SERIAL PORT (16C550)\n"
               "REG N: OUT 6 = 80+N,\n"
               "THEN PORT 7 (JP4: 6+7)\n"
               "DIVISOR 12 = 9600 BAUD")
place([(SERIAL_NOTE, 1.0), (SERIAL_NOTE, 0.8)],
      [(142.5 + dx, 82.6 + dy) for dy in (0.0, 0.3, 0.6, 0.9, 1.2, 1.5) for dx in (0.0, 0.3, -0.3, 0.6, -0.6)], just="left")
label("J2", "J2 %s" % N.PARTS["J2"][1], "J2\n%s" % N.PARTS["J2"][1])
# the front panel's header (2026-11-22): its first and last pins numbered at their ends, and its name beside it. The
# numbers go first and must find room (2026-11-23): placed after the name they were optional, and when the RESET
# button took the name's corner the name went to the pin 1 end and the "1" was left out without a word (the pcb-check
# session found it, comparing the two boards' texts)
for n, dy in (("1", -1), ("50", 1)):
    x, y = pad("J3", n); l, t, rr, bt = bbox("J3")
    place([(n, 0.8)], [(x, (t if dy < 0 else bt) + dy * d) for d in (1.0, 1.2, 1.4, 1.6)])
label("J3", "J3 %s" % N.PARTS["J3"][1], "J3\n%s" % N.PARTS["J3"][1])
label("X1", "X1 %s" % N.PARTS["X1"][1], "X1\n%s" % N.PARTS["X1"][1])
for ref in sorted([r for r in N.PARTS if r.startswith("U") and r not in ("U7", "U8", "U14", "U15", "U16", "U17")],
                  key=lambda r: int(r[1:])):
    label(ref, "%s %s" % (ref, N.PARTS[ref][1]), "%s\n%s" % (ref, N.PARTS[ref][1]))
# BT1 first: a "+" on the silkscreen at the holder's positive end, outside the holder, where it shows with the holder
# fitted and the cell in (Ken, 2026-11-19, asked by the pcb-check session: "Yes, both", this card and the YACC1 I/O card
# V1.2; the footprint's own "+" is on the fab layer, under the cell). It stands level with pad 1 (VBAT) in the 2 mm
# between JP4's end and the holder, and the holder's label follows it on the same line: "+ BT1 CR2032" under the
# holder's + end, with the card standing. (The label stood there alone until then, centred on the pad.)
_l = bbox("BT1")[0]; _px, _py = pad("BT1", "1")
_xs = [_l - d for d in (0.9, 1.0, 0.8, 1.1)]
_plus = place([("+", 1.0)], [(x, _py + dy) for x in _xs for dy in (0.0, 0.2, -0.2)])
place([("BT1 %s" % N.PARTS["BT1"][1], 1.0), ("BT1 %s" % N.PARTS["BT1"][1], 0.8)],
      [(_plus[0], _plus[1] + d) for d in [5.6 + 0.1 * k for k in range(12)]])
for ref in sorted([r for r in N.PARTS if r[0] in "RCYBD" and r not in ("R2", "R3", "C9", "C10", "Y1", "BT1")]):
    v = N.PARTS[ref][1].replace("32.768kHz", "32.768kHz")
    label(ref, "%s %s" % (ref, v), "%s\n%s" % (ref, v))
for ref, title in JP_TITLES:
    label(ref, title, {"JP4": "JP4 RTC\n+ UART"}.get(ref, title.replace(" ", "\n", 1)))

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
# CPU Rev D's (pcb-check wants power on planes or on tracks of 0.5 mm or more; GND has its pours)
pf = os.path.join(DEST, PROJ + ".kicad_pro"); pj = json.load(open(pf))
c = pj["net_settings"]["classes"][0]
pw = dict(c); pw.update(name="Power", track_width=0.5, priority=0)
pj["net_settings"]["classes"] = [c, pw]
pj["net_settings"]["netclass_patterns"] = [{"netclass": "Power", "pattern": "+5V"}]
json.dump(pj, open(pf, "w"), indent=2)
print("board: %d footprints, %d nets" % (len(b.GetFootprints()), len(nets)))
