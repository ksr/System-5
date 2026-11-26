# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-20
"""keyboard.py - what Rev B-Clean-Keyboard adds to Rev B-Clean, as data for gen/make_schematic.py, gen/make_board.py
and gen/silk.py. Ken, 2026-11-20: "add keyboard support to Rev B Clean, Call it Rev-b-clean-keyboard. Look at video-g
for keyboard section only. Expand bus to the 36 pin bus and add jumpers required to access keyboard. Rev-b-clean-keyboard
and Video-g will never be used at the same time", and, asked how the CPU should read it: memory-mapped, as VIDEO-G.

THE MAP (block 7, SV1 as on Rev B):
  7000-77FF  the text RAM, as Rev B
  7800/7801  the 6845 (address register / data), as Rev B and as VIDEO-G. Rev B's 6845 answers all of 7800-7FFF; here
             its select is narrowed to A10 = 0, A2 = A1 = 0, so the pair repeats every 8 addresses through 7BFF
  7802       the key (read; the read clears KEY-READY at TPB)                                  \\ where VIDEO-G TEXT has
  7804       status (read): bit 0 KEY-READY, 2 VSYNC, 3 DE, 7-6 = 10; bits 1, 4, 5 are 0        / them, so its HBIOS's
             (no mouse, the NTSC format, no GFX board)                                           keyboard code runs here
  7806, 7C00-7FFF  nothing (VIDEO-G's mouse / Y register and graphics window); writes to 7802-7807 do nothing
KEY-READY also pulls one bus flag line low: JP1 KBD FLAG picks -EF1, -EF2, -EF3 or -EF.

THE 6845 IS WRITE-ONLY (Ken, 2026-11-24: "Write-only"): its R/W is on ground and its E is NOT -MRW (CRTE: IC18A, the
spare half of the 74HCT74, as an inverter). On Rev B R/W is -MRW and E is TPB, which ends every register write in a
read (hardware/TIMING-REVIEW.md, T2) and has the 6845 drive the bus at TPB of a cycle with no memory access
(RELABEL below; software/s5emu/tests/test_hw_crtcbus.py). 7800 / 7801 read as nothing (FF on the bus Rev D).

THE KEYBOARD SECTION is VIDEO-G TEXT's (hardware/video-g/kicad/text-1.0/gen/netlist.py), part for part and pin for pin,
so its ATmega firmware (embedded/video-g-ps2) runs unchanged: the ATmega328P reads the PS/2 keyboard and puts each
key's code on MD0-7; its LDDATA edge clocks the code into the key latch and sets KEY-READY; a read of 7802 puts the
latch on the data bus and, at TPB, clears KEY-READY, as -RESET does. What differs from TEXT is only the decode (TEXT has
its own for the whole card; this card keeps Rev B's and adds one 74HCT138), and which spare gates do the small jobs:
  IC15 74HCT138   enabled by Rev B's upper-half select (-UPPER: block and A11, the net that was the 6845's -CS) and
                  A10 low; A1, A2 pick: Y0 the 6845's -CS, Y1 the key, Y2 status
  IC16 74HCT32    -RDKEY and -RDSTAT (the selects while -MRD is low); KRDT (-RDKEY while TPB is high)
  IC17 74HCT00    NOT TPB; RESETH = NOT -RESET (for IC22); KCLR = KRDT AND -RESET (two gates)
  IC18 74HCT74    KEY-READY (its second half); its first half is the 6845's E: -CLR on ground and -MRW on -PRE make Q
                  high while -MRW is low, and low otherwise (no state: the flip-flop's own data sheet, both low: Q high)
  IC19 74HCT374   the key latch
  IC20 74HCT244   the status byte
  IC21 ATmega328P the keyboard controller, with Y1 16 MHz, the FTDI header J4 and the PS/2 jack J3
  IC22 7416       the two open-collector jobs, on the gates TEXT's 7416 (its IC23) uses for them: gate D (pins 9, 8)
                  pulls the flag line low while KEY-READY, gate F (13, 12) pulls the ATmega's reset low while the bus
                  -RESET is low; the other four gates' inputs are on ground. Rev B's own 7416 (IC14) has three spare
                  gates, but their inputs are tied to ground by copper that carries ground on to other parts (pads 9,
                  11 and 13 of IC14 are each a link in that chain), so this card has a second one. First drawn with
                  two 2N7000s (Q2, Q3); Ken, 2026-11-20, asked which he would have: "swap". A 7406, a 7405 or a
                  74HC05 has the same pins and does the same in this socket
"""
OLD, NEW = "video-6845-rev-b-clean", "video-6845-rev-b-clean-keyboard"
REV, DATE = "B-Clean-Keyboard", "2026-11-24"
LIB = NEW + "-eagle"                                    # this card's own symbol and footprint library

