#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-05
"""One-off: create the Memory Rev D schematic from Rev C. Kept as the record of exactly what changed.

Rev D = Rev C with three changes (plus RN1-RN4 valued 4.7k) (hardware/memory/REVIEW.md):
  1. EPROM VPP (IC3, IC5 pin 1) tied to VCC instead of GND.
  2. IC10 (74LS00 LED driver) and its bypass capacitor C3 removed.
  3. Each activity LED runs +5V -> LED -> 470R -> that chip's gated !CE, so it lights only while the chip is enabled.
     The chip-select nets get names: RAM_LO_CE (IC1), RAM_HI_CE (IC11), EPROM_LO_CE (IC3), EPROM_HI_CE (IC5).
The edits are applied in memory to the Rev C Fusion export; then tools/kicad/eagle_sch_to_kicad.py writes the KiCad schematic.
No Eagle Rev D file is kept: from here on the KiCad project in this folder is the master (MASTER marker).
usage: make_schematic.py   (run from anywhere; writes into hardware/memory/kicad/rev-d/)
"""
import os, sys, math, re, subprocess, tempfile, xml.etree.ElementTree as ET
HERE = os.path.dirname(os.path.abspath(__file__)); DEST = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(DEST, "..", "..", "..", ".."))
SRC = os.path.join(ROOT, "hardware/memory/eagle/rev-c/fusion-export/mem3-c.sch")
CONV = os.path.join(ROOT, "tools/kicad/eagle_sch_to_kicad.py")

tree = ET.parse(SRC); root = tree.getroot(); sch = root.find("drawing/schematic")
sheet = sch.find("sheets/sheet"); nets = sheet.find("nets")
libs = {l.get("name"): l for l in sch.find("libraries")}
parts = {p.get("name"): p for p in sch.find("parts")}
insts = sheet.find("instances")

def net(name):
    for n in nets:
        if n.get("name") == name: return n
    n = ET.SubElement(nets, "net", {"name": name, "class": "0"}); return n

def pin_world(part, gate, pin):
    p = parts[part]; lib = libs[p.get("library")]
    ds = lib.find("devicesets/deviceset[@name='%s']" % p.get("deviceset"))
    sym = lib.find("symbols/symbol[@name='%s']" % ds.find("gates/gate[@name='%s']" % gate).get("symbol"))
    pe = sym.find("pin[@name='%s']" % pin); px, py = float(pe.get("x")), float(pe.get("y"))
    inst = [i for i in insts if i.get("part") == part and i.get("gate") == gate][0]
    rot = inst.get("rot") or "R0"; a = math.radians(float(re.sub(r"[^\d.]", "", rot) or 0))
    if "M" in rot: px = -px
    return (round(float(inst.get("x")) + px * math.cos(a) - py * math.sin(a), 3),
            round(float(inst.get("y")) + px * math.sin(a) + py * math.cos(a), 3))

def ends(w): return [(round(float(w.get("x1")), 3), round(float(w.get("y1")), 3)), (round(float(w.get("x2")), 3), round(float(w.get("y2")), 3))]

def remove_part(name):
    """drop the part, its instances and its pinrefs. A wire that ran only to one of its pins (a stub: nothing else meets
    that end) is removed; wires that merely pass through a pin position (Rev C chains the 74151 outputs through IC10's
    inputs to the 74LS32) stay, since their ends still meet each other. One pass, no cascading."""
    for seg in [s for n in nets for s in n.findall("segment")]:
        gone = []
        for pr in list(seg.findall("pinref")):
            if pr.get("part") == name:
                gone.append(pin_world(name, pr.get("gate"), pr.get("pin"))); seg.remove(pr)
        if not gone: continue
        deg = {}
        for w in seg.findall("wire"):
            for e in ends(w): deg[e] = deg.get(e, 0) + 1
        junc = {(round(float(j.get("x")), 3), round(float(j.get("y")), 3)) for j in seg.findall("junction")}
        for w in [w for w in seg.findall("wire") if any(e in gone and deg[e] == 1 and e not in junc for e in ends(w))]:
            seg.remove(w)
    for i in [i for i in insts if i.get("part") == name]: insts.remove(i)
    sch.find("parts").remove(parts.pop(name))

