# Bringing up System-5 cards from the bus driver

`bringup.py` tests the memory, CF and 6845 video cards one at a time, from the bus driver card (BUSDRV-B), with the CPU card out of the backplane.
The bus driver plays the 1802: it runs every memory and I/O cycle itself, in the 1802's order, about 1 ms a byte.
Each step says what it proves, PASS or FAIL, and on a failure which parts to look at.

The IO card (1861 and keyboard) is left for later. The plan is a standalone CPU card redesign, and a PS/2 keyboard on the next video card (`BACKLOG.md`).

## Before the first run

1. **Flash the bus driver firmware of 2026-10-11 or later.** Its banner says `io-2`; `bringup.py` warns if it does not.
   The earlier firmware had two bus-cycle bugs, found with the simulator:
   - memory cycles had no TPB, and the 6845's E is TPB, so the CRTC never answered;
   - OUT left `-MRD` high, so the IDE card took every OUT for an INP and read the drive onto the bus while the bus driver was driving it.
   ```bash
   cd embedded/bus-driver        # from the top of the repository
   ```
   ```bash
   "/Applications/Arduino IDE.app/Contents/Resources/app/lib/backend/resources/arduino-cli" upload -p /dev/cu.usbserial-XXXX --fqbn arduino:avr:nano s5-bus-driver
   ```
   Clones with the old bootloader need `--fqbn arduino:avr:nano:cpu=atmega328old`.
2. **pyserial** on the Mac: `pip3 install pyserial`.
3. **The backplane:** the bus driver plus the one card under test. **No CPU card**: the bus driver refuses the bus while TPA/TPB toggle.
4. Run everything from `software/busdrv`.

## The order

