#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-20
"""footprints.py - this folder's footprint library (video-6845-rev-b-clean-eagle.pretty) from Rev B's, with every
part drawn: a body on F.Fab and a courtyard, which the 2005 Eagle footprints do not have (they draw a silkscreen
outline only). Without them the label placer and pcb-check take the board under a chip, a socket or the bus header for
free board (the pcb-check BODIES rule of 2026-11-19; hardware/BUILD-RULES.md, section 5). Run with KiCad's Python; it
starts from Rev B's library each run. The pads are untouched: Rev B's copper fits them as it is.

  * the DE-9 (F09HP) is left out: Rev B-Clean has none
  * the seven footprints memory Rev F also has (0207_7, C025-050X050, C30, DIL14, DIL16, E2,5-7, LED5MM: the same Eagle
    library, pad for pad) are Rev F's files, bodies and courtyards already checked there: the bus connector C30 with the
    right-angle header's body between the pads and the card edge and KiCad's 3D model of it
  * the other chips (DIL20, DIL24, DIL40, DIL48): the chip in its socket, 1.33 mm past the end pins and 1.27 mm past the
    rows, as KiCad's DIP sockets and Rev F's
  * the rest (the crystal, the jumper block, the resistor network, the RCA jack): the body is the box of the Eagle
    silkscreen outline, which draws the part
  * a courtyard round the pads, 0.1 mm out, where there is none (Rev B's parts stand closer than true courtyards allow)
"""
import os, re, shutil, sys
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__)); DEST = os.path.dirname(HERE)
SRC = os.path.join(DEST, "..", "rev-b", "video-6845-rev-b-eagle.pretty")
REVF = os.path.join(DEST, "..", "..", "..", "memory", "kicad", "rev-f", "memory-rev-d-eagle.pretty")
LIB = os.path.join(DEST, "video-6845-rev-b-clean-eagle.pretty")
FROM_F = ["0207_7", "C025-050X050", "C30", "DIL14", "DIL16", "E2,5-7", "LED5MM"]
LEFT_OUT = ["F09HP"]
MM, T = pcbnew.FromMM, pcbnew.ToMM
V = lambda x, y: pcbnew.VECTOR2I(MM(x), MM(y))


def pads_of(path):
    return sorted(re.findall(r'\(pad "([^"]*)" (\w+) (\w+)\s*\(at ([-\d. ]+)\)\s*\(size ([-\d. ]+)\)\s*\(drill ([^)]*)\)', open(path).read()))


def rect(f, layer, x0, y0, x1, y1, w):
    s = pcbnew.PCB_SHAPE(f); s.SetShape(pcbnew.SHAPE_T_RECT); s.SetLayer(layer); s.SetWidth(MM(w))
    s.SetStart(V(x0, y0)); s.SetEnd(V(x1, y1)); f.Add(s)


def main():
    shutil.rmtree(LIB, ignore_errors=True); os.makedirs(LIB)
    names = sorted(fn[:-len(".kicad_mod")] for fn in os.listdir(SRC) if fn.endswith(".kicad_mod"))
    for name in names:
        if name in LEFT_OUT:
            continue
        src = os.path.join(SRC, name + ".kicad_mod")
        if name in FROM_F:
            f = os.path.join(REVF, name + ".kicad_mod")
            assert pads_of(f) == pads_of(src), "%s: Rev F's pads are not Rev B's" % name
            shutil.copy(f, os.path.join(LIB, name + ".kicad_mod")); print("%-14s from memory Rev F" % name); continue
        shutil.copy(src, os.path.join(LIB, name + ".kicad_mod"))
        f = pcbnew.FootprintLoad(LIB, name)
        pb = [p.GetBoundingBox() for p in f.Pads()]; pc = [p.GetPosition() for p in f.Pads()]
        px0, py0, px1, py1 = (min(T(b.GetLeft()) for b in pb), min(T(b.GetTop()) for b in pb),
                              max(T(b.GetRight()) for b in pb), max(T(b.GetBottom()) for b in pb))
        fab = [g for g in f.GraphicalItems() if g.GetLayer() == pcbnew.F_Fab and not isinstance(g, pcbnew.PCB_TEXT)
               and g.GetShape() == pcbnew.SHAPE_T_RECT]
        if not fab:
            if name.startswith("DIL"):                   # the chip in its socket
                cx0, cy0, cx1, cy1 = min(T(p.x) for p in pc), min(T(p.y) for p in pc), max(T(p.x) for p in pc), max(T(p.y) for p in pc)
                body = (cx0 - 1.33, cy0 - 1.27, cx1 + 1.33, cy1 + 1.27); how = "the chip in its socket"
            else:                                        # the Eagle outline's box
                sb = [g.GetBoundingBox() for g in f.GraphicalItems() if g.GetLayer() == pcbnew.F_SilkS and not isinstance(g, pcbnew.PCB_TEXT)]
                body = (min(T(b.GetLeft()) for b in sb), min(T(b.GetTop()) for b in sb), max(T(b.GetRight()) for b in sb), max(T(b.GetBottom()) for b in sb))
                how = "its silkscreen outline's box"
            rect(f, pcbnew.F_Fab, body[0], body[1], body[2], body[3], 0.1)
        else:
            how = "had a body"
        if not f.GetCourtyard(pcbnew.F_CrtYd).OutlineCount():
            rect(f, pcbnew.F_CrtYd, px0 - 0.1, py0 - 0.1, px1 + 0.1, py1 + 0.1, 0.05)
        pcbnew.FootprintSave(LIB, f)
        print("%-14s body: %s%s" % (name, how, "" if fab else " (%.2f x %.2f mm)" % (body[2] - body[0], body[3] - body[1])))
    sys.stdout.flush(); os._exit(0)


if __name__ == "__main__":
    main()
