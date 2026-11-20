#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-18
"""make_schematic.py - Rev F's schematic: Rev E's (memory-rev-e*.kicad_sch, converted from Eagle) with the EEPROM sockets
(Ken, 2026-11-18: "yes put in Rev F"; BACKLOG of 2026-10-30), so the 1802 can rewrite its own ROM. Starts from Rev E's
files each run; writes ../memory-rev-f.kicad_sch and ../memory-rev-f-sheet1.kicad_sch.

What changes from Rev E (everything else is Rev E's, and Rev D's netlist):
  * the names: project memory-rev-f, the title block, the bus connector U$1 (Eagle's name) is J1
  * IC3 (EPROM LO) and IC5 (EPROM HI), 27C256 sockets until now with pin 1 (VPP) on VCC and pin 27 on BUFFADDR14 (the
    latched A14), get those two pins from a jumper block each, JP2 (IC3) and JP1 (IC5), a 2 x 3 header:
        pin 1 VCC     pin 2 BUFFADDR14
        pin 3 P1_x    pin 4 P27_x          (P1_x to the socket's pin 1, P27_x to its pin 27)
        pin 5 BUFFADDR14  pin 6 WR         (WR: the buffered write strobe, the RAMs' !WE)
    27C256: shunts on 1-3 and 2-4 (pin 1 VCC, pin 27 A14: Rev E). 28C256 (pin 1 A14, pin 27 !WE): a shunt on 3-5, and
    on 4-6 to let the CPU write it; without the 4-6 shunt R7 (IC3) / R6 (IC5), 47k to VCC, holds !WE high: read-only,
    so stray writes and ELF/OS's memory probe cannot change the ROM. 47k, not 10k: with a 27C256 the shunt on 2-4 puts
    the pull-up on A14, which a CD4042B output drives (rated about 0.5 mA at a valid low); two 10k would draw 0.9 mA,
    two 47k draw 0.2 mA, and a 28C256's !WE leaks at most 10 uA (0.5 V across 47k). A 27C256 must never get A14 on
    its pin 1 (VPP low: Rev B's misread fault), so the 27C256 setting is the default and the board says which shunts
    go where
  * the sockets' value reads 27C256/28C256
"""
import os, re, uuid

HERE = os.path.dirname(os.path.abspath(__file__)); DEST = os.path.dirname(HERE)
REVE = os.path.join(DEST, "..", "rev-e")
KSYM = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols"
ROOT_UUID, SHEET_UUID = "345c2e3e-e3a5-5221-490e-63bd507252b7", "ded27693-450f-1111-c0f5-fc2205799b35"
PATH = "/%s/%s" % (ROOT_UUID, SHEET_UUID)
U = lambda *k: str(uuid.uuid5(uuid.NAMESPACE_URL, "s5-memory-rev-f/" + "/".join(k)))

# the jumper blocks and pull-ups: ref -> (socket, its pin-1 net, its pin-27 net, pull-up)
SOCKETS = {"JP1": ("IC5", "P1_HI", "P27_HI", "R6"), "JP2": ("IC3", "P1_LO", "P27_LO", "R7")}
# where Rev E has each socket's pin 1 supply symbol and pin 27 label (sheet mm), from its schematic
PIN1_SUPPLY = {"IC3": ("#V7", (345.44, 281.94)), "IC5": ("#V8", (490.22, 276.86))}
PIN27_LABEL = {"IC3": (317.5, 264.16), "IC5": (462.28, 259.08)}


def block_at(s, i):
    d = 0
    for k in range(i, len(s)):
        if s[k] == "(":
            d += 1
        elif s[k] == ")":
            d -= 1
            if d == 0:
                return s[i:k + 1]


def symbol_block(s, ref):
    i = s.find('(property "Reference" "%s"' % ref)
    j = s.rfind("\t(symbol (lib_id", 0, i)
    blk = block_at(s, j)
    return j, j + len(blk)


def libsym(lib, name, prefix):
    s = open(os.path.join(KSYM, lib + ".kicad_sym")).read()
    blk = block_at(s, s.find('(symbol "%s"' % name))
    return blk.replace('(symbol "%s"' % name, '(symbol "%s:%s"' % (prefix, name), 1)


