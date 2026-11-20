#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-18 (the silkscreen of make_board.py, 2026-10-30)
"""silk.py - CPU Rev D's silkscreen, by Ken's rules:
  * every reference outside its part, readable with the parts fitted, with its type or value beside it ("U3 2732 HBIOS",
    "R1 10k"); the LEDs by their function alone (PWR, Q, PAUSE, RESET, ROM; pcb-check.ini exempts their references);
    the switch's positions, the jumpers' settings and the debug header's pins named
  * **every text reads upright with the card standing in the bus, connector down** (Ken, 2026-11-18, every board on
    every system; he asked for it on CPU Rev D that day): the bus is on the left as drawn, so every label is at KiCad
    angle 270, each at the first spot clear of every pad, part, other text, the edge and the card-support strips
    (tools/kicad/silk270.py), under its part with the card standing first. The one exception is the name line, which
    runs along the bottom edge as drawn at angle 0 (up the right-hand side with the card standing), just above the
    bottom strip. Until 2026-11-18 the labels stood at 0
  * D1 keeps its own reference field (J1's pin labels name the data lines D0-D7, and pcb-check reads a part's field
    before any free text with its name)

add(b)              used by make_board.py on a new board
silk.py             refresh: replace the silkscreen texts of the routed board, copper untouched (run with KiCad's Python);
                    J1's drawing (the header's body, its 3D model) is brought up to its library file first
"""
import os, sys
import pcbnew
HERE = os.path.dirname(os.path.abspath(__file__)); DEST = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(DEST, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "kicad")); sys.path.insert(0, HERE)
import silk270
import netlist as N
T = pcbnew.ToMM; MM = pcbnew.FromMM; V = lambda x, y: pcbnew.VECTOR2I(MM(x), MM(y))
PROJ = "cpu-rev-d"


