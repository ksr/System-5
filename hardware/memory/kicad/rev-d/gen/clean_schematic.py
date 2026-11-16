#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-05
"""Tidy the Rev D schematic for hand editing in KiCad. Run after make_schematic.py.
  1. Hidden power pins: the converter parked them just off the 1.27 mm grid (so no Eagle wire could land on one and merge
     supplies). Put them on-grid at distinct points inside the symbol body, where no wire ends: (0, 0), (0, 1.27), ...
     checked against the body outline.
  2. Wires lying entirely inside another collinear wire (Eagle drew bus entries over net wires) go: they only add a
     mid-wire end that ERC reports as unconnected.
The netlist before and after must be identical, or nothing is written.
"""
import os, re, sys, subprocess, tempfile, shutil
D = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); P = "memory-rev-d"
CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
SHEETS = [os.path.join(D, f) for f in sorted(os.listdir(D)) if f.startswith(P) and f.endswith(".kicad_sch")]
LIB = os.path.join(D, P + "-eagle.kicad_sym")

def netlist(root):
    out = tempfile.mktemp(suffix=".net")
    subprocess.run([CLI, "sch", "export", "netlist", "--format", "kicadsexpr", "-o", out, root], capture_output=True)
    s = open(out).read(); os.remove(out); nets = set()
    for name, body in re.findall(r'\(net\s+\(code "\d+"\)\s+\(name "([^"]+)"\)(.*?)(?=\n\t\t\(net\s|\n\t\)\n\))', s, re.S):
        nets.add((name, frozenset(re.findall(r'\(node\s+\(ref "([^"]+)"\)\s+\(pin "([^"]+)"\)', body))))
    return nets

def form_end(t, i):
    d = 0; j = i; ins = False
    while True:
        c = t[j]
        if ins:
            if c == "\\": j += 1
            elif c == '"': ins = False
        elif c == '"': ins = True
        elif c == "(": d += 1
        elif c == ")":
            d -= 1
            if d == 0: return j + 1
        j += 1

def fix_hidden_pins(t):
    """per top symbol definition: its hidden power pins -> (0, k*1.27) inside the body box"""
    out = []; i = 0; moved = 0
    for m in re.finditer(r'\n(\t+)\(symbol "([^"]+)"\n', t):
        pass
    # walk every (symbol "X" ...) that is a library definition (contains sub-units "X_0_1" etc.)
    for m in re.finditer(r'\(symbol "([^"]+)"\s*\n?\s*(?:\(pin_names|\(exclude_from_sim|\(power|\(in_bom|\(property)', t):
        if m.start() < i: continue
        name = m.group(1); end = form_end(t, m.start()); body = t[m.start():end]
        if "(hide yes) (name" not in body or "(length 0) (hide yes)" not in body:
            continue
        xs, ys = [], []
        for g in re.finditer(r'\((?:start|end|xy) ([\-\d.]+) ([\-\d.]+)\)', body):
            xs.append(float(g.group(1))); ys.append(float(g.group(2)))
        k = 0
        def place(pm):
            nonlocal k
            x, y = 0.0, round(1.27 * k, 2); k += 1
            if xs and not (min(xs) < x < max(xs) and min(ys) < y < max(ys)):
                raise SystemExit("%s: (%.2f, %.2f) outside the body %s" % (name, x, y, (min(xs), min(ys), max(xs), max(ys))))
            return "(at %g %g %s) (length 0) (hide yes)" % (x, y, pm.group(3))
        nb, n = re.subn(r'\(at ([\-\d.]+) ([\-\d.]+) (\d+)\) \(length 0\) \(hide yes\)', place, body)
        out.append(t[i:m.start()]); out.append(nb); i = end; moved += n
    out.append(t[i:]); return "".join(out), moved

