# Bring-up report: video

2026-10-31 12:27

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

## V1 address decode (block 7 only): PASS

    7000 (video RAM): RAM
    other blocks: nothing answers

## V2 video RAM data lines: PASS

    tested at 7010 with walking ones, walking zeros, 00 FF 55 AA
    all 8 data lines go both ways

## V3 video RAM address lines: PASS

    base 7000; address bits tested: A0 A1 A2 A3 A4 A5 A6 A7 A8 A9 A10
    every tested address bit selects a different byte

## V4 video RAM, all 2K: PASS

    all 2K of video RAM (7000-77FF): address pattern, 55, AA

## V5 CRTC register path: PASS

    cursor registers R14 (6 bits) and R15 written through 7800/7801 and read back, switching registers each time
    R14/R15 hold their values: the CRTC's E (TPB), CS, R/W and RS paths all work
    and it repeats through 7800-7FFF, as drawn (RS = A0)

## V6 HBIOS set-up and test screen: LOOK

    CRTC R0-R15 = HBIOS v1.0.4's table: 94 64 77 8 28 2 16 22 0 8 64 8 0 0 3 192
    On the monitor (composite out, 64 x 16):
      a border of + - | around the whole screen, all four corners visible
      'SYSTEM-5 6845 VIDEO BRING-UP' centred on row 2
      the printable characters on rows 5-7 (space to ?, @ to _, then ` to ~ in lower case: Rev B's goodfont),
      and @ to _ in reverse video on row 9 (a Rev A card's 64-character font shows row 7 as upper case)
      digits 0-9 repeated on row 13, and the cursor blinking at the start of the bottom row
    If the picture rolls or tears: R0-R7 assume BYTE's 9 MHz crystal and /6 character clock; check the crystal.
    If the characters are wrong but the layout is right: the character EPROM (2732, Rev B 'goodfont').
    check by eye: does the monitor show the test screen as described? (run with --interactive to answer here)

