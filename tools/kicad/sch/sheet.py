# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-26
"""sheet.py - the KiCad schematic sheet writer for the generated System-5 schematics (tools/kicad/sch/).

Copied from YACC1-D's CF card generator (hardware/cards/cf/kicad/v1.0/gen_cf.py: the s-expression helpers, LibSym,
the Sheet class: symbols, pin stubs, labels, power symbols, no-connects) and made card-independent: configure() sets the
netlist module N (PARTS, NETS, NO_CONNECT, DATE, REV), the project name, the bus connector's reference, the power nets
and where non-standard symbol libraries live. sch_wire.py (from YACC1-D, unchanged) builds on it under the name gen_cf.
"""
import os, re, uuid, subprocess, collections

APP = "/Applications/KiCad/KiCad.app/Contents"
KSYM = APP + "/SharedSupport/symbols"
KFP = APP + "/SharedSupport/footprints"
CLI = APP + "/MacOS/kicad-cli"
SYM_SUB = {"Device:CP": "Device:C_Polarized"}           # KiCad 10 renamed CP
G = 2.54
N = None
PROJ = "card"
BUSREF = "X1"
POWER_NETS = ("VCC", "GND")
LIBPATHS = {}                                            # library name -> .kicad_sym path (local, Eagle-converted)


def configure(netlist, proj, busref, power=("VCC", "GND"), libpaths=None):
    global N, PROJ, BUSREF, POWER_NETS, LIBPATHS, NETOF, NC
    N, PROJ, BUSREF, POWER_NETS, LIBPATHS = netlist, proj, busref, tuple(power), dict(libpaths or {})
    NETOF = {(r, str(p)): n for n, conns in N.NETS.items() for r, p in conns}
    NC = {(r, str(p)) for r, ps in N.NO_CONNECT.items() for p in ps}


NS = uuid.UUID("6b1f3c1e-2d4a-4c55-9a3e-5f0c0cfca4d1")   # fixed namespace: stable UUIDs run to run


def U(*key):
    return str(uuid.uuid5(NS, "/".join(str(k) for k in key)))


