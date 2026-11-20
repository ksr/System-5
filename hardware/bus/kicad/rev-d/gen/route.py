#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-18 (from the IO panel's gen/route.py)
"""route.py dsn|import - Freerouting in and out for the bus Rev D (run with KiCad's Python; gen/build.sh does).

  dsn     ../s5bus-d.dsn from the unrouted board: tools/kicad/kicad_route.py export_dsn (the GND pour left out, so
          Freerouting routes GND as tracks too; the locked bus rows and supply feeds stay fixed), then put in a fixed
          order (tools/kicad/dsn_order.py, as VIDEO-G's and the IO panel's), so the board routes the same way every
          time. ROUTE_SEED below, or the ROUTE_SEED environment variable (which wins), shuffles that order
          reproducibly: another seed is another try when one order leaves a net unrouted. 0 = the sorted order.
  import  ../s5bus-d.ses back into the board (kicad_route.import_ses: stitch, edge heal, zone fill)
"""
import os, sys
import pcbnew
HERE = os.path.dirname(os.path.abspath(__file__)); DEST = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(DEST, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "kicad")); import kicad_route, dsn_order
PROJ = "s5bus-d"
ROUTE_SEED = 0


def tees(pcb):
    """Freerouting may end a track in the middle of a locked feed (the +5V riser): connected copper, but KiCad's DRC
    calls such an end dangling. Split the feed there, so the end meets a segment's end. Nothing is deleted (deleting
    breaks pcbnew's iteration): the segment is shortened to the junction and a new one carries on from it."""
    b = pcbnew.LoadBoard(pcb); tol = pcbnew.FromMM(0.001); n = 0
    tracks = [t for t in b.GetTracks() if t.GetClass() == "PCB_TRACK"]
    for a in list(tracks):
        for p in (a.GetStart(), a.GetEnd()):
            for t in list(tracks):
                if t is a or t.GetNetCode() != a.GetNetCode() or t.GetLayer() != a.GetLayer():
                    continue
                s, e = t.GetStart(), t.GetEnd()
                if p == s or p == e:
                    continue
                dx, dy = e.x - s.x, e.y - s.y; L2 = dx * dx + dy * dy
                if not L2:
                    continue
                k = ((p.x - s.x) * dx + (p.y - s.y) * dy) / L2
                if not 0 < k < 1 or abs((p.x - s.x) * dy - (p.y - s.y) * dx) / L2 ** 0.5 > tol:
                    continue
                c = pcbnew.PCB_TRACK(b); c.SetStart(p); c.SetEnd(e); c.SetLayer(t.GetLayer()); c.SetWidth(t.GetWidth())
                c.SetNetCode(t.GetNetCode()); c.SetLocked(t.IsLocked()); b.Add(c); tracks.append(c)
                t.SetEnd(p); n += 1
    if n:
        pcbnew.SaveBoard(pcb, b)
    print("tees: %d track(s) split where another ends on them" % n)


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
        tees(pcb)
    else:
        sys.exit(__doc__)
    sys.stdout.flush(); os._exit(0)                     # skip pcbnew's exit hang (the work is saved)


if __name__ == "__main__":
    main()
