# Bus driver card firmware

`s5-bus-driver/s5-bus-driver.ino` is the Arduino Nano sketch for the System-5 bus driver cards: BUSDRV-B (`hardware/bus-driver/kicad/rev-b`, built and in use) and, since 2026-11-20, BUSDRV-C (`hardware/bus-driver/kicad/rev-c`, drawn; the last section below). The header comment has the command list.
It has the same wire protocol as Ken's YACC1 `bus-driver.ino`: `CMD:OPERAND#`, replies, then `>>`. The host tool is `software/busdrv/s5busdrv.py`.

- **Monitor by default.** At power-up every expander pin is an input. `MASTER:1#` takes the bus, and is refused while TPA/TPB toggle (a CPU is running) or the bus has no power.
- **Memory and I/O in the 1802's order:**
  - Memory: high address byte on A0–7 with a TPA pulse, low byte, -VMA, then -MRD (read) or -MRW (write), each with a TPB pulse inside it (the 6845's E).
  - I/O: `OUT` drives the data, holds -MRD low (an 1802 OUT is a memory read), sets N0–N2 and pulses TPA then TPB; `INP` sets N0–N2, pulses TPA and samples the data while TPB is high. -VMA stays high, so no memory card answers.
  - `INBLK`/`OUTBLK` run up to 64 / 32 of them in one command (a CF sector is 8 `INBLK`s).
- **Fixed 2026-10-11:** before that, memory cycles had no TPB (the CRTC never answered) and `OUT`/`INP` had no -MRD or TPA (the IDE card read the drive onto the bus during every `OUT`). Found with `software/busdrv/fwsim.py`, which runs the same steps against the cards' netlists; keep it in step with any change to a bus cycle here.
- **Open-collector lines** (-RESET, -INT, -EF) are only pulled low or released.
- **A short finder** (2026-11-21, `walk-1`): `WALK:pin,level#` drives one bus line alone; the section at the end.
- **While bus +5V is off:** the expanders are held in reset, and I²C is stopped with no pull-ups, so nothing back-feeds them.
- **No Adafruit library:** it writes the MCP23017 registers directly (I²C at 400 kHz, about 1 ms per byte).

## Build and flash

Board: Arduino Nano (ATmega328P). Many clones need the old bootloader: `arduino:avr:nano:cpu=atmega328old`. Ken's Nano (a CH340 clone, `/dev/cu.usbserial-3120`) needs it: confirmed 2026-10-19 with a Blink upload (the standard setting fails with "not in sync").

```bash
arduino-cli compile --fqbn arduino:avr:nano s5-bus-driver
```
On a Mac without `arduino-cli` on the path, the Arduino IDE carries one: `"/Applications/Arduino IDE.app/Contents/Resources/app/lib/backend/resources/arduino-cli"`.
```bash
arduino-cli upload -p /dev/cu.usbserial-XXXX --fqbn arduino:avr:nano s5-bus-driver
```

Status, 2026-10-11 (banner `s5-bus-driver blocks-1 io-2 2026-10-11`):
- Compiles with `arduino-cli` 1.5.1 (the `arduino:avr` 1.8.6 core on Ken's Mac; 1.8.8 on 2026-10-06), for both `nano` and `nano:cpu=atmega328old`, with 0 warnings from the sketch.
- Size: 14,564 bytes of flash (47%) and 772 bytes of RAM (37%).
- **Running on BUSDRV-B since 2026-10-30** (`hardware/FABRICATED.md`). The sketch's banner is now `blocks-1 io-2 clk-1 2026-10-31`: it adds `CLK:n`, clock stepping for `software/busdrv/cputrace.py`; the size above is the 2026-10-11 build's. Its bus cycles are checked against the memory Rev D, IDE/CF Rev A and 6845 Rev B netlists by `software/busdrv/test_bringup.py`.
- Bring-up procedure for the cards: `software/busdrv/BRINGUP.md`.

## BUSDRV-C (2026-11-20): one sketch for both boards

The same sketch now runs BUSDRV-C, the 36-pin card (`hardware/bus-driver/kicad/rev-c`, drawn, not built). **It has never run on a BUSDRV-C: there is none. It compiles, and its bus steps were tried in the simulator; it has not been uploaded to the BUSDRV-B in use either.**

- **Which board:** when the bus has power the sketch looks for a third MCP23017 (U3, I²C 0x22). Found: BUSDRV-C. The banner and the power-on note say which:
  - `s5-bus-driver blocks-1 io-2 clk-1 2026-11-20 BUSDRV-B`
  - `s5-bus-driver blocks-1 io-2 clk-2 ext-1 mode-1 load-1 probe-1 2026-11-20 BUSDRV-C`
  - with the bus off the board is not known yet: `... clk-1 2026-11-20 (bus off: board not known yet)`.
- **BUSDRV-B is unchanged:** U1 and U2 are pin for pin the same on both boards, and every BUSDRV-B command runs the same port writes as before. The BUSDRV-C commands answer `Error: needs BUSDRV-C (no U3 at 0x22)`.
- **New on BUSDRV-C**, all with the CPU card in place (the card stays a monitor; it never takes the bus):
  - `ext-1`: -EF1, -EF2, -EF3, -PAUSE, -DMAIN pulled low or let go; SC0 and the DEBUG cable's CLOCK, SC0, SC1 read (`SNAP`, `DBG`); SPARE5–11 (`SPARE`, `SPDIR`, `SPIN`).
  - `mode-1`: `MODE:0..3#` = RUN, RESET, PAUSE, LOAD by -RESET and -PAUSE. The two are low together only for LOAD, which sets CPU Rev D's LOADED flag. PAUSE first waits to see -RESET high on the bus: the CPU card's DS1813 holds it low for 150 ms after it is let go.
  - `mode-2` (2026-11-22): `MODE:4#` = BOOT, a boot reset: -RESET and -DMAIN low together with -PAUSE high. CPU Rev D clears its LOADED flag, so `MODE:0#` after it starts the machine in the EPROM, as the card's own RESET/RUN switch and the front panel's RESET button do. Refused while -PAUSE is low on the bus (that would be LOAD mode with a DMA request). Every other `MODE` lets -DMAIN go first. The loader now says "-DMAIN is low before the request" when something else holds the line: CPU Rev D no longer makes DMA cycles of a line that has not been high in LOAD mode.
  - `load-1`: `DMA:val#` and `LOADBLK:count,hh..#`: LOAD mode by the clock (option B of the design notes). The header comment has the steps; each checks what it expects on the bus and says what it found instead.
  - `clk-2`: the clock on D9 (Timer 1, OC1A): `CLKHZ:hz#` steady from 1 Hz to 2 MHz, `CLKSTOP:0#`, and `CLK:n#` now single edges on D9 (on BUSDRV-B it is still SPARE1).
  - `probe-1`: `PROBE`, `PCOUNT:ms#` (pin-change interrupts on D8 and A1), `PTIME:ms#` and `PDELAY:e#` (Timer 1's input capture on D8, 62.5 ns a count; only with the steady clock stopped, since Timer 1 makes it).
- **`MASTER:1#` on BUSDRV-C** is also refused while its clock runs, and when the DEBUG cable's CLOCK follows CLK OUT: a CPU Rev D is cabled to it. BUSDRV-B still cannot tell a stopped CPU card from an empty slot.
- **While bus +5V is off** D9 is an input too, so CLK OUT cannot feed an unpowered CPU card through its EXT CLK input.
- **Size (2026-11-20, `arduino-cli` 1.6.0, `arduino:avr` 1.8.6):** 21,226 bytes of flash (69% of 30,720) and 1,091 bytes of RAM (53% of 2,048), for `nano` and `nano:cpu=atmega328old`; 0 warnings from the sketch. Before BUSDRV-C: 15,222 and 802.
- **Tried without hardware:** `software/busdrv/fwsim.py` is this sketch in Python, port write for port write, and `backplane.Backplane36` is the bus Rev D with a memory card and CPU Rev D from their netlists, the 1802 moved one clock edge at a time (`cpupins.py`, checked against the real 1802's stepped trace). `software/busdrv/test_busdrv_c.py` (32 tests): 300 bytes loaded once each with no fight on the data lines, then run; the cable off, JP1 wrong, -DMAIN stuck; a BUSDRV-B refusing the new commands.
- **Before it goes on the BUSDRV-B in use:** it is a larger sketch on a card that works. Keep the 2026-10-31 build to go back to (`git show 11eab8e:embedded/bus-driver/s5-bus-driver/s5-bus-driver.ino`), and run `python3 bringup.py memory` after the upload.

## WALK: one line driven alone, to find shorts (2026-11-21)

Ken, 2026-11-21: "does debug card reach all bus lines, if so can be used as a short detector". It does: every signal
of the bus has an expander pin of its own (28 on BUSDRV-B, 34 on BUSDRV-C), each of which can read its line, pull it
low or drive it high. Bus-master mode drives all its lines at once, which shows nothing about a short, so the sketch
has one more command, on both boards, banner word `walk-1`:

- **`WALK:pin,level#`**, MONITOR mode, the CPU card out. Every bus pin is an input with the expander's own pull-up on
  (100k: a line the backplane does not hold then rests high); the one pin is driven to `level` (0 or 1), the ports are
  read, and the pin is put back as it was and the pull-ups turned off: about a millisecond. `pin` = chip × 16 + port × 8
  + bit (U1 is chip 0, port A is 0; `software/busdrv/s5busdrv.py` has the table). Level 2 drives nothing: the lines at
  rest. The answer is the GPIO ports as read, in hex: four on BUSDRV-B, six on BUSDRV-C.
- **The card is left as it was found:** the walked pin's direction and latch are put back, and an open-collector
  line the card was already holding low (`-RESET:1#`) stays low all through a walk, its own included.
- **A pin that does not follow is let go at once.** The sketch reads the pin straight after driving it; if something
  holds it the other way (a short to a supply, a card driving it) it makes the pin an input again, two expander
  transactions after it drove it (about 0.3 ms), and reads the ports after that, so the pin's own bit shows it did
  not follow. That is the one case where a pin is loaded beyond the MCP23017's 25 mA rating, and why it is kept short.
- **Refused:** level 1 on an open-collector line (never driven high, here as everywhere); a pin that is not a bus line
  (the spares, the DEBUG inputs); in MASTER mode; and whenever `MASTER:1#` would be: TPA / TPB toggling, or on
  BUSDRV-C its clock running or a CPU card answering on the DEBUG cable. (The pull-ups go on before that look, so
  that on a bare backplane with no resistors TPA and TPB are not floating inputs while they are watched.)
- **The test built on it** is `python3 bringup.py shorts` (`software/busdrv/BRINGUP.md`): every line pulled low alone
  and the pulled-down ones driven high alone, the shorts named with where the two lines are neighbours.
- **Size (2026-11-21, `arduino-cli` 1.5.1, `arduino:avr` 1.8.8):** 22,560 bytes of flash (73% of 30,720) and 1,109
  bytes of RAM (54% of 2,048); 0 warnings from the sketch. The banners: `... clk-1 walk-1 2026-11-21 BUSDRV-B` and
  `... probe-1 walk-1 2026-11-21 BUSDRV-C`.
- **Tried without hardware only**, as BUSDRV-C's commands: `fwsim.py` runs the same register writes against
  `backplane.py`, which works every line out by itself for this command (resistors, the 100k pull-ups, shorts, the
  cards' netlists); `software/busdrv/test_shorts.py`, 26 tests. **It has not been uploaded to the BUSDRV-B in use.**
