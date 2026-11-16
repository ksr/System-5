# System-5 timing review

Started 2026-10-07. A worst-case static timing check of the bus paths of the cards as built: CPU A (with its rework), memory Rev D (the card of record), 6845 (worked on Rev A; Ken's card is Rev B, whose bus side is the same), IO A and IDE A.

The gate-level emulator (`software/s5emu --hw`) shows the logic is right: the right chip answers, and no two drive the bus.
It switches every gate instantly, so it cannot show whether signals arrive in time. This review covers that.

The numbers come from two tools that share one table of 1802 timing and part delays:
- **`python3 -m s5emu.timing [MHz]`** (from `software/s5emu`) derives the paths **from the netlists**, the same ones `--hw` runs. It prints each check with the gate chain behind its worst arrival. See [Automated analysis](#automated-analysis).
- **`tools/timing_review.py [MHz]`** has the same checks written out by hand, kept as a cross-check.

## What the checks rest on

**The 1802.** The figures are from the CDP1802A datasheet in `../private-resources/elf/reference/datasheets/cdp1802.pdf` at VCC = VDD = 5 V: the timing tables on pages 6-9 and the edge positions in Figure 4 (page 10).
In clock periods T from the start of a machine cycle:

| Event | When |
|---|---|
| High address byte valid | ≤ 850 ns (typical 600) |
| TPA | rises at 1.0 T, falls at 2.0 T (+ up to 300 ns) |
| High address held after TPA falls | T/2 − 25 |
| Setup of the high address to TPA | 2T − 550, **to TPA's falling edge** (Figure 4) |
| Low address byte valid | 2.5 T + ≤ 350 |
| -MRD low (read cycles) | 1.5 T to the start of the next cycle |
| -MWR low (write cycles) | 5.0 T to **7.0 T** (+ up to 300) |
| TPB | 6.5 T to **7.5 T** (+ up to 300) |
| Data latched into the CPU | at 7.5 T: setup ≤ 25 ns, hold ≤ 200 ns |

The datasheet gives maximum delays only, so "fast" edges use the typical value (200 ns for TPA/TPB). A real 1802 can be faster than that.

**The clock.** The CPU card's crystal marking can't be read in the photos, and the board file has no part values.
The review assumes **1.76 MHz** (a 3.52 MHz crystal ÷ 2, usual for an 1861 system).
`tools/timing_review.py 1.79 2.0 …` evaluates other speeds.

**The parts.** `PARTS` in the script lists each part's maximum delays (5 V, 25 °C) and the datasheet they come from.
They were typed in from the manufacturers' published figures, not read from copies in the repo.
They should be checked once those datasheets are added to `../private-resources/elf/reference/datasheets/`: TI SN74LS series, CD4050B, CD4042B, CY62256, AT27C256, MBM2732A, IDT7134, MC6845/HD6845, CDP1852.

## Findings at 1.76 MHz

| # | Card | Finding | Worst case | Typical | Severity |
|---|---|---|---|---|---|
| T1 | CPU | 74LS374 latches the high address on TPA's **rising** edge | **−102 ns** setup | +148 ns | High (design) |
| T2 | 6845 | 6845 R/W (= -MWR) goes high **while E (= TPB) is still high** | **−394 ns**, at any clock speed | same | Medium (works today; check) |
| T3 | 6845 | E high time (= TPB width) vs the 6845's 450 ns minimum | +18 ns | +118 ns | Low |
| T4 | 6845 | Register read: data setup before the 1802 latches it | **−77 ns** | +23 ns | Low (CRTC reads are rare) |
| T5 | 6845 | Register read: data held after the 1802 latches it (E = TPB gates it) | +20 ns | more | Low (unspecified minimum) |
| T6 | IDE | INP 3 into RAM: drive data still there when the RAM's WE rises | +49 ns | more | Low (fails worst case from about 2.2 MHz) |
| — | all | Memory reads and writes, the 4042 and 373 latches, -VMA, CS/RS setup, DIOR, the keyboard port | ≥ 194 ns, mostly > 2 µs | | OK |

### T1: the CPU card's address latch clocks on the wrong edge of TPA (High)

As built, IC1 is a 74LS374, a flip-flop that loads on TPA's *rising* edge (the schematic has a transparent 74LS373 that latches on the *falling* edge).
The datasheet only guarantees the high address byte 2T − 550 ns *before TPA falls*.
At TPA's rise the high byte can still be on its way: with a slow 1802 (address 850 ns) and a fast TPA (200 ns), it arrives 82 ns *after* the edge.
The 374 then loads the previous low byte as the high address, and that cycle's EPROM window, -VMA and the boot flip-flop's A15 clock are all wrong.

It works on the real card because a typical 1802 has the high byte out about 170 ns before TPA rises.
Even so, it is a race: another 1802, a colder or warmer board, or a faster clock could break it, and the symptom would be intermittent boot failures or wrong reads.

Context: the rework (`hardware/cpu/eagle/rev-a/rework/README.md`) probably chose a 374 to avoid the 373's transparent window, in which a stale byte could glitch A15 and set the boot flip-flop early.
**The fix that keeps both:** clock the 374 from *inverted* TPA (its falling edge).
The CPU card has two spare inverters, IC6C and IC6E of the 74LS05 (their inputs are grounded today).
They are open collector, and the clock edge that matters is that output rising, so it needs a stiff pull-up (about 1 kΩ) to give a clean, quick edge.
IC7 (74LS00) has no free gate: three run the oscillator and one makes -VMA.
Setup becomes 2T − 550 − one gate = 471 ns at 1.76 MHz.
The boot flip-flop then clocks a little later in the cycle (TPA's fall + 28 ns), and -VMA is still settled well before the low address (memory data needs nothing earlier).

### T2: 6845 register writes end with R/W going high during E (Medium)

The 6845 card wires the CRTC's R/W to bus -MWR and its E to TPB.
Figure 4 puts the end of MWR at 7.0 T and the end of TPB at 7.5 T, so for the last half clock of every register write, E is high with R/W high.
The MC6845 needs R/W held 10 ns past E's fall.

This is independent of the clock speed: it is how the 1802's strobes are placed.
Two things follow:
- **The write itself.** If the HD6845 took write data on E's fall, writes would be lost. The card works (HBIOS sets up the CRTC), so the fitted HD46505 evidently takes the register while R/W is low, before R/W rises.
- **Contention.** Once R/W is high with CS and E active, the 6845 drives the data bus, while the 1802 keeps driving its write data until T − 200 ns after MWR ends. Both drive the bus for about 250 ns on every CRTC write. It is short and the drivers are weak (NMOS against CMOS), so it is unlikely to damage anything, but it is a real fight.

**Check:** a scope on the 6845's E, R/W and a data line during a CRTC write.
**Fix in a new revision:** gate R/W so it cannot rise before E falls, for example by latching -MWR at TPB's rising edge or by qualifying E with -MWR for writes.

### T3-T5: the 6845's margins (Low)

- **T3.** E = TPB is one clock wide, less the skew between its two edges: 468-568 ns against a 450 ns minimum. It passes at 1.76 MHz and fails above about 1.9 MHz.
- **T4.** E rises at 6.5 T plus up to 300 ns; the 6845 may take 320 ns more to drive its data; the 1802 latches at 7.5 T, with 25 ns setup. In the worst case that is 77 ns late; with a typical TPB (200 ns) it is 23 ns early. (The first version of this review used the typical TPB and reported +23; the netlist analysis takes the worst case.)
- **T5.** The 6845 stops driving 20 ns after E falls. The 1802 can need its input held 200 ns past its latch point, and TPB's fall delay (typical 200 ns) has no specified minimum. This holds only on typical timing.

These concern CRTC register **reads** (cursor position, R14/R15), which HBIOS rarely does.
Video RAM at 7000-77FF is not affected: the IDT7134 is enabled by the address decode and -MRD, not by TPB.

### T6: INP from the IDE drive into RAM (Low)

For `INP`, the 1802 writes the device's byte into memory with -MWR.
The IDE card ends DIOR at TPB's fall; memory Rev D's WE is -MWR through a CD4050B (up to 140 ns).
At 1.76 MHz the RAM latches 49 ns before the drive lets go (counting no minimum delay through the four gates between TPB and DIOR), and bus capacitance holds the value a little longer.
It fails the worst case from about 2.2 MHz (2.1 MHz is marginal).

### Everything else passes

These have hundreds of ns to spare, mostly over 2 µs:
- Memory Rev D: RAM and EPROM reads, RAM writes, and the CD4042B's setup and hold.
- 6845 card: the 74LS373 address latch, CS and RS setup to E.
- CPU card: -VMA (settled about 800 ns before the memory card needs it) and boot EPROM reads.
- IO card: the keyboard CDP1852 port.
- IDE card: DIOR width and drive data setup.

At 1.76 MHz, the 1802's bus is slow next to these parts.

## CPU Rev D at 2 MHz (2026-10-30)

`python3 -m s5emu.timing --cpu D 2` (from software/s5emu): CPU Rev D (`hardware/cpu/kicad/rev-d`, 4 MHz oscillator / 2)
with the cards as they are today (memory D/E, 6845 B, IO A, IDE A). HCT delays: TI SN74HCT data sheets, 4.5 V, 85 C, typed
in (`timing.py` PARTS). Compared with Rev A as built at 2 MHz and at 1.76 MHz:

| Check | Rev A, 1.76 MHz | Rev A, 2 MHz | **Rev D, 2 MHz** |
|---|---|---|---|
| T1: the CPU's A8-A15 latch | -102 ns FAILS | -170 ns FAILS | **no violation** (74HCT373, transparent on TPA) |
| CPU: -VMA settles | +818 | +716 | +608 OK (HCT is slower than LS, still far inside) |
| CPU: 2732 read data | +2166 | +1825 | +1825 OK |
| Memory D, IO A, IDE read/write data | OK | OK | OK (unchanged; microseconds to spare) |
| **T3: 6845 E (= TPB) high time, 450 ns min** | +18 marginal | -50 FAILS | **-50 FAILS** |
| T4: 6845 register read data | -77 | -145 | -145 (worst case; +23 typical at 1.76) |
| T2: 6845 R/W during E | -394 | -360 | -360 (structural; works on the HD6845) |
| T5: 6845 read hold | +20 marginal | +20 | +20 |
| **T6: INP 3 into RAM, drive data held** | +49 | +15 marginal | **+15 marginal** |

- **The CPU card itself is clean at 2 MHz**: T1 is gone, and every CPU-card path has hundreds of ns to spare.
- **2 MHz is a 6845 limit, not a CPU limit.** T3 (E = one clock wide) fails above about 1.9 MHz with the 1 MHz-grade
  HD46505RP fitted. Options: a faster CRTC grade on the video card (the 1.5 / 2 MHz grades, MC68A45 / MC68B45 or the
  equivalent HD46505 grade, have a much shorter minimum E high time: to check against their data sheets), or run the CPU
  Rev D at 1.79 MHz with a 3.579545 MHz oscillator (X1 is a socketed DIP-8 can: no board change).
- **Decided (Ken, 2026-10-30): keep 2 MHz** and fit a faster CRTC grade on the video card Rev C; its timing goes into
  `timing.py` once the part is chosen.
- **T6 is down to 15 ns** worst case at 2 MHz (the IDE card ends DIOR at TPB's fall, memory D's WE is -MWR through a
  CD4050B). Typical timing and bus capacitance add margin; a later IDE or memory revision could hold DIOR longer.
- **Start-of-cycle contention:** a read that moves from the CPU card's EPROM to another card's chip may overlap by up to
  ~110-170 ns worst case (Rev A at 2 MHz, R13 not counted: 7-62 ns), because the HCT decode (74HCT373 → 74HCT20 →
  74HCT00 × 2) is slower than Rev A's LS chain; the worst path is the boot flip-flop's own cycle. Like C1/C2, noise only:
  the data is latched about 3 µs later. 74AHCT/74ACT parts (pin-compatible, faster) would shorten it if wanted.

## Start-of-cycle contention (checked 2026-10-07)

-MRD goes high at the start of every machine cycle and low again at 1.5 T, even between two reads (Figure 4).
Every chip that drives the data bus in a read has its output enable on -MRD: memory Rev D's chips through a CD4050B, the CPU's 2732 and the 6845 card's 7134 directly.
So at each cycle start all of them stop driving.

A fight needs a chip that is **still selected from the previous cycle** when -MRD falls again, while a chip on **another card** is selected for this one.
`python3 -m s5emu.timing` checks every pair of cards (`contention()` in `timing.py`), with the same netlist paths.
It counts only chips the jumpers can select: memory D's IC3 and IC11 are never selected under the default map, so they drop out.
Chips on the same card switch together from one decode, with only gate skew between them, and are not reported.

| # | From (previous read) | To (this read) | Worst-case overlap | Typical | Cause |
|---|---|---|---|---|---|
| C1 | memory D RAM IC1, EPROM IC5 | CPU boot EPROM (F000), 6845 video RAM (7000) | **~190-230 ns** | none | the CMOS high-address path: the chip enable settles at 1275 ns, -MRD re-enables at about 1107 ns |
| C2 | CPU boot EPROM | 6845 video RAM | 28 ns + R13's RC (about 41 / 56 / 89 / 157 ns for 1 / 2.2 / 4.7 / 10 kΩ) | small | the 2732A's 100 ns output float time, then the 74LS05 open collector's RC rise |
| C2 | CPU boot EPROM | memory D RAM | 0 below about 2.2 kΩ; 34 ns at 4.7 kΩ, 102 ns at 10 kΩ | none | the same; memory D's -MRD is 55 ns later through its CD4050B |

All of these happen at the very start of the read data window, about 3 µs before the 1802 latches data at 7.5 T, so **no read is corrupted**.
What they cost is supply current spikes and ground noise while two outputs fight.

- **C1** comes from the slowest path on the bus. The 1802 may present the high address as late as 850 ns. Then a CD4050B (up to 140 ns) and a CD4042B (up to 220 ns) delay it before the 74LS151 and 74LS32 make the chip enable.
  Typical parts settle it by about 810 ns, before -MRD falls, so it only fights at the slow end.
  Memory Rev D (ordered 2026-10-09) is scrap; Rev E, the same circuit, is built and is the memory card in the machine (since 2026-10-31), so C1 applies to the machine as it runs today. **Do not swap the CD4050B for a 74HC4050** (checked 2026-10-08): the same buffer also delays -MRD to the chips' output enables, so a faster one turns the outputs on sooner and C1 grows slightly (241 ns against 228). C1 comes down to the CD4042B (up to 220 ns). Removing it needs a faster latch, which is a layout change.
- **C2** depends on R13, the pull-up on the boot EPROM's chip enable, whose value is unknown (its colour bands, or a meter).
  1 kΩ or less keeps it to the 2732A's own float time.

## Not covered yet
- **The reset and run circuit** (IC3/IC4/IC5/U1 and its rework) and the 1861's DMA timing.
- **Electrical loading:** fan-out on the bus lines, CMOS input levels from LS outputs (the 4050 and 4042 on the memory card), and rise times on long lines.


## Automated analysis

`software/s5emu/s5emu/timing.py` (2026-10-07) does the review from the netlists, for each card as `--hw` builds it (CPU A-built with its rework, memory D, 6845 B, IO A, IDE A):

1. **Events.** A machine cycle (read, write, `INP n`, `OUT n`) is a set of bus events, each a window [earliest, latest] from the table above: the high and low address bytes, TPA and TPB edges, MRD, MWR, N0-N2 and the CPU's write data. -VMA is computed on the CPU card and passed to the other cards as an event.
2. **Arcs.** Each gate output depends on its inputs as the gate models say (`deps()` in `logic.py`), with the part's delay. Each event is propagated along every path. The latest arrival at each net keeps the chain of gates it came through.
3. **Latches and registers.** The analyser simulates the card's own logic through the cycle's phases to find which bus edge opens and which closes each latch (or clocks each register). A data event that settles before the closing edge, less setup, passes as the latched value. One that changes only after it, plus hold, is blocked. One that overlaps it is reported as a violation. That is how T1 is found: "IC1 74LS374: input A_hi changes at 0-850 ns, the latch closes on TPA_rise at 768-868 ns".
4. **Feedback loops.** Gates in a loop (the IDE and IO cards' NAND latch for the INP window) are found as strongly connected sets, and an event leaves the loop within one gate delay per net in it.
5. **Checks.** These are the ones in the table above, per bus device: memory access and write timing, the 6845's bus timing, the CDP1852 select, and the ATA strobes.

Limits:
- Gates have no minimum delay (0), so hold-type checks are conservative.
- Delays are per part type, not per edge or per load.
- The 1802's fast edges are its typical values.
- Contention is checked only between cards; chips on one card are assumed to switch together.

Tests: `software/s5emu/tests/test_timing.py`.

One emulator fix came out of this work. A NAND latch whose two outputs start equal made the simulator flip both gates forever, because every gate was updated at once. Real gates never switch exactly together, so after 20 such passes `Circuit.settle` now updates one gate at a time and the latch falls into a state.

## What would settle the open points

1. The CPU crystal's frequency (its marking, or a frequency counter on TPA: TPA = clock ÷ 8).
2. R13's value on the CPU card (colour bands): it sets C2.
3. A scope or logic analyser on TPA, the 374's A15 output, -VMA, and the 6845's E and R/W during a CRTC write. That would confirm T1 and T2 directly.
4. The datasheets above, added to `../private-resources/elf/reference/datasheets/`, to check the part delays.
