# The System-5 bus

The System-5 bus is the System-4 bus of 1979, kept so old and new cards could share one backplane.
It is the 1802's own bus with almost nothing added: the multiplexed address byte, the two timing pulses, the two memory strobes, the I/O lines, one flag, one interrupt and reset. The one signal of my own is **-VMA**, valid memory address, which lets the CPU card hide the bus while its boot EPROM is answering.

## Mechanics

- **Backplane:** System-4's was Vero board with single-row SIP sockets and card supports, from the late 1970s. System-5's is **a PCB, the 2009 design** (2026-10-26): six **36-pin** slots, every pin bussed, no regulator. Slot pins 1–30 are the 30-pin bus below, pin for pin; 31–33 are -EF1, -EF2, -EF3 (above) and 34–36 -INP, -OUT, EXP (below), so a 30-pin card fits the middle 30. Its power connector X1 brings in GND only: on the copper X1 pin 2 touches the GND track, while the +5V track stops short of pin 1 (X1 was moved after routing), so +5V needs a wire to X1 pin 1 or comes in through a slot. KiCad: `hardware/bus/kicad/rev-2009/`; the 2005 Rev B design (6 slots with a regulator, not built) survives as CAM files (`hardware/bus/eagle/rev-b/fab/`).
- **New backplane, Rev D (2026, not yet ordered):** `hardware/bus/kicad/rev-d/` (S5BUS-D): **eight** 36-pin slots on the same 1.0" pitch and positions, every line one straight track; +5V and GND in on a screw terminal at the edge (both wired, unlike 2009's X1) through a 5 A power switch, a 4 A polyfuse and a P-channel MOSFET that keeps a reversed supply off the cards, a power LED, 220 µF bulk and 0.1 µF at each slot, and 10k pull-ups on D0–D7 (an empty read gives FF) and on -EF, -EF1–3, -PAUSE, -DMAIN (positions 34–36 relabelled -PAUSE, -DMAIN, SC0 on 2026-10-30 to match the 36-pin extension below; copper unchanged). Each slot's silkscreen brackets positions 4–33 (the 30-pin card) with a triangle at the +5V end: plug the card's +5V pin there, with its components facing the power connector (the arrow under each slot).
- **Card edge:** a single-row, 30-pin, 0.1" right-angle header at the bottom edge of each card (the Eagle part `C30`; the KiCad master boards keep the same footprint and position).
- **Card size:** 5.50" × 3.75" (139.7 × 95.25 mm) for the 2005 cards; the 2026 KiCad boards are about 141 × 96 mm. The connector is centred on the card's bottom edge (the 2005 board notes: centre at 0.2", 1.875").
- **Keep-outs:** 3.00" × 0.15" strips at both bottom corners, beside the connector, where the card supports grip the board.
- **Power:** +5 V only, on pin 1; ground on pin 30. There is no other supply on the bus.

## Pinout

Checked against the connector on every converted card (CPU A, memory E, 6845 B, IO A, IDE A, bus driver B): all six agree.

