# IO panel card Rev A: design notes

**Status (2026-11-18):** the card as Ken set it on 2026-11-17/18 — IN and OUT ports and INPUT's EF line on jumpers, a
DS12885 real-time clock, the TIL311s turned, the LEDs labelled by function, and (later on 2026-11-18) the bus
address on four more TIL311s — is drawn, routed and checked; not ordered. The sections "Changes of 2026-11-17/18" and
"The bus address on four TIL311s" below are the current state; the sections before them are the 2026-10-30 design.

**A serial port since 2026-11-20 (Ken):** a 16C550 UART with a MAX232 and a DE-9 socket, the card 1.75 in longer for
it (7.50 x 4.00 in, still two layers). Drawn on a test branch, `io-panel-serial`, and merged into `main` the same day at
Ken's word ("ok if check is clean i will want to merge into main for this card and order this card"): `pcb-check
--tests` showed no failures and 0 warnings at `eebc2ed`. "Programming the card" below is the software's view of the
whole card; "The serial port" further down is the circuit and the layout. Not ordered yet.

**RUN/RESET turned and the serial port's labels drawn anew, the night of 2026-11-23 (Ken):** up is RUN, as on the front
panel; JP6's two settings are pictures on the silkscreen. "RUN/RESET turned, and the serial port's settings as
pictures" below.

**A header for a front panel since 2026-11-22, and a RESET button of its own since 2026-11-23 (Ken):** the card is
8.00 x 4.00 in, with a 50-pin header (J3) at the front edge for the ribbon to `hardware/front-panel`; its DMA request
was put right (as first drawn it would have loaded every byte twice); SW12 RESET boots the EPROM, and the serial
port's settings are printed on the silkscreen. The last two sections before "Board" have it. Drawn on the
branch `front-panel`, in `main` since 2026-11-23 (Ken: "merge everything"); not ordered.

**REQ and DRIVE from a known state at power-up since 2026-11-25, and the RESET button away from INPUT since 2026-11-26
(Ken):** D1 (a BAT85), R5 and R6 (3.3k) and U9C/U9D clear the DMA request and the toggles' drive outside LOAD mode; the
UART's interrupt and the ROM LED moved to U23C/U23D, and U23 is a 74HCT03. SW12 RESET is in the front strip's top corner,
above J3, about 85 mm from INPUT. Routed again; **`pcb-check --tests` at `6f4359d`: no failures, 1 warning** (the accepted
LAYOUT one). The last two sections before "Board" have it; in `main` since 2026-11-26; not ordered.

The new IO card: System-5's front panel. LEDs, switches and two TIL311 hex displays on an I/O port, a Q LED, an INPUT button
on an EF line, and the machine's hand controls (PAUSE, LOAD) on the 36-pin bus. It replaces the 2005 IO card
(`hardware/io-1861-keyboard/`: its keyboard moves to the video card (VIDEO-G's TEXT board), its 1861 is dropped). Started 2026-10-30 (Ken).
The folder name `io-panel` is a working name. The bus: `docs/manual/bus.md`, "The 36-pin extension".

## Programming the card: ports, flags and registers

*(Written 2026-11-20, for Ken's "what is the io programming model for all parts of IO board".)*

An 1802 has seven I/O ports, 1 to 7. `OUT n` (opcode `6n`) puts M(R(X)) on the bus and adds 1 to R(X); `INP n`
(opcode `68 + n`) puts the bus in D and in M(R(X)). The card's ports are picked by jumpers; the table shows them as set.

### The ports, by number

| Port | `OUT n` | `INP n` | Jumper |
|---|---|---|---|
| 4 | the byte is latched: the eight LEDs (BIT 7-0) and the two hex digits OUT D7-D4, OUT D3-D0 show it | the eight toggles (BIT 7-0), up = 1 | JP2 (OUT) and JP1 (IN): each any port 1-7, each on its own |
| 6 | **select**: `00`-`7F` = a register of the clock (DS12885); `80`-`87` = register 0-7 of the UART (16C550) | nothing (the card does not drive the bus) | JP4: the pair 2/3, 4/5 or 6/7 |
| 7 | **data**: writes the register selected | reads the register selected | JP4 (the same pair) |

The rest of the machine, for the whole map: port 1 is the 2005 IO card's keyboard (free once that card is out), 2 and 3
are the IDE card's (register select and data), 5 is free.

### What is not a port

| Part | How a program sees it |
|---|---|
| INPUT button | a flag: low on the bus line JP3 picks (-EF1, -EF2, -EF3 or -EF; set to -EF1) while it is pressed. With CPU Rev D that is EF1: `B1` (`34`) branches while it is down, `BN1` (`3C`) while it is up |
| Q LED | lit while Q is set: `SEQ` (`7B`), `REQ` (`7A`) |
| Address display (A15-A12 ... A3-A0) | nothing to program: the address of the last machine cycle, held while the clock is stopped |
| RUN/RESET, LOAD | the hand controls: RUN off resets, LOAD on pauses, both = LOAD mode, where each INPUT press stores the toggles at M(R0) and adds 1 to R0 (one DMA IN) |
| RESET button (2026-11-23) | a boot reset: the machine starts in the EPROM (HBIOS), whatever was loaded into RAM. The RUN/RESET toggle starts again what ran before. Nothing while LOAD is on |
| Interrupts | the clock's IRQ and the UART's INTR can each pull the bus -INT low: JP4's last row and JP7, both open as set |

### The clock: select `00`-`7F`

| Register | |
|---|---|
| `00` seconds, `02` minutes, `04` hours | `01`, `03`, `05`: the alarm's |
| `06` day of the week (1 = Sunday), `07` date, `08` month, `09` year (00-99) | |
| `0A` | A: bit 7 UIP (an update is in progress), bits 6-4 = `010` to run the oscillator |
| `0B` | B: bit 7 SET (stop the clock to set it), bit 2 DM (1 = binary, 0 = BCD), bit 1 (1 = 24-hour) |
| `0C`, `0D` | C: the interrupt flags (a read clears them); D: bit 7 VRT (the battery is good) |
| `0E`-`7F` | 114 bytes of RAM kept by the battery (JP5 clears them) |

HBIOS v1.0.8 has the driver: `f_gettod` (F815) and `f_settod` (F818), binary and 24-hour, Mike Riley's convention.

### The serial port: select `80`-`87`

A 16C550, so the registers every 16550 program knows. The clock is the card's own 1.8432 MHz oscillator:
divisor = 115200 / baud (12 = 9600, 6 = 19200, 3 = 38400, 1 = 115200). Only bits 7 and 2-0 of the select byte count
for the UART, so `88`-`FF` repeat `80`-`87`; use `80`-`87`.

| Select | Read (`INP 7`) | Write (`OUT 7`) |
|---|---|---|
| `80` | RBR: the character received | THR: a character to send. With DLAB set: DLL, the divisor's low byte |
| `81` | IER | IER: bit 0 received data, bit 1 THR empty, bit 2 line status, bit 3 modem status. With DLAB set: DLM |
| `82` | IIR: bit 0 = 0 while an interrupt waits, bits 3-1 which one | FCR: bit 0 FIFOs on, bit 1 / bit 2 clear the receive / send FIFO |
| `83` | LCR | LCR: `03` = 8 bits, no parity, 1 stop; bit 7 = DLAB |
| `84` | MCR | MCR: DTR, RTS, OUT1, OUT2 (none of them leaves the card), bit 4 = loop back |
| `85` | LSR: bit 0 = a character is waiting, bit 5 = THR empty, bit 6 = all sent | |
| `86` | MSR: `00` (CTS, DSR, DCD and RI are tied off on the card) | |
| `87` | a scratch byte | a scratch byte |

Set it up, then send and receive (X = P for the `OUT`s, so each takes the byte after it; R2 is the stack pointer):

```
        sex  r3
        out  6
        db   83h            ; LCR
        out  7
        db   80h            ;   DLAB on
        out  6
        db   80h            ; DLL
        out  7
        db   12             ;   9600 baud
        out  6
        db   81h            ; DLM
        out  7
        db   0
        out  6
        db   83h            ; LCR
        out  7
        db   03h            ;   8 bits, no parity, 1 stop; DLAB off

wait:   sex  r3
        out  6
        db   85h            ; LSR
        sex  r2
        inp  7
        ani  01h            ; a character waiting?
        bz   wait
        sex  r3
        out  6
        db   80h            ; RBR / THR
        sex  r2
        inp  7              ; the character, in D and at M(R2)
        out  7              ; send it back (M(R2); R2 + 1)
        dec  r2
        br   wait
