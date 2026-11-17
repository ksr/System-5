# System-5 operator's guide: the boot monitor and Elf/OS

How to use System-5 from the keyboard: the HBIOS boot monitor; Elf/OS 5.1.1, Mike Riley's later operating system,
which the machine has run since 2026-11-15, with every program on its card; and ELF/OS 0.2.6, the system of 2004–05
that it ran before (sections 6 to 8). Written 2026-11-01 for 0.2.6; the monitor's added commands and Elf/OS v5 added 2026-11-16.

Sources:

- **The monitor:** the HBIOS source (`firmware/hbios/`: Mike Riley's BIOS 1.0.4, and `sec1.asm` for the commands
  added in v1.0.5).
- **Elf/OS 5.1.1** (sections 3 to 5): Mike Riley's v5 release and its help pages (github.com/rileym65/ElfosV5; a copy
  is in `../private-resources/elf/reference/mike-riley/elfos-v5/`), and runs in the emulator (`software/s5emu`, HBIOS
  1.0.6, kernel 5.1.1 build 229, the System-5 card image) on 2026-11-16.
- **ELF/OS 0.2.6** (sections 6 to 8): Mike Riley's notes of 3/1/2005 (in
  `../private-resources/elf/reference/mike-riley/microelf-picoelf/website/`), the programs themselves
  (`../private-resources/elf/reference/mike-riley/elfos-programs/`), and runs in the emulator (HBIOS 1.0.4, kernel
  0.2.6 build 135, the install ROM with BASIC) on 2026-11-01.

Everything marked *(checked)* was run in the emulator on the date above; the rest is from Mike's notes and help pages
or the program's own messages.

## 1. The machine as the software sees it

| Address | What |
|---|---|
| 0000–6FFF | RAM (MEM3-E, IC1). Elf/OS v5 keeps its stack and heap at the top, from 6E00 up; programs load at 2000 |
| 7000–77FF | 6845 video RAM: the screen, 64 × 16 characters |
| 7800–7FFF | 6845 registers |
| 8000–EFFF | MEM3-E's EPROM, IC5. Since 2026-11-15: Mike Riley's Elf/OS v5 installer. **`@8000` now wipes the card at once** (section 5). Before that: the ELF/OS 0.2.6 install ROM (section 6), which is kept |
| F000–FFFF | HBIOS, the CPU card's boot EPROM (FF00 = boot from the CF card) |

The console is the 6845 screen and the PS/2 keyboard (IO card: `INP 1`, key waiting on `-EF`). There is no serial
port, so programs that need one (XMODEM, below) do not work. Ports 2 and 3 are the IDE/CF card.

## 2. Power-on and the boot monitor

At power-on HBIOS sets up the 6845, clears the screen and prints its prompt:

```
test>
```

HBIOS does **not** boot from the disk by itself; you start Elf/OS from this prompt (`B`, below).

**The monitor is Mike Riley's**, part of his BIOS. It reads one line. The first character is the command; an address
follows straight after it, in hex, with no space. Use capitals for hex digits.

| Command | What it does | Example |
|---|---|---|
| `?addr` | show 128 bytes from addr, 16 to a line *(checked)* | `?F000` |
| `!addr bb bb …` | store bytes from addr on (spaces between the bytes) | `!0100 F8 41 30 00` |
| `=src dst count` | copy count bytes from src to dst (three hex numbers, spaces between) | `=8000 0100 0080` |
| `@addr` | run the code at addr, with R0 as the program counter and X = 0 | `@0100` |

**System-5 adds five commands to it** (HBIOS v1.0.5 and later; the machine runs v1.0.6). They are in the System-5
part of the ROM: Mike's monitor passes any command it does not know to them. They work in lower case too.

| Command | What it does | Example |
|---|---|---|
| `H` | list the monitor's commands *(checked)* | `H` |
| `B` | **boot Elf/OS from the CF card**, as `@FF00` does *(checked)* | `B` |
| `D start:end` | disassemble from start to end, 14 lines to a screen: at `-- more --` any key goes on, and Esc, `Q` or Ctrl-C stops. The range can also be written `D F000-F020` or `D F000 F020` | `D F000:F020` |
| `D start` | disassemble one screenful from start | `D F000` |
| `Q1` / `Q0` | turn the 1802's Q output on / off (any number but 0 is on) | `Q1` |

Any other line is ignored and the prompt comes back, with no message.

Useful addresses:

