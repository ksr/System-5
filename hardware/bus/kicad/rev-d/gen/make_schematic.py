#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-26 (from the bus driver's make_schematic.py)
"""Write the S5BUS-D schematic (one A2 sheet) from gen/netlist.py using KiCad's stock symbols.
Every connected pin gets a short wire stub and a net label (power pins: a +5V / GND power symbol); unused pins get a
no-connect flag. Symbols come from KiCad's own libraries, flattened ("extends") and embedded as KiCad does.
Deterministic: uuids derive from names, so re-running gives the same file."""
import os, re, sys, uuid
HERE = os.path.dirname(os.path.abspath(__file__)); DEST = os.path.dirname(HERE); sys.path.insert(0, HERE)
import netlist as N
LIB = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols"
PROJ = "s5bus-d"
U = lambda *k: str(uuid.uuid5(uuid.NAMESPACE_URL, "s5bus-d/" + "/".join(map(str, k))))
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

PLACE = {"J%d" % k: (38.1 + 33.02 * (k - 1), 165.1) for k in range(1, 9)}     # the slots, side by side
PLACE.update({"C%d" % (k + 1): (38.1 + 33.02 * (k - 1) + 12.7, 101.6) for k in range(1, 9)})
PLACE.update({"J9": (330.2, 63.5), "D2": (355.6, 63.5), "C10": (381.0, 63.5), "R1": (406.4, 63.5), "D1": (406.4, 88.9),
              "SW1": (320.04, 114.3), "U1": (355.6, 114.3), "C1": (381.0, 114.3), "JP1": (431.8, 63.5), "J10": (431.8, 101.6),
              "RN1": (342.9, 152.4), "RN2": (381.0, 152.4), "RN3": (419.1, 152.4), "RN4": (457.2, 152.4)})
PLACE.update({"H%d" % k: (300.0 + 12.7 * ((k - 1) % 4), 240.0 + 12.7 * ((k - 1) // 4)) for k in range(1, 9)})
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
        lib_id, X, Y, "no" if ref.startswith("H") else "yes", U(ref), prop("Reference", ref, X, Y - 2.54 - max([abs(p[1]) for p in P.values()] or [2.54])),
        prop("Value", value, X, Y + 2.54 + max([abs(p[1]) for p in P.values()] or [2.54])), prop("Footprint", fp, X, Y, True),
        prop("Datasheet", N.DOCS.get(ref, ("",))[0], X, Y, True) + ("\n" + prop("Description", N.DOCS[ref][1], X, Y, True) if ref in N.DOCS else ""), "\n".join('\t\t(pin "%s" (uuid "%s"))' % (n, U(ref, n)) for n in P), PROJ, ROOT, ref))
    for num, (px, py, ang, hidden, pname) in P.items():
        net = pinmap.get(int(num)) if num.isdigit() else pinmap.get(num)
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

# PWR_FLAGs: GND and the regulator's input come in on the barrel jack, and +5V through the source jumper and the switch,
# which KiCad all sees as passive pins (5V_REG is driven by the regulator's output)
for i, net in enumerate(("VIN_D", "+5V", "GND")):
    x, y = 304.8, 76.2 + 12.7 * i
    libs["power:PWR_FLAG"] = libsym("power:PWR_FLAG")
    body.append('\t(symbol (lib_id "power:PWR_FLAG") (at %.2f %.2f 0) (unit 1)\n\t\t(exclude_from_sim no) (in_bom no) (on_board no) (dnp no) (uuid "%s")\n%s\n%s\n%s\n%s\n\t\t(pin "1" (uuid "%s"))\n\t\t(instances (project "%s" (path "/%s" (reference "#FLG%02d") (unit 1))))\n\t)' % (
        x, y, U("flg", net), prop("Reference", "#FLG%02d" % (i + 1), x, y, True), prop("Value", "PWR_FLAG", x, y - 3.81),
        prop("Footprint", "", x, y, True), prop("Datasheet", "", x, y, True), U("flg", net, "pin"), PROJ, ROOT, i + 1))
    body.append('\t(wire (pts (xy %.2f %.2f) (xy %.2f %.2f)) (stroke (width 0) (type default)) (uuid "%s"))' % (x, y, x + 5.08, y, U("flg", net, "w")))
    if net in ("+5V", "GND"):
        power(net, x + 5.08, y, "flag" + net)
    else:
        body.append('\t(label "%s" (at %.2f %.2f 0) (fields_autoplaced yes) (effects (font (size 1.27 1.27)) (justify left bottom)) (uuid "%s"))' % (
            net, x + 5.08, y, U("flg", net, "l")))

notes = [
    (25.4, 25.4, "System-5 BUS, Rev D (S5BUS-D, 2026): eight 36-pin slots, every pin bussed. Slot positions are counted from GND (Ken, 2026-11-18): 1-30 are the 30-pin System-5 bus, GND at 1, the end pin, to +5V at 30."),
    (25.4, 30.48, "Positions 31-36, beyond +5V: -EF1, -EF2, -EF3, -DMAIN, SC0, -PAUSE (the far end), the 36-pin extension. A 30-pin card (its own pin 1 +5V, pin 30 GND) plugs into positions 30-1, flush with the GND end."),
    (25.4, 35.56, "Power: a 7-15 V adapter on the centre-positive barrel jack J9, through D2 (Schottky: off if the plug is reversed) to U1, a TSR 3-2450N switching regulator (5 V at up to 3 A), or a regulated 5 V supply on the screw terminals J10. JP1 (one shunt: REG or EXT) picks the source; the power switch SW1 (an M9040P toggle, as the IO panel's data switches) then switches it onto +5V. C10 47 uF in, C1 220 uF bulk on +5V, 0.1 uF at each slot (C2-C9), power LED D1. No fuse."),
    (25.4, 40.64, "Pull-ups (10k): RN1 on D0-D7 (an empty read gives FF); RN2 on the open-collector lines -EF, -EF1-3, -PAUSE, -DMAIN, -INT, -RESET (they also hold with the CPU card out). Idle states with no master: RN3 pulls N0-N2, TPA, TPB down; RN4 pulls -VMA, -MRD, -MRW up."),
    (25.4, 45.72, "Pin numbers here are socket positions, not the 2009 Eagle numbers (docs/manual/bus.md). Generated by gen/make_schematic.py from gen/netlist.py."),
]
for x, y, txt in notes:
    body.append('\t(text "%s" (exclude_from_sim no) (at %.2f %.2f 0) (effects (font (size 1.778 1.778)) (justify left bottom)) (uuid "%s"))' % (txt, x, y, U("note", y)))

out = ['(kicad_sch', '\t(version 20250114)', '\t(generator "eeschema")', '\t(generator_version "10.0")', '\t(uuid "%s")' % ROOT,
       '\t(paper "A2")',
       '\t(title_block (title "System-5 bus backplane Rev D (S5BUS-D)") (date "2026-10-26") (rev "D") (comment 1 "Eight 36-pin slots, barrel jack and 5 V regulator or external 5 V, bypass, pull-ups") (comment 2 "Generated by gen/make_schematic.py from gen/netlist.py"))',
       '\t(lib_symbols']
for k in sorted(libs): out.append("\t\t" + libs[k].replace("\n", "\n\t\t"))
out.append('\t)'); out += body
out += ['\t(sheet_instances (path "/" (page "1")))', '\t(embedded_fonts no)', ')']
open(os.path.join(DEST, PROJ + ".kicad_sch"), "w").write("\n".join(out) + "\n")
print("schematic: %d parts, %d power symbols, %d lines" % (len(N.PARTS), pwr_n[0], len(out)))