```

(That program is `tests/test_hw.py`'s `test_a_program_echoes_the_serial_line_on_the_netlist_cards`: it runs on the
emulator's gate-level model of CPU Rev D and this card. To send without echo, wait for LSR bit 5 first.)

### Three things to know

- **Always select before the data port.** The select byte is held in a latch on the card (U22) and in the DS12885;
  both power up holding anything. It cannot be read back.
- **One select for both chips.** A routine that uses port 6 between another routine's `OUT 6` and its `OUT 7` /
  `INP 7` changes what that one reaches. That matters only when an interrupt routine uses the clock or the UART:
  keep interrupts off across the pair then (or select again after them).
- **Moving JP4 moves both chips.** On 2/3 the pair meets the IDE card, on 4/5 the panel's own port 4 (move JP1 / JP2
  first). 6/7 is the setting to keep.

## Decided (Ken, 2026-10-30)

| Item | Decision |
|---|---|
| Output | **8 LEDs** and **2 TIL311** hex displays showing the byte written by `OUT 4`, latched in a **74HCT374**. |
| Input | **8 switches**, **eight toggle switches** (Ken, 2026-10-30), read by `INP 4` through a **74HCT244**. |
| Port | **Port 4** for both (ports 1-3 are the keyboard and the IDE card). The card decodes it itself from N0-N2 and -MRD (no bus -INP/-OUT). **Since 2026-11-17: any port 1-7, IN and OUT each on its own jumper block (set to 4).** |
| INPUT button | On **-EF1** (open collector) → the CPU's EF1. **Since 2026-11-17: -EF1, -EF2, -EF3 or -EF on a jumper (set to -EF1).** |
| Q LED | From bus Q (pin 10), through a buffer. |
| Hand controls | The COSMAC ELF's **RUN** and **LOAD** toggles (RUN off pulls -RESET, LOAD on pulls -PAUSE: LOAD mode = RUN off + LOAD on, PAUSE = RUN on + LOAD on; changed 2026-10-30 from PAUSE/LOAD with the CPU Rev D netlist, so LOAD → RESET → RUN runs a loaded program), the INPUT button on -DMAIN in LOAD mode, the 8 switches as the data. Works with or without a debug board. |
| Bus | The 36-pin interface. |
| Layout | The board layout rules: every switch, button, LED and display on the front edge, each labelled (bit 7-0, Q, INPUT, PAUSE, LOAD); `cottageworker.com` and the board name/revision; 0.1" bypass caps. |
| Layers | **2 copper layers if at all possible** (Ken, 2026-10-30): cheaper and quicker to check; `pcb-check --layers 2`. Go to 4 only if routing truly fails, and ask first. |

## Proposed (to agree with Ken)

1. **Port decode.** A 74HCT138 on N0-N2; output 4 gated with -MRD: `OUT 4` (-MRD low) clocks the '374 on TPB; `INP 4` (-MRD high)
   enables the '244 onto D0-D7 for the execute cycle. Check against the bus timing (`python3 -m s5emu.timing 2`).
2. **TIL311s.** Each has its own 4-bit latch; tie their LATCH STROBE low (transparent) and feed them from the '374's outputs, so they
   always show what the LEDs show. Left display = bits 7-4, right = bits 3-0. Blanking inputs tied off. Note: the TIL311 is long out
   of production (surplus, and not cheap); the footprint is a 14-pin wide DIP.
3. **LEDs.** The '374 drives eight LEDs through resistors (sinking or sourcing a few mA each), or through a ULN2803 if brighter.
   Q LED through a 74HCT buffer, so the bus Q line sees one CMOS input.
4. **INPUT button.** Debounced (RC + 74HCT14, or an SR latch on a changeover push-button), then:
   - to **-EF1** through an open-collector driver (74HCT05 / 74LS06 gate or a transistor), so programs read it with `B1`/`BN1`;
   - in LOAD mode (the LOAD switch on), **one -DMAIN request per press**: the request is set by the press and cleared by the DMA
     cycle (-MWR rising while -MRD is high), so a held button loads one byte, not many.
     (That clear came too late for the 1802, which looks at the request again before -MWR rises: put right on
     2026-11-22, "The DMA request lasted too long", below.)
5. **Data in LOAD mode.** The '244 also drives D0-D7 while this card's own DMA request is pending **and** -MRD is high (the DMA IN
   cycle; in IDLE the memory drives M(R0)). Never for another card's request.
6. **RUN and LOAD switches** (ELF-style). Toggles to open-collector drivers: RUN off pulls -RESET, LOAD on pulls -PAUSE. To load:
   RUN off, LOAD on, toggle bytes in with INPUT; then LOAD off (reset, R0 = 0000), RUN on: the program runs from 0000 (the CPU
   card's LOADED flag keeps its boot map off). The CPU card's RESET/RUN switch boots HBIOS and still overrides.
7. **Switches.** Eight toggles (decided, Ken 2026-10-30) with pull-downs, labelled 7 … 0, high = 1. The INPUT button and the PAUSE/LOAD
   toggles labelled by function.
8. **Folder and generator.** `hardware/io-panel/kicad/rev-a/` with `gen/netlist.py`, `make_schematic.py`, `make_board.py`, a
   `schematic/spec.py`, lines in `build_all.sh` / `make_book.py`; a model in s5emu (port 4, -EF1, LOAD/DMA) so a program can be
   toggled in on the emulator before the order.

## Netlist (2026-10-30): `gen/netlist.py`, `gen/make_schematic.py`

Written and checked: ERC 0, 58 parts, no single-pin nets; redrawn schematic (`schematic/`, 6 sheets) proven MATCH 64/64,
in the book. A gate-level walk-through checked OUT 4, INP 4, INPUT while running, LOAD mode, one DMA IN per press (held
button), and that a debug board's DMA with the button held never makes this card drive. Board not started.

- **Chips:** U1 74HCT138 (port 4), U2 74HCT374 (OUT latch), U3 74HCT244 (switches), U4 74HCT14, U5 74HCT10 (OUTCLK),
  U6 74HCT00, U9 74HC05 (open collector: -EF1, -DMAIN, the Q LED; a 74HC03 since 2026-11-22), U10 74HCT74 (REQ, ACK), U11 74HCT74 (DRIVE), U7/U8
  TIL311. Spares: U5B/C, U6D, U9 ×3, U11B.
- **OUT 4** latches on TPB's fall (OUTCLK = NAND(port 4, -MRD low, TPB) clocks the '374 as TPB ends).
- **INP 4 and LOAD data:** the '244 drives while -MRD is high and (port 4 or DRIVE). DRIVE (found in the walk-through):
  without it the switches left the bus as -MWR rose, up to 140 ns before memory D's delayed WE (CD4050B) latches them;
  DRIVE holds them until -MRD falls in the next cycle, as INP 4 already does.
- **Hand controls (ELF-style):** SW10 RUN/RESET and SW11 LOAD ground -RESET and -PAUSE directly (no driver chips; the CPU
  card's Schmitt buffers take the bounce). INPUT (SW9) is debounced (R1 10k, C1 470 nF, Schmitt: about 5 ms; the press counts at the first contact, the release once the input has stayed open about 1.7 ms).
- **Data switches: eight vertical SPDT toggles, SW1-SW8** (Ken, 2026-10-30: "vertical, just like the YACC1 IO card";
  Marquardt M9040P, the YACC1 footprint): common = the bit, ends on +5V and GND, so no pull-downs.
  The front edge is 4.00 in: the 8 data toggles, INPUT, RUN, LOAD, 10 LEDs and two TIL311s need two or more rows near it
  (or a taller card); the toggle part (the E-Switch 100 footprint is a placeholder; a smaller sub-miniature toggle may fit
  better) is to choose with the board.
- **TIL311:** pinout and footprint (HTIL311A, 0.3 in rows) taken from Ken's built YACC1 IO card (2026-10-30): 3/2/13/12 =
  data A-D, 5 latch strobe and 8 blanking to GND, 1 LED supply straight to +5V, 14 Vcc, 4/10 decimal points unused.
- **No pull-ups on the bus lines** here: the CPU Rev D and the bus Rev D have them.

## Changes of 2026-11-17/18 (Ken): jumpers, the real-time clock, the layout

- **Ports on jumpers.** JP1 IN PORT and JP2 OUT PORT (2x7 each): a jumper across row n makes port n the card's input or
  output port; set to 4. JP3 INPUT EF (2x4): INPUT's open-collector flag on -EF1, -EF2, -EF3 or -EF; set to -EF1. RN1
  (10k x8, a SIP) holds every jumper's common high with no jumper: no port, no flag.
- **Real-time clock** (Ken: "add a realtime clock to io card with a selectable io"; then "rtc as planned"): U13
  **DS12885+**, Intel bus timing (MOT low), CS tied low, RESET tied high; Y1 32.768 kHz (6 pF); BT1 a **CR2032 in a flat
  holder, Keystone 103** (an upright holder stands about 22 mm, more than the 21.3 mm between cards at the 1 in slot pitch),
  straight on VBAT (the DS12885 switches over itself). **JP4 RTC** (2x7) picks the port pair: one jumper on A2, A4 or A6
  (the address register's port), one on D3, D5 or D7 (the data port); set to 6 and 7. Its last row, INT, puts the clock's
  open-drain IRQ on the bus -INT (off; RN1 pulls IRQ up).
  - Strobes, one 74HCT02 (U12) and two spare gates: OSTB_L = NAND(MRD_H, TPB) (U6D), low in TPB of every memory read, so
    of every OUT. AS = NOR(address select, OSTB_L) (U12A): an OUT to the address port latches the byte as TPB ends.
    R/W = NOT NOR(data select, OSTB_L) (U12B, U12C): an OUT to the data port writes it on R/W's rise. DS = NOT NOR(data
    select, MRD_H) (U12D, U5C): low through an INP of the data port, while the clock drives D0-D7. (First drawn with a
    74HCT14 and a 74HCT10; one chip fewer this way, to make room for the battery.)
  - Software: HBIOS **v1.0.8** (`firmware/hbios/v1.0.8/`): f_gettod / f_settod on ports 6 and 7, as Mike Riley's BIOS
    answers them for the ELF2000's clock (month, day, year since 1972, hour, minute, second; binary, 24-hour), and
    f_getdev bit 4. ELF/OS reads the time through them.
- **TIL311s turned -90** (Ken: "bottom of display towards bus connector"), at the top of the front edge, as on his YACC1
  IO card; the eight bit LEDs, Q and PWR in a column below them.
- **LEDs labelled by their function alone** (BIT 0-7, Q, PWR; Ken, 2026-11-18): `pcb-check.ini` exempts LED1-LED10 from
  the reference-on-the-silkscreen rule, with that reason.
- **Layout:** the top row U5, U6, U4, U12 at a 12 mm pitch, then Y1 and U13 (the crystal beside X1 / X2); RN1, R9, C1
  between the rows; the middle row as before; U1, JP4, C2 and BT1 at the bottom; JP1-JP3 along the bottom edge. The board's
  name and `cottageworker.com` on end in the free column between the toggles and the LEDs' resistors, at 270 degrees, so
  that they read left to right with the card standing in the bus, connector down (Ken, 2026-11-18: "IO needs changing";
  at 90 degrees they stood upside down). (Since moved to the bottom edge as drawn, and every other text turned to 270:
  "Lengthened to 5.75 in" below.)
- **Crystal:** X1 and X2 drawn by `make_board.py` (short, locked, F.Cu); no other track or via under them on B.Cu (a
  keep-out the GND pour still fills) or between U12 and Y1 on F.Cu, as the DS12885 data sheet asks.
- **+5V:** 0.5 mm (the Power class), as pcb-check wants. Freerouting left a gap or two on every seed until two runs were
  drawn by `make_board.py`, locked on B.Cu: C9 along the top margin to the TIL311s' supply pins and back to C10, and J1's
  +5V to C7. Then seed 0 routed every net. Since 2026-11-18 Freerouting's input lists those locked runs in a fixed order
  too (`tools/kicad/dsn_order.py`: before, they came in KiCad's order and a rebuild could route differently); on that
  input seed 0 left D0 to U13 open and seed 1 routes every net, so `gen/route.py` has `ROUTE_SEED = 1`, and a rebuild
  gives the same tracks every time.
- **The 0.1 uF footprint's silkscreen outline** (`s5io.pretty/C025-050X050`, this board's copy) is drawn at the body:
  Eagle's 5 x 5 mm outline stood out of the courtyard, past the board edge at C15.
- **To check before an order:** the M9040P toggles still to be had; the switch lever direction against a real part;
  the Keystone 103 and the DS12885+ in stock; Ken's look at the pictures and the fab's viewer.

## The bus address on four TIL311s (Ken, 2026-11-18)

Ken: "add 4 TIL-311 to IO card that shows current address being put on bus, it will help during load and also
debugging"; the card stays 5.50 x 4.00 in (his choice, against a taller card or 5 V LEDs; lengthened to 5.75 in the
same evening for the displays' labels: below).

- **Circuit.** The 1802 puts the high address byte on A0-A7 while TPA is high, then the low byte to the end of the
  cycle. **U18 74HCT573** latches the high byte (LE = TPA: it follows A0-A7 during TPA and holds them as TPA falls, as
  CPU Rev D's own 74HCT373 does); **U19 74HCT573** the low byte (LE = TPB: it holds them as TPB falls, at the end of
  the cycle). Their outputs ADR15-ADR8 and ADR7-ADR0 drive **U14 (A15-A12), U15 (A11-A8), U16 (A7-A4) and U17
  (A3-A0)**, TIL311s like U7 and U8 (strobe low, so transparent; blanking low). The display shows the last machine
  cycle's address and holds it while the clock is stopped; in LOAD mode the 1802 idles on R0, so it shows the address
  the next byte goes to, and steps on with each DMA IN.
- **Why latches, not the TIL311s' own.** A TIL311's data inputs are TTL (up to 1.6 mA each), and on CPU Rev D the
  1802 drives A0-A7 straight from its pins, too weakly for two of them per line. The 573s keep the bus to HCT inputs,
  need no inverter (TPA and TPB as they come) and keep the displays' strobes tied low, as on U7 and U8.
- **Room.** The bit LEDs' eight resistors are now **RN2, an isolated 1k x 8 DIP-16** (Ken's choice; R1-R8 gone, R9-R11
  are R1-R3). Down the front edge (across the top with the card standing): U14-U17, then U7 and U8 after a 2.6 mm gap
  that holds C9, then Q, PWR and INPUT. Each bit LED stands level with its toggle (above it when standing), its bit
  number between it and the displays; each display's name and job sit in a gap between two bit LEDs, beside it. The
  toggles' labels are at 270 degrees ("SW8 BIT 7", the 0 and 1 marks too), which frees a column for U18, RN2 and U19
  between the logic and the toggles; U11 moved 1 mm. The board's name runs along the bottom edge as drawn (up the
  right-hand side when standing). C9 and C10 (the six TIL311s' supply rail) and C16, C17 (the latches).
- **Checks** (as first built; since then: below). Routed on seed 6 (`gen/route.py`; seeds 6 and 7 of 0-11 route every net); `tools/preorder_check.py
  --layers 2` PASS (DRC 0 errors, 0 warnings; netlist 114 of 114). The emulator models it from the netlist
  (`NetlistIOPanel.cycle()`, `address()`; test `IOPanel.test_address_display`: six addresses through the gates, the
  display held between cycles, each TIL311's A-D pins on the right latch outputs).

## Lengthened to 5.75 in; every label upright with the card standing; the front panel by function (Ken, 2026-11-18)

- **All the silkscreen at 270 degrees** (Ken's rule of 2026-11-18 for every board: every text reads upright, left to
  right, with the card standing in the bus, connector down; then "convert the IO panel silk to 270"). The name line
  alone runs along the bottom edge as drawn (angle 0), so it reads up the right-hand side with the card standing. J1's
  pin names stand in two staggered rows (one row at 270 would not fit the 2.54 mm pitch). The logic and the latch column
  moved 2 mm nearer the bus to make room for the latch column's labels, and the bit LEDs turned so their pads lie across
  the strip. `make_board.py` places each label at the first spot clear of every pad, part body, other text and the edge.
- **5.75 × 4.00 in** (146.05 × 101.6 mm; Ken: "for IO CARD i think we need to lengthen so TIL-311 can be under each
  display, currently too close to LED"). Until then the displays' labels sat in the gaps between the bit LEDs and the
  displays 0.4 mm from the LEDs' bit numbers. The toggles and the bit LEDs stayed where they were on the 5.50 in card;
  the 6.35 mm went in between the bit LEDs and the displays, and the displays, C9, Q, PWR, their resistors R2 and R3
  and INPUT moved with the front edge. With the card standing each display's label is now under it, each resistor's
  under it.
- **The front panel labelled by its function alone**, as its LEDs already were (Ken: "remove U14 TIL-311 and others,
  SW1..."): the displays **A15-A12, A11-A8, A7-A4, A3-A0, OUT D7-D4, OUT D3-D0** (1.0 mm: at 1.2 mm the two OUT labels
  ran together), the toggles **BIT 7 ... BIT 0, RUN/RESET, LOAD**, the push-button **INPUT**; no SW1 ..., no U14 TIL311.
  `pcb-check.ini` exempts U7, U8, U14-U17 and SW1-SW11 with that reason (pcb-check lets such a part go without its value
  too since its commit `6f7035d`).
- **C15** (U13's 0.1 uF) back where it was before the 2 mm shift: shifted, its +5V pad sat in the card-support strip's
  keep-out, and none of twelve routing seeds reached it.
- **No text in the card-support strips** (3.00 x 0.15 in from the bus edge along the top and bottom edges, where the
  card guides would hide it; found that evening on the other cards): the jumper blocks' row numbers sit just under
  their pins, JP3's columns read 1, 2, 3, EF (-EF1 ... -EF; between the battery and the strip only single characters
  fit), the caps' labels moved off the top strip, Y1's under its crystal. The name line is "System-5 IO panel  Rev A
  2026" (Ken: no "S5IO-A", as no "S5BUS-D" on the bus), all System-5 cards alike since then. Copper unchanged.
- **Checks.** Of seeds 0-11 on this layout seed 1 routes every net (the others leave one to four +5V or data links
  open); `gen/route.py` has `ROUTE_SEED = 1`. `gen/build.sh`: ERC 0, DRC 0 errors and 0 warnings, 0 unconnected, parity
  0, netlist 114 of 114, 555 holes; `tools/preorder_check.py --layers 2` PASS; schematic redrawn, book rebuilt.
  `pcb-check --tests` at elf `f28e9a1`: **no failures, the same 2 warnings** (U13's RCLR left open on purpose; the
  DS12885+ not in its footprint table) and a note naming the 27 parts labelled by function.

## The slot order of 2026-11-18 (Ken)

Ken: "looking at the bus from the power supply end I want the right most pin to be gnd followed by the next original pin
order all the way to +5v/vcc, then EF1, EF2, EF3, -DMAin, SC0" (-PAUSE kept, at the far end), and the slot counted from
GND: "start counting at gnd as pin 1, there +5v is 30 and then the pins beyond 5v". So J1's positions 1-30 are the
30-pin bus from GND (1) to +5V (30), then 31-33 -EF1..-EF3, 34 -DMAIN, 35 SC0, 36 -PAUSE (`gen/netlist.py`'s `POS`, the
bus Rev D's; `docs/manual/bus.md`, "The 36-pin extension"). The circuit is unchanged.

- **J1** is the same C36 footprint turned end for end: pad 1, GND, at the bottom as drawn. The locked +5V run to C7
  starts at J1's +5V pad wherever `POS` puts it (position 30), no longer at "pad 4".
- **The bus pins' names** follow `POS`. "-PAUSE", at the end pin beside the card-support strip, is too long for
  0.8 mm text level with its pin (it shrank to 0.7 mm, under DRC's 0.8 mm minimum): a long name at an end pin may now
  go one column further out, or 0.5 or 1.0 mm towards the middle, before it shrinks. It sits in a third column, 0.5 mm
  below its pin, at 0.8 mm.
- **Routing.** With the new order, of seeds 0-8, 10 and 11, seeds 2, 3 and 10 routed every net (9 ran on past ten
  minutes). Then the slot was renumbered from GND: no signal moved, but Freerouting's result follows the order of its
  input, pin names included, and with J1's new pin numbers none of seeds 0-11 routed every net (four ran on past eight
  minutes). So `gen/route.py` gives Freerouting J1 as it was before the renumbering (`j1_by_place`: the connector turned
  back, each pin under its old number; the same pads, nets and places), and turns J1's placement back in the session
  file before the import, which would otherwise turn the connector round on the board under its tracks (the first try
  did: 43 shorts in DRC). `ROUTE_SEED = 2`: 1953 segments, 62 vias.
- **Checks.** `gen/build.sh`: ERC 0, DRC 0 errors and 0 warnings, 0 unconnected, parity 0, netlist 114 of 114;
  `tools/preorder_check.py --layers 2` PASS; schematic redrawn, book rebuilt. `pcb-check --tests` at elf `31c54a8` (pcb-check `60fd275`, 2026-11-18):
  **no failures, the same 2 warnings** (U13's RCLR left open on purpose; the DS12885+ not in its footprint table), the
  36 bus pins on J1 as defined, the emulator's IO panel tests passing. (Its note that -DMAIN is pulled up on another
  board: the bus Rev D's RN2 and CPU Rev D's RN1, 10k each.)
- **Two layers, decided** (Ken, 2026-11-18: first "maybe make io 4 layers", then "no need for io to be 4 layers if it
  routes on 2"): this is the densest of the 36-pin cards, about 2,000 track segments, and most routing seeds leave a
  link or two open on two layers, so each change to it means a seed search. It routes completely, and stays two layers
  for as long as it does (his rule of 2026-10-30: two layers if at all possible, ask before four).
- The card no longer fits the 2009 backplane (its +5V pin would meet D2 there): it needs the bus Rev D.

## JP5, the clock's RAM-clear jumper (Ken, 2026-11-18)

pcb-check warned that U13's pin 21, RCLR, was left floating, and Ken's ruling was "change add jumper". **JP5** is a
2-pin header from RCLR (pin 1) to GND (pin 2).

- **What a shunt does** (DS12885 data sheet): RCLR held low clears the chip's 114 bytes of general-purpose RAM, never
  the clock and calendar, and only while the chip runs from its battery, the power off. So to clear the RAM: power off,
  fit the shunt for a moment, take it off again. Left fitted, the RAM would be cleared at every power-off (the clock
  keeps time all the same). **Open, nothing changes.** RCLR has its own pull-up inside the chip, and the data sheet
  forbids an outside one, so there is none; it is meant for a hand-made short like this, not for a driver. (The data
  sheet is not in `../private-resources`: check this wording against it before relying on the jumper.)
- **Where:** at the top edge beside U13, above the BIT 7 toggle (Ken's rule: jumpers near an edge), in the strip between
  C16 and C10. Labelled at 270, upright with the card standing: `JP5 RTC` / `RAM CLR` under it and `FIT =` / `CLEAR`
  over it, 0.8 mm (the strip is 5 mm deep, hence the short lines). Nothing covers them.
- **Routing and checks:** with the jumper, seed 0 routes every net (1870 segments, 66 vias; 1, 4 and 7 leave one +5V
  link open). Freerouting spends about nine minutes on this board after its autorouter is done (route optimization),
  so a seed takes ten minutes to judge. `gen/build.sh`: ERC 0, DRC 0 errors and 0 warnings, 0 unconnected, parity 0,
  netlist 115 of 115, 561 holes; `tools/preorder_check.py --layers 2` PASS. `pcb-check --tests` at elf `e0dcd53`
  (2026-11-18, by the pcb-check session): **no failures, 1 warning** (the DS12885+ not in its footprint table; the
  RCLR warning is gone).
- **A full-size print:** `io-panel-rev-a-1to1.pdf` (Ken, 2026-11-18: "can i print a pdf of io card 1:1 to check switch
  hole size"), remade by `gen/build.sh` (`tools/kicad/print_1to1.py`): print at 100 %, measure the 100 mm line, lay the
  switches on their pads.
- The emulator does not model RCLR (`s5emu/rtc.py`); its IO panel tests pass with the jumper in the netlist.

## The switches are YACC1's (Ken, 2026-11-18)

Ken: "be sure io card switches are the same as those used on yacc1 io or at least compatible footprint hole size".
The ten toggles (SW1-SW8 the bits, SW10 RUN/RESET, SW11 LOAD) are `s5io:M9040P`, whose pads are those of the built
YACC1 IO card's footprint (YACC1-D `hardware/cards/io/kicad/v1.1`, `io-v1.1-eagle:M9040P`), compared file against file:
three oval pads 5.41 x 2.71 mm, 4.699 mm apart, 1.8034 mm holes; only the description and an added courtyard differ. So
the Marquardt M9040P toggles of that card fit here. **INPUT (SW9) stays a 6 mm push-button** (`SW_PUSH_6mm`, four pads,
1.1 mm holes): on the YACC1 card IN0 is another M9040P position, and Ken chose to keep the button here.

**The toggle's body on the fab layer at full size** (Ken, 2026-11-19: "yes draw the toggle outline full size"). Eagle's
M9040P had the sketch of the lever there, 8.2 x 10.3 mm, and the body's outline on the silkscreen alone, so the checks
and the full-size print took the toggle for shorter than it is (nothing stood under one: the labels round the toggles
are placed by hand, outside the courtyard). `s5io.pretty/M9040P` now has the outline on F.Fab too: 8.64 mm wide at the
middle, 13.36 mm long, the corners cut. No pad, label or track changed: a new build gives the same silkscreen and the
same Freerouting input, so the drawing alone was put into the routed board (`tools/kicad/fp_update.py --lib`), on all
ten toggles; the bus Rev D's SW1 the same way. Copper and silkscreen checked identical; DRC 0 errors and 0 warnings;
`tools/preorder_check.py --layers 2` PASS; `pcb-check --tests` at elf `e5322e4` (pcb-check `f93259d`): **no failures,
1 warning** (the DS12885+ not in its footprint table, as before), every text clear of the parts with the toggles at
their true size.

## The bus header drawn as the part it is; "J1 BUS" out from under it (the night of 2026-11-18)

J1 is a single-row right-angle pin header: its plastic body lies on the board between the pads and the card edge, 1.5
to 4.0 mm from the pads, and its pins run on past the edge (the photos of the built MEM3-E and BUSDRV-B show it). The
C36 footprint had pads and a courtyard round them and no body, so `gen/make_board.py` printed `J1 BUS` in that strip,
at the connector's middle, and `pcb-check` passed it: under the header on a built card. Found on VIDEO-G (its
`kicad/README.md`). `s5io.pretty/C36` now carries the body (F.Fab), a courtyard round body and pads, and KiCad's 3D
model of the header, so the render shows the connector. `J1 BUS` stands on the board side of the pin names, in the gap
between U2 and U1 (the nearest free place to the connector's middle: U2's pins leave no room beside the names there).
No other label moved. The board has no silkscreen-only build, so `gen/build.sh` ran in full: the footprint's drawing is
not in Freerouting's input, which came out the same as before, and so did the route (1870 segments, 66 vias: every
track, via, pad and zone identical). DRC 0 errors and 0 warnings; `tools/preorder_check.py --layers 2` PASS.
`pcb-check --tests` at elf `a330195` (2026-11-19, by the pcb-check session): **no failures, 1 warning** (the DS12885+
not in its footprint table, as before); its earlier passes had the label under the header, which it could not see.

## A `+` at the battery holder (Ken, 2026-11-19)

Asked by the pcb-check session, "Add a + beside the battery holder on the IO panel and the YACC1 I/O card V1.2?", Ken
said: "Yes, both". The holder's footprint (Keystone 103) has its `+` on the fab layer, inside the holder, so with the
holder soldered in and the cell fitted nothing on the board said which end is positive. The silkscreen now has a `+`
level with pad 1 (VBAT), in the 2 mm between JP4's end and the holder, and the holder's label follows it on the same
line: `+ BT1 CR2032`, right under the holder's positive tab with the card standing. The label stood there alone
before, centred on the pad, and moved 5.9 mm along the line; no other label moved. Silkscreen only: `gen/build.sh` ran
in full, with the same Freerouting input and the same route (1870 segments, 66 vias; every track, via, pad and zone
identical). DRC 0 errors and 0 warnings; `tools/preorder_check.py --layers 2` PASS. `pcb-check --tests` at elf
`bb0b711` (2026-11-19, pcb-check `1525f36`, whose LABELS line reads every silkscreen text): **no failures, 1 warning**
(the DS12885+ not in its footprint table, as before); every text clear of the parts, the `+` among them.

## The serial port (Ken, 2026-11-20)

Ken: "for io card create a test branch for adding serial io and db 9 to board, ok to lengthen board". His two choices:
a 16C550 UART with its own clock and a MAX232, as on his YACC1 I/O card; the DE-9 on the side edge, in a new strip
between the logic and the panel. Drawn on the branch `io-panel-serial`; merged into `main` the same day, once
`pcb-check` was clean.

### The circuit

| Part | | |
|---|---|---|
| U20 | 16C550 UART, DIP-40 (XR16C550, TL16C550C, PC16550D) | D0-D7 on the bus; A0-A2 and CS0 from U22; CS1 high, -CS2 and -ADS low; WR = RTC_WR, -WR high; -RD = UART_RD_L, RD low; MR = RESET_H; -BAUDOUT to RCLK; -CTS, -DSR, -DCD, -RI tied high and RTS, DTR, OUT1, OUT2 open, as on the YACC1 card |
| X1 | 1.8432 MHz oscillator, half-size (8-pin DIP) can | to XIN; XOUT open. Divisor 12 = 9600 baud, 3 = 38400 |
| U22 | 74HCT573 | the select latch: LE = RTC_AS; D0, D1, D2 -> UA0-UA2 (the UART's A0-A2), D7 -> SEL_UART; four latches spare |
| U21 | MAX232, C22-C25 four 1 uF | SOUT -> T1IN, T1OUT = TX_OUT; RX_IN -> R1IN, R1OUT -> SIN; the second channel not used (T2IN and R2IN to GND) |
| JP6 | 2 x 3 header, "TX/RX" ("TX PIN" until 2026-11-23) | the null-modem block, as the YACC1 card's JP1: shunts on 1-3 and 2-4 = the card sends on DE-9 pin 2 and hears on 3 (a straight cable to a PC or a USB adapter); 3-5 and 4-6 = sends on 3, hears on 2. Both settings are drawn on the silkscreen beside the block (the last section before "Board") |
| J2 | DE-9 socket, right-angle | pins 2 and 3 through JP6, 5 and the shell to GND, the others open. The footprint is KiCad's own for a right-angle socket with the pin pattern of the YACC1 I/O card's (built, V1.1): pins 2.77 mm apart in rows 2.84 mm apart, mounting holes 25 mm apart |
| JP7 | 1 x 2 header, "UART INT" | fitted: the UART's INTR (through a gate of U9, open collector; U23C, open drain, since 2026-11-25) pulls the bus -INT low. Open as set |
| C18-C21 | 0.1 uF | U20, U21, U22, X1 |

What changed in the card that was there: the DS12885's CS (U13 pin 13), tied low until now, is SEL_UART; U11's second
flip-flop and one of U9's four spare gates, both unused until now, make the UART's read strobe and invert its INTR;
RN1's pin 8 pulls that interrupt line up. Nothing else.

### One port pair for two chips

The 1802 has seven ports, and System-5 uses 2 and 3 (IDE), 4 (this panel) and 6 and 7 (the clock); 1 and 5 are left,
which are not a pair. So the UART shares the clock's pair (JP4, set to 6 and 7), the way Mike Riley's ELF2000 puts its
UART, clock and disk behind one select register. The DS12885 uses seven bits of the byte written to the address port
(00-7F) and ignores the eighth; that eighth bit picks the chip. U22 holds it, with the same strobe and at the same
moment as the DS12885 holds its own copy (RTC_AS, as TPB ends):

- bit 7 = 0: the DS12885, as before. HBIOS v1.0.8's clock driver writes plain register numbers and needs no change
  (its test on the gate-level machine passes on this netlist).
- bit 7 = 1: the UART, register = bits 2-0 (80-87).

A UART with a jumper block of its own would need a fourth 14-pin chip for its strobes and a free pair of ports that
the machine does not have; if Ken wants it anyway, it is a small change.

### The read strobe: why the UART does not use the clock's

The clock's read strobe is "this port, and -MRD high": RTC_RD = NOR(RTCD_L, MRD_H). That is how RCA's own parts
tell an INP from an OUT, and it has a wrinkle (CDP1802 data sheet, figures 10 and 11): the N lines carry the port
number from the first clock of the cycle, but in an OUT the 1802 takes -MRD low only a clock and a half later.
For that clock and a half an OUT looks like an INP:

```
clock          0    1    2    3    4    5    6    7    0
OUT 7   N      ___/=================== 7 ==================\___
        -MRD   ~~~~~~~~~~\__________________________________/~~
        RTC_RD ___/~~~~~~\_____________________________________     a read strobe that should not be
        RTC_WR ____________________________________/~~~~\______     TPB: the write
