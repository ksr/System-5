#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-06
"""Write the BUSDRV-B schematic (one A3 sheet) from gen/netlist.py using KiCad's stock symbols.
Every connected pin gets a short wire stub and a net label (power pins: a +5V / GND power symbol); unused pins get a
no-connect flag. Symbols come from KiCad's own libraries, flattened ("extends") and embedded as KiCad does.
Deterministic: uuids derive from names, so re-running gives the same file."""
import os, re, sys, uuid
HERE = os.path.dirname(os.path.abspath(__file__)); DEST = os.path.dirname(HERE); sys.path.insert(0, HERE)
import netlist as N
LIB = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols"
PROJ = "busdrv-b"
U = lambda *k: str(uuid.uuid5(uuid.NAMESPACE_URL, "busdrv-a/" + "/".join(map(str, k))))   # "busdrv-a/" kept: the UUIDs link schematic and board
ROOT = U("root")

def block(text, i):
    d = 0; j = i; ins = False
    while True:
        c = text[j]
        if ins:
            if c == "\\": j += 1
            elif c == '"': ins = False
        elif c == '"': ins = True
        elif c == "(": d += 1
        elif c == ")":
            d -= 1
            if d == 0: return text[i:j + 1]
        j += 1

_cache = {}
def libsym(lib_id):
    """flattened symbol text named lib_id (Lib:Name), as embedded in a schematic"""
    lib, name = lib_id.split(":")
    t = _cache.setdefault(lib, open(os.path.join(LIB, lib + ".kicad_sym")).read())
    b = block(t, t.index('(symbol "%s"' % name))
    m = re.search(r'\(extends "([^"]+)"\)', b)
    if m:
        parent = m.group(1); pb = block(t, t.index('(symbol "%s"' % parent))
        props = dict(re.findall(r'\(property "([^"]+)" ("[^"]*")', b))
        pb = pb.replace('(symbol "%s_' % parent, '(symbol "%s_' % name)
        for k, v in props.items():
            pb = re.sub(r'\(property "%s" "[^"]*"' % re.escape(k), '(property "%s" %s' % (k, v), pb, count=1)
        b = pb.replace('(symbol "%s"' % parent, '(symbol "%s"' % name, 1)
    return b.replace('(symbol "%s"' % name, '(symbol "%s"' % lib_id, 1)

def pins(symtext):
    out = {}
    for m in re.finditer(r'\(pin \w+ \w+\s*\(at ([\-\d.]+) ([\-\d.]+) (\d+)\)\s*\(length ([\d.]+)\)(\s*\(hide yes\))?\s*\(name "([^"]*)".*?\(number "([^"]*)"', symtext, re.S):
        out[m.group(7)] = (float(m.group(1)), float(m.group(2)), int(m.group(3)), bool(m.group(5)), m.group(6))
    return out

PLACE = {   # ref: (x, y) on the A3 sheet, rotation 0
    "J1": (45.72, 110.49), "U1": (127.0, 76.2), "U2": (127.0, 160.02), "A1": (254.0, 110.49),
    "R1": (317.5, 50.8), "R2": (330.2, 50.8), "R3": (342.9, 50.8), "R4": (355.6, 50.8), "R5": (355.6, 76.2),
    "R6": (368.3, 50.8), "D1": (368.3, 76.2), "C1": (317.5, 101.6), "C2": (330.2, 101.6), "C3": (342.9, 101.6),
    "J2": (330.2, 165.1),
}
F = '(effects (font (size 1.27 1.27))%s)'
def prop(k, v, x, y, hide=False, ang=0):
    return '\t\t(property "%s" "%s" (at %.2f %.2f %d) %s)' % (k, v, x, y, ang, F % (" (hide yes)" if hide else ""))

body = []; libs = {}; pwr_n = [0]
def power(net, x, y, tag):
    lib_id = "power:" + net
    libs[lib_id] = libsym(lib_id)
    pwr_n[0] += 1; ref = "#PWR%02d" % pwr_n[0]
    yv = y - 3.81 if net == "+5V" else y + 5.08
    body.append('\t(symbol (lib_id "%s") (at %.2f %.2f 0) (unit 1)\n\t\t(exclude_from_sim no) (in_bom no) (on_board no) (dnp no) (uuid "%s")\n%s\n%s\n%s\n%s\n\t\t(pin "1" (uuid "%s"))\n\t\t(instances (project "%s" (path "/%s" (reference "%s") (unit 1))))\n\t)' % (
        lib_id, x, y, U("pwr", tag), prop("Reference", ref, x, y, True), prop("Value", net, x, yv), prop("Footprint", "", x, y, True),
        prop("Datasheet", "", x, y, True), U("pwr", tag, "pin"), PROJ, ROOT, ref))

