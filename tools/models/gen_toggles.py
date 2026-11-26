#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother, 2026
"""The 3D models of the toggle switches for the boards' pictures, which KiCad's library has not got (Ken, 2026-11-24). Needs
only Python; the STEP writer is gen_minidin6.py's:

    python3 tools/models/gen_toggles.py         writes the two .step files beside this script

  Toggle_M9040P.step      Marquardt M9040P, the upright toggle (footprints M9040P and SW_Toggle_M9040P); origin pad 2
  Toggle_9070-1W.step     Marquardt 9070-1W, the small right-angle one (9070-1W, SW_Toggle_SPDT_Marquardt_9070-1W); origin
                          terminal 2, the lever towards -x

From the footprints: the outlines seen from above, the pads, how far the 9070's bushing and lever reach. The heights, the
lever and the colours are by eye from the photos in YACC1-D's media (io v1.1 top, sequencer logic v2.1 top). Which way the
levers lean is arbitrary (towards pad 1). Pictures, not parts to measure.
"""
import os
from gen_minidin6 import Step, TIN, circle

HERE = os.path.dirname(os.path.abspath(__file__))
RED, BRASS = (0.62, 0.06, 0.06), (0.80, 0.74, 0.58)


def m9040p():
    s = Step("Toggle_M9040P")
    half = [(3.3528, 6.6802), (3.9878, 6.0452), (3.9878, 2.5146), (4.318, 2.286)]        # the outline's corner, x and y > 0
    body = [(x, y) for x, y in half[::-1]] + [(-x, y) for x, y in half] + [(-x, -y) for x, y in half[::-1]] + [(x, -y) for x, y in half]
    s.solid(body, [], "z", 0.0, 8.6, RED)
    s.box(-3.6, 3.6, -6.5, 6.5, 8.6, 9.2, TIN)                                           # the metal top plate
    s.solid(circle(0, 0, 3.0), [circle(0, 0, 2.0, 24)], "z", 9.2, 13.4, BRASS)           # the bushing
    s.solid(circle(0, 0, 2.0, 24), [], "z", 9.2, 12.6, TIN)
    lean = 0.24                                                                          # y per mm of height: up = towards pad 1
    s.solid(circle(0, 0.1, 0.95, 20), [], "z", 12.6, 20.6, TIN, (0, lean * 8.0), 1.45)   # the lever, wider at its end
    s.solid(circle(0, 0.1 + lean * 8.0, 0.95 * 1.45, 20), [], "z", 20.6, 21.9, TIN, (0, lean * 1.3), 0.6)
    for y in (4.699, 0.0, -4.699):
        s.box(-0.7, 0.7, y - 0.4, y + 0.4, -3.4, 0.0, TIN)
    s.write(os.path.join(HERE, "Toggle_M9040P.step"))


def t9070():
    s = Step("Toggle_9070-1W")
    s.box(-11.0, -0.635, -4.3, 4.3, 0.3, 6.6, RED)
    s.box(-11.43, -11.0, -4.445, 4.445, 0.0, 6.9, TIN)                                   # the bracket: front, top and legs
    s.box(-11.0, -5.2, -4.445, 4.445, 6.6, 6.9, TIN)
    for y in (-2.54, 2.54):
        s.box(-5.4, -4.76, y - 0.35, y + 0.35, -3.0, 0.3, TIN)
    s.solid(circle(0, 3.5, 2.54), [circle(0, 3.5, 1.6, 24)], "x", -14.6, -11.43, TIN)    # the bushing
    s.solid(circle(0, 3.5, 1.6, 24), [], "x", -13.8, -11.43, TIN)
    s.solid(circle(2.1, 3.5, 1.15, 20), [], "x", -23.4, -13.8, TIN, (-2.0, 0), 0.6)      # the lever, wider at its end
    s.solid(circle(2.28, 3.5, 0.7, 20), [], "x", -24.26, -23.4, TIN, (-0.18, 0), 1.15 / 0.7)
    for y in (-2.54, 0.0, 2.54):
        s.box(-0.635, 0.25, y - 0.3, y + 0.3, 2.6, 3.0, TIN)
        s.box(-0.25, 0.25, y - 0.3, y + 0.3, -3.0, 2.6, TIN)
    s.write(os.path.join(HERE, "Toggle_9070-1W.step"))


if __name__ == "__main__":
    m9040p()
    t9070()
