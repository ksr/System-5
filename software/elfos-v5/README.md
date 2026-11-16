# System-5 programs for Elf/OS v5

Programs of our own for Mike Riley's Elf/OS v5 on System-5, and a tool that puts them on a v5 card image. They
are on the `elfos-v5` branch only, with the rest of the v5 try-out. Mike Riley's own programs and the card image
are third-party and stay in the private repository: `../private-resources/elf/reference/mike-riley/elfos-v5/`.

| Here | What |
|---|---|
| `cls/cls.asm` | `cls` for System-5: clears the 6845 card's screen |
| `cls/cls`, `cls/cls.lst` | the Elf/OS program built from it (56 bytes) and its listing |
| `build.py` | assembles the programs with `tools/asm1802.py`; `--check` says whether the built ones match their source |
| `v5card.py` | lists a v5 card image, copies a file off it, replaces a file on it, and adds one (`add`, 2026-11-15) |

## cls

Mike Riley's `cls` types `ESC[H` and `ESC[2J`, the codes that home the cursor and clear the screen of an ANSI
terminal. HBIOS's screen is not an ANSI terminal, so on System-5 it showed `[H[2J` and cleared nothing.

This `cls` writes spaces over the screen itself: the first 1024 bytes of the 6845 card's video RAM, 7000-73FF,
which are the 16 lines of 64 characters. HBIOS types on the bottom line and scrolls the rest up, so there is no
"home": the cursor stays at the start of the bottom line, and after `cls` the screen holds only `Ready` and the
`:` prompt at the bottom. It takes 0.8 seconds at 2 MHz and 3.2 at 500 kHz, most of it Elf/OS loading the program.

- It is for the 6845 card with HBIOS 1.0.4, 1.0.5 or 1.0.6. It writes to 7000-73FF without asking what is there.
- `ver /bin/cls` shows `11/14/2026 12:0:0 Build: 1  System-5 6845 screen`. Mike Riley's says `Written by Michael
  H. Riley`.
- Tried in the s5emu emulator on both ROMs (2026-11-14), and by Ken in the v5 Codespace the same day (HBIOS 1.0.5):
  it works. On the real machine, with HBIOS 1.0.6 (2026-11-15): it works (Ken).

## Building and putting it on the card

    python3 software/elfos-v5/build.py

    python3 software/elfos-v5/v5card.py put ../private-resources/elf/reference/mike-riley/elfos-v5/system5/elfos-5.1.1-system5-16mb.img.gz /bin/cls software/elfos-v5/cls/cls

The image in `private-resources` has had this `cls` since 2026-11-14. `v5card.py put` only replaces a file that is
on the card already, in the lumps it already has: it changed two sectors of the image, 48 (the length in `/bin`'s
directory entry, 59 to 56) and 304 (the program). Mike Riley's `cls` is still on the card inside `base.lbr`.

    python3 software/elfos-v5/v5card.py ls IMAGE /bin

lists the programs on a card image with their sizes and lumps.

    python3 software/elfos-v5/v5card.py add -x IMAGE /bin/minimon minimon.bin

adds a new file (2026-11-15), as v5 itself does when it makes one (watched in s5emu: `copy /bin/ver /bin/vertest`):
the lowest free lumps, chained in the allocation table, and the first free entry of the directory; nothing else on
the card changes. `-x` marks it executable (flags 12h, as the programs `lbr` unpacks; 10h without). The directory
must exist and have a free entry. It put MINIMON and Rc/Basic Level 2 on the real 16 MB card on 2026-11-15: three
places changed for MINIMON (sector 17, `/bin`'s directory sector, its lump), Disktool5's `fsck` found the card sound,
and both run on the machine.

Tests: `test_elfos_v5_cls_is_the_system5_one` and `test_elfos_v5_boots_from_disk` in
`software/s5emu/tests/test_machine.py` (both skipped without the private image).

## Which of Mike Riley's programs send ANSI codes

A scan of every program on the v5 card and in his release (2026-11-14) found three; no other program and not
the kernel holds an escape code.

| Program | Codes | On System-5 |
|---|---|---|
| `cls` | `ESC[H` (cursor home), `ESC[2J` (clear the screen) | replaced by the `cls` here |
| `visual02` | `ESC[2J`, `ESC[J` (clear to the end of the screen), `ESC[row;colH` (put the cursor at a place) | cannot run: it loads at 6000-704A, across the kernel's heap and into the video RAM, and draws for an 80 x 24 screen. Making it work at other addresses is in `BACKLOG.md` (Ken, 2026-11-14) |
| `ur` (in his release, not on the card) | `ESC[H`, `ESC[2J` | not tried |

The other way to deal with them is in the ROM: HBIOS could act on the codes as they are typed. HBIOS 1.0.5 has
room for a small routine (207 free bytes at FC31-FCFF). It could clear the screen and swallow the other codes, but
not place the cursor, because HBIOS types on the bottom line only; and it would need a new EPROM. Not done: it is
in `BACKLOG.md` (Ken, 2026-11-14), so that programs need not be rewritten as `cls` was.