# 1. VPP -> VCC: the GND symbols V7 (IC3) and V8 (IC5) become VCC symbols turned 180 deg, pin on the same spot
for sup in ("V7", "V8"):
    seg = [s for n in nets for s in n.findall("segment") if any(pr.get("part") == sup for pr in s.findall("pinref"))][0]
    old_net = [n for n in nets if seg in n.findall("segment")][0]
    p = parts[sup]; p.set("library", "supply2"); p.set("deviceset", "VCC")
    inst = [i for i in insts if i.get("part") == sup][0]; inst.set("gate", "G$1"); inst.set("rot", "R180")
    for pr in seg.findall("pinref"):
        if pr.get("part") == sup: pr.set("gate", "G$1"); pr.set("pin", "VCC")
    old_net.remove(seg); net("VCC").append(seg)

# 3a. name the four gated chip-select nets
for old, new in (("N$35", "RAM_LO_CE"), ("N$47", "RAM_HI_CE"), ("N$44", "EPROM_LO_CE"), ("N$37", "EPROM_HI_CE")):
    net(old).set("name", new)

# 3b. LED anodes: the wire from IC10's output now ends on a new VCC symbol (placed where the IC10 pin was)
led_anode_nets = {"N$58": ("IC10", "A", "O"), "N$62": ("IC10", "B", "O"), "N$19": ("IC10", "C", "O"), "N$57": ("IC10", "D", "O")}
for nname, (pp, gg, pin) in led_anode_nets.items():
    n = net(nname); seg = n.find("segment"); x, y = pin_world(pp, gg, pin)
    for pr in list(seg.findall("pinref")):
        if pr.get("part") == pp: seg.remove(pr)
    sup = "VLED" + nname[2:]
    ET.SubElement(sch.find("parts"), "part", {"name": sup, "library": "supply2", "deviceset": "VCC", "device": ""})
    parts[sup] = sch.find("parts")[-1]
    ET.SubElement(insts, "instance", {"part": sup, "gate": "G$1", "x": str(x), "y": str(y + 2.54)})
    ET.SubElement(seg, "pinref", {"part": sup, "gate": "G$1", "pin": "VCC"})
    nets.remove(n); net("VCC").append(seg)

# 3c. resistor ends: off the shared GND symbols, each onto its chip-select net (wire shortened to half so the two stubs never meet)
for gsym, moves in (("V6", {("R4", "1"): "EPROM_LO_CE", ("R5", "2"): "EPROM_HI_CE"}),
                    ("GND6", {("R2", "1"): "RAM_LO_CE", ("R3", "2"): "RAM_HI_CE"})):
    seg = [s for n in nets for s in n.findall("segment") if any(pr.get("part") == gsym for pr in s.findall("pinref"))][0]
    for (rp, rpin), target in moves.items():
        pr = [p for p in seg.findall("pinref") if p.get("part") == rp and p.get("pin") == rpin][0]
        pos = pin_world(rp, pr.get("gate"), rpin)
        w = [w for w in seg.findall("wire") if pos in ends(w)][0]
        (ax, ay), (bx, by) = ends(w); far = (bx, by) if (ax, ay) == pos else (ax, ay)
        mid = (round((pos[0] + far[0]) / 2, 3), round((pos[1] + far[1]) / 2, 3))
        new = ET.SubElement(net(target), "segment")
        ET.SubElement(new, "pinref", {"part": rp, "gate": pr.get("gate"), "pin": rpin})
        ET.SubElement(new, "wire", {"x1": str(pos[0]), "y1": str(pos[1]), "x2": str(mid[0]), "y2": str(mid[1]), "width": "0.1524", "layer": "91"})
        seg.remove(pr); seg.remove(w)
    gnet = [n for n in nets if seg in n.findall("segment")][0]; gnet.remove(seg)
    for i in [i for i in insts if i.get("part") == gsym]: insts.remove(i)
    sch.find("parts").remove(parts.pop(gsym))

# 4. the pull-up networks are 4.7k (Ken, 2026-10-05; not recorded in the Eagle files)
for rn in ("RN1", "RN2", "RN3", "RN4"): parts[rn].set("value", "4.7k")
# capacitor values written out in full (Eagle had ".1" and "10.0")
for name, part in parts.items():
    if name.startswith("C") and part.get("value") in (".1", "0.1"): part.set("value", "0.1uF")
    if name == "C8": part.set("value", "10uF")
# real part numbers where Eagle left the value empty (the converter would show the deviceset, e.g. "74*151")
PARTNO = {"74*151": "74HCT151", "74*32": "74LS32", "4042": "CD4042", "4050": "CD4050", "LED": "LED 5mm"}
for name, part in parts.items():
    if not part.get("value") and part.get("deviceset") in PARTNO: part.set("value", PARTNO[part.get("deviceset")])
    if name in ("SV1", "SV2"): part.set("value", "2x8 header")
    if name in ("SV3", "SV4"): part.set("value", "1x8 header")
    if name == "U$1": part.set("value", "System-5 bus 30-pin")

