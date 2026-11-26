#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother, 2026
"""Render a board with the parts KiCad has no model of fitted: its PS/2 sockets (Ken, 2026-11-23: every new render of any
board shows them), and since 2026-11-24 its RCA video jack, toggle switches, TIL311 displays, fuses and the rest of SOCKETS
below. kicad-cli draws a temporary copy of the board in which those footprints have the models beside this file. The board
file is only read. A board without them is drawn as it is. The same file in elf and YACC1-D (tools/models); P32W's
(generators/models) has the PS/2 sockets and fuses only, p8x's the PS/2 sockets. Plain Python, also under KiCad's own.

    python3 fit_ps2.py BOARD.kicad_pcb [kicad-cli pcb render arguments]     e.g. --side top -o top.png
    from a build:  with fit_ps2.fitted(board) as copy: ... kicad-cli pcb render ... copy
                   fit_ps2.fit_file(copy)                                   a copy already made, fitted in place
"""
import contextlib, math, os, re, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"

# footprint -> (model, two pads, the way from the first to the second in the model, y down as on a board); the model's
# origin is the first pad
SOCKETS = {
    "MiniDIN6_MD-60SM": ("MiniDIN6_MD-60SM.step", "1", "2", (0, 2.6)),                             # elf, YACC1-D, ELFII-VIDEO
    "MiniDIN-6_Female_Horizontal_SameSky_MD-60SM": ("MiniDIN6_MD-60SM.step", "1", "2", (0, 2.6)),  # P32W
    "MiniDIN6_RA_PS2": ("MiniDIN6_RA_PS2-body.step", "1", "2", (0, -2.6)),                         # P8X
    "HTIL311A": ("TIL311.step", "1", "14", (7.62, 0)),
    "Fuse_Bourns_MF-RHT050": ("PTC_MF-RHT050.step", "1", "2", (-1.2, 5.1)),
    "Fuse_Bourns_MF-RG500": ("PTC_MF-RG500.step", "1", "2", (-1.2, 5.1)),
    "Potentiometer_Trim_3386_Inline": ("Trimmer_3386.step", "1", "2", (2.54, 0)),
    "Converter_DCDC_TRACO_TSR2-24xxN_TSR2-24xxxN_THT": ("TSR_3-2450N.step", "1", "2", (0, 2.54)),
    "Arduino_Nano": ("Arduino_Nano.step", "1", "2", (0, 2.54)),
    "PIN_3X8": ("PinHeader_3x08.step", "1", "2", (2.54, 0)),
    "E5-6": ("CP_D6.3_P5.08.step", "+", "-", (5.08, 0)),
    "M9040P": ("Toggle_M9040P.step", "2", "3", (0, 4.699)),                                        # the toggles
    "SW_Toggle_M9040P": ("Toggle_M9040P.step", "2", "3", (0, 4.699)),
    "9070-1W": ("Toggle_9070-1W.step", "2", "1", (0, 2.54)),
    "SW_Toggle_SPDT_Marquardt_9070-1W": ("Toggle_9070-1W.step", "2", "1", (0, 2.54)),
    "RCA": ("RCA.step", "S1", "S3", (0, 10.16)),                                                   # the video jack
}


# footprints that name a model KiCad does not hold: ours is added
NAMED_ONLY = {"Fuse_Bourns_MF-RHT050", "Fuse_Bourns_MF-RG500", "Converter_DCDC_TRACO_TSR2-24xxN_TSR2-24xxxN_THT",
              "Arduino_Nano"}


def _end(text, i):
    """the end of the bracketed block that starts at text[i]"""
    depth = 0
    while True:
        c = text[i]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return i + 1
        elif c == '"':
            i += 1
            while text[i] != '"':
                i += 2 if text[i] == "\\" else 1
        i += 1


def fit(text):
    """(the board's text with a model in each socket, jack and toggle that has none, how many)"""
    out, last, n = [], 0, 0
    for m in re.finditer(r'\(footprint\s+"(?:[^":]*:)?([^"]*)"', text):
        if m.group(1) not in SOCKETS:
            continue
        end = _end(text, m.start())
        block = text[m.start():end]
        model, pa, pb, way = SOCKETS[m.group(1)]
        pads = {p: (float(x), float(y)) for p, x, y in
                re.findall(r'\(pad\s+"([^"]*)"[^(]*\(at\s+([-\d.]+)\s+([-\d.]+)', block)}
        if ("(model" in block and m.group(1) not in NAMED_ONLY) or pa not in pads or pb not in pads:
            continue
        (ax, ay), (bx, by) = pads[pa], pads[pb]
        turn = math.degrees(math.atan2(-(by - ay), bx - ax) - math.atan2(-way[1], way[0]))
        out += [text[last:end - 1], '(model "%s" (offset (xyz %.4f %.4f 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 %d)))\n'
                % (os.path.join(HERE, model), ax, -ay, -int(round(turn / 90.0)) * 90 % 360)]   # KiCad turns them clockwise
        last, n = end - 1, n + 1
    return "".join(out + [text[last:]]), n


def fit_file(path):
    """fit a copy of a board in place (never the board itself)"""
    with open(path, encoding="utf-8") as f:
        text, n = fit(f.read())
    if n:
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
    return n


@contextlib.contextmanager
def fitted(board):
    """the path of a copy with the sockets fitted, beside the board (the same project and libraries), removed afterwards;
    the board's own path when it has none to fit"""
    with open(board, encoding="utf-8") as f:
        text, n = fit(f.read())
    if not n:
        yield board
        return
    h, copy = tempfile.mkstemp(prefix=".ps2-fitted-", suffix=".kicad_pcb", dir=os.path.dirname(os.path.abspath(board)))
    try:
        with os.fdopen(h, "w", encoding="utf-8") as f:
            f.write(text)
        yield copy
    finally:
        for p in (copy, copy[:-len("kicad_pcb")] + "kicad_prl"):
            if os.path.exists(p):
                os.remove(p)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    with fitted(sys.argv[1]) as b:
        sys.exit(subprocess.call([CLI, "pcb", "render"] + sys.argv[2:] + [b]))