| Step | Cards in the backplane | Command |
|---|---|---|
| 1 | bus driver alone | `python3 s5busdrv.py status`, then `python3 s5busdrv.py master on` and `snap` |
| 2 | bus driver + memory | `python3 bringup.py memory` (Rev D's circuit = MEM3-E, the card in the machine) or `python3 bringup.py memory --mem-rev B-built` (the reworked Rev B, the card before it) |
| 3 | bus driver + IDE/CF (adapter powered, CF card in) | `python3 bringup.py cf` |
| 4 | bus driver + 6845 (monitor connected) | `python3 bringup.py video --interactive` |
| 5 | all three | `python3 bringup.py all` |

Add `--report results.md` to keep a record of a run, and `--log` to see every command sent to the card.

## Jumpers the plans assume

| Card | Setting | Option to change it |
|---|---|---|
| Memory | blocks 0–6 RAM, 7 open (the 6845 card's), 8–E EPROM, F open: `RRRRRRR-EEEEEEE-` (block 0 first) | `--jumpers` |
| Memory | Rev D | `--mem-rev C` or `B-built` |
| IDE/CF | SV1 = port 2 (register select), SV2 = port 3 (data) | `--ide-sel`, `--ide-data` |
| 6845 | SV1 1-2: block 7 (video RAM 7000–77FF, CRTC 7800–7FFF) | `--video-base` |
| 6845 | Rev B, the card in the machine | `--video-rev B-Clean-Keyboard` (its 6845 is write-only: V5 reads no register back) |

The memory plan works out what each block should hold from the card's netlist, for its revision and these jumpers: the same gate-level decode the emulator runs.
On the reworked Rev B the jumpers do not decide the map. Its rework puts the chip selects on the 74LS32 bank gates, so RAM fills 0000–7FFF and the EPROM fills 8000–FFFF.

## The plans

### memory

| Step | What it does | What a failure points at |
|---|---|---|
| M1 block map | Each 4K block: write, read back, restore. RAM, EPROM (reads, ignores writes) or nothing (FF) against the expected map | Jumper columns, the chip in its socket, its 74HCT151 mux, the 74LS32 !CE gate. An EPROM block reading FF is a warning: blank and absent look the same |
| M2 data lines | Walking ones and zeros, 00 FF 55 AA, at one RAM byte | Names each stuck bit: connector pin, the RAM's I/O pin, a short to the neighbouring line |
| M3 address lines | A byte at the base and at the base with each address bit flipped; none may land on another | A0–A7 through the CD4050s (IC7, IC8); A8–A15 latched on TPA by the CD4042s (IC6, IC9). Uses only the data bits M2 found working |
| M4 RAM test | Quick: 3 × 64 bytes per RAM block, address pattern, 55, AA. `--full`: every byte (address in address, walking ones, fills), a few minutes | Bad bytes with good lines: the RAM chip |
| M5 EPROM read | The first 256 bytes of each EPROM block (all 4K with `--full`, `--rom` or `--save-rom`), twice. `--rom FILE` compares with an image (`--rom-base`, default 8000); `--save-rom FILE` keeps what was read | Unstable reads: socket, !OE / !CE |
| M6 LEDs | Reads each chip for 3 s: its LED should glow (Rev D: LED2 IC1, LED3 IC11, LED4 IC3, LED5 IC5; LED1 is +5 V) | A dark LED with a working chip: the LED or its 470 Ω |

### cf

| Step | What it does | What a failure points at |
|---|---|---|
| C1 status | `OUT 2,7`, `INP 3`: the status register, waiting up to 3 s for BSY to clear | FF: nothing answers (the CF card, adapter power, ribbon pin 1, SV1/SV2, the 74LS138). BSY stuck: card power |
| C2 register path | LBA register written and read back with every pattern | The drive's data lines go straight from the bus to the header, no buffer |
| C3 register select | Four registers get four values; each must keep its own | DA0–DA2 from the 74LS75 latch (IC7), fed from D0–D2 on `OUT 2` |
| C4 BIOS set-up | What Mike Riley's BIOS does (`resetide`): device control 0E = 02, then SET FEATURES 01 (8-bit mode) | A card that refuses 8-bit mode |
| C5 IDENTIFY | Model, serial, firmware, size | |
| C6 read sectors | LBA 0 (or `--sectors N`), shown in hex; `--image FILE` compares with a disk image | |
| C7 write test | Only with `--cf-write-lba N`: saves LBA N, writes a pattern, checks it, puts the original back, checks that | |

### video

| Step | What it does | What a failure points at |
|---|---|---|
| V1 decode | The card answers in its block and nowhere else | SV1, the 74LS85 compare (IC4) on the latched A12–A15 (74LS373, IC2, on TPA), -VMA |
| V2–V4 video RAM | Data lines, address lines A0–A10, all 2K | The IDT7134's right port |
| V5 CRTC | R14/R15 (the cursor registers, the ones a 6845 reads back) written and read, switching registers each time; then the repeat through 7800–7FFF (RS = A0) | FF: the CRTC never answers (E = TPB: old firmware; CS, R/W = -MRW, -RESET). R14 reading R15's value: RAM also answers there |
| V5 with `--video-rev B-Clean-Keyboard` | Its 6845 is write-only (R/W on ground), so R14/R15 are not read back: bytes are written to 7800 / 7801 (and their repeats) and nothing may drive a read of them (FF on the bus Rev D). That the writes land is seen on the screen, V6 | A read that is what was written: RAM also answers there. Anything else not FF: R/W (pin 22) not on ground, or E (pin 23, IC18 pin 5) high in a read |
| V6 screen | HBIOS v1.0.4's CRTC table (BYTE's 16 × 64), then a test screen: border, title, the character set with lower case (Rev B), reverse video, digits, the cursor on the bottom row | You check the monitor. A rolling picture: the crystal (the table assumes 9 MHz and ÷6). Wrong characters: the character EPROM |

### all

The three cards together: the combined map (memory as jumpered, the 6845 card in block 7), memory and video RAM not disturbing each other, the CRTC test again (it catches a memory card that also answers at 7800), the CF status, the CF register surviving 48 memory cycles untouched, and IDENTIFY.
With the reworked Rev B it reports what the netlist predicts: RAM and the 6845 card both answer at 7000–7FFF. That is open question 7 in `BACKLOG.md`, answered on the real cards.

## Without hardware: the simulator

`--sim` runs any plan against a simulated backplane, with nothing plugged in:
- `fwsim.py` is the firmware in Python, port write for port write.
- `backplane.py` drives the cards' gate-level netlist models (the emulator's `s5emu/hw.py`) pin by pin.

