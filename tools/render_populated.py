# Author: Claude (Anthropic) for Ken Rother, 2026
"""Render a KiCad board with its parts fitted, for the website's pictures: copy the .kicad_pcb to a temporary file,
attach KiCad's standard 3D model to every footprint that has none (the parts converted from Eagle), and render that
copy with kicad-cli. The board file itself is never changed. YACC1-D's tool of the same name (2026-10-11), with
System-5's parts added and its one view.

    python3 tools/render_populated.py BOARD.kicad_pcb [--check] [--back]

writes NAME-populated-render-top.png beside the board (flat, from above, drawn the way the board is drawn, like the
builds' own NAME-render-top.png, which it does not replace); the website shows it in preference to that one.
--check only lists what each footprint gets. --back also writes NAME-populated-render-bottom.png, the back of the board
(the front panel's ribbon header is there); the website shows it under the front.

Each rule names the standard model and two of its pads: the model is placed so its first pad sits on the footprint's
pad of that name, and turned (in 90-degree steps) so the line to the second pad points the same way as on the board.
"""
import math, os, re, subprocess, sys

CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
M = "${KICAD10_3DMODEL_DIR}/"
HERE = os.path.dirname(os.path.abspath(__file__))     # models/: the ones KiCad has not got

# Eagle footprint name -> (model, origin pad, second pad, where the second pad is in the model's own footprint)
RULES = {
    "C025-050X050": ("Capacitor_THT.3dshapes/C_Disc_D5.0mm_W2.5mm_P2.50mm.step", "1", "2", (2.5, 0)),
    "C025-025X050": ("Capacitor_THT.3dshapes/C_Disc_D3.0mm_W2.0mm_P2.50mm.step", "1", "2", (2.5, 0)),
    "0207_7": ("Resistor_THT.3dshapes/R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal.step", "1", "2", (7.62, 0)),
    "0207_10": ("Resistor_THT.3dshapes/R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal.step", "1", "2", (10.16, 0)),
    "E2,5-7": ("Capacitor_THT.3dshapes/CP_Radial_D6.3mm_P2.50mm.step", "+", "-", (2.5, 0)),
    "LED5MM": ("LED_THT.3dshapes/LED_D5.0mm.step", "K", "A", (2.54, 0)),
    "HC49U-V": ("Crystal.3dshapes/Crystal_HC49-4H_Vertical.step", "1", "2", (4.88, 0)),
    "MA03-1": ("Connector_PinHeader_2.54mm.3dshapes/PinHeader_1x03_P2.54mm_Vertical.step", "1", "2", (0, 2.54)),
    "1X03": ("Connector_PinHeader_2.54mm.3dshapes/PinHeader_1x03_P2.54mm_Vertical.step", "1", "2", (0, 2.54)),
    "MA04-2": ("Connector_PinHeader_2.54mm.3dshapes/PinHeader_2x04_P2.54mm_Vertical.step", "1", "3", (0, 2.54)),
    "2X07": ("Connector_PinHeader_2.54mm.3dshapes/PinHeader_2x07_P2.54mm_Vertical.step", "1", "3", (0, 2.54)),
    "MA08-1": ("Connector_PinHeader_2.54mm.3dshapes/PinHeader_1x08_P2.54mm_Vertical.step", "1", "2", (0, 2.54)),
    "MA08-2": ("Connector_PinHeader_2.54mm.3dshapes/PinHeader_2x08_P2.54mm_Vertical.step", "1", "3", (0, 2.54)),
    "C30": ("Connector_PinHeader_2.54mm.3dshapes/PinHeader_1x30_P2.54mm_Horizontal.step", "30", "1", (0, 73.66)),
    "SIL10": ("Resistor_THT.3dshapes/R_Array_SIP10.step", "1", "2", (2.54, 0)),
    "RN-5": ("Resistor_THT.3dshapes/R_Array_SIP5.step", "1", "2", (2.54, 0)),
    "RN-9": ("Resistor_THT.3dshapes/R_Array_SIP9.step", "1", "2", (2.54, 0)),
    "SIL9": ("Resistor_THT.3dshapes/R_Array_SIP9.step", "1", "2", (2.54, 0)),
    "FABC96R": ("Connector_DIN.3dshapes/DIN41612_C_3x32_Male_Horizontal_THT.step", "A1", "A2", (2.54, 0)),
    "F09HP": ("Connector_Dsub.3dshapes/DSUB-9_Socket_Horizontal_P2.77x2.54mm_EdgePinOffset9.40mm.step",
              "1", "2", (-2.77, 0)),
    # the PS/2 sockets (models/gen_minidin6.py; Ken, 2026-11-23: every new render shows them fitted)
    "MiniDIN6_MD-60SM": (HERE + "/models/MiniDIN6_MD-60SM.step", "1", "2", (0, 2.6)),
    "MiniDIN-6_Female_Horizontal_SameSky_MD-60SM": (HERE + "/models/MiniDIN6_MD-60SM.step", "1", "2", (0, 2.6)),   # P32W
    # the rest of the parts KiCad has not got (models/gen_parts.py; Ken, 2026-11-24)
    "HTIL311A": (HERE + "/models/TIL311.step", "1", "14", (7.62, 0)),
    "Fuse_Bourns_MF-RHT050": (HERE + "/models/PTC_MF-RHT050.step", "1", "2", (-1.2, 5.1)),
    "Fuse_Bourns_MF-RG500": (HERE + "/models/PTC_MF-RG500.step", "1", "2", (-1.2, 5.1)),
    "Potentiometer_Trim_3386_Inline": (HERE + "/models/Trimmer_3386.step", "1", "2", (2.54, 0)),
    "Converter_DCDC_TRACO_TSR2-24xxN_TSR2-24xxxN_THT": (HERE + "/models/TSR_3-2450N.step", "1", "2", (0, 2.54)),
    "Arduino_Nano": (HERE + "/models/Arduino_Nano.step", "1", "2", (0, 2.54)),
    "PIN_3X8": (HERE + "/models/PinHeader_3x08.step", "1", "2", (2.54, 0)),
    "E5-6": (HERE + "/models/CP_D6.3_P5.08.step", "+", "-", (5.08, 0)),
    # parts KiCad has a model for
    "C025-024X044": ("Capacitor_THT.3dshapes/C_Disc_D3.8mm_W2.6mm_P2.50mm.step", "1", "2", (2.5, 0)),
    "HC49_S": ("Crystal.3dshapes/Crystal_HC49-4H_Vertical.step", "1", "2", (4.88, 0)),
    "JP1": ("Connector_PinHeader_2.54mm.3dshapes/PinHeader_1x02_P2.54mm_Vertical.step", "1", "2", (0, 2.54)),
    "FTDI_DEVICE_SIDE": ("Connector_PinHeader_2.54mm.3dshapes/PinHeader_1x06_P2.54mm_Vertical.step", "P$1", "P$2", (0, 2.54)),
    "SW4-6.2X6.2X5.0MM": ("Button_Switch_THT.3dshapes/SW_PUSH_6mm_H5mm.step", "1", "2", (0, 4.5)),
    "TACTILE-PTH-SIDEEZ": ("Button_Switch_THT.3dshapes/SW_Tactile_SPST_Angled_PTS645Vx83-2LFS.step", "2", "1", (4.5, 0)),
    "LCD1602": ("Display.3dshapes/WC1602A.step", "1", "2", (2.54, 0)),
    "FABC96S": ("Connector_DIN.3dshapes/DIN41612_C_3x32_Female_Vertical_THT.step", "A1", "A2", (0, 2.54)),
    "DSUB-9_Socket_Horizontal_IO-V1.1": ("Connector_Dsub.3dshapes/DSUB-9_Socket_Horizontal_P2.77x2.84mm_EdgePinOffset9.90mm_"
                                         "Housed_MountingHolesOffset11.32mm.step", "1", "2", (-2.77, 0)),
    # the toggles (models/gen_toggles.py; Ken, 2026-11-24)
    "M9040P": (HERE + "/models/Toggle_M9040P.step", "2", "3", (0, 4.699)),
    "SW_Toggle_M9040P": (HERE + "/models/Toggle_M9040P.step", "2", "3", (0, 4.699)),
    "9070-1W": (HERE + "/models/Toggle_9070-1W.step", "2", "1", (0, 2.54)),
    "SW_Toggle_SPDT_Marquardt_9070-1W": (HERE + "/models/Toggle_9070-1W.step", "2", "1", (0, 2.54)),
    # the RCA jack (models/gen_rca.py; Ken, 2026-11-24)
    "RCA": (HERE + "/models/RCA.step", "S1", "S3", (0, 10.16)),
    "MiniDIN6_RA_PS2": (HERE + "/models/MiniDIN6_RA_PS2-body.step", "1", "2", (0, -2.6)),                          # P8X
    # the built 2005 cards' Eagle parts that had none (2026-11-26, so that every System-5 card renders with every part)
    "M_DIN6": (HERE + "/models/MiniDIN6_MD-60SM.step", "1", "2", (0, 2.6)),        # the IO card's PS/2 socket (2005)
    "0207_2V": ("Resistor_THT.3dshapes/R_Axial_DIN0207_L6.3mm_D2.5mm_P2.54mm_Vertical.step", "1", "2", (2.54, 0)),
    "HC49U70": ("Crystal.3dshapes/Crystal_HC49-U_Vertical.step", "1", "2", (4.88, 0)),
    "B3F-10XX": ("Button_Switch_THT.3dshapes/SW_PUSH_6mm_H5mm.step", "1", "3", (0, 4.5)),
    "1X02": ("Connector_PinHeader_2.54mm.3dshapes/PinHeader_1x02_P2.54mm_Vertical.step", "1", "2", (0, 2.54)),
    "2POL254": ("Connector_PinHeader_2.54mm.3dshapes/PinHeader_1x02_P2.54mm_Vertical.step", "1", "2", (0, 2.54)),
    "MA04-1": ("Connector_PinHeader_2.54mm.3dshapes/PinHeader_1x04_P2.54mm_Vertical.step", "1", "2", (0, 2.54)),
    "MA03-2": ("Connector_PinHeader_2.54mm.3dshapes/PinHeader_2x03_P2.54mm_Vertical.step", "1", "3", (0, 2.54)),
    "MA05-2": ("Connector_PinHeader_2.54mm.3dshapes/PinHeader_2x05_P2.54mm_Vertical.step", "1", "3", (0, 2.54)),
    "MA07-2": ("Connector_PinHeader_2.54mm.3dshapes/PinHeader_2x07_P2.54mm_Vertical.step", "1", "3", (0, 2.54)),
    "JP4Q": ("Connector_PinHeader_2.54mm.3dshapes/PinHeader_2x04_P2.54mm_Vertical.step", "1", "3", (0, 2.54)),
    "2X20": ("Connector_PinHeader_2.54mm.3dshapes/PinHeader_2x20_P2.54mm_Vertical.step", "1", "3", (0, 2.54)),
    "C36A": ("Connector_PinSocket_2.54mm.3dshapes/PinSocket_1x36_P2.54mm_Vertical.step", "33", "32", (0, 2.54)),  # the 2009 bus (pad 33 the top end: 33, 32, 31, then 1-30, 34-36)
}

