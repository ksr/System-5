#!/bin/bash
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-08
# JLCPCB order files for the 6845 Rev B master: gerbers/, the zip, a top render, a placement sheet, the BOM, DRC/ERC.
set -e
cd "$(dirname "$0")/.."
K=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
P=video-6845-rev-b
rm -rf gerbers && mkdir gerbers
$K pcb export gerbers -o gerbers/ -l F.Cu,B.Cu,F.Mask,B.Mask,F.Silkscreen,B.Silkscreen,Edge.Cuts --subtract-soldermask --no-protel-ext $P.kicad_pcb >/dev/null
$K pcb export drill -o gerbers/ --format excellon --generate-map --map-format gerberx2 $P.kicad_pcb >/dev/null
rm -f $P-gerbers.zip && (cd gerbers && zip -q ../$P-gerbers.zip *)
$K pcb render --side top --width 1600 --height 1200 -o $P-render-top.png $P.kicad_pcb >/dev/null
$K pcb export pdf -o $P-placement.pdf -l F.Fab,F.Silkscreen,Edge.Cuts --include-border-title $P.kicad_pcb >/dev/null
$K sch export bom -o $P-bom.csv --fields 'Reference,Value,Footprint,${QUANTITY}' --labels 'Reference,Value,Footprint,QUANTITY' \
   --group-by Value --ref-range-delimiter '' --exclude-dnp $P.kicad_sch >/dev/null
$K pcb drc --format json --severity-all --schematic-parity -o reports/drc.json $P.kicad_pcb >/dev/null || true
$K sch erc --format json --severity-all -o reports/erc.json $P.kicad_sch >/dev/null || true
$K pcb render --side top --width 1600 --height 1200 -o reports/$P-top.png $P.kicad_pcb >/dev/null
$K pcb render --side bottom --width 1600 --height 1200 -o reports/$P-bottom.png $P.kicad_pcb >/dev/null
$K sch export pdf -o reports/$P-schematic.pdf $P.kicad_sch >/dev/null
rm -f *.kicad_prl
python3 ../../../../tools/check_order_zip.py $P.kicad_pcb $P-gerbers.zip   # reads the zip back: copper layers, nets, holes
ls gerbers
