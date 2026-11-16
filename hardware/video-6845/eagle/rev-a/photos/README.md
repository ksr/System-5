# 6845 Rev A photos

Rev A was ordered as a bare card (no solder mask or silkscreen) in Feb 2005, and built: it was Ken's working 6845 card in early 2005.
Its chips were later moved to the Rev B card (`../../rev-b/photos/`), which is the working card now.

## `2026-10-09-built-*.jpg`: the original working Rev A card

The card in the March 2005 website photo (`docs/website-2005/images/P3070210.JPG`, "REV. A of the card"), now with its sockets empty.
- **Same board:** the 2005 photo shows the same chips that are now in the Rev B card, down to the date codes: 74AS175 "501X1" (IC9), SN74LS163AN "8939" (V1), 74LS166 "IKMI 8828" (IC11), 74LS04 "8149B" (IC6), 7416 "FFS5896" (IC14), plus a DM74LS90N at IC7, as Rev A is drawn.
- **Rev A layout:** IC10, IC13 and IC14 upright in the middle row; the SV3/SV4 jumper row above them (three jumpers fitted); SV2 by the crystal; no DB9 footprint. Same bare PCB as the blank below ("P54518" on the solder side).

Rework, matched to Ken's 2005 issues log (`docs/website-older/1802old/System-5/V6845/index.html`):

| On the board | Issues log |
|---|---|
| The 2732 (IC12) in a double socket: a white socket on the black one | "A11 Pin 21 of EPROM should be tied low not high - Fixed via double socket" |
| DB9 bolted to the edge beside the RCA jack, wired by hand on the solder side (red wire-wrap wire) | "Add DB9 pin connector to PCB" (Rev B added the footprint) |
| IC10 (74LS174) and IC13 (74LS86) in piggyback sockets with pins bent out sideways; a red wire from the top socket at IC10 to the 2732's pin 22 (A9), another from IC13 down towards the IDT7134 | probably "Add lower case character set": Rev B drives A9 with character bit 6 from a second 74LS174. Not traced pin by pin. The A9 wire is not in the March 2005 photo, so it is later |

## `2026-10-08-blank-*.jpg`: an unpopulated Rev A board

It matches Rev A's 2005 silkscreen gerber (`../fab/v6845-a.plc`), not Rev B's:
- IC10, IC13 and IC14 stand upright side by side in the middle row (in Rev B, IC10 and IC13 lie sideways and IC14 sits on its own by the RCA jack);
- the two 1×4 jumper headers SV3/SV4 sit above them (Rev B has none);
- the second chip in the top row (IC7, the 74LS90) is a 14-pin footprint (Rev B: 16-pin 74LS174).

"P54518" on the solder side is probably the fab's job or panel number.
All four photos came through chat at 1500×2000; full-resolution originals can replace them.