# a socket's model is the empty socket: the chip goes in it, standing this high (ELF II's figure, read from a render)
SEAT = 3.0
SOCKET = re.compile(r'\(model "([^"]*Package_DIP\.3dshapes/DIP-\d+_W[\d.]+mm)_Socket\.step"(.*?)\n\t\t\)\n', re.S)
# parts that need no model: holes
NO_MODEL = re.compile(r"MountingHole|dummyfp")


# footprints that name a model KiCad does not hold: ours is added
NAMED_ONLY = {"Fuse_Bourns_MF-RHT050", "Fuse_Bourns_MF-RG500", "Converter_DCDC_TRACO_TSR2-24xxN_TSR2-24xxxN_THT",
              "Arduino_Nano"}


def footprints(text):
    """(start, end) of every top-level (footprint ...) block."""
    out, i = [], 0
    while True:
        i = text.find("\n\t(footprint ", i)
        if i < 0:
            return out
        depth, j = 0, i + 2
        while True:
            c = text[j]
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    break
            elif c == '"':
                j += 1
                while text[j] != '"':              # a quoted string; a backslash quotes the next character
                    j += 2 if text[j] == "\\" else 1
            j += 1
        out.append((i + 1, j + 1))
        i = j


def rule_for(name, pads):
    base = name.split(":")[-1]
    if base in RULES:
        return RULES[base]
    m = re.match(r"(?:DIL|DIP-?)(\d+)(?:-\d+)?$", base)
    if m and "1" in pads and "2" in pads:
        n = int(m.group(1))
        p1, pn = pads["1"], pads.get(str(n))
        w = 15.24 if pn and abs(math.dist(p1, pn) - 15.24) < abs(math.dist(p1, pn) - 7.62) else 7.62
        return ("Package_DIP.3dshapes/DIP-%d_W%.2fmm.step" % (n, w), "1", "2", (0, 2.54))
    return None