def add(b):
    eb = b.GetBoardEdgesBoundingBox()
    X0, Y0, XR, YB = T(eb.GetLeft()) + 0.05, T(eb.GetTop()) + 0.05, T(eb.GetRight()) - 0.05, T(eb.GetBottom()) - 0.05
    CY = (Y0 + YB) / 2
    s = silk270.Silk(b, stroke=0.18, no_silk=[(X0, Y0, X0 + 76.2, Y0 + 3.81), (X0, YB - 3.81, X0 + 76.2, YB)])
    fp = lambda ref: b.FindFootprintByReference(ref)
    # 1. the bus: J1's pins named in two staggered columns on the board side, and "J1 BUS" beside them. Not in the margin
    #    by the bus edge, where it stood until 2026-11-18: J1 is a right-angle header and its plastic body lies there
    #    (on F.Fab in the C36 footprint since then, so no label goes under it; tools/kicad/silk270.py, bus_label)
    s.pin_names("J1", {p.GetNumber(): N.POS[int(p.GetNumber()) - 1] for p in fp("J1").Pads()})
    s.bus_label("J1", "J1 BUS")
    # 2. the name line, along the bottom edge as drawn just above the support strip (or beyond it), else along the top;
    #    clear of J1's pin names
    s.name_pair("System-5 CPU  Rev D  2026", 1.2, "cottageworker.com", 1.0,      # (no code: Ken, 2026-11-18)
                [(x, YB - 4.95) for x in [24.0 + 1.0 * k for k in range(56)]] +
                [(x, YB - 1.7) for x in [87.0 + 1.0 * k for k in range(30)]] +
                [(x, Y0 + 4.95) for x in [20.0 + 1.0 * k for k in range(60)]])
    # 3. the front panel: the LEDs by function, the switch's two positions, the debug header's pins, the jumpers
    for ref in ("LED1", "LED2", "LED3", "LED4", "LED5"):
        s.label(ref, N.PARTS[ref][1])
    s.ends("SW1", {"1": "RESET", "3": "RUN"}, h=1.2)     # lever up (towards pin 1) joins the common to pin 3, SW_RST
    s.label("SW1", "SW1")
    l, t_, r, bt = s.bbox("J2")                           # the keyed 2x3 DEBUG header: its pins in a legend below it
    s.place([("J2 DEBUG\n2 GND  4 SC0  6 GND\n1 EXT CLK  3 CLOCK  5 SC1", 0.8)],
            [(l - d, (t_ + bt) / 2 + dy) for d in [2.6 + 0.2 * k for k in range(30)] for dy in (0.0, 1.0, -1.0, 2.0, 3.0)],
            nearest=True)
    s.ends("JP1", {"1": "INT", "3": "EXT"})
    s.label("JP1", "JP1 CLK")
    for j, name in enumerate(N.EFLINES):                  # the EF blocks' rows: the bus flag lines, under JP2 standing,
        x, y = [(T(p.GetPosition().x), T(p.GetPosition().y)) for p in fp("JP2").Pads() if p.GetNumber() == str(2 * j + 1)][0]
        xs = (x - 2.4, x - 4.2) if j % 2 == 0 else (x - 4.2, x - 2.4)               # staggered, as J1's
        s.place([(name, 0.8)], [(xx, y) for xx in xs])
    for k in range(4):
        s.label("JP%d" % (k + 2), "JP%d EF%d" % (k + 2, k + 1), "JP%d\nEF%d" % (k + 2, k + 1))
    # 4. D1: its reference field and its type beside it; its cathode mark (the footprint's own "K") at 270
    got = s.place([("D1 BAT85", 1.0), ("D1 BAT85", 0.8)], s.beside("D1"), nearest=True)
    if got:
        x, y, txt, h = got
        for d in list(b.GetDrawings()):                   # the placeholder becomes the field and the type, in its box
            if isinstance(d, pcbnew.PCB_TEXT) and d.GetText() == txt and abs(T(d.GetPosition().x) - x) < 0.01 \
                    and abs(T(d.GetPosition().y) - y) < 0.01:
                bb = d.GetBoundingBox(); b.Remove(d); break
        y0, y1 = T(bb.GetTop()), T(bb.GetBottom())
        fr = fp("D1").Reference()
        fr.SetVisible(True); fr.SetLayer(pcbnew.F_SilkS); fr.SetTextSize(V(h, h)); fr.SetTextThickness(MM(0.18))
        fr.SetKeepUpright(False); fr.SetTextAngleDegrees(270); fr.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
        fr.SetPosition(V(x, y0 + 0.1))
        s.put("BAT85", x, y1 - 0.1, h, just="right")
    for x, y, txt in s.fp_texts.get("D1", []):
        s.place([(txt, 0.8)], [(x, y), (x, y - 0.4), (x - 0.6, y), (x + 0.6, y)], need=False)
    # 5. the chips ("U3 2732 HBIOS"), then the passives ("R1 10k", "C2 0.1uF")
    for ref in sorted([r for r in N.PARTS if r.startswith(("U", "X"))], key=lambda r: (r[0], int(r[1:]))):
        s.label(ref, "%s %s" % (ref, N.PARTS[ref][1]), "%s\n%s" % (ref, N.PARTS[ref][1]))
    for ref in sorted([r for r in N.PARTS if r[0] in "RC"], key=lambda r: (r[:2] if r.startswith("RN") else r[0], int(r.lstrip("RNC")))):
        s.label(ref, "%s %s" % (ref, N.PARTS[ref][1]), "%s\n%s" % (ref, N.PARTS[ref][1]))
    return s


if __name__ == "__main__":
    import kicad_route, fp_update
    pcb = os.path.join(DEST, PROJ + ".kicad_pcb")
    # the bus connector's drawing (the header's body, courtyard and 3D model) from its library file, as a new board gets
    # it: pads, nets and tracks untouched (tools/kicad/fp_update.py)
    text, _ = fp_update.update(open(pcb).read(), "J1", open(os.path.join(DEST, "s5cpu.pretty", "C36.kicad_mod")).read())
    forms = kicad_route.top_forms(text)                      # drop the old texts at the file level (pcbnew Remove()
    keep = [f for f in forms if not (f.startswith("(gr_text") and '(layer "F.SilkS")' in f)]   # breaks iteration)
    open(pcb, "w").write("(kicad_pcb\n\t" + "\n\t".join(keep) + "\n)\n")
    b = pcbnew.LoadBoard(pcb); s = add(b); pcbnew.ZONE_FILLER(b).Fill(b.Zones()); pcbnew.SaveBoard(pcb, b)
    ok = s.report()
    print("silk: %d texts dropped, labels rebuilt at 270%s" % (len(forms) - len(keep), "" if ok else " (SOME MISSED)"))
    sys.stdout.flush(); os._exit(0 if ok else 1)
