# IDE/CF card: theory of operation

The IDE card connects an IDE drive to the 1802 through two I/O ports, in 8-bit mode. In System-5 the "drive" is a CompactFlash card in a CF-to-IDE adapter, and it holds ELF/OS.
It is Mike Riley's 8-bit IDE design with port-select jumpers added.

- **In the machine: Rev A** (production version, February 2005). KiCad (netlist proven): `hardware/ide-cf/kicad/rev-a/`. No copper gerbers survive; its drill tally matches the 2005 drill file exactly.
- The software side is Mike Riley's BIOS (`firmware/hbios/v1.0.4/orig_bios/bios.asm`: `resetide`, `rdide`, `wrtide`, `bootide`).

## Parts

| Ref | Part | Job |
|---|---|---|
| IC4 | 74LS138 | decodes N0–N2 into ports 1–7 |
| IC1 (74LS04), IC2, IC3 (74LS00), IC5 (74LS32) | | INP/OUT detection and the strobe window (TPA, TPB) |
| SV1 | 2 × 7 header | the register-select port (as built: port 2) |
| SV2 | 2 × 7 header | the data port (as built: port 3) |
| IC6 | 74LS32 | combines the port selects with IN and OUT into the strobes |
| IC7 | 74LS75 | latches the drive register address from D0–D3 |
| JP1 | 2 × 20 header | the 40-pin IDE connector |
| JP2 | 1 × 2 header | |
| LED1 | | power |

## How it works

**I/O decode.** As on the IO card: IC4 (74LS138) decodes N0–N2; gates on -MRD tell `INP` (-MRD high) from `OUT` (-MRD low); a NAND-gate latch set and cleared by TPA and TPB makes the strobe window within the execute cycle. SV1 picks the port line for IDESEL, SV2 the one for IDERW.

**Selecting a register: `OUT 2`.** IDESEL OR OUT (IC6A), inverted, opens the 74LS75 latch (IC7): D0–D3 of the byte written are latched onto the drive's register address lines:

| Data bit | 74LS75 output | IDE signal (header pin) |
|---|---|---|
| D0 | Q1 | DA0 (35) |
| D1 | Q2 | DA1 (33) |
| D2 | Q3 | DA2 (36) |
| D3 | Q4 / !Q4 | CS0 (37) / CS1 (38) |

D3 = 0 asserts CS0, the command block (registers 0–7); D3 = 1 asserts CS1, the control block (so register code 0Eh is the device control register).

**Reading and writing it: port 3.** IDERW OR OUT (IC6B) drives the drive's **DIOW** (pin 23, pulled up); IDERW OR INP (IC6C) drives **DIOR** (pin 25, pulled up). So `OUT 3` writes the byte on the bus into the selected register, and `INP 3` reads the register onto the bus.

**Data.** D0–D7 go straight from the bus to the drive's DD0–DD7 (header pins 17, 15, … 3): no buffer, so the drive's data lines load the bus directly. DD8–DD15 are not used: the drive must be put in 8-bit mode (the BIOS sends SET FEATURES 01).

**Reset.** The bus -RESET goes to the drive's RESET (pin 1).

## Registers

| Code (`OUT 2`) | Read (`INP 3`) | Write (`OUT 3`) |
|---|---|---|
| 0 | data | data |
| 1 | error | features |
| 2 | sector count | sector count |
| 3 | LBA 0–7 | LBA 0–7 |
| 4 | LBA 8–15 | LBA 8–15 |
| 5 | LBA 16–23 | LBA 16–23 |
| 6 | drive/head (LBA 24–27; E0h = master, LBA) | drive/head |
| 7 | status | command |
| 0Eh | alternate status | device control (02h = interrupts off; 06h = software reset) |

Status bits: 80 BSY, 40 DRDY, 20 DF, 10 DSC, 08 DRQ, 01 ERR. Commands the BIOS uses: 20h read sectors, 30h write sectors, ECh identify, EFh set features.

## Jumpers

SV1 and SV2 each connect one of ports 1–7 to the card. No photo of the built card shows them; the BIOS reaches the drive only by `OUT 2` (register select) and `OUT 3` / `INP 3` (data), so SV1 = port 2 and SV2 = port 3 is near certain. The bus driver's bring-up (`bringup.py cf`) confirms it on the real card.

## Known points

- **T6** (`hardware/TIMING-REVIEW.md`): `INP 3` into RAM ends DIOR at TPB's fall while the RAM's write ends a little earlier: +49 ns at 1.76 MHz, failing the worst case from about 2.2 MHz.
- Mike Riley's BIOS also probes for a UART and an RTC on ports 2 and 3, which on System-5 are the IDE registers.
- The bus driver's firmware before 2026-10-11 ran `OUT` without -MRD low, which this card reads as `INP`: fixed (`software/busdrv/BRINGUP.md`).
