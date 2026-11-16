# VIDEO-G TEXT character ROM

`video-g-chargen.bin` is IC12 (AT28C64B) on the VIDEO-G 1.0 TEXT board (`hardware/video-g/`): 128 characters of 8 x 8,
made by `build.py` from System-5's own 6845-card font (`../char-rom-fonts/goodfont`, 5 x 7 glyphs with lower case),
each row shifted one dot right to sit in VIDEO-G's 8-dot cells.

Address = code x 8 + row: A0-A2 = the 6845's RA0-RA2, A3-A9 = the 7-bit character code; bit 7 of a code is reverse
video, done by the card. The first 1K is the font; it repeats 8 times to fill the 8K part.

Burn on the T48: `minipro -p AT28C64B -u -P -w video-g-chargen.bin` (`-u` lifts the software data protection,
`-P` sets it again).

A proper 8 x 8 font (wider glyphs using all 8 dots) can replace it later; the card does not care.
