# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-06
"""Hardware-faithful mode: memory cards from their KiCad netlists, the CPU card's -VMA, bus contention."""
import os, sys, unittest
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, ".."))
from s5emu.hw import HWMachine, NetlistMemoryCard, NetlistVideoCard, NetlistIDECard, NetlistIOBoard
from s5emu.machine import Video6845
from s5emu.shell import Shell
ROM108 = os.path.join(HERE, "..", "roms", "hbios-1.0.8.rom")
ROM104 = os.path.join(HERE, "..", "roms", "hbios-1.0.4.rom")


def boot(m, limit=2_000_000):
    """run until the HBIOS prompt is on the screen (or the limit); True if it got there"""
    d = Shell(m).d; n = 0
    while n < limit:
        d.run(max_instructions=50_000); n += 50_000
        if m.cpu.idle and m.cpu.instructions < n: return False
        if m.video.lines()[-1].rstrip().lower() == "test>": return True
    return False


def readers(card, a, vma=0):
    return sorted(n for n, _ in card.bus_read(a, vma)[0])


class Decode(unittest.TestCase):
    def test_rev_b_drawn_enables_the_deselected_bank(self):
        """REVIEW.md finding 1: 74LS151 strobe high forces Y low, so the bank NOT addressed is enabled"""
        c = NetlistMemoryCard("B-drawn", "----------------")
        self.assertEqual(readers(c, 0x1234), ["mem IC11", "mem IC5"])          # upper-bank chips on a lower address
        self.assertEqual(readers(c, 0x9234), ["mem IC1", "mem IC3"])
        self.assertEqual(readers(c, 0x1234, vma=1), ["mem IC1", "mem IC11", "mem IC3", "mem IC5"])   # -VMA high: all four

    def test_rev_c_gates_every_chip_select(self):
        c = NetlistMemoryCard("C", "----------------")
        for a in (0x1234, 0x9234): self.assertEqual(readers(c, a), [])
        self.assertEqual(readers(c, 0x1234, vma=1), [])
        c.set_jumpers("R-------E-------")
        self.assertEqual(readers(c, 0x0123), ["mem IC1"]); self.assertEqual(readers(c, 0x8123), ["mem IC5"])
        self.assertEqual(readers(c, 0x1123), [])

    def test_jumper_map_found_from_the_netlist(self):
        c = NetlistMemoryCard("C")
        sv2_15 = next(h for net, h in c.jumper_map().items() if ("SV2", "15") in c.nl.nets[net])
        self.assertEqual(sv2_15, [("IC1", "RAM", 0)])                          # REVIEW.md: block 0 is the SV2 15/16 column

    def test_rev_b_built_rework(self):
        c = NetlistMemoryCard("B-built")
        self.assertIn("wire IC1.20 to IC14.3 (Net-(IC14A-O))", c.nl.edits)
        self.assertEqual(c.jumpers_fitted, [])                                 # the rework bypasses the muxes
        for a in (0x0000, 0x7000, 0x7FFF): self.assertEqual(readers(c, a), ["mem IC1"])
        for a in (0x8000, 0xFFFF): self.assertEqual(readers(c, a), ["mem IC5"])
        self.assertEqual(readers(c, 0x1234, vma=1), [])

    def test_rev_f_is_rev_d(self):
        """Rev F (2026-11-18) with a 27C256 in each EPROM socket and JP2 / JP1 set for it (shunts 1-3 and 2-4): from its
        own netlist it decodes, writes and reads as Rev D, the card of record, for every 4K block as RAM, EPROM or neither,
        down to the address inside each chip (with no shunt on 2-4, R7 / R6 would hold the EPROM's A14 high)"""
        f, d = NetlistMemoryCard("F"), NetlistMemoryCard("D")
        self.assertIn("jumper JP1.2-JP1.4 (short /Sheet 1/P27_HI to /Sheet 1/BUFFADDR14)", f.nl.edits)
        for jumpers in ("RRRRRRR-EEEEEEE-", "E-R-E-R-E-R-E-R-", "R-E-R-E-R-E-R-E-", "----------------"):
            f.set_jumpers(jumpers); d.set_jumpers(jumpers)
            for a in range(0x0123, 0x10000, 0x1000):                     # A14 low in blocks 0-3 and 8-B, high in the rest
                for vma, mrd, mrw in ((0, 0, 1), (0, 1, 0), (1, 0, 1), (1, 1, 0)):
                    self.assertEqual(f.decode(a, vma, mrd, mrw), d.decode(a, vma, mrd, mrw), "%s %04X" % (jumpers, a))
        self.assertEqual(f.bus_write(0x1234, 0, 0x5A)[0], d.bus_write(0x1234, 0, 0x5A)[0])
        self.assertEqual(f.bus_read(0x1234, 0)[0], d.bus_read(0x1234, 0)[0])

    def test_rev_f_28c256_in_ic5(self):
        """a 28C256 EEPROM in IC5 (EPROM HI), JP1 3-5: A14 on its pin 1. Without 4-6, R6 holds its !WE high: it reads as
        the 27C256 did (same chip address) and takes no write. With 4-6 its !WE is WR: the CPU writes it where it reads"""
        ro, w, d = NetlistMemoryCard("F-28C256"), NetlistMemoryCard("F-28C256-W"), NetlistMemoryCard("D")
        self.assertIn("IC5 fitted as 28C256 (schematic: 27C256/28C256): pin 1 A14, pin 27 ~{WE}", ro.nl.edits)
        for c in (ro, w):
            for a in (0x8123, 0xC123, 0xE456, 0x1234, 0x7FFF):
                self.assertEqual(c.decode(a, 0, 0, 1), d.decode(a, 0, 0, 1), "%04X" % a)
            c.program(0x8123, 0x11); c.program(0xC123, 0x22)
            self.assertEqual(c.bus_read(0x8123, 0)[0], [("mem IC5", 0x11)])
            self.assertEqual(c.bus_read(0xC123, 0)[0], [("mem IC5", 0x22)])
        self.assertEqual(ro.bus_write(0x8123, 0, 0x5A), ([], ()))                     # read-only: R6 holds !WE high
        self.assertEqual(ro.bus_read(0x8123, 0)[0], [("mem IC5", 0x11)])
        self.assertEqual(w.bus_write(0x8123, 0, 0x5A), (["mem IC5"], ()))
        self.assertEqual(w.bus_read(0x8123, 0)[0], [("mem IC5", 0x5A)])
        self.assertEqual(w.bus_read(0xC123, 0)[0], [("mem IC5", 0x22)])                 # A14 reaches it: 4123 untouched
        self.assertEqual(w.bus_write(0x1234, 0, 0xA5)[0], ["mem IC1"])                  # a RAM write reaches the RAM alone
        self.assertEqual(w.bus_write(0x8123, 1, 0x77)[0], [])                           # -VMA high: nothing written
        self.assertEqual(w.bus_read(0x8123, 0)[0], [("mem IC5", 0x5A)])

    def test_write_and_read_back_through_the_netlist(self):
        c = NetlistMemoryCard("D")
        self.assertEqual(c.bus_write(0x1234, 0, 0x5A)[0], ["mem IC1"])
        self.assertEqual(c.bus_read(0x1234, 0)[0], [("mem IC1", 0x5A)])
        self.assertEqual(c.bus_write(0x9234, 0, 0x5A)[0], [])                 # EPROM: no write


