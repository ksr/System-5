#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-01
"""route.py dsn|import BOARD_DIR - Freerouting in and out for a VIDEO-G board (run with KiCad's Python).

  dsn     BOARD_DIR/<PROJ>.dsn from the unrouted board: In1.Cu (GND) and In2.Cu (+5V) become power layers and GND/+5V
          leave the network, so Freerouting routes the signals on F.Cu/B.Cu only and every GND/+5V pin (a through-hole
          pad) lands in its plane - memory Rev E's method (hardware/memory/kicad/rev-e/gen/make_planes.py).
          The DSN is then put in a fixed order (2026-11-17; tools/kicad/dsn_order.py, shared with CPU Rev D). KiCad writes its components, images and pins in an order
          that changes every time make_board.py makes the board (each build gives the footprints new UUIDs), and
          Freerouting's result depends on that order: before this, two builds of the same placement could route quite
          differently, one completely and one leaving a net open. Now the same board always routes the same way.
          ROUTE_SEED in gen/place.py (or the ROUTE_SEED environment variable, which wins) shuffles the component order
          reproducibly: another seed is another try when one order leaves a net unrouted. 0 or none = the sorted order.
          The parts' drawn outlines (silkscreen, fab and courtyard lines, which KiCad writes into each image) are left
          out: Freerouting routes around pads and keepouts, not outlines, yet they changed its result - adding
          courtyards to two footprints turned a complete route into one that stalled - so a silkscreen tidy-up must
          not reroute a board.
  import  BOARD_DIR/<PROJ>.ses back into the board (tools/kicad/kicad_route.py import_ses: stitch, edge heal, zone fill)
Freerouting runs between them, from BOARD_DIR: java -jar ~/freerouting/freerouting.jar -de P.dsn -do P.ses -mt 1
"""
import os, sys, re, importlib.util
import pcbnew
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "kicad")); import kicad_route, dsn_order

PLANES = (("In1.Cu", "GND"), ("In2.Cu", "+5V"))


def load(board_dir, name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(board_dir, "gen", name + ".py"))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def main():
    cmd, board_dir = sys.argv[1], os.path.abspath(sys.argv[2])
    N = load(board_dir, "netlist")
    PCB = os.path.join(board_dir, N.PROJ + ".kicad_pcb")
    if cmd == "dsn":
        kicad_route.export_dsn(PCB)
        dsn = PCB[:-len(".kicad_pcb")] + ".dsn"; t = open(dsn).read()
        for lname, _ in PLANES:
            t = re.sub(r'(\(layer %s\s*\(type )signal' % re.escape(lname), r'\1power', t)
        for _, net in PLANES:
            t = re.sub(r'\n\s*\(net "?%s"?\s*\(pins[^)]*\)\s*\)' % re.escape(net), '', t)    # ("+5V" may be quoted)
            t = re.sub(r'(\(class [^\n]*?) "?%s"?(?=[ )\n])' % re.escape(net), r'\1', t)
        seed = os.environ.get("ROUTE_SEED")
        seed = int(seed) if seed not in (None, "") else int(getattr(load(board_dir, "place"), "ROUTE_SEED", 0))
        t = dsn_order.fixed(t, seed, getattr(load(board_dir, "place"), "ROUTE_AS", None))   # (ROUTE_AS: a renamed net
        #                                                           keeps its old name's place in the order)
        open(dsn, "w").write(t)
        print("dsn: layers", re.findall(r'\(layer (\S+)\s*\(type (\w+)', t), "| GND/+5V still routed:",
              bool(re.search(r'\(net "?(GND|\+5V)"?\s*\(pins', t)), "| fixed order, route seed", seed)
    elif cmd == "import":
        kicad_route.import_ses(PCB, PCB[:-len(".kicad_pcb")] + ".ses")
    else:
        sys.exit(__doc__)
    sys.stdout.flush(); os._exit(0)


if __name__ == "__main__":
    main()
