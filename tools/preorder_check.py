#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-19
"""Run every check we can before a board's gerbers go to the fab. Nothing is uploaded until this says PASS.

Written after the 2026-10-09 order, when two boards were routed on four copper layers but ordered from 2-layer zips.
  1. LAYERS      the layer count Ken will order (--layers) = the board's copper layers = the copper files in the zip
  2. ERC         the schematic: no errors
  3. DRC         the board with the zones refilled: no errors, nothing unconnected, board = schematic (parity)
  4. FRESH ZIP   the zip's copper, mask, silkscreen, outline and drill files are the ones the board makes today
  5. ZIP CONTENT tools/check_order_zip.py: every copper layer, routed net and hole read back from the zip
  6. BYPASS CAPS every 0.1 uF / 100 nF capacitor has 0.1" (2.54 mm) lead spacing (Ken's rule)
  7. NETLIST     tools/kicad/compare_netlists.py: the schematic's netlist against the board, pad by pad
  8. PLANES      tools/kicad/plane_check.py, on boards with inner-layer zones: each plane one piece, every pin of its
                 net reaches it, no other net's pad inside it, no tracks on the plane layer
  9. PICTURES    one PNG per copper layer, drawn from the zip's own gerbers, written next to the zip for a look by eye
  10. SCHEMATIC  the redrawn schematic PDF kept up to date (Ken, 2026-10-28): reports/netlist.net proven against the
                 board, then tools/kicad/sch/gen_schematic.py redraws and proves the card's schematic/ and make_book.py
                 rebuilds docs/manual/pdf/system5-schematics.pdf (skipped for a board with no schematic/spec.py)
Then, by hand: open the PNGs, upload the zip to the fab's gerber viewer, and check the layer count on the order form.
usage: preorder_check.py <board.kicad_pcb> <order.zip> --layers N      exit status 1 if anything fails
Runs with any python3; it calls kicad-cli, and KiCad's own python for the zone refill only through kicad-cli.
"""
import os, re, sys, json, glob, shutil, zipfile, tempfile, subprocess, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_order_zip

CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
results = []


def say(ok, what, detail=""):
    results.append(ok); print("%s  %-11s %s" % ("PASS" if ok else "FAIL", what, detail)); sys.stdout.flush()


def run(*a):
    return subprocess.run(list(a), capture_output=True, text=True)


def strip_dates(text):
    return "\n".join(l for l in text.splitlines() if "CreationDate" not in l and "Created by" not in l and not l.startswith(";"))


