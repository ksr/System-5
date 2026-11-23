#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-22 (from the IO panel card's make_schematic.py)
"""Write the front panel Rev A schematic (one A1 sheet) from gen/netlist.py: KiCad's stock symbols for the passives,
and project symbols (../s5fp.kicad_sym, written here from netlist.CHIPS: one unit each, in DIP pin order) for the logic.
Every connected pin gets a short wire stub and a net label (power pins: a +5V / GND power symbol); unused pins get a
no-connect flag. Symbols come from KiCad's own libraries, flattened ("extends") and embedded as KiCad does.
Deterministic: uuids derive from names, so re-running gives the same file."""
import os, re, sys, uuid
HERE = os.path.dirname(os.path.abspath(__file__)); DEST = os.path.dirname(HERE); sys.path.insert(0, HERE)
import netlist as N
LIB = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols"
PROJ = "front-panel-rev-a"
U = lambda *k: str(uuid.uuid5(uuid.NAMESPACE_URL, "front-panel-rev-a/" + "/".join(map(str, k))))
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

def chipsym(name):
    """a one-unit box symbol for netlist.CHIPS[name]: pins 1..n/2 down the left, the rest up the right (as on the DIP)"""
    fp, pins = N.CHIPS[name]; n = max(pins); half = (n + 1) // 2; W = 7.62; H = 2.54 * (half + 1) / 2
    eff = '(effects (font (size 1.27 1.27)))'
    out = ['(symbol "%s" (pin_names (offset 1.016)) (exclude_from_sim no) (in_bom yes) (on_board yes)' % name,
           '\t(property "Reference" "U" (at 0 %.2f 0) %s)' % (H + 1.27, eff),
           '\t(property "Value" "%s" (at 0 %.2f 0) %s)' % (name, -H - 1.27, eff),
           '\t(property "Footprint" "%s" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))' % fp,
           '\t(property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))',
           '\t(symbol "%s_0_1" (rectangle (start %.2f %.2f) (end %.2f %.2f) (stroke (width 0.254) (type default)) (fill (type background))))' % (name, -W, H, W, -H),
           '\t(symbol "%s_1_1"' % name]
    for k in range(1, n + 1):
        if k not in pins: continue
        nm, ty = pins[k]
        if k <= half: x, y, a = -W - 2.54, H - 2.54 * k, 0
        else: x, y, a = W + 2.54, H - 2.54 * (n + 1 - k), 180
        out.append('\t\t(pin %s line (at %.2f %.2f %d) (length 2.54) (name "%s" %s) (number "%d" %s))' % (ty, x, y, a, nm, eff, k, eff))
    out += ['\t)', ')']
    return "\n".join(out)

LOCAL = {"s5fp": "\n".join(['(kicad_symbol_lib (version 20241209) (generator "make_schematic.py")'] + [chipsym(c) for c in N.CHIPS] + [')'])}
open(os.path.join(DEST, "s5fp.kicad_sym"), "w").write(LOCAL["s5fp"] + "\n")
import subprocess                                   # KiCad's own layout of the file, which the redraw tool reads
subprocess.run(["/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli", "sym", "upgrade", "--force",
                os.path.join(DEST, "s5fp.kicad_sym")], check=True, capture_output=True)

_cache = dict(LOCAL)
def libsym(lib_id):
    """flattened symbol text named lib_id (Lib:Name), as embedded in a schematic"""
    lib, name = lib_id.split(":")
    if lib not in _cache: _cache[lib] = open(os.path.join(LIB, lib + ".kicad_sym")).read()
    t = _cache[lib]
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

# placement: shelf-pack the parts left to right, rows top to bottom (the redrawn schematic, gen_schematic.py, is the
# readable drawing; this sheet only has to be correct)
PLACE = {}
def _size(ref):
    P = pins(libsym(N.PARTS[ref][0]))
    ys = [abs(p[1]) for p in P.values()] or [2.54]; xs = [abs(p[0]) for p in P.values()] or [2.54]
    return 2 * max(xs) + 30.0, 2 * max(ys) + 15.24
