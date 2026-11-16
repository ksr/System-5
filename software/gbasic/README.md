# GBASIC 1.0

An integer BASIC for System-5, written for the VIDEO-G graphics card (2026-11-01, in 1802 assembly). It runs
under Mike Riley's ELF/OS (0.2.6 build 135) and HBIOS. It has the usual statements of a full BASIC (FOR/NEXT, GOSUB,
ON, IF/THEN/ELSE, DATA/READ, INPUT, arrays), program editing (LIST, RENUM, DELETE, CONT), plain-text SAVE and LOAD on
the ELF/OS disk, and graphics: points, lines, boxes, circles and ellipses, filled or not, three pens, two pages.

- **Without VIDEO-G** (the 6845 card of today) everything but the graphics works; graphics commands say `?No graphics`.
- **VIDEO-G is not built yet**: GBASIC was written and tested in the emulator (`software/s5emu --video g`) with the
  VIDEO-G build of HBIOS (`firmware/hbios/video-g`).
- Size: **12,473 bytes** (the file is 12,479 with its ELF/OS header). With GBASIC loaded at 2000h, **6,210 bytes**
  are left for the program and its arrays (`FRE(0)` at the start).
- Speed (the emulated 1802 at 1.76 MHz): **3.5 to 5 times Rc/Basic Level 2** on loops; a filled circle of
  radius 100 in 0.66 s, ERASE in 0.15 s (table below).

