#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-26
"""gen_schematic.py - a readable, block-structured KiCad schematic for a System-5 card, drawn from its proven netlist.

The 2005 cards' KiCad schematics are machine conversions of the Eagle drawings: correct (each is proven against its
board), but laid out as Eagle drew them. This draws each card again the way YACC1-D's generated cards are drawn
(YACC1-D hardware/cards/video/kicad/v2.0/gen_v20.py): a root sheet and one sheet per functional block, the parts of a
block placed by ELK and the nets between them drawn as wires (sch_wire.py), KiCad's own symbols where they fit.

The circuit is not typed in: it is read from the card's board netlist (the converted project's reports/netlist.net, which
is proven equal to the board), and the result is proven again: KiCad's netlist of the new schematic must partition the
pins exactly as the board netlist does (every net, by pins; names may differ). The board, its project and its MASTER
files are never touched: the new schematic is a project of its own in <card>/kicad/<rev>/schematic/.

A card's spec (that folder's spec.py) says only what a drawing needs: the title, the bus connector's reference, the
blocks (which parts on which sheet, with a title and a note), better names for unnamed nets, and symbol overrides.

    python3 tools/kicad/sch/gen_schematic.py hardware/ide-cf/kicad/rev-a/schematic      (needs node + elkjs: npm install)
"""
import os, re, sys, json, types, shutil, subprocess, collections, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE)
import sheet as S0                                      # noqa: E402
import sch_wire as W                                    # noqa: E402

G = 2.54
CLI = S0.CLI

# value (as the 2005 netlists write it) -> KiCad symbol. Tried first; kept only if it has every pin the board uses.
STD = {
    "74LS00": "74xx:74LS00", "74LS02": "74xx:74LS02", "74LS04": "74xx:74LS04", "74LS05": "74xx:74LS05",
    "74LS20": "74xx:74LS20", "74LS32": "74xx:74LS32", "74LS74": "74xx:74LS74", "74LS75": "74xx:74LS75",
    "74LS85": "74xx:74LS85", "74S85": "74xx:74LS85", "74LS86": "74xx:74LS86", "74LS123": "74xx:74LS123",
    "74LS138": "74xx:74LS138", "74LS151": "74xx:74LS151", "74HCT151": "74xx:74LS151", "74LS163": "74xx:74LS163",
    "74HC160": "74xx:74LS161", "74LS166": "74xx:74LS166", "74LS174": "74xx:74LS174", "74LS175": "74xx:74LS175",
    "74AS175": "74xx:74LS175", "74LS373": "74xx:74LS373", "74LS374": "74xx:74LS374", "7416": "74xx:74LS05",
    "CD4042": "4xxx:4042", "4042": "4xxx:4042", "CD4050": "4xxx:4050", "4050": "4xxx:4050",
    "62256": "Memory_RAM:KM62256CLP", "27256": "Memory_EPROM:27C256", "HD6845": "GPU:MC6845", "6845": "GPU:MC6845",
    "CDP1802": "CPU:CDP1802ACE", "CDP1802BCE": "CPU:CDP1802ACE", "PIC16F84": "MCU_Microchip_PIC16:PIC16F84A-XXP",
    "MCP23017": "Interface_Expansion:MCP23017_SP",
    "74HCT00": "74xx:74LS00", "74HCT14": "74xx:74LS14", "74HCT20": "74xx:74LS20", "74HCT74": "74xx:74LS74",   # same pinouts
    "74HCT373": "74xx:74LS373", "CDP1802ACE": "CPU:CDP1802ACE",
    "74HCT138": "74xx:74LS138", "74HCT374": "74xx:74LS374", "74HCT244": "74xx:74LS244", "74HCT10": "74xx:74LS10",
    "74HC05": "74xx:74LS05", "74HCT02": "74xx:74LS02", "74HCT573": "74xx:74LS573",
}


def std_for(value, lib, part):
    v = value.upper().replace("74*", "74LS").replace("N", "") if value.startswith("74") else value
    v = re.sub(r"^(74[A-Z]*\d+)[A-Z]*$", r"\1", v)
    if v in STD:
        return STD[v]
    for k in (value, part):
        if k in STD:
            return STD[k]
    p = part or ""
    for pat, sym in PATTERNS:
        m = re.search(pat, p)
        if m:
            return sym % tuple(int(g) for g in m.groups()) if m.groups() else sym
    return None


