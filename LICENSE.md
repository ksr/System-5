# Licence

System-5 is Ken Rother's work, 2004–2026, except for the parts listed under "Not Ken's" below.

| What | Licence |
|---|---|
| Hardware designs (schematics, board layouts, gerbers and order files), documents (the manual, the READMEs and notes, the website), photos and renders | [CC BY 4.0](LICENSES/CC-BY-4.0.txt) |
| Software: source code, scripts and the programs built from them, wherever they are (`software/`, `embedded/`, `firmware/`, `tools/`, and code beside a board, such as the PIC keyboard firmware) | [MIT](LICENSES/MIT.txt) |

To credit a design or document under CC BY 4.0: "System-5 by Ken Rother, cottageworker.com", with a link to this
repository.

## Not Ken's

- **HBIOS** contains Mike Riley's 2004–05 BIOS for ELF/OS: the `orig_bios/` folders in `firmware/hbios/`, the copies
  on the old website (`docs/website-2005/System-5/BIOS/`) and every HBIOS ROM built from them (in `firmware/hbios/`,
  `software/s5emu/roms/` and `hardware/cpu/eagle/rev-a/rom/`). They
  come under his notice, in [`firmware/hbios/NOTICE.md`](firmware/hbios/NOTICE.md): they may be used, changed, copied
  and distributed as long as the notice is kept, **but not used in commercial applications without his written
  permission**. Ken's own HBIOS code (the `sec1.asm` files and the build scripts) is MIT.
- **The 2513 character fonts** in `firmware/char-rom-fonts/` (`2513u.bin`, `2513l.bin` and the images made from them,
  among them `firmware/video-g-chargen/`) are images of the Signetics 2513 character-generator ROM, found on the net
  in 2005. The C tools beside them are Ken's (MIT).
- **Eagle libraries** in `hardware/libraries/eagle/`: `k1.lbr` is Ken's; the others came with Eagle or were
  downloaded, and keep their makers' terms.
- **KiCad library parts** (symbols, footprints and 3D models from KiCad's own libraries, as used in the KiCad designs)
  keep KiCad's library licence: CC BY-SA 4.0, with its exception for designs that use them.

Mike Riley's ELF/OS (the 0.2.6 kernel and programs, Elf/OS v5, disktool and rcasm), the datasheets and the other
third-party material System-5 was built with are not in this repository: they carry no permission to publish them.
