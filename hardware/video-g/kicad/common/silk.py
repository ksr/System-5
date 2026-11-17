#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-02
"""silk.py - the VIDEO-G boards' silkscreen (Ken's rules, 2026-10-24 / 10-31 / 11-02): every reference outside its part
with its type or value beside it ("IC5" over "74HCT138" in the band above each socket, "C5" over "100n" beside each
bypass cap, "R3 1k" to a resistor's right; where place.py gives just the reference, for parts in a narrow strip, the
value goes on a second line), jacks, jumpers and LEDs by what they do (place.LABELS / REFPOS), plus place.TEXTS (the
board name, cottageworker.com). Ken, 2026-11-17: the 2026-11-02 rule (every part's value on the silkscreen) applies to
VIDEO-G.

add(b, N, P)        used by make_board.py on a new board
silk.py BOARD_DIR   refresh: replace the silkscreen texts of the routed board with today's place.py, copper untouched
                    (run with KiCad's Python)
"""
import os, sys, importlib.util
import pcbnew
MM = pcbnew.FromMM; V = lambda x, y: pcbnew.VECTOR2I(MM(x), MM(y)); TO = pcbnew.ToMM


def court(fp):
    """the courtyard, else the part's extent (make_board.py's overlap check)"""
    cy = fp.GetCourtyard(pcbnew.F_CrtYd)
    return cy.BBox() if cy.OutlineCount() else fp.GetBoundingBox(False, False)


def extent(fp):
    """where a label must not go: the pads and every outline the part draws, courtyard, silk and fab. A courtyard alone
    is not enough: the 0.1" bypass cap's 5 x 5 mm silk box (from Eagle) is larger than its courtyard (2026-11-17)"""
    bb = fp.GetBoundingBox(False, False)
    cy = fp.GetCourtyard(pcbnew.F_CrtYd)
    if cy.OutlineCount(): bb.Merge(cy.BBox())
    return bb


def add(b, N, P):
    def silk(txt, x, y, h=1.0, angle=0, just=None):
        t = pcbnew.PCB_TEXT(b); t.SetText(txt); t.SetLayer(pcbnew.F_SilkS); t.SetTextSize(V(h, h))
        t.SetTextThickness(MM(max(0.15, 0.15 * h))); t.SetPosition(V(x, y))
        if angle: t.SetTextAngleDegrees(angle)
        if just == "left": t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
        elif just == "right": t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_RIGHT)
        b.Add(t)
    LABELS = getattr(P, "LABELS", {}); REFPOS = getattr(P, "REFPOS", {})
    for fp in b.GetFootprints():
        ref = fp.GetReference(); fp.Reference().SetVisible(False); fp.Value().SetVisible(False)
        if ref == "J1" and ref not in LABELS: continue          # the bus connector: its pin names are in the footprint
        bb = extent(fp); l, r, t_, btm = TO(bb.GetLeft()), TO(bb.GetRight()), TO(bb.GetTop()), TO(bb.GetBottom())
        spot = REFPOS.get(ref)
        ic = ref.startswith("IC")
        text = ("%s\n%s" % (ref, fp.GetValue())) if ic else ("%s %s" % (ref, fp.GetValue())) if ref[0] in "RCYF" else ref
        if ref in LABELS: text = LABELS[ref]
        if text == "": continue                                  # labelled with its IC (place.py)
        if text == ref and ref[0] in "RCYF" and fp.GetValue():  # a bare reference: the value on a second line
            text = "%s\n%s" % (ref, fp.GetValue())
        if spot:
            silk(text, spot[0], spot[1], spot[2] if len(spot) > 2 else 1.0, spot[3] if len(spot) > 3 else 0,
                 spot[4] if len(spot) > 4 else "left")
        elif ic:                                                 # ICs: two lines in the band above the socket
            silk(text, l + 0.2, t_ - 2.4, 0.9, 0, "left")
        elif ref in getattr(N, "DECOUPLE", {}) and ref not in LABELS:   # bypass caps: "Cn" over "100n" beside the
            silk("%s\n%s" % (ref, fp.GetValue()), r + 1.5, (t_ + btm) / 2, 0.8, 90)   # cap, turned (two lines: the band is low)
        elif ref[0] == "R" and not ref.startswith("RN"):        # resistors: right of the part
            silk(text, r + 0.3, (t_ + btm) / 2, 0.8, 0, "left")
        else:                                                    # others: above the courtyard
            silk(text, l + 0.2, t_ - 0.9, 0.9, 0, "left")
    for txt, x, y, h, ang, just in getattr(P, "TEXTS", []):
        silk(txt, x, y, h, ang, just)


if __name__ == "__main__":
    HERE = os.path.dirname(os.path.abspath(__file__))
    ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
    sys.path.insert(0, os.path.join(ROOT, "tools", "kicad")); sys.path.insert(0, HERE)
    import kicad_route
    board_dir = os.path.abspath(sys.argv[1])
    def load(name):
        spec = importlib.util.spec_from_file_location(name, os.path.join(board_dir, "gen", name + ".py"))
        m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
    N = load("netlist"); P = load("place")
    pcb = os.path.join(board_dir, N.PROJ + ".kicad_pcb")
    forms = kicad_route.top_forms(open(pcb).read())          # drop the old texts at the file level (pcbnew Remove()
    keep = [f for f in forms if not (f.startswith("(gr_text") and '(layer "F.SilkS")' in f)]   # breaks iteration)
    open(pcb, "w").write("(kicad_pcb\n\t" + "\n\t".join(keep) + "\n)\n")
    b = pcbnew.LoadBoard(pcb); add(b, N, P); pcbnew.ZONE_FILLER(b).Fill(b.Zones()); pcbnew.SaveBoard(pcb, b)
    print("silk: %d texts dropped, labels rebuilt from place.py" % (len(forms) - len(keep)))
    sys.stdout.flush(); os._exit(0)