def main():
    root = open(os.path.join(REVE, "memory-rev-e.kicad_sch")).read()
    sheet = open(os.path.join(REVE, "memory-rev-e-sheet1.kicad_sch")).read()
    title = ('(title_block (title "System-5 Memory Rev F (MEM3-F)") (date "2026-11-18") (rev "F") (comment 1 "64K RAM/EPROM '
             'card, KiCad master - edit in KiCad") (comment 2 "Rev E (MEM3-E) with EEPROM sockets (JP1, JP2: 27C256 or '
             '28C256) and its silkscreen fixed, 2026-11-18; see README.md"))')
    for name in ("root", "sheet"):
        s = root if name == "root" else sheet
        s = s.replace("memory-rev-e", "memory-rev-f")
        s = re.sub(r'\(title_block \(title "System-5 Memory Rev E \(MEM3-E\)"\)[^\n]*\)\)', title, s, count=1)
        if name == "root": root = s
        else: sheet = s
    sheet = sheet.replace('(property "Reference" "U$1"', '(property "Reference" "J1"').replace('(reference "U$1")', '(reference "J1")')

    # 1. the sockets' pin 27: Rev E's BUFFADDR14 label becomes P27_x; pin 1: its VCC symbol goes, a P1_x label in its place
    body = []
    for jp, (ic, p1, p27, r) in SOCKETS.items():
        x, y = PIN27_LABEL[ic]
        pat = '(label "BUFFADDR14" (at %g %g 0)' % (x, y)
        assert sheet.count(pat) == 1, (ic, pat)
        sheet = sheet.replace(pat, '(label "%s" (at %g %g 0)' % (p27, x, y))
        ref, (x, y) = PIN1_SUPPLY[ic]
        a, b = symbol_block(sheet, ref)
        assert "supply2_VCC" in sheet[a:b], ref
        sheet = sheet[:a] + sheet[b:].lstrip("\n")
        body.append('\t(label "%s" (at %g %g 270) (fields_autoplaced yes) (effects (font (size 1.778 1.778)) (justify right bottom)) (uuid "%s"))'
                    % (p1, x, y, U("p1", ic)))
    # the values: either part fits
    for ic in ("IC3", "IC5"):
        a, b = symbol_block(sheet, ic)
        blk = sheet[a:b]
        nb = re.sub(r'\(property "Value" "27256"', '(property "Value" "27C256/28C256"', blk, count=1)
        assert nb != blk, ic
        sheet = sheet[:a] + nb + sheet[b:]

    # 2. the new symbols' definitions: KiCad's 2 x 3 header; Rev E's own resistor and VCC symbols serve as they are
    i = sheet.find("(lib_symbols")
    blk = block_at(sheet, i)
    hdr = libsym("Connector_Generic", "Conn_02x03_Odd_Even", "Connector_Generic")
    sheet = sheet[:i] + blk[:-1] + "\t" + hdr.replace("\n", "\n\t\t") + "\n\t)" + sheet[i + len(blk):]

    # 3. JP1, JP2, R6, R7 below the drawing (sheet y 372-392), each pin on a short wire to its label or VCC symbol
    nv = max(int(n) for n in re.findall(r'\(reference "#V(\d+)"\)', sheet))
    def prop(k, v, x, y, hide=False):
        return '\t\t(property "%s" "%s" (at %g %g 0) (effects (font (size 1.778 1.778))%s))' % (k, v, x, y, " (hide yes)" if hide else "")
    def instance(ref, lib, x, y, value, fp, pins, bom=True):
        return ('\t(symbol (lib_id "%s") (at %g %g 0) (unit 1)\n\t\t(exclude_from_sim no) (in_bom %s) (on_board %s) (dnp no) (uuid "%s")\n%s\n%s\n%s\n%s\n%s\n'
                '\t\t(instances (project "memory-rev-f" (path "%s" (reference "%s") (unit 1))))\n\t)'
                % (lib, x, y, "yes" if bom else "no", "yes" if bom else "no", U("sym", ref), prop("Reference", ref, x, y - 6.0),
                   prop("Value", value, x, y + 6.5), prop("Footprint", fp, x, y, True), prop("Datasheet", "", x, y, True),
                   "\n".join('\t\t(pin "%s" (uuid "%s"))' % (p, U("pin", ref, p)) for p in pins), PATH, ref))
    def vcc(x, y, tag):
        nonlocal nv
        nv += 1; ref = "#V%d" % nv
        return ('\t(symbol (lib_id "memory-rev-d-eagle:supply2_VCC") (at %g %g 0) (unit 1)\n\t\t(exclude_from_sim no) (in_bom no) (on_board no) (dnp no) (uuid "%s")\n'
                '%s\n%s\n%s\n%s\n\t\t(pin "1" (uuid "%s"))\n\t\t(instances (project "memory-rev-f" (path "%s" (reference "%s") (unit 1))))\n\t)'
                % (x, y - 2.54, U("vcc", tag), prop("Reference", ref, x, y - 2.54, True), prop("Value", "VCC", x, y - 6.0),
                   prop("Footprint", "", x, y, True), prop("Datasheet", "", x, y, True), U("vcc", tag, "pin"), PATH, ref))
    def wire(x1, y1, x2, y2, tag):
        return '\t(wire (pts (xy %g %g) (xy %g %g)) (stroke (width 0) (type default)) (uuid "%s"))' % (x1, y1, x2, y2, U("w", tag))
    def label(net, x, y, left, tag):
        return '\t(label "%s" (at %g %g %d) (fields_autoplaced yes) (effects (font (size 1.778 1.778)) (justify %s bottom)) (uuid "%s"))' % (
            net, x, y, 180 if left else 0, "right" if left else "left", U("l", tag))
    X = {"JP2": 88.9, "JP1": 190.5}                     # on the 1.27 mm grid
    for jp, (ic, p1, p27, r) in SOCKETS.items():
        x, y = X[jp], 381.0
        body.append(instance(jp, "Connector_Generic:Conn_02x03_Odd_Even", x, y, "%s PART" % ("EPROM LO" if ic == "IC3" else "EPROM HI"),
                             "Connector_PinHeader_2.54mm:PinHeader_2x03_P2.54mm_Vertical", [str(n) for n in range(1, 7)]))
        nets = {"1": "VCC", "3": p1, "5": "BUFFADDR14", "2": "BUFFADDR14", "4": p27, "6": "WR"}
        for n, net in nets.items():
            k = int(n); left = k % 2 == 1
            px = x - 5.08 if left else x + 7.62; py = y - 2.54 * (1 - (k - 1) // 2)
            ex = px - 2.54 if left else px + 2.54
            body.append(wire(px, py, ex, py, "%s.%s" % (jp, n)))
            body.append(vcc(ex, py, "%s.%s" % (jp, n)) if net == "VCC" else label(net, ex, py, left, "%s.%s" % (jp, n)))
        rx, ry = x + 40.64, y                            # the pull-up: pin 1 to P27_x, pin 2 to VCC
        body.append(instance(r, "memory-rev-d-eagle:rcl_R-US__0207_7", rx, ry, "47k",
                             "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P2.54mm_Vertical", ["1", "2"]))   # upright
        body.append(wire(rx - 5.08, ry, rx - 7.62, ry, r + ".1")); body.append(label(p27, rx - 7.62, ry, True, r + ".1"))
        body.append(wire(rx + 5.08, ry, rx + 7.62, ry, r + ".2")); body.append(vcc(rx + 7.62, ry, r + ".2"))
    body.append('\t(text "EEPROM sockets (2026-11-18): JP1 (IC5, EPROM HI) and JP2 (IC3, EPROM LO). 27C256: shunts 1-3 and 2-4 '
                '(VPP on VCC, pin 27 A14). 28C256: shunt 3-5 (pin 1 A14); add 4-6 to write it (pin 27 !WE on WR), else '
                'R6 / R7 hold !WE high (read-only). Never A14 on a 27C256\'s pin 1." (exclude_from_sim no) (at 60 398 0) '
                '(effects (font (size 1.778 1.778)) (justify left bottom)) (uuid "%s"))' % U("note"))
    k = sheet.rfind("\t(sheet_instances")
    if k < 0:
        k = sheet.rfind(")")
    sheet = sheet[:k] + "\n".join(body) + "\n" + sheet[k:]
    open(os.path.join(DEST, "memory-rev-f.kicad_sch"), "w").write(root)
    open(os.path.join(DEST, "memory-rev-f-sheet1.kicad_sch"), "w").write(sheet)
    print("schematic: Rev E's + JP1, JP2, R6, R7; IC3 / IC5 pins 1 and 27 on the jumpers")


if __name__ == "__main__":
    main()