class Video(unittest.TestCase):
    """the 6845 Rev B card from its netlist: 74LS85 block compare gated by -VMA, A11 splits RAM / CRTC"""
    def setUp(self):
        self.v = Video6845(); self.c = NetlistVideoCard(self.v, "B")

    def test_decode(self):
        self.assertEqual(readers(self.c, 0x7000), ["6845 IC1"])                 # IDT7134 bus port
        self.assertEqual(readers(self.c, 0x77FF), ["6845 IC1"])
        self.assertEqual(readers(self.c, 0x7801), ["6845 IC3"])                 # the 6845
        self.assertEqual(readers(self.c, 0x7FFF), ["6845 IC3"])                 # RS = A0 only: mirrored to 7FFF
        self.assertEqual(readers(self.c, 0x7000, vma=1), [])                    # the comparator's A=B cascade = not -VMA
        for a in (0x6FFF, 0x8000, 0xF000): self.assertEqual(readers(self.c, a), [])

    def test_registers_and_ram(self):
        self.c.bus_write(0x7000, 0, ord("H")); self.assertEqual(self.v.vram[0], ord("H"))
        self.c.bus_write(0x7800, 0, 14); self.c.bus_write(0x7801, 0, 0x12)        # R14 = cursor high
        self.assertEqual(self.v.reg[14], 0x12); self.assertEqual(self.c.bus_read(0x7801, 0)[0], [("6845 IC3", 0x12)])
        self.c.bus_write(0x7800, 0, 1); self.assertEqual(self.c.bus_read(0x7801, 0)[0], [("6845 IC3", 0)])   # R1 is write-only

    def test_display_parts_proven_off_the_bus(self):
        self.assertEqual(sorted(self.c.c.unmodelled), ["IC10", "IC11", "IC12", "IC13", "IC14", "IC7", "IC8", "IC9", "X1"])


class IDECard(unittest.TestCase):
    """the IDE Rev A card from its netlist: 74LS138 port decode, 74LS75 register latch, NAND-latch INP window"""
    def test_register_select_and_strobes(self):
        c = NetlistIDECard("A")
        self.assertEqual(c.cycle(2, True, 0x07), (None, None))                  # OUT 2 latches the register, no strobe
        self.assertEqual(c.cycle(3, False), ("r", 7))                          # INP 3: DIOR on register 7 (status)
        self.assertEqual(c.cycle(3, True, 0x20), ("w", 7))                     # OUT 3: DIOW on register 7 (command)
        self.assertEqual(c.cycle(2, True, 0x0E), (None, None))
        self.assertEqual(c.cycle(3, True, 0x02), ("w", 0x0E))                  # CS1: control block, device control
        for n in (1, 4, 5, 6, 7): self.assertEqual(c.cycle(n, False), (None, None))
        self.assertEqual(c.cycle(2, False), (None, None))                      # INP from the select port: nothing drives
        self.assertEqual(c.dmap, list(range(8)))                               # DD0-7 are bus D0-7, in order