def f(v):
    s = ("%.4f" % v).rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def q(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


# ---------------------------------------------------------------------------------------------------------------------
# a small s-expression reader (enough for .kicad_sym files)
_TOK = re.compile(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()"]+')


def sparse(s):
    toks = _TOK.findall(s)
    pos = [0]

    def rd():
        out = []
        while pos[0] < len(toks):
            t = toks[pos[0]]; pos[0] += 1
            if t == "(":
                out.append(rd())
            elif t == ")":
                return out
            else:
                out.append(t)
        return out
    return rd()


def unq(t):
    return t[1:-1].replace('\\"', '"').replace("\\\\", "\\") if t.startswith('"') else t


def sfind(lst, key):
    return [x for x in lst if isinstance(x, list) and x and x[0] == key]


def lib_block(text, name):
    """The text of one top-level (symbol "name" ...) in a .kicad_sym file."""
    i = text.index('\n\t(symbol "%s"\n' % name) + 1
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
            if d == 0:
                return text[i:j + 1]
        j += 1


def kicad_cli(*args):
    r = subprocess.run([CLI] + list(args), capture_output=True, text=True)
    if r.returncode != 0 or "Unable" in r.stdout + r.stderr:
        raise SystemExit("kicad-cli %s failed:\n%s%s" % (" ".join(args[:2]), r.stdout, r.stderr))


def top_forms(text):
    """the top-level (...) forms inside a KiCad s-expression file"""
    forms, d, ins, start, j = [], 0, False, None, text.index("(") + 1
    while j < len(text):
        c = text[j]
        if ins:
            if c == "\\": j += 1
            elif c == '"': ins = False
        elif c == '"': ins = True
        elif c == "(":
            if d == 0: start = j
            d += 1
        elif c == ")":
            if d == 0: break
            d -= 1
            if d == 0: forms.append(text[start:j + 1])
        j += 1
    return forms


class LibSym:
    """One library symbol: its text (renamed lib:name for lib_symbols), pins per unit, property offsets."""
    def __init__(self, libid, block):
        self.libid = libid
        bare = libid.split(":")[1]
        self.text = block.replace('(symbol "%s"' % bare, '(symbol "%s"' % libid, 1)
        sym = sparse(block)[0]
        if sfind(sym, "extends"):
            raise SystemExit("%s: derived symbols are not handled" % libid)
        self.props, self.just = {}, {}
        for p in sfind(sym, "property"):
            at = sfind(p, "at")[0]
            self.props[unq(p[1])] = (float(at[1]), float(at[2]), float(at[3]))
            eff = sfind(p, "effects")
            j = sfind(eff[0], "justify") if eff else []
            self.just[unq(p[1])] = " ".join(j[0][1:]) if j else ""
        self.pins = collections.defaultdict(list)          # unit -> [pin dict]  (unit 0 = common to all units)
        self.body = collections.defaultdict(list)          # unit -> body outline points (library coords, y up)
        for sub in sfind(sym, "symbol"):
            m = re.match(r'"(.*)_(\d+)_(\d+)"$', sub[1])
            unit, style = int(m.group(2)), int(m.group(3))
            if style > 1:
                continue                                    # De Morgan alternates: same pins
            for g in sub[2:]:
                if not isinstance(g, list) or not g:
                    continue
                if g[0] in ("rectangle", "arc"):
                    self.body[unit] += [(float(k[1]), float(k[2])) for k in g if isinstance(k, list) and k[0] in ("start", "mid", "end")]
                elif g[0] in ("polyline", "bezier"):
                    self.body[unit] += [(float(k[1]), float(k[2])) for k in sfind(sfind(g, "pts")[0], "xy")]
                elif g[0] == "circle":
                    c, r = sfind(g, "center")[0], float(sfind(g, "radius")[0][1])
                    self.body[unit] += [(float(c[1]) - r, float(c[2]) - r), (float(c[1]) + r, float(c[2]) + r)]
            for p in sfind(sub, "pin"):
                at = sfind(p, "at")[0]
                self.pins[unit].append(dict(num=unq(sfind(p, "number")[0][1]), x=float(at[1]), y=float(at[2]),
                                            ang=int(float(at[3])), etype=p[1]))
        self.units = sorted(u for u in self.pins if u > 0) or [0]

    def unit_pins(self, unit):
        return self.pins.get(0, []) + (self.pins.get(unit, []) if unit else [])

    def unit_body(self, unit):
        """(x0, y0, x1, y1) of the unit's graphics, library coords (y up), or None"""
        pts = self.body.get(0, []) + (self.body.get(unit, []) if unit else [])
        if not pts:
            return None
        return min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)


_libtext = {}


def std_symbol(libid):
    lib, name = libid.split(":")
    path = LIBPATHS.get(lib) or os.path.join(KSYM, lib + ".kicad_sym")
    if path not in _libtext:
        _libtext[path] = open(path).read()
    block = lib_block(_libtext[path], name)
    m = re.search(r'\(extends "([^"]+)"\)', block)
    if m:                                               # a derived symbol: its base's graphics and pins, under its name
        base = m.group(1)
        block = lib_block(_libtext[path], base).replace('(symbol "%s"' % base, '(symbol "%s"' % name, 1)
        block = block.replace('(symbol "%s_' % base, '(symbol "%s_' % name)
    return LibSym(libid, block)


NETOF, NC = {}, set()
ROOT_UUID = U("sheet", "root")
STUB = 2 * G


def rot_pt(x, y, rot):
    """screen-coordinate rotation, KiCad sense (positive = counter-clockwise as seen)"""
    return {0: (x, y), 90: (y, -x), 180: (-x, -y), 270: (-y, x)}[rot % 360]


def dir_name(dx, dy):
    return {(1, 0): "R", (-1, 0): "L", (0, -1): "U", (0, 1): "D"}[(dx, dy)]


class Sheet:
    def __init__(self):
        self.syms = {}           # libid -> LibSym
        self.out = []            # schematic items (text)
        self.pwr = 0
        self.flg = 0
        self.labels = set()      # (x, y, net) already labelled
        self.placed = collections.defaultdict(set)   # ref -> units placed
        self.pinhits = set()     # (ref, pin) drawn
        self.first_unit_uuid = {}

    def lib(self, libid):
        if libid not in self.syms:
            self.syms[libid] = std_symbol(libid)
        return self.syms[libid]

    def wire(self, x1, y1, x2, y2):
        self.out.append('\t(wire (pts (xy %s %s) (xy %s %s)) (stroke (width 0) (type default)) (uuid "%s"))'
                        % (f(x1), f(y1), f(x2), f(y2), U("w", x1, y1, x2, y2)))

    def label(self, x, y, net, d):
        if (round(x, 3), round(y, 3), net) in self.labels:
            return
        self.labels.add((round(x, 3), round(y, 3), net))
        ang, just = {"R": (0, "left bottom"), "L": (180, "right bottom"), "U": (90, "left bottom"),
                     "D": (270, "right bottom")}[d]
        self.out.append('\t(label %s (at %s %s %d) (effects (font (size 1.27 1.27)) (justify %s)) (uuid "%s"))'
                        % (q(net), f(x), f(y), ang, just, U("l", x, y, net)))

    def noconn(self, x, y):
        self.out.append('\t(no_connect (at %s %s) (uuid "%s"))' % (f(x), f(y), U("nc", x, y)))

    def text(self, x, y, s, size=1.524, bold=False, just="left top"):
        self.out.append('\t(text %s (exclude_from_sim no) (at %s %s 0) (effects (font (size %s %s)%s) (justify %s)) '
                        '(uuid "%s"))' % (q(s), f(x), f(y), f(size), f(size), " (bold yes)" if bold else "", just,
                                          U("t", x, y, s[:20])))

    def box(self, x1, y1, x2, y2, title):
        self.out.append('\t(rectangle (start %s %s) (end %s %s) (stroke (width 0.2) (type dash) (color 72 72 160 1)) '
                        '(fill (type none)) (uuid "%s"))' % (f(x1), f(y1), f(x2), f(y2), U("box", title)))
        self.text(x1 + 1.27, y1 + 1.27, title, size=2.0, bold=True)

    def power(self, kind, x, y, d, flag=False):
        """a power symbol (or PWR_FLAG) whose pin is at (x, y), its graphic pointing in direction d"""
        if flag:
            libid, self.flg = "power:PWR_FLAG", self.flg + 1
            ref, value = "#FLG%02d" % self.flg, "PWR_FLAG"
            rot = 0
        else:
            libid = "power:" + kind
            self.pwr += 1
            ref, value = "#PWR%03d" % self.pwr, kind
            up = {"U": 0, "L": 90, "D": 180, "R": 270}
            rot = up[d] if kind != "GND" else (up[d] + 180) % 360   # VCC, +5V: arrow up at 0; GND: bars down at 0
        s = self.lib(libid)
        vx, vy, _ = s.props["Value"]
        if rot in (90, 270):                              # sideways symbol: horizontal text clear of the graphic
            vy = 5.6 if vy > 0 else -5.6
        ox, oy = rot_pt(vx, -vy, rot)
        if rot in (90, 270):
            oy -= 0.9                                     # lift it off the stub line
        fa = (360 - rot) % 360 if rot != 180 else 0       # field angles are stored relative to the symbol; upside
                                                          # down, KiCad turns the text with it, so it stays level
        uid = U("pwr", ref)
        self.out.append(
            '\t(symbol (lib_id %s) (at %s %s %d) (unit 1) (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no) '
            '(uuid "%s")\n\t\t(property "Reference" %s (at %s %s 0) (effects (font (size 1.27 1.27)) (hide yes)))\n'
            '\t\t(property "Value" %s (at %s %s %d) (effects (font (size 1.27 1.27))))\n'
            '\t\t(property "Footprint" "" (at %s %s 0) (effects (font (size 1.27 1.27)) (hide yes)))\n'
            '\t\t(property "Datasheet" "" (at %s %s 0) (effects (font (size 1.27 1.27)) (hide yes)))\n'
            '\t\t(pin "1" (uuid "%s"))\n'
            '\t\t(instances (project "%s" (path "/%s" (reference %s) (unit 1))))\n\t)'
            % (q(libid), f(x), f(y), rot, uid, q(ref), f(x), f(y), q(value), f(x + ox), f(y + oy), fa, f(x), f(y),
               f(x), f(y), U("pp", ref), PROJ, ROOT_UUID, q(ref)))

    @staticmethod
    def auto_fields(s, unit, rot, pins):
        """Reference/Value positions (sheet offsets + justify) that keep the text off the symbol body, for symbols whose
        library fields sit inside the body (KiCad's 74xx gates) or are drawn rotated (Device:R/C/LED; this sheet draws
        every field horizontal): pins only above/below the body -> both fields to its right, one line each side of the
        centre; otherwise Reference above the body and Value below it, left-aligned with the body. The field angle is
        written as (360 - rot), so the justify below acts in sheet terms."""
        b = s.unit_body(unit)
        if b is None:
            return {}
        corners = [rot_pt(u, -v, rot) for u in (b[0], b[2]) for v in (b[1], b[3])]
        x0, x1 = min(c[0] for c in corners), max(c[0] for c in corners)
        y0, y1 = min(c[1] for c in corners), max(c[1] for c in corners)       # sheet offsets, y down
        out = {}
        for key in ("Reference", "Value"):
            lx, ly, la = s.props.get(key, (0, 0, 0))
            inside = b[0] - 0.2 <= lx <= b[2] + 0.2 and b[1] - 0.2 <= ly <= b[3] + 0.2
            if not inside and la % 180 == (rot % 180):
                continue                                    # library placement is already clear and horizontal
            out[key] = None
        if not out:
            return {}
        dirs = set()
        for p in pins:
            dx, dy = {0: (1, 0), 90: (0, -1), 180: (-1, 0), 270: (0, 1)}[(p["ang"] + 180) % 360]
            dirs.add(rot_pt(dx, dy, rot))
        side = bool(dirs) and all(d[0] == 0 for d in dirs)
        if side:
            cy = (y0 + y1) / 2
            place = {"Reference": (x1 + 0.9, cy - 0.3, "left bottom"), "Value": (x1 + 0.9, cy + 0.3, "left top")}
        else:
            place = {"Reference": (x0, y0 - 0.6, "left bottom"), "Value": (x0, y1 + 0.6, "left top")}
        return {k: place[k] for k in out}

    def part(self, ref, unit, x, y, rot=0, stub=STUB, fields=None, skip=(), pstub=None):
        """place one unit of a PARTS symbol and draw every one of its pins: stub+label, stub+power symbol, or NC.
        fields: {'Reference': (dx, dy[, justify]), 'Value': ...} overrides of the property offsets (sheet mm); fields not
        given use the library position, or auto_fields() where that would put the text on the body."""
        value, symid, fpid, note = N.PARTS[ref]
        libid = SYM_SUB.get(symid, symid)
        s = self.lib(libid)
        uid = U("sym", ref, unit)
        self.first_unit_uuid.setdefault(ref, uid)
        if unit == min(s.units):
            self.first_unit_uuid[ref] = uid
        self.placed[ref].add(unit)
        pins = s.unit_pins(unit)
        props = []
        auto = self.auto_fields(s, unit, rot, pins)
        for key, val, hide in (("Reference", ref, False), ("Value", value, False), ("Footprint", fpid, True),
                               ("Datasheet", "", True), ("Description", note, True)):
            just = ""
            if fields and key in fields:
                px, py = fields[key][:2]
                just = fields[key][2] if len(fields[key]) > 2 else ""
            elif key in auto:
                px, py, just = auto[key]
            else:
                lx, ly, _ = s.props.get(key, (0, 0, 0))
                px, py = rot_pt(lx, -ly, rot)
                just = s.just.get(key, "") if rot == 0 else ""   # the library's own justify holds in its own frame
            props.append('\t\t(property "%s" %s (at %s %s %d) (effects (font (size 1.27 1.27))%s%s))'
                         % (key, q(val), f(x + px), f(y + py), (360 - rot) % 360,
                            (" (justify %s)" % just) if just else "", " (hide yes)" if hide else ""))
        self.out.append(
            '\t(symbol (lib_id %s) (at %s %s %d) (unit %d) (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no) '
            '(uuid "%s")\n%s\n%s\n\t\t(instances (project "%s" (path "/%s" (reference %s) (unit %d))))\n\t)'
            % (q(libid), f(x), f(y), rot, unit, uid, "\n".join(props),
               "\n".join('\t\t(pin %s (uuid "%s"))' % (q(p["num"]), U("pin", ref, p["num"])) for p in pins),
               PROJ, ROOT_UUID, q(ref), unit))
        ends = {}
        for p in pins:
            px, py = rot_pt(p["x"], -p["y"], rot)
            wx, wy = x + px, y + py
            a = (p["ang"] + 180) % 360                      # outward direction, library sense (y up)
            dx, dy = {0: (1, 0), 90: (0, -1), 180: (-1, 0), 270: (0, 1)}[a]
            dx, dy = rot_pt(dx, dy, rot)
            key = (ref, p["num"])
            self.pinhits.add(key)
            ends[p["num"]] = (wx, wy)
            if key in skip:
                continue
            net = NETOF.get(key)
            if net is None:
                if key in NC or ref == BUSREF:
                    self.noconn(wx, wy)
                    continue
                raise SystemExit("schematic: %s.%s is neither on a net nor a no-connect" % key)
            st = pstub if (pstub and net in POWER_NETS) else stub
            ex, ey = wx + dx * st, wy + dy * st
            self.wire(wx, wy, ex, ey)
            d = dir_name(dx, dy)
            if net in POWER_NETS:
                self.power(net, ex, ey, d)
            else:
                self.label(ex, ey, net, d)
        return ends

    def write(self, path, title, comments=(), paper="A3"):
        head = ['(kicad_sch', '\t(version 20260306)', '\t(generator "elf-gen-schematic")', '\t(generator_version "1.0")',
                '\t(uuid "%s")' % ROOT_UUID, '\t(paper "%s")' % paper,
                '\t(title_block (title %s) (date "%s") (rev "%s") (company "System-5")' % (q(title), N.DATE, N.REV)]
        head += ['\t\t(comment %d %s)' % (k + 1, q(c)) for k, c in enumerate(comments)]
        head[-1] += ')'
        head.append('\t(lib_symbols')
        for libid in sorted(self.syms):
            head.append(self.syms[libid].text)
        head.append('\t)')
        tail = ['\t(sheet_instances (path "/" (page "1")))', '\t(embedded_fonts no)', ')', '']
        open(path, "w").write("\n".join(head + self.out + tail))
