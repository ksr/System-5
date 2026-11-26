#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-17
"""route.py dsn|import - Freerouting in and out for the IO panel Rev A (run with KiCad's Python; gen/build.sh does).

  dsn     ../io-panel-rev-a.dsn from the unrouted board: tools/kicad/kicad_route.py export_dsn (the GND pours left out, so
          Freerouting routes GND as tracks too; the project's Power class, io-panel-rev-a.kicad_pro, makes +5V 0.5 mm
          wide), then put in a fixed order (tools/kicad/dsn_order.py, as VIDEO-G's), so the board routes the same
          way every time. ROUTE_SEED below, or the ROUTE_SEED environment variable (which wins), shuffles that order
          reproducibly: another seed is another try when one order leaves a net unrouted. 0 = the sorted order.
  import  ../io-panel-rev-a.ses back into the board (kicad_route.import_ses: stitch, edge heal, zone fill)
"""
import os, sys
import pcbnew
HERE = os.path.dirname(os.path.abspath(__file__)); DEST = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(DEST, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "kicad")); import kicad_route, dsn_order
PROJ = "io-panel-rev-a"
ROUTE_SEED = 1          # 2026-11-25, the power-up fix (D1, R5, R6; U9's and U23's gates changed round): seed 1 routes every
                        # net; 3 leaves one +5V link open (C10); the others not judged. Until then the same seed:
                        # 2026-11-23, RUN/RESET turned end for end (SW10's -RESET pad at its other end): seed 1 routes
                        # every net; 5 leaves two +5V links open (0, 2, 3, 4 not judged). Until then 3: 2026-11-23, with the card's own RESET button (SW12, U23, R4, C26; R2 and R3 3 mm nearer the
                        # LEDs): seed 3 routes every net; 2 and 0 leave two links open, 1 one (D0). Until then 2:
                        # 2026-11-22, with the front panel's header J3 and RN3 (the card 0.5 in longer; J3's +5V pins
                        # drawn in make_board.py): seed 2 routes every net; 1 leaves the toggle column's +5V open
                        # from the displays' rail (0 not tried). Judged with the autorouter alone (-mt 0), 3.5 minutes
                        # a seed. Until then 1:
                        # 2026-11-20, with the serial port (the card 1.75 in longer): seeds 1 and 2
                        # route every net, 0 leaves two links open, once make_board.py draws the six links round JP6 and
                        # the serial block's +5V; without the +5V drawn every seed left one to four +5V links open.
                        # (A seed is judged in two minutes with the autorouter alone: java ... -mt 0.)
                        # 2026-11-18, with JP5 (the RTC's RAM-clear jumper): seed 0 routes every net (1870 segments, 66 vias);
                        # 1, 4 and 7 leave one +5V link open. Freerouting spends about nine minutes on this board after its
                        # autorouter is done (route optimization), so a seed takes ten minutes to judge. J1 goes in under its
                        # old pin names (j1_by_place below). Before JP5: 2; before the slot's new order: 1


def j1_by_place(t):
    """Freerouting's input with J1's pins named as they were until 2026-11-18. That day the slot's positions were
    renumbered from the GND end (pin k became 37 - k; J1's footprint turned end for end) without moving one signal, but
    Freerouting's result follows the order of its input, pin names included: with the new names none of seeds 0-11
    routed every net of this board (four ran on past eight minutes), where the old names route it completely on seed 2.
    So J1 goes in as before: turned back, each pin under its old number. The same pads, the same nets, the same places;
    the board, its netlist and every drawing keep the new numbers."""
    import re
    t, n = re.subn(r"(\(place J1 \S+ \S+ front )(\d+)", lambda m: m.group(1) + str((int(m.group(2)) + 180) % 360), t)
    assert n == 1, "route.py: J1's place line not found in the DSN"
    def pins(m):
        return re.sub(r"\bJ1-(\d+)\b", lambda k: "J1-%d" % (37 - int(k.group(1))), m.group(0))
    return re.sub(r"\(pins [^)]*\)", pins, t)


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    pcb = os.path.join(DEST, PROJ + ".kicad_pcb")
    if cmd == "dsn":
        kicad_route.export_dsn(pcb)
        dsn = os.path.join(DEST, PROJ + ".dsn")
        seed = os.environ.get("ROUTE_SEED")
        seed = int(seed) if seed not in (None, "") else ROUTE_SEED
        t = open(dsn).read()                            # read first: opening it to write empties it
        open(dsn, "w").write(dsn_order.fixed(j1_by_place(t), seed))
        print("dsn: fixed order, J1's pins by their place, route seed", seed)
    elif cmd == "import":
        ses = os.path.join(DEST, PROJ + ".ses")
        # the session file carries each part's placement, and importing it puts the parts there: turn J1 back to where
        # the board has it, or the import would turn the connector round under its tracks (j1_by_place above)
        import re
        t, n = re.subn(r"(\(place J1 \S+ \S+ front )(\d+)", lambda m: m.group(1) + str((int(m.group(2)) + 180) % 360), open(ses).read())
        assert n == 1, "route.py: J1's place line not found in the session file"
        open(ses, "w").write(t)
        kicad_route.import_ses(pcb, ses)
    else:
        sys.exit(__doc__)
    sys.stdout.flush(); os._exit(0)                     # skip pcbnew's exit hang (the work is saved)


if __name__ == "__main__":
    main()