# Eagle part (lib_device) -> KiCad symbol, for passives, headers and the bus connector
PATTERNS = [
    (r"^rcl_R-", "Device:R"), (r"^rcl_C-", "Device:C"), (r"CRYTAL|CRYSTAL", "Device:Crystal"),
    (r"PINHD-2X(\d+)$", "Connector_Generic:Conn_02x%02d_Odd_Even"), (r"PINHD-1X(\d+)$", "Connector_Generic:Conn_01x%02d"),
    (r"_MA(\d+)-2$", "Connector_Generic:Conn_02x%02d_Odd_Even"), (r"_MA(\d+)-1$", "Connector_Generic:Conn_01x%02d"),
    (r"_C30$", "system5:System5_Bus"), (r"^Conn_01x30$", "system5:System5_Bus"), (r"7134", "system5:IDT7134"),
]


VALUE = {"C-US": "C", ".1": "0.1uF", "10.0": "10uF", "CPOL-US": "C", "R-US_": "R", "CRYTAL": "Crystal",
         "BOOTROM": "2732", "1852": "CDP1852", "PAKVI": "PAK-VI", "PIC16F8*": "PIC16F84", "MINI_DIN_6": "PS/2 mini-DIN-6",
         "JP4Q": "EF jumper", "10-XX": "RESET", "RCA": "RCA jack"}


def nice_value(v, libid):
    """the 2005 drawings' placeholder values made readable (the drawings carry no values for most passives)"""
    if libid == "system5:System5_Bus":
        return "System-5 bus"
    if v.startswith("74*"):
        return "74LS" + v[3:]
    return VALUE.get(v, v)


# ---------------------------------------------------------------------------------------------------------------------
# the board netlist
def parse_netlist(path):
    tree = S0.sparse(open(path).read())[0]
    comps, nets = {}, {}
    for c in S0.sfind(S0.sfind(tree, "components")[0], "comp"):
        g = lambda k: (S0.unq(S0.sfind(c, k)[0][1]) if S0.sfind(c, k) and len(S0.sfind(c, k)[0]) > 1 else "")
        src = S0.sfind(c, "libsource")
        lib = S0.unq(S0.sfind(src[0], "lib")[0][1]) if src else ""
        part = S0.unq(S0.sfind(src[0], "part")[0][1]) if src else ""
        comps[g("ref")] = dict(value=g("value"), footprint=g("footprint"), lib=lib, part=part)
    for n in S0.sfind(S0.sfind(tree, "nets")[0], "net"):
        name = S0.unq(S0.sfind(n, "name")[0][1])
        nets[name] = [(S0.unq(S0.sfind(x, "ref")[0][1]), S0.unq(S0.sfind(x, "pin")[0][1])) for x in S0.sfind(n, "node")]
    return comps, nets


def partition(nets):
    """the nets as pin sets, single-pin (unconnected) nets left out: what two drawings of one circuit must share"""
    return {frozenset(p) for p in nets.values() if len(p) > 1}


def clean_name(n, rename):
    if n in rename:
        return rename[n]
    b = n.split("/")[-1]
    if b in rename:
        return rename[b]
    m = re.match(r"Net-\((.*)\)$", b)
    if m:
        b = m.group(1).replace("{slash}", "/")
        b = re.sub(r"~\{([^}]*)\}", r"\1", b)
    return b