DIP = "Package_DIP:DIP-%d_W7.62mm_Socket"
FP_R = "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P2.54mm_Vertical"     # standing, as VIDEO-G's and memory Rev F's
FP_C = LIB + ":C025-050X050"                             # 0.1 inch lead spacing: Ken's bypass-cap rule

# reference: (value, symbol, footprint, what it does)
PARTS = {
    "IC15": ("74HCT138", "74xx:74LS138", DIP % 16, "register select in 7800-7BFF: the 6845, the key, status"),
    "IC16": ("74HCT32", "74xx:74LS32", DIP % 14, "read enables; key-read strobe"),
    "IC17": ("74HCT00", "74xx:74LS00", DIP % 14, "NOT TPB, -RESET buffer, KEY-READY clear"),
    "IC18": ("74HCT74", "74xx:74LS74", DIP % 14, "KEY-READY; the 6845's E (NOT -MRW)"),
    "IC19": ("74HCT374", "74xx:74LS374", DIP % 20, "key latch, read at 7802"),
    "IC20": ("74HCT244", "74xx:74LS244", DIP % 20, "status, read at 7804"),
    "IC21": ("ATmega328P-PU", "MCU_Microchip_ATmega:ATmega328P-P", DIP % 28, "PS/2 keyboard controller"),
    "Y1":   ("16MHz", "Device:Crystal", "Crystal:Crystal_HC49-U_Vertical", "ATmega clock"),
    "IC22": ("7416", "74xx:74LS05", DIP % 14, "open collector: KEY-READY onto the flag line, the bus -RESET onto the ATmega's reset"),
    "J3":   ("KEYBOARD", "video-g-local:MINIDIN6", LIB + ":MiniDIN6_MD-60SM", "PS/2 keyboard (Same Sky MD-60SM)"),
    "J4":   ("FTDI", "Connector_Generic:Conn_01x06", "Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical",
             "GND CTS VCC(nc) TXD RXD DTR: ATmega bootloader"),
    "JP1":  ("KBD FLAG", "Connector_Generic:Conn_02x04_Odd_Even", "Connector_PinHeader_2.54mm:PinHeader_2x04_P2.54mm_Vertical",
             "one shunt: KEY-READY onto -EF1, -EF2, -EF3 or -EF"),
    "F1":   ("0.5A PTC", "Device:Polyfuse", "Fuse:Fuse_Bourns_MF-RHT050", "keyboard +5 V"),
    "R7":   ("10k", "Device:R", FP_R, "ATmega reset pull-up"),
    "R8":   ("4.7k", "Device:R", FP_R, "keyboard clock pull-up"),
    "R9":   ("4.7k", "Device:R", FP_R, "keyboard data pull-up"),
    "R10":  ("10k", "Device:R", FP_R, "LDDATA pull-up (no ATmega fitted: no key)"),
    "R11":  ("10k", "Device:R", FP_R, "bus -EF pull-up (the 2009 backplane has none)"),
    "C16":  ("0.1uF", "Device:C", FP_C, "IC15"), "C17": ("0.1uF", "Device:C", FP_C, "IC16"),
    "C18":  ("0.1uF", "Device:C", FP_C, "IC17"), "C19": ("0.1uF", "Device:C", FP_C, "IC18"),
    "C20":  ("0.1uF", "Device:C", FP_C, "IC19"), "C21": ("0.1uF", "Device:C", FP_C, "IC20"),
    "C22":  ("0.1uF", "Device:C", FP_C, "IC21"), "C23": ("0.1uF", "Device:C", FP_C, "IC21 AVCC"),
    "C27":  ("0.1uF", "Device:C", FP_C, "IC22"),
    "C24":  ("0.1uF", "Device:C", FP_C, "FTDI DTR auto-reset"),
    "C25":  ("22pF", "Device:C", FP_C, "Y1 load"), "C26": ("22pF", "Device:C", FP_C, "Y1 load"),
}

