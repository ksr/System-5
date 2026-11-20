#!/bin/sh
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-26
# Redraw every System-5 card's schematic from its board netlist, prove each one, and bind them into one book
# (tools/kicad/sch/README.md).
cd "$(dirname "$0")/../../.." || exit 1
fail=0
for d in cpu/kicad/rev-d io-panel/kicad/rev-a cpu/kicad/rev-a memory/kicad/rev-e memory/kicad/rev-f video-6845/kicad/rev-b video-6845/kicad/rev-b-clean video-6845/kicad/rev-b-clean-keyboard io-1861-keyboard/kicad/rev-a ide-cf/kicad/rev-a bus-driver/kicad/rev-b bus-driver/kicad/rev-c bus/kicad/rev-2009 bus/kicad/rev-d video-g/kicad/text-1.0 video-g/kicad/gfx-1.0; do
  echo "== $d"
  python3 tools/kicad/sch/gen_schematic.py "hardware/$d/schematic" || fail=1
done
python3 tools/kicad/sch/make_book.py || fail=1     # the book of every card: docs/manual/pdf/system5-schematics.pdf
exit $fail
