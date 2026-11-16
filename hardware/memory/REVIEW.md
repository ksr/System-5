# Memory card (mem3): design review

Reviewed 2026-10-05 from the Fusion export of Rev B (`eagle/rev-b/fusion-export/mem3-b.sch`).
That export is proven identical to the April 2005 order gerbers (`../FABRICATED.md`).
The XML board of Rev C mill (`eagle/rev-c-mill/mem3-c.brd`, 2014) was used for comparison.

## How the card works

| Function | Parts | Notes |
|---|---|---|
| Low address A0–A7 | IC7, IC8 (4050 buffers) | Buffered bus A0–7 goes straight to every memory chip. |
| High address A8–A15 | IC6, IC9 (4042 latches) | Fed from the buffered A0–7; CLK = TPA, POL = VCC. |
| Bank select | IC14A, IC14B (74LS32) | Lower 32K = `-VMA OR A15`; upper 32K = `-VMA OR /A15`. |
| 4K block select | IC2, IC15 (lower), IC4, IC13 (upper): 74LS151 | One mux per chip. A12–A14 select one of 8 jumpers; G = bank select. |
| Read / write | IC8 (4050) | Buffered -MRD drives every `!OE`. Buffered -MRW drives the RAM `!WE`. |
| Chips | IC1, IC11: 62256 RAM; IC3, IC5: 27256 EPROM | IC1/IC3 sit in the lower 32K, IC11/IC5 in the upper 32K. |

How this lines up with the 1802 bus:
- The 1802 multiplexes its address. The high byte is on A0–7 while TPA is high; the low byte follows.
- The 4042 with POL high is transparent while its clock is high and latches on the falling edge. Clocking it from TPA therefore latches the high byte at the end of TPA. **Correct.**
- The 4050 delay on the latch's data inputs helps: the high byte is still present when TPA falls.

## Finding 1 (critical): a deselected bank still enables its chips

This is confirmed by Ken's rework and by the Rev C redesign.

**The fault.** Each chip's `!CE` comes from its 74LS151's `Y` output (pin 5). The bank-select signal drives the mux strobe `G` (pin 7).
On a 74LS151, **G high forces Y LOW** (and W high). So whenever a bank is *not* selected, its muxes pull their chips' `!CE` low and *enable* them.

What that does with 32K RAM in the lower half and 32K ROM in the upper half, as built:

| Cycle | Chips enabled |
|---|---|
| Any access to 0x0000–0x7FFF | The RAM, as intended, **and** the ROM, because the ROM's bank strobe is high. Both drive the data bus on every read. |
| Any access to 0x8000–0xFFFF | The ROM **and** the RAM. Writes into the ROM area also land in RAM. |
| Reset, while the CPU card holds -VMA high to boot from its own EPROM | **Every chip on this card.** They fight the CPU card's boot EPROM. |

The card cannot work as drawn. Rev A uses the same mux scheme (Rev A ops notes), so it has the same fault.

**The rework on the working board.** Ken's board has the `!CE` pins of the RAM and the ROM lifted and wired to the 7432. That is the right fix: `!CE = Y OR bank-select`, built from the two spare 74LS32 gates.
The 7432 has exactly two spare gates, so the rework covers exactly two chips. That fits a board with one RAM and one ROM fitted.

**As built: the Rev B board, from Ken's photos of 2026-10-05.**
- The underside silkscreen reads "PcbFabEx FXA5474", so this is the board from order FXA5474ED07, made by PCB Fab Express.
- Fitted: RAM in IC1 (RAM LO, 0x0000–0x7FFF), EPROM in IC5 (EPROM HI, 0x8000–0xFFFF), and muxes IC2 and IC13. IC3, IC11, IC4, IC15 and IC10 (LED driver) are empty; only the power LED is fitted.
- Two red wires run on the underside from the 74LS32 (IC14) to **pin 20 (`!CE`) of IC1** and to **pin 20 of IC5**. Both landing points were matched to the board's pad coordinates.
- No wire goes to the 74LS151 outputs. So the two chip selects come from the 74LS32 bank selects, not from the muxes, and the 4K jumpers no longer affect them.
- Most likely wiring: the spare gates, inputs lifted off ground, buffer IC14 pin 3 (lower bank) and pin 6 (upper bank) onto the two `!CE` pins. That gives RAM `!CE` = `-VMA OR A15` and ROM `!CE` = `-VMA OR /A15`, which is a complete fix for a 32K RAM + 32K ROM card.
- Not confirmed: exactly which IC14 pins are lifted and joined. That needs a close-up photo.

