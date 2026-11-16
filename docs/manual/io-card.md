# IO card (1861 video and keyboard): theory of operation

The IO card has two independent halves: a PS/2 keyboard interface that delivers ASCII characters through a CDP1852 input port, and a CDP1861 "Pixie" graphics chip with composite video out.
The machine uses the keyboard; the 1861 half has never been tested, and on the built card it is not on any port.

- **In the machine: Rev A** (ordered 2005-01-04, NoTouch 17593-iNTJ). KiCad (netlist proven, copper = the 2005 order gerbers): `hardware/io-1861-keyboard/kicad/rev-a/`.
- PIC firmware (PS/2 serial to parallel): `hardware/io-1861-keyboard/pic-ps2-firmware/`.
- **It depends on the CPU card.** The 1861 needs the CPU clock, DMA OUT, the state codes and its own EF line, which are not on the bus; they come over a ribbon from the CPU card's SV3. A standalone CPU card redesign comes first (`BACKLOG.md`); the next 6845 card revision is to take over the PS/2 keyboard.

## Parts

| Ref | Part | Job |
|---|---|---|
| X1 | 6-pin mini-DIN | PS/2 keyboard |
| U$5, U$6 | PAK-VI, resonator | PS/2 keyboard decoder: keyboard clock and data in, ASCII out on a serial line (TX) |
| IC1, Q1 | PIC16F84, crystal | serial to parallel: receives the PAK-VI's serial ASCII on RA0, puts it on RB0–RB7 and strobes the 1852 on RA2 |
| U$1 | CDP1852 | 8-bit input port: holds the character for the 1802 and raises SR (service request) |
| IC12 | 74LS138 | decodes N0–N2 into ports 1–7 |
| IC11 (74LS04), IC13 (74LS32), IC14, IC15 (74LS00), IC16 (74LS02) | | the INP/OUT decode and strobe window; port select for the 1852 and the 1861 |
| SV2 | 2 × 7 header | the keyboard's port (as built: port 1) |
| SV6 | 2 × 7 header | the 1861's port (as built: empty) |
| SV1 | 1 × 3 header | where the keyboard flag goes: 2-3 = bus -EF (as built), 1-2 = the ribbon (KEF) |
| U$3 | CDP1861 | graphics: DMA video from memory, sync, interrupt, EF |
| IC2 | 74LS74 | remembers display on/off (LED4) |
| U$4, R13–R15 | RCA jack, mix resistors | 1861 composite video out |
| SV3 | 2 × 8 header | ribbon to the CPU card |
| LED1–LED5 | | power; 1852 SR (character waiting); PIC activity; 1861 display on; PAK-VI data available |

## The keyboard path

1. The PS/2 keyboard's clock and data go to the PAK-VI (a preprogrammed PIC keyboard decoder), which turns key presses into ASCII and sends each character as a serial byte on its TX pin.
2. The PIC16F84 (IC1) receives that byte on RA0, puts it on RB0–RB7 (the 1852's DI0–DI7) and pulses RA2, the 1852's CLK. The code for it is in `pic-ps2-firmware/`.
3. The CDP1852 (U$1, input mode) latches the byte and sets its **SR** output: a character is waiting. SR lights LED2 and goes to SV1: with SV1 on 2-3 it drives the bus **-EF** line, which the CPU card's JP1 routes to **EF3**.
4. The program waits for EF3 and executes `INP 1`. The 1852 is selected when CS1 (the port select, from SV2 through an inverter) and CS2 (-MRD, high during an `INP`) are both high; it drives the character onto the data bus, the 1802 stores it in memory and D, and reading the port clears SR.

HBIOS does exactly this (`inchar`: `BN3 inchar`, then `INP 1`).

## The I/O decode

IC12 (74LS138) decodes N0–N2: output Y0 is active when N = 0 (no I/O instruction), Y1–Y7 when an `INP n` / `OUT n` is under way. Gates on -MRD split I/O cycles into **IN** (-MRD high: `INP`) and **OUT** (-MRD low: `OUT`), and a NAND-gate latch driven by TPA and TPB limits them to the instruction's execute cycle.
SV2 connects one port line to the 1852's select; SV6 connects one port line to the 1861 logic. The IDE card uses the same circuit.

## The 1861 half

The CDP1861 makes a 64 × 128 (or 64 × 32) dot display by DMA: during each line it asks the 1802 for 8 bytes with DMA OUT, and the 1802 reads them from memory onto the bus, where the 1861 shifts them out as dots.

- **Clock, state codes, DMA, EF:** over the SV3 ribbon from the CPU card: LCLK (the inverted CPU clock), SC0 and SC1, DMA OUT (to the CPU), EFV (the 1861's EF, to the CPU's JP3).
- **Interrupt:** the 1861 drives the bus -INT before each frame, so the program can set up R0 for the DMA.
- **On and off:** with a port fitted on SV6, `INP n` asserts DISPLAY ON and `OUT n` DISPLAY OFF (a 74LS02 combines the port with IN or OUT); IC2 records which, for LED4.
- **Video:** VIDEO and SYNC through R13/R14 and R15 to the RCA jack.

On the built card SV6 and the CPU card's JP3 are empty, so the 1861 never turns on. The emulator can model it on port 4 (`--io-rev A-1861`).

## Headers

| Header | What |
|---|---|
| SV1 | keyboard flag: 1-2 to the ribbon (KEF), 2-3 to the bus -EF |
| SV2 | keyboard port (one of ports 1–7) |
| SV3 | ribbon to the CPU card's SV3 |
| SV6 | 1861 port |

## Known points

- The CDP1852's CS1 is taken as active high from the 2005 Eagle library symbol; there is no 1852 datasheet in `../private-resources/elf/reference/` to confirm it (`BACKLOG.md`).
- The 1861 has never been run on this card.
