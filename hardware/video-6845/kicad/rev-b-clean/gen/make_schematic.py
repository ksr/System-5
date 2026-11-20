#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-20
"""make_schematic.py - Rev B-Clean's schematic: Rev B's (../rev-b/video-6845-rev-b*.kicad_sch, converted from the 2005
Eagle drawing and proven against the board) without the DB9. Ken, 2026-11-20: "a clean version of current video card,
no need for db9, composite only ... a cleanup with minimal to no changes to circuit. Lets call this Rev B-Clean";
and the same day, asked about the 6845's open light-pen input: "Yes tie light pen to gnd".
Starts from Rev B's files each run; writes ../video-6845-rev-b-clean.kicad_sch, its sheet, and this folder's copy of
the symbol library.

What changes from Rev B (everything else is Rev B's, wire for wire):
  * the names: project video-6845-rev-b-clean, the title block (rev B-Clean), the libraries
    (video-6845-rev-b-clean-eagle); the bus connector U$1 (Eagle's name) is J1 and the RCA jack U$4 is J2
  * SV1's value is "ADDRESS BLOCK 2x4" (it was "2x4 header"): the same 2 x 4 header, named for what it sets
  * the 6845's light-pen strobe input (IC3 pin 3, LPSTB; Eagle's symbol calls it LPSTD) is tied to ground: a ground
    symbol on the pin, where Rev B has a no-connect mark. The one change to the circuit. Open, as BYTE and the 2005
    drawing have it, the NMOS part's input floats
  * X1, the DB9, is gone: its nine one-pin symbols, the no-connect marks on its five unused pins, and nothing else. It
    carried three signals that all go on to other parts (the 7416's video on pin 7, which still feeds the RCA jack
    through R5; the 6845's VSYNC on pin 9 and HSYNC on pin 8, which still feed the 7416) and ground on pin 1, so no
    net loses anything but its DB9 pin. The wires that ran only to it go too.
"""
import os, re, uuid

HERE = os.path.dirname(os.path.abspath(__file__)); DEST = os.path.dirname(HERE)
REVB = os.path.join(DEST, "..", "rev-b")
OLD, NEW = "video-6845-rev-b", "video-6845-rev-b-clean"
DATE, REV = "2026-11-20", "B-Clean"
RENAME = {"U$1": "J1", "U$4": "J2"}
GONE = "X1"
SV1_VALUE = "ADDRESS BLOCK 2x4"
LPSTB = (406.4, 252.73)                                  # the end of IC3's pin 3 on the sheet (mm)
U = lambda *k: str(uuid.uuid5(uuid.NAMESPACE_URL, "s5-video-6845-rev-b-clean/" + "/".join(k)))


def block_at(s, i):
    d = 0
    for k in range(i, len(s)):
        if s[k] == "(":
            d += 1
        elif s[k] == ")":
            d -= 1
            if d == 0:
                return s[i:k + 1]


def title(s, text, c1, c2):
    i = s.index("(title_block"); blk = block_at(s, i)
    new = '(title_block (title "%s") (date "%s") (rev "%s") (comment 1 "%s") (comment 2 "%s"))' % (text, DATE, REV, c1, c2)
    return s[:i] + new + s[i + len(blk):]