| Line | Effect |
|---|---|
| `@FF00` | boot Elf/OS from the CF card, as `B` *(checked)* |
| `@8000` | **wipes the card**: the Elf/OS v5 installer in MEM3-E's EPROM formats the card at once, with no question (section 5). With the 0.2.6 install ROM fitted instead, it is that ROM's installer and its menu (section 6) |
| `@F1C0` | the IO panel demo (v1.0.5 and later): the toggles to the LEDs, INPUT to Q, until Reset. For the IO panel card, which is not built yet |
| `?7000` | the first lines of the screen memory |
| `!7000 48 45 4C 4C 4F` | writes HELLO straight into the top left of the screen |

`@` jumps without checking: run only code you know is there.

## 3. Elf/OS 5.1.1: starting and using it

Elf/OS v5 is Mike Riley's later operating system: kernel 5.1.1, build 229, of 8/27/2024. System-5 has run it since
2026-11-15. It needs HBIOS 1.0.6: on 1.0.4 or 1.0.5 a v5 card hangs before its first message. The kernel on the card
carries a 6-byte change for System-5, which keeps its stack and heap below the video RAM.

At the monitor type `B` (or `@FF00`) *(checked)*:

```
test>B
Starting Elf/OS ...
V5.1.1

Ready
:
```

`Ready` and the `:` prompt come back after every command. Type a command and its arguments, then Enter.

- **Lower case.** Commands and file names are in lower case on the card, and case matters: `DIR` gives
  `File not found.` *(checked)*.
- **Where programs are found:** in `/bin`, from any directory *(checked)*. A program somewhere else runs by its path
  (`/test/prog`), or by its name from its own directory.
- **A program must be marked executable to run.** `copy` does not carry the mark, so a copied program gives
  `File not found.` until `chmod +x` is used on it *(checked)*. `dir -l` shows the mark as `*`.
- **Paths:** a path starting with `/` is from the root; otherwise from the current directory. `chdir` changes it:
  there is no `cd`. A directory's name needs no `/` after it.
- **No message means it worked:** most commands print nothing when they succeed.
- **The card** holds `bin/` (the programs), `os/` (the kernel, `/os/kernel`) and `base.lbr`, the library the
  programs were unpacked from *(checked)*. Space is counted in allocation units (AUs) of 8 sectors (4K): 3906 on
  the 16 MB card, 3821 of them free on a fresh one *(checked)*.
- **Memory:** a program loads at 2000 and may use memory up to 6E00, about 19.5K; the kernel's heap is above
  that *(checked: `himem` gives 6E00)*.
- **The date:** there is no clock. The date starts at 8/27/2024 at every boot and new files get it;
  `date mm/dd/yyyy` sets it until the next boot *(checked)*.
- **The screen** is 64 × 16 and scrolls, so a long listing runs off the top: `dir` in `/bin` just fits, and
  `sysinfo` loses its first lines. `cls` clears it.
- **A v5 card and a 0.2.6 card are different formats** (section 6).

## 4. Elf/OS 5.1.1: the programs on the card

Every program in `/bin` on System-5's card: Mike Riley's base tools as the card image has them, and `minimon` and
`basic`, added to the machine's card on 2026-11-15. *(checked)* means run in the emulator on 2026-11-16; "usage line"
means only that the program was run with nothing after its name and answered with its usage.

