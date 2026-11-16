#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-05
"""Post-routing: every silkscreen text gets a stroke of at least 0.15 mm (JLCPCB's minimum; Eagle's vector-font texts were
thinner), and at least 15% of its height. Run with KiCad's Python on ../memory-rev-d.kicad_pcb."""
import os, sys, pcbnew
brd = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "memory-rev-d.kicad_pcb")
b = pcbnew.LoadBoard(brd); MM = pcbnew.FromMM; n = 0
def fix(t):
    global n
    if t.GetLayer() not in (pcbnew.F_SilkS, pcbnew.B_SilkS): return
    want = max(MM(0.15), int(t.GetTextHeight() * 0.15))
    if t.GetTextThickness() < want: t.SetTextThickness(want); n += 1
for d in b.GetDrawings():
    if isinstance(d, pcbnew.PCB_TEXT): fix(d)
for fp in b.GetFootprints():
    fix(fp.Reference()); fix(fp.Value())
    for g in fp.GraphicalItems():
        if isinstance(g, pcbnew.PCB_TEXT): fix(g)
# footprint values follow the schematic (the Eagle board import carried its own value strings): read them from the netlist
import re as _re
_net = open(os.path.join(os.path.dirname(brd), "reports", "netlist.net")).read()
_val = dict(_re.findall(r'\(comp\s+\(ref "([^"]+)"\)\s+\(value "([^"]*)"\)', _net))
synced = 0
for fp in b.GetFootprints():
    v = _val.get(fp.GetReference())
    if v is not None and fp.GetValue() != v: fp.SetValue(v); synced += 1
print("footprint values synced to the schematic:", synced)
# jumper blocks and LEDs carry their own labels (ROM/GND/RAM rows, 4K addresses, EPROM HI ... PWR): hide the Eagle
# references and header pin numbers that sat on top of the pads and the new labels
hidden = 0
for fp in b.GetFootprints():
    r = fp.GetReference()
    if r.startswith(("SV", "LED")):
        fp.Reference().SetVisible(False); hidden += 1
        if r.startswith("SV"):
            for g in fp.GraphicalItems():
                g = g.Cast()                      # pcbnew hands footprint texts back as BOARD_ITEM
                if hasattr(g, "GetText") and g.GetText().strip().isdigit(): g.SetVisible(False); hidden += 1
    if r == "C5":                                 # its reference sat on the HI block's E000 label: put it right of the cap
        bb = fp.GetBoundingBox(False); fp.Reference().SetPosition(pcbnew.VECTOR2I(bb.GetRight() + MM(1.2), bb.GetCenter().y))
print("references / pin numbers hidden:", hidden)
# resistor, capacitor and resistor-network values on the silkscreen: the reference field is hidden and a footprint text
# "<ref> <value>" takes its place (same position, angle, size). Literal text: a field cannot hold ${REFERENCE} (it is
# the designator itself and expands recursively). Idempotent: an existing "<ref> ..." text is updated, not duplicated.
VALUES = {"C8": "10uF"}
shown = 0
for fp in b.GetFootprints():
    r = fp.GetReference()
    if not (r.startswith(("C", "RN")) or (r.startswith("R") and r[1:].isdigit())): continue
    v = VALUES.get(r, "0.1uF" if r.startswith("C") else ("4.7k" if r.startswith("RN") else fp.GetValue()))
    fp.SetValue(v); fp.Value().SetVisible(False)
    rf = fp.Reference(); label = "%s %s" % (r, v)
    bb = fp.GetBoundingBox(False)
    if r == "R5": rf.SetPosition(pcbnew.VECTOR2I(bb.GetCenter().x, bb.GetTop() - MM(1.0)))      # above: LED5 is below it
    if r == "R4": rf.SetPosition(pcbnew.VECTOR2I(bb.GetCenter().x, bb.GetBottom() + MM(1.0)))   # below: LED4 is above it
    t = None
    for g in fp.GraphicalItems():
        g = g.Cast()
        if isinstance(g, pcbnew.PCB_TEXT) and g.GetText().startswith(r + " "): t = g
    if t is None:
        t = pcbnew.PCB_TEXT(fp); fp.Add(t)
    t.SetText(label); t.SetLayer(rf.GetLayer()); t.SetTextSize(rf.GetTextSize()); t.SetTextThickness(max(rf.GetTextThickness(), MM(0.15)))
    t.SetTextAngle(rf.GetTextAngle()); t.SetPosition(rf.GetPosition()); t.SetHorizJustify(rf.GetHorizJustify()); t.SetVertJustify(rf.GetVertJustify())
    if r in ("R4", "R5"): t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER)   # centred over/under the resistor, clear of the LED labels
    rf.SetVisible(False); shown += 1
print("value labels (R, C, RN):", shown)
pcbnew.SaveBoard(brd, b); print("silk texts thickened:", n)
# the headers' pin-number texts ignore SetVisible in KiCad 10: drop them from the SV footprints at the text level
import re
sys.path.insert(0, os.path.join(os.path.dirname(brd), "..", "..", "..", "..", "tools", "kicad")); import kicad_route
def strip_numbers(fp):
    out, i, dropped = [], 0, 0
    for m in re.finditer(r'\(fp_text user "\d+"', fp):
        if m.start() < i: continue
        d, j = 0, m.start()
        while True:
            d += {"(": 1, ")": -1}.get(fp[j], 0); j += 1
            if d == 0: break
        out.append(fp[i:m.start()]); i = j; dropped += 1
    out.append(fp[i:]); return "".join(out), dropped
text = open(brd).read(); forms = kicad_route.top_forms(text); total = 0
for k, f in enumerate(forms):
    if f.startswith("(footprint") and re.search(r'\(property "Reference" "SV\d"', f):
        forms[k], dn = strip_numbers(f); total += dn
open(brd, "w").write("(kicad_pcb\n\t" + "\n\t".join(forms) + "\n)\n"); print("header pin-number texts dropped:", total); sys.stdout.flush(); os._exit(0)
