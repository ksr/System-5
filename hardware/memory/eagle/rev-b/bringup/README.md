# Memory Rev B (reworked, the 2005 card): first bring-up from the bus driver, 2026-10-30

BUSDRV-B (JLCPCB Y56) with only this card in the 2009 backplane, CPU card out. `software/busdrv/bringup.py memory --mem-rev B-built`.
Fitted (Ken): one 62256 (IC1) and one 27256 (IC5); IC3 and IC11 (the second EPROM/RAM sockets) and one of IC4/IC15/IC10 are empty, which the rework does not need.

| Result | |
|---|---|
| Bus driver | firmware `blocks-1 io-2 2026-10-11`; takes the bus; bus power sensed |
| RAM 0000–6FFF | **good**: block map, all 8 data lines, A0–A14, quick RAM test; 4K of random data verified and read back twice with no error |
| 7000–7FFF | **nothing answers**: the rework keeps the jumper decode (block 7 open), so the RAM and the 6845 do not overlap. This answers BACKLOG question 7, and it means the emulator's `B-built` model (RAM over all of 0000–7FFF, wires from IC14 pins 3 and 6) is wrong: the wires must come off IC14's spare gates as in `../../../REVIEW.md`'s proposed rework. To confirm on the card: which IC14 pins the red wires leave from |
| EPROM 8000–FFFF (IC5) | **reads wrong on this card, but the chip is good.** On the card about 35% of bytes read wrong (repeatably, and about 0.6% flicker), unchanged by reseating. On Ken's T48 the same chip (a Microchip 27C256, ID 0x298C) reads identically three times: `2026-10-30-eprom-ic5-t48-read.bin`, md5 `45ee7276a4ec2a0c5a67592b0232b9ec`. **Cause: Rev B ties the EPROM's VPP (pin 1) to GND** (`../../../REVIEW.md`, finding 2); a 27C256 needs VPP = VCC to read reliably. Ken's 2005 chip, an Atmel AT27C256R, tolerated it; this one does not. Fix on this card: lift IC5 pin 1 and wire it to pin 28 (VCC). Rev D/E already tie VPP to VCC. The card's read is kept as `2026-10-30-eprom-ic5-read.bin` |
| EPROM contents | **an ELF/OS install ROM** (MINIMON, SETBOOT, HEXDUMP, RENAME, INSTALL, MKDIR, RMDIR, CHDIR, PATCH and more), a different build from `../private-resources/elf/firmware/elfos-install-rom/elfos.32k.rom.01` (65% of bytes the same) and matching no file in the repo: the T48 read is the only copy. 8000–EFFF hold data; F000–FFFF is blank |
| −RESET, −INT, −EF | read low: the 2009 backplane has no pull-ups, so released lines float (expected) |

The two EPROM reads (`2026-10-30-eprom-ic5-t48-read.bin` and `2026-10-30-eprom-ic5-read.bin`) are Mike Riley's ELF/OS
install ROM, so they are not in this repository: since 2026-11-15 they are in the private repository private-resources,
at `../private-resources/elf/hardware/memory/eagle/rev-b/bringup/`, beside `../private-resources/elf/firmware/elfos-install-rom/` (also moved
there).

The first run of `bringup.py` was fooled by the floating data bus (a read straight after a write saw the write where nothing answered, so 7000 and F000 looked like RAM); `probe()` now charges the bus to the opposite value before every read, and the idle-line check is a warning on a bus without pull-ups.

## 2026-10-30/31: after the VPP fix (IC5 pin 1 to pin 28)

- The EPROM reads the same as before the fix (560 of 32768 bytes differ from the first card read, about the flicker). In 8000–EFFF every byte the card reads is the T48 byte with extra 1 bits and never a missing one (28,672 of 28,672), whatever is left on the bus before the read: IC5 is outputting 1s where its cells hold 0s. So VPP was not the cause, or the fix is not making contact. F000 reads floating-bus leftovers (nothing selected there).
- The RAM, good before the rework, no longer answers in any block (writes do not stick), also after reseating IC1.
- An IDE card left in the backplane is not the cause (the data bus read FF with it in and out; it later floated again).
- Not finished, and not picked up again: MEM3-E was built on 2026-10-31 and has been the memory card in the machine since (`hardware/memory/kicad/rev-e/bringup/README.md`). At the time: Ken plans to build MEM3-E instead, if its independent review is good. Next steps if it is picked up again: 5 V at IC1 and IC5 pins 28–14 against the bus connector; IC5 pin 1 = pin 28 and clear of its socket contact (GND on Rev B); bent pins or bridges on IC12/IC14/the muxes near the rework.
- `bringup.py --rom-base 8000` was taken as decimal (1F40), which offset the comparison; `--rom-base` and `--video-base` are now hex.
