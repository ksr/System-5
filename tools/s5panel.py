#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-22
"""s5panel.py - the front panel's ribbon: one definition for the two boards it joins.

Ken, 2026-11-22: "I want to add ability to have a front panel if system is ever put in a case. This will mean bringing
all IO switches, LEDs, and TIL311 signals out to a ribbon cable connector." The IO panel card's J3 and the front
panel's J1 are keyed 2x25 headers joined by a straight 50-way ribbon: pin n to pin n, and conductor n of the cable is
pin n, so two pins next to each other in this list lie side by side in the cable.

    import s5panel
    s5panel.RIBBON            [(pin, net on the IO panel card, name on the front panel, what it is)], pins 1-50
    s5panel.io_pins()         {pin: the IO panel card's net}
    s5panel.panel_pins()      {pin: the front panel's net}
    python3 tools/s5panel.py  prints the table

Thirty-eight signals and twelve supply pins:
  ADR15-ADR0   the bus address as the IO card's two 74HCT573s hold it, for the four address displays
  OUT7-OUT0    the IO card's output port (its 74HCT374), for the eight bit LEDs and the two data displays
  SW7-SW0      the eight data toggles (on the front panel: on = +5V through RN2's 1k, off = open, the IO card pulling it down), to the IO card's 74HCT244
  Q_LED_L      low while Q is high (the IO card's U5B), to sink the Q LED
  ROM_LED_L    low while the CPU card's EPROM answers (-VMA high; the IO card's U23D, open drain), to sink the ROM LED
  INPUT_L      the INPUT button, to ground (the IO card's R1 / C1 debounce it)
  -RESET, -PAUSE, -DMAIN   the three bus lines themselves, open collector: the RUN and LOAD toggles pull the first
               two to ground, the RESET button pulls -RESET and -DMAIN together (a boot reset: docs/manual/bus.md),
               and the front panel reads all three for its RESET, PAUSE and START FROM RAM LEDs
The switch lines INPUT_RC (42), -RESET (44) and -PAUSE (46) have a ground wire on each side; -DMAIN (48) lies between
GND (47) and +5V (49). They are the ones a spike could matter on. The address and
output lines change at the machine's rate and sit at the other end of the cable. +5V is on four wires and ground on
eight: six TIL311s take up to about 1.1 A.
"""
RIBBON = ([(1, "+5V", "+5V", "supply"), (2, "+5V", "+5V", "supply"), (3, "GND", "GND", "ground")] +
          [(4 + k, "ADR%d" % (15 - k), "ADR%d" % (15 - k), "address display") for k in range(16)] +
          [(20, "GND", "GND", "ground")] +
          [(21 + k, "OUT%d" % (7 - k), "OUT%d" % (7 - k), "bit LED and data display") for k in range(8)] +
          [(29, "GND", "GND", "ground")] +
          [(30 + k, "SW%d" % (7 - k), "SW%d" % (7 - k), "data toggle") for k in range(8)] +
          [(38, "GND", "GND", "ground"),
           (39, "LED_Q_K", "Q_LED_L", "Q LED, sunk while Q is high"),
           (40, "ROM_LED_L", "ROM_LED_L", "ROM LED, sunk while the EPROM answers"),
           (41, "GND", "GND", "ground"),
           (42, "INPUT_RC", "INPUT_L", "INPUT button, to ground"),
           (43, "GND", "GND", "ground"),
           (44, "-RESET", "-RESET", "bus line: RUN toggle, RESET button, RESET LED"),
           (45, "GND", "GND", "ground"),
           (46, "-PAUSE", "-PAUSE", "bus line: LOAD toggle, PAUSE LED"),
           (47, "GND", "GND", "ground"),
           (48, "-DMAIN", "-DMAIN", "bus line: RESET button (boot), read for START FROM RAM"),
           (49, "+5V", "+5V", "supply"), (50, "+5V", "+5V", "supply")])
assert [p for p, *_ in RIBBON] == list(range(1, 51)), "the ribbon is pins 1-50, each once"


def io_pins():
    """{pin: the IO panel card's net} for its J3"""
    return {p: io for p, io, _, _ in RIBBON}


def panel_pins():
    """{pin: the front panel's net} for its J1"""
    return {p: fp for p, _, fp, _ in RIBBON}


if __name__ == "__main__":
    print("pin  IO panel J3   front panel J1   what")
    for p, io, fp, what in RIBBON:
        print("%3d  %-12s  %-15s  %s" % (p, io, fp, what))
