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
   cd ~/Developer/elf/embedded/bus-driver
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
