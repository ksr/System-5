#!/bin/sh
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-17 (after hardware/video-g/kicad/common/build.sh)
#
# build.sh - build and check CPU Rev D from gen/netlist.py: the schematic and its ERC and netlist, the unrouted 2-layer
#   board (make_board.py), Freerouting on a fixed-order input (route.py; +5V 0.5 mm wide, the project's Power class),
#   DRC with the zones refilled and schematic parity, the order files (gerbers, drill, zip read back, render,
#   placement PDF) and tools/preorder_check.py --layers 2, which also redraws schematic/ and rebuilds the book.
#   hardware/cpu/kicad/rev-d/gen/build.sh
# Needs KiCad 10 and Freerouting 1.9 (~/freerouting/freerouting.jar, or FRJAR). MP = the most Freerouting passes (default
# 100: it stops sooner once every net is routed). ROUTE_SEED (route.py) picks another routing order.
# Before an order the board must also pass pcb-check (hardware/BUILD-RULES.md; pcb-check.ini beside the board).
set -e
G=$(cd "$(dirname "$0")" && pwd); B=$(cd "$G/.." && pwd); ROOT=$(cd "$B/../../../.." && pwd)
PYK=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
CLI=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
FRJAR="${FRJAR:-$HOME/freerouting/freerouting.jar}"; MP=${MP:-100}; P=cpu-rev-d
q() { grep -v -E 'Fontconfig|traits|Debug|GetWidth called|^$' || true; }
mkdir -p "$B/reports" "$B/logs"; cd "$B"

echo "== $P: schematic, ERC, netlist"
python3 "$G/make_schematic.py"
$CLI sch erc --format json -o reports/erc.json "$P.kicad_sch" 2>&1 | q
$CLI sch export netlist -o reports/netlist.net "$P.kicad_sch" 2>&1 | q

echo "== $P: board, Freerouting"
$PYK "$G/make_board.py" 2>&1 | q
$PYK "$G/route.py" dsn 2>&1 | q
rm -f "$P.ses"
java -jar "$FRJAR" -de "$P.dsn" -do "$P.ses" -mt 1 -mp "$MP" > logs/freerouting.log 2>&1
grep -E "Auto-routing was completed|optimization was completed" logs/freerouting.log | tail -2
$PYK "$G/route.py" import 2>&1 | q | tail -4

echo "== $P: DRC"
$CLI pcb drc --format json --refill-zones --schematic-parity -o reports/drc.json "$P.kicad_pcb" 2>&1 | q
python3 - <<EOF
import json, collections
d = json.load(open("reports/drc.json"))
v = d.get("violations", []); u = d.get("unconnected_items", []); p = d.get("schematic_parity", [])
print("DRC: %d errors, %d warnings %s; %d unconnected; parity %d" % (
    sum(x["severity"] == "error" for x in v), sum(x["severity"] != "error" for x in v),
    dict(collections.Counter(x["type"] for x in v)), len(u), len(p)))
EOF

echo "== $P: order files, pre-order check"
$PYK "$ROOT/tools/kicad/kicad_route.py" finish "$B/$P.kicad_pcb" 2>&1 | q | tail -4
$PYK "$ROOT/tools/kicad/print_1to1.py" "$B/$P.kicad_pcb" 2>&1 | q | tail -1     # the board at full size, to lay parts on
rm -rf _dsn_tmp.* 2>/dev/null || true
python3 "$ROOT/tools/preorder_check.py" "$B/$P.kicad_pcb" "$B/$P-gerbers.zip" --layers 2
