# MEM3-E independent review, 2026-10-31

Two fresh reviewers, one for the circuit and one for the board and build, worked from the design files, the ordered zip and the datasheets. They read `REVIEW-2026-10-30.md` only afterwards, to say where they disagree.

**Verdict: build it. No blockers from either.**
- **Board:** the ordered zip equals the board: fresh gerbers and drill are identical except for the dates; `check_order_zip` passes with 4 layers, 88/88 nets and 455/455 holes.
- **Netlist:** MATCH 88/88.
- **Planes:** whole, with every GND and VCC pad on its plane.
- **Bus connector:** identical in position, rotation and pinout to memory Rev B, BUSDRV-B and 6845 Rev B.
- **Footprints:** every footprint and the jumper labels agree with the nets.
- **Circuit:** every pin is correct; the decode selects at most one chip per block; the Rev B chip-select and VPP faults are gone.
- **Simulation:** `bringup.py --sim memory` gives 6 pass, 1 warn (blank EPROM), 0 fail.

## Changes to the 2026-10-30 review

- **IC14: keep the 74LS32, and R2/R4 at 470 Ω.** This replaces P1. With a 74HCT32, a floating -VMA no longer reads as high. With the CPU card out and before the bus driver takes the bus, the chips could be selected and drive the data bus while -MRD floats. The LS32 load on the CD4042B (0.4 mA against 0.51 mA guaranteed) is within spec, if with little margin.
  - If a 74HCT32 is ever fitted: power up only with a bus master, use 1k for R2/R4, and mark it on the board (the silkscreen says 74LS32). The bus Rev D's suggested -VMA pull-up (N7) would remove the floating input.
- **Speed:** with the CPU card's CDP1802BCE the limit is about 3.5 MHz, not 2.2 MHz; the CDP1802A limit is about 2.5 MHz. The 2.2 MHz figure used the A part's address set-up, or a longer 4042 set-up time, or both. Either way, 1.76 MHz has a wide margin.
- **27C256, not the NMOS 27256: the main reason is the high level.** The 1802 needs 3.5 V for a high on the unbuffered data bus, and the 2009 backplane has no pull-ups. An NMOS 27256 guarantees only 2.4 V.
- **C8 is 2.07 mm from the top edge,** 3.8 mm closer than on the built Rev B. Use a 5 mm-diameter 10 µF cap, 16 V or more, and check it clears the card guide.

## New build cautions

1. **Bypass caps against the sockets:** 12 of the 14 0.1 µF caps have their silkscreen outline 0.1 mm from the IC outline. Use slim MLCCs (3 mm thick or less) and standard sockets; fit the sockets before the caps.
2. **No ZIF sockets:** a ZIF socket will not fit the EPROM positions, and an extractor cannot grip from the cap end. Use machined-pin or dual-wipe sockets and lever the chips out evenly.
3. **Every notch faces right,** toward the jumpers and LEDs, with pin 1 the top-right pad. The pin-1 pads are not square, so check each socket before soldering.
4. **RN3's "1" sits beside the LO block's GND label:** don't take it for pin 1 of the header.
5. **RN1–RN4 must be 10-pin bussed networks** (9 resistors, e.g. Bourns 4610X-101-472LF). A 9-pin network would shift every pin by one.
6. **Trim leads to 2 mm or less underneath:** the cards are 1" apart. Seat U$1 flat and square to the edge.

The parts list, bare-board checks and bring-up order in `REVIEW-2026-10-30.md` stand, except IC14 and R2/R4 as above. Extra items to buy: the type of the 30-pin right-angle header, C8's voltage and diameter, and up to 16 shunts.