def main(brd, zpath, layers):
    brd = os.path.abspath(brd); zpath = os.path.abspath(zpath); d = os.path.dirname(brd)
    sch = brd[:-len(".kicad_pcb")] + ".kicad_sch"; tmp = tempfile.mkdtemp(prefix="preorder-")
    cu, tracks, vias, zones, pads, holes = check_order_zip.board(brd)
    z = zipfile.ZipFile(zpath); files = {n.split("/")[-1]: z.read(n) for n in z.namelist() if not n.endswith("/")}
    zcu = [n for n, b in files.items() if b"%TF.FileFunction,Copper" in b[:4000]]
    # 1. layers
    say(layers == len(cu) == len(zcu), "LAYERS", "ordering %d, board has %d copper layers %s, zip has %d copper files"
        % (layers, len(cu), cu, len(zcu)))
    # 2. ERC
    if os.path.exists(sch):
        r = run(CLI, "sch", "erc", "--format", "json", "--severity-all", "-o", os.path.join(tmp, "erc.json"), sch)
        e = json.load(open(os.path.join(tmp, "erc.json")))
        v = [x for s in e.get("sheets", []) for x in s.get("violations", [])]
        errs = [x for x in v if x.get("severity") == "error"]
        say(not errs, "ERC", "%d errors, %d warnings %s" % (len(errs), len(v) - len(errs),
            dict(collections.Counter(x["type"] for x in errs)) if errs else ""))
    else:
        say(False, "ERC", "no schematic %s" % os.path.basename(sch))
    # 3. DRC on a copy (refilling zones never touches the real board)
    cp = os.path.join(tmp, "board"); shutil.copytree(d, cp, ignore=shutil.ignore_patterns("gerbers", "*.zip", "*.png", "*.pdf", ".history"))
    for t in ("fp-lib-table", "sym-lib-table"):         # project libraries named relative to the board, e.g. VIDEO-G's
        f = os.path.join(cp, t)                             # ${KIPRJMOD}/../lib, must still resolve from the copy
        if os.path.exists(f):
            s = open(f).read(); open(f, "w").write(s.replace("${KIPRJMOD}", d))
    cb = os.path.join(cp, os.path.basename(brd))
    run(CLI, "pcb", "drc", "--format", "json", "--severity-all", "--schematic-parity", "--refill-zones",
        "-o", os.path.join(tmp, "drc.json"), cb)
    r = json.load(open(os.path.join(tmp, "drc.json")))
    errs = [x for x in r["violations"] if x["severity"] == "error"]; warns = len(r["violations"]) - len(errs)
    say(not errs, "DRC", "%d errors %s, %d warnings (silkscreen notes are warnings)" % (len(errs),
        dict(collections.Counter(x["type"] for x in errs)) if errs else "", warns))
    say(not r["unconnected_items"], "UNCONNECTED", "%d" % len(r["unconnected_items"]))
    par = [p["description"] for p in r["schematic_parity"]]
    real = [p for p in par if not p.startswith(("Value (", "Missing symbol field"))]
    say(not real, "PARITY", "%d board/schematic differences in nets or parts%s%s" % (len(real), "; e.g. " + real[0] if real else "",
        " (%d value-text notes ignored)" % (len(par) - len(real)) if len(par) > len(real) else ""))
    # 4. the zip is what the board makes today
    gdir = os.path.join(tmp, "gerbers"); os.makedirs(gdir)
    run(CLI, "pcb", "export", "gerbers", "--no-protel-ext", "--layers",
        ",".join(cu + ["F.Mask", "B.Mask", "F.Silkscreen", "B.Silkscreen", "Edge.Cuts"]), "-o", gdir + "/", brd)
    sep = any(n.endswith(("-PTH.drl", "-NPTH.drl")) for n in files)
    run(CLI, "pcb", "export", "drill", "--format", "excellon", "--excellon-units", "mm",
        *(["--excellon-separate-th"] if sep else []), "-o", gdir + "/", brd)
    stale, absent = [], []
    for n, b in files.items():
        if not n.endswith((".gbr", ".drl")) or "drl_map" in n: continue
        f = os.path.join(gdir, n)
        if not os.path.exists(f): absent.append(n); continue
        if strip_dates(b.decode("latin-1")) != strip_dates(open(f, encoding="latin-1").read()): stale.append(n)
    say(not stale and not absent, "FRESH ZIP", "every file matches the board" if not (stale or absent)
        else "stale: %s; not regenerated: %s" % (stale, absent))
    # 5. zip contents
    ok, lines = check_order_zip.check(brd, zpath)
    say(ok, "ZIP CONTENT", "copper layers, nets per layer, routed nets and holes read back from the zip")
    for l in lines:
        if l.startswith("FAIL"): print("              " + l)
    # 6. bypass caps
    t = open(brd).read(); bad = []
    for blk in re.split(r'\n\t\(footprint ', t)[1:]:
        ref = re.search(r'\(property "Reference" "(C\d+)"', blk)
        if not ref: continue
        val = re.search(r'\(property "Value" "([^"]*)"', blk).group(1)
        if not re.fullmatch(r'0?\.1\s*u?F?|100\s*nF?', val.strip(), re.I): continue
        p = [tuple(map(float, a.split()[:2])) for a in re.findall(r'\(pad "[^"]*" thru_hole \w+\s*\(at ([-\d. ]+)\)', blk)]
        if len(p) >= 2:
            pitch = ((p[0][0] - p[1][0]) ** 2 + (p[0][1] - p[1][1]) ** 2) ** .5
            if abs(pitch - 2.54) > 0.1: bad.append("%s %.2f mm" % (ref.group(1), pitch))
    say(not bad, "BYPASS CAPS", "all 0.1 uF at 2.54 mm" if not bad else "not 0.1\": %s" % ", ".join(bad))
    # 7. netlist proof
    KPY = "/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3"; here = os.path.dirname(os.path.abspath(__file__))
    if os.path.exists(sch):
        net = os.path.join(tmp, "sch.net"); run(CLI, "sch", "export", "netlist", "--format", "kicadsexpr", "-o", net, sch)
        r = run(sys.executable, os.path.join(here, "kicad", "compare_netlists.py"), net, brd)
        m = [l for l in r.stdout.splitlines() if l.startswith(("RESULT", "identical"))]
        say("RESULT: MATCH" in r.stdout, "NETLIST", "; ".join(m))
    # 8. planes
    if any(L.startswith("In") for L in cu):
        r = run(KPY, os.path.join(here, "kicad", "plane_check.py"), brd)
        lines = [l for l in r.stdout.splitlines() if l.startswith(("PASS", "FAIL", "no planes"))]
        say(r.returncode == 0, "PLANES", lines[0] if len(lines) == 1 else "")
        if len(lines) > 1: [print("              " + l) for l in lines]
    # 10. the redrawn schematic and the book, from the board's own netlist
    sdir = os.path.join(os.path.dirname(os.path.abspath(brd)), "schematic"); rnet = os.path.join(os.path.dirname(os.path.abspath(brd)), "reports", "netlist.net")
    if os.path.exists(os.path.join(sdir, "spec.py")):
        r = run(sys.executable, os.path.join(here, "kicad", "compare_netlists.py"), rnet, brd)
        if "RESULT: MATCH" not in r.stdout:
            say(False, "SCHEMATIC", "reports/netlist.net does not match the board: export it from the schematic again")
        else:
            g = run(sys.executable, os.path.join(here, "kicad", "sch", "gen_schematic.py"), sdir)
            b = run(sys.executable, os.path.join(here, "kicad", "sch", "make_book.py")) if g.returncode == 0 else g
            pdf = [l.split(":", 1)[1].strip() for l in g.stdout.splitlines() if l.startswith("PDF:")]
            say(g.returncode == 0 and b.returncode == 0, "SCHEMATIC", "redrawn, MATCH: %s; book rebuilt" % (pdf[0] if pdf else "?")
                if g.returncode == 0 and b.returncode == 0 else (g.stdout + g.stderr + b.stderr).strip().splitlines()[-1:])
    # 9. pictures from the zip's own copper gerbers
    try:
        from PIL import Image, ImageDraw
        outs = []
        for n in sorted(zcu):
            out = os.path.join(os.path.dirname(zpath), "check-" + n.replace(".gbr", ".png")); draw(files[n].decode("latin-1"), out); outs.append(os.path.basename(out))
        say(True, "PICTURES", "look at each by eye: %s" % ", ".join(outs))
    except ImportError:
        say(True, "PICTURES", "skipped (no PIL); view the zip in a gerber viewer instead")
    shutil.rmtree(tmp, ignore_errors=True)
    ok = all(results)
    print("\nRESULT:", "PASS - now look at the pictures, check the fab's gerber viewer and order %d layers" % layers if ok
          else "FAIL - do not order")
    return ok