| Command | What it does |
|---|---|
| `asm` | Asm/02-lite v0.1, the 1802 assembler: `asm [options] srcname` *(usage line checked)* |
| `basic` | Rc/Basic Level 2 (section 9) *(checked)* |
| `btcheck` | a check that prints `Passed` *(checked)*. It has no help page; by its name, a check of the card's boot code |
| `chdir` | show the current directory, or change it: `chdir /bin` *(checked)* |
| `chmod` | set or clear a file's flags: `+x` / `-x` executable, `+w` / `-w` the W flag, `+h` / `-h` hidden, `+a` / `-a` altered *(checked: `+x`, `+w`)* |
| `cls` | clear the screen: System-5's own program (below) *(checked)* |
| `copy` | copy a file: `copy src dest`. `dest` can be a directory, or `.` for the current one; `-o` overwrites without asking, `-n` does not truncate the destination *(checked: file to file)* |
| `crc` | a file's CRC-16: `crc /bin/cls` gives `CFDC` *(checked)* |
| `create` | make a file of a given size: `create [-c] [-f char] [-o] [-s size] [-z] name` (`-s 4k`, `-s 100b`; `-c` in one piece, `-z` filled) |
| `date` | show the system date, or set it: `date 11/16/2026` *(checked)* |
| `del` | delete a file *(checked)* |
| `dir` | list a directory: `dir [options] [path]`. `-l` the long form (flags, date, size), `-h` hidden files too, `-s` / `-n` / `-d` sorted by size / name / date, `-r` in reverse *(checked: plain and `-l`)* |
| `do` | run a script: a text file of command lines, run one after another until one fails *(usage line checked)* |
| `dump` | save memory to a plain file: it asks for the start address, the end address and the file name *(checked)* |
| `echo` | type a message; for scripts *(checked)* |
| `echoon`, `echooff` | set and clear the kernel's echo flag. No effect seen here *(checked)*: HBIOS shows each key itself |
| `editor` | the line editor (below) *(checked)* |
| `exec` | run code already in memory: `exec addr`. **Always give the address** (section 11) |
| `free` | the card's total and free AUs *(checked)* |
| `fsck` | check the file system (below) *(checked)* |
| `halt` | stop the system (not run) |
| `heap` | show the kernel's heap; `heap +size` takes a permanent block, `heap -address` gives one back (`$` before a hex number) *(checked: `heap` alone)* |
| `help` | help pages. They are in a library that is not on the card, so `help dir` gives `File not found` *(checked)* |
| `hexdump` | show a file in hex *(checked)* |
| `hexedit` | a hex editor for a file: it shows 256 bytes at a time, with the place in the file as its prompt; `Q` leaves *(checked: open and `Q`)* |
| `himem` | show the top of program memory, or set it: `himem addr` *(checked: shows 6E00)* |
| `ifmod` | `ifmod filename command` *(usage line checked)*; no help page |
| `lbr` | the library tool: `lbr l name` lists a library, `lbr e name` unpacks all of it, `lbr a name file …` adds files. The name is given without `.lbr` *(checked: `lbr l base`)* |
| `link` | Link/02-lite v0.1, the linker for what `asm` writes. **Always give a file name** (section 11) |
| `load` | load a program without running it, and show where: `load /bin/cls` gives `2000 0032` *(checked)* |
| `minimon` | the memory monitor (below) *(checked)* |
| `mkdir` | make a directory *(checked)* |
| `more` | show a text file (it has no help page; a two-line file showed as with `type`) *(checked)* |
| `move` | move a file into another directory: `move file directory` |
| `nvr` | a monitor for battery-backed memory. System-5 has none: `No NVR installed` *(checked)* |
| `owns` | `owns lumpnumber` *(usage line checked)*; no help page |
| `prompt` | type a message and wait for Enter; for scripts *(checked)* |
| `reboot` | start Elf/OS again (not run) |
| `rename` | rename a file in its own directory: `rename old new` *(checked)* |
| `retval` | show the value the last program ended with *(checked: `00`)* |
| `rmdir` | remove a directory, which must be empty *(checked)* |
| `save` | save memory as a program: it asks for the start, end and execution addresses and the file name, and marks the file executable *(checked)* |
| `scandir` | `scandir dirname` *(usage line checked)*; no help page |
| `stat` | a file's details: its first lump, size, flags, date, directory entry and chain of lumps *(checked)* |
| `sysinfo` | a report on the system in 21 lines (below) *(checked)* |
| `touch` | set a file's A flag and give it the system date *(checked: it runs)* |
| `trunc` | set a file's size in bytes, smaller or larger: `trunc file size` *(usage line checked)* |
| `type` | show a text file *(checked)* |
| `ver` | the kernel's version (`5.1.1 Build 229 8/27/2024`), or a program's date and build: `ver /bin/dir` *(checked)* |
| `visual02` | Mike Riley's full-screen 1802 debugger. **It cannot run on System-5** (section 11) |
| `xr`, `xs` | XMODEM receive and send. They need a serial port, which System-5 does not have |

### Files and directories

```
: mkdir /test
: copy /bin/echo /test/e3
: chdir /test
: chmod +x e3
: e3 hello
hello
: dir -l
e3                 *  A  08/27/2024 12:00:14  75
```

*(checked)*. In `dir -l` the columns are the name, the flags, the date and time, and the size in bytes. The flags: `*`
executable, `W` the W flag (`bin/` and `os/` have it), `A` altered. Mike's help page calls `+w` write protection, but
`del` still deleted a file with W set *(checked)*: do not count on it.

`del /test/e3`, then `rmdir /test`, take them away again. `rename` cannot move a file to another directory; `move`
is for that.

### editor — the line editor

`editor name` edits a text file, making it if it is not there (`New file`). It is not the `EDIT` of 0.2.6 (section
8): the help page in Mike's release describes that older editor, and this one has none. What follows was found by
trying it *(checked)*.

The prompt is the current line's number and `>`. **A line typed at the prompt is text**: it goes in at that line,
and the lines from there on move down. A command starts with a backslash:

