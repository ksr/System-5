#!/bin/bash
# Report which Fusion exports (hardware/**/fusion-export/) exist and are Eagle XML.
cd "$(dirname "$0")" || exit 1
rows=(
  "cpu/eagle/rev-a cpu2-a.sch cpu2-a.brd"
  "io-1861-keyboard/eagle/rev-a Video.sch Video.brd"
  "memory/eagle/rev-a mem3.sch mem3.brd"
  "memory/eagle/rev-b mem3-b.sch mem3-b.brd"
  "video-6845/eagle/rev-b v6845-b.sch v6845-b.brd"
  "video-6845/eagle/rev-a v6845-a.sch v6845-a.brd"
  "ide-cf/eagle/rev-a ide1-a.sch ide1-a.brd"
  "cpu/eagle/rev-b cpu2-b.sch cpu2-b.brd"
  "cpu/eagle/rev-c cpu2-c.sch cpu2-c.brd"
  "memory/eagle/rev-c mem3-c.sch mem3-c.brd"
  "memory/eagle/mem2-16k-6116 mem2.sch mem2.brd"
  "memory/eagle/mem1-24k-6116 mem1.sch mem1.brd"
  "cpu/eagle/cpu1-prototype cpu1.sch cpu1.brd"
  "proto-breadboard/eagle/rev-a proto1-a.sch proto1-a.brd"
  "bus/eagle/rev-2009 bus.sch bus.brd"
  "bus/eagle/rev-c bus.sch"
  "bus/eagle/rev-b bus.sch"
  "bus/eagle/rev-a bus.sch"
  "circuits/eagle IOBOARD.sch kio.sch"
)
done=0; total=0
for row in "${rows[@]}"; do
  set -- $row; dir=$1; shift
  for f in "$@"; do
    total=$((total+1)); p="$dir/fusion-export/$f"
    if [ ! -f "$p" ]; then st="missing"
    elif head -c 200 "$p" | grep -q '<eagle version='; then
      st="ok ($(head -c 300 "$p" | grep -o 'version="[0-9.]*"' | tail -1))"; done=$((done+1))
    else st="NOT XML"; fi
    printf '%-45s %s\n' "$p" "$st"
  done
done
echo "$done / $total exported"