The rework below instead keeps the per-4K jumpers working. It assumes the RAM is IC1 (lower) and the ROM is IC5 (upper):

| Gate | Inputs | Output to | Rework |
|---|---|---|---|
| IC14C | pin 9 ← IC2 pin 5 (Y); pin 10 ← IC14 pin 3 (lower-bank select) | pin 8 → IC1 pin 20 (`!CE`) | Lift IC1 pin 20. Free IC14 pins 9/10, which Rev B grounds. |
| IC14D | pin 12 ← IC13 pin 5 (Y); pin 13 ← IC14 pin 6 (upper-bank select) | pin 11 → IC5 pin 20 (`!CE`) | Lift IC5 pin 20. Free IC14 pins 12/13, which Rev B grounds. |

Rev B also feeds the chip's activity LED (IC10) from the raw `Y`. After this rework, that LED still lights when the *other* bank is accessed.

**Rev C has the fix designed in, from 2005.** The 2005 Rev C schematic (Fusion export, 2026-10-05) and the 2014 Rev C mill board are wired the same way:
- A second 74LS32 (IC12) is added.
- All four 74151 strobes are tied active (G to GND).
- Every `!CE` = `Y OR bank-select`.

Rev C still drives the two RAM LEDs from the raw `Y`; the EPROM LEDs were moved to the gated `!CE`. So the RAM LEDs light when that RAM's bank is *not* selected. This is cosmetic.

A fix that needs no extra gates: take `!CE` from the 74151's `W` output (pin 6) instead of `Y`.
- W is forced HIGH when the strobe is off.
- When selected, W is the inverse of the jumper.
- The jumper sense inverts: jumper fitted (D grounded) now means that 4K block is *disabled*.

## Finding 2 (check): EPROM VPP is tied to ground

Pin 1 (VPP) of both 27256 sockets is on GND, in Rev B, Rev C (2005) and Rev C mill.
The Atmel AT27C256R in the photo specifies VPP at 5 V in read mode. NMOS 27256s also expect VPP = VCC.
Grounded VPP is out of spec. It often works with CMOS parts, but the safe choice is to tie pin 1 to VCC in a new revision.

## Finding 3 (minor): activity LEDs are driven by a 74LS00 output going high

The LEDs run from the NAND output through 470 Ω to ground. A 74LS output is specified to source only 0.4 mA when high, so the LEDs will be dim.
Sinking the current instead (LED from VCC through the resistor into the gate output) gives full brightness.

## Checked and fine

- **TPA latching:** correct; see above.
- **Read and write strobes:**
  - RAM `!WE` from -MRW. The 1802's write pulse comes late in the cycle, after the address and chip select have settled.
  - `!OE` from -MRD. The 1802 holds MRD high during writes and during INP (I/O-to-memory), so the memory never drives the bus while the CPU or an I/O device does.
  - OUT reads memory onto the bus with MRD low, as intended.
- **Jumper headers:** each 4K column has three rows: RAM D, GND, EPROM D (SV2 + SV3, SV1 + SV4). A jumper can ground either the RAM or the EPROM input for a block, never both. The board coordinates confirm the column order matches (D7 with D7 … D0 with D0).
- **Pull-ups:** 10-pin SIL networks, pin 1 to VCC, pins 3–10 to the mux D inputs (pin 2 unused).
- **Unused inputs:** the 4050's E/F inputs and the 74LS32's C/D inputs are tied to ground in Rev B (that is what the rework frees).
- **CMOS speed:** the 4042 adds at most a few hundred ns from TPA to A8–15. An 1802 machine cycle is 8 clocks, about 4.5 µs at 1.79 MHz, so there is ample margin for 200 ns memories.
- **Data bus:** the memories drive the bus directly, with no buffer. That is fine for a handful of cards on the 1802's bus.
