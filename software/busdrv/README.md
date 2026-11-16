# s5busdrv.py: host tool for the System-5 bus driver card

**Bringing up cards:** `bringup.py` runs test plans for the memory, CF and 6845 cards; the procedure is `BRINGUP.md`.

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

- **`simcard.py`** is a quick behavioural card for the host tool's own tests. `fwsim.py` + `backplane.py` are the faithful one: the firmware's port writes, step by step, driving the cards' netlist models (used by `bringup.py --sim`).

Tests run against the simulators (all passing on 2026-10-11: 9 for the host tool, 17 for the bring-up plans):

```bash
python3 test_s5busdrv.py
```
```bash
python3 test_bringup.py
```

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