Contents: [Starting](#starting) - [Typing and editing](#typing-and-editing) - [Numbers and variables](#numbers-and-variables)
\- [Expressions](#expressions) - [Statements](#statements) - [Graphics](#graphics) - [Files](#files) -
[Errors](#errors) - [Machine code](#machine-code) - [Putting GBASIC on a CF card](#putting-gbasic-on-a-cf-card) -
[Building and testing](#building-and-testing) - [Inside](#inside) - [Limits and known gaps](#limits-and-known-gaps)

## Starting

At the ELF/OS prompt:

```
$ GBASIC
$ GBASIC MAZE            (loads the program MAZE and runs it)
```

```
GBASIC 1.0 for System-5
VIDEO-G graphics 512 x 200
6210 bytes free
Ready
```

The second line says what GBASIC found on port 4: `VIDEO-G graphics 512 x 200` (or `x 256` with the MONITOR jumper
set for an IBM 5151), `VIDEO-G text, no GFX board: no graphics`, or `No VIDEO-G: text only`. When it starts, GBASIC
sets the VIDEO-G control register to 00 (text on, graphics off, page 0) and clears both graphics pages. `BYE` goes
back to ELF/OS (with text on and graphics off).

## Typing and editing

A line typed **with a number** goes into the program (replacing a line with that number); a number alone deletes
that line. A line **without a number** runs at once. `Ready` means GBASIC waits for the next line.

| Key | While typing a line |
|---|---|
| Backspace, Delete | rub out the last character |
| Ctrl-C, Esc | throw the line away (`^C`) |
| Enter | done |
| F1-F12, arrows, Home, ... (VIDEO-G keyboard codes 80h and up) | ignored here (a program reads them with `INKEY`) |

Lines are up to 127 characters; GBASIC wraps its own output at the 64th column. Keywords may be typed in lower case,
and spaces are optional: `fori=1to10step2` is `FOR I=1 TO 10 STEP 2`. GBASIC stores lines **tokenized** (keywords as
one byte, numbers as two) and LIST puts the spaces back in its own way. Line numbers are 1 to 65535.

**While a program runs**, Ctrl-C or Esc stops it with `Break in nnn`; `CONT` goes on. Any other key pressed while a
program runs is kept for `INKEY` or `INPUT`. During `LIST`, a key pauses and another one goes on; Ctrl-C or Esc stops.

| Command | What it does |
|---|---|
| `RUN` / `RUN n` | clear the variables and run from the start / from line n |
| `LIST` / `LIST n` / `LIST a-b` / `LIST a-` / `LIST -b` | show the program, or a part |
| `NEW` | remove the program and every variable |
| `CLEAR` | every variable to 0, arrays removed, RESTORE, the FOR/GOSUB stack emptied |
| `DELETE a-b` / `DELETE n` | remove lines a to b / line n |
| `RENUM` / `RENUM start` / `RENUM start,step` | renumber (10,10 if not given); fixes every GOTO, GOSUB, THEN, ELSE, RESTORE, RUN and ON list |
| `CONT` | go on after `STOP`, `END` or a break (not after an error, or after the program was changed) |
| `BYE` | back to ELF/OS |

Changing the program (any numbered line, DELETE, RENUM) clears the variables, as in Microsoft BASIC.

## Numbers and variables

**Numbers** are 16-bit signed integers, -32768 to 32767. Arithmetic wraps around without an error
(`32767+1` is `-32768`, `100*400` is `-25536`); division truncates towards 0 (`-7/2` is `-3`) and `MOD` has the sign of
the left side (`-7 MOD 3` is `-1`). A number in a program may be written as 0 to 65535 (`PEEK(61440)`; values above
32767 are stored as their negative twins) or in hex as `&H` and one to four digits (`&HF000`).

**Variables** are named by a letter, or a letter and a letter or digit: `A`, `X1`, `DX`, `CY`. All are 0 at RUN.
Longer names are not allowed (`ABC=1` is a syntax error). As in Microsoft BASIC, a name must not start with a
keyword: `TO`, `IF`, `ON`, `OR` are keywords, so `TOTAL=5` is a syntax error (it starts with `TO`), and in a run of
letters a keyword is found first (`FORI=ATOB` is `FOR I=A TO B`). Up to 96 different names (simple variables and
arrays together) can be used in a program.

**Arrays** have one or two dimensions and start at index 0. `DIM A(100)` has 101 elements `A(0)`..`A(100)`;
`DIM M(3,4)` has 4 x 5. An array used without `DIM` gets `DIM A(10)` automatically. A simple variable and an array may
have the same name (`A` and `A(1)` are different). Arrays take 2 bytes an element from the free memory.

## Expressions

From the lowest precedence to the highest:

| Operators | |
|---|---|
| `OR` `XOR` | bitwise, 16 bits |
| `AND` | bitwise |
| `NOT` | bitwise complement; it applies to a whole comparison: `NOT A=B` is `NOT (A=B)` |
| `=` `<>` `<` `>` `<=` `>=` | signed comparisons: true is **-1**, false is 0 |
| `+` `-` | |
| `*` `/` `MOD` | |
| `-` `+` (sign) | |
| numbers, variables, `( )`, functions | |

Because true is -1 (all bits set), `AND`, `OR` and `NOT` work both as logic and on bits:
`IF X>0 AND X<512 THEN ...`, `B = PEEK(A) AND &H0F`.

| Function | Value |
|---|---|
| `ABS(x)` | absolute value |
| `SGN(x)` | -1, 0 or 1 |
| `RND(n)` | a random number from 0 to n-1 (n > 0); `RND(0)` gives 0 to 32767; `RND(-n)` starts the sequence again from n (returns 0) |
| `PEEK(a)` | the byte at address a (0-255) |
| `INP(p)` | reads I/O port p (1-7) |
| `USR(a)` / `USR(a, v)` | calls machine code at a with v in RF, returns RF ([Machine code](#machine-code)) |
| `FRE(0)` (or `FRE`) | free bytes: between the end of the arrays and the top of the program area |
| `POINT(x, y)` | 1 if the pixel is set on the page being drawn, 0 if not or off the screen |
| `INKEY` | the key waiting, or 0 if none (it does not wait). VIDEO-G's special keys give 128-218 (below) |

`INKEY` codes of the VIDEO-G keyboard: F1-F12 = 128-139; Home 144, Up 145, PgUp 146, Left 147, keypad 5 148,
Right 149, End 150, Down 151, PgDn 152, Ins 153, Del 154; with Shift add 64 (192-218). Ordinary keys give their ASCII
code (Enter 13, Esc 27, Backspace 8). Ctrl-C and Esc stop a running program, so `INKEY` never sees them.

## Statements

Several statements can share a line, separated by `:`. `'` starts a remark like `REM`.

| Statement | What it does |
|---|---|
| `LET v = expr` / `v = expr` | assignment (`LET` may be left out); `v` may be an array element `A(I,J)` |
| `PRINT items` / `? items` | prints expressions, `"strings"`, `TAB(n)` (to column n), `SPC(n)` (n spaces), `CHR$(n)` (the character with code n). `;` joins, `,` moves to the next 16-column zone; a newline at the end unless the list ends in `;` or `,`. Numbers print without spaces: `PRINT 1;2` gives `12` (add `" "` where wanted). |
| `INPUT v1, v2...` / `INPUT "prompt"; v1...` / `INPUT "prompt", v1...` | reads numbers (decimal with a sign, or `&H` hex) separated by commas. `? ` is printed after the prompt with `;`, not with `,`. Too few numbers: it asks again with `?? `; something else: `?Redo from start`. Ctrl-C stops the program. |
| `IF expr THEN statements [ELSE statements]` | runs the statements after `THEN` if expr is not 0, else those after `ELSE` (or the next line). `THEN 100` and `ELSE 200` are short for `GOTO`; `IF expr GOTO 100` also works. The `ELSE` belongs to the first `IF` on the line. |
| `GOTO n` | n may be an expression |
| `GOSUB n` / `RETURN` | subroutine; `RETURN` also leaves any FOR loop begun in the subroutine |
| `ON expr GOTO n1, n2, ...` / `ON expr GOSUB ...` | goes to the expr-th line of the list; outside 1..count, goes on with the next statement |
| `FOR v = a TO b [STEP s]` ... `NEXT [v[, w...]]` | loops. As in Microsoft BASIC the body runs at least once, and `NEXT` tests; a loop also ends when v would go past 32767 or -32768. `NEXT` alone closes the innermost loop; `NEXT I,J` closes two. Starting a FOR with a variable already looping drops that old loop (and the loops inside it). |
| `DIM a(n)[, b(n,m), ...]` | creates arrays (n, m up to 32767, memory allowing) |
| `DATA items` / `READ v[, v...]` / `RESTORE` / `RESTORE n` | DATA items are numbers or expressions, read in program order; RESTORE starts again from the first DATA or from line n |
| `END` | stops (CONT goes on after it) |
| `STOP` | stops with `Break in nnn` |
| `REM text` / `' text` | a remark (to the end of the line) |
| `POKE a, v` | stores the byte v at address a |
| `OUT p, v` | sends the byte v to port p (1-7) |
| `CALL a` | runs machine code at a ([Machine code](#machine-code)) |
| `WAIT n` | waits n sixtieths of a second (VIDEO-G's VSYNC: n frames; without VIDEO-G a timed loop for 1.76 MHz) |
| `RANDOMIZE n` | starts the random sequence from n (the same n gives the same numbers). GBASIC also stirs the seed while it waits for keys. |
| `CLS` | blanks the text screen; the next output starts at the left of the bottom row (HBIOS always writes on the bottom row) |
| `LOCATE row, column` | the next output goes straight to that place on the screen (row 0-24 on VIDEO-G, 0-15 on the 6845 card; column 0-63) without scrolling, until a newline (or `Ready`): `LOCATE 0,50: PRINT "SCORE";S;`. An `INPUT` after it prompts and echoes there. |
| `NEW` `RUN` `LIST` `CLEAR` `CONT` `DELETE` `RENUM` `BYE` | see [Typing and editing](#typing-and-editing); they may be used in a program too (`RUN`, `CLEAR` and `BYE` are the useful ones) |
| `SAVE` `LOAD` `FILES` `DIR` `KILL` | see [Files](#files) |
| `GRAPHICS` `TEXT` `MIX` `PAGE` `PEN` `PSET` `DOT` `ERASE` `LINE` `BOX` `CIRCLE` `ELLIPSE` | see [Graphics](#graphics) |

Examples:

```
10 REM times table
20 FOR I=1 TO 9: FOR J=1 TO 9
30 PRINT TAB(J*6);I*J;
40 NEXT J: PRINT: NEXT I

10 INPUT "HOW MANY";N: IF N<1 THEN 10
20 S=0: FOR I=1 TO N: READ X: S=S+X: NEXT
30 PRINT "SUM";S;" MEAN";S/N
40 DATA 4,8,15,16,23,42

10 ON RND(3)+1 GOSUB 100,200,300: GOTO 10
100 PRINT "ROCK": RETURN
200 PRINT "PAPER": RETURN
300 PRINT "SCISSORS": RETURN
```

## Graphics

VIDEO-G's graphics layer is **512 x 200** pixels on an NTSC monitor or TV (**512 x 256** on an IBM 5151, set by the
MONITOR jumper), one bit a pixel, **x from 0 (left) to 511, y from 0 (top) to 199** (or 255). There are two pages;
one is shown, one is drawn on (they may be the same). Text and graphics show together: their dots are combined by OR,
or by XOR (`MIX XOR`).

Every drawing command is **clipped** to the screen: any coordinates are allowed (-32768 to 32767), and only the part
on the screen is drawn. Every drawing command uses the **pen**: `PEN 1` draws (sets pixels), `PEN 0` erases (clears
them), `PEN 2` inverts them. Each pixel of a shape is touched exactly once, so drawing a shape a second time with
`PEN 2` removes it and leaves the picture under it as it was (handy for moving things).

| Command | What it does |
|---|---|
| `GRAPHICS ON` / `GRAPHICS OFF` | show the graphics layer or not (GFX-ON); the pages keep what is on them |
| `TEXT ON` / `TEXT OFF` | show the text or not (TEXT-OFF). Back at `Ready`, GBASIC turns the text on again. |
| `MIX OR` / `MIX XOR` | text and graphics combine by OR (the default) or XOR |
| `PAGE s` / `PAGE s, d` | show page s (0 or 1) and draw on page d (s if not given): `PAGE 0,1` draws on page 1 while page 0 is shown, then `PAGE 1,0` flips |
| `PEN p` | 1 = draw, 0 = erase, 2 = invert (1 at the start) |
| `PSET x, y` / `DOT x, y` | one pixel |
| `LINE x1, y1, x2, y2` | a line (Bresenham) |
| `LINE x, y` | a line from where the last PSET or LINE ended |
| `BOX x1, y1, x2, y2` / `BOX x1, y1, x2, y2, F` | a rectangle with these corners, outline or filled |
| `CIRCLE x, y, r` / `CIRCLE x, y, r, F` | a circle, outline or filled; r from 0 to 1000 |
| `ELLIPSE x, y, rx, ry` / `ELLIPSE x, y, rx, ry, F` | an ellipse with half-widths rx (across) and ry (up and down), 0 to 1000 |
| `ERASE` / `ERASE b` | clears the page being drawn on; `ERASE b` fills every byte with b instead (`ERASE 255` sets every pixel, `ERASE 170` stripes) |
| `POINT(x, y)` | (a function) 1 if the pixel is set |

The last argument of BOX, CIRCLE and ELLIPSE is the fill: the letter `F` alone, or any expression (not 0 = filled):
`CIRCLE 100,100,50,F` and `CIRCLE 100,100,50,1` are the same. Pixels are not square: on an NTSC screen the 512 x 200
dots take about the same share of a 4:3 picture across and down (64 characters at 1.5 MHz are about 81% of a line,
200 lines about 82% of the visible ones), so a pixel is about half as wide as it is high, and a `CIRCLE` looks like
a tall ellipse; `ELLIPSE x, y, 2 * r, r` looks about round (how round depends on the monitor).

Circles and ellipses fill exactly the pixels inside the ellipse of half-widths rx + 1/2, ry + 1/2, computed with
integers only (32-bit sums, no multiplications in the loop); filled shapes are drawn a whole byte (8 pixels) at a
time. A filled circle of radius 100 sets 31,714 pixels (pi x 100.5^2 = 31,731).

**Speed** (the emulated 1802 at 1.76 MHz, from `tests/test_gbasic.py`; the statement alone, without typing it):

| Statement | Time |
|---|---|
| `ERASE` (200 lines) | 0.15 s |
| `LINE 0,0,511,199` (512 pixels, diagonal) | 0.23 s |
| `LINE 0,100,511,100` (horizontal) / `LINE 100,0,100,199` (vertical) | 11 ms / 40 ms |
| `BOX 100,50,400,150` / `BOX 100,50,400,150,F` | 52 ms / 0.36 s |
| `CIRCLE 256,100,100` / `CIRCLE 256,100,100,F` | 0.86 s / 0.66 s |
| `ELLIPSE 256,100,200,80` / filled | 0.76 s / 0.63 s |
| `PSET 100,100` | 5 ms |
| `FOR I=1 TO 100: NEXT` | 0.17 s (Rc/Basic L2: 0.75 s) |
| `FOR I=1 TO 100: A=A+I*2: NEXT` | 0.58 s (Rc/Basic L2: 2.8 s) |
| `10 I=1 / 20 I=I+1 / 30 IF I<100 THEN GOTO 20`, RUN | 0.92 s (Rc/Basic L2: 3.2 s) |

Examples:

```
10 ERASE: GRAPHICS ON
20 FOR R=10 TO 90 STEP 10: CIRCLE 128,100,R: NEXT
30 FOR X=256 TO 511 STEP 16: LINE 256,199,X,0: NEXT
40 BOX 300,120,500,190,F: PEN 2: CIRCLE 400,155,30,F: PEN 1

10 REM a ball: PEN 2 draws it, and drawing it again in the same place removes it (a key stops it)
20 ERASE: GRAPHICS ON: PEN 2: X=20: Y=20: DX=3: DY=2
30 CIRCLE X,Y,8,F
40 WAIT 1: CIRCLE X,Y,8,F
50 X=X+DX: Y=Y+DY: IF X<8 OR X>503 THEN DX=-DX
60 IF Y<8 OR Y>191 THEN DY=-DY
70 IF INKEY=0 THEN 30
80 PEN 1: GRAPHICS OFF

10 REM drawing on page 1 while page 0 shows, then showing it
20 GRAPHICS ON: PAGE 0,1: ERASE
30 FOR I=0 TO 199 STEP 4: LINE 0,I,511,199-I: NEXT
40 PAGE 1
```

`tests/screens/` has pictures from the test programs (`demo-screen.png`: text and graphics as the monitor shows them;
`demo-graphics.png`: the graphics page alone; `demo-xor.png`: with `MIX XOR`; `parabola.png`).

**How it talks to VIDEO-G** (DESIGN.md sections 2-3): `OUT 7` = the pixel line, then the line's 64 bytes are at
7800-783F (bit 7 of byte 0 = x 0); `OUT 4` = the control register (GBASIC keeps a copy, because it cannot be read);
`INP 4` = the status, read once at start. Without the GFX board every graphics command (and TEXT, MIX) gives
`?No graphics`.

## Files

Programs are saved as **plain text**, exactly as LIST shows them, each line ending in CR LF. So a saved program can be
shown with ELF/OS `TYPE`, copied, edited with `EDIT`, or written on the Mac and copied to the card; `LOAD` reads any
such text, with CR, LF or CR LF line ends (lines without a line number are skipped), and tokenizes it line by line.

| Command | What it does |
|---|---|
| `SAVE "name"` | writes the program to the file (replacing it) |
| `LOAD "name"` | reads a program, replacing the one in memory; ends a running program. If the file is not there (`?File not found`), the old program stays. |
| `FILES` / `DIR` / `FILES "path/"` | lists the directory, four names a line; directories end in `/` |
| `KILL "name"` | deletes a file |

File names are as ELF/OS has them: up to 19 characters, no spaces, `/` for directories, **case matters** (the ELF/OS
programs are in capitals). `SAVE` needs 831 bytes of free memory for its buffers (above the arrays); `LOAD` keeps
531 bytes at the top of the program area for its own.

SAVE and LOAD move about **280 bytes a second** (a 60-line, 3.3K program: 12 s to save, 11 s to load). Most of the
time is ELF/OS: the 0.2.6 kernel's read and write handle each byte with several subroutine calls (about 400
instructions a byte); LOAD also tokenizes each line as if it were typed.

## Errors

An error stops the program with `?message in nnn` (no line number for a direct command) and returns to `Ready`.

| Message | Meaning |
|---|---|
| `Syntax error` | not BASIC as GBASIC knows it, or a name of three or more letters |
| `Out of memory` | no room for the line, the array, or SAVE's buffers |
| `Undefined line` | GOTO, GOSUB, THEN, RESTORE or RUN to a line that is not there |
| `RETURN without GOSUB` / `NEXT without FOR` | |
| `Division by zero` | `/` or `MOD` by 0 |
| `Bad subscript` | an index below 0 or past the DIM, or the wrong number of indexes |
| `Already DIMed` | DIM of an array that exists |
| `Out of DATA` | READ past the last DATA item |
| `Illegal value` | a value outside what the statement takes (a port not 1-7, PEN 3, a radius over 1000, LOCATE off the screen, ...) |
| `Can't continue` | CONT after an error or a change |
| `Too complex` | the expression or the FOR/GOSUB nesting is too deep (about 40 levels of parentheses; 24 FOR or 48 GOSUB levels) |
| `No graphics` | a graphics command without VIDEO-G's GFX board |
| `File error` / `File not found` | |
| `Line too long` | more than 250 bytes once tokenized |
| `Overflow` | a number over 65535 in the program text |
| `Too many variables` | more than 96 names |
| `Break` | (Ctrl-C, Esc or STOP: `Break in nnn`; CONT goes on) |

## Machine code

`USR(a, v)` and `CALL a` call machine code at address a with SCRT (`SEP R4`), as ELF/OS programs call the kernel: the
code returns with `SEP R5` with R2 (the stack, X = 2) as it found it, and must not change R3-R6 (the program counter
and SCRT). Any other register may be used (GBASIC saves its text pointer RB itself; interrupts are off).
For `USR`, RF holds v on entry and the value of the function on return.
The free RAM between the arrays and 6900h (see `FRE(0)`) is safe for small routines (POKE them in before use); so is
RAM the program never reaches. Example (RF = RF * 2):

```
10 FOR I=0 TO 6: READ B: POKE &H6800+I,B: NEXT
20 PRINT USR(&H6800,1234)
30 DATA &H8F,&HFE,&HAF,&H9F,&H7E,&HBF,&HD5: REM GLO RF SHL PLO RF GHI RF SHLC PHI RF SEP R5
```

`PEEK`, `POKE`, `INP` and `OUT` reach everything: the text screen at 7000h (row r, column c at 7000h + 64 r + c),
the graphics window at 7800h, the ports (1 = the keyboard, 4 = VIDEO-G status/control, 5/6 = the 6845, 7 = the Y
register / mouse, 2/3 = the IDE card: careful).

## Putting GBASIC on a CF card

The program is the file `software/gbasic/gbasic` (load address 2000h, 12,479 bytes with its 6-byte header). It goes in
the root directory of the ELF/OS disk as `GBASIC` (the 0.2.6 kernel runs programs from the current directory, so put
a copy in `/BIN` too if you work there).

- **A new card from the Mac:** `software/s5emu/tools/mkelfos.py card.img --mb 16`, then add GBASIC with disktool
  (built by mkelfos in the temp folder, from `../private-resources/elf/software/disktool/main.c`):
  `printf 'copy [software/gbasic/gbasic] GBASIC\nquit\n' | $TMPDIR/s5emu-disktool card.img`; write the image to the
  card (`dd`, as for any CF image). Programs can be added the same way (`copy [mygame.bas] MYGAME`): they are text.
- **An existing card:** copy the image off the card, add the file with disktool as above, and write it back; or, on
  System-5, use any way of getting bytes into memory (the bus driver, an EPROM) and ELF/OS `SAVE` from 2000h to
  50B8h with exec 2000h.
- **In the emulator:** `cd software/s5emu; python3 tools/mkelfos.py elfos.img`, add GBASIC as above, then
  `python3 -m s5emu --video g --disk elfos.img`, type `@FF00`, Enter, then `GBASIC`. The `png` command writes the
  screen as a picture; `software/gbasic/tests/harness.py` does all of it from Python.

## Building and testing

```
python3 software/gbasic/build.py
python3 software/gbasic/tests/test_gbasic.py
```

`build.py` writes `src/tables.inc` (the keyword tables, from `tools/gen_tables.py`) and assembles `src/gbasic.asm`
with `tools/asm1802.py` (the repository's Python 1802 assembler: rcasm's syntax, plus a check on every short branch,
relaxing jumps and macros). Out come `gbasic` (the ELF/OS program), `gbasic.bin`, `gbasic.sym` and `gbasic.lst` (the
listing; s5emu's `sym` reads its labels).

`tests/test_gbasic.py` (35 tests, about 2.5 minutes) boots ELF/OS on the emulated System-5 with VIDEO-G (once; the
tests start from a snapshot), starts GBASIC and types into it. It checks expressions, every statement, editing and
LIST round trips, INPUT, breaks and CONT, errors, USR/CALL, SAVE/LOAD/FILES/KILL and TYPE from ELF/OS, `GBASIC FILE`
from the command line; and the graphics **pixel for pixel** against Python models of the same integer algorithms
(lines, boxes, circles and ellipses, on and off the screen), the pens (PEN 2 twice leaves nothing), pages, the 5151
height, a machine without the GFX board, the 6845 card (text only), and the examples in this README. It prints
the timings above.

## Inside

| File | What |
|---|---|
| `src/gbasic.asm` | the top: includes the rest |
| `src/defs.inc` | registers, ports, tokens below 80h, limits, error numbers, macros (`call`, `rtn`, `push`, ...) |
| `src/main.asm` | start, `Ready`, errors, console output (putc: 64-column wrap, LOCATE, SAVE's buffer), keys, the line editor |
| `src/token.asm` | the tokenizer: keywords (by their first letter), numbers, variable names |
| `src/list.asm` | LIST (back to text, spaces put back) |
| `src/edit.asm` | the program store: insert/replace/delete lines, NEW, CLEAR, DELETE, RENUM |
| `src/exec.asm` | the statement loop and the statements |
| `src/expr.asm` | expressions (precedence climbing), variables and arrays, functions, 16- and 32-bit arithmetic |
| `src/gfx.asm` | VIDEO-G: detection, the display switches, pixels, spans, lines, boxes, ellipses |
| `src/file.asm` | SAVE, LOAD, FILES, KILL through the ELF/OS kernel |
| `src/bss.asm` | the RAM layout |
| `tools/gen_tables.py` | the keyword list: tokens, names, the statement and operator tables |

**Program store.** A line is `[length][number hi][number lo][tokens][0]`; keywords are one byte (80h-D1h), numbers
`01 hi lo` (`02 hi lo` for `&H`), variables `03 slot*2` (`04` for an array). The store begins with a dummy line 0
and ends with a 0; a jump to a line sets the current line to the line before it, so the statement loop steps onto
the target as at any line end. FOR and GOSUB keep their frames on a stack of their own (240 bytes), so `NEXT` jumps
straight back to the loop without searching.

**Memory.**

| Address | What |
|---|---|
| 0000-1FFF | ELF/OS (the kernel and its buffers) |
| 2000-50B8 | GBASIC |
| 50B9-68FF | **the program, then its arrays** (6,215 bytes, 6,210 free when empty); LOAD uses the top 531 bytes for its buffers |
| 6900-69BF, 6A00-6ABF | the values and names of the variables (96) |
| 6B10-6BFF | the FOR/GOSUB stack |
| 6C00-6DFF | LOAD's read buffer, the typed line, its tokens |
| 6E00-6EFF | GBASIC's own variables |
| 6F00-6FFF | the machine stack (expressions nest here) |
| 7000-77FF / 7800 | the text screen / VIDEO-G's graphics window |

## Limits and known gaps

- **No strings** (no string variables or functions); strings appear only as literals in PRINT, INPUT prompts and
  file names. No floating point. `CHR$` exists only as a PRINT item.
- **VIDEO-G is not built**: everything was tested in the emulator's behavioural model; the timings are the emulated
  1802's. The keyboard codes are those of the VIDEO-G PS/2 firmware of 2026-11-02.
- **The ELF/OS boot loader writes port 4** (sector numbers, the ELF hex-display habit), which leaves VIDEO-G's control
  register at 0Eh (graphics on, XOR) after a boot until a program writes it; GBASIC does at start
  (`firmware/hbios/video-g/README.md`).
- HBIOS on VIDEO-G uses the NTSC table (64 x 25) even with the 5151 jumper; GBASIC's graphics follow the jumper
  (256 lines), and LOCATE keeps to the 25 text rows HBIOS uses.
- The mouse is not used by GBASIC (`INP(7)` and `INP(4)` reach it).
- `FOR` bodies run at least once; `IF ... ELSE` on one line pairs the ELSE with the first IF.
- Lines far off the screen are drawn pixel by pixel (they are clipped per pixel): `LINE -30000,-30000,30000,30000`
  takes many seconds. Circles and boxes are clipped by rows and are fast.
- 96 variable names; 6.1K for programs. SAVE and LOAD are slow (about 280 bytes a second: the ELF/OS kernel).