D8 = ((3, 2), (4, 5), (7, 6), (8, 9), (13, 12), (14, 15), (17, 16), (18, 19))    # (D, Q) of a 74x374's bits 0..7
A244 = ((2, 18), (4, 16), (6, 14), (8, 12), (11, 9), (13, 7), (15, 5), (17, 3))   # (A, Y) of a 74x244's bits 0..7
STATUS = ("KREADY", "GND", "VSYNC", "DE", "GND", "GND", "GND", "VCC")              # bits 0..7: 10xx 0x0k

# every pin of every new part: reference -> {pin: net}; a pin not named here is left open (a no-connect mark)
PINS = {
    "IC15": {1: "ADDR1", 2: "ADDR2", 3: "GND", 4: "-UPPER", 5: "ADDR10", 6: "VCC", 15: "-CRTCCS", 14: "-SELKEY",
             13: "-SELSTAT", 16: "VCC", 8: "GND"},
    "IC16": {1: "-SELKEY", 2: "-MRD", 3: "-RDKEY", 4: "-SELSTAT", 5: "-MRD", 6: "-RDSTAT", 9: "-RDKEY", 10: "TPBN",
             8: "KRDT", 12: "GND", 13: "GND", 14: "VCC", 7: "GND"},
    "IC17": {1: "TPB", 2: "TPB", 3: "TPBN", 4: "-RESET", 5: "-RESET", 6: "RESETH", 9: "KRDT", 10: "-RESET", 8: "KCLRN",
             12: "KCLRN", 13: "KCLRN", 11: "KCLR", 14: "VCC", 7: "GND"},
    "IC18": {1: "GND", 4: "-MRW", 5: "CRTE", 2: "GND", 3: "GND", 13: "KCLR", 12: "VCC", 11: "LDDATA", 10: "VCC", 9: "KREADY",
             14: "VCC", 7: "GND"},
    "IC19": dict([(1, "-RDKEY"), (11, "LDDATA"), (20, "VCC"), (10, "GND")]
                 + [(d, "MD%d" % i) for i, (d, q) in enumerate(D8)] + [(q, "CPUDATA%d" % i) for i, (d, q) in enumerate(D8)]),
    "IC20": dict([(1, "-RDSTAT"), (19, "-RDSTAT"), (20, "VCC"), (10, "GND")]
                 + [(a, STATUS[i]) for i, (a, y) in enumerate(A244)] + [(y, "CPUDATA%d" % i) for i, (a, y) in enumerate(A244)]),
    "IC21": dict([(1, "MRST"), (2, "FTX"), (3, "FRX"), (4, "KCLK"), (6, "KDAT"), (7, "VCC"), (8, "GND"), (9, "XT1"),
                  (10, "XT2"), (12, "LDDATA"), (16, "KREADY"), (20, "VCC"), (22, "GND")]
                 + [(p, "MD%d" % i) for i, p in enumerate((23, 24, 25, 26, 27, 28, 14, 15))]),
    "Y1": {1: "XT1", 2: "XT2"},
    # the 7416, a hex inverter with open-collector outputs (1A 1Y 2A 2Y 3A 3Y GND 4Y 4A 5Y 5A 6Y 6A VCC): a high input
    # pulls its output low. Gates D and F as on VIDEO-G TEXT; the four spare inputs on ground, their outputs open
    "IC22": {9: "KREADY", 8: "EFOC", 13: "RESETH", 12: "MRST", 1: "GND", 3: "GND", 5: "GND", 11: "GND", 14: "VCC", 7: "GND"},
    "J3": {5: "KCLK", 1: "KDAT", 4: "PS2VCC", 3: "GND", "S": "GND"},
    "J4": {1: "GND", 2: "GND", 4: "FTX", 5: "FRX", 6: "FDTR"},
    "JP1": {2: "EFOC", 4: "EFOC", 6: "EFOC", 8: "EFOC", 1: "-EF1", 3: "-EF2", 5: "-EF3", 7: "-EF"},
    "F1": {1: "VCC", 2: "PS2VCC"},
    "R7": {1: "MRST", 2: "VCC"}, "R8": {1: "KCLK", 2: "VCC"}, "R9": {1: "KDAT", 2: "VCC"},
    "R10": {1: "LDDATA", 2: "VCC"}, "R11": {1: "-EF", 2: "VCC"},
    "C24": {1: "FDTR", 2: "MRST"}, "C25": {1: "XT1", 2: "GND"}, "C26": {1: "XT2", 2: "GND"},
}
for _c in ("C16", "C17", "C18", "C19", "C20", "C21", "C22", "C23", "C27"):
    PINS[_c] = {1: "VCC", 2: "GND"}
