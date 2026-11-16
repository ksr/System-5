# VIDEO-G 1.0 GFX - bill of materials

Written by `hardware/video-g/kicad/common/bom.py` from `gen/netlist.py` (2026-11-01). Every IC goes in a socket.

| Qty | Value | Footprint | References | What to buy |
|---|---|---|---|---|
| 1 | AS6C62256-55 | DIP-28_W15.24mm_Socket | IC1 | AS6C62256-55PCN (Alliance, 55 ns, 600-mil DIP-28); not a 300-mil 'skinny' 62256 |
| 4 | 74HCT157 | DIP-16_W7.62mm_Socket | IC2, IC3, IC4, IC5 | 74HCT157 (CMOS inputs: no load on the 1802's address lines) |
| 3 | 74HCT374 | DIP-20_W7.62mm_Socket | IC6, IC10, IC12 |  |
| 1 | 74HCT244 | DIP-20_W7.62mm_Socket | IC7 |  |
| 1 | 74LS374 | DIP-20_W7.62mm_Socket | IC8 |  |
| 1 | 74LS166 | DIP-16_W7.62mm_Socket | IC9 |  |
| 1 | ATmega328P-PU | DIP-28_W7.62mm_Socket | IC11 | ATmega328P-PU with the Arduino Uno bootloader burned (ISP) before fitting |
| 1 | 74HCT74 | DIP-14_W7.62mm_Socket | IC13 |  |
| 1 | 74LS04 | DIP-14_W7.62mm_Socket | IC14 |  |
| 1 | 74LS05 | DIP-14_W7.62mm_Socket | IC15 |  |
| 1 | 74LS08 | DIP-14_W7.62mm_Socket | IC16 |  |
| 1 | 74LS20 | DIP-14_W7.62mm_Socket | IC17 |  |
| 1 | 74LS32 | DIP-14_W7.62mm_Socket | IC18 |  |
| 1 | 74HCT273 | DIP-20_W7.62mm_Socket | IC19 |  |
| 1 | 16MHz | Crystal_HC49-U_Vertical | Y1 | 16 MHz, HC-49/U, 18-20 pF load |
| 1 | System-5 bus | C30 | J1 |  |
| 1 | MOUSE | MiniDIN6_MD-60SM | J2 | Same Sky (CUI Devices) MD-60SM, date code after 2022-03-03 |
| 1 | FTDI | PinHeader_1x06_P2.54mm_Vertical | J3 | 1 x 6 pin header, 2.54 mm (an FTDI cable programs the ATmega) |
| 1 | FROM TEXT | IDC-Header_2x20_P2.54mm_Vertical | J4 | 2 x 20 shrouded box header, 2.54 mm (the ribbon comes with the TEXT board's) |
| 1 | 0.5A PTC | Fuse_Bourns_MF-RHT050 | F1 | Bourns MF-RHT050 (0.5 A hold, radial) |
| 1 | 10k x8 | R_Array_SIP9 | RN1 | 10k x8 BUSSED, pin 1 common, 9-pin SIP (e.g. Bourns 4609X-101-103LF) |
| 2 | 10k | R_Axial_DIN0207_L6.3mm_D2.5mm_P2.54mm_Vertical | R1, R3 | 1/4 W metal film, mounted standing |
| 4 | 4.7k | R_Axial_DIN0207_L6.3mm_D2.5mm_P2.54mm_Vertical | R2, R4, R5, R6 | 1/4 W metal film, mounted standing |
| 21 | 100n | C025-050X050 | C1, C2, C3, C4, C5, C6, C7, C8, C9, C10, C11, C12, C13, C14, C15, C16, C17, C18, C19, C20, C21 | ceramic X7R, 50 V, 0.1 in (2.54 mm) lead spacing |
| 1 | 47u 16V | CP_Radial_D6.3mm_P2.50mm | C22 | 47 uF electrolytic, 16 V or more, radial 6.3 mm, 2.5 mm pitch |
| 2 | 22p | C025-050X050 | C23, C24 | ceramic C0G (NP0), 50 V, 0.1 in lead spacing |

**IC sockets:** 6 x DIP-14, 300 mil, 5 x DIP-16, 300 mil, 6 x DIP-20, 300 mil, 1 x DIP-28, 600 mil, 1 x DIP-28, 300 mil

Totals: 19 ICs, 56 parts.
