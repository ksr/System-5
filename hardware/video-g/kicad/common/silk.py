#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-02; every text at 270 since 2026-11-18
"""silk.py - the VIDEO-G boards' silkscreen, by Ken's rules:
  * every reference outside its part, readable with the parts fitted, with its type or value beside it ("IC5 74HCT138",
    "C5 100n", "R3 1k"; 2026-10-24, 10-31, 11-02; for VIDEO-G since 2026-11-17); jacks, jumpers and LEDs by what they do
    (place.LABELS)
  * **every text reads upright with the card standing in the bus, connector down** (2026-11-18, every board on every
    system): the bus is on the left as drawn, so every label is at KiCad angle 270 (tools/kicad/silk270.py places each
    at the first spot clear of every pad, part, other text and the edge, under its part with the card standing first).
    The one exception is the name line (place.NAME), which runs along the bottom edge as drawn, angle 0: up the side
    with the card standing. Until 2026-11-18 the labels stood at 0 and 90 in the band above each socket.
  * the bus connector's pin names (in J1's footprint, at 0) are written again at 270 in two staggered columns; the DE-9's
    pin numbers too

add(b, N, P)        used by make_board.py on a new board
silk.py BOARD_DIR   refresh: replace the silkscreen texts of the routed board with today's place.py, copper untouched
                    (run with KiCad's Python); the drawing of every part from lib/video-g-local (the bus header's
                    body and 3D model, the RCA jack's body) is brought up to its library file first; stops with an
                    error if a label found no room
"""
import os, sys, importlib.util
import pcbnew
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "..", "tools", "kicad"))
import silk270
MM = pcbnew.FromMM; V = lambda x, y: pcbnew.VECTOR2I(MM(x), MM(y)); TO = pcbnew.ToMM


def court(fp):
    """the courtyard, else the part's extent (make_board.py's overlap check)"""
    cy = fp.GetCourtyard(pcbnew.F_CrtYd)
    return cy.BBox() if cy.OutlineCount() else fp.GetBoundingBox(False, False)


