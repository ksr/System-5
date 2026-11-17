# VIDEO-G 1.0 TEXT - bill of materials

Written by `hardware/video-g/kicad/common/bom.py` from `gen/netlist.py` (2026-11-17). Every IC goes in a socket.

| Qty | Value | Footprint | References | What to buy |
|---|---|---|---|---|
| 1 | 74HCT373 | DIP-20_W7.62mm_Socket | IC1 | 74HCT373 (CMOS inputs: no load on the 1802's address lines) |
| 1 | 74LS85 | DIP-16_W7.62mm_Socket | IC2 |  |
| 1 | IDT7134 | DIP-48_W15.24mm_Socket | IC3 | IDT7134SA or LA, 55-90 ns, DIP-48 (600 mil); the 6845 card's chip also fits |
| 1 | HD68B45SP | DIP-40_W15.24mm_Socket | IC4 | HD68B45SP (Hitachi) or MC68B45P (Motorola): the 2 MHz grade is needed, for the write E pulse (284 ns at 1.76 MHz, DESIGN.md section 4); the 6845 card's 1 MHz HD6845 is too slow for it |
| 3 | 74HCT138 | DIP-16_W7.62mm_Socket | IC5, IC6, IC7 | 74HCT138 (CMOS inputs on the bus address) |
| 1 | 74LS244 | DIP-20_W7.62mm_Socket | IC8 |  |
| 1 | 74HCT374 | DIP-20_W7.62mm_Socket | IC9 |  |
| 1 | ATmega328P-PU | DIP-28_W7.62mm_Socket | IC10 | ATmega328P-PU with the Arduino Uno bootloader burned (ISP) before fitting |
| 1 | 74LS374 | DIP-20_W7.62mm_Socket | IC11 |  |
| 1 | AT28C64B-15 | DIP-28_W15.24mm_Socket | IC12 | AT28C64B-15PU (Microchip), burned on the T48 with firmware/video-g-chargen/video-g-chargen.bin |
| 1 | 74LS166 | DIP-16_W7.62mm_Socket | IC13 |  |
| 1 | 74LS175 | DIP-16_W7.62mm_Socket | IC14 |  |
| 1 | 74F163A | DIP-16_W7.62mm_Socket | IC15 | 74F163A or 74ALS163B (V2.0 review R3-1: CHARCLOCK set-up to the 166's SH/-LD); keep a spare |
| 2 | 74LS04 | DIP-14_W7.62mm_Socket | IC16, IC17 |  |
| 1 | 74HCT08 | DIP-14_W7.62mm_Socket | IC18 |  |
| 1 | 74LS08 | DIP-14_W7.62mm_Socket | IC19 |  |
| 1 | 74LS32 | DIP-14_W7.62mm_Socket | IC20 |  |
| 1 | 74LS10 | DIP-14_W7.62mm_Socket | IC21 |  |
| 1 | 74LS86 | DIP-14_W7.62mm_Socket | IC22 |  |
| 1 | 7416 | DIP-14_W7.62mm_Socket | IC23 |  |
| 1 | 74HCT74 | DIP-14_W7.62mm_Socket | IC24 |  |
| 1 | 12MHz | Crystal_HC49-U_Vertical | Y1 | 12 MHz, HC-49/U |
| 1 | 16MHz | Crystal_HC49-U_Vertical | Y2 | 16 MHz, HC-49/U, 18-20 pF load |
| 1 | System-5 bus | C30 | J1 |  |
| 1 | RCA | RCA | J2 | RCA jack, right-angle PCB mount (YACC1 V1.0 card's footprint) |
| 1 | DB9 F | F09HP | J3 | DE-9 female, right-angle PCB mount (F09HP footprint: 2.74 mm pitch, 2.54 mm between rows) |
| 1 | KEYBOARD | MiniDIN6_MD-60SM | J4 | Same Sky (CUI Devices) MD-60SM, date code after 2022-03-03 |
| 1 | FTDI | PinHeader_1x06_P2.54mm_Vertical | J5 | 1 x 6 pin header, 2.54 mm (an FTDI cable programs the ATmega) |
| 1 | TO GFX | IDC-Header_2x20_P2.54mm_Vertical | J6 | 2 x 20 shrouded box header, 2.54 mm; 40-way IDC ribbon (two 2 x 20 IDC sockets, about 10 cm) |
| 1 | BLOCK | PinHeader_2x04_P2.54mm_Vertical | SV1 | 2 x 4 pin header + 1 shunt on 1-2 (block 7, 7000); each fitted shunt is a 0 bit |
| 1 | MONITOR | PinHeader_1x03_P2.54mm_Vertical | JP1 | 1 x 3 pin header + shunt: 1-2 NTSC, 2-3 IBM 5151 |
| 1 | VSYNC | PinHeader_1x03_P2.54mm_Vertical | JP2 | 1 x 3 pin header + shunt: 1-2 +VSYNC, 2-3 -VSYNC (5151) |
| 1 | KBD-EF | PinHeader_1x02_P2.54mm_Vertical | JP3 | 1 x 2 pin header + shunt: fitted = the keyboard flag on the bus -EF |
| 1 | 0.5A PTC | Fuse_Bourns_MF-RHT050 | F1 | Bourns MF-RHT050 (0.5 A hold, radial) |
| 1 | PWR | LED_D5.0mm | LED1 |  |
| 1 | 10k x4 | R_Array_SIP5 | RN1 | 10k x4 BUSSED, pin 1 common, 5-pin SIP (e.g. Bourns 4605X-101-103LF) |
| 2 | 10k x5 | R_Array_SIP6 | RN2, RN3 | 10k x5 BUSSED, pin 1 common, 6-pin SIP (e.g. Bourns 4606X-101-103LF) |
| 3 | 1k | R_Axial_DIN0207_L6.3mm_D2.5mm_P2.54mm_Vertical | R1, R2, R3 | 1/4 W metal film, mounted standing |
| 4 | 33 | R_Axial_DIN0207_L6.3mm_D2.5mm_P2.54mm_Vertical | R4, R11, R12, R13 | 1/4 W metal film, mounted standing |
| 1 | 270 | R_Axial_DIN0207_L6.3mm_D2.5mm_P2.54mm_Vertical | R5 | 1/4 W metal film, mounted standing |
| 1 | 330 | R_Axial_DIN0207_L6.3mm_D2.5mm_P2.54mm_Vertical | R6 | 1/4 W metal film, mounted standing |
| 1 | 10k | R_Axial_DIN0207_L6.3mm_D2.5mm_P2.54mm_Vertical | R7 | 1/4 W metal film, mounted standing |
| 3 | 4.7k | R_Axial_DIN0207_L6.3mm_D2.5mm_P2.54mm_Vertical | R8, R9, R10 | 1/4 W metal film, mounted standing |
| 26 | 100n | C025-050X050 | C1, C2, C3, C4, C5, C6, C7, C8, C9, C10, C11, C12, C13, C14, C15, C16, C17, C18, C19, C20, C21, C22, C23, C24, C25, C27 | ceramic X7R, 50 V, 0.1 in (2.54 mm) lead spacing |
| 1 | 47u 16V | CP_Radial_D6.3mm_P2.50mm | C26 | 47 uF electrolytic, 16 V or more, radial 6.3 mm, 2.5 mm pitch |
| 2 | 22p | C025-050X050 | C28, C29 | ceramic C0G (NP0), 50 V, 0.1 in lead spacing |

**IC sockets:** 9 x DIP-14, 300 mil, 7 x DIP-16, 300 mil, 4 x DIP-20, 300 mil, 1 x DIP-28, 300 mil, 1 x DIP-28, 600 mil, 1 x DIP-40, 600 mil, 1 x DIP-48, 600 mil

**Jumper shunts:** 4 x 2.54 mm, one each for JP1, JP2, JP3, SV1.

Totals: 24 ICs, 83 parts.
