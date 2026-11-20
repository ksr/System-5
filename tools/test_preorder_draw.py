#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-19
"""test_preorder_draw.py - the copper check pictures draw each pad as the shape its aperture is.

    python3 tools/test_preorder_draw.py          (or: python3 -m unittest tools/test_preorder_draw.py)

tools/preorder_check.py's draw() makes the check-*.png a person looks at before an order. Until 2026-11-19 it drew every
pad as a circle of the first number of its aperture: a rounded-rectangle pin 1 was a 0.25 mm speck, the cards' octagonal
bus pads 1 mm dots, and a pad of a shape of its own (KiCad's FreePoly, whose one number is an angle) would have been a
disc 270 mm across. This draws one pad of every kind KiCad writes and measures each in the picture.
"""
import importlib.util, os, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("preorder_check", os.path.join(HERE, "preorder_check.py"))
pc = importlib.util.module_from_spec(spec); spec.loader.exec_module(pc)

PX = 24                                                   # pixels per mm in the test picture
# one pad of each kind on a line, 5 mm apart, and a 0.25 mm track under them
GERBER = """%FSLAX46Y46*%
%MOMM*%
%AMRoundRect*4,1,4,$2,$3,$4,$5,$6,$7,$8,$9,$2,$3,0*1,1,$1+$1,$2,$3*1,1,$1+$1,$4,$5*1,1,$1+$1,$6,$7*1,1,$1+$1,$8,$9*20,1,$1+$1,$2,$3,$4,$5,0*20,1,$1+$1,$4,$5,$6,$7,0*20,1,$1+$1,$6,$7,$8,$9,0*20,1,$1+$1,$8,$9,$2,$3,0*%
%AMOutline8P*4,1,8,$1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$1,$2,$17*%
%AMRotRect*21,1,$1,$2,0,0,$3*%
%AMHorizOval*20,1,$1,$2,$3,$4,$5,0*1,1,$1,$2,$3*1,1,$1,$4,$5*%
%AMFreePoly0*4,1,5,1.500000,-0.500000,1.500000,0.500000,-0.500000,0.500000,-1.500000,-0.500000,-0.500000,-1.200000,1.500000,-0.500000,$1*%
%AMMystery*1,1,$1,0,0*%
%ADD10C,1.600000*%
%ADD11R,1.700000X1.700000*%
%ADD12O,1.200000X2.400000*%
%ADD13RoundRect,0.250000X-0.550000X-0.550000X0.550000X-0.550000X0.550000X0.550000X-0.550000X0.550000X0*%
%ADD14Outline8P,-0.762000X0.315631X-0.315631X0.762000X0.315631X0.762000X0.762000X0.315631X0.762000X-0.315631X0.315631X-0.762000X-0.315631X-0.762000X-0.762000X-0.315631X90.000000*%
%ADD15RotRect,2.400000X1.000000X45.000000*%
%ADD16HorizOval,1.000000X-0.600000X-0.600000X0.600000X0.600000X0*%
%ADD17FreePoly0,270.000000*%
%ADD18Mystery,270.000000*%
%ADD19C,0.250000*%
D10*X5000000Y5000000D03*
D11*X10000000Y5000000D03*
D12*X15000000Y5000000D03*
D13*X20000000Y5000000D03*
D14*X25000000Y5000000D03*
D15*X30000000Y5000000D03*
D16*X35000000Y5000000D03*
D17*X40000000Y5000000D03*
D18*X45000000Y5000000D03*
D19*X5000000Y2000000D02*X45000000Y2000000D01*
M02*
"""
# pad centre x (mm) -> (what, width, height in mm, the colour it must have)
DARK, ORANGE = "dark", "orange"
PADS = {5: ("circle 1.6", 1.6, 1.6, DARK), 10: ("rectangle 1.7 x 1.7", 1.7, 1.7, DARK), 15: ("obround 1.2 x 2.4", 1.2, 2.4, DARK),
        20: ("RoundRect, 1.6 x 1.6 with its 0.25 mm corners", 1.6, 1.6, DARK), 25: ("Outline8P, the bus pad's octagon", 1.524, 1.524, DARK),
        30: ("RotRect 2.4 x 1.0 at 45 degrees", 2.404, 2.404, DARK), 35: ("HorizOval, 1.0 wide between (-0.6, -0.6) and (0.6, 0.6)", 2.2, 2.2, DARK),
        40: ("FreePoly, its corners turned 270 degrees", 1.7, 3.0, DARK), 45: ("a macro not known: a 1 mm orange dot", 1.0, 1.0, ORANGE)}


class Pads(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PIL import Image
        f = os.path.join(tempfile.mkdtemp(), "kinds.png"); pc.draw(GERBER, f, px=PX)
        cls.im = Image.open(f).convert("RGB")

    def box(self, x_mm):
        """the size in mm and the colour of what is drawn within 2.4 mm of a pad's centre, above the track"""
        im = self.im; px = im.load()
        cx = (x_mm - 3.0) * PX; cy = (7.0 - 5.0) * PX       # draw() leaves 2 mm round the 5..45 x 2..5 mm of the test
        xs, ys, cols = [], [], set()
        for x in range(max(0, int(cx - 2.4 * PX)), min(im.width, int(cx + 2.4 * PX))):
            for y in range(max(0, int(cy - 2.4 * PX)), min(im.height, int(cy + 2.4 * PX))):
                r, g, b = px[x, y]
                if (r, g, b) != (255, 255, 255) and not (r > 150 and g < 90 and b < 90):       # not paper, not the red track
                    xs.append(x); ys.append(y); cols.add(ORANGE if r > 200 and 100 < g < 180 and b < 60 else DARK)
        self.assertTrue(xs, "nothing drawn at x = %s mm" % x_mm)
        return (max(xs) - min(xs) + 1) / PX, (max(ys) - min(ys) + 1) / PX, cols

    def test_each_kind_at_its_size(self):
        for x, (what, w, h, colour) in PADS.items():
            with self.subTest(pad=what):
                gw, gh, cols = self.box(x)
                self.assertAlmostEqual(gw, w, delta=0.12, msg="%s: %.2f mm wide in the picture" % (what, gw))
                self.assertAlmostEqual(gh, h, delta=0.12, msg="%s: %.2f mm tall in the picture" % (what, gh))
                self.assertEqual(cols, {colour}, what)

    def test_the_picture_is_the_size_of_the_board(self):
        # 5..45 mm by 2..5 mm of copper and 2 mm round it: a pad drawn far too large would stretch the picture
        self.assertEqual(self.im.size, (int(44 * PX), int(7 * PX)))


if __name__ == "__main__":
    unittest.main()
