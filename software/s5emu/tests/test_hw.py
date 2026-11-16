# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-06
"""Hardware-faithful mode: memory cards from their KiCad netlists, the CPU card's -VMA, bus contention."""
import os, sys, unittest
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, ".."))
from s5emu.hw import HWMachine, NetlistMemoryCard, NetlistVideoCard, NetlistIDECard, NetlistIOBoard
from s5emu.machine import Video6845
from s5emu.shell import Shell
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
