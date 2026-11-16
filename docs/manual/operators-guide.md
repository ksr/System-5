# System-5 operator's guide: the boot monitor and ELF/OS

How to use System-5 from the keyboard: the HBIOS boot monitor, the ELF/OS installer, and every ELF/OS command and
program. Written 2026-11-01.

Sources: the HBIOS 1.0.4 source (`firmware/hbios/v1.0.4/orig_bios/bios.asm`), Mike Riley's ELF/OS 0.2.6 notes (3/1/2005, in
`../private-resources/elf/reference/mike-riley/microelf-picoelf/website/`), the programs themselves (`../private-resources/elf/reference/mike-riley/elfos-programs/`), and
runs in the emulator (`software/s5emu`, HBIOS 1.0.4, kernel 0.2.6 build 135, the install ROM with BASIC). Everything
marked *(checked)* was run in the emulator on 2026-11-01; the rest is from Mike's notes or the program's own messages.

## 1. The machine as the software sees it

| Address | What |
|---|---|
| 0000–6FFF | RAM (MEM3-E, IC1) |
| 7000–77FF | 6845 video RAM: the screen, 64 × 16 characters |
| 7800–7FFF | 6845 registers |
| 8000–EFFF | the ELF/OS install ROM (MEM3-E, IC5): the installer and the utilities, plus BASIC |
| F000–FFFF | HBIOS, the CPU card's boot EPROM (FF00 = boot from the CF card) |

The console is the 6845 screen and the PS/2 keyboard (IO card: `INP 1`, key waiting on `-EF`). There is no serial
port, so programs that need one (XMODEM, below) do not work. Ports 2 and 3 are the IDE/CF card.

## 2. Power-on and the boot monitor

At power-on HBIOS sets up the 6845, clears the screen and prints its prompt:

```
test>
```

HBIOS does **not** boot from the disk by itself; you start ELF/OS from this prompt (`@FF00`, below).

The monitor reads one line. The first character is the command; an address follows straight after it, in hex, with
no space. Use capitals for hex digits. Any other line is ignored and the prompt comes back.

| Command | What it does | Example |
|---|---|---|
| `?addr` | show 128 bytes from addr, 16 to a line *(checked)* | `?F000` |
| `!addr bb bb …` | store bytes from addr on (spaces between the bytes) | `!0100 F8 41 30 00` |
| `=src dst count` | copy count bytes from src to dst (three hex numbers, spaces between) | `=8000 0100 0080` |
| `@addr` | run the code at addr, with R0 as the program counter and X = 0 | `@0100` |

Useful addresses:

| Line | Effect |
|---|---|
| `@FF00` | **boot ELF/OS from the CF card** *(checked)*: prints `Starting...`, then `Elf/OS Ready` |
| `@8000` | **the ELF/OS installer** in the install ROM (section 3) *(checked)* |
| `?7000` | the first lines of the screen memory |
| `!7000 48 45 4C 4C 4F` | writes HELLO straight into the top left of the screen |

`@` jumps without checking: run only code you know is there.

## 3. The ELF/OS installer (`@8000`)

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

## 4. Using ELF/OS

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

## 5. Command reference

The **ROM** column gives the load address of the copy in the install ROM (what `INSTALL` puts on the disk). It
matters when a program has to stay clear of memory you are working on: for example, `SAVE` and `DUMP` load at 6000, so
they can save a program sitting at 2000.

| Command | ROM | What it does |
|---|---|---|
| `ASM` | 6000 | 1802 assembler |
| `BASIC` | 2000 | Rc/Basic Level 1 (section 6) |
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
Starts Rc/Basic Level 1 (section 6). `BYE` returns to ELF/OS.

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

## 6. Rc/Basic

Mike Riley's BASIC for ELF/OS. Level 1 is on the install ROM as `BASIC`; Level 2 is larger (6.4K) and not on the ROM
(it can be copied to the CF card: `BACKLOG.md`). Both read their keywords from a table; the lists below were read
from the programs themselves.

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
`ASC(` `VAL(` `STR$(` `CHR$(` `LEFT$(` `RIGHT$(` `MID$(`, `VARPTR(`. Not yet run on System-5.

## 7. Other programs in the reference folder

Mike Riley's other ELF/OS programs are in `../private-resources/elf/reference/mike-riley/elfos-programs/`. They are not on the install ROM or
on `mkelfos.py` disks, and none has been run on System-5 yet; copy them to the CF card to try them.

| Program | What it is |
|---|---|
| `rcbasicl2` | Rc/Basic Level 2 (section 6) |
| `forth/forth` | Forth (with `ext.forth`, extra words in source form) |
| `rclisp` | Lisp |
| `tbc` | a Tiny BASIC compiler (`tbcsource/tbc/tbc.doc`) |
| `life` | Conway's Life: type a starting pattern (space or `.` for empty, anything else for a cell), then a blank line |
| `chip8` | a CHIP-8 interpreter |
| `zrun3` | a Z-machine interpreter (text adventures) |
| `lbr` | the library tool, as `/BIN/LBR` |
| `xr`, `xs` | XMODEM receive and send: they need a serial port, which System-5 does not have |

## 8. Known problems

| Problem | Workaround |
|---|---|
| `DIR` drops every fifth name (HBIOS loses the first character after a 64-column wrap) | the files are still there |
| `EDIT` with no file name hangs | always give a name |
| `EXEC` from the install ROM loads at 7000 = screen memory | use `MINIMON` `@addr` |
| The installer's option 1 misses the end of the card and never stops | do not use it; build the card on the Mac |
| HBIOS probes ports 2/3 for a UART and clock, which are the IDE registers here | none needed so far |
| No serial port | XMODEM (`xr`, `xs`) cannot be used; move files on the CF card instead |

For programming (the BIOS calls, the kernel API, the memory and I/O maps) see the [programmer's guide](programmers-guide.md).
