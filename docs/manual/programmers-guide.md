# System-5 programmer's guide

How to program System-5 on the bare machine: the memory and I/O maps, each device as software sees it, the boot ROM (HBIOS) and its monitor, the BIOS calls, and the tools.
The hardware behind each section is in the card chapters; the 1802 instruction set is in `../private-resources/elf/reference/datasheets/` (the RCA user manual, MPM-201A).

## The machine at a glance

| Item | Value |
|---|---|
| CPU | CDP1802, about 1.76 MHz (crystal unread; the 1861 frequency), 4.5 µs per machine cycle |
| RAM | 0000–6FFF (28K) |
| Video RAM | 7000–77FF (64 × 16 characters at 7000–73FF) |
| CRTC | 7800 (address register), 7801 (data register) |
| EPROM | 8000–EFFF on the memory card; F000–FFFF the CPU card's boot ROM (HBIOS) |
| Console | the 6845 screen and the PS/2 keyboard (no serial port) |
| Disk | a CompactFlash card on the IDE card, 512-byte sectors by LBA |
| Operating system | Mike Riley's Elf/OS 5.1.1 (build 229), his later release, booted from the CF card since 2026-11-15; before that his ELF/OS 0.2.6 |

## Memory map

| Address | Contents | Notes |
|---|---|---|
| 0000–00FF | monitor stack and workspace | the monitor's stack starts at 00FF and grows down |
| 0100–6FFF | programs; ELF/OS | ELF/OS's boot sector loads at 0100 |
| 7000–73FF | screen: row r, column c at 7000 + 64 r + c | one byte per character, 7-bit ASCII; bit 7 = reverse video |
| 7400–77FD | rest of the video RAM | free, not displayed |
| 77FE–77FF | HBIOS's cursor position (high, low) | do not use |
| 7800–7FFF | 6845 CRTC | even address = register select, odd = data |
| 8000–EFFF | EPROM | the memory card's jumpers decide this |
| F000–FFFF | HBIOS | boot code, video and keyboard drivers, Mike Riley's BIOS and monitor |

The memory card in the machine, Rev E (MEM3-E, since 2026-10-31), decodes by jumper: it leaves 7000–7FFF to the 6845 card and F000–FFFF to the CPU card's EPROM, so each address has one driver (`memory-card.md`).

## I/O map

| Instruction | Device | Effect |
|---|---|---|
| `INP 1` | keyboard (CDP1852) | the waiting character; clears the ready flag |
| `OUT 2` | IDE register select | bits 0–2 = register, bit 3 = control block (0Eh = device control) |
| `OUT 3` | IDE | write the selected register |
| `INP 3` | IDE | read the selected register |
| `INP 4` / `OUT 4` | 1861 display on / off | only if the IO card's SV6 is fitted (it is not on the built card) |

| Flag / line | Meaning |
|---|---|
| EF3 | a keyboard character is waiting (`B3` / `BN3`) |
| Q | free: on the bus, and the CPU card's Q LED |
| EF1, EF2, EF4 | not connected |
| interrupt | only the 1861 can interrupt; with it off, interrupts never come |

### The 2026 boards (designed, not built)

The maps above are the machine as built. The boards designed in 2026 change two parts of them; each has its own chapter.

- **VIDEO-G TEXT and GFX** ([video-g-text-card.md](video-g-text-card.md), [video-g-gfx-card.md](video-g-gfx-card.md)) answer in one 4K block, like the 6845 card, and use no I/O port. In block 7: 7000–77FF the text RAM; 7800 / 7801 the 6845 (write-only, reads FF); 7802 the key (reading it clears KEY-READY); 7804 status (bit 0 KEY-READY, 1 MOUSE-READY, 2 VSYNC, 3 DE, 4 MONITOR, 5 GFX-PRESENT, bits 7–6 = 10), and on GFX its control register when written; 7806 on GFX the mouse byte (read) and the Y register (write); 7C00–7C3F, repeated to 7FFF, the GFX graphics window. The keyboard is read from memory there, not from `INP 1`.
- **The IO panel** ([io-panel.md](io-panel.md)) replaces the 2005 IO card: `OUT 4` the LEDs and the two OUT digits, `INP 4` the toggles (JP1 and JP2 may move these to any port 1–7); port 6 selects a clock register (`00`–`7F`) or a UART register (`80`–`87`), port 7 writes or reads it (JP4: ports 2/3, 4/5 or 6/7; 6/7 as set, which leaves the IDE card its ports 2 and 3). INPUT is on EF1 as set (JP3). The [front panel](front-panel.md) is the same card's controls on a ribbon and adds no port.

## Programming the devices

### The screen

Write characters straight into the video RAM. Upper and lower case display (the "goodfont" character ROM); set bit 7 for reverse video.

```
        ldi  high 7000h+64*2+10   ; row 2, column 10
        phi  rf
        ldi  low 7000h+64*2+10
        plo  rf
        ldi  'A'
        str  rf
```