| Pin | Signal | Driven by | Used by | Notes |
|---|---|---|---|---|
| 1 | +5V | power supply | every card | |
| 2–9 | D0–D7 | the 1802 (writes, OUT data from memory) / the selected card (reads) | every card | bidirectional, unbuffered on every card |
| 10 | Q | 1802 | (nothing on the present cards) | the 1802's Q output; the CPU card also drives its Q LED |
| 11 | TPA | 1802 | CPU, memory, 6845, IO, IDE | timing pulse A: the high address byte is on A0–A7 while it is high |
| 12 | TPB | 1802 | 6845 (its E), IO, IDE | timing pulse B, at the end of the cycle |
| 13 | -MRD | 1802 | memory, 6845, IO, IDE | memory read strobe, active low; also the direction of an I/O instruction |
| 14 | -MRW | 1802 | memory, 6845 | memory write strobe, active low (the 1802 calls it -MWR) |
| 15–22 | A0–A7 | 1802 | CPU, memory, 6845 | multiplexed: high byte during TPA, then low byte |
| 23 | -INT | IO card (the 1861) | CPU | interrupt request, active low, open collector, pulled up on the CPU card |
| 24 | N2 | 1802 | IO, IDE | I/O lines: n during `OUT n` / `INP n`, 0 otherwise |
| 25 | -EF | IO card (keyboard flag, SV1 2-3) | CPU (jumpered to one of EF1–EF4 by JP1) | the one external flag line; called -EF4 on the 2005 schematics |
| 26 | -VMA | CPU card | memory, 6845 | valid memory address, active low (see below) |
| 27 | -RESET | CPU card (CM1232) | 6845 (the CRTC's RESET), IO (1852, 1861, PIC, PAK-VI), IDE (the drive's RESET) | active low, open collector |
| 28 | N1 | 1802 | IO, IDE | |
| 29 | N0 | 1802 | IO, IDE | |
| 30 | GND | | every card | |

Not on the bus: the clock, the DMA lines, the state codes SC0/SC1 and the other three flags. The 1861 needs them, so they run from the CPU card to the IO card on a ribbon (CPU SV3 to IO SV3); the front panel connector (CPU SV6) carries the run-control lines.

## The 1802's machine cycle

Every 1802 instruction is two or three machine cycles of 8 clocks each: one fetch, one or two execute.
In clock periods T from the start of a cycle (CDP1802A datasheet, Figure 4, at 5 V):

