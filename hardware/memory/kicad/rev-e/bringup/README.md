# MEM3-E bring-up from the bus driver (2026-10-31)

Built card, on the 2009 backplane with the 6845 Rev B card (no CPU card). Jumpers: RAM 0000-6FFF (IC1, mux IC2, SV2),
EPROM 8000-EFFF (IC5, mux IC13, SV4); 7000 open for the 6845, F000 open for the CPU card's boot EPROM. IC3, IC11, IC4,
IC15, RN2, RN3 not fitted (not needed for this map).

- **IC2 (74HCT151) was bad:** blocks 2000 and 4000 never answered (inputs D2/D4 dead). Swapped; all of 0000-6FFF answers.
- **RAM: PASS.** Data lines, address lines A0-A14, and the full test of 0000-6FFF (`s5busdrv.memtest`: address in
  address, 8 walking ones, fills 55 AA 00 FF; 35 min). A first full run had 3 single-bit glitches at different
  addresses and bits (6FFA, 31AC); the re-run was clean.
- **EPROM:** the old Rev B card's IC5 EPROM read with about 430 bytes showing extra 1 bits (weak bits); replaced by a
  Toshiba TC57256D-20 programmed on the T48 with `../private-resources/elf/hardware/memory/eagle/rev-b/bringup/2026-10-30-eprom-ic5-t48-read.bin`
  (md5 45ee7276a4ec2a0c5a67592b0232b9ec; verified and read back identical). VPP 21 V: see CLAUDE.md, EPROM programmer.
  **In IC5: PASS** - all of 8000-EFFF reads back identical to the image (`bringup.py memory --rom ...`). So the extra-1
  bits were the old chip, not the card.
- The block-map step reports RAM at 7000: that is the 6845's video RAM (the video card was in). It calls A000, C000
  and E000 empty because their sample bytes are FF; M5 reads them correctly.

**MEM3-E: RAM and EPROM both good.**
