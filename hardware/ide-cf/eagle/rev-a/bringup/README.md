# IDE/CF Rev A: first bring-up from the bus driver, 2026-10-30

BUSDRV-B in the 2009 backplane with this card (and the reworked Memory Rev B, which does not answer I/O cycles); CPU card out. `software/busdrv/bringup.py cf`: **7 PASS, 1 WARN** (−INT floats: the 2009 backplane has no pull-ups).

- **Jumpers confirmed:** register select on port 2 (SV1), data on port 3 (SV2), as derived from the BIOS.
- The data path, the register-select latch (DA0–DA2), Mike Riley's BIOS set-up (device control 02, SET FEATURES 01 for 8-bit mode) and IDENTIFY all work.
- **The CF card** (in a CF-to-IDE adapter): model `16MB CLS`, serial `3A38C04AA1330012`, firmware 3.00, 31,360 sectors (16.1 MB), CHS 490/2/32: the 16 MB card from the 2005 website photo.
- **Sector 0 is the ELF/OS boot loader**, identical to the one in `../private-resources/elf/firmware/elfos-install-rom/` and Mike Riley's `setboot`: the card still holds Ken's ELF/OS installation.

Full report: `2026-10-30-bringup-report.md`.
