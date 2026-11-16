#!/bin/sh
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-01
# run.sh - build the host co-simulation of video-g-ps2.ino and run every check (README.md "Host simulation").
# Needs clang++ (Xcode command line tools). Builds in a temporary folder; prints "overall: 0" when every check passes.
# Two V2.0-style variants are built for comparison only; their failures are expected and do not count.
S=$(cd "$(dirname "$0")" && pwd)
INO="$S/../video-g-ps2.ino"
O=$(mktemp -d "${TMPDIR:-/tmp}/video-g-ps2-sim.XXXXXX") || exit 2
sed 's/^#define KEYS_VT100 0 /#define KEYS_VT100 1 /' "$INO" > "$O/vt100.ino"
sed 's/^#define READ_GUARD_US 1000UL/#define READ_GUARD_US 5UL/' "$INO" > "$O/guard5.ino"
grep -v 'EIMSK &= ~_BV(INT0);' "$INO" > "$O/nomask.ino"
grep -q '^#define KEYS_VT100 1 ' "$O/vt100.ino" && grep -q '^#define READ_GUARD_US 5UL' "$O/guard5.ino" || { echo "variant edit failed"; exit 2; }
build() { clang++ -std=c++17 -O1 -Wall -Wno-unused-function -I "$S" -DSKETCH="\"$2\"" -o "$O/$1" "$S/sim.cpp" || exit 2; }
build sim "$INO"; build sim_vt100 "$O/vt100.ino"; build sim_guard5 "$O/guard5.ino"; build sim_nomask "$O/nomask.ino"
rc=0
for t in kb_start kb_typing kb_caps kb_special kb_hotplug kb_during_led kb_burst_fast kb_burst_slow kb_stress \
         kb_inhibit kb_late console mouse mouse_hotplug mouse_late mouse_resync mouse_on_at_start \
         strap_text strap_gfx strap_gfx_marginal; do
  "$O/sim" $t || rc=1
done
"$O/sim_vt100" vt100 || rc=1
echo "---- for comparison, V2.0's 5 us load check against the bus driver's slow INP (failures expected):"
"$O/sim_guard5" kb_burst_slow
echo "---- for comparison, INT0 left enabled during the request-to-send as in V2.0 (a doubled key expected):"
"$O/sim_nomask" kb_inhibit
rm -rf "$O"
echo "overall: $rc"
exit $rc
