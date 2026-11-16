# Bus backplane, 2009 (from Eagle's backups)

Copied 2026-10-26 from `~/Documents/Projects/elf-2/ksrcad/Bus/`, where they sat beside the Rev A/B/C folders:
`eagle-backups/bus.b##` (board) and `bus.s##` (schematic), both dated 2009-02-04, Eagle 4 binary.
`bus.brd` and `bus.sch` are byte-identical copies under the names Eagle and Fusion open.

Exported from Fusion 2026-10-26 (`fusion-export/`) and converted: `hardware/bus/kicad/rev-2009/` (netlist proof MATCH
36/36), redrawn in `hardware/bus/kicad/rev-2009/schematic/`.

What the board is: **six 36-pin slots** (`C36A`), every pin bussed, 8 mounting holes, and X1, a 2-pin power connector.
Slot pins 1-30 are the System-5 bus pin for pin (pin 1 = +5V, named `5V` here; 30 = GND); 31-33 = -EF1, -EF2, -EF3
(silkscreened above the 30); 34-36 = -INP, -OUT, EXP (below). A 30-pin card fits the middle 30.
Against the 2005 Rev B board (`../rev-b/fab/bus-rev-b-silkscreen.png`): the same six 36-pin slots, but pin 36 is EXP
(Rev B: -IOM) and there is no regulator, LED or capacitors.
**X1 on the copper** (DRC of the conversion, 2026-10-26): the GND track runs down the board edge and ends on X1's pad 2, so X1 pin 2 IS GND (Eagle's netlist never logged it: the track was drawn onto the pad, not connected); both +5V branches dangle (a 75 mm run down the edge and a 7 mm stub ending about 9.5 mm from X1): X1 pin 1 is connected to nothing. X1 was evidently moved after routing. So X1 brings in GND only; +5V needs a wire from X1 pin 1 to the 5V track (slot pin 1) or comes in through a slot. To confirm with a meter: X1.2 to slot pin 30 beeps, X1.1 to slot pin 1 does not.
Photos of two bare boards (both sides): `photos/2026-10-26-*.jpg`. (The other names in the binary file, U4, DTPA, DN0..., are schematic leftovers, not parts on the board.)