def drop_contained(t):
    """a wire lying entirely inside another collinear wire (Eagle drew bus entries over net wires) adds nothing but a
    mid-wire end that ERC reports as unconnected: drop it"""
    W = [(m, tuple(map(float, m.group(1, 2, 3, 4)))) for m in re.finditer(r'\n\t\(wire \(pts \(xy ([\-\d.]+) ([\-\d.]+)\) \(xy ([\-\d.]+) ([\-\d.]+)\)\)[^\n]*', t)]
    def inside(a, b):   # a within b, both axis-aligned and collinear
        (ax1, ay1, ax2, ay2), (bx1, by1, bx2, by2) = a, b
        if ay1 == ay2 == by1 == by2:
            return min(bx1, bx2) <= min(ax1, ax2) and max(ax1, ax2) <= max(bx1, bx2)
        if ax1 == ax2 == bx1 == bx2:
            return min(by1, by2) <= min(ay1, ay2) and max(ay1, ay2) <= max(by1, by2)
        return False
    dead = set()
    for i, (mi, a) in enumerate(W):
        for j, (mj, b) in enumerate(W):
            if i != j and j not in dead and inside(a, b) and (a != b or i > j): dead.add(i); break
    out, last = [], 0
    for i in sorted(dead, key=lambda k: W[k][0].start()):
        m = W[i][0]; out.append(t[last:m.start()]); last = m.end()
    out.append(t[last:]); return "".join(out), len(dead)

def drop_stubs(t, pts_free):
    gone = 0
    def keep(m):
        nonlocal gone
        x1, y1, x2, y2 = map(float, m.group(1, 2, 3, 4))
        if ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5 < 0.3 and ((x1, y1) in pts_free or (x2, y2) in pts_free):
            gone += 1; return ""
        return m.group(0)
    t = re.sub(r'\n\t\(wire \(pts \(xy ([\-\d.]+) ([\-\d.]+)\) \(xy ([\-\d.]+) ([\-\d.]+)\)\)[^\n]*', keep, t)
    return t, gone

root = os.path.join(D, P + ".kicad_sch")
before = netlist(root)
bak = tempfile.mkdtemp(); [shutil.copy(f, bak) for f in SHEETS + [LIB]]
# free wire ends from ERC
erc = tempfile.mktemp(suffix=".json")
subprocess.run([CLI, "sch", "erc", "--format", "json", "--severity-all", "-o", erc, root], capture_output=True)
import json
free = set()
for s in json.load(open(erc))["sheets"]:
    for v in s["violations"]:
        if v["type"] == "unconnected_wire_endpoint":
            for it in v["items"]: free.add((round(it["pos"]["x"] * 100, 2), round(it["pos"]["y"] * 100, 2)))
os.remove(erc)
moved = stubs = 0
for f in SHEETS + [LIB]:
    t = open(f).read(); t, n = fix_hidden_pins(t); moved += n
    if f != LIB:
        t2 = t
        free_r = {(round(x, 2), round(y, 2)) for x, y in free}
        def norm(t):   # compare free points against wire coords as written
            return t
        t, g = drop_contained(t); stubs += g
    open(f, "w").write(t)
