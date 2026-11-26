#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother, 2026
"""The other 3D models for the boards' pictures that KiCad's library has not got, or names but does not hold (Ken,
2026-11-24). Needs only Python; the STEP writer is gen_minidin6.py's:

    python3 tools/models/gen_parts.py           writes the .step files beside this script

  TIL311.step             TI's hexadecimal display (footprint HTIL311A), showing 8; the dot layout is P32W's
                          (generators/gen_footprints.py there, from SODS001D); origin pad 1, the character upright
  PTC_MF-RHT050.step, PTC_MF-RG500.step   Bourns resettable fuses; body width and thickness from the footprint; origin pad 1
  Trimmer_3386.step       the 3/8 inch square trimmer with its pins in line; origin pad 1
  TSR_3-2450N.step        TRACO's three-pin regulator; the outline from its footprint; origin pad 1
  Arduino_Nano.step       the module on its pins; the outline from its footprint; origin pad 1, the USB socket towards +y
  PinHeader_3x08.step     three rows of eight pins (YACC1's PIN_3X8); origin pad 1
  CP_D6.3_P5.08.step      an electrolytic 6.3 mm across on 5.08 mm pins (E5-6); origin its + pad

What is not named above (heights, colours, the Nano's parts) is for the look only. Pictures, not parts to measure.
"""
import math, os
from gen_minidin6 import Step, TIN, BLACK, circle

HERE = os.path.dirname(os.path.abspath(__file__))
GOLD = (0.86, 0.70, 0.30)


def out(s):
    s.write(os.path.join(HERE, s.name + ".step"))


def til311():
    s = Step("TIL311")
    s.box(3.81 - 5.08, 3.81 + 5.08, -7.62 - 9.4, -7.62 + 9.4, 0.5, 3.7, (0.36, 0.03, 0.04))
    rows = (".XX.", "X..X", "X..X", ".XX.", "X..X", "X..X", ".XX.")
    for r in range(7):
        lean = (3 - r) * 6.90 / 6 * math.tan(math.radians(5.0))
        for c in range(4):
            x, y, on = 3.81 + (c - 1.5) * 4.30 / 3 + lean, 1.78 + r * 6.90 / 6, rows[r][c] == "X"
            w = 0.36 if on else 0.30
            s.box(x - w, x + w, -y - w, -y + w, 3.7, 3.76 if on else 3.73, (1.0, 0.18, 0.10) if on else (0.24, 0.02, 0.03))
    for x in (3.81 - 4.1, 3.81 + 4.1):
        s.box(x - 0.3, x + 0.3, -9.36, -8.76, 3.7, 3.73, (0.24, 0.02, 0.03))
    for n in range(1, 15):
        if n not in (6, 9, 11):
            x, y = (0.0, -(n - 1) * 2.54) if n <= 7 else (7.62, -(14 - n) * 2.54)
            s.box(x - 0.25, x + 0.25, y - 0.25, y + 0.25, -3.0, 0.5, TIN)
    out(s)


def ptc(name, width, height):
    """a flat block standing across its two pins, which are 5.1 mm apart along it and 1.2 mm across"""
    s = Step(name)
    r, w = 1.5, width / 2
    prof = [(-w, 0.8), (w, 0.8)]
    for cx, cz, a0 in ((w - r, 0.8 + height - r, 0), (-w + r, 0.8 + height - r, 90)):
        prof += [(cx + r * math.cos(math.radians(a0 + a)), cz + r * math.sin(math.radians(a0 + a))) for a in range(0, 91, 15)]
    s.solid([(y - 2.55, z) for y, z in prof], [], "x", -0.6 - 1.5, -0.6 + 1.5, (0.85, 0.68, 0.10))
    for x, y in ((0.0, 0.0), (-1.2, -5.1)):
        s.solid([(p + x, q + y) for p, q in circle(0, 0, 0.3, 12)], [], "z", -3.0, 0.8, TIN)
    out(s)