| Command | Effect |
|---|---|
| `\L` | list the whole text, with line numbers |
| `\T` / `\B` | go to the top / to the bottom (the line after the last) |
| `\F text` | find: shows the first line that holds the text |
| `\C` | copy to the copy buffer. With nothing after it, at line 1 of four, it took all four lines |
| `\P` | paste the copy buffer at the current line (`??? Copy buffer empty` if nothing was copied) |
| `\R` | show a ruler of column numbers |
| `\S` | save the file |
| `\Q` | back to Elf/OS. Save with `\S` first: whether `\Q` alone saves was not tried |
| `\A` | back to Elf/OS **without saving**: the file is not written |

Anything else gives `??? Unknown command`. `\D`, `\I`, `\E` and `\Z` are commands too (`\D` alone answers
`???Argument error`); what they take was not worked out.

```
: editor /test/t.txt
New file
    1>first line
    2>second line
    3>\S
    3>\Q
```

### asm, link — assembler and linker

`asm [options] srcname` announces itself as Asm/02-lite v0.1, and `link` as Link/02-lite v0.1. Mike Riley's documents
for his assemblers and linker are in the release (`asm.doc`, `asm02.doc`, `link02.doc`). Neither has been used on
System-5 beyond its opening lines.

### minimon — memory monitor

The same commands as the boot monitor's first four, with a `>` prompt, plus a way back *(checked)*:

| Command | Effect |
|---|---|
| `?addr` | show 128 bytes from addr |
| `!addr bb bb …` | store bytes |
| `=src dst len` | copy len bytes |
| `@addr` | run at addr |
| `/` | back to Elf/OS |

Built from Mike's v5 source and put on the machine's card on 2026-11-15; it loads at 6000.

### load, save, dump — programs and memory

- `load name` puts a program in memory at its load address without running it.
- `save` and `dump` both announce themselves as `File dump utility` and ask, one line at a time, for
  `Start address :`, `End address   :`, then (`save` only) `Exec address  :`, and `Filename      :` *(checked)*.
  `save` writes a program file, with its 6-byte header and the executable mark; `dump` writes the bytes alone.
  Saving 2000 to 2010 gave 23 bytes with `save` and 17 with `dump`.

### fsck — checking the card

```
: fsck
FSCK/5 0.1p
by Michael H. Riley
Checking boot sector:
  Check value: Good
Sector 0:
  Filesystem: LAT-16
  V5MdPtr   : Good
Scanning filesystem:
  base.lbr
Scanning LAT:
..
```

*(checked)*. A sound card ends there, with no `Orphaned lump:` lines.

**Look at the first line.** `FSCK/5 0.1p` is the corrected program, on the card image since 2026-11-13.
`FSCK/5 v0.1` is Mike Riley's own, on a card written from an older image: on a card this small it lists false orphans
without end (Reset stops it), and **it must never be run with `-f`**, which would write zeros over good data. His
is still inside `base.lbr`, so unpacking that library again (`lbr e /base` in `/bin`) brings it back.

### sysinfo

Prints 21 lines, so the first eight scroll away; it waits at its `RAM` line while it tests the memory. What is left on
the screen *(checked)*:

```
f_freemem   : 30720 30K
Heap        : $6E01
High Mem    : $6E00
bios        : 1.0.4
  IDE       : Yes
  Floppy    : No
  BB Serial : Yes
  UART      : No
  RTC       : No
  NVR       : No
  $F800     : No
  $F000     : No
  sd_rd/wr  : No
```

- `bios : 1.0.4` is the version of Mike Riley's BIOS inside HBIOS. HBIOS 1.0.5 and 1.0.6 hold the same BIOS, so
  they say 1.0.4 too.
- `30K` counts the 2K of video RAM after the 28K of main RAM.
- `BB Serial : Yes` is not true of System-5. The lines from `IDE` down are what the BIOS says it supports, a fixed
  answer, and not tests of the hardware.

Every line is explained in `software/s5emu/CODESPACE.md`.

### cls — System-5's own

Mike Riley's `cls` sends the codes that clear an ANSI terminal, which HBIOS's screen showed as `[H[2J`. The card has
a `cls` written for System-5 instead (`software/elfos-v5/cls/`): it writes spaces over the screen, leaving `Ready` and
the `:` prompt on the bottom lines *(checked)*. `ver /bin/cls` says `System-5 6845 screen`.

## 5. The Elf/OS v5 card

**The card is made on the Mac**, from the image `elfos-5.1.1-system5-16mb.img.gz` in
`../private-resources/elf/reference/mike-riley/elfos-v5/system5/` (16,000,000 bytes, 31,250 sectors, for the 16 MB
card): unpack it, write it to the card raw with `dd`, read the card back and compare. `TRY-ON-REAL-MACHINE.md`, in
the folder above the image, has the steps, one at a time. The image has the corrected `fsck` and System-5's `cls`.

