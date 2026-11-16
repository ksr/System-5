#!/usr/bin/env bash
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-12
# Start the System-5 emulator in a browser. The GitHub Codespace runs this (.devcontainer/devcontainer.json); it works
# the same on a Mac.
#
#   software/s5emu/web-start.sh            make the CF card image if it is missing, then start the emulator in the
#                                          background and wait until its page answers
#   software/s5emu/web-start.sh --prepare  only make the CF card image
#   software/s5emu/web-start.sh --fg       run in the foreground instead (Ctrl-C stops it)
#   software/s5emu/web-start.sh --stop     stop a background emulator
#
# Settings, from the environment: S5_PORT (default 8802), S5_CLOCK (max, 2m, 1.76m, 500k; default max),
# S5_OS (what is on the CF card: 0.2.6, the default, or 5 for Mike Riley's Elf/OS v5, see below),
# S5_DISK (the CF card image; default software/s5emu/disks/elfos.img, made by tools/mkelfos.py: ELF/OS 0.2.6, 15 MB
# like the real 16 MB card, from Mike Riley's files in the private repository private-resources beside this one;
# without them the emulator runs with no CF card; with S5_OS=5 software/s5emu/disks/elfos-v5.img), S5_ROM (the CPU card's ROM; default
# HBIOS 1.0.6, the one in the machine since 2026-11-15, with the monitor commands H, B, D and Q1 / Q0 and the disk
# calls in LBA mode; S5_ROM=software/s5emu/roms/hbios-1.0.5.rom or hbios-1.0.4.rom runs an earlier one),
# S5_PANEL (the IO panel card, A by default; S5_PANEL=none leaves it out).
# The panel takes port 4, so the 1861 is on no port, as on the real IO card.
#
# Elf/OS v5 (S5_OS=5; from the elfos-v5 branch, 2026-11-13, merged 2026-11-15): it is Mike Riley's and carries no
# licence, so its disk image is not in this repository. It is in the private repository private-resources, under
# elf/reference/mike-riley/elfos-v5/ (the README there says how it was made: kernel 5.1.1 build 229 with a 6-byte
# patch, so that its stack stays below System-5's video RAM). On a Mac that repository sits beside this one. A
# Codespace is given read access to it (.devcontainer/devcontainer.json) and fetches the one file with its
# GITHUB_TOKEN. S5_V5_GZ names another copy of the image (.img.gz); S5_V5_REPO another repository to fetch it from.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${S5_PORT:-8802}"
CLOCK="${S5_CLOCK:-max}"
PANEL="${S5_PANEL:-A}"
case "${S5_OS:-0.2.6}" in
    5|v5|V5|5.*) OS=5 ;;
    0.2.6|2) OS=0.2.6 ;;
    *) echo "S5_OS: 0.2.6 or 5, not '${S5_OS}'" >&2; exit 1 ;;
esac
if [ "$OS" = 5 ]; then DISK="${S5_DISK:-$HERE/disks/elfos-v5.img}"; else DISK="${S5_DISK:-$HERE/disks/elfos.img}"; fi
V5_REPO="${S5_V5_REPO:-ksr/private-resources}"
V5_PATH="elf/reference/mike-riley/elfos-v5/system5/elfos-5.1.1-system5-16mb.img.gz"
V5_GZ="${S5_V5_GZ:-$HERE/../../../private-resources/$V5_PATH}"
LOG="$HERE/disks/web.log"
ROM=""
if [ -n "${S5_ROM:-}" ]; then
    [ -f "$S5_ROM" ] || { echo "S5_ROM: no such file: $S5_ROM" >&2; exit 1; }
    ROM="$(cd "$(dirname "$S5_ROM")" && pwd)/$(basename "$S5_ROM")"
fi
mkdir -p "$HERE/disks"

up() { curl -s -m 2 -o /dev/null "http://127.0.0.1:$PORT/api/state?light"; }

if [ "${1:-}" = "--stop" ]; then
    if pkill -f "s5emu --ui web .*--web-port $PORT"; then
        # wait until it has gone (5 s at most), so that a start can follow at once: --stop && web-start.sh
        for _ in $(seq 1 20); do up || break; sleep 0.25; done
        echo "stopped"
    else
        echo "not running"
    fi
    exit 0
fi

