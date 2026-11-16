# CPU Rev A bring-up from the bus driver (2026-10-31)

The setup: the bus driver's SPARE1 (J2 pin 1) is wired to the CPU card's IC8 pin 3, the clock input of the 74x74 that divides
the crystal oscillator down to the 1802's CLOCK. IC8 pin 3 is lifted from IC7. Each rising edge on SPARE1 is
therefore one 1802 clock edge, and the 1802 (a static part) stands still in between. The bus driver stays in MONITOR mode
(firmware `clk-1`) and reads the whole bus after every edge. The tool is
`software/busdrv/cputrace.py`. **Restore IC8 pin 3 to IC7 before running the card from its crystal again.**

## Results

- **The card runs HBIOS correctly.** On the bench with only the CPU and 6845 cards in (no memory card), from power-on:
  **20,799 bus cycles agree with the emulator** (`s5emu --hw`, CPU A-built + 6845 B, from their netlists), from the
  first fetch at 0000. This covers the boot remap to F000+, the CRTC set-up (7800/7801) and clearing the screen at 7000+.
  The comparison stops where HBIOS first reads its stack at 00FE/00FF. There is no RAM there, so the card reads whatever
  the floating bus holds and the program goes its own way from then on. That is the expected end.
  - Trace: `2026-10-31-trace-from-power-on.txt` (one line per machine cycle). The raw bus states after every
    clock edge are in `.raw.gz`; `cputrace.py --from-raw FILE --compare` reads it as it is.
  - The screen came on and cleared, as on the trace.
- **IRX (60) does a dummy read** of R(X) in its execute cycle, with −MRD low. The emulator does not log it, because the
  data is not used. `cputrace --compare` skips such reads.
- **Timing finding T2 seen on hardware:** on a CRTC write, the 1802 raises −MRW while TPB is still high. The 6845 then
  sees a read and drives the bus (00) for the rest of TPB. This is harmless, because the CRTC latches the right byte
  (the screen works), but it is a real bus fight. `cputrace` takes a write's data while −MRW is low.
- **A floating data bus holds its last byte** (the 2009 backplane has no data pull-ups). With no RAM, reads of
  00FE/00FF returned the previous fetched byte (72, F0), not FF as the emulator assumes. This answers question 6 in
  `BACKLOG.md` (no pull-ups; the bus holds its last value), and is fixed on bus Rev D (10k pull-ups on D0–D7).
- **Reset works only at power-on.**
  - S1 does not reset the 1802, even with the clock running.
  - Bus −RESET from the bus driver does not reset it either: the 1802 keeps executing while −RESET is held low.
  - S1 does not pull bus −RESET.
  - This fits the 2005 reset rework (IC5 pins 1/3 bent out, a wire to the 1802 socket; question 2 in `BACKLOG.md`).
- **The watchdog** (CM1232/DS1232) gave no reset pulses during the stepped run: the rework disables it.

## Whole system (2026-10-31 / 11-01)

- With MEM3-E (RAM 0000-6FFF, EPROM 8000-EFFF) and the 6845 in, still clock-stepped: the screen cleared, the cursor
  flashed and HBIOS printed its own `test>` prompt (F9C6 in the CPU ROM: no boot disk, the IDE card was out).
- IC8 pin 3 restored to IC7 (the card runs from its crystal again). With the IO card and a PS/2 keyboard added, all
  cards in: **the system works** - HBIOS boots to `test>` and takes keys.
- `cputrace.py --jumpers RRRRRRR-EEEEEEE- --mem-rom <image>` gives the emulator the same memory card and EPROM.
- **Clock-select jumper added (Ken, 2026-11-01):** IC8 pin 3 now takes either IC7's oscillator (normal running) or
  the bus driver's SPARE1 (stepped clock for `cputrace.py`), chosen by a jumper, so no more lifting pins.