INP 7   N      ___/=================== 7 ==================\___
        -MRD   ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        -MWR   ~~~~~~~~~~~~~~~~~~~~~~~~~~~~\_________/~~~~~~~~~~     the 1802 writes the byte to memory
        RTC_RD ___/~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\___
        -RD    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\_______________/~~     the UART's, from U11B
```

A DS12885 does not mind being read for a moment before it is written (only its register C changes when read, and
nobody writes that one). A 16550 does: a write to THR (register 0) would first read register 0, which is RBR, and a
read of RBR takes the received character out. Every character sent would throw one away.

So the UART's -RD is the !Q of U11's second flip-flop, used by its two asynchronous inputs alone: -MWR (the bus's
-MRW) on its preset, RTC_RD on its clear. -MWR goes low only in a cycle that writes memory, and of the cycles in
which RTC_RD is high only an INP does. !Q goes low when -MWR falls in an INP of the data port (clock 5) and stays low
after -MWR rises, until the port's select goes away at the end of the cycle: the 1802 has the data on the bus for the
second half of the cycle, through its write to memory and past the edge where it latches D. With RTC_RD low, the clear
holds !Q high; with both inputs low (a memory write anywhere else) a 74HCT74 drives both outputs high, so !Q stays
high then too. `tests/test_hw.py` (`test_serial_port_read_strobe`) runs every port in both directions through the
gates and checks each phase.

The same wrinkle makes the 74HCT244 put the toggles on the bus for that clock and a half at the start of an OUT 4
(the IN and OUT ports being the same number). Nothing else drives the bus then, so it does no harm: it is what a
CDP1852 pair does on any 1802.

**Left as it was, for Ken to decide:** the clock still gets RTC_RD_L with the early pulse. Giving the DS12885 the new
strobe as well (its DS = UART_RD_L; each chip's own select decides which answers) would take that pulse away and
free U5's third gate. It is one line in `gen/netlist.py`.

### The strobes against a 16550's limits

From TI's TL16C550C data sheet (SLLS177I, section 5.7, read on 2026-11-20; older 16550s such as the PC16550D ask for
two to three times as long), with the 1802 at 2 MHz, one clock = 500 ns:

| | The chip wants | The card gives |
|---|---|---|
| Write strobe (WR2, pin 19, active high) | 40 ns or more | TPB of the OUT: 500 ns |
| Data valid before the strobe ends (the chip takes the byte on its trailing edge) | 15 ns | the memory has had the byte on the bus since early in the cycle |
| Data held after the strobe ends | 5 ns | about 200 ns: -MRD stays low for half a clock after TPB |
| Read strobe (RD1, pin 21, active low) | 40 ns or more | clock 5 to the end of the cycle: about 1.5 us |
| Data on the bus after the strobe starts | within 45 ns | the 1802 writes it to memory at clock 7, 1 us later, and takes it into D after that |
| Register and chip select steady round either strobe | 7 ns before, 20 ns after | held in U22 from one OUT to the address port until the next |
| MR (active high) | 1 us | as long as -RESET is low |

The other write and read inputs are tied to their idle levels, as the data sheet asks: WR1 (pin 18) high, RD2 (pin
22) low. ADS low makes the chip follow A0-A2 and its selects directly. A read of the receiver buffer takes the
character out ("DR is cleared by reading all of the data in the receiver buffer register or the FIFO"), which is why a
stray read strobe matters.

### The layout

- **7.50 x 4.00 in (190.5 x 101.6 mm)**, 1.75 in longer; the whole panel (toggles, bit LEDs, displays, Q, PWR, INPUT,
  the name) moved out with the front edge, and JP5 kept its place.
- **J2 at the top edge as drawn**, which is the left side with the card standing in the bus, seen from the parts side;
  past the 3.00 in card-guide strip. It faces off the board: its mounting holes 10.22 mm from the edge, as on the
  YACC1 I/O card, so its flange is 0.7 mm inside the edge and its shroud beyond it.
- The MAX232 lies behind J2 with its line pins towards it and its four capacitors on the other side; JP6 beside it,
  under J2's pins 2 and 3 (behind an edge connector is as near the edge as a jumper can be there; the YACC1 card has
  its own in the same place). The UART stands below, D0-D7 on its bus side, with its select latch and its oscillator
  on its left, the oscillator beside XIN. JP7 at the bottom edge.
- Two layers still. Two things are drawn by `gen/make_board.py` and locked, as the displays' +5V rail already was;
  everything else is Freerouting's. (1) The six short links between J2, JP6 and the MAX232: each signal sits on two
  pins diagonally across JP6's middle column, and Freerouting left J2's pin 2 open on two seeds of three. (2) The
  serial block's +5V, 0.5 mm on the back: C19, the MAX232 and C24, down to a rail under the MAX232's capacitors from
  which C20, U22, U20 and C18 hang; U20's tied-off inputs down its own pin column; C21 and the oscillator. Without
  it every seed tried left one to four +5V links open. For the same reason the MAX232's unused T2IN is tied to GND
  (the YACC1 card ties it to +5V): it sits in the middle of the chip's line side.

### In the emulator

`software/s5emu/s5emu/uart.py` is the 16C550 as behaviour (registers, DLAB, loop mode, the receive and THR-empty
interrupts; no time: a character written is sent at once). The netlist card (`hw.NetlistIOPanel`) plays it on its own
pins as the gates drive them (CS0, WR, -RD, A0-A2, MR, INTR), and since then runs each INP and OUT in the
order the 1802 makes it (N first, then -MRD; -MWR; TPB), which is what shows the early pulse. The fast machine
(`machine.IOPanel`) has the UART on ports 6 and 7 the same way. `serial_in()` / `serial_out()` on the netlist card,
`uart.receive()` / `uart.sent()` on either, are the line. Tests: four in `tests.test_hw.IOPanel` (the shared ports,
the read strobe, the interrupt and reset, and a program on CPU Rev D that echoes the line), one in `tests.test_machine`.

### Not done

- No BIOS support: HBIOS's serial entries are stubs. A driver (and perhaps a console on the serial line) is the next
  step if the port stays.
- No TTL-level header beside the DE-9 (the YACC1 I/O card V1.2 has one for a USB cable). Easy to add.
- No modem lines on the DE-9; the UART's inputs are tied off, so software that waits for CTS will wait for ever.
- The emulator does not pass the card's -INT on to the 1802 (nor the clock's): the interrupt is tested at the card.
- Not through `s5emu.timing`, which does not know the panel: the strobes were set against the data sheet by hand
  ("The strobes against a 16550's limits", above).

## The front panel's header, and the DMA request put right (Ken, 2026-11-22)

### The header

Ken, 2026-11-22: "I want to add ability to have a front panel if system is ever put in a case. This will mean bringing
all IO switches, LEDs, and TIL311 signals out to a ribbon cable connector"; "dont forget q line"; "and cpu status leds
for mode". Asked how the connector should go on this card, he chose "Lengthen to 8.00 in" with one 50-pin header at
the front edge.

So the card is **8.00 x 4.00 in (203.2 x 101.6 mm)**, still two layers. Every part stayed where it was; the new
0.5 in strip beyond the displays holds **J3**, a keyed 2x25 header, upright, pin 1 at the top as drawn. A straight
50-way ribbon joins it to the front panel's J1, pin n to pin n. `tools/s5panel.py` is the one pin map for both
boards, and the front panel's `DESIGN.md` has the table.

What the card adds for it:

| Part | What it does |
|---|---|
| J3 | the ribbon: the address and output latches' outputs, the data lines, the Q LED's sink, INPUT, the bus -RESET, -PAUSE and -DMAIN, +5V on four pins and ground on eight |
| RN3, 10k x8 | pulls the data lines SW0-SW7 down. The front panel's toggles switch a line to +5V through 1k or leave it open |
| U9D | ROM_LED_L = NAND(-VMA, -VMA), open drain: sinks the front panel's ROM LED while the CPU card's EPROM answers (U23D since 2026-11-25) |
| J1 | now takes -VMA and SC0 from the bus as well |

No chip was added. U9 changed type (below), and its fourth gate is the ROM LED's (U23D's since 2026-11-25).

**The card's own toggles and the front panel's.** The card's data toggles sit between +5V and ground. If they are
fitted and a front panel is plugged in too, the card's win and nothing is harmed (the front panel's reach the line
through 1k). A card built for a front panel leaves SW1-SW8 out. RUN, LOAD and INPUT work together on the two boards:
either one pulls its line low, so both RUN toggles must be at RUN for the machine to run. With the displays fitted
on both boards the twelve TIL311s take about 2.2 A of the backplane's 3 A: fit them on one.

J3's +5V pins are joined to the displays' supply rail by tracks drawn in `gen/make_board.py`, locked, as that rail is.

### The DMA request lasted too long

Reading the 1802's data sheet for the front panel's RESET showed a fault in this card as it was drawn. It had passed
every check, the emulator's too, and would have shown only on the built card.

**The fault.** In LOAD mode a press of INPUT sets REQ, which pulled -DMAIN low. REQ was cleared by ACK, clocked when
-MWR rises at the end of the DMA cycle's write. But the 1802 samples its DMA request at clock 7 of every cycle, the
DMA cycle's own too, and -MWR rises just after that (data sheet, figure 4; figure 12 shows the request gone by then
for a single cycle). So the request still stood when the 1802 looked again, and a second DMA cycle followed: **the
toggles' byte written at two addresses for every press.**

**Why the emulator did not show it.** Its model ran one DMA cycle for a press and never asked whether the request
was still there at clock 7. It does now (`NetlistIOPanel.s2_begin()`, `s2_end()`), and the old circuit is kept as
the revision `A-req` so that a test shows the two cycles (`IOPanel.test_the_request_as_first_drawn_made_two_cycles`).

**The fix.** The COSMAC ELF drops its request with the state code as the DMA cycle starts, and so does this card
now. SC0 is on the 36-pin bus; in LOAD mode it is high in every idle cycle and low in a DMA cycle.

    -DMAIN = NAND(REQ, SC0)        U9B, open drain

The line is low while REQ is set and the 1802 has not yet started the DMA cycle, and is let go as SC0 falls, more
than a microsecond before clock 7 at 2 MHz. REQ itself is still cleared by ACK as before: DRIVE, which keeps the
toggles on the bus through the write, needs it that long.

U9 was a 74HC05 (six open-collector inverters, three used). It is now a **74HC03** (four open-drain NAND gates),
all four used: INPUT's flag, the DMA request, the UART's interrupt, the ROM LED. RN1's spare resistor pulls SC0 up, so
the gate's input is defined with no CPU card in the bus (the bus Rev D has no resistor on SC0). Since 2026-11-25 U9C and
U9D are REQCLR_L and DRVL_L, and the UART's interrupt and the ROM LED are on U23C and U23D ("The power-up states of REQ
and DRIVE", below).

### The address display in LOAD mode

The same reading turned up a small thing about the address display (2026-11-18). The data sheet says TPA is left out
of the idle cycles of LOAD mode. The high byte's latch (U18) is clocked by TPA, so in LOAD mode the two left digits
change only when a byte is loaded, and show that byte's page; the two right digits follow R(0) all the time. After
the byte at 00FF goes in the display reads 0000 until the next byte. Not changed.

## The card's own RESET button, and the serial port's settings on the silkscreen (Ken, 2026-11-23)

### RESET

Ken, 2026-11-23: "the IO card also needs a reset in case front panel is not installed."

The card had RUN/RESET, a toggle that holds the bus -RESET low. That is a plain reset: it starts again whatever ran
before, the loaded program if there is one. What it could not do is bring HBIOS back after a load; for that one had
to reach the CPU card's switch. **SW12 RESET** is a push-button for a boot reset, the same as the front panel's.

| Part | What it does |
|---|---|
| SW12 | pressed, it puts +5V on BTN_H |
| R4, 10k | holds BTN_H low otherwise |
| U23A (74HCT03 since 2026-11-25, a 74HC03 until then; open drain) | pulls -RESET low while BTN_H is high and -PAUSE is high |
| U23B | pulls -DMAIN low on the same condition |
| C26 | U23's 0.1 uF |

-RESET and -DMAIN low together, with -PAUSE high, is a boot reset (`docs/manual/bus.md`): the CPU card clears its
LOADED flag, and when the button is let go the machine starts in the EPROM.

**It does nothing while LOAD is on.** Both gates take the bus line -PAUSE as their second input. In LOAD mode a low
-DMAIN is a DMA request, and the button must not make one.

**No debounce.** A bouncing boot reset is still a boot reset, and the CPU card's reset chip holds -RESET low for
150 ms after the last release, by which time -DMAIN is high again. The CPU card passes -DMAIN to the 1802 only in
LOAD mode, so the bounce cannot write to memory.

So there are now two things named RESET on the card, and they differ:

| Control | Lines | What starts afterwards |
|---|---|---|
| RUN/RESET toggle, at RESET | -RESET | what ran before: the loaded program, or HBIOS |
| RESET button | -RESET and -DMAIN | HBIOS, always |

Ken, 2026-11-23, asked whether one of them should have another name (`BOOT` was suggested for the button): both keep
RESET, here and on the front panel.

The button was in the bottom corner of the front strip, under J3 (as drawn on 2026-11-23; since 2026-11-26 it is in the
top corner, above J3: "The RESET button moved away from INPUT", below). U23 stands between the toggle column and the Q and
PWR LEDs' resistors, which moved 3 mm towards the LEDs. U23's other two gates were spare (the UART's INTR and the ROM LED since 2026-11-25).

### The serial port's settings (as first drawn; redrawn that night, next section)

Ken, 2026-11-23: "can you add more detail to silkscreen for IO card settings for serial port."

The port's three jumper blocks had their names and little more. A block of seven lines now stands in the free patch
under RN3, between the UART and the toggles:

    SERIAL PORT (16C550)
    J2 AS SET: 2 TX 3 RX 5 GND
    JP6: TX ON PIN 2 OR PIN 3
    JP4: PORTS 6 + 7 (AS RTC)
    REG N: OUT 6 = 80+N, PORT 7
    DIVISOR 12 = 9600 BAUD
    JP7 FITTED: INT ON -INT

| Line | What it tells the person setting the card up |
|---|---|
| J2 AS SET | the DE-9's pins with JP6 as it is shipped: the card sends on pin 2, hears on pin 3, ground on 5 |
| JP6 | the block that swaps the two; the `2` and `3` printed over it show which pair of shunts is which |
| JP4 | the port pair, shared with the clock: address port 6, data port 7 as set |
| REG N | how a program reaches UART register N: write 80+N to port 6, then read or write port 7 |
| DIVISOR 12 | the divisor latch value for 9600 baud with the 1.8432 MHz can (3 is 38400) |
| JP7 FITTED | a shunt puts the UART's interrupt on the bus -INT |

JP4 kept its short title, `JP4 RTC`, for want of room on one line; since that night it is `JP4 RTC` / `+ UART`, on two.

### What else moved on the silkscreen

The new parts pushed four older texts about (`python3 tools/kicad/silkdiff.py` against the board before the button
lists every one):

| Text | What happened | Why |
|---|---|---|
| `INPUT` | moved 11.3 mm, from above its button to below it (card standing) | R4 stands where it was; it now sits under its button as `RESET` does under its own |
| `J3 FRONT PANEL` | moved from the header's pin 50 end to its pin 1 end | the RESET button took its corner |
| `50` | new, at the header's pin 50 end | there was no room for it while the name stood there |
| `R2 1k`, `R3 1k` | 3 mm, with their resistors | room for U23 |
| the name line and `cottageworker.com` | 14.5 mm along the bottom edge | room for C26 and the buttons |

**The `1` at J3's pin 1 was lost for a morning.** The two pin numbers were placed after the header's name and were
allowed to be left out; when the name moved to the pin 1 end, the `1` found no room and was dropped without a word.
The first report of this build did not list it, nor the moves of `INPUT` and the name: the pcb-check session found
all three by comparing the two boards. `gen/make_board.py` now places the two numbers first and stops if either has
no room; the card was built again (the name 1.5 mm to the side, the `1` where it had been, the copper the same track
for track), and `tools/kicad/silkdiff.py` now exists to list such changes after any build.

### Built and checked

`gen/route.py` seed 3 (seeds 0 and 2 leave two links open, 1 one): 91 parts, 3253 track segments, 164 vias. The older
check passes (DRC 0 errors, netlist 140 of 140). A full build took 69 minutes, twice (Freerouting's optimization 66
to 67 of them).

The second build, for the `1`, gave the same copper: the same 3417 tracks and vias, and in the order files the same
pads, tracks and pours on both copper layers, the same masks, outline and holes; the front silkscreen differs by the
name's 75 strokes and the five of the `1`.

`pcb-check --tests` at `bf641d1` (2026-11-23, pcb-check `1133958`; before the `1` was put back, at `a3c0213` with
pcb-check `d5ef4ad`, the same result): **no failures, 1 warning.** The warning is the
one the card had before: J2, the DE-9, is on the side edge and begins 65.6 mm from the front edge, 5.6 mm past the
60 mm within which the check expects an outside connector (LAYOUT). **Ken accepted it on 2026-11-23**: the connector
stays where he put it, the check's limit for this card is not raised, and the warning stands in every report.
Its LABELS line passes: every reference and value on the silkscreen, and every text clear of the parts, the legend
included. A note asks to confirm that -DMAIN, -RESET and ROM_LED_L, which this card only pulls low, are pulled up
elsewhere: the first two by 10k resistors on the bus Rev D (RN2) and again on CPU Rev D (RN1), and -RESET by the CPU
card's reset chip as well; the third by the front panel's ROM LED and its resistor.

The pcb-check session ran the card again at `26e17ea` with the same result, compared the second build's order zip
with the first's shape for shape (only the front silkscreen differs), and planted 17 wiring faults in copies of this
card's netlist and 11 in the front panel's, each run through the card's own test line: all 28 were caught.

### In the emulator

`NetlistIOPanel.set(reset=)`, the debugger's `panel reset`; the fast machine has the button too. Since the same day
the model plays every switch on the card as the netlist wires it (`hw.switch_contact`): a closed contact sets its net
to the level the switch's other pin gives it. Before that the model set the net and level it knew, and a switch
wired to the wrong rail passed every test; the pcb-check session showed it by running this card's tests on damaged
copies of its netlist (SW12 between ground and BTN_H was not caught). It is caught now, by the card's two reset
tests and by `IOPanel.test_the_switches_are_played_as_the_netlist_wires_them`.

## RUN/RESET turned, and the serial port's settings as pictures (Ken, the night of 2026-11-23)

Two points Ken had noted that day for this Mac ("log i will change on other machine"), both on his word that night
("1 yes, 2 yes as suggested").

**RUN/RESET: up is RUN.** The card's toggle had RESET at the front-edge end (up with the card standing) and RUN toward
the bus; the front panel's is up for RUN, the ELF's way, and LOAD and the data toggles agree on both boards (up is LOAD,
up is 1). SW10 is turned end for end (`gen/make_board.py`: rotation 270 where the other nine have 90). The M9040P's
origin is its middle pin, so the body stayed where it was and pins 1 and 3 changed places. The netlist, the emulator and
the tests are unchanged (pin 1 = -RESET, pin 2 = ground: the labels and the model read the pads).

**The serial port's labels.** Each setting stands at its own jumper now:

| Where | What it says |
|---|---|
| JP6 `TX/RX`, the 2 x 3 block by the DE-9 | its two settings as pictures, the way the block stands with the card in the bus: the block's outline, its six pins, the two shunts outlined where they go. Shunts on the upper two rows (3-5, 4-6): `PIN 2=RX` / `PIN 3=TX`. On the lower two (1-3, 2-4): `PIN 2=TX` / `PIN 3=RX`. The pins are the DE-9's, and TX is what the card sends |
| J2 `RS-232` | its name alone |
| JP4 `RTC` / `+ UART` | the port pair, the clock's and the UART's |
| JP7 `UART INT` / `FIT = -INT` | a shunt puts the UART's interrupt on -INT |
| the note under RN3 | four lines at 1.0 mm (seven at 0.8 mm before): `SERIAL PORT (16C550)` / `REG N: OUT 6 = 80+N,` / `THEN PORT 7 (JP4: 6+7)` / `DIVISOR 12 = 9600 BAUD` |

Ken's words on the block, in order: "for serial port, i believe the 2x3 decides if de9 connector 2 is rx or tx and de3
connector 3 is tx or rx (null modem function) I would like that clearer on silk screen"; of a first version in words
("UP PIN 2=RX 3=TX"), "the problem is it is not clear where jumpers go for each more (null modem or not null modem)
there is no need to show the words null modem but it should be clear how to confgure the jumoers"; of the pictures,
"much better so both sys5 and yacc1 io card pls"; and of the DE-9's pins numbered at the connector, "we don't need pin
2,3 5 it is cluttering" (they are gone). The YACC1 I/O card V1.2 has the same pictures (its JP1).

`shunts()` in `gen/make_board.py` draws the pictures, placed like any label: the build stops if one has no room.
`tools/kicad/silkdiff.py` against the board before: 15 texts changed: the labels
of the table, `RUN` and `RESET` (exchanged), and `C18 0.1uF`, 2.0 mm along.

### Built and checked

`gen/route.py` seed 1 (5 leaves two +5V links open; 0, 2, 3, 4 not judged): 91 parts, 3093 track segments, 147 vias.
preorder_check --layers 2 PASS (ERC 0, DRC 0 errors and 0 warnings, parity 0, 140/140; the redrawn schematic in the book,
JP4's and JP6's values `RTC + UART` and `TX/RX`). A full build took about 70 minutes (Freerouting's optimization 59).

**`pcb-check --tests` on that board, before its commit** (2026-11-24, 00:20 to 00:23, pcb-check `ac554f4`): **no failures**; the LAYOUT
warning Ken accepted on 2026-11-23 (J2, the DE-9, on the side edge) and COMMITTED, which goes with the commit; the card's
emulator tests pass. `make qa-quick`: OK. Nothing of it has run on hardware.

## The power-up states of REQ and DRIVE (Ken, 2026-11-25: "fix both power-up faults in one new route")

Ken's answer, through the Product Manager, to a fault the bus Rev D test found (`software/busdrv/busboard.py`).

**The fault.** A 74HCT74 comes up in either state, and nothing put REQ (U10A) or DRIVE (U11A) in a known one. REQ's clear
was ACK_L alone, and ACK is held clear while INPUT is up. REQ up as 1 kept DRIVE set whenever -MRD was high, so the '244
put the toggles on D0-D7 in **every memory write**, against the 1802; -DMAIN was low whenever SC0 was high, and a press of
INPUT in LOAD mode made no DMA cycle. The same happened with a request still pending as LOAD was turned off. DRIVE up as 1
put the toggles against the 00 the 1802 drives in RESET, until the first -MRD.

**The change.**

    REQCLR_L    low outside LOAD mode: NAND(LOAD_L, LOAD_L), U9C, open drain
                low while ACK is set: D1, a Schottky, its cathode on ACK_L (U10B), its anode on REQCLR_L; R5 3.3k to +5V
                U10A's -CLR
    DRVL_L      NAND(DRIVE, LOAD_H), U9D, open drain; R6 3.3k to +5V
                U6A's input, in place of DRIVE_L: a DMA puts the toggles on the bus in LOAD mode alone

U9C and U9D were the UART's INTR and the ROM LED, which went to U23C and U23D, the two spare gates of the same type: the new
gates stand beside U10, U11 and U6, and J3 and the UART are nearer U23. One diode and two resistors more: 94 parts. No
other net changed. **U23 is a 74HCT03** (Ken, 2026-11-25: "Yes, with the HCT03"), U9 a 74HC03 as before: a 16C550's INTR is
only promised at 2.4 V high (TL16C550C, PC16550D), and a 74HC03 needs 3.15 V where a 74HCT03 needs 2.0 V. TI's CD74HCT03
sheet (SCHS414) has the 74HC03's pins, open-drain outputs, VIH 2.0 V and VIL 0.8 V at 4.5 to 5.5 V, VOL 0.33 V at 4 mA (to
85 degrees C), input 10 pF, input rise at most 500 ns at 4.5 V. Its other inputs (BTN_H, -PAUSE, -VMA) are 0 and +5V.

**D1's drop, and the resistor** (BAT85 / BAT85S in a DO-35; Vishay BAT85S, document 85513 Rev. 2.2: at most 240 mV at
0.1 mA, 320 mV at 1 mA, 400 mV at 10 mA, at 25 degrees C). R5 is 3.3k: (5.25 - 0.5 V) / 3.3k = 1.44 mA, where the diode drops at
most 0.335 V (between its 1 and 10 mA figures). ACK_L is at most 0.33 V at 4 mA (TI SN74HCT74, SCLS169G, at 4.5 V, to 85 degrees
C; 0.1 V at 20 uA), so REQCLR_L is at most 0.33 + 0.335 = **0.665 V against the 74HCT74's 0.8 V: 0.135 V to spare**; about 0.09 V
with the diode at 0 degrees C (its drop then some 2 mV a degree more: from memory, not the sheet). U9C alone: 0.33 V at 4 mA
(TI SN74HC03, SCLS077F). High: the HC03's output leaks at most 5 uA and the HCT inputs 1 uA, so 3.3k keeps it at +5V. Rise: about
45 pF (the HC03's output, the diode's 10 pF, the input's 10 pF at most, the track: an estimate) makes 0.15 us, **0.33 us from 10
to 90 %, against the 500 ns the HCT74's sheet allows**. The choice (2026-11-25, 4.7k first): at 4.7k the low has 0.15 V to spare
and the rise 0.035 us (0.465 us; with 60 pF it would be over the limit); at 3.3k 0.135 V and 0.17 us (0.44 us at 60 pF). R6 is
3.3k too. A clear needs only to be gone before the next INPUT edge (setup 0 ns), and U4's Schmitt and C1 keep those
milliseconds apart.

**What it does not change:** power up with LOAD already on. REQ and CPU Rev D's DMA_ARMED then have no state (the panel
sees LOAD mode at once), so INPUT may load nothing, or the toggles' byte may be written by itself; LOAD off and on mends it.
The manual says to power up with LOAD off (`docs/manual/bus.md`).

**In the emulator:** `software/s5emu/s5emu/logic.py` has a diode onto a pulled-up net (`WiredDiode`), and
`software/busdrv/test_busboard.py` (`PowerUp`) runs the five cards and the program on the bus Rev D's netlist from every
flip-flop and latch at 0, at 1, REQ alone, DRIVE alone, both, and unknown: no bus fight in the reset, and the program runs.
The same test on the card as it was drawn (its two old connections put back) fails from each of the four states with one
of them at 1.

**Layout:** D1 between U9 and U10, R5 between U10 and U11, R6 between U3 and U9, upright in the gaps of the
middle row. The labels of U3, U9, U10, U13, C11 and C12 moved (U13's to its bus side, C12's in two lines beside it, so that each
line stands by its own part); no other part or label did.

### Built and checked

`gen/route.py` seed 1 (3 leaves one +5V link open, at C10; the others not judged), routed as placed on 2026-11-25: 94 parts, 3132
track segments, 146 vias, two layers. preorder_check --layers 2 PASS (ERC 0, DRC 0 errors and 0 warnings, 0 unconnected, parity
0, 142/142; the redrawn schematic in the book). A full build took 79 minutes (Freerouting's optimization 75).

`tools/kicad/silkdiff.py` against the card before (`84f1bd1`): 181 texts then, 184 now. New: `D1
BAT85`, `R5 3.3k`, `R6 3.3k`; `U23 74HCT03` in place of `U23 74HC03`; `C12 0.1uF` on two lines; moved: `C11 0.1uF`, `U3 74HCT244`,
`U9 74HC03`, `U10 74HCT74`, `U13 DS12885+`.

**`pcb-check` at `57dce4a`** (2026-11-25, pcb-check `fe2c0b3`, without `--tests`): **no failures, 1 warning**, LAYOUT, the one Ken
accepted on 2026-11-23 (J2, the DE-9, on the side edge). COPPER 142 nets, no shorts or opens; INDEPENDENT the same by its own
method; DAMAGE 13 of 13. The card's tests on this board are QA's to run. Nothing of it has run on hardware; not ordered.

## The RESET button moved away from INPUT (Ken, 2026-11-26: "Yes, move it too")

As on the front panel the same day: SW12 RESET stood beside SW9 INPUT in the front strip's bottom corner (as drawn),
too easy to hit when pressing INPUT. It is now in that strip's top corner, above J3, the button centred at
(206.85, 18.0), about 85 mm from INPUT; with the card standing connector down both are on the front edge, INPUT at its
right end, RESET at its left. Its RESET label at 270 beside it. R4 (BTN_H's 10k) and U23 stay where they were (Ken's
"Yes, route it" with R4 there); no circuit change. Silkscreen (`silkdiff.py`): 184 texts, three moved: RESET with its
button, `J3 FRONT PANEL` from the header's pin 1 end to its pin 50 end, `R4 10k` 7.4 mm. Routed again, seed 1 as
before (12:52 to 13:48, Freerouting single-threaded and niced beside other work): 3321 track segments, 145 vias; ERC 0,
DRC 0 errors and 0 warnings, nothing unconnected, parity 0, netlist 142 of 142; `tools/preorder_check.py` PASS.
**`pcb-check --tests` at `6f4359d` (pcb-check `4e5bf24`): no failures, 1 warning**, the accepted LAYOUT one (J2, the
DE-9 on the side edge; the moved button is not named); the copper rebuilt by two methods, which agree; 13 of 13
faults planted in copies of the zip noticed; the card's tests (IOPanel, the front panel, power-up) pass.

## Board (2026-10-30): `gen/make_board.py`

- **5.50 × 4.00 in** (5.75 since 2026-11-18: above), J1 = `s5io:C36` (as CPU Rev D), its pins named on the silkscreen; the card-support strips kept free.
- **Front panel as on Ken's YACC1 IO card** (Ken, 2026-10-30): eight vertical M9040P toggles in a column (BIT 7 at the top,
  each labelled 0 / 1 at its ends), then RUN/RESET (RUN / RESET) and LOAD (OFF / LOAD); INPUT push-button beside LOAD;
  the eight bit LEDs (7 … 0), Q and PWR in a column at the front edge with their resistors; the two TIL311s side by side in
  the bottom-right corner (U7 bits 7-4, U8 bits 3-0). The HTIL311A footprint's drawing is on F.Fab in this copy (it ran over
  its pads on the silkscreen). U1 ('138) sits beside N0-N2 at the bottom of the connector.
- **2 layers**, Freerouting (869 segments, 21 vias), GND pours both sides. `preorder_check --layers 2`: **PASS** (ERC 0,
  DRC 0, parity 0, netlist 64/64, bypass caps 0.1", schematic redrawn). Not ordered. That is the older check,
  `tools/preorder_check.py`; before an order the board has to pass `pcb-check` (every system since 2026-11-06;
  `hardware/BUILD-RULES.md`, section 2).
- To check before an order: the M9040P toggles still to be had (or a pin-compatible vertical SPDT toggle: 3 pins on 4.7 mm),
  the switch lever direction against a real part (labels assume the lever closes the common to the far end), Ken's look at
  the pictures.
- **Emulator (2026-10-30):** `python3 -m s5emu --hw --cpu-rev D --panel A` runs the card from its netlist: OUT 4 / INP 4,
  INPUT on -EF1, RUN/LOAD, one DMA IN per INPUT press. A 9-byte program toggled in ELF-style (RUN off, LOAD on, toggles +
  INPUT per byte; LOAD off; RUN on) runs from 0000 and copies the toggles to the LEDs and TIL311s, with no bus events; the
  CPU card's RESET/RUN then boots HBIOS again (tests/test_hw.py `IOPanel`, 4 tests; all 30 pass).