The cursor is the 6845's R14 (high, 6 bits) and R15 (low): write the register number to 7800, then the value to 7801. The value is the character's address relative to 7000.
HBIOS's `outchar` (through `f_type`) does all this: it handles CR, LF, backspace and scrolling (by copying), and keeps the cursor in 77FE–77FF.

### The keyboard

```
wait:   bn3  wait        ; EF3: a character is waiting
        sex  r2
        inp  1           ; D = M(R2) = the character
```

`INP` also writes the byte into memory at R(X), so point X at a byte you can spare (the stack top, as above).
The keyboard sends ASCII; ESC is 1Bh (HBIOS's break test looks for it).

### The CF card

```
        sex  r3          ; immediate OUT: the byte after the instruction
        out  2
        db   07h         ; select the status register
        sex  r2
        inp  3           ; D = status: 80 BSY, 40 DRDY, 08 DRQ, 01 ERR
```

To read a sector: wait for DRDY; write the sector count (register 2) = 1, LBA 0–23 (registers 3–5), E0h + LBA 24–27 (register 6); command 20h (register 7); wait for DRQ; select register 0 and do 512 `INP 3`s. Before the first transfer put the drive in 8-bit mode: features (register 1) = 01h, command EFh. The BIOS does all of this (`f_ideread`, `f_idewrt`, `f_iderst`).

### The 6845

The registers and HBIOS's values are in `video-6845-card.md`. Only R14–R17 can be read back; the others are write-only. On the 6845 card Rev B-Clean-Keyboard and on VIDEO-G (neither built) none can: the 6845 is write-only, and 7800 / 7801 read as FF. No program needs to read them: HBIOS keeps the cursor in 77FE–77FF. Hardware scrolling by changing R12/R13 works within 2K only (the bus sees 2K of the 4K video RAM).

## Starting the machine

1. Reset clears the CPU card's boot flip-flop: the boot EPROM answers at every address and the bus is hidden (-VMA high).
2. The 1802 starts at 0000 with P = 0 and X = 0, and fetches HBIOS's first bytes. `LDI F0h / PHI R0` makes the next fetch come from F0xx: the first access with A15 high sets the flip-flop, and from then on HBIOS runs at F000–FFFF with the bus cards visible.
3. HBIOS loads the 6845 (`vtable`), clears the screen, stores the cursor position and jumps to the monitor (`f_minimon`).
4. The monitor sets R2 = 00FF, X = 2, initialises SCRT (R4 = call, R5 = return, R6 = return address) and prompts.

## The monitor

The monitor is Mike Riley's, part of his BIOS: it reads a line and acts on its first character. Addresses and bytes are in hex. The commands from `H` down are System-5's additions to it (HBIOS v1.0.5 and later), in the System-5 part of the ROM; his monitor passes any command it does not know to them.

| Command | Effect |
|---|---|
| `?addr` | dump 128 bytes from addr |
| `!addr bb bb …` | store bytes at addr |
| `=src dst count` | copy memory |
| `@addr` | run at addr with P = 0 and X = 0 (R0 = addr) |
| `@FF00` | boot ELF/OS from the CF card (`f_boot`) |
| `H` | list the commands (**HBIOS v1.0.5** and later; the machine runs v1.0.6) |
| `B` | boot the OS from the CF card, as `@FF00` (**v1.0.5**) |
| `D start:end` | disassemble, 14 lines a screen; at `-- more --` any key goes on, Esc stops (**v1.0.5**). `D start`: one screenful |
| `Q1` / `Q0` | Q output on (`SEQ`) / off (`REQ`) (**v1.0.5**) |
| `@F1C0` | the IO panel demo: toggles to the LEDs, INPUT (EF1) to Q, until Reset (**v1.0.5**) |
| `@F1E0` | key codes: wait for a key (EF3), read it (`INP 1`), write its code as `0x31` at the start of the bottom line, over the last, until Reset; self-contained, straight into the video RAM (**v1.0.7**, 2026-11-17) |

`f_boot` resets the drive, reads LBA 0 into 0100 and runs it there (R0 = 0100).

The monitor looks only at the first character and reads the rest as hex. Anything it does not know gives the prompt again, with no message. `H`, `B`, `D` and `Q1` / `Q0` are in HBIOS v1.0.5 (`firmware/hbios/v1.0.5/`) and v1.0.6, the machine's ROM since 2026-11-15; v1.0.4 does not have them.

## BIOS calls

HBIOS keeps Mike Riley's standard jump table at FF00, so ELF/OS and its programs find the BIOS at the same addresses as on every Riley-BIOS 1802. Call with SCRT:

```
        sep  r4          ; R4 = scall
        dw   0ff09h      ; f_msg: type the string at RF
```

The registers: R2 = stack (X = 2), R3 = program counter, R4 = call, R5 = return, R6 = return address and inline arguments. Most routines take and return values in D, DF (error flag), RD and RF.

| Address | Name | Does | In / out |
|---|---|---|---|
| FF00 | f_boot | boot from the CF card | |
| FF03 | f_type | type the character in D (System-5: the screen) | D |
| FF06 | f_read | read a character (System-5: the keyboard, echoed) | → D |
| FF09 | f_msg | type a zero-terminated string | RF |
| FF0F | f_input | read a line, up to 256 bytes | RF = buffer |
| FF12 | f_strcmp | compare strings | RF, RD |
| FF15 | f_ltrim | skip leading spaces | RF |
| FF18 | f_strcpy | copy a string | RF → RD |
| FF1B | f_memcpy | copy memory | RF → RD, RC = count |
| FF30 | f_mul16 | RC:RB = RF × RD | |
| FF33 | f_div16 | RB = RF / RD, RF = remainder | uses R8, R9 |
| FF36 | f_iderst | reset the drive, 8-bit mode | |
| FF39 | f_idewrt | write a sector | RF = buffer, R7 = LBA 0–15, R8.0 = LBA 16–23, R8.1 = E0h + LBA 24–27; DF = error. HBIOS 1.0.6 (the machine's since 2026-11-15) sets E0h itself, as Mike Riley's later BIOS does; 1.0.4 and 1.0.5 send R8.1 to the card as given, and 00h there is a CHS address the card refuses (Elf/OS v5 passes 00h) |
| FF3C | f_ideread | read a sector | as f_idewrt |
| FF3F | f_initcall | set up SCRT (R4, R5), then jump to R6 | |
| FF42 | f_ideboot | boot from the drive | |
| FF45 | f_hexin | hex text to a number | RF = text → RD |
| FF48 | f_hexout2 | a byte as 2 hex digits | RD → text at RF |
| FF4B | f_hexout4 | a word as 4 hex digits | RD → text at RF |
| FF4E | f_tty | type the character in D | D |
| FF51 | f_mover | copy a program image from ROM into RAM and run it | RF = image: RAM start, RAM end, run address (2 bytes each), then the program |
| FF54 | f_minimon | the monitor | |
| FF57 | f_freemem | find the last writable address | → RF |
| FF5A | f_isnum | is D a digit? | DF |
| FF5D | f_atoi | decimal text to a number | RF → RD |
| FF60 | f_uintout | unsigned number to decimal text | RD → RF |
| FF63 | f_intout | signed number to decimal text | RD → RF |
| FF66 | f_inmsg | type the string that follows the call | inline |
| FF69 | f_inputl | read a line, RC = maximum length | RF |
| FF6C | f_brktest | was a break (ESC) typed? | DF |
| FF6F | f_findtkn | look up a token | |
| FF72–FF7E | f_isalpha, f_ishex, f_isalnum, f_idnum, f_isterm | character tests | DF |
| FF81 | f_getdev | which devices are present | |

The serial-port, baud-rate and drive-geometry entries (FF0C, FF1E–FF2D) are stubs on System-5. The source, with each routine's register use, is `firmware/hbios/v1.0.4/orig_bios/bios.asm`; the System-5 video and keyboard code is `firmware/hbios/v1.0.4/sec1.asm`, reached from Mike's `type` and `read` through F203 and F200.

## ELF/OS

Since 2026-11-15 the machine runs Mike Riley's later operating system, Elf/OS 5.1.1 (build 229), from the CF card; it needs HBIOS 1.0.6. Before that it ran his ELF/OS 0.2.6 (build 135), the system of 2004–05. The commands of both are in the [operator's guide](operators-guide.md); 0.2.6's kernel API, file system and utilities are documented with its source in `../private-resources/elf/reference/mike-riley/`. Known issues found with the emulator:
- HBIOS loses the first character after a 64-column line wrap, so `DIR` drops every fifth name.
- `EDIT` with no file name hangs (kernel 0.2.6 build 135's empty-path handling); give a name.

## Tools

| Tool | Where | Use |
|---|---|---|
| rcasm | `../private-resources/elf/reference/mike-riley/` | Mike Riley's 1802 assembler; HBIOS's Makefile uses it with `cpp` and `srec_cat` |
| srecord (`srec_cat`) | | merges and converts ROM images (Intel hex, binary) |
| s5emu | `software/s5emu/` | emulator: boots HBIOS and ELF/OS; `--hw` runs the cards from their netlists; terminal and browser debuggers |
| s5busdrv.py | `software/busdrv/` | the bus driver card: peek, poke, load, dump, memory test, `INP`/`OUT` with the CPU card out |
| bringup.py | `software/busdrv/` | test plans for the memory, CF and 6845 cards |

Building HBIOS: `firmware/hbios/v1.0.4/Makefile` assembles `sec1.asm`, merges it over Mike's `bios.img` and writes `sec1.rom`, the 4K image for the CPU card's 2732.
