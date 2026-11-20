#!/bin/sh
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-18 (after the IO panel's gen/build.sh)
#
# build.sh - build and check memory Rev F: its schematic from Rev E's with the EEPROM sockets (make_schematic.py), ERC
#   and netlist, the board from Rev E's with Rev E's tracks kept and locked (make_board.py), Freerouting for the new
#   connections only (route.py: 4 layers, the planes kept), the silkscreen (silk.py), DRC with the zones refilled and
#   schematic parity, the order files and tools/preorder_check.py --layers 4, which also redraws schematic/ and rebuilds
#   the book. hardware/memory/kicad/rev-f/gen/build.sh
# Needs KiCad 10 and Freerouting 1.9 (~/freerouting/freerouting.jar, or FRJAR). ROUTE_SEED (route.py) picks another
# routing order. Before an order the board must also pass pcb-check (pcb-check.ini beside the board).
set -e
G=$(cd "$(dirname "$0")" && pwd); B=$(cd "$G/.." && pwd); ROOT=$(cd "$B/../../../.." && pwd)
PYK=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
CLI=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
FRJAR="${FRJAR:-$HOME/freerouting/freerouting.jar}"; MP=${MP:-100}; P=memory-rev-f
q() { grep -v -E 'Fontconfig|traits|Debug|GetWidth called|^$' || true; }
mkdir -p "$B/reports" "$B/logs"; cd "$B"

echo "== $P: schematic, ERC, netlist, parts list, schematic PDF"
python3 "$G/make_schematic.py"
$CLI sch erc --format json -o reports/erc.json "$P.kicad_sch" 2>&1 | q
$CLI sch export netlist -o reports/netlist.net "$P.kicad_sch" 2>&1 | q
$CLI sch export bom --fields 'Reference,Value,Footprint,${QUANTITY}' --labels 'Reference,Value,Footprint,QUANTITY' \
    --group-by 'Value,Footprint' --ref-range-delimiter '-' --sort-field Reference -o "$P-bom.csv" "$P.kicad_sch" 2>&1 | q
$CLI sch export pdf -o "$P-schematic.pdf" "$P.kicad_sch" 2>&1 | q

echo "== $P: board from Rev E's, Freerouting for the new connections, silkscreen"
$PYK "$G/make_board.py" 2>&1 | q
$PYK "$G/route.py" dsn 2>&1 | q
rm -f "$P.ses"
java -jar "$FRJAR" -de "$P.dsn" -do "$P.ses" -mt 1 -mp "$MP" > logs/freerouting.log 2>&1
grep -E "Auto-routing was completed|optimization was completed" logs/freerouting.log | tail -2
$PYK "$G/route.py" import 2>&1 | q | tail -4
$PYK "$G/silk.py" 2>&1 | q | grep -E 'name line|JP|R6 |R7 |no room|wrote|written|drawings|courtyards'

echo "== $P: DRC"
$CLI pcb drc --format json --refill-zones --schematic-parity -o reports/drc.json "$P.kicad_pcb" 2>&1 | q
python3 - <<PYEOF
import json, collections
d = json.load(open("reports/drc.json"))
v = d.get("violations", []); u = d.get("unconnected_items", []); p = d.get("schematic_parity", [])
print("DRC: %d errors, %d warnings %s; %d unconnected; parity %d" % (
    sum(x["severity"] == "error" for x in v), sum(x["severity"] != "error" for x in v),
    dict(collections.Counter(x["type"] for x in v)), len(u), len(p)))
PYEOF

echo "== $P: order files, pre-order check"
$PYK "$ROOT/tools/kicad/kicad_route.py" finish "$B/$P.kicad_pcb" 2>&1 | q | tail -4
rm -rf _dsn_tmp.* 2>/dev/null || true
python3 "$ROOT/tools/preorder_check.py" "$B/$P.kicad_pcb" "$B/$P-gerbers.zip" --layers 4