# 2b. data-line wires that run on from their labelled junction to a bus drawn as graphics (Eagle buses come across as
#     polylines) end on nothing: drop such a wire when its free end sits on a polyline, then drop polylines no wire touches
def drop_to_graphic_bus(t, free):
    polys = [tuple(map(float, m.groups())) for m in re.finditer(r'\(polyline \(pts \(xy ([\-\d.]+) ([\-\d.]+)\) \(xy ([\-\d.]+) ([\-\d.]+)\)\)', t)]
    def on_poly(x, y):
        return any((x1 == x2 == x and min(y1, y2) <= y <= max(y1, y2)) or (y1 == y2 == y and min(x1, x2) <= x <= max(x1, x2)) for x1, y1, x2, y2 in polys)
    labels = [(float(x), float(y)) for x, y in re.findall(r'\((?:label|global_label|hierarchical_label) "[^"]*" (?:\(shape [a-z_]+\) )?\(at ([\-\d.]+) ([\-\d.]+)', t)]
    def carries_label(a, b):   # a label anywhere on the wire makes it part of the net (BUSDATA4's sits on its bus stub)
        return any((a[0] == b[0] == lx and min(a[1], b[1]) <= ly <= max(a[1], b[1])) or
                   (a[1] == b[1] == ly and min(a[0], b[0]) <= lx <= max(a[0], b[0])) for lx, ly in labels)
    gone = 0
    def keep(m):
        nonlocal gone
        a = (float(m.group(1)), float(m.group(2))); b = (float(m.group(3)), float(m.group(4)))
        if ((a in free and on_poly(*b)) or (b in free and on_poly(*a))) and not carries_label(a, b): gone += 1; return ""
        return m.group(0)
    t = re.sub(r'\n\t\(wire \(pts \(xy ([\-\d.]+) ([\-\d.]+)\) \(xy ([\-\d.]+) ([\-\d.]+)\)\)[^\n]*', keep, t)
    ends = {(float(a), float(b)) for a, b in re.findall(r'\(wire \(pts \(xy ([\-\d.]+) ([\-\d.]+)\)', t)} | \
           {(float(a), float(b)) for a, b in re.findall(r'\(wire \(pts \(xy [\-\d.]+ [\-\d.]+\) \(xy ([\-\d.]+) ([\-\d.]+)\)', t)}
    pg = 0
    def keep_poly(m):
        nonlocal pg
        x1, y1, x2, y2 = map(float, m.group(1, 2, 3, 4))
        touched = any((x1 == x2 == ex and min(y1, y2) <= ey <= max(y1, y2)) or (y1 == y2 == ey and min(x1, x2) <= ex <= max(x1, x2)) for ex, ey in ends)
        if not touched and m.group(0).count("(color 0 0 132") : pg += 1; return ""
        return m.group(0)
    t = re.sub(r'\n\t\(polyline \(pts \(xy ([\-\d.]+) ([\-\d.]+)\) \(xy ([\-\d.]+) ([\-\d.]+)\)\)[^\n]*', keep_poly, t)
    return t, gone, pg
erc2 = tempfile.mktemp(suffix=".json")
subprocess.run([CLI, "sch", "erc", "--format", "json", "--severity-all", "-o", erc2, root], capture_output=True)
free2 = set()
for s_ in json.load(open(erc2))["sheets"]:
    for v in s_["violations"]:
        if v["type"] == "unconnected_wire_endpoint":
            for it in v["items"]: free2.add((round(it["pos"]["x"] * 100, 2), round(it["pos"]["y"] * 100, 2)))
os.remove(erc2)
busw = busp = 0
for f in SHEETS:
    t = open(f).read(); t, g, pg = drop_to_graphic_bus(t, free2); busw += g; busp += pg; open(f, "w").write(t)
print("wires to graphic buses removed: %d; graphic bus lines left untouched by wires removed: %d" % (busw, busp))

# 3. title blocks: this is the Rev D master now, not a conversion
for f in SHEETS:
    t = open(f).read()
    t = re.sub(r'\(title_block[^\n]*\)\n', '(title_block (title "System-5 Memory Rev D (MEM3-D)") (date "2026-10-05") (rev "D") '
               '(comment 1 "64K RAM/EPROM card, KiCad master - edit in KiCad") (comment 2 "From Rev C (2005, Eagle) by gen/; see README.md"))\n', t, count=1)
    open(f, "w").write(t)
after = netlist(root)
if after != before:
    for f in SHEETS + [LIB]: shutil.copy(os.path.join(bak, os.path.basename(f)), f)
    print("NETLIST CHANGED - reverted:", len(before ^ after), "net differences"); sys.exit(1)
print("hidden power pins moved on-grid: %d; wires inside other wires removed: %d; netlist identical (%d nets)" % (moved, stubs, len(after)))
