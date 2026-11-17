#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-17
"""s5bus.py - the System-5 bus pinout, for pcb-check's bus check (its bus_pins setting).

    python3 tools/s5bus.py --pins [CONNECTOR]      one line per pin: CONNECTOR PIN SIGNAL (default J1)

The definition is the one the bus Rev D backplane is made from (hardware/bus/kicad/rev-d/gen/netlist.py, BUS: the
30-pin bus, pin 1 +5V to pin 30 GND), so a card is checked against the backplane's own names. This prints a 30-pin
card's edge connector, pins 1-30. Pins the card leaves open are fine to pcb-check (it compares only connected pins).
"""
import argparse, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "hardware", "bus", "kicad", "rev-d", "gen", "netlist.py")


def bus():
    """{pin: signal} for the 30-pin bus, read from the backplane generator's BUS table (not imported: it builds a board)"""
    text = open(SRC).read()
    m = re.search(r"^BUS = \{(.*?)\}", text, re.S | re.M)
    if not m: sys.exit("s5bus.py: no BUS table in %s" % SRC)
    pins = {int(k): v for k, v in re.findall(r'(\d+):\s*"([^"]+)"', m.group(1))}
    if sorted(pins) != list(range(1, 31)): sys.exit("s5bus.py: the BUS table is not pins 1-30")
    return pins


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--pins", nargs="?", const="J1", metavar="CONNECTOR")
    a = ap.parse_args()
    if not a.pins: ap.print_help(); return 1
    for pin, sig in sorted(bus().items()):
        print("%s %d %s" % (a.pins, pin, sig))
    return 0


if __name__ == "__main__":
    sys.exit(main())