It reports bus fights (two parts driving the data lines at once), which real hardware cannot.
It also takes `--fault` to show what a failure looks like:

| Fault | What it simulates |
|---|---|
| `stuck:mem:3:0` | data line 3 stuck low on the memory card (`mem`, `video` or `ide`) |
| `addr:4:0` | address line A4 stuck low on the backplane |
| `empty:IC1` | a memory card chip left out |
| `card-jumpers:RRR-----EEEEEEE-` | the card jumpered differently from `--jumpers` |
| `nodrive` | the IDE card with no CF card behind it |
| `legacy` | the firmware's bus cycles before 2026-10-11 |

```bash
python3 bringup.py --sim memory --fault stuck:mem:3:0
```

Tests: `python3 test_bringup.py` (17 tests, about three minutes), plus `python3 test_s5busdrv.py` for the host tool.

## shorts: a short finder (either card, 2026-11-21)

Every bus line the card reaches has an expander pin of its own that can read it, pull it low or drive it high: 28
lines on BUSDRV-B, all 34 signals of the 36-pin bus on BUSDRV-C. So the bus driver can look for shorts between bus
lines (Ken, 2026-11-21: it reaches every line, so it "can be used as a short detector"): it drives **one line at a
time** and watches all the others. Two lines that move together are joined.

Use it on a **bare backplane** first (a new bus Rev D after its eight sockets are soldered: 288 joints 0.1 inch
apart), then with **one new card at a time**. **The CPU card must be out:** an 1802 drives its lines even in reset.
It needs the firmware of 2026-11-21 or later (`walk-1` in its banner).

```bash
python3 bringup.py shorts
```

| Step | What it does | What a failure points at |
|---|---|---|
| S1 connect | Bus power; the firmware has `WALK`; the card may drive a line | No power; an older sketch; a CPU seen: TPA / TPB toggling, or on BUSDRV-C its clock running or a CPU card answering on the DEBUG cable |
| S2 at rest | Nothing driven and the expanders' own 100k pull-ups on, read three times. On the bus Rev D TPA, TPB and N0–N2 rest low (its 10k pull-downs) and every other line high; on the 2009 backplane, which has no resistors, every line rests high | "rests low": shorted to ground, or held by a card. "rests high" on a pulled-down line: no pull-down, or joined to +5V or to a pulled-up line. "no clear level": a pull-up joined to a pull-down. **Q low ends the plan: a CPU card is in the bus** |
| S3 low | Each line pulled low alone, for about a millisecond | "will not go low": held high against the pin (a short to +5V, a card driving it); the card lets go at once |
| S4 high | Each pulled-down line driven high alone (the bus Rev D only: there are none on the 2009 backplane) | "will not go high": shorted to ground |
| S5 together | Two lines that take each other low, or high, are shorted; three or more are named as one group. For each it says where the lines lie side by side: positions in the slots, pins of the bus driver's own expanders | A solder bridge between neighbouring slot pins, or on the bus driver itself. Lines that are neighbours nowhere: look at the card in the bus. "one way only": a card's logic, not a plain short |

What it finds and what it cannot:

- **It finds** a short between two bus lines, a short to ground and a short to +5V.
- **It cannot see** an open joint (a line that does not reach a slot: `bus36` finds a missing pull resistor, and the
  card can be moved from slot to slot), or a short behind a card's buffers.
- **A pull-up joined to a pull-down** (N1 and -RESET are neighbours in the slots) sits at about 2.7 V, between the
  expander's input thresholds, and reads high on one chip and low on another. All three cases are found: both lines read
  high (each takes the other low), both read low (the held line rises when the pulled-down one is driven high), or
  now one and now the other (the pair follows the pulled-down line both ways, tried four times over).
- **Open-collector lines are never driven high**, as everywhere in the firmware. Nothing is lost: a short from one of
  them to a pulled-down line shows when that pulled-down line is driven, low or high.
- **A line shorted to +5V** can only be found by pulling it low. The card reads its pin straight after driving it and
  lets go if it did not follow: the pin is held against the supply for two expander transactions, about 0.3 ms.