**Getting a file onto the card** also goes through the Mac, because there is no serial port for `xr`: read the card
into an image, change the image with `software/elfos-v5/v5card.py` (`ls` lists it, `add -x` adds a program,
`put` replaces a file), write it back and compare. `minimon` and `basic` got onto the machine's card that way.

**The installer in the EPROM: do not type `@8000` with a card you want to keep.** Since 2026-11-15 MEM3-E's IC5 holds
Mike Riley's v5 installer, with the System-5 change to its kernel. `@8000` formats the card **at once, with no
question**. It then sets up the boot code, the allocation table, `/os` and `/bin`, installs five programs (`dir`,
`chdir`, `lbr`, `xr`, `chmod`) and offers to boot; about a minute at 500 kHz. What it leaves is kernel 5.0.2 with
those five programs only: Mike's way to the rest is XMODEM, which System-5 cannot use, so the full set comes from the
Mac's image. It installed on the real machine on 2026-11-15, byte for byte as in the emulator; booting a card it made
is tried in the emulator with HBIOS 1.0.6 and not yet on the machine.

**Tools that must not touch a v5 card:** `mkelfos.py`, the old `disktool`, and the 0.2.6 install ROM (section 6).
They are for 0.2.6 cards, which are a different format.

## 6. ELF/OS 0.2.6: the installer (`@8000` with the 0.2.6 install ROM)

ELF/OS 0.2.6 is the system System-5 was built for in 2004–05, and what the machine ran until 2026-11-15. Sections 6
to 8 describe it as it was then. To go back to it, write its card image to the CF card on the Mac (`~/s5-cf.img`,
made by `mkelfos.py`) and fit its install ROM in MEM3-E's IC5 if the installer or `INSTALL` is wanted. On a Mac the
emulator still starts with 0.2.6. **A 0.2.6 card and a v5 card are different formats:** `mkelfos.py`, the old
`disktool` and this installer must not be used on a v5 card.

The install ROM begins with a branch to its installer. From the monitor, `@8000` shows *(checked)*:

```
Elf/Os Installation
1> Run hard drive init tool
2> Run filesystem gen tool
3> Run sys tool
4> Install binaries
5> Boot Elf/OS
   Option ?
```

| Option | What it does |
|---|---|
| 1 | **Do not use it: it cannot leave a usable card** (found 2026-11-04). It erases everything on the drive and counts sectors as it goes, but it misses the end of the card. Once the count passes the card's size (31,360 on the 16 MB card, after 40 minutes or more at 500 kHz) nothing more is being written, and it will not stop by itself: the count just climbs and wraps. It stores no size, so option 2 can only make a 0-sector filesystem afterwards. Turn the machine off and build the card on the Mac. |
| 2 | Makes an empty ELF/OS filesystem: **erases every file**. It takes the size from sector 0, so the card must already hold one, as a card made on the Mac does. Prints the sector count, the allocation unit (AU) size, the number of AUs and where the master directory is. |
| 3 | Copies the kernel to the drive (sectors 1–16). Harmless to files: use it to put a new kernel on. Ends with `System copied.` |
| 4 | Installs the utilities: asks about each program in the ROM, one at a time (as `INSTALL` does). |
| 5 | Boots ELF/OS *(checked)*. |

A new card: build it on the Mac with `mkelfos.py` (`BACKLOG.md`, "Build the CF card on the Mac"), then boot with `@FF00`.

## 7. Using ELF/OS 0.2.6

When ELF/OS is waiting for a command it shows

```
Elf/OS Ready
$
```

Type a command and its arguments, then Enter. Commands are program files on the disk: typing `DIR` runs the file
`DIR`. Type commands and file names in **capitals** (the files are stored in capitals).

- **Where programs are found:** with the kernel on System-5's disks (0.2.6 build 135) a program runs from the current
  directory. Disks made by `mkelfos.py` have every utility in both `/` and `/BIN/`; if you change directory, use the
  path (`/DIR`) or put the program there too.
- **File names:** up to 19 characters, anything but `/`. There are no extensions; you may use them as part of the name.
- **Directories:** a path ends with `/` when it names a directory (`DIR BIN/`, `CHDIR BIN/`), except with `MKDIR`, which
  takes the name with no trailing `/`. A path starting with `/` is from the root; otherwise from the current directory.
  A whole path is at most 80 characters.
- **Programs** are files with a 6-byte header: load address, size, start address. `SAVE` and the assembler write it.
- **Disk space** is counted in allocation units (AUs) of 8 sectors (4K).

## 8. ELF/OS 0.2.6 command reference