| Event | When | What the cards do |
|---|---|---|
| High address byte valid on A0–A7 | ≤ 850 ns (typically 600) | |
| TPA high | 1.0 T to 2.0 T | CPU card latches the high byte (74LS374 as reworked; on TPA's rising edge, see timing finding T1); memory card (CD4042) and 6845 card (74LS373) are transparent while TPA is high and hold when it falls |
| Low address byte valid | 2.5 T + ≤ 350 ns | the low byte goes straight to the chips |
| -MRD low (read cycles) | 1.5 T to the end of the cycle | output enables |
| -MWR low (write cycles) | 5.0 T to 7.0 T | write enables; data is valid before it falls and after it rises |
| TPB high | 6.5 T to 7.5 T | 6845 E; I/O strobes end |
| Data latched by the 1802 | 7.5 T | read data must be set up 25 ns before |

At the clock assumed in the timing review (1.76 MHz: a 3.52 MHz crystal ÷ 2), T is 568 ns and a machine cycle 4.5 µs. The cards are much faster than the bus: almost every path has hundreds of nanoseconds to spare. The exceptions are listed in `hardware/TIMING-REVIEW.md` (T1–T6).

### Reading memory

A memory card sees: TPA (latch the high byte) → the low byte → -VMA low → -MRD low → it drives D0–D7 until -MRD rises at the end of the cycle.

### Writing memory

The same, with -MRD high; the 1802 drives D0–D7 and pulses -MWR from 5 T to 7 T. RAM writes on -MWR's rising edge, with the data still valid.

### I/O instructions

| Instruction | N0–N2 | -MRD | Data on the bus | Who drives it |
|---|---|---|---|---|
| `OUT n` (61–67) | n | low (the 1802 reads M(R(X))) | the byte at M(R(X)) | the memory card; the port latches it |
| `INP n` (69–6F) | n | high (the 1802 writes M(R(X))) | the port's byte | the port; memory stores it with -MWR, and the 1802 also loads it into D |

So an I/O card selects on N ≠ 0 and takes the direction from -MRD: low = `OUT` (write to the port), high = `INP` (read from the port).
Both I/O cards (IO and IDE) use the same small circuit for this: a 74LS138 on N0–N2, gates on -MRD, and a NAND-gate latch timed by TPA and TPB that makes the strobe window (`hardware/circuits/eagle/` holds the sub-circuits).

### -VMA

-VMA is my addition. The CPU card drives it high while its own EPROM is answering, and low when the address belongs to the bus:

| CPU card state | -VMA | The CPU card's EPROM |
|---|---|---|
| After reset, before any access with A15 high (boot map) | high | answers at every address |
| After that, Boot/REMAP mode (SV5), address in the EPROM's 4K window (SV2/SV4, normally F000) | high | answers |
| After that, any other address | low | off |
| No-ROM mode (SV5) | always low | never |

Memory cards and the 6845 card must qualify their chip selects with -VMA (the memory card ORs it into each chip's !CE; the 6845 card enables its 74LS85 compare with it). I/O cards do not look at -VMA.

## Rules for a card

These follow from how the bus works and from the 2005 board notes (`hardware/board-notes/`) and the 2026 build rules (`hardware/BUILD-RULES.md`):

- **Latch the high address yourself** from A0–A7 on TPA if you decode above A7. A transparent latch (373, 4042) that holds when TPA falls meets the 1802's guarantee; an edge-triggered latch on TPA's rising edge does not (timing finding T1).
- **Qualify memory decodes with -VMA.** Otherwise your card answers alongside the CPU card's boot EPROM after reset.
- **Drive D0–D7 only while selected and while -MRD is low** (memory), or during the `INP` window (I/O).
- **Open-collector only** on -INT, -EF and -RESET: other cards share them.
- **Do not load the bus heavily.** No card buffers the bus (the memory card buffers its own inputs with CD4050Bs); every card adds its inputs to every line.
- **Bypass capacitors:** 0.1 µF on every chip, 0.1" lead spacing (the rule since 2026-10-19).

## The 36-pin extension (draft)

**Status: a proposal (2026-10-30), not yet used by any card.** The 36-pin slots of the 2009 backplane and the bus Rev D carry six lines beyond the 30-pin bus, but until now they had names only (from the 2009 drawing): nothing drove them, and no timing was written down. This section defines them for the next cards: CPU Rev D (`hardware/cpu/kicad/rev-d/DESIGN.md`), the next 6845 video card (with the PS/2 keyboard) and the new IO card (LEDs, switches, TIL311s) and a 36-pin debug board. It changes nothing in the 30-pin bus: a 30-pin card plugs into positions 4–33 and ignores these lines, and a 36-pin card works in a slot whose extra lines nobody drives (the pull-ups hold them inactive).

**Numbering.** Positions are counted along the 36-pin socket, as on the bus Rev D: 1–3 at the +5V end, 4–33 the 30-pin bus (bus pins 1–30), 34–36 at the GND end. The 2009 Eagle drawing numbers the same contacts 31–36, and its copper wired -EF1 to -EF3 in the opposite order to its silkscreen (`hardware/bus/kicad/rev-d/gen/netlist.py`); the silkscreen order (-EF3 next to +5V) is the one used here.

| Position | Signal | Driven by | Used by | Proposed meaning |
|---|---|---|---|---|
| 1 | -EF1 | any card | CPU EF1 (jumper) | external flag, active low, **open collector** |
| 2 | -EF2 | any card | CPU EF2 (jumper) | external flag, open collector |
| 3 | -EF3 | any card | CPU EF3 (jumper): the keyboard on the next video card | external flag, open collector |
| 34 | -PAUSE | a debug board, a front panel (open collector) | CPU card | low = pause: the CPU card pulls the 1802's WAIT low; with -RESET also low the 1802 is in LOAD mode |
| 35 | -DMAIN | a debug board (open collector) | CPU card (the 1802's DMA IN) | low = DMA IN request, **LOAD mode only**: the 1802 writes the bus byte to M(R0) and steps R0 |
| 36 | EXP → **SC0** | CPU card (buffered) | debug board | **SC0**, the 1802's state code bit 0 (low = fetch, while no DMA runs). Not the external clock: that comes in on the CPU card's own EXT CLK header pin |

**Pull-ups.** The bus Rev D pulls -EF1–3 and positions 34–35 (-PAUSE, -DMAIN) up with 10k, along with -EF, -INT and -RESET (RN2); SC0 has no pull-up. So that no card drives the bus with no master present, RN3 pulls N0–N2, TPA and TPB down and RN4 pulls -VMA, -MRD and -MRW up. The 2009 backplane has no pull-ups at all, so on it a 36-pin card must not rely on these lines idling high.

**Flags.** With -EF (bus pin 25; called -EF4 on the 2005 schematics) the bus has four flag lines for the 1802's four EF inputs. The CPU card routes them **straight across** (2026-10-30): EF1 = -EF1, EF2 = -EF2, EF3 = -EF3, **EF4 = -EF**, with a jumper block per EF input to change that. The keyboard flag moves to **-EF3** on the next video card, so HBIOS, which waits on EF3, needs no change. The old 30-pin IO card can only reach -EF: with it, jumper EF3 = -EF. The IDE card uses no flag line (the BIOS polls its status register). Every flag driver is open collector, so several cards may share a line.

**I/O decode stays on the cards.** Positions 34–35 were named -INP and -OUT on the 2009 drawing. It was decided (2026-10-30) not to have the CPU card generate those strobes: the saving is two or three chips per I/O card, against new, untested bus timing that every card would depend on. I/O cards keep decoding N0–N2 and -MRD themselves (above), as the IO A and IDE A cards do; the two lines carry debug control instead.

**-PAUSE and -DMAIN: debug control with the CPU card in place.** The 1802 cannot release its bus, so today the bus driver works only with the CPU card out. With these two lines (and the existing -RESET) a debug board can stop, step and load the machine with the CPU card in:

| Wanted | Lines | The 1802 |
|---|---|---|
| reset | -RESET low (any card) | CLEAR low: reset; every card resets too |
| pause | -PAUSE low | WAIT low, CLEAR high: stops between cycles |
| step | -PAUSE, or the CPU card's EXT CLK pin (jumper wire) | a cycle or a clock edge at a time |
| step an instruction | step until SC0 goes low | stops at the next fetch; address on A0–A7, opcode on D0–D7 |
| load memory | -RESET and -PAUSE low together, then -DMAIN | LOAD mode (WAIT and CLEAR low) |
| run | release -PAUSE and -RESET | runs (the CPU card's RUN pulse after reset) |

**Who drives them** (2026-10-30): the new IO card (ELF-style RUN and LOAD switches, its INPUT button on -DMAIN, its 8 switches as the data) and a debug board (from the Mac), either alone or both; the CPU card has only RESET/RUN and listens. All three lines are open collector, so any card may pull them and none can fight. **One rule for LOAD:** a card drives D0–D7 only for a DMA request it made itself (its own -DMAIN active) and only in the DMA cycle (-MRD high), so the data bus has one source per byte.

**Machine control: who drives what** (2026-10-30). -RESET (bus pin 27, position 30) is open collector like -PAUSE and -DMAIN: the CPU card drives it from its power-on reset and its RESET/RUN switch, and **listens to it**, so any card that pulls it low (the debug board, the IO card's LOAD switch) resets the 1802; every card receives it (the 6845's CRTC, the IDE drive, the IO card's chips), so a reset from any source resets the whole machine. Rev A already took -RESET from the bus. **What a reset starts** (CPU Rev D): HBIOS from the boot EPROM, except after a LOAD: LOAD mode sets the CPU card's LOADED flag, which keeps its boot map off, so LOAD → RESET → RUN runs the loaded program from 0000 (as on a COSMAC ELF); the CPU card's own RESET/RUN switch, and power-on, clear LOADED and boot HBIOS again. Each control works alone or with the others:

| Card | Controls | Lines |
|---|---|---|
| CPU card | RESET/RUN switch (front edge), power-on reset; a PAUSE LED | drives -RESET; listens to -RESET, -PAUSE, -DMAIN; drives SC0 |
| IO card (by hand) | RUN and LOAD switches (ELF-style), the INPUT button, 8 data switches | RUN off = -RESET; LOAD on = -PAUSE (both = LOAD mode); -DMAIN; D0–D7 in its own DMA cycle |
| Debug board (from the Mac) | reset, pause, step, load, run | -RESET, -PAUSE, -DMAIN, D0–D7 in its own DMA cycle; the CPU card's EXT CLK pin (jumper wire); reads SC0 |

-PAUSE is a **level**, not a pulse (Rev A's run latches took pulses on its front-panel header): the CPU card holds WAIT low while it is low. **Loading.** In LOAD mode the 1802 runs only two kinds of cycle (CDP1802 data sheet, `../private-resources/elf/reference/datasheets/cdp1802.pdf`): IDLE, where memory reads M(R0) onto the bus (-MRD low; TPA is suppressed), and DMA IN, where the bus byte is written to M(R0) and R0 steps (-MRD high, -MWR pulses). So the debug board drives D0–D7 **only while -MRD is high** with its request pending, and takes -MWR's (or TPB's) rising edge as "byte written"; it needs neither SC0 nor SC1. Before LOAD, R0 = 0000 (reset clears it). **State codes.** SC0/SC1 are not on the bus. They would let a debug board stop exactly at the start of each instruction (SC = 00 is a fetch); without them it steps by cycle or clock edge.

**The external clock is not on the bus.** The CDP1802 is a static design, so its clock may be slowed, stopped and stepped one edge at a time, which lets a debug board single-step the machine. The CPU card takes an external clock on its own **EXT CLK header pin**, buffered (a Schmitt input, 74HCT14) and held low by a pull-down when nothing is connected, and an INT/EXT jumper picks it; a debug board reaches it with a jumper wire (TTL levels, 0 up to 2 MHz on CPU Rev D). The bus driver (BUSDRV-B, a 30-pin card) does this from one of its J2 spare pins (SPARE1–4), and wires other spare pins to -EF1–3, -PAUSE or -DMAIN the same way when a test needs them (2026-10-30).

**EXP (position 36) = SC0** (2026-10-30; EXP is not the external clock). The state code is 00 in a fetch, 01 in an execute, 10 in a DMA cycle and 11 in an interrupt cycle. With -DMAIN used in LOAD mode only, no DMA cycle happens while the machine runs, so **SC0 low = an instruction fetch**: a debug board stepping the clock (or pulsing -PAUSE) stops at the start of each instruction, and reads the instruction's address off A0–A7 (high byte at TPA, low byte after) and the opcode off D0–D7. That is instruction-level single-step and, with the clock stepped, address breakpoints, from one line. The CPU card drives it totem-pole through a buffer (an 1802 output must not drive the backplane directly). Other candidates, not chosen: the CPU clock out (a card with timing needs can carry its own oscillator), SC1 (needed to find DMA cycles on a running machine, which -DMAIN does not allow), a memory bank bit, a second interrupt. EXP has no pull-up on the bus Rev D, which suits a driven line.

**Finalizing.** The bus Rev D is not ordered yet, so its net names, the pin labels beside each slot, the RN2 silkscreen note and the pull-ups follow this definition once it is settled; its copper does not depend on it.

**-DMAIN is LOAD mode only** (2026-10-30). On a running machine a DMA IN would steal a cycle and write to wherever R0 points (HBIOS and ELF/OS do not set R0 up for it), and a device could not find the DMA cycle without SC1. The CPU card passes -DMAIN straight to the 1802 either way, so allowing running-mode DMA later is a change to this definition, not to the CPU card.

**Open questions.** None left in the line assignments; the exact drive and timing of -PAUSE, -DMAIN and SC0 are settled with the CPU Rev D design (`python3 -m s5emu.timing 2`).