- **With cards in the bus:** in the simulator, with the memory, 6845 and IDE cards from their netlists in place, no
  single line driven low or high makes any of them drive the data lines or move another line, so the test runs clean
  with them in. On the real 2009 backplane a card's TTL inputs load the lines that have no resistor (A0–A7, Q), where
  only the 100k pull-ups hold them: a "no clear level" there is that, not a short. The bare backplane has no such doubt.

`--bus d` or `--bus 2009` says which backplane it is; left out, the plan tells them apart by the pull-downs. One step
at a time, by hand:

```bash
python3 s5busdrv.py walk
```
```bash
python3 s5busdrv.py walk -MRD low
```

In the simulator (`--busdrv C`: BUSDRV-C in a bus Rev D; without it BUSDRV-B in the 2009 backplane; `--cards
mem,video,ide` puts cards in the bus):

```bash
python3 bringup.py --sim shorts --busdrv C --fault short:N1:RESET --fault short:D0:D1
```

| Fault | What it simulates |
|---|---|
| `short:D0:D1` | two bus lines joined (names with or without the dash) |
| `short:N0:GND`, `short:D0:+5V` | a line joined to a supply |
| `between:0`, `between:1` | how the expander reads a line held between its thresholds: low every time, or high; without it, either, anew at each read |
| `oneway:A3:A4` | A3 low takes A4 low and not the other way round: a card's logic between two lines, which the plan names as a warning, not as a short |
| `cpu-in` | BUSDRV-C: a CPU card left in the bus with its DEBUG ribbon off, so the card cannot see it |

Tests: `python3 test_shorts.py` (26 tests, a few seconds): the simulator's own arithmetic, the `WALK` command, and the plan
on sound backplanes and with each kind of short.

## BUSDRV-C: the 36-pin bus, and the CPU card in place

BUSDRV-C (`hardware/bus-driver/kicad/rev-c`, drawn, not built) runs the same firmware; it finds its third expander and says `BUSDRV-C` in its banner.
Everything above works on it as on BUSDRV-B. It has two plans of its own. **Neither has run on hardware: there is no BUSDRV-C, bus Rev D or CPU Rev D yet.** Both pass on the simulator, and that is all that is known.

| Step | Cards in the backplane | Command |
|---|---|---|
| 1 | bus Rev D with the bus driver alone | `python3 bringup.py bus36` |
| 2 | bus driver + memory (CPU card out) | `python3 bringup.py memory`, as above |
| 3 | bus driver + memory + CPU Rev D, the 6-way ribbon from the bus driver's J4 to the CPU card's J2 (DEBUG), the CPU card's JP1 on EXT | `python3 bringup.py load` |

**In step 3 the bus driver never takes the bus.** It holds the 1802 by -RESET and -PAUSE and is its clock. `MASTER` is refused: the DEBUG cable shows it that a CPU card is there.

### bus36

The bus Rev D's pull-ups and pull-downs, and the six lines of the 36-pin extension. With a card in the backplane the "at rest" step will name the lines that card drives.

| Step | What it does | What a failure points at |
|---|---|---|
| X1 at rest | Nothing driven: -RESET, -INT, -EF, -EF1 to -EF3, -PAUSE, -DMAIN, -MRD, -MRW, -VMA and D0–D7 read high, TPA, TPB and N0–N2 low | A line held the wrong way: a card in the backplane, a short, or a resistor network missing |
| X2 open-collector lines | Each of the eight pulled low alone: it reads low, the other seven stay high; let go, it comes back up | Stays low after it is let go: no pull-up on that line (RN1, RN2). Two lines low together: a short between neighbouring pins |
| X3 driven lines | As bus master: TPA and TPB driven high, -MRD, -MRW and -VMA low, N = 7, D0–D7 = 00; each let go and read again | A line that stays where it was driven has no pull-down (RN3) or pull-up (RN4, RN1) |
| X4 DEBUG header | J4's CLOCK, SC0, SC1 with no cable: 1 1 1 (the expander pulls them up), and the clock test finds no CPU card | A cable left on, or a short at U3's GPB0–2 |

### load