def model_block(model, offset, rot):
    return ('\t\t(model "%s%s"\n\t\t\t(offset\n\t\t\t\t(xyz %.4f %.4f 0)\n\t\t\t)\n\t\t\t(scale\n\t\t\t\t(xyz 1 1 1)\n'
            '\t\t\t)\n\t\t\t(rotate\n\t\t\t\t(xyz 0 0 %d)\n\t\t\t)\n\t\t)\n' % ("" if model.startswith("/") else M, model, offset[0], offset[1], rot))


def populate(text, report):
    pieces, last = [], 0
    for a, b in footprints(text):
        block = text[a:b]
        name = block.split('"')[1]
        ref = re.search(r'\(property "Reference" "([^"]*)"', block)
        ref = ref.group(1) if ref else "?"
        if "(model " in block and name.split(":")[-1] not in NAMED_ONLY:
            sock = SOCKET.search(block)
            if sock:                       # the chip in the socket: the socket's own offset and turn, raised by SEAT
                chip = sock.group(0).replace("_Socket.step", ".step")
                chip = re.sub(r"(\(offset\s*\(xyz [-\d.]+ [-\d.]+ )[-\d.]+\)", lambda m: m.group(1) + "%g)" % SEAT, chip, 1)
                pieces += [text[last:b - 1], "\t\t" + chip, "\t"]
                last = b - 1
                report.append("%-6s %-40s has a model, + %s in the socket" % (ref, name, sock.group(1).split("/")[-1] + ".step"))
            else:
                report.append("%-6s %-40s has a model" % (ref, name))
            continue
        pads = {}
        for m in re.finditer(r'\(pad "([^"]*)"[^(]*\(at ([-\d.]+) ([-\d.]+)', block):
            pads.setdefault(m.group(1), (float(m.group(2)), float(m.group(3))))
        rule = rule_for(name, pads)
        if not rule or rule[1] not in pads or rule[2] not in pads:
            report.append("%-6s %-40s %s" % (ref, name, "a hole: no model" if NO_MODEL.search(name) else "no model (left bare)"))
            continue
        model, pa, pb, std = rule
        (ax, ay), (bx, by) = pads[pa], pads[pb]
        # angles with y up (board files have y down)
        ang = math.degrees(math.atan2(-(by - ay), bx - ax) - math.atan2(-std[1], std[0]))
        rot = -int(round(ang / 90.0)) * 90 % 360   # KiCad turns models clockwise for a positive angle
        pieces += [text[last:b - 1], model_block(model, (ax, -ay), rot), "\t"]
        last = b - 1
        report.append("%-6s %-40s %s, rotate %d" % (ref, name, model.split("/")[-1], rot))
    pieces.append(text[last:])
    return "".join(pieces)


