#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-18 (the silkscreen of make_board.py, that morning)
"""silk.py - the bus driver Rev C's silkscreen, by Ken's rules:
  * every reference outside its part, readable with the parts fitted, with its type or value beside it ("R1 4.7k",
    "U1 MCP23017" with what it carries); the PWR LED by its function alone (pcb-check.ini exempts its reference);
    every pin of J2, J3 and the DEBUG header named
  * **every text reads upright with the card standing in the bus, connector down** (Ken, 2026-11-18, every board on
    every system; "yes convert bus driver silk to 270" that evening): the bus is on the left as drawn, so every label is
    at KiCad angle 270, each at the first spot clear of every pad, part, other text, the edge and the card-support
    strips (tools/kicad/silk270.py, as CPU Rev D's gen/silk.py), under its part with the card standing first. The one
    exception is the name line, "System-5 bus driver  Rev C  2026" with cottageworker.com (one naming for every card,
    Ken, 2026-11-18), at 0 along the bottom edge as drawn: up the right-hand side with the card standing

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
T = pcbnew.ToMM
PROJ = "busdrv-c"
JOB = {"U1": "0x20: D0-D6, A0-A6", "U2": "0x21: D7, A7, CONTROL", "U3": "0x22: -EF1-3, -PAUSE, -DMAIN, SC0"}
PINS = {"J2": ("CLK OUT", "PROBE1", "PROBE2", "SPARE1", "SPARE2", "SPARE3", "SPARE4", "+5V", "GND"),
        "J3": ("SPARE5", "SPARE6", "SPARE7", "SPARE8", "SPARE9", "SPARE10", "SPARE11", "GND")}


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
    s.name_pair("System-5 bus driver  Rev C  2026", 1.2, "cottageworker.com", 1.0,
                [(x, YB - 4.95) for x in [24.0 + 1.0 * k for k in range(56)]] +
                [(x, YB - 1.7) for x in [87.0 + 1.0 * k for k in range(30)]] +
                [(x, Y0 + 4.95) for x in [24.0 + 1.0 * k for k in range(56)]] +
                [(x, Y0 + 1.7) for x in [87.0 + 1.0 * k for k in range(30)]])
    # 3. the front edge: the PWR LED by its function, J2's and J3's pins (three staggered columns: their names are up to
    #    seven letters), their titles, the DEBUG header's pins in a legend under it (odd pin, even pin: as CPU Rev D's J2)
    s.label("LED1", N.PARTS["LED1"][1])
    for ref, names in PINS.items():
        s.pin_names(ref, {str(n + 1): name for n, name in enumerate(names)}, side="left", cols=(2.4, 4.2, 6.0))
        s.label(ref, "%s %s" % (ref, N.PARTS[ref][1]), "%s\n%s" % (ref, N.PARTS[ref][1]))
    l, t_, r, bt = s.bbox("J4")
    s.place([("J4 DEBUG (CPU J2)\n2 GND  4 SC0  6 GND\n1 CLK OUT  3 CLOCK  5 SC1", 0.8)],
            [(l - d, (t_ + bt) / 2 + dy) for d in [2.6 + 0.2 * k for k in range(30)] for dy in (0.0, 1.0, -1.0, 2.0, 3.0)],
            nearest=True)
    # 4. the expanders with what each carries, the Nano, then the passives ("R1 4.7k", "C1 0.1uF")
    for ref, job in JOB.items():
        s.label(ref, "%s MCP23017 %s" % (ref, job), "%s MCP23017\n%s" % (ref, job))
    s.label("U4", "U4 ARDUINO NANO (USB)", "U4 ARDUINO NANO\n(USB)")
    for ref in sorted([r for r in N.PARTS if r[0] in "RC"], key=lambda r: (r[0], int(r[1:]))):
        s.label(ref, "%s %s" % (ref, N.PARTS[ref][1]), "%s\n%s" % (ref, N.PARTS[ref][1]))
    return s


if __name__ == "__main__":
    import kicad_route, fp_update
    pcb = os.path.join(DEST, PROJ + ".kicad_pcb")
    # the bus connector's drawing (the header's body, courtyard and 3D model) from its library file, as a new board gets
    # it: pads, nets and tracks untouched (tools/kicad/fp_update.py)
    text, _ = fp_update.update(open(pcb).read(), "J1", open(os.path.join(DEST, "s5bd.pretty", "C36.kicad_mod")).read())
    forms = kicad_route.top_forms(text)                      # drop the old texts at the file level (pcbnew Remove()
    keep = [f for f in forms if not (f.startswith("(gr_text") and '(layer "F.SilkS")' in f)]   # breaks iteration)
    open(pcb, "w").write("(kicad_pcb\n\t" + "\n\t".join(keep) + "\n)\n")
    b = pcbnew.LoadBoard(pcb); s = add(b); pcbnew.ZONE_FILLER(b).Fill(b.Zones()); pcbnew.SaveBoard(pcb, b)
    ok = s.report()
    print("silk: %d texts dropped, labels rebuilt at 270%s" % (len(forms) - len(keep), "" if ok else " (SOME MISSED)"))
    sys.stdout.flush(); os._exit(0 if ok else 1)
