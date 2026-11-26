#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-20
"""make_schematic.py - Rev B-Clean-Keyboard's schematic: Rev B-Clean's (../rev-b-clean, itself Rev B's 2005 Eagle
drawing without the DE-9) with the keyboard section of gen/keyboard.py. Starts from Rev B-Clean's files each run, so
build that card first (its gen/build.sh); writes ../video-6845-rev-b-clean-keyboard.kicad_sch, its sheet, and this
folder's symbol library and library tables.

What it does to Rev B-Clean's sheet (everything else is that sheet, wire for wire):
  * the names: the project, the title block (rev B-Clean-Keyboard), the libraries; the paper is wider, for the new part
  * J1, the bus connector, has the 36 pins of the new slots: the Eagle symbol k1_C30 with six more pins, k1_C36. Its
    pins 1-30 keep the 30-pin card's numbers (1 = +5V ... 30 = GND), where the copper is; 31-36 are the slot's
    positions beyond +5V (-EF1, -EF2, -EF3, -DMAIN, SC0, -PAUSE: Ken's slot order of 2026-11-18)
  * labels on pins of the old parts that the new section uses (keyboard.JOIN): the bus -MRD, the 6845's DE and VSYNC,
    the bus -EF and the three new flag lines
  * the 6845's -CS (IC3 pin 25) cut from the gate that drove it (IC5 pin 3): that gate's output is now -UPPER, the
    74HCT138's enable, and the 6845's -CS is the 74HCT138's first output, -CRTCCS
  * the 6845's R/W (IC3 pin 22) off -MRW and onto ground, its E (pin 23) off TPB and onto CRTE (keyboard.RELABEL)
  * the new parts (keyboard.PARTS), KiCad's own symbols, each unit placed to the right of the old drawing with a
    stub and a label on every connected pin and a no-connect mark on every open one (as VIDEO-G's
    kicad/common/make_schematic.py draws its cards)
Then it proves what it made: KiCad exports the netlist, and every net is compared with Rev B-Clean's netlist changed
by keyboard.py's tables. Any difference stops the build.
"""
import math, os, re, subprocess, sys, uuid

HERE = os.path.dirname(os.path.abspath(__file__)); DEST = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(DEST, "..", "..", "..", ".."))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(ROOT, "hardware", "video-g", "kicad", "common"))
import keyboard as K
import symlib

BASE = os.path.join(DEST, "..", "rev-b-clean")
OLD, NEW, LIB = K.OLD, K.NEW, K.LIB
CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
U = lambda *k: str(uuid.uuid5(uuid.NAMESPACE_URL, "s5-" + NEW + "/" + "/".join(map(str, k))))
G = 2.54
snap = lambda v: round(v / G) * G
F = '(effects (font (size 1.27 1.27))%s)'


def block(t, i):
    d = 0; ins = False; k = i
    while True:
        c = t[k]
        if ins:
            if c == "\\": k += 1
            elif c == '"': ins = False
        elif c == '"': ins = True
        elif c == "(": d += 1
        elif c == ")":
            d -= 1
            if d == 0: return t[i:k + 1]
        k += 1


def title(s, text, c1, c2):
    i = s.index("(title_block"); blk = block(s, i)
    return s[:i] + '(title_block (title "%s") (date "%s") (rev "%s") (comment 1 "%s") (comment 2 "%s"))' % (
        text, K.DATE, K.REV, c1, c2) + s[i + len(blk):]