def add(b, N, P):
    s = silk270.Silk(b)
    LABELS = getattr(P, "LABELS", {}); SPOTS = getattr(P, "SPOTS", {})
    fps = {f.GetReference(): f for f in b.GetFootprints()}
    # 1. the name line (the rule's exception, at 0 along an edge), placed first: the labels go round it. place.NAME:
    #    (name, height, cottageworker.com, height, spots), or a list of those to try in turn (a narrower layout of the
    #    same words where the first finds no room)
    alts = getattr(P, "NAME", None)
    alts = [] if alts is None else [alts] if isinstance(alts, tuple) else alts
    for k, alt in enumerate(alts):
        miss = len(s.missed)
        if s.name_pair(*alt):
            break
        if k < len(alts) - 1:
            del s.missed[miss:]
    for text, x, y, h, angle, just in getattr(P, "FIXED", []):     # texts already where they belong (upright)
        s.put(text, x, y, h, angle, just)
    # 2. the bus pins' names beside J1's pads, then "J1 BUS"
    names = dict(getattr(P, "J1_NAMES", {}))             # place.J1_NAMES {pad: name} (the 36-pin connector has no texts
    j1 = fps["J1"]                                       # of its own), else the footprint's own pin names (C30)
    for x, y, t in ([] if names else s.fp_texts.get("J1", [])):
        p = min(j1.Pads(), key=lambda p: abs(TO(p.GetPosition().y) - y))
        names[p.GetNumber()] = t
    s.pin_names("J1", names)
    # "J1 BUS": place.SPOTS["J1"], else past either end of the connector in the margin (clear of the card-guide strips),
    # else on the board side of the pin names, the connector's middle first. Never in the margin beside the pads: the
    # connector is a right-angle header, and its plastic body lies there (drawn on F.Fab in the C30 / C36 footprints
    # since 2026-11-18, so the placer keeps every label off it; until then "J1 BUS" was printed under the header)
    s.bus_label("J1", "J1 BUS", spots=SPOTS.get("J1"))    # tools/kicad/silk270.py: the same on every card
    # 3. other footprints' own texts that belong on the silkscreen (place.FP_TEXTS: the DE-9's pin numbers): where they
    #    were, turned to 270
    for ref in getattr(P, "FP_TEXTS", ()):
        for x, y, t in s.fp_texts.get(ref, []):
            s.place([(t, 0.8)], [(x, y), (x + 0.6, y), (x - 0.6, y), (x, y + 0.8), (x, y - 0.8)], need=False)
    # 4. a jumper's settings at its ends (place.PIN_LABELS {ref: {pin: text}}: "NTSC" beyond pin 1, "5151" beyond
    #    pin 3), each beyond its pin along the header, out from the header's middle
    for ref, labels in getattr(P, "PIN_LABELS", {}).items():
        pads = {p.GetNumber(): (TO(p.GetPosition().x), TO(p.GetPosition().y)) for p in fps[ref].Pads()}
        mx = sum(x for x, _ in pads.values()) / len(pads); my = sum(y for _, y in pads.values()) / len(pads)
        for pin, text in labels.items():
            px, py = pads[pin]; dx, dy = px - mx, py - my; n = (dx * dx + dy * dy) ** 0.5 or 1.0
            ux, uy = dx / n, dy / n                       # out along the header, else beside the pin, either side
            s.place([(text, 0.8)], [(px + ux * d + ox, py + uy * d + oy) for d in (1.8, 2.0, 2.2, 2.5, 2.8, 3.2)
                                    for ox, oy in ((0, 0), (0, 0.6), (0, -0.6), (0.6, 0), (-0.6, 0))]
                    + [(px - uy * d * sd, py + ux * d * sd) for d in (2.2, 2.5, 2.8, 3.2, 3.6) for sd in (-1, 1)], nearest=True)
    # 5. labels: what does a job first (jacks, jumpers, LEDs: their labels are long), then the chips, then the rest
    def kind(ref):
        return 0 if LABELS.get(ref) not in (None, "", ref) else 1 if ref.startswith("IC") else 2
    for ref in sorted((r for r in fps if r != "J1" and not r.startswith("H")), key=lambda r: (kind(r), r[:2], len(r), r)):
        f = fps[ref]; val = f.GetValue()
        lab = LABELS.get(ref)
        if lab and lab != ref:                                # a label by what it does: one line, or (one, two lines)
            text, two = (lab, None) if isinstance(lab, str) else lab
        else:
            text, two = "%s %s" % (ref, val), "%s\n%s" % (ref, val)
        s.label(ref, text, two, spots=SPOTS.get(ref))
    # 6. notes, at 270 too, wherever they fit
    for text, h, spots in getattr(P, "NOTES", []):
        s.place([(text, h), (text, 0.8)], spots)
    return s


if __name__ == "__main__":
    ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
    sys.path.insert(0, os.path.join(ROOT, "tools", "kicad")); sys.path.insert(0, HERE)
    import kicad_route
    board_dir = os.path.abspath(sys.argv[1])
    def load(name):
        spec = importlib.util.spec_from_file_location(name, os.path.join(board_dir, "gen", name + ".py"))
        m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
    N = load("netlist"); P = load("place")
    pcb = os.path.join(board_dir, N.PROJ + ".kicad_pcb")
    # the drawing (body, courtyard, 3D model) of every part whose footprint is in lib/video-g-local, from its library
    # file, as a new board gets it: the bus connector's header body (2026-11-18), the RCA jack's (2026-11-19). Pads, nets
    # and tracks untouched (tools/kicad/fp_update.py)
    import fp_update, symlib
    mods = {ref: open(os.path.join(symlib.LOCAL_FP, part[2].split(":")[1] + ".kicad_mod")).read()
            for ref, part in N.PARTS.items() if part[2].split(":")[0] == symlib.LOCAL_NAME}
    text, n = fp_update.update_all(open(pcb).read(), mods)
    forms = kicad_route.top_forms(text)                      # drop the old texts at the file level (pcbnew Remove()
    keep = [f for f in forms if not (f.startswith("(gr_text") and '(layer "F.SilkS")' in f)]   # breaks iteration)
    open(pcb, "w").write("(kicad_pcb\n\t" + "\n\t".join(keep) + "\n)\n")
    b = pcbnew.LoadBoard(pcb); s = add(b, N, P); pcbnew.ZONE_FILLER(b).Fill(b.Zones()); pcbnew.SaveBoard(pcb, b)
    ok = s.report()
    print("silk: %d texts dropped, labels rebuilt at 270 from place.py%s" % (len(forms) - len(keep), "" if ok else " (SOME MISSED)"))
    sys.stdout.flush(); os._exit(0 if ok else 1)
