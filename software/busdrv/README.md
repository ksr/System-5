# s5busdrv.py: host tool for the System-5 bus driver card

**Bringing up cards:** `bringup.py` runs test plans for the memory, CF and 6845 cards; the procedure is `BRINGUP.md`.
**BUSDRV-C**, the 36-pin card that works with the CPU card in place, is at the end of this page.

Talks to the card's Nano over USB serial (115200 baud). The port is auto-detected; use `--port` to choose.
Needs `pyserial`:

```bash
pip3 install pyserial
```

Run commands from this folder (`software/busdrv`):

```bash
python3 s5busdrv.py status
```
```bash
python3 s5busdrv.py master on
```
```bash
python3 s5busdrv.py dump 0x0000 256
```
```bash
python3 s5busdrv.py load monitor.hex
```
```bash
python3 s5busdrv.py memtest 0x0000 0x6FFF
```
```bash
python3 s5busdrv.py --auto-master peek 0x8000 16
```

- **`master on`** is needed before memory and I/O commands. Pull the CPU card first.
- **`--auto-master`** takes the bus for a single command and releases it afterwards.
- **`--sim`** runs against `simcard.py`, a simulated card behind a Memory Rev D card: RAM 0000–6FFF, 7000 open (reads FF), EPROM 8000–FFFF, and an echo I/O port 4.
- **`--log`** shows the serial traffic.
- **`watch`** prints the bus lines on every change, useful with the CPU running, where the card stays in monitor mode.
- **`load`** takes Intel hex or binary, and verifies what it wrote.
- **`walk`** (firmware of 2026-11-21, CPU card out) drives one bus line alone for a moment and shows which other lines
  moved with it: `walk` alone lists every line at rest, `walk -MRD low` pulls -MRD low. It is the step of the **short
  finder**, `python3 bringup.py shorts`, which walks every line and names the shorts (`BRINGUP.md`).

- **`simcard.py`** is a quick behavioural card for the host tool's own tests. `fwsim.py` + `backplane.py` are the faithful one: the firmware's port writes, step by step, driving the cards' netlist models (used by `bringup.py --sim`).

Tests run against the simulators (all passing on 2026-11-21: 9 for the host tool, 17 for the bring-up plans, 32 for
BUSDRV-C, 26 for the short finder, `python3 test_shorts.py`):

```bash
python3 test_s5busdrv.py
```
```bash
python3 test_bringup.py
```
```bash
python3 test_busdrv_c.py
```

## BUSDRV-C: the 36-pin card (2026-11-20)

BUSDRV-C (`hardware/bus-driver/kicad/rev-c`, drawn, not built) runs the same firmware and the same tool. The firmware finds the card's third expander and says `BUSDRV-C` in its banner; on a BUSDRV-B the commands below answer `Error: needs BUSDRV-C`.
**None of this has run on hardware.** It runs on the simulator (`--sim --rev C`, and `bringup.py --sim bus36` / `load`) and in the emulator (`python3 -m s5emu --hw --cpu-rev D --buslink`).

What is new is that it works **with the CPU card in place**: CPU Rev D, the 6-way ribbon between the two DEBUG headers, the CPU card's JP1 on EXT. The bus driver is then the 1802's clock.

```bash
python3 s5busdrv.py mode load
```
```bash
python3 s5busdrv.py loadrun program.hex
```
```bash
python3 s5busdrv.py clk 320 --cycles
```
```bash
python3 s5busdrv.py clktest
```

- **`mode run|reset|pause|load`** holds -RESET and -PAUSE. Both are low together only for LOAD (that sets the CPU card's LOADED flag), and LOAD always goes through RESET, so loading starts at 0000.
- **`dmaload FILE`** fills RAM from 0000 through LOAD mode: each byte is one DMA IN cycle, with the clock stepped by the card (about 7 ms a byte). The card reads the address of every write off the bus. **`loadrun FILE [ADDR] [HZ]`** then runs it, the 1802 clocked by the card at 2 MHz unless HZ says otherwise (0: clock stopped).
  A file that does not begin at 0000 gets zeros below it and a jump to its start.
- **`clkhz HZ`**, **`clkstop`**, **`clk N`**: the card's clock on CLK OUT, steady, stopped, or N edges at a time with the bus changes listed (`--cycles`: one line a machine cycle, with the state code).
- **`line -EF1 on`** (and -EF2, -EF3, -PAUSE, -DMAIN): the extension's open-collector lines. **`dbg`**: the DEBUG cable's CLOCK, SC0, SC1.
- **`probe`**, **`pcount MS`**, **`ptime`**, **`pdelay 0|1`**: the two probe inputs on J2: levels, edges counted, PROBE1's period and high time, the time from a clock edge to PROBE1's next edge (62.5 ns steps).
- **`master on` is refused** while the DEBUG cable shows a CPU card. With the CPU card out, BUSDRV-C is bus master as BUSDRV-B is.

The simulator for it: `fwsim.py` with `rev="C"` on `backplane.Backplane36` (the bus Rev D, a memory card and CPU Rev D from their netlists) and `cpupins.py`, the 1802's pins one clock edge at a time, checked edge for edge against the real 1802's clock-stepped trace of 2026-10-31. `BRINGUP.md` has the two bring-up plans and the faults the simulator can show.

## cputrace.py: the CPU card, cycle by cycle (2026-10-31)

With the CPU card in, the bus driver can only listen. To see every bus cycle, it steps the CPU's clock:
the bus driver's **SPARE1 (J2 pin 1) is wired to the CPU card's IC8 pin 3** (the 74x74 that halves the oscillator into
the 1802's CLOCK; pin 3 bent out of its socket, away from IC7). Each rising edge on SPARE1 is one 1802 clock edge
(16 per machine cycle); the 1802 is static (its clock is rated from DC), so it waits between edges. Firmware `clk-1`
or later: `CLK:n#` steps and reports every bus change.

    python3 cputrace.py --no-reset --cycles 400 --compare

prints one line per machine cycle (address, R/W/-, data, N, Q, -VMA) and compares the bus cycles with the emulator
(`s5emu --hw`, CPU + 6845 cards from their netlists), first finding where the card is in the emulator's run.
About 45 machine cycles a second.

- **Reset:** the CPU card resets only at power-on. Its S1 and bus -RESET do not restart the 1802 (2026-10-31; the
  2005 rework around IC5 and U1), so use `--no-reset` and power-cycle for a run from 0000.
- **Never take bus master with the CPU card in.** With its clock stepped TPA does not toggle, so `MASTER:1#` (and
  `bringup.py`) cannot tell the CPU card is there.
- To restore the card: put IC8 pin 3 back in its socket. (Restored 2026-11-01; since then a jumper on the CPU card selects
  IC8 pin 3's clock: the crystal oscillator IC7, or SPARE1 for stepping. Set it to SPARE1 before running `cputrace.py`.)
