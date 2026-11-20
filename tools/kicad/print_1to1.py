#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-18
"""print_1to1.py BOARD.kicad_pcb [OUT.pdf] - the board at full size (1:1) on one sheet, to print and lay real parts on
(Ken, 2026-11-18: "how can i print bus board 1:1 so i can measure things like switch"). Run with KiCad's Python:

    /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 \\
        tools/kicad/print_1to1.py hardware/bus/kicad/rev-d/s5bus-d.kicad_pcb

Writes BOARD-1to1.pdf beside the board (or OUT.pdf): the outline, every pad with its hole at its real size, the parts'
outlines and labels (silkscreen and fab), no tracks and no copper pours, the board in the middle of a US Letter sheet
(Tabloid for a board that does not fit; upright for a tall board), and under it a 100 mm line with a tick every 10 mm.

Print it at 100 % ("Actual size" / Scale 100 %, never "Scale to fit"), then measure the 100 mm line with a ruler: if it
is 100 mm, the print is 1:1 and a part laid on its pads shows whether it fits.
The board file is not touched: the print is made from a copy.
"""
import glob, os, re, subprocess, sys
import pcbnew
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import kicad_route
CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
MM, T = pcbnew.FromMM, pcbnew.ToMM
SHEETS = (("USLetter", 279.4, 215.9), ("USLedger", 431.8, 279.4))          # KiCad's names, lying (landscape)
MARGIN, RULER = 10.0, 22.0                                                 # the printer's edge; room for the 100 mm line


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    brd = os.path.abspath(sys.argv[1]); d = os.path.dirname(brd); name = os.path.basename(brd)[:-len(".kicad_pcb")]
    out = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else os.path.join(d, name + "-1to1.pdf")
    tmp = os.path.join(d, "_1to1_tmp.kicad_pcb")
    # a copy without tracks, vias and zones (taken out of the file's text: pcbnew loses its place when items are removed)
    forms = kicad_route.top_forms(open(brd).read())
    keep = [f for f in forms if not f.startswith(("(segment", "(via", "(arc", "(zone"))]
    open(tmp, "w").write("(kicad_pcb\n\t" + "\n\t".join(keep) + "\n)\n")
    try:
        b = pcbnew.LoadBoard(tmp)
        bb = b.GetBoardEdgesBoundingBox(); w, h = T(bb.GetWidth()), T(bb.GetHeight())
        paper = None
        for pname, pw, ph in SHEETS:                    # lying first, then upright
            for upright in (False, True):
                sw, sh = (ph, pw) if upright else (pw, ph)
                if w <= sw - 2 * MARGIN and h + RULER <= sh - 2 * MARGIN:
                    paper = (pname + (" portrait" if upright else ""), sw, sh); break
            if paper:
                break
        if not paper:
            sys.exit("print_1to1: the board (%.1f x %.1f mm) does not fit a Tabloid sheet" % (w, h))
        pname, sw, sh = paper
        c = bb.GetCenter()
        shift = pcbnew.VECTOR2I(MM(sw / 2) - c.x, MM((sh - RULER) / 2) - c.y)
        for it in list(b.GetFootprints()) + list(b.GetDrawings()):
            it.Move(shift)
        # the 100 mm line, under the board: a tick every 10 mm, a longer one at each end and in the middle
        x0, y0 = sw / 2 - 50.0, (sh - RULER) / 2 + h / 2 + 9.0
        def line(x1, y1, x2, y2, wd=0.15):
            s = pcbnew.PCB_SHAPE(b); s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetLayer(pcbnew.F_Fab)
            s.SetStart(pcbnew.VECTOR2I(MM(x1), MM(y1))); s.SetEnd(pcbnew.VECTOR2I(MM(x2), MM(y2))); s.SetWidth(MM(wd)); b.Add(s)
        def text(s, x, y, hgt=2.0):
            t = pcbnew.PCB_TEXT(b); t.SetText(s); t.SetLayer(pcbnew.F_Fab); t.SetTextSize(pcbnew.VECTOR2I(MM(hgt), MM(hgt)))
            t.SetTextThickness(MM(0.15 * hgt)); t.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y))); b.Add(t)
        line(x0, y0, x0 + 100.0, y0)
        for k in range(11):
            line(x0 + 10.0 * k, y0, x0 + 10.0 * k, y0 - (3.0 if k in (0, 5, 10) else 1.5))
        text("0", x0, y0 - 4.6, 1.6); text("50", x0 + 50.0, y0 - 4.6, 1.6); text("100 mm", x0 + 100.0, y0 - 4.6, 1.6)
        text("%s at 1:1 (%.1f x %.1f mm). Print at 100 %%, not 'scale to fit': this line must measure 100 mm." % (name, w, h),
             sw / 2, y0 + 3.6, 2.0)
        pcbnew.SaveBoard(tmp, b)
        t = open(tmp).read()
        form = '(paper "%s" portrait)' % pname.split()[0] if "portrait" in pname else '(paper "%s")' % pname
        t = re.sub(r'\(paper "[^"]*"( portrait)?\)', form, t, count=1)
        open(tmp, "w").write(t)
        r = subprocess.run([CLI, "pcb", "export", "pdf", "--layers", "F.Cu,F.Silkscreen,F.Fab,Edge.Cuts", "--black-and-white",
                            "--drill-shape-opt", "2", "--mode-single", "-o", out, tmp], capture_output=True, text=True)
        if r.returncode or not os.path.exists(out):
            sys.exit("print_1to1: kicad-cli failed: " + (r.stderr or r.stdout)[-400:])
    finally:
        for f in glob.glob(os.path.join(d, "_1to1_tmp.*")):
            os.remove(f)
    print("print_1to1: %s, %.1f x %.1f mm board on %s (%.1f x %.1f mm); print at 100 %% and measure the 100 mm line" % (
        os.path.relpath(out), w, h, pname, sw, sh))
    sys.stdout.flush(); os._exit(0)


if __name__ == "__main__":
    main()
