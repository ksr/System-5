#!/bin/sh
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-20 (after Rev B-Clean's and memory Rev F's)
#
# build.sh - build and check the 6845 video card Rev B-Clean-Keyboard (Ken, 2026-11-20: "add keyboard support to Rev B
#   Clean ... Look at video-g for keyboard section only. Expand bus to the 36 pin bus and add jumpers required to
#   access keyboard"; memory-mapped, as VIDEO-G: the key at 7802, the status at 7804):
#     make_schematic.py   Rev B-Clean's schematic with the 36-pin bus connector and the keyboard section (keyboard.py);
#                         ERC, netlist, parts list, schematic PDF
#     footprints.py       Rev B-Clean's footprint library with the 36-pin header and the PS/2 jack
#     make_board.py       Rev B-Clean's board, longer and with the six new bus pins: Rev B's copper kept and locked
#                         (but the 6845's select, cut, and one track's corner moved from under pin 31), the new parts
#                         placed, nothing routed
#     route_leftovers.py --first   the 6845's R/W to ground and the composite video, across Rev B's copper alone; locked
#     route.py            Freerouting adds the keyboard section's connections on the same two layers
#     route_leftovers.py  a maze router joins the few long connections Freerouting leaves open
#     silk.py             the silkscreen
#   then DRC with schematic parity, the order files, the 1:1 print and tools/preorder_check.py --layers 2, which also
#   redraws schematic/ and rebuilds the book. hardware/video-6845/kicad/rev-b-clean-keyboard/gen/build.sh
# Needs KiCad 10, Java and ~/freerouting/freerouting.jar. The routing takes about three minutes (-mp 20: Freerouting
# gets no further with more passes on this board).
# Before an order the board must also pass pcb-check (pcb-check.ini beside the board).
set -e
G=$(cd "$(dirname "$0")" && pwd); B=$(cd "$G/.." && pwd); ROOT=$(cd "$B/../../../.." && pwd)
PYK=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
CLI=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
FR="$HOME/freerouting/freerouting.jar"
P=video-6845-rev-b-clean-keyboard
q() { grep -v -E 'Fontconfig|traits|Debug|GetWidth called|swig/python|^$' || true; }
mkdir -p "$B/reports" "$B/logs"; cd "$B"

echo "== $P: schematic, ERC, netlist, parts list, schematic PDF"
python3 "$G/make_schematic.py"
$CLI sch erc --format json -o reports/erc.json "$P.kicad_sch" 2>&1 | q
$CLI sch export netlist -o reports/netlist.net "$P.kicad_sch" 2>&1 | q
$CLI sch export bom --fields 'Reference,Value,Footprint,${QUANTITY}' --labels 'Reference,Value,Footprint,QUANTITY' \
    --group-by 'Value,Footprint' --ref-range-delimiter '-' --sort-field Reference -o "$P-bom.csv" "$P.kicad_sch" 2>&1 | q
$CLI sch export pdf -o "$P-schematic.pdf" "$P.kicad_sch" 2>&1 | q

echo "== $P: footprints, the board from Rev B-Clean's, routing"
$PYK "$G/footprints.py" 2>&1 | q | tail -3
$PYK "$G/make_board.py" 2>&1 | q
$PYK "$G/route_leftovers.py" --first 2>&1 | q
$PYK "$G/route.py" dsn 2>&1 | q | tail -1
rm -f "$P.ses"
java -jar "$FR" -de "$P.dsn" -do "$P.ses" -mt 1 -mp 20 > logs/freerouting.log 2>&1 || true
grep -E "Auto-routing was completed|optimization was completed" logs/freerouting.log | sed 's/.*INFO  /   /'
$PYK "$G/route.py" import 2>&1 | q | tail -1
rm -f "$P.dsn" "$P.ses"
$PYK "$G/route_leftovers.py" 2>&1 | q

echo "== $P: silkscreen"
$PYK "$G/silk.py" > logs/silk.log 2>&1 || { q < logs/silk.log | grep -E 'no room|Error|error' ; echo "build.sh: the silkscreen was not written: stopping"; exit 1; }
q < logs/silk.log | grep -E 'name line|removed|wrote'

echo "== $P: DRC"
$CLI pcb drc --format json --refill-zones --schematic-parity -o reports/drc.json "$P.kicad_pcb" 2>&1 | q
python3 - <<PYEOF
import json, collections, sys
d = json.load(open("reports/drc.json"))
v = d.get("violations", []); u = d.get("unconnected_items", []); p = d.get("schematic_parity", [])
print("DRC: %d errors, %d warnings %s; %d unconnected; parity %d" % (
    sum(x["severity"] == "error" for x in v), sum(x["severity"] != "error" for x in v),
    dict(collections.Counter(x["type"] for x in v)), len(u), len(p)))
if u or any(x["severity"] == "error" for x in v):
    sys.exit("build.sh: the board is not clean: stopping before the order files")
PYEOF

echo "== $P: order files, 1:1 print, pre-order check"
$PYK "$ROOT/tools/kicad/kicad_route.py" finish "$B/$P.kicad_pcb" 2>&1 | q | tail -4
$PYK "$ROOT/tools/kicad/print_1to1.py" "$B/$P.kicad_pcb" 2>&1 | q | tail -1
rm -rf _dsn_tmp.* 2>/dev/null || true
python3 "$ROOT/tools/preorder_check.py" "$B/$P.kicad_pcb" "$B/$P-gerbers.zip" --layers 2