The **ROM** column gives the load address of the copy in the install ROM (what `INSTALL` puts on the disk). It
matters when a program has to stay clear of memory you are working on: for example, `SAVE` and `DUMP` load at 6000, so
they can save a program sitting at 2000.

| Command | ROM | What it does |
|---|---|---|
| `ASM` | 6000 | 1802 assembler |
| `BASIC` | 2000 | Rc/Basic Level 1 (section 9) |
| `CD` | – | change or show the current directory (disk only; the same as `CHDIR`) |
| `CHDIR` | 2000 | change or show the current directory |
| `COPY` | 2000 | copy a file |
| `DEL` | 2000 | delete a file |
| `DIR` | 2000 | list a directory |
| `DUMP` | 6000 | save memory to a file |
| `EDIT` | 2000 | line editor |
| `EXEC` | 7000 | run a program already in memory (**see the warning**) |
| `FREE` | 2000 | disk space |
| `HEXDUMP` | 2000 | show a file in hex |
| `INSTALL` | 2000 | install programs from the install ROM |
| `LBR` | – | file library tool (disk only) |
| `LOAD` | 7C00 | load a program without running it |
| `MINIMON` | 5E00 | small memory monitor |
| `MKDIR` | 2000 | make a directory |
| `PATCH` | 2000 | patch a file from a control file |
| `RENAME` | 2000 | rename a file |
| `RMDIR` | 2000 | remove an empty directory |
| `SAVE` | 6000 | save memory as a program file |
| `SEDIT` | – | sector editor (disk only) |
| `SETBOOT` | 3000 | write the boot loader to sector 0 |
| `STAT` | 2000 | show a file's size |
| `TDUMP` | – | save memory to a file, loading at 2000 (disk only) |
| `TYPE` | 2000 | show a text file |
| `VER` | 2000 | show the ELF/OS version, or a file's date |

### ASM — assembler
`ASM name` assembles the text file `name.ASM` and writes the program `name`, with its execution header. It lists the
source as it goes; errors show in the listing. Mike's notes walk through a short program: `EDIT BAUD.ASM`, type it in,
`ASM BAUD`, then run `BAUD`.

### BASIC
Starts Rc/Basic Level 1 (section 9). `BYE` returns to ELF/OS.

### CHDIR, CD — current directory
- `CHDIR` alone shows the current directory (`/` at the root) *(checked with `CD`)*.
- `CHDIR path/` changes to it; `CHDIR /` goes back to the root.
- `CD` (on the disk, not in the ROM) does the same; a bad path gives `Invalid Directory`.

### COPY — copy a file
`COPY source destination`. This is also how to move a file to another directory (copy, then `DEL` the original):
`RENAME` cannot move between directories.

### DEL — delete a file
`DEL path`.

### DIR — list a directory
`DIR` lists the current directory, `DIR path/` another one. Directories show with a trailing `/`.
*Known fault:* HBIOS loses the first character after the screen's 64-column wrap, so `DIR` drops every fifth name
*(checked)*. The files are there; see them with `DIR` on a smaller directory, `STAT name`, or by running them.

### DUMP, TDUMP — save memory to a file
Both ask, one at a time: `Start address :`, `End address   :`, `Exec address  :` and `Filename      :`
*(checked for TDUMP)*. `DUMP` loads at 6000; `TDUMP` (disk only) is the same tool loading at 2000, for saving memory
that `DUMP` itself would overwrite.

### EDIT — line editor
`EDIT name` edits a text file, creating it if it does not exist (`New file`). The prompt is `>`.
**Always give a name:** `EDIT` with no name hangs the machine (kernel fault; power off and on).

| Command | Effect |
|---|---|
| `T` / `B` | go to the top / bottom of the text |
| `U`, `,nU` | up one line / n lines |
| `D`, `,nD` | down one line / n lines |
| `nG` | make line n the current line |
| `P`, `nP`, `,nP`, `n,mP` | print the current line / line n / n lines from here / m lines from line n |
| `Itext` | insert one line of text here (`nItext`: at line n) |
| `I` | insert lines until Ctrl-C (`nI`: at line n) |
| `K`, `nK`, `,nK`, `n,mK` | delete the current line / line n / n lines from here / m lines from line n |
| `S` | save to the file named when EDIT started |
| `Q` | quit to ELF/OS (save first: `Q` does not save) |

### EXEC — run a program in memory
`EXEC addr` starts the code at addr.
**Warning (System-5):** the install ROM's EXEC loads itself at 7000, which is the screen memory here. Do not use it
until it is fixed (`BACKLOG.md`); use `MINIMON`'s `@addr` instead.

### FREE — disk space
Shows `Total AUs:` and `Free AUs :` (1 AU = 8 sectors = 4K).