def main():
    board = os.path.abspath(sys.argv[1])
    report = []
    before = open(board, "rb").read()
    text = populate(before.decode("utf-8"), report)
    print("\n".join(report))
    bare = [r for r in report if "left bare" in r]
    if "--check" in sys.argv:
        return
    if bare: raise SystemExit("render_populated.py: parts left bare (give each footprint a rule in RULES):\n" + "\n".join(bare))
    here, name = os.path.split(board[:-len(".kicad_pcb")])
    # the copy sits beside the original (same project, libraries and variables)
    stem = os.path.join(here, ".render-populated")
    open(stem + ".kicad_pcb", "w", encoding="utf-8").write(text)
    try:
        for side in ["top"] + (["bottom"] if "--back" in sys.argv else []):
            out = os.path.join(here, "%s-populated-render-%s.png" % (name, side))
            subprocess.run([CLI, "pcb", "render", "--side", side, "--quality", "high", "--floor", "-w", "1800", "-h", "1200",
                            "-o", out, stem + ".kicad_pcb"], check=True, capture_output=True)
            print("wrote", out)
    finally:
        for ext in (".kicad_pcb", ".kicad_prl"):
            if os.path.exists(stem + ext): os.remove(stem + ext)
    if open(board, "rb").read() != before: raise SystemExit("render_populated.py: the board file changed")


if __name__ == "__main__":
    main()