PINS = {ref: {str(k): v for k, v in pins.items()} for ref, pins in PINS.items()}

# pins of Rev B-Clean's own parts that join the new nets: (reference, pin) -> net
#   J1's pin 13 is the bus -MRD, which Rev B's sheet leaves unnamed; IC3 is the 6845 (18 DE, 40 VSYNC, 25 -CS);
#   J1's -EF (pin 25, open on Rev B) and the 36-pin connector's positions 31-33
JOIN = {("J1", "13"): "-MRD", ("IC3", "18"): "DE", ("IC3", "40"): "VSYNC", ("IC3", "25"): "-CRTCCS",
        ("J1", "25"): "-EF", ("J1", "31"): "-EF1", ("J1", "32"): "-EF2", ("J1", "33"): "-EF3"}
CUT = ("IC3", "25")                                    # the wire into this pin goes: Rev B's -CS net
CUT_AT, CUT_SEGMENTS = ("IC5", "3"), 2                 # on the board the track is cut at its other end, at IC5 pin 3: the
#                                                        first two pieces go (2.54 mm to the first corner under IC5 and
#                                                        the slant after it) and the rest stays on the 6845's pin
UPPER = ("IC5", "3")                                   # ... which stays on this pin, the NAND that makes it: -UPPER
# pins of Rev B-Clean's own parts that leave their net for another: (reference, pin) -> (the label on the pin's wire, the
# net it joins). The label on the sheet goes (a supply symbol for GND); on the board the last piece of Rev B's track into
# the pin goes, and what then hangs of the old net is cut back (TIDY). The 6845's R/W and E (above)
RELABEL = {("IC3", "22"): ("-MRW", "GND"), ("IC3", "23"): ("TPB", "CRTE")}
# routed before Freerouting, across Rev B's copper alone (gen/route_leftovers.py --first): (reference, pin, a pad of the piece
# of copper it must join, or None for any). The 6845's R/W to ground (walled in afterwards), and the composite video to the
# RCA jack (Freerouting's way round, 2026-11-24, made that net 189 mm long; it was 133 and is about 125 so)
FIRST = (("IC3", "22", ("J1", "30")), ("J2", "C1", ("IC14", "4")))
SOON = ("CRTE", "-MRW", "TPB")                          # of what Freerouting leaves open, these nets are joined first
J1_NEW = {"31": "-EF1", "32": "-EF2", "33": "-EF3", "34": "-DMAIN", "35": "SC0", "36": "-PAUSE"}   # the slot's names

# ---- the board -------------------------------------------------------------------------------------------------------
# Rev B-Clean's board is 141.0 x 96.24 mm, x 10.0-151.0 and y 10.11-106.35 as drawn (bus connector down the left edge).
# This card is 190.5 x 106.565 mm (7.50 in, the IO panel's length; VIDEO-G TEXT's height): 49.5 mm longer at the front
# (right) edge for the keyboard section, and 10.325 mm more at the +5V end of the bus edge (the top, as drawn) for the
# connector's six more positions, which lie beyond +5V. Rev B-Clean's parts and copper stay exactly where they are, but
# the RCA jack. (First drawn 188.0 mm long, VIDEO-G TEXT's length; Ken, 2026-11-20: "ok to grow card if needed": the
# 2.5 mm more are behind the PS/2 jack, where the fuse and the two pull-ups had no room for their labels beside them.)
FRONT = 10.0 + 190.5
EDGE = (10.0, 106.35 - 106.565, FRONT, 106.35)          # left, top, right, bottom

