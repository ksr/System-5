#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-01
"""build.py - the VIDEO-G TEXT character ROM (IC12, AT28C64B) from System-5's own font.

firmware/char-rom-fonts/goodfont is the 6845 card's 2732 font: 128 characters x 8 rows, 5 x 7 glyphs (lower case with
descenders) in data bits 7-3, bit 7 the leftmost dot, row 0 blank. VIDEO-G's cells are 8 dots wide, so each row is
shifted right one dot (bits 6-2): one blank dot left, two right - a 3-dot gap between characters.
The ROM address is code x 8 + row (A0-A2 = the 6845's RA0-RA2, A3-A9 = the 7-bit code; bit 7 of a code = reverse video,
done by the card). A10-A12 are grounded on the board, so only the first 1K is read; the image repeats it 8 times to fill
the 8K part. Burn: minipro -p AT28C64B -u -P -w video-g-chargen.bin
"""
import os, hashlib
HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "..", "char-rom-fonts", "goodfont"), "rb").read()
assert len(src) == 1024
font = bytes(b >> 1 for b in src)
img = font * 8
open(os.path.join(HERE, "video-g-chargen.bin"), "wb").write(img)
print("video-g-chargen.bin: %d bytes, md5 %s" % (len(img), hashlib.md5(img).hexdigest()))
for ch in "Ag8":
    print(ch, " ".join(format(font[ord(ch) * 8 + r], "08b").replace("0", ".").replace("1", "#") for r in range(8)))
