#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-18 (after VIDEO-G's common/route.py)
"""route.py dsn|import - Freerouting in and out for Rev F (run with KiCad's Python; gen/build.sh does).
  dsn     ../memory-rev-f.dsn from make_board.py's board: In1.Cu (GND) and In2.Cu (VCC) become power layers and GND / VCC
          leave the network, so Freerouting routes the signals on F.Cu / B.Cu only and every GND / VCC pin lands in its
          plane (memory Rev E's method, ../../rev-e/gen/make_planes.py). Rev E's tracks are locked, so Freerouting keeps
          them and adds only the EEPROM sockets' new connections. Then a fixed order (tools/kicad/dsn_order.py), shuffled
          by ROUTE_SEED below or the ROUTE_SEED environment variable, so a rebuild routes the same way.
  import  ../memory-rev-f.ses back into the board (tools/kicad/kicad_route.py import_ses: stitch, edge heal, zone fill),
          then any new (unlocked) track left with an end that meets nothing taken out again: Freerouting bridged a
          0.05 mm step in one of Rev E's tracks (IC4's D6: pin 13, RN3, SV1) that KiCad already counts as joined, and left a stub
"""
import os, sys, re
import pcbnew
HERE = os.path.dirname(os.path.abspath(__file__)); DEST = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(DEST, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "kicad")); import kicad_route, dsn_order
PCB = os.path.join(DEST, "memory-rev-f.kicad_pcb")
PLANES = (("In1.Cu", "GND"), ("In2.Cu", "VCC"))
ROUTE_SEED = 1                                           # 0 and 3 leave JP2 pin 2 (A14) unrouted since R6 and R7 stand upright


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "dsn":
        kicad_route.export_dsn(PCB)
        dsn = PCB[:-len(".kicad_pcb")] + ".dsn"; t = open(dsn).read()
        for lname, _ in PLANES:
            t = re.sub(r'(\(layer %s\s*\(type )signal' % re.escape(lname), r'\1power', t)
        for _, net in PLANES:
            t = re.sub(r'\n\s*\(net "?%s"?\s*\(pins[^)]*\)\s*\)' % re.escape(net), '', t)
            t = re.sub(r'(\(class [^\n]*?) "?%s"?(?=[ )\n])' % re.escape(net), r'\1', t)
        seed = os.environ.get("ROUTE_SEED")
        seed = int(seed) if seed not in (None, "") else ROUTE_SEED
        t = dsn_order.fixed(t, seed)
        open(dsn, "w").write(t)
        print("dsn: layers", re.findall(r'\(layer (\S+)\s*\(type (\w+)', t), "| GND/VCC still routed:",
              bool(re.search(r'\(net "?(GND|VCC)"?\s*\(pins', t)), "| fixed order, route seed", seed)
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
        if gone:
            b = pcbnew.LoadBoard(PCB); pcbnew.ZONE_FILLER(b).Fill(b.Zones()); pcbnew.SaveBoard(PCB, b)
        print("dangling new tracks taken out: %d" % len(gone))
    else:
        sys.exit(__doc__)
    sys.stdout.flush(); os._exit(0)


if __name__ == "__main__":
    main()
