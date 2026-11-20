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
  - `load-1`: `DMA:val#` and `LOADBLK:count,hh..#`: LOAD mode by the clock (option B of the design notes). The header comment has the steps; each checks what it expects on the bus and says what it found instead.
  - `clk-2`: the clock on D9 (Timer 1, OC1A): `CLKHZ:hz#` steady from 1 Hz to 2 MHz, `CLKSTOP:0#`, and `CLK:n#` now single edges on D9 (on BUSDRV-B it is still SPARE1).
  - `probe-1`: `PROBE`, `PCOUNT:ms#` (pin-change interrupts on D8 and A1), `PTIME:ms#` and `PDELAY:e#` (Timer 1's input capture on D8, 62.5 ns a count; only with the steady clock stopped, since Timer 1 makes it).
- **`MASTER:1#` on BUSDRV-C** is also refused while its clock runs, and when the DEBUG cable's CLOCK follows CLK OUT: a CPU Rev D is cabled to it. BUSDRV-B still cannot tell a stopped CPU card from an empty slot.
- **While bus +5V is off** D9 is an input too, so CLK OUT cannot feed an unpowered CPU card through its EXT CLK input.
- **Size (2026-11-20, `arduino-cli` 1.6.0, `arduino:avr` 1.8.6):** 21,226 bytes of flash (69% of 30,720) and 1,091 bytes of RAM (53% of 2,048), for `nano` and `nano:cpu=atmega328old`; 0 warnings from the sketch. Before BUSDRV-C: 15,222 and 802.
- **Tried without hardware:** `software/busdrv/fwsim.py` is this sketch in Python, port write for port write, and `backplane.Backplane36` is the bus Rev D with a memory card and CPU Rev D from their netlists, the 1802 moved one clock edge at a time (`cpupins.py`, checked against the real 1802's stepped trace). `software/busdrv/test_busdrv_c.py` (32 tests): 300 bytes loaded once each with no fight on the data lines, then run; the cable off, JP1 wrong, -DMAIN stuck; a BUSDRV-B refusing the new commands.
- **Before it goes on the BUSDRV-B in use:** it is a larger sketch on a card that works. Keep the 2026-10-31 build to go back to (`git show 11eab8e:embedded/bus-driver/s5-bus-driver/s5-bus-driver.ino`), and run `python3 bringup.py memory` after the upload.
