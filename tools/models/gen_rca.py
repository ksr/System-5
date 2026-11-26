#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother, 2026
"""The 3D model of the RCA jack (composite video) for the boards' pictures, which KiCad's library has not got either (Ken,
2026-11-24). Needs only Python; the STEP writer is gen_minidin6.py's:

    python3 tools/models/gen_rca.py             writes RCA.step beside this script

For the "RCA" footprint of System-5's, YACC1's and the ELF II's video cards (Eagle's; pads S1, C1, S3 in a row, S2 under the
bracket's plate). Its origin is pad S1, the barrel towards +x. From the footprint: the pads, the plate and arms (10.16 wide,
5.08 in front of the row), the barrel's 7.62 mm and its 11.43 mm end. The rest (heights, the centre contact's shape) is by
eye from the photo of the built Rev B card, hardware/video-6845/eagle/rev-b/photos in elf. A picture, not a part to measure.
"""
import os
from gen_minidin6 import Step, TIN, circle

HERE = os.path.dirname(os.path.abspath(__file__))
WHITE = (0.85, 0.83, 0.78)
MID, CZ = -5.08, 5.4                                    # the centre line's y (y up), the barrel's height


def main():
    s = Step("RCA")
    plate = [(MID - 5.08, 0.0), (MID + 5.08, 0.0), (MID + 5.08, 8.6), (MID + 3.2, 10.6), (MID - 3.2, 10.6), (MID - 5.08, 8.6)]
    s.solid(plate, [], "x", 4.7, 5.2, TIN)                                              # the bracket's front plate
    for y0, y1 in ((-0.25, 0.25), (-10.41, -9.91)):                                     # its arms, down to S1 and S3
        s.box(-0.6, 4.7, y0, y1, 0.0, 4.6, TIN)
        s.box(-0.6, 0.6, y0, y1, -3.0, 0.0, TIN)
    s.box(4.7, 5.2, MID - 0.6, MID + 0.6, -3.0, 0.0, TIN)                               # its foot in S2
    s.solid(circle(MID, CZ, 4.6), [circle(MID, CZ, 3.4)], "x", 5.2, 5.9, TIN)           # the flange, the barrel
    s.solid(circle(MID, CZ, 3.81), [circle(MID, CZ, 3.4)], "x", 5.9, 11.43, TIN)
    s.solid(circle(MID, CZ, 3.4), [circle(MID, CZ, 1.6, 20)], "x", 5.2, 9.5, WHITE)     # the insulator
    s.solid(circle(MID, CZ, 1.6, 20), [circle(MID, CZ, 1.2, 20)], "x", 5.2, 9.5, TIN)   # the centre contact
    s.solid(circle(MID, CZ, 2.4, 20), [], "x", 3.6, 4.7, WHITE)                         # behind the plate, and its tail to C1
    s.box(-0.3, 3.6, MID - 0.8, MID + 0.8, CZ - 0.3, CZ + 0.3, TIN)
    s.box(-0.3, 0.3, MID - 0.8, MID + 0.8, -3.0, CZ - 0.3, TIN)
    s.write(os.path.join(HERE, "RCA.step"))


if __name__ == "__main__":
    main()
