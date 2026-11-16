# CPU Rev A: the board as built

Read from Ken's photos of 2026-10-07 (`../photos/2026-10-07-*.jpg`, front and back, full resolution), against the converted board (`../../kicad/rev-a`).
`cpu-a-board-map.png` is the board in the photos' orientation (bus connector at the top), with pin 1 of each part marked.

The 2005 notes say this board "needed pin lifting, double sockets and rewiring" (`hardware/FABRICATED.md`).

## Settled from the photos

| Item | As built | Schematic |
|---|---|---|
| IC1 address latch | **SN74LS374N**, edge-triggered on TPA rising | 74LS373, transparent while TPA is high |
| IC2 boot EPROM | MBM2732A-30 in a **double socket** | 2732 |
| U1 reset chip | DS1232 (same pinout as the CM1232) | CM1232 |
| SV2 (EPROM half) | H: the window is in the upper 32K | |
| SV4 (EPROM bank) | pins 1-2: bank 7, so F000 | |
| SV5 (VMA mode) | pins 3-4: Boot/REMAP | |
| JP1 (bus EF) | row 3: the bus `-EF` line goes to EF3 | |
| JP2, JP3, JP4 | empty: the front-panel, 1861 and keyboard-cable flags go nowhere | |

On the IO card, SV1 is on 2-3, so the keyboard's 1852 drives the bus `-EF` line, and JP1 puts it on EF3.
The emulator (`software/s5emu --hw`) uses all of the above.

## The rework

### Boot flip-flop: IC8 74LS74

Three legs of IC8 are bent out of the socket, each with a red wire.
They are the 3rd, 4th and 5th pins of the row nearest the 1802, which on this footprint are **pins 10, 11 and 12**:

| Pin | Name | Schematic connection |
|---|---|---|
| 10 | PRE2 | the EPROM-window select (SV4 common) |
| 11 | CLK2 | GND |
| 12 | D2 | GND |

So the rework turns the boot flip-flop from a set-only latch into a **clocked** flip-flop.

Where the wires land, with the photo calibrated against the board (JP1, SV5 and SV4 as reference points):
- two wires go to **SV2's end column: pin 5 = VCC and pin 6 = ADDR15** (the latched A15, unused in the H setting);
- the wire that seemed to reach the EPROM socket lands **on an ADDR15 via** beside it (32 px away; EPROM pin 1 is 39 px);
- the other red wires around the SV2 cluster (one under the EPROM's notch, one loop) are slack or a second VCC run.

### The derived wiring (2026-10-07)

The wires reach only VCC and A15, and only one assignment works:

| IC8 pin | As drawn | As built (derived) |
|---|---|---|
| 10 PRE2 | EPROM-window select | **VCC**: no preset (PRE on A15 would preset it at 0000) |
| 11 CLK2 | GND | **ADDR15**: the only signal with an edge |
| 12 D2 | GND | **VCC** |
| 13 CLR2 | -RESET | -RESET (unchanged) |

So **reset clears the flip-flop, and the first rising edge of the latched A15 sets it**, ending the boot map.
This is the same scheme as YACC1's FORCE-ROM (`~/Developer/YACC1-D/docs/cards/memory.md` section 3.1).
The ROM supplies that edge: HBIOS starts `LDI F0 / PHI R0` ("Trigger Boot rom remap"); with P = 0, R0 is the
program counter, so the next fetch is F003.
It is also what the 2005 ops notes say ("First access to memory with A15 high sets the flip flop"): they describe the
reworked board, not the schematic.
The 74LS373 → 74LS374 swap belongs to the same fix: the transparent 373 follows the bus while TPA is high, so the
window decode feeding an asynchronous PRE could glitch; the 374 latches once, on TPA's rising edge, and gives a clean A15
edge to clock on.

What is inferred rather than traced: which wire goes to which pin. The logic above follows from the endpoints alone.
`software/s5emu --hw` models it as CPU revision `A-built` (the default); `--cpu-rev A` is the card as drawn.

### Reset circuit: IC5 74LS123 and U1 DS1232

- IC5 **pins 1 (1A) and 3 (1CLR)** are bent out, with red wires. As drawn, 1A = GND and 1CLR = `-RESET`: the one-shot that makes the RUN pulse after reset.
- U1 **pin 7 (/ST, the watchdog strobe)** is bent out, with a red wire toward R13. As drawn it is on TPA. Most likely this disables the watchdog, so an idle or waiting 1802 is not reset.
- On the back, a red wire runs from the U1/IC5 area to a pin of the 1802 socket, and a short one links the two rows of IC5.

These only change how the machine comes out of reset; they are off the bus path, and the emulator's reset plays them.

**Needed from Ken (lower priority):** where the IC5 and U1 wires go.
