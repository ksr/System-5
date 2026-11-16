# Bring-up report: cf

2026-10-30 09:10

## B1 bus driver, bus power, bus master: PASS

    bus driver: Note: bus power on, MONITOR mode / s5-bus-driver blocks-1 io-2 2026-10-11
    bus=on mode=MONITOR
    bus driver is bus master

## B2 control lines idle: WARN

    D=00 A=00 TPA=0 TPB=0 -MRD=1 -MRW=1 -VMA=1 Q=0 N=0 -RESET=1 -INT=0 -EF=1 SP=0
    -INT reads low with nothing asking for it

- On a backplane without pull-ups (the 2009 bus) a released open-collector line floats and reads low here: that is expected. On a bus with pull-ups (Rev D) it means a card holds -INT low or the line is shorted to GND: pull cards one at a time to find which.

## C1 drive status: PASS

    register select OUT 2, data port 3 (IDE card SV1 / SV2)
    status register: 50 (DRDY DSC)

## C2 register data path: PASS

    LBA 0-7 register (3) written and read back: walking ones and zeros, 00 FF 55 AA

## C3 register select (DA0-DA2): PASS

    wrote R2=11 R3=22 R4=44 R5=88, read R2=11 R3=22 R4=44 R5=88

## C4 BIOS set-up: control register, 8-bit mode: PASS

    device control 0E = 02, then status 50 (DRDY DSC)
    SET FEATURES 01 (8-bit transfers): status 50 (DRDY DSC)

## C5 IDENTIFY DEVICE: PASS

    model    16MB CLS
    serial   3A38C04AA1330012
    firmware 3.00
    LBA sectors 31360 (16.1 MB); CHS 490/2/32

## C6 read sector 0: PASS

    LBA 0, first 64 bytes:
      000  90 B3 F8 06 A3 D3 F8 FF B4 F8 E0 A4 F8 FF B5 F8
      010  F1 A5 F8 00 B2 F8 F0 A2 F8 01 A7 F8 03 BF F8 00
      020  AF E2 87 52 64 22 73 F8 00 B7 A8 F8 E0 B8 D4 FF
      030  3C 60 72 A7 17 87 FF 0F 3A 22 F8 03 B0 F8 00 A0
      ... last two bytes 00 82

