# s5emu: System-5 emulator and debugger

An emulator of the System-5 1802 computer for debugging software.
It runs the real ROMs and ELF/OS disks, with a terminal debugger and a browser debugger that share one command language. Pure Python 3, standard library only.

```bash
cd software/s5emu
```
```bash
python3 -m s5emu
```

That opens the terminal debugger; type `c` to run. You get the HBIOS monitor prompt `TEST>`.

```bash
python3 -m s5emu --ui web
```

That opens the emulator in a browser at http://127.0.0.1:8802/.

## In a browser, and in a GitHub Codespace

The browser page has two tabs. **Machine** is the System-5 to use: the 64 x 16 screen (click it and type; paste
works too), Run / Pause, Reset, **Boot ELF/OS** (it types `@FF00` and Enter at the monitor's prompt), the emulated
clock (as fast as possible, 2 MHz, 1.76 MHz, 500 kHz) with the rate it actually reaches, the 1861's picture when
the 1861 is on, and the **IO panel card** when it is fitted (`--panel A`; `web-start.sh` fits it unless
`S5_PANEL=none`): its LEDs and TIL311s, the eight toggles, INPUT, RUN, LOAD and the Q light, to toggle a program in
as on a COSMAC ELF. **Debugger** is the debugger: registers, the code at PC with breakpoints, memory and the command line.

The easy way to start it, with a CF card image of ELF/OS 0.2.6 made the first time (`tools/mkelfos.py`, 15 MB like
the real 16 MB card, in `disks/`, never committed):

```bash
./web-start.sh --fg
```

Without `--fg` it runs in the background (`./web-start.sh --stop` stops it). `S5_CLOCK=1.76m` and `S5_PORT=8803`
change the clock and the port, and `S5_ROM=roms/hbios-1.0.4.rom` the ROM (the default is HBIOS 1.0.6, the machine's since
2026-11-15, here and in a GitHub Codespace; `S5_ROM=roms/hbios-1.0.5.rom` runs the one before it; the line under the
screen says which ROM runs). `S5_OS=5` (from the `elfos-v5` branch, merged 2026-11-15) puts Mike Riley's Elf/OS v5
on the card (`disks/elfos-v5.img`), unpacked from the image in the private repository `../private-resources` (it is
third-party and unlicensed, so it is not in this repository); `CODESPACE.md` has the details.

**In a GitHub Codespace**, nothing to install: on github.com, **Code -> Codespaces -> Create codespace on main**. The
repository's `.devcontainer/` makes the CF card image when the Codespace is created and starts the emulator every
time it starts; the page opens in a browser tab. [CODESPACE.md](CODESPACE.md) is the guide.

Options for the page: `--run` starts the machine running at once; `--clock 500k|1.76m|2m|max` sets the emulated
clock (a machine cycle is 8 clocks, so this is `--speed` in clocks); `--web-host 0.0.0.0` listens on every interface
instead of this computer only. The debugger command `speed` changes the clock while it runs.

The page talks to the emulator through one small object (`emu`: `state`, `command`, `key`, `mem`), over HTTP to
`s5emu/web.py`. A page that runs the emulator itself in the browser sets `window.S5_EMU` before the page's script
and needs no server: that is the next step (`BACKLOG.md`).

## What is emulated

| Card | Model |
|---|---|
| CPU | **RCA 1802**, every instruction with cycle counts, interrupts and DMA-out. 0x68 is not an 1802 instruction (it is the 1804/5/6 prefix), but it runs as on the chip: an input from no port, so the floating bus (FF) goes to M(R(X)) and D; the debugger's `op68 stop` makes it stop there instead. **4K EPROM** at F000 (`--rom-base`). At reset it is also seen at 0000 until the first access with A15 high: the CPU card's VMA remap, which the ROM's first `LDI F0 / PHI R0` relies on. |
| Memory | 16 × 4K blocks, each jumpered RAM / EPROM / open (`--jumpers RRRRRRR-EEEEEEE-` is the default: RAM 0000–6FFF, 7000 open for video, EPROM 8000–EFFF). Open blocks float to FF; EPROM ignores writes. |
| 6845 video | 2K video RAM at 7000–77FF, CRTC address/data at 7800/7801. Start address and cursor are honoured; 64 × 16 as HBIOS sets it. |
| IO card | Keyboard on port 1, with EF3 = key waiting. **1861**: `INP 4` = on, `OUT 4` = off (`--pixie-port`); 262 lines × 14 cycles per frame; interrupt at line 78; 128 lines × 8 DMA bytes; EF1 frame markers. |
| IO panel card (`--panel A`; designed 2026-10-30, not built) | Port 4: `OUT 4` latches the byte the 8 LEDs and two TIL311s show, `INP 4` reads the 8 toggles; INPUT is EF1 while held; RUN off resets and holds the 1802, LOAD on pauses it, both = LOAD mode (each INPUT press stores the toggles at M(R0), R0 counts on); after LOAD mode RUN runs RAM from 0000 (CPU Rev D's LOADED flag), otherwise Reset boots the ROM. The 1861 comes off port 4. Its DS12885 clock is on ports 6 and 7, and since 2026-11-20 a 16C550 UART shares them: a byte with bit 7 set written to port 6 picks a UART register (80h-87h), one with bit 7 clear a clock register; `panel.uart.receive()` puts characters on the line, `panel.uart.sent()` takes what was sent. The debugger's `panel` command sets it all. `--hw --panel A` runs the card from its netlist instead (with `--cpu-rev D`). |
| IDE/CF | Mike Riley's 8-bit IDE: `OUT 2` selects a register, port 3 is data. Commands read 20, write 30, identify EC and set-features EF. As a real card (2026-11-15): with register 6 bit 6 set the address is LBA28, without it cylinder / head / sector in the geometry IDENTIFY reports (16 x 63), and a read or write of an address off the card is ERR with ID not found (10h) and no data. Backed by `--disk FILE`; the `save` command writes it back. |
| Bus driver | `--buslink` opens a pty that speaks the BUSDRV-B firmware protocol, so `software/busdrv/s5busdrv.py --port <pty>` drives the emulated machine as it would the real card. Taking the bus is refused while the emulated CPU runs. With CPU Rev D (`--hw --cpu-rev D`) it answers as BUSDRV-C, the 36-pin card that works with the CPU card in place (2026-11-20): `mode run/reset/pause/load`, LOAD mode filling RAM by DMA IN with the CPU card's LOADED flag (`dmaload`, `loadrun`), the -EF lines. It never takes the bus there, and the emulator has no clock edges, so the clock and probe commands are stand-ins (`s5emu/buslink.py`). |

This is a **behavioural** model of each card. For the hardware-faithful mode, see the next section.

## VIDEO-G (`--video g`)

```bash
python3 -m s5emu --video g --disk elfos.img
```

System-5 with the VIDEO-G card (`hardware/video-g/DESIGN.md`, not built yet) in place of the 6845 card and the IO card
(`s5emu/videog.py`, a behavioural model). The ROM defaults to `roms/hbios-video-g.rom`, the VIDEO-G build of HBIOS
(`firmware/hbios/video-g`: the memory-mapped card, 64 x 25, a 24-row scroll; on v1.0.8 since 2026-11-20, so the
monitor's `B` boots ELF/OS and the IO panel's clock has its driver). **VIDEO-G is memory-mapped since 2026-11-17
(Ken): it answers no I/O port.**

| What | Model |
|---|---|
| Text | 2K at 7000-77FF, 64 x 25 (6845 R1/R6), cursor from R14/R15 |
| Graphics window | 7C00-7C3F = pixel line Y (written at 7806) of page CPAGE, bit 7 of byte 0 = x 0; repeated to 7FFF |
| Pages | two of 16K (512 x 256); NTSC shows lines 0-199. At power-up they hold noise (seeded) |
| 7804 | write = control (TEXT-OFF, GFX-ON, XOR, DPAGE, CPAGE, MOUSE-ON; on the GFX board, so nothing without it); read = status (KEY-READY, MOUSE-READY, VSYNC and DE from the CPU clock, MONITOR, GFX-PRESENT, ID 10) |
| 7800/7801, 7802, 7806 | 6845 address / data (7801 reads R14-R17); the key (EF3 = KEY-READY); Y register (write) / mouse byte (read). 7800-7807 repeat through 7BFF |
| Ports | none answer VIDEO-G; the IDE card keeps 2/3, and `--panel A` puts the IO panel on port 4 beside it |
| Keys | ASCII; F1-F12 = 80-8B; Home, Up, PgUp, Left, keypad 5, Right, End, Down, PgDn, Ins, Del = 90-9A, Shift + 40h (`videog.KEYS`) |
| Mouse | `video.mouse_packet(dx, dy, buttons)` queues a PS/2 packet, only while MOUSE-ON; the latch keeps its byte after MOUSE-ON goes off (read 7806 once before turning it back on) |
| Options | `--monitor mda` (IBM 5151: 512 x 256, MONITOR = 1), `--no-gfx` (the TEXT board alone: the window and the mouse float) |

With `--hw` (2026-11-20) TEXT and GFX are read from their KiCad netlists (`s5emu/hwvideog.py`: every decode, the
R/-W latch, the READY flip-flops and the graphics write slot through the cards' own gates; the RAMs, the 6845, the
latches and the two ATmegas played on the pins those gates drive). `--videog-rev none` keeps the behavioural model on
the modelled bus, `--no-gfx` unplugs the ribbon, `--kbd-flag` is TEXT's JP3, and `--panel A` fits the IO panel beside
it in either machine. What the netlist model found is in `hardware/video-g/DESIGN.md`, section 10.

Commands: `png FILE [screen|gfx|text] [SCALE]` writes the picture as a PNG (green on black; `screen` combines text
and graphics as the control register says, with the 6845 Rev B character ROM `firmware/char-rom-fonts/goodfont`);
`vg` shows the control register, Y register and status. `screen` shows the 25 text rows.

Found with it: the ELF/OS boot loader writes the sector numbers to port 4 while it loads the kernel, which left the
port version's control register at 0E (graphics on); the memory-mapped card (2026-11-17) answers no port, which settles
it (`firmware/hbios/video-g/README.md`).

## The 6845 card with the keyboard on it (`--video kbd`)

```bash
python3 -m s5emu --video kbd --panel A --disk elfos.img
```

```bash
python3 -m s5emu --hw --cpu-rev D --video kbd --panel A --disk elfos.img
python3 -m s5emu --hw --cpu-rev D --panel A --front A      # the front panel on the IO card's ribbon
```

System-5 with the 6845 card **Rev B-Clean-Keyboard** (`hardware/video-6845/kicad/rev-b-clean-keyboard`, 2026-11-20,
not built) in place of the 6845 card and the IO card: Rev B's video with VIDEO-G TEXT's PS/2 keyboard on the same
card. The ROM defaults to `roms/hbios-video-g.rom`, which polls the status at 7804 and reads the key at 7802, the
addresses this card shares with VIDEO-G; it sets the 6845 for 64 x 25.

| What | Model |
|---|---|
| Instruction level | `machine.Video6845KbdMachine` / `Video6845Kbd`: the text RAM at 7000-77FF; the 6845 at 7800 / 7801; the key at 7802 (the read takes it); the status at 7804 (bit 0 KEY-READY, bit 7 = 1); 7800-7807 repeat through 7BFF; nothing at 7806 or 7C00-7FFF. EF3 is KEY-READY |
| `--hw` | `hw.NetlistVideoKbdCard`, **from the card's netlist**: Rev B's gates and the new 74HCT138, '32, '00 and '74 are simulated; the key latch, the status buffer and the ATmega are played on the enables those gates make. `--kbd-flag ef / ef1 / ef2 / ef3 / none` is the card's JP1 (the bus line KEY-READY pulls low). VSYNC and DE in the status read 0 in both models |
| `--video-rev B-Clean` | Rev B-Clean (the card without the keyboard) from its own netlist: on the bus it is Rev B |

Tests: `tests/test_hw_videokbd.py` (the card alone from its netlist; then the ROM, the keyboard, the IO panel and
Elf/OS 5.1.1 on both machines).

## Hardware-faithful mode (`--hw`)

```bash
python3 -m s5emu --hw
```

Every memory cycle goes onto a modelled bus. Each card says whether it drives the data lines, and two drivers at once are logged as contention. The details are in `s5emu/hw.py`.

| Card | How it is modelled |
|---|---|
| Memory | **Gate level, from the card's KiCad netlist** (`hardware/memory/kicad/rev-*/reports/netlist.net`): 4050 buffers, 4042 latches clocked by TPA, 74LS32 bank selects, 74LS151 block muxes, then the CE/OE/WE and address pins of each chip. |
| 6845 (Rev B, the built card) | **Gate level, from its netlist** (`hardware/video-6845/kicad/rev-b`): 74LS373 address latch, a 74LS85 comparing A12-A15 with jumper SV1 (gated by -VMA), then the IDT7134 dual-port RAM's bus port (A11 = 0) or the 6845's register interface (A11 = 1, E = TPB, RS = A0). The character generator and dot clock are not simulated; the netlist proves they cannot reach the bus path. `--video-rev none` = the old behavioural model. |
| IDE/CF (Rev A) | **Gate level, from its netlist** (`hardware/ide-cf/kicad/rev-a`): each INP/OUT runs in four phases (TPA, TPB) through the 74LS138 port decode, the 74LS75 register latch and the NAND-latch INP window; the drive (the CF image) sees DIOR/DIOW and DA0-2/CS0/CS1 on its 40-pin header. Jumpers SV1 = port 2 (select), SV2 = port 3 (data). `--ide-rev none` = behavioural. |
| IO panel card (`--panel A`, 2026-10-30, not built) | **Gate level, from its netlist** (`hardware/io-panel/kicad/rev-a`): the 74HCT138 port 4 decode, the 74HCT374 OUT latch (the LEDs and TIL311s), the 74HCT244 INP enable (its drive played from its OE), INPUT on -EF1, RUN/LOAD on -RESET/-PAUSE, the REQ/ACK/DRIVE flip-flops: one DMA IN per INPUT press in LOAD mode. The CPU core gained `dma_in()`. Shell: `panel [sw HEX \| input \| run on\|off \| load on\|off]`. Use with `--cpu-rev D`: toggle a program in (RUN off, LOAD on, `panel sw`/`panel input` per byte), LOAD off, RUN on, and it runs from 0000 (tests/test_hw.py `IOPanel`). |
| Front panel (`--front A`, with `--panel A`; 2026-11-22, not built) | **Gate level, from its netlist** (`hardware/front-panel/kicad/rev-a`), on the IO panel card's ribbon (`tools/s5panel.py`, pin for pin): its displays and LEDs show what the IO card's latches hold; its toggles, INPUT, RUN and LOAD act through the ribbon; its RESET button pulls -RESET and -DMAIN together, a boot reset, which CPU Rev D's gates decode to clear LOADED; START FROM RAM is its own copy of that flag. The debugger's `front` command works it (`front sw 5A`, `front input`, `front run off`, `front load on`, `front reset`). The IO panel card's own RESET button is `panel reset`, in the fast machine too. -RESET, -PAUSE and -DMAIN are settled among all the cards that pull them (`HWMachine.lines_update()`). **Each switch is played as the netlist wires it** (`hw.switch_contact`, 2026-11-23, both panels): a closed contact sets its net to the level the switch's other pin gives it (the supply it is on, or the supply its net reaches through a resistor), and the IO card takes what the front panel's own nets put on the ribbon (`ribbon_in()`), so a switch wired to the wrong place fails the tests as it would fail on the bench. |
| CPU card Rev D (`--cpu-rev D`, 2026-10-30, not built) | **Gate level, from its netlist** (`hardware/cpu/kicad/rev-d`): 74HCT373 latch (transparent on TPA), the boot flip-flop cleared by CLEAR (= -RESET through two 74HCT14s) and set by the first A15 edge, LOADED (set by LOAD mode, cleared by the RESET/RUN switch, which a machine reset plays), the 74HCT20 F000 window, -VMA and the EPROM enable from a 74HCT00. Jumpers as for the 2005 IO card: JP2 EF1/EF2, JP3 -EF -> EF3. `ccard.mode(reset, pause)` holds -RESET/-PAUSE as a debug board would. HBIOS and ELF/OS boot on it with no bus events (tests/test_hw.py `CPURevD`, `Boot`). |
| CPU card (Rev A) | **Gate level, from its netlist** (`hardware/cpu/kicad/rev-a`), as drawn: 74LS373 address latch, 74LS138 EPROM window (SV2/SV4 from `--rom-base`), the 74LS74 boot flip-flop (cleared by -RESET, set by the first access to the EPROM window, not by any A15 access), SV5 -VMA mode (`--vma remap\|boot\|norom`), the 74LS05 EPROM enable, and JP3/JP4 EF routing (1861 = EF1, keyboard = EF3). The 1802 and the CM1232 reset chip are the emulator's own. The built board's red-wire rework is not modelled yet. `--cpu-rev none` = behavioural. |
| IO (1861, keyboard) (Rev A) | **Gate level, from its netlist** (`hardware/io-1861-keyboard/kicad/rev-a`): the same 74LS138 port decode and INP/OUT strobes as the IDE card; jumper SV2 = the keyboard's CDP1852 port (1), SV6 = the 1861's (4), with a 74LS02 making DISPON (INP) and DISPOFF (OUT). The PIC16F84 + PAK-VI keyboard path and the 1861's DMA timing stay behavioural; the netlist proves the PIC side cannot reach the bus path. `--io-rev none` = behavioural. |

Every card on the bus now comes from its netlist; jumper settings are assumptions until Ken confirms them from the boards (`bus card` lists them). A memory cycle runs in the 1802's three phases (TPA high with the high byte, TPA falls, the low byte with -MRD/-MRW and TPB). Each netlist card is proved at load: every net that can change a bus device's control or address pin is driven only by modelled logic, and the data lines reach only bus devices; otherwise the card refuses to build.

`--mem-rev`:

| Value | Card |
|---|---|
| `D` (default) | **The card of record** for hardware emulation (Ken, 2026-10-06): the Rev D KiCad master in `hardware/memory/kicad/rev-d`. |
| `F` | Rev F (MEM3-F, 2026-11-18, not built; `hardware/memory/kicad/rev-f`): Rev E with EEPROM sockets. A 27C256 in IC3 and IC5, JP2 and JP1 at 1-3 and 2-4 (netlist `jumper` edits), so it decodes, reads and writes as Rev D. |
| `F-28C256` | Rev F with a 28C256 EEPROM in IC5 (`refit`: pin 1 A14, pin 27 !WE), read-only: JP1 3-5, and R6 (47k) holds its !WE high. |
| `F-28C256-W` | The same 28C256 that the CPU can write: JP1 3-5 and 4-6 (its !WE on WR, the RAMs' strobe). A write lands at once; a real 28C256 is busy for up to 10 ms after it. |
| `C` | Rev C (2005). |
| `B-built` | Ken's Rev B board as photographed on 2026-10-05: RAM in IC1, EPROM in IC5, and the red-wire rework putting the 74LS32 bank selects on both `!CE` pins. The rework is netlist edits (`lift`/`wire`) in `MEMORY_REVS`, so a close-up photo can correct it. |
| `B-drawn` | Rev B as drawn, every socket filled. |

Jumpers (`--jumpers`) work on the netlist too: the card tries grounding each header net and records which chip and 4K block it enables (`bus card` lists them).

Debugger additions:

| Command | What it does |
|---|---|
| `bus` | The contention log: `fight` (drivers disagree), `double` (two drivers, same value), `multi-write` (a write lands in two places), `undefined` (a chip control pin is X) |
| `bus map` | Who answers a read in each 4K block, right now |
| `bus card` | The memory card: netlist, rework, empty sockets, jumpers |
| `bus stop fight,double` / `bus stop off` | Stop the run on those events (`--bus-stop` at start) |

What it shows so far (HBIOS 1.0.4, 2026-10-06):

| Card | Result |
|---|---|
| `B-drawn` | Stops on the very first fetch: the CPU EPROM and all four memory chips drive the bus (REVIEW.md finding 1). |
| `B-built` | Boots to `test>`. The RAM in IC1 also answers 7000-7FFF, the 6845 card's block: every video RAM and CRTC write lands in both, and video RAM reads are double-driven (same value, so no fight yet). |
| `C`, `D` | Boot, with no bus events. With memory D and the 6845 card from their netlists, ELF/OS boots and runs `FREE` with no bus events (about 400 s). |

It runs about 40-65 thousand instructions a second, about half the speed of a real 1802; the decode cache makes the netlist cost a one-off per address.

## Debugger commands (both front ends, `-c` and `--script`)

| Command | What it does |
|---|---|
| `s [N]` | Step N instructions |
| `n` | Step over a call (`SEP R4` + address, i.e. SCRT CALL, or a plain `SEP Rn`) |
| `c` | Run (Esc or Pause stops) |
| `until ADDR` | Run to ADDR |
| `b ADDR`, `bd ADDR` / `bd all`, `bl` | Set, delete, list breakpoints. ADDR can be hex, `$hex`, `0x..`, `..h`, a symbol, `R3` or `pc`. |
| `w r\|w\|i\|o ADDR`, `wd`, `wl` | Watch a memory read/write or an I/O port in/out |
| `r` | Registers |
| `set R3=F000` / `set D=12` | Change a register |
| `m ADDR [LEN]` | Memory dump |
| `poke ADDR BYTE...` | Write memory |
| `d [ADDR] [N]` | Disassemble, with symbols and SCRT `CALL`/`RETN` |
| `trace [N]` | The last N instructions executed |
| `stack` | SCRT call stack |
| `screen` | The 6845 screen as text |
| `key TEXT` | Type on the keyboard (`\n` = Enter, `\e` = Esc) |
| `load FILE [ADDR]` | Load Intel hex or binary into RAM |
| `rom FILE`, `romhi FILE` | Load the CPU-card or memory-card EPROM |
| `sym FILE` | Load symbols from an rcasm or A18 listing |
| `disk FILE`, `save` | Attach a disk image; write it back |
| `pixie` | 1861 status |
| `link` | Path of the bus-driver pty |
| `view text\|pixie\|auto` | Terminal only: which picture the screen pane shows (auto shows the 1861 while it's on) |

## Booting ELF/OS

```bash
python3 tools/mkrom.py
```
```bash
python3 tools/mkelfos.py elfos.img --mb 16
```
```bash
python3 -m s5emu --disk elfos.img
```

1. `tools/mkrom.py` builds `roms/hbios-1.0.4.rom`: HBIOS plus Mike Riley's BIOS 1.0.4. It's already in `roms/`.
2. `tools/mkelfos.py` makes a bootable disk: FSGEN, then kernel 0.2.6 build 135, then Mike's programs in `/` and `/BIN`.
3. At `TEST>` type `@FF00` (BIOS boot) and Enter, then press Enter once more. You get `Elf/OS Ready` and `$`.

Notes:
- **Type commands in capitals** (`DIR`, `FREE`): disktool uppercases names when it copies them.
- **The BIOS 0.9 ROM can't run this kernel.** `firmware/hbios/v0.9/sec1.rom` has no `f_isalnum` at FF78, so every command is "File not found".
- **Found while bringing this up:** ELF/OS `DIR` prints 4 names × 16 characters, exactly the 64-column width, and HBIOS loses the first name of the next row at the wrap. So every 5th name is missing. That's in HBIOS, not the emulator.

## Speed and tests

The emulator runs about 0.4–0.7 million instructions per second (a real 1802 at 1.79 MHz runs about 0.11 million). `--speed 223750` throttles it to real time in machine cycles.

```bash
python3 tests/test_cpu.py
```
```bash
python3 tests/test_machine.py
```
```bash
python3 tests/test_hw.py
```

- `test_cpu.py`: 14 instruction tests.
- `test_hw.py`: Rev B's chip-select fault, Rev C's fix, jumpers found from the netlist, the B-built rework, and booting each card.
- `test_machine.py`: the real HBIOS monitor boots, keyboard echo, memory jumpers, CRTC cursor, an 1861 DMA frame byte for byte, IDE read/write, the IDE's CHS addressing and end-of-card errors, HBIOS 1.0.6's disk calls in LBA mode where 1.0.4 and 1.0.5 fail (a boot loader that reads as Elf/OS v5 does), and ELF/OS booting from a fresh disk and running `FREE`.
- `test_web.py`: the browser page's HTTP API as the page uses it: boots running, a typed key echoes, the clock changes, both kinds of state.
- `test_videog.py`: the VIDEO-G model (status, window, pages, CRTC ports, reset, VSYNC, PNG) and the VIDEO-G HBIOS (boot screen, the 24-row line feed and its 47 ms).
- `test_newset.py` (2026-11-20): the new card set together (CPU Rev D, the IO panel, VIDEO-G TEXT + GFX, with the memory and IDE cards) on both machines: the VIDEO-G HBIOS's commands, a program that reaches every new card, a program toggled in from the panel, Elf/OS 5.1.1 with the clock and `vgdemo`; on the hardware machine the bus log must stay empty.
- `test_hw_videog.py`: VIDEO-G TEXT and GFX from their netlists (`hwvideog.py`), cycle by cycle.
- `test_hw_videokbd.py`: the 6845 card Rev B-Clean-Keyboard: the card alone from its netlist, then the ROM, the keyboard, the panel and Elf/OS 5.1.1 on both machines (`--video kbd`).
- `test_buslink_c.py`: `--buslink` speaking BUSDRV-C's protocol with CPU Rev D.

## Files

| File | What it is |
|---|---|
| `s5emu/cpu.py` | The 1802 |
| `s5emu/machine.py` | System-5 cards and memory map |
| `s5emu/disasm.py` | Disassembler |
| `s5emu/debugger.py` | Breakpoints, watches, trace, symbols, SCRT stack |
| `s5emu/shell.py` | The command language |
| `s5emu/tui.py` | Terminal debugger (curses; needs a terminal of at least 110 × 34) |
| `s5emu/web.py`, `s5emu/web/index.html` | The browser page: the Machine and Debugger tabs, and the server behind them |
| `web-start.sh`, `CODESPACE.md`, `../../.devcontainer/` | Starting the page (in the background, with a CF card image made the first time), and the GitHub Codespace |
| `s5emu/buslink.py` | BUSDRV-B protocol on a pty; BUSDRV-C's with CPU Rev D |
| `s5emu/videog.py` | `--video g`: the VIDEO-G card and its machine, the PNG writer |
| `s5emu/hwvideog.py` | `--hw --video g`: VIDEO-G TEXT and GFX from their netlists |
| `s5emu/netlist.py`, `s5emu/logic.py`, `s5emu/hw.py` | `--hw`: KiCad netlist reader with reworks, gate models, the bus and the per-revision memory cards |
| `tools/mkrom.py`, `tools/mkelfos.py` | ROM and disk builders |
| `roms/hbios-1.0.4.rom` / `.hex` | Built ROM |
| `roms/hbios-1.0.5.rom` / `.hex` | HBIOS v1.0.5 (`firmware/hbios/v1.0.5/build.py`): v1.0.4 plus the monitor commands H, B, D (disassembler) and Q1 / Q0; in the machine for a few hours on 2026-11-15 |
| `roms/hbios-1.0.6.rom` / `.hex` | HBIOS v1.0.6 (`firmware/hbios/v1.0.6/build.py`): v1.0.5 with the disk calls always in LBA mode, which Elf/OS v5 needs on a real card; in the machine since 2026-11-15 |
| `roms/hbios-video-g.rom` / `.hex` | HBIOS for VIDEO-G (`firmware/hbios/video-g/build.py`) |
