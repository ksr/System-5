#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-20
"""footprints.py - this folder's footprint library: Rev B-Clean's (every part drawn with its body and courtyard:
../rev-b-clean/gen/footprints.py), with two more:

  * C36, the 36-pin bus connector, made here from C30: the same thirty pads in the same places with the same numbers
    (1 = +5V ... 30 = GND, the 30-pin card's numbering, where Rev B's copper is) and six more beyond pad 1, 31-36 (the
    slot's positions past +5V: -EF1, -EF2, -EF3, -DMAIN, SC0, -PAUSE); the right-angle header's body, the courtyard and
    KiCad's 3D model lengthened to match. NOT the numbering of the other cards' C36 (which count all 36 from GND):
    this card keeps Rev B's schematic, whose bus symbol numbers the 30-pin way
  * MiniDIN6_MD-60SM, the PS/2 jack: VIDEO-G's (hardware/video-g/kicad/lib/video-g-local.pretty), as it is
Plain Python; starts from Rev B-Clean's library each run."""
import os, re, shutil, uuid

HERE = os.path.dirname(os.path.abspath(__file__)); DEST = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(DEST, "..", "..", "..", ".."))
import sys; sys.path.insert(0, HERE)
import keyboard as K
SRC = os.path.join(DEST, "..", "rev-b-clean", K.OLD + "-eagle.pretty")
VG = os.path.join(ROOT, "hardware", "video-g", "kicad", "lib", "video-g-local.pretty")
LIB = os.path.join(DEST, K.LIB + ".pretty")
U = lambda *k: str(uuid.uuid5(uuid.NAMESPACE_URL, "s5-" + K.NEW + "/fp/" + "/".join(map(str, k))))


def block(t, i):
    d = 0
    for k in range(i, len(t)):
        if t[k] == "(": d += 1
        elif t[k] == ")":
            d -= 1
            if d == 0: return t[i:k + 1]


def main():
    shutil.rmtree(LIB, ignore_errors=True); shutil.copytree(SRC, LIB)
    shutil.copy(os.path.join(VG, "MiniDIN6_MD-60SM.kicad_mod"), LIB)
    s = open(os.path.join(LIB, "C30.kicad_mod")).read()
    pad1 = block(s, s.index('(pad "1"'))
    x1 = float(re.search(r'\(at ([-\d.]+) ', pad1).group(1))
    x2 = float(re.search(r'\(at ([-\d.]+) ', block(s, s.index('(pad "2"'))).group(1))
    assert abs((x2 - x1) - 2.54) < 0.001 and abs(x1 + 36.83) < 0.001, (x1, x2)
    new = ""
    for k in range(1, 7):
        p = re.sub(r'\(pad "1"', '(pad "%d"' % (30 + k), pad1, count=1)
        p = re.sub(r'\(at [-\d.]+ ', '(at %s ' % ("%.2f" % (x1 - 2.54 * k)).rstrip("0").rstrip("."), p, count=1)
        p = re.sub(r'\(uuid "[^"]+"\)', '(uuid "%s")' % U("C36", 30 + k), p)
        new += "\t" + p + "\n"
    far = x1 - 2.54 * 6 - 1.27                         # the body's and courtyard's new end: as far past pad 36 as it was past pad 1
    s = s.replace("(start -38.1 1.5)", "(start %.2f 1.5)" % far, 1).replace("(start -38.1 -0.862)", "(start %.2f -0.862)" % far, 1)
    assert "%.2f 1.5)" % far in s and "%.2f -0.862)" % far in s
    assert s.count("PinHeader_1x30_P2.54mm_Horizontal") == 1
    s = s.replace("PinHeader_1x30_P2.54mm_Horizontal", "PinHeader_1x36_P2.54mm_Horizontal")
    s = re.sub(r'\(footprint "C30"', '(footprint "C36"', s, count=1)
    i = s.index('(pad "1"')
    s = s[:i] + new.lstrip("\t") + "\t" + s[i:]
    open(os.path.join(LIB, "C36.kicad_mod"), "w").write(s)
    os.remove(os.path.join(LIB, "C30.kicad_mod"))
    print("library: Rev B-Clean's %d footprints, C36 for C30 (pads 31-36 at x %.2f to %.2f), and the PS/2 jack"
          % (len(os.listdir(SRC)), x1 - 2.54, x1 - 2.54 * 6))


if __name__ == "__main__":
    main()