_x, _y, _row = 38.1, 60.96, 0.0
for ref in N.PARTS:
    w, h = _size(ref)
    if _x + w > 800: _x, _y, _row = 38.1, _y + _row, 0.0
    PLACE[ref] = (round((_x + w / 2) / 2.54) * 2.54, round((_y + h / 2) / 2.54) * 2.54)
    _x += w; _row = max(_row, h)
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
    body.append('\t(symbol (lib_id "%s") (at %.2f %.2f 0) (unit 1)\n\t\t(exclude_from_sim no) (in_bom %s) (on_board yes) (dnp no) (uuid "%s")\n%s\n%s\n%s\n%s\n%s\n\t\t(instances (project "%s" (path "/%s" (reference "%s") (unit 1))))\n\t)' % (
        lib_id, X, Y, "no" if lib_id.startswith("Mechanical:") else "yes", U(ref), prop("Reference", ref, X, Y - 2.54 - max([abs(p[1]) for p in P.values()] or [2.54])),
        prop("Value", value, X, Y + 2.54 + max([abs(p[1]) for p in P.values()] or [2.54])), prop("Footprint", fp, X, Y, True),
        prop("Datasheet", N.DOCS.get(ref, ("",))[0], X, Y, True) + ("\n" + prop("Description", N.DOCS[ref][1], X, Y, True) if ref in N.DOCS else ""), "\n".join('\t\t(pin "%s" (uuid "%s"))' % (n, U(ref, n)) for n in P), PROJ, ROOT, ref))
    for num, (px, py, ang, hidden, pname) in P.items():
        net = pinmap.get(int(num)) if num.isdigit() else pinmap.get(num)     # "SH": the DE-9's shell
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
    x, y = 762.0, 520.7 + 12.7 * i
    libs["power:PWR_FLAG"] = libsym("power:PWR_FLAG")
    body.append('\t(symbol (lib_id "power:PWR_FLAG") (at %.2f %.2f 0) (unit 1)\n\t\t(exclude_from_sim no) (in_bom no) (on_board no) (dnp no) (uuid "%s")\n%s\n%s\n%s\n%s\n\t\t(pin "1" (uuid "%s"))\n\t\t(instances (project "%s" (path "/%s" (reference "#FLG%02d") (unit 1))))\n\t)' % (
        x, y, U("flg", net), prop("Reference", "#FLG%02d" % (i + 1), x, y, True), prop("Value", "PWR_FLAG", x, y - 3.81),
        prop("Footprint", "", x, y, True), prop("Datasheet", "", x, y, True), U("flg", net, "pin"), PROJ, ROOT, i + 1))
    body.append('\t(wire (pts (xy %.2f %.2f) (xy %.2f %.2f)) (stroke (width 0) (type default)) (uuid "%s"))' % (x, y, x + 5.08, y, U("flg", net, "w")))
    power(net, x + 5.08, y, "flag" + net)

notes = [
    (25.4, 25.4, "System-5 front panel, Rev A (2026): the hand controls and displays on a board that mounts as the front of a case, on a 50-way ribbon from the IO panel card's J3 (pin n to pin n; tools/s5panel.py). Design notes: ../DESIGN.md."),
    (25.4, 30.48, "Displays: U1-U4 the bus address ADR15-ADR0, U5 / U6 the IO card's output port OUT7-OUT0, LED1-LED8 the same byte (RN1). Data toggles SW1-SW8 switch SW0-SW7 to +5V through RN2 (1k); the IO card pulls them down. INPUT (SW11) to ground."),
    (25.4, 35.56, "RUN/RESET (SW9) grounds -RESET, LOAD (SW10) grounds -PAUSE. RESET (SW12, debounced by R7 / C1 / U7D) pulls -RESET and -DMAIN low together through U10A / U10B (74HC03, open drain): a boot reset, which starts the machine in the EPROM. Not while -PAUSE is low."),
    (25.4, 40.64, "Status LEDs (1k each from +5V): PWR; Q (the IO card sinks it); PAUSE and RESET (PAUSE_N and RESET_N, U7E / U7F); ROM (the IO card sinks it); START FROM RAM = !Q of U9A, a copy of the CPU card's LOADED flag: set by LOAD mode (U8A), cleared by a boot reset (U8B)."),
    (25.4, 45.72, "Generated by gen/make_schematic.py from gen/netlist.py."),
]
for x, y, txt in notes:
    body.append('\t(text "%s" (exclude_from_sim no) (at %.2f %.2f 0) (effects (font (size 1.778 1.778)) (justify left bottom)) (uuid "%s"))' % (txt, x, y, U("note", y)))

out = ['(kicad_sch', '\t(version 20250114)', '\t(generator "eeschema")', '\t(generator_version "10.0")', '\t(uuid "%s")' % ROOT,
       '\t(paper "A1")',
       '\t(title_block (title "System-5 front panel Rev A") (date "2026-11-22") (rev "A") (comment 1 "Six TIL311s, bit and status LEDs, data toggles, RUN, LOAD, INPUT, RESET; a 50-way ribbon to the IO panel card") (comment 2 "Generated by gen/make_schematic.py from gen/netlist.py"))',
       '\t(lib_symbols']
for k in sorted(libs): out.append("\t\t" + libs[k].replace("\n", "\n\t\t"))
out.append('\t)'); out += body
out += ['\t(sheet_instances (path "/" (page "1")))', '\t(embedded_fonts no)', ')']
open(os.path.join(DEST, PROJ + ".kicad_sch"), "w").write("\n".join(out) + "\n")
print("schematic: %d parts, %d power symbols, %d lines" % (len(N.PARTS), pwr_n[0], len(out)))
