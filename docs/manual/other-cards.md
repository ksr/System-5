# Other cards and designs

Cards that were designed, half-designed or planned, but are not in the machine.

## Solderless breadboard prototyping card

`hardware/proto-breadboard/eagle/rev-a/`. A card that carries a solderless breadboard on the bus, for trying circuits. Rev A was drawn in 2005 ("current working version"); the 2005 website says no PCB was made, and its 2005 operating notes are headings only (bus buffering, address expansion, I/O, chip selection, 4K bank select, EPROM and RAM). Its Eagle files are Eagle 4 binary, not yet exported to KiCad (`hardware/FUSION-EXPORT.md`).

## Front panel

Never designed. The 2005 website lists a "Front Panel Card" page that was never written. The CPU card is ready for one: its SV6 header carries the run-control lines (-RUN, -PAUSE, -LOAD, CLEAR, WAIT), DMA IN, SC1 and a flag (FEF, routed to an EF line by JP2), and SV1 takes an external reset switch. System-4's wire-wrap front panel (switches and LEDs on two CDP1852s at N2, plus Q, Reset/Run and EF4) used those lines.

## Bus (backplane)

System-4's backplane is Vero board, from the late 1970s. For System-5 there are PCB backplane designs (`hardware/bus/eagle/`): Rev A (the 1982 definition) and Rev B/C (2005) as schematics, with Rev B's CAM files (silkscreen and drill report: 6 slots, a regulator, `rev-b/fab/bus-rev-b-silkscreen.png`), and a 2009 board with 6 slots and no regulator, which survives only as Eagle's backup files (`rev-2009/`). The slots are 36 pins: the 30-pin bus with -EF1-3 above and -INP, -OUT, -IOM below, the extra I/O signals the 2005 notes planned "so logic is not recreated on each card requiring IO". The board built is the 2009 one, without the regulator (2026-10-26); it is converted to KiCad (`hardware/bus/kicad/rev-2009/`, with a redrawn schematic). On its copper the power connector X1 reaches GND (pin 2) but not +5V (pin 1): the +5V track stops short. A fresh design, **Rev D** (S5BUS-D, 2026: 8 slots, both supply pins wired, pull-ups), is in `hardware/bus/kicad/rev-d/`, not yet ordered.

## Earlier and unbuilt revisions

| Card | Revision | Status |
|---|---|---|
| CPU | cpu1 prototype | first cut with an 1861 on the CPU card, unrouted |
| CPU | Rev B | drawn 2005 (adds JP5: reset only, or reset then run), never built |
| CPU | Rev C | Eagle backups only |
| Memory | mem1 (24K, 12 × 6116), mem2 (16K, 8 × 6116) | early designs, not built |
| Memory | Rev A | ordered 2004; same chip-select fault as Rev B |
| Memory | Rev C | drawn 2005 with the chip-select fix; the circuit Rev D and E carry |
| IO | Rev B | to-do list only |
| IDE | Rev B | description only |
| 6845 | Rev A | built and worked first (early 2005); a built card and a blank board survive |

`hardware/FABRICATED.md` has the evidence for each.

## Planned (2026)

- **A standalone CPU card**, so the IO card's 1861 no longer needs the CPU card's ribbon.
- **The next 6845 card revision with a PS/2 keyboard connector**, laid out to the 2026 board rules (front-edge connectors and LED, labels, readable references).
