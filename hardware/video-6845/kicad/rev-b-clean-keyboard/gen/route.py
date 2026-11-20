#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-20 (after memory Rev F's gen/route.py)
"""route.py dsn|import - Freerouting in and out for Rev B-Clean-Keyboard (run with KiCad's Python; gen/build.sh does).
  dsn     ../video-6845-rev-b-clean-keyboard.dsn from make_board.py's board. Rev B's tracks are locked, so Freerouting
          keeps them and adds only the keyboard section's connections, on the same two layers. Then a fixed order
          (tools/kicad/dsn_order.py), shuffled by ROUTE_SEED below or the ROUTE_SEED environment variable, so a rebuild
          routes the same way.
  import  the session file back into the board (tools/kicad/kicad_route.py import_ses), then any new (unlocked) track
          left with an end that meets nothing taken out again (as memory Rev F's route.py does).
"""
import os, sys, re
import pcbnew
HERE = os.path.dirname(os.path.abspath(__file__)); DEST = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(DEST, "..", "..", "..", ".."))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(ROOT, "tools", "kicad"))
import keyboard as K
import kicad_route, dsn_order
PCB = os.environ.get("ROUTE_PCB") or os.path.join(DEST, K.NEW + ".kicad_pcb")   # (ROUTE_PCB: a copy, for a seed search)
ROUTE_SEED = 2      # seeds 0-5 on this placement each leave 1 to 7 of the 157 connections open, whatever the pass limit;
#                     gen/route_leftovers.py joins them on every one. Seed 2 leaves the fewest (one)


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "dsn":
        kicad_route.export_dsn(PCB)
        dsn = PCB[:-len(".kicad_pcb")] + ".dsn"; t = open(dsn).read()
        seed = os.environ.get("ROUTE_SEED")
        seed = int(seed) if seed not in (None, "") else ROUTE_SEED
        t = dsn_order.fixed(t, seed)
        open(dsn, "w").write(t)
        print("dsn: layers", re.findall(r'\(layer (\S+)\s*\(type (\w+)', t), "| fixed order, route seed", seed)
    elif cmd == "import":
        kicad_route.import_ses(PCB, PCB[:-len(".kicad_pcb")] + ".ses")
        import json, subprocess, tempfile
        CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
        gone = set()
        for _ in range(10):                              # DRC's own word on what dangles; only new tracks go
            rep = os.path.join(tempfile.mkdtemp(), "drc.json")
            subprocess.run([CLI, "pcb", "drc", "--format", "json", "-o", rep, PCB], capture_output=True)
            ids = {i["uuid"] for v in json.load(open(rep))["violations"] if v["type"] == "track_dangling" for i in v["items"]}
            b = pcbnew.LoadBoard(PCB)
            more = {t.m_Uuid.AsString() for t in b.GetTracks() if t.m_Uuid.AsString() in ids and not t.IsLocked()}
            if not more:
                break
            gone |= more
            forms = kicad_route.top_forms(open(PCB).read())
            open(PCB, "w").write("(kicad_pcb\n\t" + "\n\t".join(f for f in forms if not (f.startswith("(segment") and any(u in f for u in more))) + "\n)\n")
        b = pcbnew.LoadBoard(PCB); b.BuildConnectivity()
        new = [t for t in b.GetTracks() if not t.IsLocked()]
        print("dangling new tracks taken out: %d; new: %d segments and %d vias; connections still open: %d" % (
            len(gone), sum(t.Type() != pcbnew.PCB_VIA_T for t in new), sum(t.Type() == pcbnew.PCB_VIA_T for t in new),
            b.GetConnectivity().GetUnconnectedCount(False)))
    else:
        sys.exit(__doc__)
    sys.stdout.flush(); os._exit(0)


if __name__ == "__main__":
    main()
