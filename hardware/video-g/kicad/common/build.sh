#!/bin/sh
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-01
#
# build.sh BOARD_DIR - build and check a VIDEO-G board from its gen/netlist.py and gen/place.py:
#   netlist check, schematic + ERC, the exported netlist proven against netlist.py, the unrouted 4-layer board,
#   Freerouting (signals on F.Cu/B.Cu; In1.Cu GND and In2.Cu VCC planes), the leftover router, DRC with the zones
#   refilled and schematic parity, the order files (gerbers, drill, zip read back, render, placement PDF) and
#   tools/preorder_check.py --layers 4.
#   hardware/video-g/kicad/common/build.sh hardware/video-g/kicad/gfx-1.0
# Needs KiCad 10 and Freerouting 1.9 (~/freerouting/freerouting.jar, or FRJAR). MP = Freerouting passes (default 60).
set -e
B=$(cd "$1" && pwd); C=$(cd "$(dirname "$0")" && pwd); ROOT=$(cd "$C/../../../.." && pwd)
PYK=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
CLI=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
FRJAR="${FRJAR:-$HOME/freerouting/freerouting.jar}"; MP=${MP:-60}
P=$(cd "$B/gen" && python3 -c "import netlist; print(netlist.PROJ)")
q() { grep -v -E 'Fontconfig|traits|Debug|GetWidth called|^$' || true; }
mkdir -p "$B/reports" "$B/logs"; cd "$B"

echo "== $P: netlist, schematic, ERC, netlist proof"
python3 gen/netlist.py
python3 "$C/make_schematic.py" "$B"
$CLI sch erc --format json -o reports/erc.json "$P.kicad_sch" 2>&1 | q
$CLI sch export netlist -o reports/netlist.net "$P.kicad_sch" 2>&1 | q
python3 "$C/checknet.py" "$B"

echo "== $P: board, Freerouting"
$PYK "$C/make_board.py" "$B" 2>&1 | q
$PYK "$C/route.py" dsn "$B" 2>&1 | q
rm -f "$P.ses"
java -jar "$FRJAR" -de "$P.dsn" -do "$P.ses" -mt 1 -mp "$MP" > logs/freerouting.log 2>&1
grep -E "Auto-routing was completed|optimization was completed" logs/freerouting.log | tail -2
$PYK "$C/route.py" import "$B" 2>&1 | q | tail -4
$PYK "$C/route_leftovers.py" "$B/$P.kicad_pcb" 2>&1 | q | tail -6

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
rm -rf logs/*.kicad_pcb _dsn_tmp.* 2>/dev/null || true
python3 "$ROOT/tools/preorder_check.py" "$B/$P.kicad_pcb" "$B/$P-gerbers.zip" --layers 4
