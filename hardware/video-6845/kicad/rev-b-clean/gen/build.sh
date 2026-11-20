#!/bin/sh
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-20 (after memory Rev F's gen/build.sh)
#
# build.sh - build and check the 6845 video card Rev B-Clean (Ken, 2026-11-20: "a clean version of current video card,
#   no need for db9, composite only. Add bypass caps and proper silkscreen ... minimal to no changes to circuit"):
#   its schematic from Rev B's without the DB9 (make_schematic.py), ERC and netlist; the footprint library with every
#   part drawn (footprints.py); the board from Rev B's with Rev B's copper kept and locked, less the DB9's tracks
#   (make_board.py: nothing is routed, no connection is new); the silkscreen (silk.py); DRC with schematic parity; the
#   order files, the 1:1 print and tools/preorder_check.py --layers 2, which also redraws schematic/ and rebuilds the
#   book. hardware/video-6845/kicad/rev-b-clean/gen/build.sh
# Needs KiCad 10. Before an order the board must also pass pcb-check (pcb-check.ini beside the board).
set -e
G=$(cd "$(dirname "$0")" && pwd); B=$(cd "$G/.." && pwd); ROOT=$(cd "$B/../../../.." && pwd)
PYK=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
CLI=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
P=video-6845-rev-b-clean
q() { grep -v -E 'Fontconfig|traits|Debug|GetWidth called|swig/python|^$' || true; }
mkdir -p "$B/reports"; cd "$B"

echo "== $P: schematic, ERC, netlist, parts list, schematic PDF"
python3 "$G/make_schematic.py"
$CLI sch erc --format json -o reports/erc.json "$P.kicad_sch" 2>&1 | q
$CLI sch export netlist -o reports/netlist.net "$P.kicad_sch" 2>&1 | q
$CLI sch export bom --fields 'Reference,Value,Footprint,${QUANTITY}' --labels 'Reference,Value,Footprint,QUANTITY' \
    --group-by 'Value,Footprint' --ref-range-delimiter '-' --sort-field Reference -o "$P-bom.csv" "$P.kicad_sch" 2>&1 | q
$CLI sch export pdf -o "$P-schematic.pdf" "$P.kicad_sch" 2>&1 | q

echo "== $P: footprints, the board from Rev B's, silkscreen"
$PYK "$G/footprints.py" 2>&1 | q | tail -3
$PYK "$G/make_board.py" 2>&1 | q
$PYK "$G/silk.py" 2>&1 | q | grep -E 'name line|no room|removed|wrote'

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

echo "== $P: order files, 1:1 print, pre-order check"
$PYK "$ROOT/tools/kicad/kicad_route.py" finish "$B/$P.kicad_pcb" 2>&1 | q | tail -4
$PYK "$ROOT/tools/kicad/print_1to1.py" "$B/$P.kicad_pcb" 2>&1 | q | tail -1
rm -rf _dsn_tmp.* 2>/dev/null || true
python3 "$ROOT/tools/preorder_check.py" "$B/$P.kicad_pcb" "$B/$P-gerbers.zip" --layers 2
