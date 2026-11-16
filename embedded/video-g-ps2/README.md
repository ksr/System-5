# video-g-ps2 — the PS/2 controller of VIDEO-G 1.0

The firmware for the ATmega328P on **both** VIDEO-G boards (`hardware/video-g/DESIGN.md` sections 4 and 5; netlists
`hardware/video-g/kicad/text-1.0/gen/netlist.py` IC10 and `.../gfx-1.0/gen/netlist.py` IC11). One sketch: a strap on
PD7 makes it a **keyboard** controller on the TEXT board and a **mouse** controller on the GFX board. Written
2026-11-01 from YACC1-D's `embedded/video-ps2` (the controller of YACC1's video card V2.0, revised after its design
reviews; copied, never modified).

**Status: not yet run on hardware.** It compiles for the Uno target with arduino-cli 1.5.1 / AVR core 1.8.8 with no
warnings (`--warnings all`): **6,342 bytes of flash (19 %), 385 bytes of RAM (18 %)**; with `KEYS_VT100 1`, 6,486 /
419. A host co-simulation (`sim/`, below) runs the sketch against bit-level PS/2 keyboard and mouse models, the latch
and READY flip-flop, and a CPU doing INP cycles; all its checks pass.

## The two modes

| PD7 (Arduino D7) | Board | Mode |
|---|---|---|
| open (read with the internal pull-up: 1) | TEXT (IC10) | keyboard |
| R6 4.7k to GND (0) | GFX (IC11) | mouse |

Each board has its own ATmega328P (16 MHz, Uno bootloader, FTDI header) with one PS/2 jack: clock on PD2 (INT0), data
on PD4, 4.7k pull-ups on the board. Both hand bytes to the CPU the same way: the byte on MD0-MD7, then a low pulse on
LDDATA (PD6, idle high, 10k pull-up), whose rising edge clocks a 74HCT374 and sets **READY** (KEY-READY on TEXT,
MOUSE-READY on GFX: a 74HCT74 half with D = 1). The CPU's INP clears READY at TPB; -RESET clears it too. The firmware
sees READY on PB2.

