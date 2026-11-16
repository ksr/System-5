# IO panel card Rev A: design notes (draft)

The new IO card: System-5's front panel. LEDs, switches and two TIL311 hex displays on an I/O port, a Q LED, an INPUT button
on an EF line, and the machine's hand controls (PAUSE, LOAD) on the 36-pin bus. It replaces the 2005 IO card
(`hardware/io-1861-keyboard/`: its keyboard moves to the video card Rev C, its 1861 is dropped). Started 2026-10-30 (Ken).
Nothing is drawn yet. The folder name `io-panel` is a working name. The bus: `docs/manual/bus.md`, "The 36-pin extension".

## Decided (Ken, 2026-10-30)

| Item | Decision |
|---|---|
| Output | **8 LEDs** and **2 TIL311** hex displays showing the byte written by `OUT 4`, latched in a **74HCT374**. |
| Input | **8 switches**, **eight toggle switches** (Ken, 2026-10-30), read by `INP 4` through a **74HCT244**. |
| Port | **Port 4** for both (ports 1-3 are the keyboard and the IDE card). The card decodes it itself from N0-N2 and -MRD (no bus -INP/-OUT). |
| INPUT button | On **-EF1** (open collector) → the CPU's EF1. |
| Q LED | From bus Q (pin 10), through a buffer. |
| Hand controls | The COSMAC ELF's **RUN** and **LOAD** toggles (RUN off pulls -RESET, LOAD on pulls -PAUSE: LOAD mode = RUN off + LOAD on, PAUSE = RUN on + LOAD on; changed 2026-10-30 from PAUSE/LOAD with the CPU Rev D netlist, so LOAD → RESET → RUN runs a loaded program), the INPUT button on -DMAIN in LOAD mode, the 8 switches as the data. Works with or without a debug board. |
| Bus | The 36-pin interface. |
| Layout | The board layout rules: every switch, button, LED and display on the front edge, each labelled (bit 7-0, Q, INPUT, PAUSE, LOAD); `cottageworker.com` and the board name/revision; 0.1" bypass caps. |
| Layers | **2 copper layers if at all possible** (Ken, 2026-10-30): cheaper and quicker to check; preorder_check `--layers 2`. Go to 4 only if routing truly fails, and ask first. |

## Proposed (to agree with Ken)

1. **Port decode.** A 74HCT138 on N0-N2; output 4 gated with -MRD: `OUT 4` (-MRD low) clocks the '374 on TPB; `INP 4` (-MRD high)
   enables the '244 onto D0-D7 for the execute cycle. Check against the bus timing (`python3 -m s5emu.timing 2`).
2. **TIL311s.** Each has its own 4-bit latch; tie their LATCH STROBE low (transparent) and feed them from the '374's outputs, so they
   always show what the LEDs show. Left display = bits 7-4, right = bits 3-0. Blanking inputs tied off. Note: the TIL311 is long out
   of production (surplus, and not cheap); the footprint is a 14-pin wide DIP.
3. **LEDs.** The '374 drives eight LEDs through resistors (sinking or sourcing a few mA each), or through a ULN2803 if brighter.
   Q LED through a 74HCT buffer, so the bus Q line sees one CMOS input.
4. **INPUT button.** Debounced (RC + 74HCT14, or an SR latch on a changeover push-button), then:
   - to **-EF1** through an open-collector driver (74HCT05 / 74LS06 gate or a transistor), so programs read it with `B1`/`BN1`;
   - in LOAD mode (the LOAD switch on), **one -DMAIN request per press**: the request is set by the press and cleared by the DMA
     cycle (-MWR rising while -MRD is high), so a held button loads one byte, not many.
5. **Data in LOAD mode.** The '244 also drives D0-D7 while this card's own DMA request is pending **and** -MRD is high (the DMA IN
   cycle; in IDLE the memory drives M(R0)). Never for another card's request.
