#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-19
"""Check a JLCPCB order zip against its KiCad board, from the files that would be uploaded.

Written after the 2026-10-09 order: the bus driver A and memory Rev D boards were routed on four copper layers, but
their zips held only the top and bottom copper, so most tracks were never sent. DRC passed, because it checks the
board file, not the zip. This reads the zip back:
  1. COPPER LAYERS  the zip has one copper gerber per copper layer of the board, and the job file agrees
  2. NETS           on each copper layer, every net with tracks or vias there is named in that layer's gerber
                    (KiCad's X2 net attributes, %TO.N,<net>*%), and the gerber has at least as many strokes as tracks
  3. ROUTED NETS    every net with two or more pads has copper (tracks or a zone) on a layer that is in the zip
  4. DRILL          the drill file has one hole per plated pad and via (and per non-plated hole)
usage: check_order_zip.py <board.kicad_pcb> <order.zip>        exit status 1 if anything fails
"""
import re, sys, json, zipfile, collections


def board(path):
    t = open(path).read()
    head = t[:t.find("(setup")] if "(setup" in t else t
    cu = [n for n, kind in re.findall(r'\(\d+ "([^"]+\.Cu)" (signal|power|mixed|jumper)', head)]
    tracks = collections.defaultdict(collections.Counter)            # layer -> net -> segments
    for kind, body in re.findall(r'\n\t\((segment|arc)\b(.*?)\n\t\)', t, re.S):
        L = re.search(r'\(layer "([^"]+)"\)', body).group(1); n = re.search(r'\(net "([^"]*)"\)', body)
        tracks[L][n.group(1) if n else ""] += 1
    vias = collections.Counter()
    for body in re.findall(r'\n\t\(via\b(.*?)\n\t\)', t, re.S):
        n = re.search(r'\(net "([^"]*)"\)', body); vias[n.group(1) if n else ""] += 1
    zones = collections.defaultdict(set)                               # net -> layers
    for body in re.findall(r'\n\t\(zone\b(.*?)\n\t\)', t, re.S):
        if "(keepout" in body: continue
        n = re.search(r'\(net "([^"]*)"\)', body); ls = re.search(r'\(layers? ((?:"[^"]+"\s*)+)\)', body)
        if n and ls:
            for L in re.findall(r'"([^"]+)"', ls.group(1)):
                if L.endswith(".Cu"): zones[n.group(1)].add(L)
    pads = collections.Counter(); holes = 0
    for fp in re.findall(r'\n\t\(footprint\b(.*?)\n\t\)', t, re.S):
        for pad in re.findall(r'\(pad "[^"]*" (thru_hole|np_thru_hole|smd|connect)(.*?)\n\t\t\)', fp, re.S):
            if pad[0] in ("thru_hole", "np_thru_hole"): holes += 1
            n = re.search(r'\(net "([^"]*)"\)', pad[1])
            if n and n.group(1) and not n.group(1).startswith("unconnected-"): pads[n.group(1)] += 1
    return cu, tracks, vias, zones, pads, holes + sum(vias.values())


def check(brd, zpath):
    cu, tracks, vias, zones, pads, nholes = board(brd)
    z = zipfile.ZipFile(zpath); files = {n: z.read(n) for n in z.namelist() if not n.endswith("/")}
    ok = True; out = []
    def say(good, msg):
        nonlocal ok; ok &= good; out.append(("PASS " if good else "FAIL ") + msg)
    # 1. copper layers
    copper = {}                                                        # board layer name -> gerber text
    for name, data in files.items():
        txt = data.decode("latin-1"); m = re.search(r'%TF\.FileFunction,Copper,L(\d+),(\w+)', txt)
        if m:
            k = int(m.group(1)); L = "F.Cu" if m.group(2) == "Top" else "B.Cu" if m.group(2) == "Bot" else "In%d.Cu" % (k - 1)
            copper[L] = txt
    say(sorted(copper) == sorted(cu), "copper layers: board %s, zip %s" % (cu, sorted(copper)))
    job = [d for n, d in files.items() if n.endswith(".gbrjob")]
    if job:
        lj = json.loads(job[0]).get("GeneralSpecs", {}).get("LayerNumber")
        say(lj == len(cu), "job file LayerNumber %s, board copper layers %d" % (lj, len(cu)))
    # 2. nets per layer
    used = set(tracks) | ({L for L in cu} if vias else set())
    for L in sorted(used):
        if L not in copper: say(False, "%s carries %d track segments but has no gerber in the zip" % (L, sum(tracks[L].values()))); continue
        g = copper[L]; named = set(re.findall(r'%TO\.N,([^*]*)\*%', g)); strokes = len(re.findall(r'D01\*', g))
        want = {n for n in tracks[L] if n} | {n for n in vias if n}
        missing = sorted(n for n in want if n not in named)
        say(not missing, "%s: %d nets with copper here, all named in the gerber%s" % (L, len(want), "" if not missing else "; MISSING %s" % missing[:10]))
        say(strokes >= sum(tracks[L].values()), "%s: %d strokes in the gerber for %d track segments" % (L, strokes, sum(tracks[L].values())))
    # 3. every multi-pad net has copper on a layer that is in the zip
    unrouted = []
    for n, k in pads.items():
        if k < 2: continue
        layers = {L for L in tracks if tracks[L].get(n)} | zones.get(n, set())
        if not (layers & set(copper)) : unrouted.append(n)
    say(not unrouted, "%d nets with 2+ pads, each has tracks or a zone on a layer in the zip%s" % (sum(1 for k in pads.values() if k >= 2), "" if not unrouted else "; NONE for %s" % unrouted[:10]))
    # 4. drill
    drl = [d.decode("latin-1") for n, d in files.items() if n.lower().endswith((".drl", ".xln"))]
    hits = sum(len(re.findall(r'^X-?[\d.]+Y-?[\d.]+', d, re.M)) for d in drl)
    say(hits == nholes, "drill: %d hits in the zip, %d holes on the board" % (hits, nholes))
    return ok, out


if __name__ == "__main__":
    if len(sys.argv) != 3: sys.exit(__doc__)
    ok, out = check(sys.argv[1], sys.argv[2])
    print("\n".join(out)); print("RESULT:", "PASS" if ok else "FAIL"); sys.exit(0 if ok else 1)