class IOCard(unittest.TestCase):
    """the IO Rev A card from its netlist: 74LS138 decode, CDP1852 keyboard port, 74LS02 DISPON/DISPOFF for the 1861"""
    def test_1861_has_no_port_as_built(self):
        c = NetlistIOBoard("A")                                                # photo 2026-10-07: SV6 empty
        for n in range(1, 8): self.assertFalse(c.cycle(n, False)[1]); self.assertFalse(c.cycle(n, True, 0)[2])

    def test_ports(self):
        c = NetlistIOBoard("A-1861")
        self.assertEqual(c.cycle(1, False), (True, False, False, ()))            # INP 1: keyboard 1852 onto the bus
        self.assertEqual(c.cycle(4, False), (False, True, False, ()))            # INP 4: 1861 display on
        self.assertEqual(c.cycle(4, True, 0), (False, False, True, ()))          # OUT 4: 1861 display off
        for n in (2, 3, 5, 6, 7): self.assertEqual(c.cycle(n, False), (False, False, False, ()))
        self.assertEqual(c.cycle(1, True, 0), (False, False, False, ()))         # OUT 1: the 1852 is input only
        self.assertEqual(sorted(c.c.unmodelled), ["IC1", "U$5", "U$6", "X1"])   # PIC, PAK-VI, resonator, PS/2 socket

    def test_1861_dma_through_the_netlist_cards(self):
        """machine.py's 1861 test program: INP 4 turns the display on through the IO card's own decode"""
        prog = [0xF8, 0x00, 0xB1, 0xB2, 0xB3, 0xF8, 0x32, 0xA1, 0xF8, 0xFF, 0xA2, 0xF8, 0x10, 0xA3, 0xE2, 0xD3,
                0x6C, 0x30, 0x11]
        isr = [0x72, 0x70, 0x22, 0x78, 0x22, 0x52, 0xF8, 0x02, 0xB0, 0xF8, 0x00, 0xA0, 0x30, 0x30]
        m = HWMachine(io_rev="A-1861"); m.cpurom.remap = False                 # as built SV6 is empty: fit port 4
        for i, b in enumerate(prog): m.write(i, b)
        for i, b in enumerate(isr): m.write(0x30 + i, b)
        pic = bytes((0xAA if (r // 4) % 2 else 0x55) for r in range(128) for _ in range(8))
        for i, b in enumerate(pic): m.write(0x200 + i, b)
        for _ in range(60_000): m.step()
        self.assertTrue(m.pixie.on); self.assertEqual(bytes(m.pixie.frame), pic); self.assertEqual(m.log.events, {})


@unittest.skipUnless(os.path.exists(ROM104), "run tools/mkrom.py first")
class CPUCard(unittest.TestCase):
    """the CPU Rev A card from its netlist: 74LS373 latch, 74LS138 window (F000), 74LS74 boot flip-flop, SV5 -VMA"""
    def test_boot_map_as_built_ends_on_the_first_a15_edge(self):
        """reworked IC8 (photos 2026-10-07): CLK = latched A15, D = PRE = VCC, like YACC1's FORCE-ROM"""
        m = HWMachine(cpu_rom=ROM104); c = m.ccard
        self.assertEqual(c.cycle(0x0000, 0, 1), (1, 0x000, None))              # boot map: the EPROM at 0000, -VMA high
        self.assertEqual(c.cycle(0x7FFF, 0, 1), (1, 0xFFF, None)); self.assertFalse(c.booted())
        self.assertEqual(c.cycle(0x8123, 0, 1), (0, None, None))               # A15 rises: the map ends in this very cycle
        self.assertTrue(c.booted())
        self.assertEqual(c.cycle(0xF123, 0, 1), (1, 0x123, None))              # the EPROM only in its window now
        m.reset(); self.assertFalse(c.booted())
        self.assertEqual(c.cycle(0xF003, 0, 1), (1, 0x003, None)); self.assertTrue(c.booted())   # the boot code's jump

    def test_boot_map_as_drawn_ends_on_the_eprom_window(self):
        m = HWMachine(cpu_rom=ROM104, cpu_rev="A"); c = m.ccard
        self.assertEqual(c.cycle(0x8123, 0, 1), (1, 0x123, None))              # A15 alone does not end it as drawn
        self.assertFalse(c.booted())
        self.assertEqual(c.cycle(0xF001, 0, 1), (1, 0x001, None)); self.assertTrue(c.booted())
        self.assertEqual(c.cycle(0x0000, 0, 1), (0, None, None))

    def test_vma_modes(self):
        for mode, before, after in (("boot", 1, 0), ("norom", 0, 0)):
            c = HWMachine(cpu_rom=ROM104, vma_mode=mode, cpu_rev="A").ccard
            self.assertEqual(c.cycle(0x0000, 0, 1)[0], before); c.cycle(0xF000, 0, 1)
            self.assertEqual(c.cycle(0xF000, 0, 1)[0], after)                  # Boot only: the window is the bus afterwards

    def test_ef_routing_from_the_jumpers(self):
        m = HWMachine(cpu_rom=ROM104)
        self.assertEqual(m.ccard.ef_routes(), {3: "-EF4"})                     # JP1 row 3: the bus -EF line (photo)
        self.assertTrue(m.iocard.sr_on_bus)                                    # IO card SV1 2-3: the 1852 flag on bus -EF
        self.assertFalse(m.ef(3)); m.kbd.press("A"); self.assertTrue(m.ef(3)); self.assertFalse(m.ef(1))


class CPURevD(unittest.TestCase):
    """CPU Rev D (2026-10-30) from its netlist: CLEAR/WAIT straight from -RESET/-PAUSE, the boot flip-flop, LOADED"""
    def test_boot_map_ends_on_the_first_a15_edge(self):
        c = HWMachine(cpu_rom=ROM104, cpu_rev="D").ccard
        self.assertEqual(c.cycle(0x0000, 0, 1), (1, 0x000, None)); self.assertFalse(c.booted()); self.assertFalse(c.loaded())
        self.assertEqual(c.cycle(0x8123, 0, 1), (0, None, None)); self.assertTrue(c.booted())
        self.assertEqual(c.cycle(0xF123, 0, 1), (1, 0x123, None))
        self.assertEqual(c.cycle(0x0000, 0, 1), (0, None, None))

    def test_load_reset_run_runs_ram_and_the_switch_boots_hbios(self):
        m = HWMachine(cpu_rom=ROM104, cpu_rev="D"); c = m.ccard
        c.mode(0, 0); self.assertTrue(c.loaded())                               # LOAD: -RESET and -PAUSE low
        self.assertEqual(c.cycle(0x0000, 1, 0)[0], 0)                           # DMA writes from 0000 reach the RAM
        c.mode(0, 1); self.assertFalse(c.booted()); self.assertTrue(c.loaded())  # RESET (LOAD off): R0 = 0000
        c.mode(1, 1)                                                            # RUN
        self.assertEqual(c.cycle(0x0000, 0, 1), (0, None, None))               # the loaded program, not the boot EPROM
        self.assertEqual(c.cycle(0xF003, 0, 1), (1, 0x003, None))              # HBIOS still answers at F000
        c.mode(0, 1); c.mode(1, 1)                                              # a bus reset (debug board, IO card RUN)
        self.assertEqual(c.cycle(0x0000, 0, 1)[0], 0)                           # keeps LOADED
        m.reset(); self.assertFalse(c.loaded())                                 # the RESET/RUN switch
        self.assertEqual(c.cycle(0x0000, 0, 1), (1, 0x000, None))              # boots HBIOS again

    def test_pause_does_not_touch_the_boot_map(self):
        c = HWMachine(cpu_rom=ROM104, cpu_rev="D").ccard
        c.mode(1, 0); self.assertFalse(c.loaded()); c.mode(1, 1)
        self.assertEqual(c.cycle(0x0000, 0, 1), (1, 0x000, None))

    def test_the_ram_led_shows_loaded(self):
        """LED6 RAM (Ken, 2026-11-21): on U8A's own Q output (pin 5, the net LOADED) through R8, its cathode on GND, so
        it is lit while LOADED is set: LOAD mode lights it, resets from the bus leave it lit, the card's RESET/RUN
        switch (and power-on) puts it out. NOT_LOADED, the output that gates the boot map, carries no LED current"""
        m = HWMachine(cpu_rom=ROM104, cpu_rev="D"); c = m.ccard; nl = c.nl
        net = lambda ref, pin: nl.net(ref, pin).split("/")[-1]
        self.assertEqual((net("U8", 5), net("U8", 6)), ("LOADED", "NOT_LOADED"))
        self.assertEqual({net("R8", 1), net("R8", 2)}, {"LOADED", "LED_RAM"})
        self.assertEqual((net("LED6", 1), net("LED6", 2)), ("GND", "LED_RAM"))          # 1 = cathode, 2 = anode
        self.assertEqual(sorted(r for (r, p), v in nl.pins.items() if v[0].split("/")[-1] == "NOT_LOADED"), ["U5", "U8"])
        loaded = next(n for n in nl.nets if n.split("/")[-1] == "LOADED")
        lit = lambda: c.c.val.get(loaded) == 1
        self.assertFalse(lit()); self.assertEqual(c.cycle(0x0000, 0, 1, commit=False)[0], 1)     # power-on: dark, HBIOS
        c.mode(1, 0); self.assertFalse(lit()); c.mode(1, 1)                              # PAUSE alone: still dark
        c.mode(0, 1); c.mode(0, 0); self.assertTrue(lit())                               # LOAD mode: lit
        c.mode(0, 1); c.mode(1, 1); self.assertTrue(lit())                               # RESET, then RUN: lit, and RAM runs
        self.assertEqual(c.cycle(0x0000, 0, 1, commit=False)[0], 0)
        c.mode(0, 1); c.mode(1, 1); self.assertTrue(lit())                               # a reset from the bus: still lit
        m.reset(); self.assertFalse(lit())                                               # the card's own switch: dark, HBIOS
        self.assertEqual(c.cycle(0x0000, 0, 1, commit=False)[0], 1)

    def test_ef_routing_for_the_2005_io_card(self):
        m = HWMachine(cpu_rom=ROM104, cpu_rev="D")
        self.assertEqual(m.ccard.ef_routes(), {1: "-EF1", 2: "-EF2", 3: "-EF4"})   # JP3: the bus -EF line on EF3
        self.assertFalse(m.ef(3)); m.kbd.press("A"); self.assertTrue(m.ef(3))


class IOPanel(unittest.TestCase):
    """the IO panel card (2026-10-30) from its netlist: port 4, -EF1, one DMA IN per INPUT press in LOAD mode"""
    def test_port_4(self):
        from s5emu.hw import NetlistIOPanel
        p = NetlistIOPanel()
        self.assertEqual(p.out(4, 0xA5), (False, 0xA5)); self.assertEqual(p.out(3, 0xFF)[1], 0xA5)   # only OUT 4 latches
        p.set(switches=0x3C); self.assertEqual(p.inp(4), 0x3C); self.assertIsNone(p.inp(1))
        self.assertFalse(p.ef1()); p.set(pressed=True); self.assertTrue(p.ef1()); self.assertFalse(p.dmain())  # not LOAD

    def test_one_dma_in_per_press(self):
        from s5emu.hw import NetlistIOPanel
        p = NetlistIOPanel(); p.set(run=False, load=True); self.assertTrue(p.load_mode())
        p.set(switches=0x7B, pressed=True); self.assertTrue(p.dmain())
        self.assertEqual(p.dma_in(), 0x7B); self.assertFalse(p.dmain())
        self.assertIsNone(p.dma_in())                                          # held: no second byte
        p.set(pressed=False); p.set(switches=0x30, pressed=True); self.assertEqual(p.dma_in(), 0x30)

    @unittest.skipUnless(os.path.exists(ROM104), "run tools/mkrom.py first")
    def test_toggle_in_and_run_a_program_with_cpu_rev_d(self):
        m = HWMachine(cpu_rom=ROM104, cpu_rev="D", panel_rev="A"); d = Shell(m).d
        prog = [0xE1, 0xF8, 0x20, 0xA1, 0x6C, 0x64, 0x21, 0x30, 0x04]       # SEX 1; LDI 20; PLO 1; INP 4; OUT 4; DEC 1; BR 04
        m.panel_set(run=False); m.panel_set(load=True)                         # LOAD mode
        for b in prog: m.panel_set(switches=b); m.panel_set(input=True); m.panel_set(input=False)
        self.assertEqual([m.read(a) for a in range(9)], prog); self.assertTrue(m.ccard.loaded())
        m.panel_set(load=False); self.assertEqual(m.cpu.R[0], 0)              # RESET
        m.panel_set(switches=0x5A, run=True); d.run(max_instructions=2000)     # RUN: the toggles appear on the LEDs
        self.assertEqual(m.panel.latch, 0x5A)
        m.panel_set(switches=0xC3); d.run(max_instructions=2000); self.assertEqual(m.panel.latch, 0xC3)
        self.assertEqual(m.log.events, {})
        m.reset(); self.assertFalse(m.ccard.loaded()); self.assertTrue(boot(m))   # the CPU card's RESET/RUN: HBIOS

    def test_input_button_on_ef1(self):
        m = HWMachine(cpu_rom=ROM104, cpu_rev="D", panel_rev="A")
        self.assertFalse(m.ef(1)); m.panel_set(input=True); self.assertTrue(m.ef(1)); m.panel_set(input=False)

    def test_jumpers_pick_the_ports_and_the_ef_line(self):
        """JP1 / JP2 / JP3 (Ken, 2026-11-17): the IN port, the OUT port and INPUT's bus EF line, each on its own jumper"""
        from s5emu.hw import NetlistIOPanel
        p = NetlistIOPanel(in_port=1, out_port=5, ef="-EF3", rtc_ports=None)
        self.assertEqual(p.out(5, 0x5A)[1], 0x5A); self.assertEqual(p.out(4, 0x11)[1], 0x5A)    # OUT 5 only
        p.set(switches=0xC3); self.assertEqual(p.inp(1), 0xC3); self.assertIsNone(p.inp(5)); self.assertIsNone(p.inp(4))
        p.set(pressed=True); self.assertTrue(p.ef("-EF3")); self.assertFalse(p.ef("-EF1")); self.assertFalse(p.ef("-EF"))
        p = NetlistIOPanel(in_port=None, out_port=None, ef=None, rtc_ports=None)                # no jumpers: no port at all
        for n in range(1, 8): self.assertIsNone(p.inp(n)); self.assertNotEqual(p.out(n, 0x77)[1], 0x77)
        p.set(pressed=True); self.assertFalse(any(p.ef(e) for e in ("-EF1", "-EF2", "-EF3", "-EF")))

    def test_address_display(self):
        """the bus address on four TIL311s (Ken, 2026-11-18): U18 holds the high byte as TPA falls, U19 the low byte as
        TPB falls (74HCT573s, so the bus sees HCT inputs); the displays keep the last cycle's address while A0-A7 change
        between cycles, and each TIL311's data pins (3, 2, 13, 12 = A-D) take four of the latches' outputs in order"""
        from s5emu.hw import NetlistIOPanel
        p = NetlistIOPanel()
        for a in (0x0000, 0x1234, 0xF00F, 0xA55A, 0xFFFF, 0x8001):
            self.assertEqual(p.cycle(a), a, "%04X" % a)
        p.c.drive(A=0x3C); p.c.settle(); self.assertEqual(p.address(), 0x8001)       # no TPA / TPB: held
        p.cycle(0x7000, n=4, read=False); self.assertEqual(p.address(), 0x7000)     # an OUT's cycle too: any cycle
        self.assertTrue(p.leds().startswith("ADDR 7000"))
        net = lambda ref, pin: p.nl.net(ref, pin).split("/")[-1]
        for ref, first in (("U14", 12), ("U15", 8), ("U16", 4), ("U17", 0)):
            self.assertEqual([net(ref, pin) for pin in (3, 2, 13, 12)], ["ADR%d" % (first + i) for i in range(4)], ref)
            self.assertEqual((net(ref, 5), net(ref, 8)), ("GND", "GND"), ref)        # strobe and blanking low
        self.assertEqual((net("U18", 11), net("U19", 11)), ("TPA", "TPB"))

    def test_rtc_strobes_through_the_gates(self):
        """the DS12885 (2026-11-18) on JP4's pair: OUT to the address port pulses AS, OUT to the data port R/W, INP of it
        holds DS low, through U6D, U12 and U5C; nothing on any other port or direction. Then a byte of its RAM and the
        time, written and read back through the gates"""
        import datetime
        from s5emu.hw import NetlistIOPanel
        from s5emu.rtc import DS12885
        for pair in (6, 4, 2):
            p = NetlistIOPanel(rtc_ports=pair, in_port=1 if pair != 2 else 4, out_port=1 if pair != 2 else 4)
            for n in range(1, 8):
                for out in (True, False):
                    self.assertEqual(p.strobes(n, out), (n == pair and out, n == pair + 1 and out, n == pair + 1 and not out),
                                     (pair, n, out))
        clock = [datetime.datetime(2026, 11, 18, 2, 0, 0)]
        p = NetlistIOPanel(rtc=DS12885(now=lambda: clock[0]))
        p.out(6, 0x40); p.out(7, 0xA5); p.out(6, 0x41); p.out(7, 0x5A)
        p.out(6, 0x40); self.assertEqual(p.inp(7), 0xA5); p.out(6, 0x41); self.assertEqual(p.inp(7), 0x5A)
        self.assertIsNone(p.inp(6))                                            # the address port reads nothing
        for reg, v in ((0x0A, 0x20), (0x0B, 0x86), (0x04, 13), (0x02, 7), (0x00, 30), (0x0B, 0x06)): p.out(6, reg); p.out(7, v)
        clock[0] += datetime.timedelta(seconds=10)
        got = []
        for reg in (0x04, 0x02, 0x00): p.out(6, reg); got.append(p.inp(7))
        self.assertEqual(got, [13, 7, 40])
        p.set(switches=0xFF); p.out(6, 0x40); self.assertEqual(p.inp(7), 0xA5)    # the toggles stay off the bus (IN port 4)

    @unittest.skipUnless(os.path.exists(ROM108), "build firmware/hbios/v1.0.8 first")
    def test_hbios_108_sets_and_reads_the_clock_on_the_netlist_cards(self):
        """the whole path from the netlists: CPU Rev D runs HBIOS v1.0.8, whose f_settod / f_gettod reach the IO panel's
        DS12885 through the card's decoder, jumpers and gates (ports 6 and 7)"""
        import datetime
        from s5emu.rtc import DS12885
        clock = [datetime.datetime(2026, 11, 18, 2, 0, 0)]
        m = HWMachine(cpu_rom=ROM108, cpu_rev="D", panel_rev="A"); m.panel.rtc = DS12885(now=lambda: clock[0])
        self.assertTrue(boot(m))
        prog = bytes([0x90, 0xB3, 0xF8, 0x06, 0xA3, 0xD3, 0xE2,                # 0100 R3 = 0106, SEP R3; SEX R2
                      0xF8, 0x03, 0xBF, 0xF8, 0x00, 0xAF, 0xD4, 0xF8, 0x18,    # 0107 RF = 0300; CALL f_settod
                      0xF8, 0x03, 0xBF, 0xF8, 0x10, 0xAF, 0xD4, 0xF8, 0x15,    # 0110 RF = 0310; CALL f_gettod
                      0xF8, 0x02, 0xBF, 0xF8, 0x00, 0xAF,                      # 0119 RF = 0200
                      0x3B, 0x25, 0xF8, 0x45, 0x30, 0x27, 0xF8, 0x4F,          # 011F BNF 0125; 'E'; BR 0127; 0125 'O'
                      0x5F, 0x30, 0x28])                                       # 0127 STR RF; 0128 BR 0128
        for i, b in enumerate(prog): m.write(0x0100 + i, b)
        for i, b in enumerate([12, 31, 54, 23, 59, 58]): m.write(0x0300 + i, b)   # 2026-12-31 23:59:58 (54 = 2026 - 1972)
        m.kbd.press("@0100\n"); Shell(m).d.run(max_instructions=400_000)
        self.assertEqual(chr(m.read(0x0200)), "O")
        self.assertEqual([m.read(0x0310 + i) for i in range(6)], [12, 31, 54, 23, 59, 58])
        self.assertEqual(m.panel.rtc.time(), datetime.datetime(2054, 12, 31, 23, 59, 58))
        self.assertEqual(m.log.events, {})

    # ---- the serial port (2026-11-20): a 16C550 on the RTC's port pair
    @staticmethod
    def _uart(p):
        def wr(reg, v): p.out(6, 0x80 | reg); p.out(7, v)
        def rd(reg): p.out(6, 0x80 | reg); return p.inp(7)
        return wr, rd

    def test_serial_port_shares_the_rtcs_ports(self):
        """the byte written to the address port picks the chip: bit 7 set = the UART's register (U22 holds bits 7 and
        2-0), clear = the DS12885's, whose CS is that bit. Characters go out and come in; the clock still answers"""
        import datetime
        from s5emu.hw import NetlistIOPanel
        from s5emu.rtc import DS12885
        clock = [datetime.datetime(2026, 11, 20, 5, 0, 0)]
        p = NetlistIOPanel(rtc=DS12885(now=lambda: clock[0])); wr, rd = self._uart(p)
        net = lambda ref, pin: p.nl.net(ref, pin).split("/")[-1]
        self.assertEqual([net("U20", n) for n in ("12", "13", "14", "25")], ["SEL_UART", "+5V", "GND", "GND"])   # CS0, CS1, -CS2, -ADS
        self.assertEqual([net("U20", n) for n in ("18", "19", "21", "22")], ["+5V", "RTC_WR", "UART_RD_L", "GND"])  # -WR, WR, -RD, RD
        self.assertEqual([net("U20", n) for n in ("36", "37", "38", "39")], ["+5V"] * 4)                       # modem inputs off
        self.assertEqual((net("U13", "13"), net("U22", "11"), net("U20", "35")), ("SEL_UART", "RTC_AS", "RESET_H"))
        self.assertEqual((net("U20", "16"), net("X1", "5"), net("U20", "9"), net("U20", "15")), ("UCLK", "UCLK", "UBAUD", "UBAUD"))
        wr(3, 0x80); wr(0, 12); wr(1, 0); wr(3, 0x03)                          # DLAB; divisor 12; 8 bits, no parity, 1 stop
        self.assertEqual(p.uart.baud(), 9600); self.assertEqual((rd(3), rd(1)), (0x03, 0x00))
        self.assertEqual(rd(5), 0x60)                                          # THR empty, nothing received
        for c in b"Hi": wr(0, c)
        self.assertEqual(p.serial_out(), b"Hi")
        p.serial_in("ok"); self.assertEqual(rd(5), 0x61)
        self.assertEqual((rd(0), rd(0), rd(5)), (ord("o"), ord("k"), 0x60))
        wr(7, 0x5A); p.out(6, 0x40); p.out(7, 0xA5)                            # the UART's scratch byte; a byte of the RTC's RAM
        self.assertEqual(p.inp(7), 0xA5); self.assertEqual(rd(7), 0x5A)        # each chip kept its own
        p.out(6, 0x40); self.assertEqual(p.inp(7), 0xA5)
        for reg, v in ((0x0A, 0x20), (0x0B, 0x06), (0x04, 13), (0x02, 7), (0x00, 30)): p.out(6, reg); p.out(7, v)
        clock[0] += datetime.timedelta(seconds=10); p.out(6, 0x00); self.assertEqual(p.inp(7), 40)   # the clock counts
        self.assertEqual(rd(5), 0x60); self.assertEqual(p.serial_out(), b"")   # and none of that reached the UART

    def test_serial_port_read_strobe(self):
        """the UART's -RD comes from U11B, not from the RTC's DS. The 1802 puts N out from the start of an OUT's cycle and
        takes -MRD low 1.5 clocks later (data sheet, figure 11), so 'this port and -MRD high' is true for a moment in
        every OUT to the data port: the DS12885's DS pulses there (it does not mind), the 16C550's -RD must not, or a
        character written to THR would first read RBR and lose a received one. -RD is low only in an INP of the data
        port, from -MWR's fall to the end of the cycle; WR only in TPB of an OUT to it"""
        from s5emu.hw import NetlistIOPanel
        p = NetlistIOPanel(); wr, rd = self._uart(p)
        net = lambda ref, pin: p.nl.net(ref, pin).split("/")[-1]
        self.assertEqual([net("U11", n) for n in ("13", "12", "11", "10", "8")], ["RTC_RD", "GND", "GND", "-MRW", "UART_RD_L"])
        p.out(6, 0x80)                                                         # the UART, register 0
        for n in range(1, 8):
            for out in (True, False):
                s = p._io(n, out, 0x80 if out else None)                       # (an OUT 6 of 80h keeps the UART picked)
                self.assertEqual(s["urd_low"], [] if out or n != 7 else ["mwr", "tpb", "after"], (n, out))
                self.assertEqual(s["uwr"] == (1, 0), out and n == 7, (n, out))
                self.assertEqual((s["usel"], s["ureg"], s["rtc_sel"]), (True, 0, False), (n, out))
        s = p._io(7, True, 0x00); self.assertEqual((s["rd_early"], s["rd"]), (0, 1))    # the RTC's DS: low early in the OUT
        s = p._io(7, False); self.assertEqual((s["rd_early"], s["rd"]), (0, 0))         # and through the INP
        wr(1, 0x00); p.serial_in("AB")
        wr(0, ord("x")); wr(0, ord("y"))                                       # two characters sent with two waiting:
        self.assertEqual((rd(0), rd(0), rd(5)), (ord("A"), ord("B"), 0x60))    # both still there, in order
        self.assertEqual(p.serial_out(), b"xy")
        # a memory write elsewhere (-MWR low, no port): U11B's preset and clear both low, !Q high: no read
        c = p.c; c.drive(N=0, MRD=1, MRW=0); low = c.settle().get(p.u_rd); c.drive(MRW=1); c.settle()
        self.assertEqual(low, 1)

    def test_serial_port_interrupt_and_reset(self):
        """INTR through a gate of U9 (open collector) to JP7: fitted, a received character pulls the bus -INT low while
        the UART's receive interrupt is on; open, it does not. -RESET low is the UART's MR: the interrupt enables clear"""
        from s5emu.hw import NetlistIOPanel
        for fitted in (True, False):
            p = NetlistIOPanel(uart_int=fitted); wr, rd = self._uart(p)
            self.assertFalse(p.int_low())                                      # nothing asked for yet
            wr(1, 0x01); self.assertFalse(p.int_low())
            p.serial_in("x"); self.assertEqual(p.int_low(), fitted); self.assertEqual(rd(2) & 0x0F, 0x04)   # IIR: received data
            self.assertEqual(rd(0), ord("x")); self.assertFalse(p.int_low()); self.assertEqual(rd(2) & 0x0F, 0x01)
            wr(1, 0x03); self.assertEqual(p.int_low(), fitted); self.assertEqual(rd(2) & 0x0F, 0x02)        # THR empty, once
            self.assertFalse(p.int_low())
            wr(1, 0x01); p.serial_in("y"); p.set(run=False); p.set(run=True)   # RUN/RESET off and on: MR
            self.assertFalse(p.int_low()); self.assertEqual(rd(1), 0x00); self.assertEqual(rd(0), ord("y"))  # RBR is kept

    @unittest.skipUnless(os.path.exists(ROM108), "build firmware/hbios/v1.0.8 first")
    def test_a_program_echoes_the_serial_line_on_the_netlist_cards(self):
        """the whole path: CPU Rev D runs a program that sets the UART to 9600 baud and sends back each character it
        receives, through the IO panel's decoder, jumpers, select latch and gates; the clock is read in between"""
        m = HWMachine(cpu_rom=ROM108, cpu_rev="D", panel_rev="A"); self.assertTrue(boot(m))
        prog = bytes([0x90, 0xB3, 0xF8, 0x06, 0xA3, 0xD3,                      # 0100 R3 = 0106, SEP R3
                      0xE3, 0x66, 0x83, 0x67, 0x80,                            # 0106 SEX R3; OUT 6,83; OUT 7,80: LCR = DLAB
                      0x66, 0x80, 0x67, 0x0C, 0x66, 0x81, 0x67, 0x00,          # 010B DLL = 12, DLM = 0
                      0x66, 0x83, 0x67, 0x03,                                  # 0113 LCR = 03
                      0xE3, 0x66, 0x85, 0xE2, 0x6F, 0xFA, 0x01, 0x32, 0x17,    # 0117 LSR: a character? no: again
                      0xE3, 0x66, 0x80, 0xE2, 0x6F,                            # 0120 RBR -> D and M(R2)
                      0x67, 0x22, 0x30, 0x17])                                 # 0125 OUT 7 (THR), DEC R2; BR 0117
        for i, b in enumerate(prog): m.write(0x0100 + i, b)
        m.kbd.press("@0100\n"); d = Shell(m).d; d.run(max_instructions=200_000)
        self.assertEqual(m.panel.uart.baud(), 9600)
        m.panel.serial_in("System-5"); d.run(max_instructions=20_000)
        self.assertEqual(m.panel.serial_out(), b"System-5")
        m.panel.out(6, 0x0D); self.assertEqual(m.panel.inp(7), 0x80)           # the DS12885's register D: its battery is good
        m.panel.serial_in("!"); d.run(max_instructions=5_000); self.assertEqual(m.panel.serial_out(), b"!")
        self.assertEqual(m.log.events, {})


V5_GZ = os.path.join(HERE, "..", "..", "..", "..", "private-resources", "elf", "reference", "mike-riley", "elfos-v5", "system5",
                     "elfos-5.1.1-system5-16mb.img.gz")


@unittest.skipUnless(os.path.exists(V5_GZ) and os.path.exists(ROM108), "needs the Elf/OS v5 image (private-resources) and HBIOS v1.0.8")
class SystemV5(unittest.TestCase):
    """the whole machine from its netlists with the new cards: CPU Rev D, the IO panel (its clock through its own
    decoder, jumpers and gates) and memory Rev F with a 28C256 in IC5 that the CPU can write (JP1 3-5 and 4-6), with the
    6845, IDE and IO cards; HBIOS v1.0.8 boots Elf/OS v5 (about 80 s), and neither touches the EEPROM (8000-EFFF):
    Elf/OS's memory probe (f_freemem) stops below it"""
    def test_elfos_v5_on_cpu_rev_d_with_the_io_panels_clock(self):
        import datetime, gzip, tempfile
        from s5emu.rtc import DS12885
        img = tempfile.mktemp(suffix=".img")
        with gzip.open(V5_GZ) as f, open(img, "wb") as g: g.write(f.read())
        try:
            m = HWMachine(cpu_rom=ROM108, cpu_rev="D", panel_rev="A", mem_rev="F-28C256-W", disk=img); sh = Shell(m)
            eeprom = bytes(m.memory.contents["IC5"])
            clock = [datetime.datetime(2054, 11, 18, 3, 0, 0)]                    # 2026 in ELF/OS's years
            m.panel.rtc = DS12885(now=lambda: clock[0], start=clock[0])
            def until(prompt, cap=40_000_000):
                for _ in range(0, cap, 250_000):
                    sh.d.run(max_instructions=250_000)
                    if not m.kbd.queue and m.video.lines()[-1].rstrip() == prompt: return
                self.fail("no %r prompt; the screen:\n%s" % (prompt, "\n".join(m.video.lines())))
            until("test>"); m.kbd.press("B\n"); until(":")
            m.kbd.press("sysinfo\n"); until(":")
            self.assertIn("  RTC       : Yes (11/18/2026 03:00:00)", [l.rstrip() for l in m.video.lines()])
            m.kbd.press("date 1/2/2027 3:4:5\n"); until(":")
            self.assertEqual(m.panel.rtc.time(), datetime.datetime(2055, 1, 2, 3, 4, 5))
            self.assertEqual(m.log.events, {})                                      # no fights, nothing undefined
            self.assertEqual(bytes(m.memory.contents["IC5"]), eeprom)              # the EEPROM untouched
        finally:
            os.remove(img)


@unittest.skipUnless(os.path.exists(ROM104), "run tools/mkrom.py first")
class Boot(unittest.TestCase):
    def test_cpu_rev_d_boots_hbios_and_echoes_a_key(self):
        m = HWMachine(cpu_rom=ROM104, cpu_rev="D"); self.assertTrue(boot(m)); self.assertEqual(m.log.events, {})
        m.kbd.press("X"); Shell(m).d.run(max_instructions=200_000)
        self.assertTrue(m.video.lines()[-1].lower().startswith("test>x"))

    def test_rev_b_drawn_cannot_boot(self):
        m = HWMachine(mem_rev="B-drawn", cpu_rom=ROM104)
        self.assertFalse(boot(m, 100_000))
        (kind, names, blk), = [k for k in m.log.events if k[0] == "fight"]
        self.assertIn("CPU EPROM", names); self.assertIn("mem IC1", names)

    def test_rev_b_built_boots_and_shares_7000_with_the_6845(self):
        m = HWMachine(mem_rev="B-built", cpu_rom=ROM104)
        self.assertTrue(boot(m))
        kinds = set(m.log.events)
        self.assertEqual({b for _, _, b in kinds}, {7})                       # every event is in 7000-7FFF
        self.assertIn(("multi-write", ("mem IC1", "6845 IC1"), 7), kinds)               # RAM and the 6845 card's video RAM
        self.assertFalse(any(k == "fight" for k, _, _ in kinds))

    def test_rev_f_boots_clean(self):
        m = HWMachine(mem_rev="F", cpu_rom=ROM104)
        self.assertTrue(boot(m)); self.assertEqual(m.log.events, {})

    def test_rev_c_boots_clean(self):
        m = HWMachine(mem_rev="C", cpu_rom=ROM104)
        self.assertTrue(boot(m)); self.assertEqual(m.log.events, {})

    def test_keyboard_echo_through_the_netlist_cards(self):
        m = HWMachine(cpu_rom=ROM104); self.assertTrue(boot(m))
        m.kbd.press("X"); Shell(m).d.run(max_instructions=200_000)
        self.assertTrue(m.video.lines()[-1].lower().startswith("test>x")); self.assertEqual(m.log.events, {})

    def test_stop_on_fight(self):
        m = HWMachine(mem_rev="B-drawn", cpu_rom=ROM104); m.stop_on = {"fight"}
        r = Shell(m).d.run(max_instructions=1000)
        self.assertTrue(r.startswith("bus: fight"), r)


if __name__ == "__main__":
    unittest.main(verbosity=1)