def draw(g, out, px=8):
    """the tracks and pads of one copper gerber (fills drawn faintly), so missing tracks show at a glance"""
    from PIL import Image, ImageDraw
    m = re.search(r'%FSLAX\d(\d)', g); dec = int(m.group(1)) if m else 6
    aps = {}
    for a in re.finditer(r'%ADD(\d+)([A-Za-z]+)[^,]*,([\d.]+)', g): aps[int(a.group(1))] = float(a.group(3))
    x = y = 0; ap = 10; reg = False; segs = []; fl = []; regpts = []; polys = []
    for tok in re.split(r'\*', g.replace("\n", "")):
        tok = tok.strip("%")
        if tok == "G36": reg = True; regpts = []; continue
        if tok == "G37": reg = False; polys.append(regpts); continue
        a = re.fullmatch(r'D(\d+)', tok)
        if a and int(a.group(1)) >= 10: ap = int(a.group(1)); continue
        a = re.fullmatch(r'(?:G0?[123])?X(-?\d+)?Y?(-?\d+)?(?:I-?\d+J-?\d+)?D0?([123])|(?:G0?[123])?(?:X(-?\d+))?(?:Y(-?\d+))?(?:I-?\d+J-?\d+)?D0?([123])', tok)
        if not a: continue
        gx, gy, op = (a.group(4), a.group(5), a.group(6)) if a.group(6) else (a.group(1), a.group(2), a.group(3))
        nx = int(gx) / 10 ** dec if gx else x; ny = int(gy) / 10 ** dec if gy else y
        if reg: regpts.append((nx, ny))
        elif op == "1": segs.append((x, y, nx, ny, aps.get(ap, 0.2)))
        elif op == "3": fl.append((nx, ny, aps.get(ap, 1.0)))
        x, y = nx, ny
    pts = [(s[0], s[1]) for s in segs] + [(s[2], s[3]) for s in segs] + [(f[0], f[1]) for f in fl] + [p for q in polys for p in q]
    if not pts: Image.new("RGB", (200, 100), "white").save(out); return
    x0 = min(p[0] for p in pts) - 2; x1 = max(p[0] for p in pts) + 2; y0 = min(p[1] for p in pts) - 2; y1 = max(p[1] for p in pts) + 2
    W, H = int((x1 - x0) * px), int((y1 - y0) * px); im = Image.new("RGB", (W, H), "white"); dr = ImageDraw.Draw(im)
    P = lambda a, b: ((a - x0) * px, (y1 - b) * px)
    for q in polys:
        if len(q) > 2: dr.polygon([P(*p) for p in q], fill=(225, 232, 245))
    for a, b, c, e, w in segs:
        dr.line([P(a, b), P(c, e)], fill=(200, 40, 40), width=max(1, int(w * px)))   # every width: a 2026-10-27 review
                                                                                 # found 2.5 mm feeds left out (w < 2.0)
    for a, b, w in fl:
        r = max(1, w * px / 2); cx, cy = P(a, b); dr.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(40, 40, 40))
    im.save(out)


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) != 4 or a[2] != "--layers": sys.exit(__doc__)
    sys.exit(0 if main(a[0], a[1], int(a[3])) else 1)
