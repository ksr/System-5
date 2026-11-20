#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-17
"""route.py dsn|import - Freerouting in and out for CPU Rev D (run with KiCad's Python; gen/build.sh does).

  dsn     ../cpu-rev-d.dsn from the unrouted board: tools/kicad/kicad_route.py export_dsn (the GND pours left out, so
          Freerouting routes GND as tracks too; the project's Power class, cpu-rev-d.kicad_pro, makes +5V 0.5 mm
          wide), then put in a fixed order (tools/kicad/dsn_order.py, as VIDEO-G's), so the board routes the same
          way every time. ROUTE_SEED below, or the ROUTE_SEED environment variable (which wins), shuffles that order
          reproducibly: another seed is another try when one order leaves a net unrouted. 0 = the sorted order.
  import  ../cpu-rev-d.ses back into the board (kicad_route.import_ses: stitch, edge heal, zone fill)
"""
import os, sys
import pcbnew
HERE = os.path.dirname(os.path.abspath(__file__)); DEST = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(DEST, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "kicad")); import kicad_route, dsn_order
PROJ = "cpu-rev-d"
ROUTE_SEED = 0          # 2026-11-18, with JP1 at the top edge, the EF blocks 1.5 in nearer the bus and the 9070-1W for
                        # SW1: seed 0 (the sorted order) routes every net, 1029 segments, 35 vias (2 leaves two +5V links
                        # open; the others not tried). Before those moves: 1; before the slot's renumbering: 3


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    pcb = os.path.join(DEST, PROJ + ".kicad_pcb")
    if cmd == "dsn":
        kicad_route.export_dsn(pcb)
        dsn = os.path.join(DEST, PROJ + ".dsn")
        seed = os.environ.get("ROUTE_SEED")
        seed = int(seed) if seed not in (None, "") else ROUTE_SEED
        t = open(dsn).read()                            # read first: opening it to write empties it
        open(dsn, "w").write(dsn_order.fixed(t, seed))
        print("dsn: fixed order, route seed", seed)
    elif cmd == "import":
        kicad_route.import_ses(pcb, os.path.join(DEST, PROJ + ".ses"))
    else:
        sys.exit(__doc__)
    sys.stdout.flush(); os._exit(0)                     # skip pcbnew's exit hang (the work is saved)


if __name__ == "__main__":
    main()
