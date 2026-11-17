# 6845 video card Rev C: design notes (draft)

The console card: Rev B's 6845 video (BYTE, May 1979) plus the PS/2 keyboard interface moved over from the IO card, on the
36-pin bus. Started 2026-10-30 (Ken). Nothing is drawn yet; this file collects the decisions and the proposals still to
agree. References: Rev B (`../rev-b/`, `docs/manual/video-6845-card.md`), the IO card's keyboard half
(`hardware/io-1861-keyboard/kicad/rev-a/`, `docs/manual/io-card.md`), the bus (`docs/manual/bus.md`, "The 36-pin extension").

## Decided (Ken, 2026-10-30)

| Item | Decision |
|---|---|
| Video | Rev B's circuit, with a **2 MHz-grade 6845 CRTC** (Ken, 2026-10-30: for the CPU Rev D at 2 MHz; item 9): HD6845-family CRTC, IDT7134 dual-port video RAM, 2732 character generator ("goodfont"), the dot-clock oscillator (9 MHz for HBIOS's CRTC table), composite out. |
| Keyboard | **The same path as the IO card today:** PAK-VI PS/2 decoder (AWC, still sold: <https://www.awce.com/pak6.htm>) → PIC16F84 with Ken's firmware (`hardware/io-1861-keyboard/pic-ps2-firmware/`) → CDP1852 input port. |
| Keyboard port and flag | Port 1 (as today), the 1852's SR on **-EF3** (the 36-pin straight-across EF mapping: -EF3 → EF3, where HBIOS waits), so HBIOS needs no change. |
| Bus | The 36-pin interface. The video side uses only the 30-pin lines; the keyboard flag uses -EF3. |
| Layout | The board layout rules (front-edge video jack, DB9, PS/2 socket and LEDs; labels; readable references with IC types), `cottageworker.com` and the board name/revision on the silkscreen, 0.1" bypass caps. |
| Layers | **2 copper layers if at all possible** (Ken, 2026-10-30): cheaper and quicker to check; `pcb-check --layers 2`. Go to 4 only if routing truly fails, and ask first. |

## Proposed (to agree with Ken)

1. **Flag jumper.** A 3-pin jumper puts the 1852's SR on -EF3 (default, CPU Rev D) or on -EF (bus pin 25), so the card also works
   with the old CPU Rev A, whose EF inputs see only -EF (its JP1 routes -EF to EF3).
2. **Keyboard port jumper.** Keep the IO card's port-select header (ports 1-7, default 1) and its decode: a 74HCT138 on N0-N2, gates
   on -MRD, the TPA/TPB strobe window (the proven circuit; the bus has no -INP/-OUT).
3. **Video block.** Keep SV1 (74LS85 compare with -VMA). Default block 7 (7000-7FFF, today's HBIOS); block E (E000-EFFF) is one
   jumper move (SV1 7-8) once HBIOS is rebuilt (`BACKLOG.md`, "Move the 6845 video to E000-EFFF").
4. **Logic family.** HCT where the part is pin-compatible and the timing allows (74HCT373 latch, 74HCT138); keep LS/S where BYTE's
   video timing depends on it (the '163 must stay a 74LS163 or 74HCT163, `video-6845-card.md`). The PIC's and PAK-VI's clocks:
   their own resonators, as on the IO card.
5. **PIC part.** The PIC16F84A is old; a pin-compatible PIC16F628A or PIC16F88 runs the same firmware with small changes
   (configuration bits, the comparators off). Keep the 18-pin socket so either fits.
6. **Outputs (front edge):** composite RCA, the DB9 (video, HSYNC, VSYNC), the PS/2 mini-DIN.
   LEDs: PWR, KEY (1852 SR: a character waiting), and the PAK-VI data LED if kept.
7. **Board size.** Rev B is about 141 × 96 mm and full; the keyboard adds a PAK-VI, a PIC, a 1852, a '138, gates and the socket.
   Check the fit early; a taller card (the bus has no height limit beyond the card guides) or SMD resistor networks are the options.
8. **Folder and generator.** `hardware/video-6845/kicad/rev-c/` with `gen/netlist.py`, `make_schematic.py`, `make_board.py`, a
   `schematic/spec.py`, and lines in `build_all.sh` / `make_book.py`. The 2005 Rev B netlist (`../rev-b/reports/netlist.net`) is
   the starting point for the video half, the IO card's for the keyboard half.
9. **CRTC speed grade: decided, a faster grade** (Ken, 2026-10-30: the CPU Rev D stays at 2 MHz). To do: pick the part (a
   2 MHz-grade 6845, e.g. the MC68B45 or the equivalent HD46505 grade), read its minimum E high time, tAS/tAH and data
   delay from its data sheet into `timing.py` PARTS, and rerun `python3 -m s5emu.timing --cpu D 2` with it (T3-T5).
   Background (timing review 2026-10-30): with CPU Rev D at 2 MHz, E = TPB is ~400 ns high worst case; Rev B's
   1 MHz-grade HD46505RP needs 450 ns (T3 fails above ~1.9 MHz). Fit a 1.5 or 2 MHz grade CRTC (check its minimum E high
   time), or the CPU runs at 1.79 MHz. Also: the IDT7132 (2K) would do for the video RAM; only 2K of the IDT7134 is used.
10. **Emulator.** s5emu models Rev B and the IO card from their netlists; model Rev C the same way, so HBIOS and ELF/OS boot on it
   before the order.