The strap is read twice at start: once with the pull-up (open = 1), and once after charging the pin through the
pull-up and turning the pull-up off for 3 us (R6 empties it at once; an open pin keeps its charge). Either reading 0
means mouse mode. R6 is 4.7k (2026-11-02; first drawn as 10k, which against the 20-50k internal pull-up left the pin
at 0.8-1.7 V, above the AVR's guaranteed 0 of 1.5 V); with 4.7k the pin sits at 0.4-0.95 V. The second test stays as
belt and braces.

### Keyboard mode (TEXT)

V2.0's keyboard handling: scan code set 2 to ASCII (US layout), Shift, Caps Lock, Ctrl, Num Lock and the keypad. The
firmware drives the three LEDs itself; there is no command path from the CPU. At start (and on the console's `r`) it
resets the keyboard ($FF, then its self-test answer $AA) and sends the LED state ($ED). A keyboard plugged in later,
or one that resets itself, sends $AA: the firmware then clears the Shift/Ctrl state and sends the LEDs again. Keys
typed while the CPU is busy wait in a 63-byte queue.

The CPU's side is the IO card's, unchanged: KEY-READY pulls the bus **-EF** low through a 7416 gate (jumper KBD-EF;
CPU card JP1 row 3 = EF3) and shows on INP 4 bit 0; **INP 1** reads the key. HBIOS's `inchar` (`BN3 inchar`, `INP 1`)
works as it is. After a reset the keyboard is ready in about 1.5 s: Optiboot waits about 1 s after every external
reset (the bus -RESET resets the ATmega too), then the keyboard's own reset takes 0.3-0.75 s. Keys pressed before
that are lost.

### Mouse mode (GFX)

The mouse reports only while **MOUSE-ON** (PB3, the GFX control register's bit 5, OUT 4) is 1, so HBIOS never sees
mouse bytes.

- **MOUSE-ON rises:** V2.0's start sequence: reset ($FF, answered $FA $AA $00), then enable data reporting ($F4). The
  mouse runs at its defaults: stream mode, 100 reports/s, 4 counts/mm, 1:1. Bytes waiting in the receive ring are
  dropped before the reset, and so are any that were held back while the start sequence ran (they are from before the
  reset). The first packets come about 0.5 s after MOUSE-ON rises.
- **MOUSE-ON falls:** disable reporting ($F5), then drop the queue, the receive ring and any part packet.
- **Packets:** 3 bytes, queued only whole. Byte 1 always has bit 3 set: a byte 1 without it is skipped (V2.0's
  resynchronisation). New: a part packet followed by 25 ms of silence is dropped. After a lost byte (a parity error
  on the cable) a stream can stay misaligned while the mouse keeps moving, because Y bytes often have bit 3 set too.
  The 25 ms rule realigns it at the first pause.
- **Hot plug:** a mouse that answers nothing when MOUSE-ON rises is tried again every 2 s while MOUSE-ON stays 1. A
  mouse plugged in (or reset) while running sends $AA $00 and then nothing: the firmware sees that, a part packet
  followed by silence, and starts it again.

The CPU reads TEXT's status port **INP 4 bit 1** (MOUSE-READY), then **INP 7**. The packet layout:

| Byte | Bits |
|---|---|
| 1 | 0 left, 1 right, 2 middle button; 3 always 1; 4 X sign, 5 Y sign; 6 X overflow, 7 Y overflow |
| 2 | X movement (with the X sign: 9-bit two's complement) |
| 3 | Y movement (positive = up) |

```
mwait: SEX R2       ; R(X) points at a scratch byte
       INP 4        ; status -> M(R(X)) and D
       ANI 02H      ; MOUSE-READY?
       BZ mwait
       INP 7        ; the byte (clears MOUSE-READY at TPB)
```

**Turning the mouse on again:** when MOUSE-ON falls, a byte already in the latch stays there (MOUSE-READY stays 1;
only INP 7 or -RESET clears it). So before setting MOUSE-ON, read INP 7 while INP 4 bit 1 is 1, and start counting
packets at a byte with bit 3 set.

**Throughput:** the firmware loads bytes at least 1 ms apart (the read guard, below), so a packet needs 2 ms or more.
A moving mouse sends up to 300 bytes/s. If the CPU reads more slowly than that for long, the 63-byte queue fills and
whole packets are dropped.

### Rules for both modes

- **INP 1 / INP 7 only after READY was seen 1** (EF3, or INP 4 bit 0 / bit 1). This is V2.0's rule (R2-10). After
  each load the firmware reads READY back. If it did not set, an INP was clearing it, and the same byte is loaded again.
  A program that reads without waiting for READY could clear it inside that check and get the byte twice.
- **The read guard:** READY falls at TPB, but the INP's read enable lasts to the end of that cycle. A pin-change
  interrupt timestamps READY's fall, and the next byte is loaded only 1 ms later. That covers the 1802 at any clock and
  the bus driver's `INP:n#`, which holds TPB high for about 0.3 ms (I2C-stepped). A master that holds one INP longer
  than 1 ms, such as the CPU single-stepped with `CLK:n#`, can see the latch change under its read.

## Codes sent (keyboard mode)

| Key | Byte |
|---|---|
| Letters, digits, punctuation, Space | ASCII, US layout; Shift and Caps Lock as on a PC (Caps Lock + Shift gives lower case) |
| Ctrl + A..Z, Ctrl + @ [ \ ] ^ _ | $01-$1A; $00, $1B-$1F |
| Enter, keypad Enter | **$0D** (CR) |
| Backspace | **$08** |
| Tab | $09 |
| Esc | **$1B** |
| F1 ... F12 | $80 ... $8B |
| Home, Up, PgUp, Left, keypad 5, Right, End, Down, PgDn, Insert, Delete | $90, $91, $92, $93, $94, $95, $96, $97, $98, $99, $9A. The grey keys always send these; the keypad sends them with Num Lock off |
| Shift + any key in the two rows above | the code + $40 ($C0-$CB, $D0-$DA) |
| Keypad with Num Lock on | 0-9 and . |
| Keypad / * - + | / * - + |
| Caps Lock, Num Lock, Scroll Lock | nothing sent. Each toggles its state and LED on the first make (a held key's repeats do not toggle). Num Lock starts off, so the keypad sends the editing codes |
| Alt, AltGr, Windows, Menu, Print Screen, Pause, Ctrl-Break, multimedia keys | nothing |

Ctrl does not change the special codes. Typematic repeat comes from the keyboard: a held key repeats its byte.

**Why these codes.** The old System-5 keyboard was a PS/2 keyboard into an AWC **PAK-VI**. The PIC16F84 on the IO card
(`hardware/io-1861-keyboard/pic-ps2-firmware/keyboard.c`) only receives the PAK-VI's 9600-baud bytes, 8 bits, and
strobes them into the CDP1852 unchanged. Ken's PAK-VI had RX unconnected, so it ran in its default "cooked" mode: ASCII,
with single bytes above $7F for the special keys, as in the table. The table is from AWC's PAK-VIa manual (v1.4, 2003);
Ken's card has the original PAK-VI pinout, whose manual was not found, but AWC describes the VIa as the same chip with a
different pinout and a bigger buffer. Keeping those codes:

1. **Enter $0D, Backspace $08, Esc $1B and Ctrl-C $03 are what HBIOS and Riley's BIOS act on.** Riley's `input` ends a
   line on $0D, deletes on $08 and cancels on $03, and stores anything else, $7F included. HBIOS's `outchar` handles
   CR, LF and BS, and never prints $7F. HBIOS's `brk` (used by the Tiny BASIC build) treats $1B as BREAK. The emulator
   (`software/s5emu`) sends the same $0D, $08 and $1B.
2. **One byte per key suits HBIOS.** `inchar` echoes every byte and `input` stores every byte. A VT100 arrow (V2.0's
   choice) would put three bytes in the line and show "[A". In the BASIC build its leading $1B would also stop the
   program.
3. **It is what System-5 software saw before**, and an 1802 program can test one byte (`XRI 91H`) instead of parsing
   a sequence.

Build option `KEYS_VT100 1` restores V2.0's mapping: Up/Down/Right/Left ESC `[A`/`[B`/`[C`/`[D`, Home ESC `[H`, End
ESC `[F`, PgUp ESC `[5~`, PgDn ESC `[6~`, Delete $7F; nothing for the F keys, Insert or keypad 5; no Shift + $40. A
sequence is queued whole or not at all; its bytes reach the CPU at least 1 ms apart.

**A quirk the old keyboard had too:** HBIOS's `outchar` strips bit 7 before printing (bit 7 of the text RAM is reverse
video), so a special key echoes as its low 7 bits. F9 ($88) moves the cursor back like Backspace, F11 ($8A) scrolls
like a line feed, and Shift + a special key ($C0-$DA) prints @ or a letter. The bytes stored are right. The VIDEO-G
HBIOS could skip echoing bytes of $80 and up.

## Pins

| ATmega328P (DIP pin) | Arduino | TEXT, IC10 (keyboard) | GFX, IC11 (mouse) |
|---|---|---|---|
| PD0 RXD (2), PD1 TXD (3) | D0, D1 | FTX / FRX: FTDI header J5 pins 4 / 5 | FTX / FRX: FTDI header J3 pins 4 / 5 |
| PD2 INT0 (4) | D2 | KCLK: keyboard jack J4 pin 5, R9 4.7k | MCLK: mouse jack J2 pin 5, R4 4.7k |
| PD4 (6) | D4 | KDAT: J4 pin 1, R10 4.7k | MDAT: J2 pin 1, R5 4.7k |
| PD6 (12) | D6 | LDDATA out: IC9 CLK, IC24B CLK; RN2 10k pull-up | LDDATA out: IC12 CLK, IC13B CLK; R3 10k pull-up |
| PD7 (13) | D7 | not connected: keyboard mode | MSTRAP, R6 4.7k to GND: mouse mode |
| PC0-PC5 (23-28), PB0, PB1 (14, 15) | A0-A5, D8, D9 | MD0-MD7 out to the key latch IC9 (INP 1) | MD0-MD7 out to the mouse latch IC12 (INP 7) |
| PB2 (16) | D10 | KREADY in (IC24B Q) | MREADY in (IC13B Q) |
| PB3 (17) | D11 | not connected | MOUSEON in (IC19 Q5, OUT 4 bit 5) |
| PD3, PD5, PB4, PB5 (5, 11, 18, 19) | D3, D5, D12, D13 | not connected | not connected |
| RESET (1) | | MRST: R7 10k, C27 from DTR; bus -RESET through IC23 (7416) | MRST: R1 10k, C21 from DTR; bus -RESET through IC15 (74LS05) |

MD0-MD7 are outputs all the time (only the latch listens). Unused pins are inputs with pull-ups, and so is PB3 on TEXT.
The serial RX pin has its pull-up on, so with no FTDI cable it reads idle.

## Changes from V2.0

| | V2.0 (YACC1 video card) | VIDEO-G |
|---|---|---|
| PS/2 ports | keyboard (INT0) and mouse (INT1) on one chip | one port per chip (INT0/PD4); the PD7 strap chooses keyboard or mouse |
| CPU interface | data latch, status port, command latch (-RDCMD, BUSY), INTREQ, SRC | the data latch and READY only: no commands, no interrupt, no source bit |
| Keyboard LEDs | CPU commands $10-$17 | the firmware alone |
| Mouse on / off | commands $04 / $05 | the MOUSE-ON input: rising edge = reset + enable; falling edge = $F5 + flush |
| MD0-MD7 | released with pull-ups between transfers (shared with the command latch, V2-9) | outputs all the time |
| Next load after a read | FULL read twice, 5 us apart (YACC1's read strobe holds FULL clear for 7 us) | 1 ms after READY's fall, timestamped by a pin-change interrupt; the reload-if-READY-did-not-set check stays. In `sim/`, the 5 us check let the bus driver's slow INP read "te quick brown fox 01234567899" for "the quick brown fox 0123456789" |
| Request-to-send | the transmitter armed after the 120 us (V2-3) | the same, and INT0 masked during the 120 us. Otherwise the host's own clock edge can complete a frame the device was sending, and the device then aborts it and sends it again: a doubled key (shown in `sim/`) |
| Arrows, editing and F keys | VT100 sequences, Delete $7F, no F keys | the PAK-VI's single bytes (above); V2.0's with `KEYS_VT100 1` |
| Lock keys | every make toggles: a held Caps Lock flickers at the repeat rate | toggle on the first make only |
| Hot plug | none | keyboard $AA: LEDs again; mouse: retry every 2 s, and $AA $00 then silence restarts it |
| Mouse packets | bit-3 resynchronisation | the same, plus a part packet dropped after 25 ms of silence |
| Debug console | on and off by CPU command $FE | `d` on the console, or `DEBUG_AT_START 1`; also `?` and `r` |

Kept: the receiver and sender (data bit read first, frame timeout, 11-clock host-to-device timing, V2-3), reply
filtering while a command waits (R2-10: other bytes are held and handed on in order), the set-2 translation (V2-18's
E0 7E and E0 59 fixes), whole mouse packets, LDDATA idle high (V2-7) and the reload check.

## Console

38400 8N1 on the FTDI header. Opening the port resets the ATmega through DTR. The start line looks like
`video-g-ps2 2026-11-01: keyboard mode (TEXT), strap PD7 pull-up 1 release 1`. One-letter commands:

| Key | Does |
|---|---|
| `d` | debug output on/off: every PS/2 byte (`kb 1C`, `ms 08`), every byte loaded (`-> 61`), mouse and keyboard events |
| `?` | status: mode, LEDs or MOUSE-ON and mouse state, queue length, READY, frame errors, receive overruns, load retries |
| `r` | start again: reset the keyboard, or start/stop the mouse as MOUSE-ON says |

## Building and flashing

Compile (Ken's Mac):

```
"/Applications/Arduino IDE.app/Contents/Resources/app/lib/backend/resources/arduino-cli" compile \
    --fqbn arduino:avr:uno --warnings all embedded/video-g-ps2
```

**Upload through the FTDI header** (J5 on TEXT, J3 on GFX: GND, CTS, VCC, TXD, RXD, DTR, so a standard 5 V FTDI cable
or adapter fits with GND to pin 1). The header's VCC pin is not connected: the card must sit in a powered backplane,
and the bus -RESET must not be held low, because it holds the ATmega in reset. DTR resets the ATmega into Optiboot:

```
arduino-cli upload --fqbn arduino:avr:uno -p /dev/cu.usbserial-XXXX embedded/video-g-ps2
```

Both boards take the same build. After flashing, the console's start line shows which mode the strap chose.

**A blank ATmega328P** needs the Uno bootloader first, and neither card has an ISP header, so program it before
fitting. Ken's T48 can program it in its socket. `compile --output-dir build` also writes
`build/video-g-ps2.ino.with_bootloader.hex` (the sketch plus Optiboot). Then:

```
minipro -p ATMEGA328P@DIP28 -w build/video-g-ps2.ino.with_bootloader.hex
minipro -p ATMEGA328P@DIP28 -c config -r fuses.conf     # shows the format; set it to the Uno's fuses:
                                                       #   lfuse 0xFF, hfuse 0xDE, efuse 0xFD (0x05), lock 0x0F
minipro -p ATMEGA328P@DIP28 -c config -w fuses.conf
```

The device name and the fuse names (`lfuse`, `hfuse`, `efuse`, `lock`) are from minipro 0.7.4's database; these
commands have not been run on a chip yet. Instead, an Arduino running the ArduinoISP sketch can burn the bootloader
and fuses into a chip on a breadboard: `arduino-cli burn-bootloader --fqbn arduino:avr:uno -P arduinoasisp -p
/dev/cu.usbmodemXXXX`. Then upload the sketch over the FTDI header as above.

## Host simulation (`sim/`)

`sim/run.sh` compiles the sketch on the Mac (clang++) against `sim/Arduino.h`, a fake AVR core whose port registers
drive a model of the board. It then runs the checks in `sim/sim.cpp`. The model:

- a PS/2 keyboard or mouse at bit level: 11-clock frames both ways, request-to-send, a host inhibit aborting a frame
  and the byte sent again, the commands and their answers ($FF $FA $AA [$00], $ED, $F4, $F5);
- the 74HCT374 latch and the READY flip-flop, cleared while TPB of an INP is high;
- a CPU polling READY and running INP cycles at 1802 speed or at the bus driver's I2C-stepped speed. It counts any
  change of the latch while its read enable is on.

Checked: the start sequences bit-exact, typing (Shift, Caps Lock, Ctrl, keypad, every special code), the LED commands,
held lock keys, a key typed during an LED command, bursts with a backlog at both read speeds, 300 random keys with LED
commands in between, a command started just before a frame's 11th clock, keyboard and mouse hot plug, MOUSE-ON edges,
whole packets, realignment after a lost byte, the three strap cases, the console and the `KEYS_VT100` build. The run
also builds two V2.0-style variants for comparison (5 us load check; INT0 not masked); their failures are expected.
The model's timing is idealised: interrupt latency and the real analog levels are not modelled.

## Not verified yet

- Nothing has run on an ATmega328P with a real keyboard or mouse.
- The PAK-VI codes come from the PAK-VIa manual (see above). The key codes HBIOS and ELF/OS depend on ($0D, $08, $1B,
  $03) do not depend on that manual.
- The strap: see "The two modes".
- The T48 commands for a blank chip (above).