# The Elf/OS v5 card: unpack the ready image, from the private-resources repository beside this one, or fetched from
# GitHub (that one file) where there is a GITHUB_TOKEN that may read it, as in a Codespace made from this branch.
make_v5_disk() {
    local gz="$V5_GZ" got="$DISK.gz.tmp"
    if [ ! -f "$gz" ]; then
        if [ -z "${GITHUB_TOKEN:-}" ]; then
            echo "Elf/OS v5: no disk image. It is not in this repository; it should be at" >&2
            echo "  $gz" >&2
            echo "(git clone https://github.com/$V5_REPO beside this repository), and there is no GITHUB_TOKEN to" >&2
            echo "fetch it with." >&2
            return 1
        fi
        echo "fetching the Elf/OS v5 disk image from $V5_REPO"
        if ! curl -fsSL -m 120 -H "Authorization: Bearer $GITHUB_TOKEN" -H "Accept: application/vnd.github.raw+json" \
                -o "$got" "https://api.github.com/repos/$V5_REPO/contents/$V5_PATH"; then
            rm -f "$got"
            echo "Elf/OS v5: could not fetch the disk image from $V5_REPO." >&2
            echo "A Codespace needs read access to that repository: GitHub asks for it when the Codespace is created" >&2
            echo "(Authorize and continue). See software/s5emu/CODESPACE.md." >&2
            return 1
        fi
        gz="$got"
    fi
    echo "making the CF card image $DISK (Elf/OS v5)"
    if ! gzip -dc "$gz" > "$DISK.tmp"; then
        rm -f "$DISK.tmp" "$got"
        echo "Elf/OS v5: the disk image did not unpack ($gz)" >&2
        return 1
    fi
    rm -f "$got"
    mv "$DISK.tmp" "$DISK"
}

NODISK=""
if [ ! -f "$DISK" ]; then
    if [ "$OS" = 5 ]; then
        make_v5_disk || exit 1
    elif [ -n "$(python3 -c 'import sys; sys.path.insert(0, sys.argv[1]); import mkelfos; print(*mkelfos.missing())' "$HERE/tools")" ]; then
        # ELF/OS 0.2.6 (kernel, programs, disktool) is Mike Riley's and kept in the private repository private-resources,
        # not here: the emulator then runs with no CF card and starts at the HBIOS monitor
        echo "no CF card image: ELF/OS 0.2.6 is Mike Riley's and not in this repository (tools/mkelfos.py says more)."
        echo "The emulator starts at the HBIOS monitor (H lists its commands); S5_DISK can name a card image of your own."
        NODISK=1
    else
        if ! command -v cc > /dev/null; then
            echo "mkelfos.py needs a C compiler (cc) to build disktool: sudo apt-get install -y build-essential" >&2
            exit 1
        fi
        echo "making the CF card image $DISK"
        python3 "$HERE/tools/mkelfos.py" "$DISK" --mb 15 | tail -4
    fi
fi
[ "${1:-}" = "--prepare" ] && exit 0

if up; then echo "the emulator is already running: http://127.0.0.1:$PORT/"; exit 0; fi

cd "$HERE"
CMD=(python3 -m s5emu --ui web --run --web-port "$PORT" --clock "$CLOCK")
[ -z "$NODISK" ] && CMD+=(--disk "$DISK")
[ -n "$ROM" ] && CMD+=(--rom "$ROM")
[ "$PANEL" != "none" ] && CMD+=(--panel "$PANEL")
if [ "${1:-}" = "--fg" ]; then exec "${CMD[@]}"; fi

# in the background, detached from this shell, so it outlives the command that started it
if command -v setsid > /dev/null; then
    setsid nohup "${CMD[@]}" > "$LOG" 2>&1 < /dev/null &
else
    nohup "${CMD[@]}" > "$LOG" 2>&1 < /dev/null &
fi
for _ in $(seq 1 40); do
    if up; then
        if [ -n "$NODISK" ]; then CARD="no CF card"; else CARD="CF card: $(basename "$DISK")"; fi
        echo "System-5 emulator running: http://127.0.0.1:$PORT/  ($CARD; log: $LOG)"; exit 0
    fi
    sleep 0.25
done
echo "the emulator did not start; its log:" >&2
cat "$LOG" >&2
exit 1
