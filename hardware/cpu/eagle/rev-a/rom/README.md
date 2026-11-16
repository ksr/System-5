# The CPU card's EPROM (2732), read 2026-10-30

**Since 2026-11-15 the card runs HBIOS v1.0.6**, on a Fujitsu MBM2732A (`firmware/hbios/v1.0.6/README.md`); v1.0.5
ran for a few hours that day before it, on another MBM2732A. The v1.0.5 and v1.0.4 chips are kept as spares; a
v1.0.4 chip read on the T48 that day still matched the md5 below.

Read on Ken's XGecu T48 with `minipro -p "2732A@DIP24" -r` (minipro on the Mac; T48 firmware 00.1.03, which minipro calls out of date, reads fine). Two reads, identical. 4,096 bytes, md5 `7ba760ce8382f964c038d2859e8ae431`: `2026-10-30-cpu-eprom-2732.bin`.

**It is HBIOS v1.0.4, byte for byte** the image the emulator boots, `software/s5emu/roms/hbios-1.0.4.rom` (built by `software/s5emu/tools/mkrom.py`: Mike Riley's BIOS 1.0.4 plus Ken's HBIOS v0.9 section, `firmware/hbios/`). It runs at F000 (first instruction `F8 F0`).

HBIOS contains Mike Riley's BIOS, so this read comes under his 2005 notice: free to use, change, copy and distribute
with the notice kept, not for commercial use without his written permission (`firmware/hbios/NOTICE.md`).