def pin_ends(sheet):
    """{(reference, pin): (x, y)} for every pin of every symbol on the sheet: the symbol's place, mirror and turn applied
    to the pin's place in its library symbol (checked against the sheet: 366 of Rev B-Clean's pins end on a wire, label
    or mark, the other 62 being hidden supply pins and spare gates)"""
    ls = block(sheet, sheet.index("(lib_symbols")); lib = {}
    for m in re.finditer(r'\n\t\t\(symbol "([^"]+)"', ls):
        name = m.group(1); blk = block(ls, m.start() + 3); units = {}
        for sm in re.finditer(r'\(symbol "%s_(\d+)_(\d+)"' % re.escape(name.split(":")[-1]), blk):
            for pm in re.finditer(r'\(pin \w+ \w+ \(at ([-\d.]+) ([-\d.]+) \d+\) \(length [-\d.]+\).*?\(number "([^"]+)"', block(blk, sm.start()), re.S):
                units.setdefault(int(sm.group(1)), []).append((pm.group(3), float(pm.group(1)), float(pm.group(2))))
        lib[name] = units
    ends = {}
    for m in re.finditer(r'\n\t\(symbol \(lib_id "([^"]+)"\) \(at ([-\d.]+) ([-\d.]+) (\d+)\)(?: \(mirror (\w)\))? \(unit (\d+)\)', sheet):
        ref = re.search(r'\(property "Reference" "([^"]+)"', block(sheet, m.start() + 2)).group(1)
        X, Y, rot, mir, unit = float(m.group(2)), float(m.group(3)), int(m.group(4)), m.group(5), int(m.group(6))
        for num, px, py in lib.get(m.group(1), {}).get(unit, []) + lib.get(m.group(1), {}).get(0, []):
            if mir == "x": py = -py
            if mir == "y": px = -px
            a = math.radians(rot)
            ends[(ref, num)] = (round(X + px * math.cos(a) - py * math.sin(a), 2), round(Y - (px * math.sin(a) + py * math.cos(a)), 2))
    return ends


def fmt(v):
    return ("%.2f" % v).rstrip("0").rstrip(".")


