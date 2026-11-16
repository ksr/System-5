#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-01
"""route.py dsn|import BOARD_DIR - Freerouting in and out for a VIDEO-G board (run with KiCad's Python).

  dsn     BOARD_DIR/<PROJ>.dsn from the unrouted board: In1.Cu (GND) and In2.Cu (VCC) become power layers and GND/VCC
          leave the network, so Freerouting routes the signals on F.Cu/B.Cu only and every GND/VCC pin (a through-hole
          pad) lands in its plane - memory Rev E's method (hardware/memory/kicad/rev-e/gen/make_planes.py)
  import  BOARD_DIR/<PROJ>.ses back into the board (tools/kicad/kicad_route.py import_ses: stitch, edge heal, zone fill)
Freerouting runs between them, from BOARD_DIR: java -jar ~/freerouting/freerouting.jar -de P.dsn -do P.ses -mt 1
"""
import os, sys, re, importlib.util
import pcbnew
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "kicad")); import kicad_route

cmd, board_dir = sys.argv[1], os.path.abspath(sys.argv[2])
spec = importlib.util.spec_from_file_location("netlist", os.path.join(board_dir, "gen", "netlist.py"))
sys.path.insert(0, HERE); N = importlib.util.module_from_spec(spec); spec.loader.exec_module(N)
PCB = os.path.join(board_dir, N.PROJ + ".kicad_pcb"); PLANES = (("In1.Cu", "GND"), ("In2.Cu", "VCC"))

if cmd == "dsn":
    kicad_route.export_dsn(PCB)
    dsn = PCB[:-len(".kicad_pcb")] + ".dsn"; t = open(dsn).read()
    for lname, _ in PLANES:
        t = re.sub(r'(\(layer %s\s*\(type )signal' % re.escape(lname), r'\1power', t)
    for _, net in PLANES:
        t = re.sub(r'\n\s*\(net %s\s*\(pins[^)]*\)\s*\)' % re.escape(net), '', t)
        t = re.sub(r'(\(class [^\n]*?) %s(?=[ )\n])' % re.escape(net), r'\1', t)
    open(dsn, "w").write(t)
    print("dsn: layers", re.findall(r'\(layer (\S+)\s*\(type (\w+)', t), "| GND/VCC still routed:",
          bool(re.search(r'\(net (GND|VCC)\s*\(pins', t)))
elif cmd == "import":
    kicad_route.import_ses(PCB, PCB[:-len(".kicad_pcb")] + ".ses")
else:
    sys.exit(__doc__)
sys.stdout.flush(); os._exit(0)
