# Bus driver card firmware

`s5-bus-driver/s5-bus-driver.ino` is the Arduino Nano sketch for the System-5 bus driver card (BUSDRV-B, `hardware/bus-driver/kicad/rev-b`). The header comment has the command list.
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
