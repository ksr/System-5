#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-20
"""buspins.py - this card's bus connector for pcb-check's BUS PINS line (bus_pins in ../pcb-check.ini): one line
"J1 PAD NET" for each of J1's 36 pads, the net as this card names it.

The signals are the bus Rev D backplane's own (tools/s5bus.py). J1's pads 1-30 are the 30-pin card's pins (+5V at 1,
GND at 30, as Rev B's 2005 drawing numbers them); pads 31-36 are the slot's positions 31-36 (-EF1, -EF2, -EF3, -DMAIN,
SC0, -PAUSE). Rev B's nets keep the names Eagle gave them, so three kinds are put into this card's words: +5V is VCC,
D0-D7 are CPUDATA0-7, A0-A7 are ADDR0-7. TPA (pad 11) and -VMA (pad 26) have no name of their own on this card (KiCad
calls them after a pin), and pcb-check leaves a net without a name unchecked; their copper is Rev B's, locked.
"""
import os, re, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools")); import s5bus


def here(name):
    if name == "+5V": return "VCC"
    m = re.fullmatch(r"([AD])(\d)", name)
    return name if not m else ("ADDR" if m.group(1) == "A" else "CPUDATA") + m.group(2)


bus, pos = s5bus.bus(), s5bus.positions()
for n in range(1, 37):
    print("J1 %d %s" % (n, here(bus[n] if n <= 30 else pos[n])))