# 3d. redraw the LED section in the empty strip below the circuit: one row per chip, VCC -> LED -> 470R -> its CE net,
#     in the board's order (EPROM HI, EPROM LO, RAM HI, RAM LO). The rows from 3b/3c are removed first.
LEDROWS = [("LED5", "R5", "EPROM_HI_CE", "1"), ("LED4", "R4", "EPROM_LO_CE", "2"),
           ("LED3", "R3", "RAM_HI_CE", "1"), ("LED2", "R2", "RAM_LO_CE", "2")]   # last field: the R pin that meets the LED
movers = {x for row in LEDROWS for x in row[:2]}
for n in list(nets):
    for seg in list(n.findall("segment")):
        if any(pr.get("part") in movers or pr.get("part", "").startswith("VLED") for pr in seg.findall("pinref")):
            n.remove(seg)
    if not n.findall("segment"): nets.remove(n)
for name in [k for k in parts if k.startswith("VLED")]:
    for i in [i for i in insts if i.get("part") == name]: insts.remove(i)
    sch.find("parts").remove(parts.pop(name))
X0, Y0, DY = -170.18, -25.4, -12.7
plain = sheet.find("plain")
t = ET.SubElement(plain, "text", {"x": str(X0), "y": str(Y0 + 7.62), "size": "2.54", "layer": "97"})
t.text = "ACTIVITY LEDS - each lights while its chip is enabled (Rev D)"
def wire(seg, x1, y1, x2, y2):
    ET.SubElement(seg, "wire", {"x1": "%.2f" % x1, "y1": "%.2f" % y1, "x2": "%.2f" % x2, "y2": "%.2f" % y2, "width": "0.1524", "layer": "91"})
for k, (led, res, ce, rled) in enumerate(LEDROWS):
    y = Y0 + DY * k; x = X0
    sup = "VLED%d" % k
    ET.SubElement(sch.find("parts"), "part", {"name": sup, "library": "supply2", "deviceset": "VCC", "device": ""}); parts[sup] = sch.find("parts")[-1]
    ET.SubElement(insts, "instance", {"part": sup, "gate": "G$1", "x": "%.2f" % x, "y": "%.2f" % (y + 2.54)})
    for part, px, rot in ((led, x + 15.24, "R90"), (res, x + 30.48, "R180" if rled == "2" else "R0")):
        inst = [i for i in insts if i.get("part") == part][0]
        for a in list(inst): inst.remove(a)                      # drop the smashed name/value positions: default placement
        inst.attrib.pop("smashed", None); inst.set("x", "%.2f" % px); inst.set("y", "%.2f" % y); inst.set("rot", rot)
    rce = "1" if rled == "2" else "2"
    s1 = ET.SubElement(net("VCC"), "segment")
    ET.SubElement(s1, "pinref", {"part": sup, "gate": "G$1", "pin": "VCC"}); ET.SubElement(s1, "pinref", {"part": led, "gate": "G$1", "pin": "A"})
    wire(s1, x, y, x + 12.7, y)
    s2 = ET.SubElement(net("LED_%s" % led), "segment")
    ET.SubElement(s2, "pinref", {"part": led, "gate": "G$1", "pin": "C"}); ET.SubElement(s2, "pinref", {"part": res, "gate": "G$1", "pin": rled})
    wire(s2, x + 20.32, y, x + 25.4, y)
    s3 = ET.SubElement(net(ce), "segment")
    ET.SubElement(s3, "pinref", {"part": res, "gate": "G$1", "pin": rce})
    wire(s3, x + 35.56, y, x + 45.72, y)
    ET.SubElement(s3, "label", {"x": "%.2f" % (x + 45.72), "y": "%.2f" % y, "size": "1.778", "layer": "95"})

# 2. IC10 and C3 out
remove_part("IC10"); remove_part("C3")
for n in [n for n in nets if not n.findall("segment")]: nets.remove(n)

tmp = tempfile.mkdtemp(prefix="mem3d-"); out = os.path.join(tmp, "mem3-d.sch"); tree.write(out, encoding="utf-8", xml_declaration=True)
r = subprocess.run([sys.executable, CONV, out, DEST, "memory-rev-d"], capture_output=True, text=True)
print(r.stdout.strip()); print(r.stderr.strip()[-2000:]) if r.returncode else None
sys.exit(r.returncode)
