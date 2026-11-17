#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-01
"""make_schematic.py BOARD_DIR - write a VIDEO-G board's KiCad schematic from its gen/netlist.py.

The working schematic for ERC, the netlist export and the board's schematic parity: every unit of every symbol placed
on one sheet in rows, each connected pin with a short stub and a net label (VCC / GND: power symbols), each unused pin
with a no-connect flag. The readable schematic for the PDF book is redrawn from the board netlist by
tools/kicad/sch/gen_schematic.py (schematic/spec.py). Deterministic: uuids derive from names.
Writes BOARD_DIR/<PROJ>.kicad_sch, where PROJ is the netlist module's PROJ.
"""
import os, sys, uuid, importlib.util
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import symlib

board = os.path.abspath(sys.argv[1])
spec = importlib.util.spec_from_file_location("netlist", os.path.join(board, "gen", "netlist.py"))
N = importlib.util.module_from_spec(spec); spec.loader.exec_module(N)
PROJ = N.PROJ
U = lambda *k: str(uuid.uuid5(uuid.NAMESPACE_URL, PROJ + "/" + "/".join(map(str, k))))
ROOT = U("root")
POWER_NETS = ("+5V", "GND")                 # System-5's names (2026-11-17; VCC before)
FLAG_NETS = ("+5V", "GND") + tuple(getattr(N, "FLAG_NETS", ()))
G = 2.54
snap = lambda v: round(v / G) * G
F = '(effects (font (size 1.27 1.27))%s)'


def prop(k, v, x, y, hide=False, ang=0):
    return '\t\t(property "%s" "%s" (at %.2f %.2f %d) %s)' % (k, v, x, y, ang, F % (" (hide yes)" if hide else ""))


pinmap = N.pinmap()
libs, body = {}, []
pwr_n = [0]


def power(net, x, y, tag):
    lib_id = "power:" + net
    libs[lib_id] = symlib.symbol(lib_id)
    pwr_n[0] += 1; ref = "#PWR%03d" % pwr_n[0]
    yv = y - 3.81 if net != "GND" else y + 5.08
    body.append('\t(symbol (lib_id "%s") (at %.2f %.2f 0) (unit 1)\n\t\t(exclude_from_sim no) (in_bom no) (on_board no) '
                '(dnp no) (uuid "%s")\n%s\n%s\n%s\n%s\n\t\t(pin "1" (uuid "%s"))\n\t\t(instances (project "%s" (path "/%s" '
                '(reference "%s") (unit 1))))\n\t)' % (
                    lib_id, x, y, U("pwr", tag), prop("Reference", ref, x, y, True), prop("Value", net, x, yv),
                    prop("Footprint", "", x, y, True), prop("Datasheet", "", x, y, True), U("pwr", tag, "pin"), PROJ, ROOT,
                    ref))


# ---- lay the units out in rows (cell = body extent + room for stubs and labels) -------------------------------------
LABEL_ROOM = 22.86
cells = []
for ref, (value, lib_id, fp, note) in N.PARTS.items():
    P = symlib.pins(lib_id); us = [u for u in symlib.units(lib_id) if u != 0] or [0]
    for unit in us:
        up = [p for p in P.values() if p.unit in (unit, 0)]
        xs = [p.x for p in up] or [0]; ys = [p.y for p in up] or [0]
        w = (max(xs) - min(xs)) + 2 * LABEL_ROOM + 10; h = (max(ys) - min(ys)) + 15
        cells.append((ref, unit, lib_id, up, min(xs), max(ys), w, h))
WIDTH = 1150.0
x = y = 30.0; rowh = 0; place = []
for cell in cells:
    ref, unit, lib_id, up, minx, maxy, w, h = cell
    if x + w > WIDTH:
        x = 30.0; y += rowh + 8; rowh = 0
    ox = snap(x + LABEL_ROOM + 5 - minx); oy = snap(y + 10 + maxy)
    place.append((ref, unit, lib_id, up, ox, oy))
    x += w; rowh = max(rowh, h)
HEIGHT = y + rowh + 40