def main():
    root = open(os.path.join(REVB, OLD + ".kicad_sch")).read().replace(OLD, NEW)
    sheet = open(os.path.join(REVB, OLD + "-sheet1.kicad_sch")).read().replace(OLD, NEW)
    c1 = "64 x 16 text card (BYTE, May 1979), composite out; KiCad master - edit in KiCad"
    c2 = "Rev B (Ken's working card, 2005) without the DB9, 2026-11-20; see README.md"
    root = title(root, "System-5 6845 video Rev B-Clean", c1, c2)
    sheet = title(sheet, "System-5 6845 video Rev B-Clean, sheet 1", c1, c2)
    for old, new in RENAME.items():
        n = sheet.count('(property "Reference" "%s"' % old)
        assert n >= 1, old
        sheet = sheet.replace('(property "Reference" "%s"' % old, '(property "Reference" "%s"' % new)
        sheet = sheet.replace('(reference "%s")' % old, '(reference "%s")' % new)
    # SV1's value says what it is for: the board prints each part's reference with its value ("SV1 ADDRESS BLOCK")
    i = sheet.index('(property "Reference" "SV1"'); j = sheet.index('(property "Value" "', i)
    assert sheet[j:j + 40].startswith('(property "Value" "2x4 header"'), sheet[j:j + 40]
    sheet = sheet[:j] + '(property "Value" "%s"' % SV1_VALUE + sheet[j + len('(property "Value" "2x4 header"'):]
    # the DB9: every symbol whose reference is X1, and where each one's pin ended (to find the no-connect marks there)
    gone = 0; ends = []
    while True:
        i = sheet.find('(property "Reference" "%s"' % GONE)
        if i < 0:
            break
        j = sheet.rfind("\t(symbol (lib_id", 0, i); blk = block_at(sheet, j + 1)
        at = re.search(r'\(at ([-\d.]+) ([-\d.]+)', blk); ends.append((float(at.group(1)), float(at.group(2))))
        sheet = sheet[:j] + sheet[j + 1 + len(blk):].lstrip("\n"); gone += 1
    assert gone == 9, gone
    # a no-connect mark within one pin's length (5.08 mm) of a removed symbol belonged to it
    marks = 0
    for m in list(re.finditer(r'\t\(no_connect \(at ([-\d.]+) ([-\d.]+)\)[^\n]*\n', sheet))[::-1]:
        x, y = float(m.group(1)), float(m.group(2))
        if any((abs(x - ex) <= 7.7 and abs(y - ey) <= 0.01) or (abs(y - ey) <= 7.7 and abs(x - ex) <= 0.01)
               for ex, ey in ends):                   # (the symbols stand upright: the pin runs along y)
            sheet = sheet[:m.start()] + sheet[m.end():]; marks += 1
    assert marks == 5, marks
    # the wires that ran to its four used pins (ground, video, HSYNC, VSYNC): each pin ended 2.54 mm from its symbol;
    # take away the wire that ends there, and then any wire left with an end on nothing, until none is
    def wires(text):
        return [(m.start(), m.end(), (float(m.group(1)), float(m.group(2))), (float(m.group(3)), float(m.group(4))))
                for m in re.finditer(r'\t\(wire \(pts \(xy ([-\d.]+) ([-\d.]+)\) \(xy ([-\d.]+) ([-\d.]+)\)\)[^\n]*\n', text)]
    same = lambda a, b: abs(a[0] - b[0]) < 0.01 and abs(a[1] - b[1]) < 0.01
    loose = [(ex, ey - 2.54) for ex, ey in ends]; cut = 0
    while loose:
        pt = loose.pop(); ws = wires(sheet)
        hit = [w for w in ws if same(w[2], pt) or same(w[3], pt)]
        if len(hit) != 1:                                  # nothing ends here, or a junction of others: leave it
            continue
        a, b, p0, p1 = hit[0]; other = p1 if same(p0, pt) else p0
        sheet = sheet[:a] + sheet[b:]; cut += 1
        rest = [w for w in wires(sheet) if same(w[2], other) or same(w[3], other)]
        on_wire = any(min(w[2][0], w[3][0]) - 0.01 <= other[0] <= max(w[2][0], w[3][0]) + 0.01 and
                      min(w[2][1], w[3][1]) - 0.01 <= other[1] <= max(w[2][1], w[3][1]) + 0.01 and
                      (abs(w[2][0] - w[3][0]) < 0.01 or abs(w[2][1] - w[3][1]) < 0.01) for w in wires(sheet))
        if len(rest) == 1 and not re.search(r'\((?:label|global_label|junction|no_connect)[^\n]*\(at %g %g' % other, sheet):
            loose.append(other)                            # that end now hangs too
    # the 6845's light-pen input to ground: the no-connect mark at the pin's end goes, and a ground symbol (Eagle's, as
    # the sheet's others) lies there, turned so that its bars point away from the chip between the neighbouring pins' wires
    mark = '\t(no_connect (at %g %g)' % LPSTB
    assert sheet.count(mark) == 1, mark
    i = sheet.index(mark); j = sheet.index("\n", i) + 1
    sheet = sheet[:i] + sheet[j:]
    n = max(int(k) for k in re.findall(r'\(reference "#[A-Z+]*(\d+)"\)', sheet)) + 1
    path = re.search(r'\(instances \(project "%s" \(path "([^"]+)"' % NEW, sheet).group(1)
    x, y = LPSTB[0] - 2.54, LPSTB[1]                    # turned 270: its pin's end is 2.54 mm to the right of its origin
    gnd = ('\t(symbol (lib_id "%s-eagle:supply1_GND") (at %g %g 270) (unit 1)\n'
           '\t\t(exclude_from_sim no) (in_bom no) (on_board no) (dnp no) (uuid "%s")\n'
           '\t\t(property "Reference" "#GND%d" (at %g %g 0) (effects (font (size 1.27 1.27)) (hide yes)))\n'
           '\t\t(property "Value" "GND" (at %g %g 0) (effects (font (size 1.778 1.778) (thickness 0.1422)) (justify right bottom)))\n'
           '\t\t(property "Footprint" "" (at %g %g 0) (effects (font (size 1.27 1.27)) (hide yes)))\n'
           '\t\t(property "Datasheet" "" (at %g %g 0) (effects (font (size 1.27 1.27)) (hide yes)))\n'
           '\t\t(pin "1" (uuid "%s"))\n'
           '\t\t(instances (project "%s" (path "%s" (reference "#GND%d") (unit 1))))\n\t)\n'
           % (NEW, x, y, U("lpstb-gnd"), n, x, y, x - 3.2, y + 0.9, x, y, x, y, U("lpstb-gnd", "pin"), NEW, path, n))
    k = sheet.rfind("\t(sheet_instances")
    if k < 0:
        k = sheet.rfind(")")
    sheet = sheet[:k] + gnd + sheet[k:]
    open(os.path.join(DEST, NEW + ".kicad_sch"), "w").write(root)
    open(os.path.join(DEST, NEW + "-sheet1.kicad_sch"), "w").write(sheet)
    open(os.path.join(DEST, NEW + "-eagle.kicad_sym"), "w").write(         # (its symbols name their footprints' library)
        open(os.path.join(REVB, OLD + "-eagle.kicad_sym")).read().replace(OLD, NEW))
    for table in ("fp-lib-table", "sym-lib-table"):
        open(os.path.join(DEST, table), "w").write(open(os.path.join(REVB, table)).read().replace(OLD, NEW))
    print("schematic: Rev B's without X1 (9 symbols, %d no-connect marks, %d wires); U$1 is J1, U$4 is J2; IC3 pin 3 on ground" % (marks, cut))


if __name__ == "__main__":
    main()