### HEXDUMP — show a file in hex
`HEXDUMP name`. A program file starts with its 6-byte header (load address, size, start address).

### INSTALL — install programs from the ROM
Reads the table at 8000 in the install ROM and asks about each program in turn (`Install DIR ?` …): `Y` installs it
into the current directory, `N` skips it *(checked)*. The install ROM with BASIC (burned 2026-11-01,
`../private-resources/elf/firmware/elfos-install-rom/with-basic/`) lists 23 programs, the last being `BASIC`.

### LBR — file libraries (disk only)
`LBR A|D|E|L library [file]`: add a file to a library, delete one from it, extract one, or list the library *(usage
message checked)*. A library is one file holding several.

### LOAD — load without running
`LOAD name` puts the program in memory at its load address and shows its start and execution addresses. Then use
`MINIMON` to look at it or `@` to run it.

### MINIMON — memory monitor
The same commands as the boot monitor, with a `>` prompt, plus a way back:

| Command | Effect |
|---|---|
| `?addr` | show memory |
| `!addr bb bb …` | store bytes |
| `=src dst len` | copy len bytes |
| `@addr` | run at addr |
| `/` | back to ELF/OS |

### MKDIR, RMDIR — directories
`MKDIR name` (no trailing `/`); `RMDIR path` removes a directory, which must be empty.

### PATCH — patch a program
`PATCH controlfile`. The control file is text: line 1 is the file to patch; then lines of a 4-digit hex address followed
by 2-digit hex bytes. If line 2 is `R` (relative mode), the addresses are memory addresses (PATCH reads the program's
header to find the file offsets); otherwise they are offsets in the file.

### RENAME — rename a file
`RENAME old new`, within one directory.

### SAVE — save memory as a program
Asks for the start, end and execution addresses and the file name, and writes them as a program file with its header.
Loads at 6000.

### SEDIT — sector editor (disk only)
Works directly on the drive's sectors. **Writing a sector can destroy the filesystem.** The prompt is `>`. Tested on an
emulator disk *(checked)*:

| Command | Effect |
|---|---|
| `Rnnnn` | read sector nnnn (hex) into the buffer |
| `Annnn` | read the first sector of allocation unit nnnn (AU × 8) |
| `N` / `P` | next / previous sector |
| `D` | show the current sector number |
| `L` / `H` | show the low / high half of the buffer (0000–00FF / 0100–01FF) in hex and text |
| `Eaddr bb bb …` | change bytes in the buffer (addr 0000–01FF) |
| `W` | write the buffer back to the current sector |
| `C` | shows a 4-digit value (FFFF on the sectors tried); its meaning is not confirmed |
| `Q` | back to ELF/OS |

### SETBOOT — boot loader
Writes the boot loader to sector 0 (`Boot Loader installed on sector 0`). Needed only if sector 0 has been damaged.

### STAT — file size
`STAT name` prints the file's size in bytes *(checked: `STAT DIR` gives 500)*.

### TYPE — show a text file
`TYPE name`.

### VER — versions
`VER` alone shows the kernel: `0.2.6 Build 135 9/13/2005` *(checked)*. `VER name` shows a program's date
(`VER DIR` gives `3/4/2005`).

### Not a command: BUILD
The file `BUILD` in `/BIN` on disks made by `mkelfos.py` is a script for the Mac's disk tool (lines like `copy [dir] dir`),
not an 1802 program. **Do not run it.**

## 9. Rc/Basic

Mike Riley's BASIC for ELF/OS. **Level 2 is on the Elf/OS v5 card as `basic`** (added 2026-11-15; 6.4K). Level 1 is on
the 0.2.6 install ROM as `BASIC`. Both read their keywords from a table; the lists below were read from the programs
themselves. Keywords are typed in capitals.

Numbers are integers, in decimal (`PEEK(61440)` reads F000). The prompt is `>`. Lines with a number are stored;
lines without one run at once.

**Level 1** *(checked: `PRINT`, `LET`, `IF … THEN GOTO`, `RUN`, `LIST`, `NEW`, `SAVE`, `LOAD`, `BYE`, `FRE()`, `PEEK()`)*

| Kind | Keywords |
|---|---|
| Statements | `PRINT` `LET` `GOTO` `IF … THEN` `END` `GOSUB` `RETURN` `REM` `INPUT` `POKE` `OUT` `PLOT` |
| Commands | `RUN` `LIST` `NEW` `BYE` (back to ELF/OS) `SAVE "name"` `LOAD "name"` (the name in quotes) |
| Functions | `PEEK(a)` `FRE()` (free bytes: 19599 with nothing loaded) `RND(n)` `INP(p)` `FLG(n)` `USR(a)` |
| Operators | `+ - * /`, comparisons, `AND` `OR` |