6. **RUN and LOAD switches** (ELF-style). Toggles to open-collector drivers: RUN off pulls -RESET, LOAD on pulls -PAUSE. To load:
   RUN off, LOAD on, toggle bytes in with INPUT; then LOAD off (reset, R0 = 0000), RUN on: the program runs from 0000 (the CPU
   card's LOADED flag keeps its boot map off). The CPU card's RESET/RUN switch boots HBIOS and still overrides.
7. **Switches.** Eight toggles (decided, Ken 2026-10-30) with pull-downs, labelled 7 … 0, high = 1. The INPUT button and the PAUSE/LOAD
   toggles labelled by function.
8. **Folder and generator.** `hardware/io-panel/kicad/rev-a/` with `gen/netlist.py`, `make_schematic.py`, `make_board.py`, a
   `schematic/spec.py`, lines in `build_all.sh` / `make_book.py`; a model in s5emu (port 4, -EF1, LOAD/DMA) so a program can be
   toggled in on the emulator before the order.

## Netlist (2026-10-30): `gen/netlist.py`, `gen/make_schematic.py`

Written and checked: ERC 0, 58 parts, no single-pin nets; redrawn schematic (`schematic/`, 6 sheets) proven MATCH 64/64,
in the book. A gate-level walk-through checked OUT 4, INP 4, INPUT while running, LOAD mode, one DMA IN per press (held
button), and that a debug board's DMA with the button held never makes this card drive. Board not started.

- **Chips:** U1 74HCT138 (port 4), U2 74HCT374 (OUT latch), U3 74HCT244 (switches), U4 74HCT14, U5 74HCT10 (OUTCLK),
  U6 74HCT00, U9 74HC05 (open collector: -EF1, -DMAIN, the Q LED), U10 74HCT74 (REQ, ACK), U11 74HCT74 (DRIVE), U7/U8
  TIL311. Spares: U5B/C, U6D, U9 ×3, U11B.
- **OUT 4** latches on TPB's fall (OUTCLK = NAND(port 4, -MRD low, TPB) clocks the '374 as TPB ends).
- **INP 4 and LOAD data:** the '244 drives while -MRD is high and (port 4 or DRIVE). DRIVE (found in the walk-through):
  without it the switches left the bus as -MWR rose, up to 140 ns before memory D's delayed WE (CD4050B) latches them;
  DRIVE holds them until -MRD falls in the next cycle, as INP 4 already does.
- **Hand controls (ELF-style):** SW10 RUN/RESET and SW11 LOAD ground -RESET and -PAUSE directly (no driver chips; the CPU
  card's Schmitt buffers take the bounce). INPUT (SW9) is debounced (R9 10k, C1 470 nF, Schmitt: about 5 ms).
- **Data switches: eight vertical SPDT toggles, SW1-SW8** (Ken, 2026-10-30: "vertical, just like the YACC1 IO card";
  Marquardt M9040P, the YACC1 footprint): common = the bit, ends on +5V and GND, so no pull-downs.
  The front edge is 4.00 in: the 8 data toggles, INPUT, RUN, LOAD, 10 LEDs and two TIL311s need two or more rows near it
  (or a taller card); the toggle part (the E-Switch 100 footprint is a placeholder; a smaller sub-miniature toggle may fit
  better) is to choose with the board.
- **TIL311:** pinout and footprint (HTIL311A, 0.3 in rows) taken from Ken's built YACC1 IO card (2026-10-30): 3/2/13/12 =
  data A-D, 5 latch strobe and 8 blanking to GND, 1 LED supply straight to +5V, 14 Vcc, 4/10 decimal points unused.
- **No pull-ups on the bus lines** here: the CPU Rev D and the bus Rev D have them.

## Board (2026-10-30): `gen/make_board.py`

- **5.50 × 4.00 in**, J1 = `s5io:C36` (as CPU Rev D), its pins named on the silkscreen; the card-support strips kept free.
- **Front panel as on Ken's YACC1 IO card** (Ken, 2026-10-30): eight vertical M9040P toggles in a column (BIT 7 at the top,
  each labelled 0 / 1 at its ends), then RUN/RESET (RUN / RESET) and LOAD (OFF / LOAD); INPUT push-button beside LOAD;
  the eight bit LEDs (7 … 0), Q and PWR in a column at the front edge with their resistors; the two TIL311s side by side in
  the bottom-right corner (U7 bits 7-4, U8 bits 3-0). The HTIL311A footprint's drawing is on F.Fab in this copy (it ran over
  its pads on the silkscreen). U1 ('138) sits beside N0-N2 at the bottom of the connector.
- **2 layers**, Freerouting (869 segments, 21 vias), GND pours both sides. `preorder_check --layers 2`: **PASS** (ERC 0,
  DRC 0, parity 0, netlist 64/64, bypass caps 0.1", schematic redrawn). Not ordered.
- To check before an order: the M9040P toggles still to be had (or a pin-compatible vertical SPDT toggle: 3 pins on 4.7 mm),
  the switch lever direction against a real part (labels assume the lever closes the common to the far end), Ken's look at
  the pictures.
- **Emulator (2026-10-30):** `python3 -m s5emu --hw --cpu-rev D --panel A` runs the card from its netlist: OUT 4 / INP 4,
  INPUT on -EF1, RUN/LOAD, one DMA IN per INPUT press. A 9-byte program toggled in ELF-style (RUN off, LOAD on, toggles +
  INPUT per byte; LOAD off; RUN on) runs from 0000 and copies the toggles to the LEDs and TIL311s, with no bus events; the
  CPU card's RESET/RUN then boots HBIOS again (tests/test_hw.py `IOPanel`, 4 tests; all 30 pass).
