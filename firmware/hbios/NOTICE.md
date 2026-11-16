# HBIOS: Mike Riley's BIOS with Ken Rother's System-5 code

HBIOS is Mike Riley's 2004–05 BIOS for ELF/OS with Ken Rother's System-5 section added: the 6845 video and
keyboard drivers (2005), and the monitor commands and disk fixes of v1.0.5 and v1.0.6 (2026; each version's README).

- **Mike Riley's:** the BIOS source in every `orig_bios/` folder here (`bios.asm`, its listings and copies) and on
  the old website (`docs/website-2005/System-5/BIOS/`), and,
  through it, every HBIOS ROM built from it: the `.rom`, `.hex` and `.img` files in this folder, the emulator's ROMs
  in `software/s5emu/roms/` and the CPU card's EPROM read in `hardware/cpu/eagle/rev-a/rom/`. Ken's few changes
  inside his source are marked `KSR`.
- **Ken Rother's:** the `sec1.asm` files, `index.htm`, the Makefiles and the build and check scripts
  (MIT: `LICENSES/MIT.txt` at the top of the repository).

Mike Riley's source carries this notice, which stays with it and with every ROM built from it:

    *******************************************************************
    *** This software is copyright 2005 by Michael H Riley          ***
    *** You have permission to use, modify, copy, and distribute    ***
    *** this software so long as this copyright notice is retained. ***
    *** This software may not be used in commercial applications    ***
    *** without express written permission from the author.         ***
    *******************************************************************

The copies in `old/ksrbios/` and `v0.9/` carry the same notice with the year 2004.