# ---- symbols, stubs, labels -----------------------------------------------------------------------------------------
for ref, unit, lib_id, up, X, Y in place:
    value, _, fp, note = N.PARTS[ref]
    libs[lib_id] = symlib.symbol(lib_id)
    top = max([p.y for p in up] or [0]); bot = min([p.y for p in up] or [0])
    uref = U(ref, unit)
    body.append('\t(symbol (lib_id "%s") (at %.2f %.2f 0) (unit %d)\n\t\t(exclude_from_sim no) (in_bom yes) (on_board yes) '
                '(dnp no) (uuid "%s")\n%s\n%s\n%s\n%s\n%s\n\t\t(instances (project "%s" (path "/%s" (reference "%s") '
                '(unit %d))))\n\t)' % (
                    lib_id, X, Y, max(unit, 1), uref, prop("Reference", ref, X, Y - top - 2.54),
                    prop("Value", value, X, Y - bot + 2.54), prop("Footprint", fp, X, Y, True),
                    prop("Datasheet", "", X, Y, True),
                    "\n".join('\t\t(pin "%s" (uuid "%s"))' % (p.number, U(ref, p.number)) for p in up), PROJ, ROOT, ref,
                    max(unit, 1)))
    for p in up:
        net = pinmap[ref].get(p.number)
        cx, cy = X + p.x, Y - p.y                                  # symbol y is up, sheet y is down
        if net is None:
            if p.hidden: continue
            body.append('\t(no_connect (at %.2f %.2f) (uuid "%s"))' % (cx, cy, U(ref, p.number, "nc"))); continue
        d = {0: (-1, 0), 180: (1, 0), 90: (0, 1), 270: (0, -1)}[p.angle]    # the stub leaves the pin away from the body
        ex, ey = cx + G * d[0], cy + G * d[1]
        body.append('\t(wire (pts (xy %.2f %.2f) (xy %.2f %.2f)) (stroke (width 0) (type default)) (uuid "%s"))' % (
            cx, cy, ex, ey, U(ref, p.number, "w")))
        if net in POWER_NETS:
            power(net, ex, ey, ref + "." + p.number)
        else:
            la = {(-1, 0): (180, "right"), (1, 0): (0, "left"), (0, 1): (270, "right"), (0, -1): (90, "left")}[d]
            body.append('\t(label "%s" (at %.2f %.2f %d) (fields_autoplaced yes) (effects (font (size 1.27 1.27)) '
                        '(justify %s bottom)) (uuid "%s"))' % (net, ex, ey, la[0], la[1], U(ref, p.number, "l")))

# ---- PWR_FLAGs: the bus connector and the fuse are passive pins -----------------------------------------------------
libs["power:PWR_FLAG"] = symlib.symbol("power:PWR_FLAG")
for i, net in enumerate(FLAG_NETS):
    fx, fy = snap(30.0 + 30 * i), snap(HEIGHT - 20)
    body.append('\t(symbol (lib_id "power:PWR_FLAG") (at %.2f %.2f 0) (unit 1)\n\t\t(exclude_from_sim no) (in_bom no) '
                '(on_board no) (dnp no) (uuid "%s")\n%s\n%s\n%s\n%s\n\t\t(pin "1" (uuid "%s"))\n\t\t(instances (project "%s" '
                '(path "/%s" (reference "#FLG%02d") (unit 1))))\n\t)' % (
                    fx, fy, U("flg", net), prop("Reference", "#FLG%02d" % (i + 1), fx, fy, True),
                    prop("Value", "PWR_FLAG", fx, fy - 3.81), prop("Footprint", "", fx, fy, True),
                    prop("Datasheet", "", fx, fy, True), U("flg", net, "pin"), PROJ, ROOT, i + 1))
    body.append('\t(wire (pts (xy %.2f %.2f) (xy %.2f %.2f)) (stroke (width 0) (type default)) (uuid "%s"))' % (
        fx, fy, fx + 5.08, fy, U("flg", net, "w")))
    if net in POWER_NETS:
        power(net, fx + 5.08, fy, "flag" + net)
    else:
        body.append('\t(label "%s" (at %.2f %.2f 0) (fields_autoplaced yes) (effects (font (size 1.27 1.27)) '
                    '(justify left bottom)) (uuid "%s"))' % (net, fx + 5.08, fy, U("flg", net, "l")))

for i, line in enumerate(N.SCH_NOTES):
    body.append('\t(text "%s" (exclude_from_sim no) (at 30 %.2f 0) (effects (font (size 2.0 2.0)) (justify left bottom)) '
                '(uuid "%s"))' % (line.replace('"', "'"), 12 + 3.2 * i, U("note", i)))

out = ['(kicad_sch', '\t(version 20250114)', '\t(generator "eeschema")', '\t(generator_version "10.0")',
       '\t(uuid "%s")' % ROOT, '\t(paper "User" %.0f %.0f)' % (WIDTH + 30, HEIGHT + 20),
       '\t(title_block (title "%s") (date "%s") (rev "%s") (comment 1 "%s") (comment 2 "Generated by '
       'hardware/video-g/kicad/common/make_schematic.py from gen/netlist.py"))' % (N.CARD, N.DATE, N.REV, N.SUBTITLE),
       '\t(lib_symbols']
for k in sorted(libs):
    out.append("\t\t" + libs[k].replace("\n", "\n\t\t"))
out.append('\t)'); out += body
out += ['\t(sheet_instances (path "/" (page "1")))', '\t(embedded_fonts no)', ')']
open(os.path.join(board, PROJ + ".kicad_sch"), "w").write("\n".join(out) + "\n")
print("schematic %s: %d parts, %d units, %d power symbols, sheet %.0f x %.0f mm" % (
    PROJ, len(N.PARTS), len(place), pwr_n[0], WIDTH + 30, HEIGHT + 20))