LOAD mode by the clock (`hardware/bus-driver/kicad/rev-c/DESIGN.md`): the bus driver steps the 1802's clock one edge at a time and reads the bus between edges, so it can let -DMAIN go the moment the 1802 has taken the request and put the byte on D0–D7 only inside the DMA cycle.

| Step | What it does | What a failure points at |
|---|---|---|
| L1 cable | Eight edges on CLK OUT; the cable's CLOCK must follow each one and hold between them | The ribbon (J4 to the CPU card's J2); the CPU card's JP1 not on EXT |
| L2 modes | `MODE` RESET, then LOAD: -RESET and -PAUSE as the bus shows them | U2 (-RESET) or U3 (-PAUSE) of the bus driver; another card holding a line (the IO panel's RUN and LOAD toggles) |
| L3 load | A 48-byte program by `LOADBLK`. The card reads the address of every write off the bus: the first must be 0000 and each next one more | "SC0 stays low": -DMAIN held low by something else. "no DMA cycle": -DMAIN does not reach the 1802. "CLK OUT does not reach": the cable. "a second DMA cycle": -DMAIN slow to rise |
| L4 run | `MODE` RUN, then the clock stepped with `CLK`, the bus traced: the first fetch must be 0000 from RAM (not the EPROM: LOADED), the program reads all 48 of its bytes and the bus driver checks each against what it sent; Q rises at the end | A wrong byte: the data was not held through the write, or the RAM took a second write. First fetch from the EPROM: LOAD mode did not set the CPU card's LOADED flag (U8A) |
| L5 pause | -PAUSE low: 64 clock edges move nothing on the bus; let go, the cycles go on | -PAUSE to the 1802's WAIT (the CPU card's U7) |
| L6 bus reset | `MODE` RESET then RUN: the loaded program starts again | LOADED should survive a plain reset from the bus; a boot reset clears it (the CPU card's RESET/RUN switch, power-on, the front panel's RESET, `MODE:4#`) |

After `load`, the host tool does the same with a real program:

```bash
python3 s5busdrv.py loadrun program.hex
```

It loads the file from 0000 by DMA IN (47 expander transactions a byte: about 7 ms by estimate, so 28K in a little over three minutes), then lets the 1802 run at 2 MHz from the bus driver's clock. `python3 s5busdrv.py loadrun program.hex 0` leaves the clock stopped, for `python3 s5busdrv.py clk 320 --cycles` (twenty machine cycles, one line each). To run at the CPU card's own 2 MHz: `python3 s5busdrv.py mode reset`, move JP1 to INT, `python3 s5busdrv.py mode run`.

### The simulator for BUSDRV-C

`bus36` and `load` with `--sim` run on `backplane.Backplane36`: the bus Rev D's resistors, a memory card from its netlist, CPU Rev D's gates from its netlist, and the 1802 itself as `cpupins.py`, which moves its pins one clock edge at a time. That pin model was checked against the real 1802: given the data bus of the 2026-10-31 clock-stepped trace of CPU Rev A, it makes the same TPA, TPB, -MRD, -MRW, N, Q and address bytes on every clock edge of the first 25,280 machine cycles (`test_busdrv_c.py` replays the first 6,000); after that a byte read off a floating bus (that bench had no memory card) differs between the two. What that trace does not hold is taken from the data sheet and said so in `cpupins.py`: RESET, PAUSE, LOAD and the DMA cycle. `--busdrv C` runs the older plans on the simulated BUSDRV-C.

| Fault | What it simulates |
|---|---|
| `nocable` | the DEBUG ribbon left off |
| `jp1int` | the CPU card's JP1 on its own oscillator |
| `stuck-line:DMAIN:0` | a bus line held low (or `:1`, high) by something else |
| `nopull:PAUSE` | a pull resistor of the bus Rev D missing (a line's name, `D` or `N`) |
| `hold-dmain`, `early-data` | the firmware doing a LOAD step wrongly: -DMAIN let go a cycle late (a second write), the byte on the bus too early (a fight with the memory card) |

```bash
python3 bringup.py --sim load --fault stuck-line:DMAIN:0
```

Tests: `python3 test_busdrv_c.py` (32 tests, under a minute).
