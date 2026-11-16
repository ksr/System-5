# Bring-up report: memory

2026-10-30 08:31

## B1 bus driver, bus power, bus master: PASS

    bus driver: Note: bus power on, MONITOR mode / s5-bus-driver blocks-1 io-2 2026-10-11
    bus=on mode=MONITOR
    bus driver is bus master

## B2 control lines idle: WARN

    D=00 A=00 TPA=0 TPB=0 -MRD=1 -MRW=1 -VMA=1 Q=0 N=0 -RESET=0 -INT=0 -EF=0 SP=0
    -RESET reads low with nothing asking for it
    -INT reads low with nothing asking for it
    -EF reads low with nothing asking for it
    (a low -RESET also holds the 6845 in reset: the CRTC steps would fail)

- On a backplane without pull-ups (the 2009 bus) a released open-collector line floats and reads low here: that is expected. On a bus with pull-ups (Rev D) it means a card holds -RESET low or the line is shorted to GND: pull cards one at a time to find which.

- On a backplane without pull-ups (the 2009 bus) a released open-collector line floats and reads low here: that is expected. On a bus with pull-ups (Rev D) it means a card holds -INT low or the line is shorted to GND: pull cards one at a time to find which.

- On a backplane without pull-ups (the 2009 bus) a released open-collector line floats and reads low here: that is expected. On a bus with pull-ups (Rev D) it means a card holds -EF low or the line is shorted to GND: pull cards one at a time to find which.

## M1 block map against the jumpers: FAIL

    memory Rev B-built, jumpers RRRRRRR-EEEEEEE- (block 0 first; R = RAM, E = EPROM, - = open)
    on Rev B-built the jumpers do nothing: its rework wires each chip select. The expected map below is what its netlist decodes.
    7000: expected RAM (IC1), found nothing
    9000: expected EPROM (IC5), found unstable
    A000-FFFF: expected EPROM (IC5), reads FF: not fitted, blank, or not selected
    block  expected found
    0000  RAM      RAM      ok
    1000  RAM      RAM      ok
    2000  RAM      RAM      ok
    3000  RAM      RAM      ok
    4000  RAM      RAM      ok
    5000  RAM      RAM      ok
    6000  RAM      RAM      ok
    7000  RAM      nothing  FAIL
    8000  ROM      ROM      ok
    9000  ROM      unstable FAIL
    A000  ROM      nothing  WARN
    B000  ROM      ROM      ok
    C000  ROM      nothing  WARN
    D000  ROM      ROM      ok
    E000  ROM      nothing  WARN
    F000  ROM      nothing  WARN

- RAM missing: check IC1's jumper for the block ((no jumper: wired)), IC1 in its socket (pin 1, bent pins), its select mux IC2 (74x151), and the 74LS32 that gates its !CE.

- EPROM reads FF: is IC5 fitted and programmed? A blank EPROM reads FF everywhere, so an empty socket and a blank chip look the same here.

## M2 data lines (RAM): PASS

    tested at 0010 with walking ones, walking zeros, 00 FF 55 AA
    all 8 data lines go both ways

## M3 address lines (RAM): PASS

    base 0000; address bits tested: A0 A1 A2 A3 A4 A5 A6 A7 A8 A9 A10 A11 A12 A13 A14
    every tested address bit selects a different byte

## M4 RAM test (quick): PASS

    quick test: 3 x 64 bytes in each RAM block, address pattern, 55, AA (--full tests every byte)

## M5 EPROM read: FAIL

    8000-80FF  sum 71A2  first bytes C2 B0 05 D4 4D F2 0E 93
    8000: two reads of the same bytes differ
    9000-90FF  sum 9058  first bytes F9 5F B2 F8 FF B2 EA F8
    9000: two reads of the same bytes differ
    A000-A0FF  sum FF00  blank (all FF)
    B000-B0FF  sum 9888  first bytes 9D 8F 77 DF 7F F8 15 FF
    B000: two reads of the same bytes differ
    C000-C0FF  sum B6A8  first bytes 31 06 0E 03 07 F4 9B BF
    C000: two reads of the same bytes differ
    D000-D0FF  sum 9B15  first bytes 31 06 0C 13 0F F4 F8 68
    D000: two reads of the same bytes differ
    E000-E0FF  sum B9D6  first bytes 30 16 0C 03 07 F4 9A FF
    E000: two reads of the same bytes differ
    F000-F0FF  sum 3F42  first bytes FF FF FF FF FF FF FF FF
    F000: two reads of the same bytes differ
    (the first 256 bytes of each block; --full, --rom or --save-rom read all 4K)

- Unstable EPROM reads: a slow EPROM is fine at this speed, so suspect a loose socket, a floating !OE or !CE, or two parts driving the bus.

## M6 chip-select LEDs: LOOK

    (Rev B-built: its LEDs are driven by a 74LS00, IC10; each should still light with its chip)
    the LED for IC1 (IC1 62256 RAM): reading 0000 for 3 s now - the LED for IC1 should glow, the other chip LEDs stay dark
    the LED for IC5 (IC5 27256 EPROM): reading 8000 for 3 s now - the LED for IC5 should glow, the other chip LEDs stay dark
    check by eye: did each chip's LED glow while it was read, and only then? (run with --interactive to answer here)