Level 1 has **no FOR/NEXT**: loop with `IF … THEN GOTO`:

```
10 LET I=1
20 PRINT I*I
30 LET I=I+1
40 IF I<4 THEN GOTO 20
RUN
```

prints 1, 4, 9 *(checked)*. An error prints `ERROR:n in line m` (a statement Level 1 does not know is `ERROR:2`).

**Level 2** adds `FOR` `TO` `STEP` `NEXT`, `ON`, `DATA` `READ` `RESTORE`, `DIM`, `RANDOM`, `CLEAR`, and strings: `LEN(`
`ASC(` `VAL(` `STR$(` `CHR$(` `LEFT$(` `RIGHT$(` `MID$(`, `VARPTR(`. It runs on the machine under Elf/OS v5 (since
2026-11-15), and it starts with `RC/Basic L2` and the `>` prompt *(checked under v5: `PRINT`, `FOR … TO … NEXT`, a
string variable and `LEN(`, `FRE()`, which gives 16436 with a three-line program, `SAVE "T1"`, `BYE`)*:

```
10 FOR I=1 TO 3
20 PRINT I*I
30 NEXT I
RUN
```

prints 1, 4, 9.

## 10. Other programs in the reference folder

Mike Riley's other ELF/OS programs are in `../private-resources/elf/reference/mike-riley/elfos-programs/`. They are not on the 0.2.6
install ROM or on `mkelfos.py` disks. Of them only Rc/Basic Level 2 has been run on System-5 (on the v5 card, as
`basic`); copy the others to the CF card to try them.

| Program | What it is |
|---|---|
| `rcbasicl2` | Rc/Basic Level 2 (section 9) |
| `forth/forth` | Forth (with `ext.forth`, extra words in source form) |
| `rclisp` | Lisp |
| `tbc` | a Tiny BASIC compiler (`tbcsource/tbc/tbc.doc`) |
| `life` | Conway's Life: type a starting pattern (space or `.` for empty, anything else for a cell), then a blank line |
| `chip8` | a CHIP-8 interpreter |
| `zrun3` | a Z-machine interpreter (text adventures) |
| `lbr` | the library tool, as `/BIN/LBR` |
| `xr`, `xs` | XMODEM receive and send: they need a serial port, which System-5 does not have |

## 11. Known problems

Both systems:

| Problem | Workaround |
|---|---|
| A line longer than 64 characters loses what comes after the wrap (HBIOS's screen routine). Under 0.2.6 `DIR` drops every fifth name; under v5 `ver` on a program loses the end of its line | the files are still there |
| HBIOS probes ports 2/3 for a UART and clock, which are the IDE registers here | none needed so far |
| No serial port | XMODEM (`xr`, `xs`) cannot be used; move files on the CF card instead |

Elf/OS 5.1.1:

| Problem | Workaround |
|---|---|
| **`@8000` wipes the card at once**, with the v5 installer in MEM3-E's EPROM | do not type it with a card you want to keep (section 5) |
| A v5 card hangs at boot on HBIOS 1.0.4 or 1.0.5 | HBIOS 1.0.6 |
| `link` with no file name does not come back: it prints `Lowest Address : FFFF`, `Highest Address: 0000` and stops there (emulator, 2026-11-16) | always give a file name; Reset, then `B` |
| `exec` with no address prints `Usage: exec address`, then puts stray characters on the screen and does not come back (emulator, 2026-11-16) | always give the address; Reset, then `B` |
| A copied program gives `File not found.` | `chmod +x` on the copy |
| `help` finds no pages: its library is not on the card | this guide; Mike's pages are in `hlp.lbr` in his release |
| Mike Riley's own `fsck` (`FSCK/5 v0.1`) lists false orphans without end on a small card, and `-f` would damage it | the card has the corrected one (`FSCK/5 0.1p`); never run his with `-f` |
| `visual02` cannot run: it loads at 6000–704A, across the kernel's heap and into the video RAM, and draws for an 80 × 24 terminal | `minimon`, or the boot monitor's `D` |
| `sysinfo` says `BB Serial : Yes` | it is what the BIOS claims, not a test: there is no serial port |
| Commands in capitals give `File not found.` | type them in lower case |

ELF/OS 0.2.6:

| Problem | Workaround |
|---|---|
| `EDIT` with no file name hangs | always give a name |
| `EXEC` from the install ROM loads at 7000 = screen memory | use `MINIMON` `@addr` |
| The installer's option 1 misses the end of the card and never stops | do not use it; build the card on the Mac |

For programming (the BIOS calls, the kernel API, the memory and I/O maps) see the [programmer's guide](programmers-guide.md).