def main():
    root = open(os.path.join(BASE, OLD + ".kicad_sch")).read().replace(OLD, NEW)
    sheet = open(os.path.join(BASE, OLD + "-sheet1.kicad_sch")).read().replace(OLD, NEW)
    symfile = open(os.path.join(BASE, OLD + "-eagle.kicad_sym")).read().replace(OLD, NEW)
    # (each of the two lines must fit the title block: about 80 characters)
    c1 = "Text card after BYTE, May 1979; key at 7802, status at 7804; made by gen/build.sh"
    c2 = "Rev B-Clean on the 36-pin bus with VIDEO-G's PS/2 keyboard section (README.md)"
    root = title(root, "System-5 6845 video Rev B-Clean-Keyboard", c1, c2)
    sheet = title(sheet, "System-5 6845 video Rev B-Clean-Keyboard, sheet 1", c1, c2)
    assert sheet.count('(paper "A2")') == 1
    sheet = sheet.replace('(paper "A2")', '(paper "User" 1160 420)')
    path = re.search(r'\(instances \(project "%s" \(path "([^"]+)"' % re.escape(NEW), sheet).group(1)

    # ---- J1: the 36-pin connector. Eagle's k1_C30 with six more pins, as k1_C36, in the sheet and in the library
    name30, name36 = LIB + ":k1_C30", LIB + ":k1_C36"
    ls_at = sheet.index("(lib_symbols"); ls = block(sheet, ls_at)
    i = ls.index('(symbol "%s"' % name30); d30 = block(ls, i)
    pins = {m.group(3): (float(m.group(1)), float(m.group(2)), m.group(0))
            for m in re.finditer(r'\(pin \w+ \w+ \(at ([-\d.]+) ([-\d.]+) \d+\) \(length [-\d.]+\)[^\n]*\(number "([^"]+)"[^\n]*', d30)}
    assert len(pins) == 30, len(pins)
    (x1, y1, line1), (x2, y2, _) = pins["1"], pins["2"]
    # the six new pins on the symbol's other side, opposite pins 1-6 (beyond pin 1, on the pins' own side, the sheet has
    # the +5V wire: a pin there would be on +5V). Checked below: nothing on the sheet touches where they end
    assert abs(y1 - y2) < 0.01 and re.search(r"\(at [-\d.]+ [-\d.]+ 270\)", line1), "J1's pins are not where this expects them"
    extra = []
    for k, (num, name) in enumerate(sorted(K.J1_NEW.items())):
        px, py = x1 + (x2 - x1) * k, -y1
        new = re.sub(r'\(at [-\d.]+ [-\d.]+ \d+\)', '(at %s %s 90)' % (fmt(px), fmt(py)), line1, count=1)
        new = re.sub(r'\(name "[^"]*"', '(name "%s"' % name, new, count=1)
        new = re.sub(r'\(number "[^"]*"', '(number "%s"' % num, new, count=1)
        new = re.sub(r'^\(pin \w+ ', '(pin passive ', new, count=1)       # (pin 1 is the +5V supply pin: these are not)
        extra.append(new)
    assert "\n" not in line1                            # a pin is one line here
    d36 = d30.replace(line1, line1 + "".join("\n\t\t\t\t" + e for e in extra), 1).replace("k1_C30", "k1_C36").replace(LIB + ':C30"', LIB + ':C36"')
    ls = ls[:i] + d30 + "\n\t\t" + d36 + ls[i + len(d30):]
    sheet = sheet[:ls_at] + ls + sheet[ls_at + len(block(sheet, ls_at)):]
    j = sheet.index('(symbol (lib_id "%s")' % name30); inst = block(sheet, j)
    assert '(property "Reference" "J1"' in inst
    new_inst = inst.replace(name30, name36, 1)
    assert new_inst.count(LIB + ':C30"') == 1
    new_inst = new_inst.replace(LIB + ':C30"', LIB + ':C36"')       # its footprint: gen/footprints.py makes it
    assert new_inst.count('"System-5 bus 30-pin"') == 1
    new_inst = new_inst.replace('"System-5 bus 30-pin"', '"System-5 bus 36-pin"')      # its value, as the board's J1 has it
    k = new_inst.index("(instances")
    new_inst = new_inst[:k] + "".join('(pin "%s" (uuid "%s"))\n\t\t' % (n, U("J1", n)) for n in sorted(K.J1_NEW)) + new_inst[k:]
    sheet = sheet[:j] + new_inst + sheet[j + len(inst):]
    bare = d36.replace(name36, "k1_C36", 1)             # the same symbol for the library file (no library prefix there)
    k = symfile.rindex(")")
    symfile = symfile[:k].rstrip() + "\n\t" + bare.replace("\n\t\t", "\n\t") + "\n)\n"

    ends = pin_ends(sheet)
    for num in K.J1_NEW:                                # the new pins end on bare sheet
        x, y = ends[("J1", num)]
        for m in re.finditer(r'\(wire \(pts \(xy ([-\d.]+) ([-\d.]+)\) \(xy ([-\d.]+) ([-\d.]+)\)', sheet):
            ax, ay, bx, by = map(float, m.groups())
            assert not (min(ax, bx) - 0.01 <= x <= max(ax, bx) + 0.01 and min(ay, by) - 0.01 <= y <= max(ay, by) + 0.01
                        and (abs(ax - bx) < 0.01 or abs(ay - by) < 0.01)), "J1 pin %s ends on a wire at (%s, %s)" % (num, x, y)
    wire_re = r'\t\(wire \(pts \(xy ([-\d.]+) ([-\d.]+)\) \(xy ([-\d.]+) ([-\d.]+)\)\)[^\n]*\n'
    same = lambda a, b: abs(a[0] - b[0]) < 0.01 and abs(a[1] - b[1]) < 0.01
    body = []

    def label(net, x, y, tag, ang=0):
        just = {0: "left", 180: "right", 90: "left", 270: "right"}[ang]
        body.append('\t(label "%s" (at %s %s %d) (fields_autoplaced yes) (effects (font (size 1.27 1.27)) (justify %s bottom)) (uuid "%s"))'
                    % (net, fmt(x), fmt(y), ang, just, U("l", tag)))

    # ---- the 6845's -CS cut from IC5's gate: the wire into the pin goes; -CRTCCS on the pin, -UPPER on what is left
    cs = ends[K.CUT]
    hit = [m for m in re.finditer(wire_re, sheet) if same((float(m.group(1)), float(m.group(2))), cs) or same((float(m.group(3)), float(m.group(4))), cs)]
    assert len(hit) == 1, len(hit)
    m = hit[0]; a, b = (float(m.group(1)), float(m.group(2))), (float(m.group(3)), float(m.group(4)))
    other = b if same(a, cs) else a
    sheet = sheet[:m.start()] + sheet[m.end():]
    label("-UPPER", other[0], other[1], "upper")

    # ---- labels on the old parts' pins that the new section uses; a no-connect mark there goes
    for (ref, pin), net in sorted(K.JOIN.items()):
        x, y = ends[(ref, pin)]
        mark = '\t(no_connect (at %s %s)' % (fmt(x), fmt(y))
        if mark in sheet:
            k = sheet.index(mark); sheet = sheet[:k] + sheet[sheet.index("\n", k) + 1:]
        label(net, x, y, "join-%s-%s" % (ref, pin))
    # ---- the pins of old parts that change net: the label at the far end of the pin's own wire goes
    relabelled = []
    for (ref, pin), (old_label, net) in sorted(K.RELABEL.items()):
        e = ends[(ref, pin)]
        hit = [m for m in re.finditer(wire_re, sheet) if same((float(m.group(1)), float(m.group(2))), e) or same((float(m.group(3)), float(m.group(4))), e)]
        assert len(hit) == 1, (ref, pin, len(hit))
        m = hit[0]; a, b = (float(m.group(1)), float(m.group(2))), (float(m.group(3)), float(m.group(4)))
        far = b if same(a, e) else a
        head = '\t(label "%s" (at %s %s ' % (old_label, fmt(far[0]), fmt(far[1]))
        assert sheet.count(head) == 1, head
        k = sheet.index(head); sheet = sheet[:k] + sheet[sheet.index("\n", k) + 1:]
        relabelled.append((net, far[0], far[1], "relabel-%s-%s" % (ref, pin)))
        if net != "GND": label(net, far[0], far[1], relabelled[-1][3])
    for num in sorted(K.J1_NEW):                        # the connector's positions this card leaves open
        if ("J1", num) not in K.JOIN:
            x, y = ends[("J1", num)]
            body.append('\t(no_connect (at %s %s) (uuid "%s"))' % (fmt(x), fmt(y), U("nc", "J1", num)))

    # ---- the new parts: each unit of each symbol in rows to the right of the old drawing
    libs = {}; pwr = [0]

    def prop(k, v, x, y, hide=False):
        return '\t\t(property "%s" "%s" (at %.2f %.2f 0) %s)' % (k, v, x, y, F % (" (hide yes)" if hide else ""))

    def power(net, x, y, tag):
        lib_id = "power:" + net; libs[lib_id] = symlib.symbol(lib_id)
        pwr[0] += 1; ref = "#PWR%03d" % pwr[0]
        yv = y - 3.81 if net != "GND" else y + 5.08
        body.append('\t(symbol (lib_id "%s") (at %.2f %.2f 0) (unit 1)\n\t\t(exclude_from_sim no) (in_bom no) (on_board no) (dnp no) (uuid "%s")\n%s\n%s\n%s\n%s\n'
                    '\t\t(pin "1" (uuid "%s"))\n\t\t(instances (project "%s" (path "%s" (reference "%s") (unit 1))))\n\t)'
                    % (lib_id, x, y, U("pwr", tag), prop("Reference", ref, x, y, True), prop("Value", net, x, yv),
                       prop("Footprint", "", x, y, True), prop("Datasheet", "", x, y, True), U("pwr", tag, "pin"), NEW, path, ref))

    for net, x, y, tag in relabelled:
        if net == "GND": power(net, x, y, tag)

    LABEL_ROOM = 22.86; X0, WIDTH = 570.0, 1140.0
    cells = []
    for ref, (value, lib_id, fp, note) in K.PARTS.items():
        P = symlib.pins(lib_id); us = [u for u in symlib.units(lib_id) if u != 0] or [0]
        for unit in us:
            up = [p for p in P.values() if p.unit in (unit, 0)]
            xs = [p.x for p in up] or [0]; ys = [p.y for p in up] or [0]
            cells.append((ref, unit, lib_id, up, min(xs), max(ys), (max(xs) - min(xs)) + 2 * LABEL_ROOM + 10, (max(ys) - min(ys)) + 15))
    x, y, rowh, place = X0, 30.0, 0, []
    for ref, unit, lib_id, up, minx, maxy, w, h in cells:
        if x + w > WIDTH:
            x = X0; y += rowh + 8; rowh = 0
        place.append((ref, unit, lib_id, up, snap(x + LABEL_ROOM + 5 - minx), snap(y + 10 + maxy)))
        x += w; rowh = max(rowh, h)
    assert y + rowh < 400, "the new parts run off the sheet"
    for ref, unit, lib_id, up, X, Y in place:
        value, _, fp, note = K.PARTS[ref]
        own = lib_id.startswith("video-g-local:")       # VIDEO-G's own symbol (the mini-DIN): this card's library has a copy
        use = LIB + ":" + lib_id.split(":")[1] if own else lib_id
        text = symlib.symbol(lib_id)
        if own:
            text = text.replace('(symbol "%s"' % lib_id, '(symbol "%s"' % use, 1)
            bare_name = lib_id.split(":")[1]
            if '(symbol "%s"' % bare_name not in symfile:
                k = symfile.rindex(")")
                symfile = symfile[:k].rstrip() + "\n\t" + text.replace('(symbol "%s"' % use, '(symbol "%s"' % bare_name, 1) + "\n)\n"
        libs[use] = text
        top = max([p.y for p in up] or [0]); bot = min([p.y for p in up] or [0])
        body.append('\t(symbol (lib_id "%s") (at %.2f %.2f 0) (unit %d)\n\t\t(exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no) (uuid "%s")\n%s\n%s\n%s\n%s\n%s\n'
                    '\t\t(instances (project "%s" (path "%s" (reference "%s") (unit %d))))\n\t)'
                    % (use, X, Y, max(unit, 1), U(ref, unit), prop("Reference", ref, X, Y - top - 2.54), prop("Value", value, X, Y - bot + 2.54),
                       prop("Footprint", fp, X, Y, True), prop("Datasheet", "", X, Y, True),
                       "\n".join('\t\t(pin "%s" (uuid "%s"))' % (p.number, U(ref, p.number)) for p in up), NEW, path, ref, max(unit, 1)))
        for p in up:
            net = K.PINS.get(ref, {}).get(p.number)
            cx, cy = X + p.x, Y - p.y                   # a symbol's y runs up, the sheet's down
            if net is None:
                if not p.hidden:
                    body.append('\t(no_connect (at %.2f %.2f) (uuid "%s"))' % (cx, cy, U(ref, p.number, "nc")))
                continue
            d = {0: (-1, 0), 180: (1, 0), 90: (0, 1), 270: (0, -1)}[p.angle]     # the stub leaves the pin away from the body
            ex, ey = cx + G * d[0], cy + G * d[1]
            body.append('\t(wire (pts (xy %.2f %.2f) (xy %.2f %.2f)) (stroke (width 0) (type default)) (uuid "%s"))' % (cx, cy, ex, ey, U(ref, p.number, "w")))
            if net in ("VCC", "GND"):
                power(net, ex, ey, ref + "." + p.number)
            else:
                la = {(-1, 0): 180, (1, 0): 0, (0, 1): 270, (0, -1): 90}[d]
                label(net, ex, ey, "%s.%s" % (ref, p.number), la)
    notes = ["KEYBOARD SECTION (Rev B-Clean-Keyboard, 2026-11-20): VIDEO-G TEXT's, memory-mapped. 7800/7801 the 6845, 7802 the key, 7804 status",
             "(bit 0 KEY-READY, 2 VSYNC, 3 DE, 7-6 = 10). IC15 is enabled by -UPPER (block and A11, Rev B's old -CS for the 6845) and A10 low.",
             "KEY-READY also pulls a bus flag line low through IC22 (7416, open collector): JP1 picks -EF1, -EF2, -EF3 or -EF. See gen/keyboard.py."]
    for n, line in enumerate(notes):
        body.append('\t(text "%s" (exclude_from_sim no) (at %.0f %.2f 0) (effects (font (size 2.0 2.0)) (justify left bottom)) (uuid "%s"))'
                    % (line, X0, 17 + 3.2 * n, U("note", n)))       # (inside the frame, above the first row of parts)
    # the new symbols' definitions into the sheet
    ls_at = sheet.index("(lib_symbols"); ls = block(sheet, ls_at)
    add = "".join("\t\t" + libs[k].replace("\n", "\n\t\t") + "\n" for k in sorted(libs))
    sheet = sheet[:ls_at] + ls[:-1].rstrip() + "\n" + add + "\t)" + sheet[ls_at + len(ls):]
    k = sheet.rfind("\t(sheet_instances")
    if k < 0:
        k = sheet.rfind(")")
    sheet = sheet[:k] + "\n".join(body) + "\n" + sheet[k:]

    open(os.path.join(DEST, NEW + ".kicad_sch"), "w").write(root)
    open(os.path.join(DEST, NEW + "-sheet1.kicad_sch"), "w").write(sheet)
    open(os.path.join(DEST, NEW + "-eagle.kicad_sym"), "w").write(symfile)
    for table in ("fp-lib-table", "sym-lib-table"):
        open(os.path.join(DEST, table), "w").write(open(os.path.join(BASE, table)).read().replace(OLD, NEW))
    import json
    pro = json.loads(open(os.path.join(BASE, OLD + ".kicad_pro")).read().replace(OLD, NEW))
    # the tracks Freerouting adds: 0.254 mm as all of Rev B's, the supplies 0.5 mm; vias 0.8 / 0.4 mm. (Rev B's project
    # carried the converter's class, 0.15 mm tracks and 0.46 mm vias, which nothing on the board uses.) The minimum
    # rules stay Rev B's, which its own copper keeps to.
    base = dict(pro["net_settings"]["classes"][0]); base.update(track_width=0.254, clearance=0.2, via_diameter=0.8, via_drill=0.4)
    power = dict(base); power.update(name="Power", track_width=0.5)
    pro["net_settings"]["classes"] = [base, power]
    pro["net_settings"]["netclass_patterns"] = [{"netclass": "Power", "pattern": "VCC"}, {"netclass": "Power", "pattern": "GND"}]
    open(os.path.join(DEST, NEW + ".kicad_pro"), "w").write(json.dumps(pro, indent=2) + "\n")
    units = len(place)
    print("schematic: Rev B-Clean's + J1 with 36 pins, the 6845's -CS through IC15, %d new parts (%d units, %d supply symbols)"
          % (len(K.PARTS), units, pwr[0]))

    # ---- the proof: KiCad's netlist of what was written against Rev B-Clean's netlist changed by keyboard.py
    os.makedirs(os.path.join(DEST, "reports"), exist_ok=True)
    out = os.path.join(DEST, "reports", "netlist.net")
    subprocess.run([CLI, "sch", "export", "netlist", "-o", out, os.path.join(DEST, NEW + ".kicad_sch")], capture_output=True)

    def nets(p):
        s = open(p, encoding="utf-8").read(); r = {}
        for name, b in re.findall(r'\(net\s+\(code "\d+"\)\s+\(name "([^"]+)"\)(.*?)(?=\n\t\t\(net\s|\n\t\)\n\))', s, re.S):
            r[name] = set(re.findall(r'\(node\s+\(ref "([^"]+)"\)\s+\(pin "([^"]+)"\)', b))
        return r
    base = nets(os.path.join(BASE, "reports", "netlist.net")); got = nets(out)
    want = {n: set(v) for n, v in base.items()}
    of = lambda node: next(n for n, v in want.items() if node in v)
    cs_net = of(K.CUT); want[cs_net].discard(K.CUT); assert want[cs_net] == {K.UPPER}, want[cs_net]
    want["-UPPER"] = want.pop(cs_net)
    def named(label):                                   # the net a label on the sheet names
        for cand in (label, "/Sheet 1/" + label):
            if cand in want: return cand
        want[label] = set(); return label
    for node, (_, net) in K.RELABEL.items():
        want[of(node)].discard(node); want[named(net)].add(node)
    for node, net in K.JOIN.items():
        if node == K.CUT or node[0] == "J1" and node[1] in K.J1_NEW:
            named(net); want[named(net)].add(node); continue
        old = of(node); new = named(net)
        if old != new:
            want[new] |= want.pop(old)
    for ref, pins_ in K.PINS.items():
        for pin, net in pins_.items():
            want[named(net)].add((ref, pin))
    multi = lambda d: {frozenset(v) for v in d.values() if len(v) > 1}
    if multi(want) != multi(got):
        w, g = multi(want), multi(got)
        for grp in sorted(w - g, key=sorted)[:8]:
            near = max(g - w, key=lambda x: len(x & grp), default=frozenset())
            print("  wanted, not made: %d pins %s...; nearest made net lacks %s and has besides %s" % (
                len(grp), sorted(grp)[:4], sorted(grp - near)[:12], sorted(near - grp)[:12]))
        raise SystemExit("make_schematic.py: the netlist is not Rev B-Clean's with the keyboard section")
    print("netlist: %d nets of two pins or more (Rev B-Clean: %d), each as Rev B-Clean's changed by gen/keyboard.py"
          % (len(multi(got)), len(multi(base))))


if __name__ == "__main__":
    main()