# Rev B-Clean's parts that move: reference -> (x, y, rotation) of the footprint's origin.
#   J2, the RCA jack (Ken, 2026-11-20: "it is messy to have keyboard and video connector on different edges. Need to move
#   together. Less of an issue for FTDI"): from the side edge, where 2005 put it, to the front edge under the PS/2 jack,
#   turned so that its mouth is at that edge (0.38 mm inside it, as it was at the side edge). Its origin is pad S1; at
#   270 the centre pin is 5.07 mm below it and the mouth 11.54 mm to its right. Rev B's video track is kept: the new
#   track joins its end, and what then hangs is taken off (gen/route_leftovers.py, TIDY)
#   LED1, the power LED, and its resistor R1 (Ken, 2026-11-20: "I would prefer for the power LED to be in the corner like
#   most/all other boards"): Rev B has them in its own front corner, which on this longer card is 56 mm from the front
#   edge. They go to this card's front corner, bottom as drawn, where memory Rev E / F and BUSDRV-B have theirs (6.5 mm
#   from the front edge, 7.4 mm from the bottom one), turned as they were. The FTDI header gives up that corner
MOVE = {"J2": (FRONT - 0.38 - 11.54, 31.2, 270),
        "LED1": (FRONT - 6.5, 99.0, 180), "R1": (FRONT - 10.9, 98.6, 270)}
# nets tidied after routing, each named by a pad on it: track ends left touching nothing are cut back. Rev B's select
# track (cut at IC5), its video track and the ground chain that ran through the RCA jack's old pads
TIDY = (("IC3", "25"), ("J2", "C1"), ("J2", "S1"), ("LED1", "A"), ("LED1", "K"), ("J1", "12"), ("J1", "14"))   # (S1: GND; LED1 A: VCC, K: the LED's own net; J1 12, 14: TPB and -MRW,
#  which end at the 6845 no more)

# reference: (x, y, rotation) of the footprint's origin: pin 1 for KiCad's parts, the middle for the Eagle capacitor
PLACE = {
    # IC15, the decoder, lies in the strip along the top edge (the 10 mm this card is taller than Rev B, with only tracks
    # in it), just past the card-guide strip: 20 mm from IC5 pin 3 and the kept -CS track, which it joins. In the front
    # section, 90 mm away across Rev B's copper, no routing order found both of those connections (eight tried)
    "IC15": (88.0, 9.5, 90), "IC16": (156.0, 35.0, 0), "IC17": (156.0, 58.5, 0), "IC18": (156.0, 82.0, 0),
    "IC19": (170.5, 9.0, 0), "IC20": (170.5, 40.5, 0),
    "IC21": (187.5, 51.0, 0),
    "C16": (110.5, 5.7, 90), "C17": (159.8, 30.6, 0), "C18": (159.8, 54.1, 0), "C19": (159.8, 77.6, 0),
    "C20": (174.3, 4.4, 0), "C21": (174.3, 36.1, 0), "C22": (191.3, 46.4, 0), "C23": (182.8, 58.0, 90),   # (C23 in the lane left of the ATmega, by its pins 7 and 8)
    "Y1": (171.9, 69.0, 0), "C25": (171.6, 74.4, 0), "C26": (177.4, 74.4, 0),
    "IC22": (170.5, 85.0, 0), "C27": (174.3, 80.4, 0),  # the second 7416, under the crystal in the latches' column
    "R7": (182.5, 88.6, 0), "C24": (183.8, 95.5, 0),    # the ATmega's reset pull-up and the DTR capacitor, beside the 7416
    "R10": (160.0, 20.0, 0),                            # LDDATA's pull-up: in the free space above IC16 (the front corner
    #                                                     is the LED's and its resistor's)
    "J4": (166.5, 103.8, 90),                           # FTDI header along the bottom edge under the 7416, pin 1 (GND) at
    #                                                     the bus end (Ken: its place matters less; the LED has the corner)
    "J3": (FRONT - 0.3, 20.0, 0),                        # the PS/2 jack at the front edge, its mouth facing off the board
    "R8": (184.9, 13.5, 270), "R9": (184.9, 19.0, 270), "F1": (185.2, 24.5, 270),       # behind the PS/2 jack
    "JP1": (33.0, 5.6, 270),                            # KBD FLAG at the top edge by J1's new pins: four pairs along the edge
    "R11": (39.0, 7.8, 0),
}