def trimmer():
    s = Step("Trimmer_3386")
    cx, cy, h = 2.54, 2.8575, 4.76
    s.box(cx - h, cx + h, cy - h, cy + h, 0.4, 5.2, (0.08, 0.25, 0.62))
    s.solid(circle(cx, cy, 3.1), [], "z", 5.2, 5.45, (0.05, 0.16, 0.45))
    s.box(cx - 2.3, cx + 2.3, cy - 0.35, cy + 0.35, 5.45, 5.5, BLACK)
    for x in (0.0, 2.54, 5.08):
        s.box(x - 0.25, x + 0.25, -0.25, 0.25, -3.0, 0.4, TIN)
    out(s)


def tsr():
    s = Step("TSR_3-2450N")
    s.box(-6.66, 1.94, -10.04, 4.96, 0.3, 10.5, BLACK)
    for y in (0.0, -2.54, -5.08):
        s.box(-0.35, 0.35, y - 0.3, y + 0.3, -3.5, 0.3, TIN)
    out(s)


def nano():
    s = Step("Arduino_Nano")
    for x in (0.0, 15.24):
        s.box(x - 1.27, x + 1.27, -36.83, 1.27, 0.0, 2.5, BLACK)
        for n in range(15):
            s.box(x - 0.3, x + 0.3, -n * 2.54 - 0.3, -n * 2.54 + 0.3, -3.0, 0.0, GOLD)
            s.box(x - 0.6, x + 0.6, -n * 2.54 - 0.6, -n * 2.54 + 0.6, 4.1, 4.5, TIN)
    s.box(-1.27, 16.51, -39.37, 3.81, 2.5, 4.1, (0.05, 0.22, 0.40))
    s.box(3.81, 11.43, -41.91, -32.6, 4.1, 8.0, TIN)                                     # the USB socket
    s.box(4.4, 10.8, -41.95, -41.5, 4.9, 7.2, BLACK)
    chip = [(7.62 + x, -13.5 + y) for x, y in ((0, -5.0), (5.0, 0), (0, 5.0), (-5.0, 0))]
    s.solid(chip, [], "z", 4.1, 5.2, BLACK)                                              # the ATmega328P, set at 45 degrees
    s.box(6.0, 9.2, -23.8, -21.4, 4.1, 5.8, TIN)                                         # the reset button
    s.solid(circle(7.62, -22.6, 0.8, 16), [], "z", 5.8, 6.4, (0.9, 0.9, 0.88))
    for x in (4.2, 6.5, 8.8, 11.1):
        s.box(x - 0.7, x + 0.7, -27.6, -26.8, 4.1, 4.8, (0.9, 0.85, 0.7))                # the four LEDs
    for x in (5.08, 7.62, 10.16):
        for y in (0.4, 2.94):
            s.box(x - 0.32, x + 0.32, y - 0.32, y + 0.32, 4.1, 12.5, GOLD)               # the ICSP pins
    s.box(3.81, 11.43, -0.87, 4.21 - 0.4, 4.1, 6.6, BLACK)
    out(s)


def header_3x8():
    s = Step("PinHeader_3x08")
    s.box(-1.27, 19.05, -6.35, 1.27, 0.0, 2.54, BLACK)
    for r in range(3):
        for c in range(8):
            s.box(c * 2.54 - 0.32, c * 2.54 + 0.32, -r * 2.54 - 0.32, -r * 2.54 + 0.32, 2.54, 8.5, GOLD)
            s.box(c * 2.54 - 0.32, c * 2.54 + 0.32, -r * 2.54 - 0.32, -r * 2.54 + 0.32, -3.0, 0.0, GOLD)
    out(s)


def electrolytic():
    s = Step("CP_D6.3_P5.08")
    s.solid(circle(2.54, 0, 3.15), [], "z", 0.2, 11.0, (0.10, 0.30, 0.75))
    s.solid(circle(2.54, 0, 2.6), [], "z", 11.0, 11.1, TIN)
    s.box(4.9, 5.75, -0.9, 0.9, 0.3, 10.9, (0.75, 0.82, 0.92))                           # the stripe on the - side
    for x in (0.0, 5.08):
        s.solid(circle(x, 0, 0.3, 12), [], "z", -3.0, 0.2, TIN)
    out(s)


if __name__ == "__main__":
    til311()
    ptc("PTC_MF-RHT050", 7.4, 11.0)
    ptc("PTC_MF-RG500", 10.4, 13.0)
    trimmer()
    tsr()
    nano()
    header_3x8()
    electrolytic()