# ---------------------------------------------------------------------------------------------------------------------
def load_spec(folder):
    spec = importlib.util.spec_from_file_location("spec", os.path.join(folder, "spec.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def build_N(sp, folder):
    comps, nets = parse_netlist(os.path.join(folder, "..", "reports", "netlist.net"))
    found = [f for f in os.listdir(os.path.join(folder, "..")) if f.endswith("-eagle.kicad_sym")]
    elib = found[0][:-len(".kicad_sym")] if found else None
    if elib:
        S0.LIBPATHS[elib] = os.path.abspath(os.path.join(folder, "..", found[0]))
    for f in os.listdir(os.path.join(folder, "..")):          # a generated card's own library (e.g. CPU Rev D's s5cpu)
        if f.endswith(".kicad_sym") and not f.endswith("-eagle.kicad_sym"):
            S0.LIBPATHS[f[:-len(".kicad_sym")]] = os.path.abspath(os.path.join(folder, "..", f))
    local = os.path.join(HERE, "system5.kicad_sym")
    if os.path.exists(local):
        S0.LIBPATHS["system5"] = local
    tbl = os.path.join(folder, "..", "sym-lib-table")          # a generated card's own local libraries (VIDEO-G)
    if os.path.exists(tbl):
        for name, uri in re.findall(r'\(name "([^"]+)"\)\s*\(type "[^"]+"\)\s*\(uri "([^"]+)"\)', open(tbl).read()):
            S0.LIBPATHS.setdefault(name, os.path.abspath(uri.replace("${KIPRJMOD}", os.path.join(folder, ".."))))
    used = collections.defaultdict(set)
    for n, ps in nets.items():
        for r, p in ps:
            used[r].add(p)
    parts, chosen = {}, {}
    for ref, c in comps.items():
        cands = []
        if ref in getattr(sp, "SYMBOLS", {}):
            cands.append(sp.SYMBOLS[ref])
        s = std_for(c["value"], c["lib"], c["part"])
        if s:
            cands.append(s)
        if elib:
            cands.append("%s:%s" % (elib, c["part"]))
        if c["lib"] and c["part"]:
            cands.append("%s:%s" % (c["lib"], c["part"]))
        pick = None
        for libid in cands:
            try:
                sym = S0.std_symbol(S0.SYM_SUB.get(libid, libid))
            except (ValueError, KeyError, FileNotFoundError, SystemExit):
                continue
            pins = {p["num"] for u in sym.pins for p in sym.pins[u]}
            if used[ref] <= pins:
                pick = libid
                break
        if pick is None:
            raise SystemExit("%s (%s, %s:%s): no symbol has all its pins %s" % (ref, c["value"], c["lib"], c["part"], sorted(used[ref])))
        chosen[ref] = pick
        val = getattr(sp, "VALUES", {}).get(ref) or nice_value(c["value"], pick)
        parts[ref] = (val, pick, c["footprint"], getattr(sp, "NOTES", {}).get(ref, ""))
    rename = getattr(sp, "RENAME", {})
    NETS = {}
    for n, ps in nets.items():
        if len(ps) < 2 and not n.split("/")[-1] in ("VCC", "GND", "+5V"):
            continue
        name = clean_name(n, rename)
        if name in NETS:
            raise SystemExit("two nets named %s" % name)
        NETS[name] = ps
    NC = collections.defaultdict(list)
    for ref, (val, libid, fp, note) in parts.items():
        sym = S0.std_symbol(S0.SYM_SUB.get(libid, libid))
        for u in sym.pins:
            for p in sym.pins[u]:
                if p["num"] not in used[ref] or not any((ref, p["num"]) in ps for ps in NETS.values()):
                    if p["num"] not in NC[ref]:
                        NC[ref].append(p["num"])
    N = types.SimpleNamespace(PARTS=parts, NETS=NETS, NO_CONNECT=dict(NC), DATE=sp.DATE, REV=sp.REV)
    return N, nets


# ---------------------------------------------------------------------------------------------------------------------
DRAWN = "Drawn from the board netlist by tools/kicad/sch/gen_schematic.py"
TB_CHARS = 80                                      # what fits on a line of KiCad's title block


def comments(texts):
    """the title block's comment lines: each text wrapped to TB_CHARS (at "; " first, then at spaces), the first text
    nearest the title (KiCad stacks comment 1 lowest)"""
    lines = []
    for t in texts:
        out = []
        for part in t.split("; "):
            if out and len(out[-1]) + 2 + len(part) <= TB_CHARS:
                out[-1] += "; " + part
                continue
            words, cur = part.split(" "), ""
            for w in words:
                if cur and len(cur) + 1 + len(w) > TB_CHARS:
                    out.append(cur); cur = w
                else:
                    cur = (cur + " " + w) if cur else w
            out.append(cur)
        lines += out[::-1]                         # stacked upwards: a text's first line on top
    if len(lines) > 9:
        raise SystemExit("title block: more than 9 comment lines: %s" % lines)
    return "\n".join('\t\t(comment %d %s)' % (k + 1, S0.q(l)) for k, l in enumerate(lines))


class SubSheet(W.WSheet):
    def write(self, path, file_uuid, title, paper, page, sp):
        head = ['(kicad_sch', '\t(version 20260306)', '\t(generator "elf-gen-schematic")', '\t(generator_version "1.0")',
                '\t(uuid "%s")' % file_uuid, '\t' + W.paper_sexpr(paper),
                '\t(title_block (title %s) (date "%s") (rev "%s") (company "System-5")'
                % (S0.q("%s: %s" % (sp.TITLE, title)), sp.DATE, sp.REV)
                + "\n" + comments(["Sheet %d of the %s schematic" % (page, sp.TITLE), DRAWN, sp.THEORY]) + ')',
                '\t(lib_symbols']
        for libid in sorted(self.syms):
            head.append(self.syms[libid].text)
        head.append('\t)')
        open(path, "w").write("\n".join(head + self.out + ['\t(embedded_fonts no)', ')', '']))


def sheet_items(sp, N, lib):
    """[(key, name, title, wired units, label-style units, where, note)]; the power units, the decoupling capacitors and
    anything the spec names "power" go on the power sheet"""
    units = {}
    for ref, (val, libid, fp, note) in N.PARTS.items():
        units[ref] = lib(S0.SYM_SUB.get(libid, libid)).units
    def expand(items):
        out = []
        for it in items:
            if isinstance(it, tuple):
                out.append(it)
            else:
                us = units[it]
                if len(us) > 1 and it.startswith(("IC", "U")) and power_unit(N, lib, it) == us[-1]:
                    us = us[:-1]                          # the power unit goes on the power sheet
                out += [(it, u) for u in us]
        return out
    def spare(ref, unit):
        """a gate with every input on a supply (or open) and nothing on its outputs: an unused section"""
        pins = lib(S0.SYM_SUB.get(N.PARTS[ref][1], N.PARTS[ref][1])).unit_pins(unit)
        if not ref.startswith(("IC", "U")) or len(units[ref]) < 2 or not pins:
            return False
        for p in pins:
            n = S0.NETOF.get((ref, p["num"]))
            if p["etype"] in ("output", "tri_state", "open_collector") and n is not None:
                return False
            if p["etype"] == "input" and n not in S0.POWER_NETS + (None,):
                return False
        return True
    spares = []
    out, placed = [], set()
    for key, name, title, items, fixed, note in sp.SHEETS:
        it = expand(items)
        spares += [x for x in it if spare(*x)]
        placed |= {x for x in it if spare(*x)}
        it = [x for x in it if not spare(*x)]
        fx = expand(fixed[0]) if fixed else []
        placed |= set(it) | set(fx)
        out.append([key, name, title, it, fx, fixed[1] if fixed else None, note])
    rest = [(r, u) for r in sorted(units, key=lambda r: (re.sub(r"\d", "", r), int(re.sub(r"\D", "", r) or 0)))
            for u in units[r] if (r, u) not in placed]
    pw = next(s for s in out if s[0] == "power")
    pw[4] = pw[4] + spares + rest
    return [tuple(s) for s in out]


def power_unit(N, lib, ref):
    s = lib(S0.SYM_SUB.get(N.PARTS[ref][1], N.PARTS[ref][1]))
    last = s.units[-1]
    pins = s.unit_pins(last)
    nets = {S0.NETOF.get((ref, p["num"])) for p in pins}
    return last if pins and nets <= set(S0.POWER_NETS) | {None} else None


def pin_shape(D, sheet, net):
    kinds = {D.pin_etype[k] for k in D.sheet_pins[sheet][net]}
    if kinds & {"output", "tri_state", "open_collector"}:
        return "output"
    if "bidirectional" in kinds:
        return "bidirectional"
    if kinds <= {"input"}:
        return "input"
    return "passive"


def build(folder):
    sp = load_spec(folder)
    S0.configure(types.SimpleNamespace(NETS={}, NO_CONNECT={}), sp.PROJ, sp.BUSREF, getattr(sp, "POWER", ("VCC", "GND")))
    N, board_nets = build_N(sp, folder)
    S0.configure(N, sp.PROJ, sp.BUSREF, getattr(sp, "POWER", ("VCC", "GND")), S0.LIBPATHS)
    S0.ROOT_UUID = S0.U(sp.PROJ, "root")
    root_uuid = S0.ROOT_UUID
    cache = W.WSheet("cache", lambda n: "hier")
    specs = sheet_items(sp, N, cache.lib)
    bus = {n for n, ps in N.NETS.items() if any(r == sp.BUSREF for r, p in ps)} - set(S0.POWER_NETS)
    D = W.Design(N, bus, [(name, it + fx) for key, name, title, it, fx, where, note in specs], cache.lib, hier=True,
                 power=S0.POWER_NETS)
    for f in os.listdir(folder):
        if f.endswith(".kicad_sch"):
            os.remove(os.path.join(folder, f))
    blocks, pwr, flg, stats, pinhits = [], 0, 0, [], set()
    pspec = next(s for s in specs if s[0] == "power")
    flags_on = "power" if (pspec[3] or pspec[4]) else specs[0][0]   # an empty Power sheet: the flags go on the first
    for page, (key, name, title, items, fx, where, note) in enumerate(specs, 2):
        su = S0.U(sp.PROJ, "sheet", key, "instance")
        S0.ROOT_UUID = root_uuid + "/" + su
        S = SubSheet(sp.PROJ + "/" + key, lambda net: "hier", shape=lambda net, n=name: pin_shape(D, n, net))
        S.pwr, S.flg = pwr, flg
        ox, oy = 15.24, 30.48
        ext = None
        if fx:
            if where == "left":
                rows, x = [], 0
                for ref, unit in fx:
                    nd = W.Node(D, None, ref, unit, set(), S.label_kind)
                    rows.append((nd, x - nd.box.x0, -nd.box.y0))
                    x += nd.box.x1 - nd.box.x0 + 2
            else:
                rows = W.label_style_rows(D, fx, S.label_kind, width=380.0)
            ext = W.draw_rows(S, rows, ox, oy)

        def measure(L, ext=ext, where=where):
            dry = SubSheet("dry", lambda net: "hier")
            e0, _ = W.draw(dry, D, L, items, 0, 0, hier=True)
            w, h = e0.x1 - e0.x0, e0.y1 - e0.y0
            if ext is not None:
                fw, fh = ext.x1 - ext.x0, ext.y1 - ext.y0
                w, h = (fw + 7.62 + w, max(fh, h)) if where == "left" else (max(fw, w), fh + 10.16 + h)
            return w + 5, h + (oy - 12.7) + 5, dry.nwires
        L, layering = W.best_layout(D, name, items, S.label_kind, measure) if items else (None, None)
        unclear = []
        if items and L is not None:
            lx, ly = (ext.x1 + 7.62, oy) if (ext and where == "left") else (ox, (ext.y1 + 10.16) if ext else oy)
            dry = SubSheet("dry", lambda net: "hier")
            e0, _ = W.draw(dry, D, L, items, 0, 0, hier=True)
            lx = round((lx - e0.x0) / G) * G
            ly = round((ly - e0.y0) / G) * G
            e2, unclear = W.draw(S, D, L, items, lx, ly, hier=True)
            ext = e2 if ext is None else ext | e2
        elif items:
            rows = W.label_style_rows(D, items, S.label_kind, width=560.0)
            e2 = W.draw_rows(S, rows, ox, (ext.y1 + 10.16) if ext else oy)
            ext = e2 if ext is None else ext | e2
        if key == flags_on:
            ext = ext or W.Box(ox, oy, ox + 10, oy)
            y = round((ext.y1 + 10.16) / G) * G
            for k, kind in enumerate(S0.POWER_NETS):
                x = ox + 5.08 + 15.24 * k
                S.wire(x, y, x + 7.62, y)
                S.power(kind, x, y, "U" if k == 0 else "D")
                S.power(kind, x + 7.62, y, "U", flag=True)
            S.text(ox + 40.64, y - 1.27, "PWR_FLAGs: the bus supplies %s and %s." % S0.POWER_NETS, size=1.5)
            ext = ext | W.Box(ox, y - 6, ox + 140, y + 6)
        ext = ext or W.Box(ox, oy, ox + 10, oy)
        S.text(ox, 12.7, title, size=2.5, bold=True)
        S.text(ox, 17.78, note, size=1.5)
        name_w = max(len(l) for l in note.split("\n")) * 1.5 * 0.8
        w, h = max(ext.x1, ox + name_w) - ox + 5, ext.y1 - 12.7 + 5
        paper = W.paper_for(w, h)[0]
        fname = "%s-%s.kicad_sch" % (sp.PROJ, key)
        S.write(os.path.join(folder, fname), S0.U(sp.PROJ, "sheet", key, "file"), name, paper, page, sp)
        pwr, flg = S.pwr, S.flg
        pinhits |= S.pinhits
        nets = sorted({n for n in D.sheet_pins[name] if n not in S0.POWER_NETS})
        blocks.append((key, name, title, fname, su, page, [(n, pin_shape(D, name, n)) for n in nets]))
        stats.append((name, paper, len(items) + len(fx), S.nwired, S.nlabels,
                      ("wired, ELK " + layering) if L is not None else ("label style" if items or fx else "-"), unclear))
    S0.ROOT_UUID = root_uuid
    missing = [k for k in list(S0.NETOF) + list(S0.NC) if k not in pinhits]
    if missing:
        raise SystemExit("schematic: pins not drawn: %s" % missing[:20])
    write_root(sp, folder, blocks, root_uuid)
    return sp, N, board_nets, stats


def write_root(sp, folder, blocks, root_uuid):
    out = []
    eff = "(effects (font (size 1.27 1.27))"
    X, Y, rowh = 25.4, 76.2, 0
    nblocks = collections.Counter(n for b in blocks for n, s in b[6])
    for key, name, title, fname, su, page, pins in blocks:
        left = [(n, s) for n, s in pins if nblocks[n] > 1 and s in ("input", "passive")]
        right = [(n, s) for n, s in pins if nblocks[n] > 1 and s not in ("input", "passive")]
        local = [(n, s) for n, s in pins if nblocks[n] == 1]
        lw = max([len(n) for n, s in left + local] + [4]) * 1.0 + 9
        rw = max([len(n) for n, s in right + local] + [4]) * 1.0 + 9
        w = round((max([len(n) for n, s in pins] + [10]) * 2 * 1.0 + 12.7) / G) * G
        top = max(len(left), len(right))
        rows = top + (1 + len(local) if local else 0)
        h = (rows + 1) * G
        x = round((X + lw) / G) * G
        if x + w + rw > 400:
            X, Y, rowh = 25.4, Y + rowh + 20.32, 0
            x = round((X + lw) / G) * G
        y = Y
        L = ['\t(sheet (at %s %s) (size %s %s) (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no) '
             '(fields_autoplaced yes)' % (S0.f(x), S0.f(y), S0.f(w), S0.f(h)),
             '\t\t(stroke (width 0.1524) (type solid)) (fill (color 0 0 0 0.0000)) (uuid "%s")' % su,
             '\t\t(property "Sheetname" %s (at %s %s 0) %s (justify left bottom)))' % (S0.q(name), S0.f(x), S0.f(y - 0.7), eff),
             '\t\t(property "Sheetfile" %s (at %s %s 0) %s (justify left top)))' % (S0.q(fname), S0.f(x), S0.f(y + h + 0.6), eff)]
        placed = [("L", i, n, s, "") for i, (n, s) in enumerate(left)] + [("R", i, n, s, "") for i, (n, s) in enumerate(right)]
        for i, (n, s) in enumerate(local):
            placed += [("L", top + 1 + i, n, s, ""), ("R", top + 1 + i, n, s, "2")]
        if local:
            out.append('\t(polyline (pts (xy %s %s) (xy %s %s)) (stroke (width 0.1524) (type dash)) (uuid "%s"))'
                       % (S0.f(x), S0.f(y + (top + 1) * G), S0.f(x + w), S0.f(y + (top + 1) * G), S0.U(sp.PROJ, "rline", key)))
        for side, i, n, s, k in placed:
            py = y + (i + 1) * G
            px = x if side == "L" else x + w
            L.append('\t\t(pin %s %s (at %s %s %d) %s (justify %s)) (uuid "%s"))'
                     % (S0.q(n), s, S0.f(px), S0.f(py), 180 if side == "L" else 0, eff,
                        "left" if side == "L" else "right", S0.U(sp.PROJ, "spin", key, n + k)))
            ex = px - 2 * G if side == "L" else px + 2 * G
            out.append('\t(wire (pts (xy %s %s) (xy %s %s)) (stroke (width 0) (type default)) (uuid "%s"))'
                       % (S0.f(px), S0.f(py), S0.f(ex), S0.f(py), S0.U(sp.PROJ, "rw", key, n + k)))
            ang, just = (180, "right bottom") if side == "L" else (0, "left bottom")
            out.append('\t(label %s (at %s %s %d) %s (justify %s)) (uuid "%s"))'
                       % (S0.q(n), S0.f(ex), S0.f(py), ang, eff, just, S0.U(sp.PROJ, "rl", key, n + k)))
        L += ['\t\t(instances (project "%s" (path "/%s" (page "%d"))))' % (sp.PROJ, root_uuid, page), '\t)']
        out.append("\n".join(L))
        X = x + w + rw + 10
        rowh = max(rowh, h)
    note = ["%s, one sheet per functional block:" % sp.TITLE]
    note += ["  sheet %d  %-14s %s" % (page, name, title) for key, name, title, fname, su, page, pins in blocks]
    note += ["", sp.ROOT_NOTE, "",
             "Every net of a sheet is a pin of its sheet symbol here, labelled with the net's name. Above a dashed line:",
             "the nets the sheet shares with other sheets (left: it reads them, right: it drives them). Below it: nets",
             "drawn on that sheet only. VCC and GND are power symbols on the sheets."]
    out.append('\t(text %s (exclude_from_sim no) (at 25.4 15.24 0) (effects (font (size 1.5 1.5)) (justify left top)) '
               '(uuid "%s"))' % (S0.q("\n".join(note)), S0.U(sp.PROJ, "rootnote")))
    paper = W.paper_for(max(X - 25.4, 200), Y + rowh + 10 - 22.86)[0]
    head = ['(kicad_sch', '\t(version 20260306)', '\t(generator "elf-gen-schematic")', '\t(generator_version "1.0")',
            '\t(uuid "%s")' % root_uuid, '\t' + W.paper_sexpr(paper),
            '\t(title_block (title %s) (date "%s") (rev "%s") (company "System-5")' % (S0.q(sp.TITLE), sp.DATE, sp.REV)
            + "\n" + comments([sp.SUBTITLE, DRAWN, sp.THEORY]) + ')',
            '\t(lib_symbols)']
    tail = ['\t(sheet_instances (path "/" (page "1")))', '\t(embedded_fonts no)', ')', '']
    open(os.path.join(folder, sp.PROJ + ".kicad_sch"), "w").write("\n".join(head + out + tail))


def finish(folder, sp, board_nets, stats):
    pro = os.path.join(folder, sp.PROJ + ".kicad_pro")
    if not os.path.exists(pro):
        json.dump({"meta": {"filename": sp.PROJ + ".kicad_pro", "version": 3}, "schematic": {}, "boards": [],
                   "sheets": [], "text_variables": {}}, open(pro, "w"), indent=2)
    root = os.path.join(folder, sp.PROJ + ".kicad_sch")
    net = os.path.join(folder, sp.PROJ + "-netlist.net")
    subprocess.run([CLI, "sch", "export", "netlist", "-o", net, root], capture_output=True, text=True, check=True)
    _, got = parse_netlist(net)
    a, b = partition(board_nets), partition(got)
    ok = a == b
    print("netlist proof: the new schematic against the board netlist: %s (%d nets with two or more pins)"
          % ("MATCH" if ok else "DIFFER: %d only on the board, %d only in the new schematic" % (len(a - b), len(b - a)), len(a)))
    if not ok:
        for s in sorted(a - b, key=len)[:8]:
            print("   board only:", sorted(s)[:8])
        for s in sorted(b - a, key=len)[:8]:
            print("   new only:  ", sorted(s)[:8])
    pdf = os.path.join(folder, sp.PROJ + ".pdf")
    subprocess.run([CLI, "sch", "export", "pdf", "-o", pdf, root], capture_output=True, text=True, check=True)
    erc = os.path.join(folder, sp.PROJ + "-erc.json")
    subprocess.run([CLI, "sch", "erc", "--format", "json", "--severity-error", "-o", erc, root], capture_output=True, text=True)
    nerr = sum(len(s.get("violations", [])) for s in json.load(open(erc)).get("sheets", []))
    print("ERC: %d errors (%s)" % (nerr, os.path.basename(erc)))
    for name, paper, n, nw, nl, how, unclear in stats:
        print("  sheet %-14s %s %3d units %3d nets wired %3d labels  %s%s" % (name, paper, n, nw, nl, how,
              ("  names not clear: " + ", ".join(unclear)) if unclear else ""))
    print("PDF:", os.path.relpath(pdf, ROOT))
    return ok


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    folder = os.path.abspath(sys.argv[1])
    why = W.elk_ready()
    if why:
        raise SystemExit(why)
    sp, N, board_nets, stats = build(folder)
    sys.exit(0 if finish(folder, sp, board_nets, stats) else 1)


if __name__ == "__main__":
    main()
