# 6845 video Rev B (the 2005 card): first bring-up from the bus driver, 2026-10-31

BUSDRV-B in the 2009 backplane, CPU card out. `software/busdrv/bringup.py video` (6 pass, 1 warn, 0 fail, 1 to check by eye): report `2026-10-31-bringup-report.md`.

| Result | |
|---|---|
| Decode | the card answers in block 7 only (SV1 1-2 confirmed) |
| Video RAM 7000–77FF | **good**: all 8 data lines, A0–A10, all 2K with address pattern, 55 and AA |
| CRTC | R14/R15 written and read back through 7800/7801, repeating through 7800–7FFF (RS = A0): E (TPB), CS, R/W and RS all work |
| Test screen | **works** (Ken, 2026-10-31): HBIOS v1.0.4's CRTC table, 9 MHz crystal (Ken), test screen on the monitor. Blank at first: the 6845's RESET (IC3 pin 2) comes straight from bus -RESET (pin 27), and with the CPU card out nothing holds it high (the bus driver's -RESET is open-collector, the 2009 backplane has no pull-up), so the CRTC stayed in reset (registers still read and write). A 10k from bus pin 27 to pin 1 (+5 V) fixed it; the IDE card also pulls -RESET high |
| −RESET, −INT, −EF | read low: no pull-ups on the 2009 backplane (expected) |