for ref, (lib_id, value, fp, pinmap) in N.PARTS.items():
    s = libsym(lib_id); libs[lib_id] = s; P = pins(s); X, Y = PLACE[ref]
    body.append('\t(symbol (lib_id "%s") (at %.2f %.2f 0) (unit 1)\n\t\t(exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no) (uuid "%s")\n%s\n%s\n%s\n%s\n%s\n\t\t(instances (project "%s" (path "/%s" (reference "%s") (unit 1))))\n\t)' % (
        lib_id, X, Y, U(ref), prop("Reference", ref, X, Y - 2.54 - max(abs(p[1]) for p in P.values())),
        prop("Value", value, X, Y + 2.54 + max(abs(p[1]) for p in P.values())), prop("Footprint", fp, X, Y, True),
        prop("Datasheet", "", X, Y, True), "\n".join('\t\t(pin "%s" (uuid "%s"))' % (n, U(ref, n)) for n in P), PROJ, ROOT, ref))
    for num, (px, py, ang, hidden, pname) in P.items():
        net = pinmap.get(int(num)) if num.isdigit() else None
        cx, cy = X + px, Y - py                           # symbol y is up, sheet y is down
        if hidden and net is None: continue
        if net is None:
            body.append('\t(no_connect (at %.2f %.2f) (uuid "%s"))' % (cx, cy, U(ref, num, "nc"))); continue
        d = {0: (-1, 0), 180: (1, 0), 90: (0, 1), 270: (0, -1)}[ang]      # the stub leaves the pin away from the body
        ex, ey = cx + 2.54 * d[0], cy + 2.54 * d[1]
        body.append('\t(wire (pts (xy %.2f %.2f) (xy %.2f %.2f)) (stroke (width 0) (type default)) (uuid "%s"))' % (cx, cy, ex, ey, U(ref, num, "w")))
        if net in ("+5V", "GND"):
            power(net, ex, ey, ref + "." + num)
        else:
            la = {(-1, 0): (180, "right"), (1, 0): (0, "left"), (0, 1): (270, "right"), (0, -1): (90, "left")}[d]
            body.append('\t(label "%s" (at %.2f %.2f %d) (fields_autoplaced yes) (effects (font (size 1.27 1.27)) (justify %s bottom)) (uuid "%s"))' % (
                net, ex, ey, la[0], la[1], U(ref, num, "l")))

# PWR_FLAGs: +5V and GND are driven from the bus connector, which KiCad sees as passive pins
for i, net in enumerate(("+5V", "GND")):
    x, y = 393.7, 160.02 + 12.7 * i
    libs["power:PWR_FLAG"] = libsym("power:PWR_FLAG")
    body.append('\t(symbol (lib_id "power:PWR_FLAG") (at %.2f %.2f 0) (unit 1)\n\t\t(exclude_from_sim no) (in_bom no) (on_board no) (dnp no) (uuid "%s")\n%s\n%s\n%s\n%s\n\t\t(pin "1" (uuid "%s"))\n\t\t(instances (project "%s" (path "/%s" (reference "#FLG%02d") (unit 1))))\n\t)' % (
        x, y, U("flg", net), prop("Reference", "#FLG%02d" % (i + 1), x, y, True), prop("Value", "PWR_FLAG", x, y - 3.81),
        prop("Footprint", "", x, y, True), prop("Datasheet", "", x, y, True), U("flg", net, "pin"), PROJ, ROOT, i + 1))
    body.append('\t(wire (pts (xy %.2f %.2f) (xy %.2f %.2f)) (stroke (width 0) (type default)) (uuid "%s"))' % (x, y, x + 5.08, y, U("flg", net, "w")))
    power(net, x + 5.08, y, "flag" + net)

notes = [
    (25.4, 25.4, "System-5 BUS DRIVER (BUSDRV-B): an Arduino Nano on USB drives two MCP23017 I2C expanders straight onto the 30-pin System-5 bus."),
    (25.4, 30.48, "Bus master only with the CPU card removed; with the CPU in, the firmware keeps every expander pin an input (monitor)."),
    (25.4, 35.56, "Open-collector lines (-RESET, -INT, -EF) are only ever driven low or left floating. MCP23017 GPA7/GPB7 are output-only: they carry SPARE1-4 (J2)."),
    (25.4, 40.64, "Power: the Nano runs from USB; expanders, I2C pull-ups and XRST pull-up from bus +5V, so USB never feeds the bus. A0 (BUS_SENSE) reads bus +5V."),
]
for x, y, txt in notes:
    body.append('\t(text "%s" (exclude_from_sim no) (at %.2f %.2f 0) (effects (font (size 1.778 1.778)) (justify left bottom)) (uuid "%s"))' % (txt, x, y, U("note", y)))

out = ['(kicad_sch', '\t(version 20250114)', '\t(generator "eeschema")', '\t(generator_version "10.0")', '\t(uuid "%s")' % ROOT,
       '\t(paper "A3")',
       '\t(title_block (title "System-5 Bus Driver Rev B (BUSDRV-B)") (date "2026-10-19") (rev "B") (comment 1 "Arduino Nano + 2x MCP23017 on the System-5 bus; KiCad master") (comment 2 "Generated by gen/make_schematic.py from gen/netlist.py"))',
       '\t(lib_symbols']
for k in sorted(libs): out.append("\t\t" + libs[k].replace("\n", "\n\t\t"))
out.append('\t)'); out += body
out += ['\t(sheet_instances (path "/" (page "1")))', '\t(embedded_fonts no)', ')']
open(os.path.join(DEST, PROJ + ".kicad_sch"), "w").write("\n".join(out) + "\n")
print("schematic: %d parts, %d power symbols, %d lines" % (len(N.PARTS), pwr_n[0], len(out)))
