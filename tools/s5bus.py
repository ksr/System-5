#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-17
"""s5bus.py - the System-5 bus pinout, for pcb-check's bus check (its bus_pins setting).

    python3 tools/s5bus.py --pins [CONNECTOR]                  a 30-pin card: CONNECTOR PIN SIGNAL, pins 1-30 (default J1)
    python3 tools/s5bus.py --pins [CONNECTOR] --positions 36   a 36-pin card (CPU Rev D, the IO panel): positions 1-36

The definition is the one the bus Rev D backplane is made from (hardware/bus/kicad/rev-d/gen/netlist.py): BUS, the
30-pin bus as a 30-pin card's connector is numbered (pin 1 +5V to pin 30 GND), and POS, its 36-pin slots numbered by
position from the GND end (Ken, 2026-11-18: GND 1 ... +5V 30, then -EF1 31, -EF2 32, -EF3 33, -DMAIN 34, SC0 35, -PAUSE
36, so bus pin n is position 31 - n; until then 1-3 -EF1..-EF3, 4-33 the bus, 34-36 -PAUSE, -DMAIN, SC0), so a card is
checked against the backplane's own names. Pins the card leaves open are fine to pcb-check (it compares only connected
pins).
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


def positions():
    """{position: signal} for a 36-pin slot, from the backplane generator's POS line: lists of names and of the bus
    pins (BUS[i] for i in a range), added together; worked out here with nothing but BUS and range to hand"""
    text = open(SRC).read()
    m = re.search(r'^POS = ([^#\n]+)', text, re.M)
    if not m: sys.exit("s5bus.py: no POS line in %s" % SRC)
    expr = m.group(1).strip()
    if not re.fullmatch(r'[\[\]\w\s"+,()\-]+', expr): sys.exit("s5bus.py: POS is not lists of names and bus pins: %s" % expr)
    try:
        names = eval(expr, {"__builtins__": {}, "BUS": bus(), "range": range})
    except Exception as e:
        sys.exit("s5bus.py: cannot read POS (%s): %s" % (e, expr))
    if len(names) != 36 or len(set(names)) != 36: sys.exit("s5bus.py: POS is not 36 different positions")
    return {i + 1: n for i, n in enumerate(names)}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--pins", nargs="?", const="J1", metavar="CONNECTOR")
    ap.add_argument("--positions", type=int, choices=(30, 36), default=30)
    a = ap.parse_args()
    if not a.pins: ap.print_help(); return 1
    for pin, sig in sorted((bus() if a.positions == 30 else positions()).items()):
        print("%s %d %s" % (a.pins, pin, sig))
    return 0


if __name__ == "__main__":
    sys.exit(main())
