# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-22
"""The front panel (hardware/front-panel/kicad/rev-a) from its netlist, alone and on the machine: CPU Rev D, the IO
panel card and the front panel on that card's ribbon, each from its own netlist (hw.py).

Ken, 2026-11-22: "I want to add ability to have a front panel if system is ever put in a case. This will mean bringing
all IO switches, LEDs, and TIL311 signals out to a ribbon cable connector. It will also mean bring the CPU reset out
to a connector"; "dont forget q line"; "and cpu status leds for mode"; "unless the IO panel via the bus can do what
the cpu card reset can do then we dont need line from cpu card all can come from io".

    cd software/s5emu && python3 -m unittest tests.test_front_panel
"""
import os, sys, unittest
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "tools"))
import s5panel
from s5emu.hw import HWMachine, NetlistFrontPanel, NetlistIOPanel
from s5emu.shell import Shell
ROM108 = os.path.join(HERE, "..", "roms", "hbios-1.0.8.rom")
PROG = [0xE1, 0xF8, 0x20, 0xA1, 0x6C, 0x64, 0x21, 0x7B, 0x30, 0x04]   # SEX 1; LDI 20; PLO 1; INP 4; OUT 4; DEC 1; SEQ; BR 04


def machine():
    return HWMachine(cpu_rom=ROM108, cpu_rev="D", video_rev=None, io_rev=None, panel_rev="A", front_rev="A", pixie_port=0)


def prompt(m, limit=3_000_000):
    """run until HBIOS's prompt is on the screen; True if it got there"""
    d = Shell(m).d; n = 0
    while n < limit:
        d.run(max_instructions=50_000); n += 50_000
        if m.video.lines()[-1].rstrip().lower() == "test>": return True
    return False


class Ribbon(unittest.TestCase):
    def test_pin_for_pin(self):
        """tools/s5panel.py is the one pin map: the IO panel card's J3 and the front panel's J1 both follow it, so a
        straight 50-way ribbon joins each line to itself"""
        io, fp = NetlistIOPanel().nl, NetlistFrontPanel().nl
        self.assertEqual(len(s5panel.RIBBON), 50)
        for pin, io_net, fp_net, what in s5panel.RIBBON:
            self.assertEqual(io.net("J3", str(pin)).split("/")[-1], io_net, "IO panel J3 pin %d (%s)" % (pin, what))
            self.assertEqual(fp.net("J1", str(pin)).split("/")[-1], fp_net, "front panel J1 pin %d (%s)" % (pin, what))
        power = [io for _, io, _, _ in s5panel.RIBBON]
        self.assertEqual((power.count("+5V"), power.count("GND")), (4, 8))

    def test_the_io_card_pulls_the_data_lines_down(self):
        """the front panel's toggles switch a data line to +5V through 1k or leave it open: the IO card's RN3 (10k to
        ground) makes an open line a 0, and the '244's inputs do not float with nothing plugged in"""
        p = NetlistIOPanel(toggles=False)
        self.assertEqual(p.sw_byte(), 0x00); p.remote(0xA5, False); self.assertEqual(p.sw_byte(), 0xA5)
        self.assertEqual(p.inp(4), 0xA5)
        q = NetlistIOPanel(); q.set(switches=0x0F); q.remote(0xF0, False)   # the card's own toggles fitted: they win
        self.assertEqual(q.inp(4), 0x0F)


class Card(unittest.TestCase):
    """the front panel by itself, the ribbon's lines set by hand"""
    def test_mode_leds_and_the_copy_of_loaded(self):
        f = NetlistFrontPanel(); lit = lambda: {k for k, v in f.leds().items() if v}
        f.lines(0, 1, 0); self.assertEqual(lit(), {"PWR", "RESET"})              # a boot reset (as at power-on)
        f.lines(1, 1, 1); self.assertEqual(lit(), {"PWR"})
        f.lines(1, 0, 1); self.assertEqual(lit(), {"PWR", "PAUSE"})              # PAUSE alone: no flag
        f.lines(0, 1, 1); f.lines(0, 0, 1); self.assertEqual(lit(), {"PWR", "PAUSE", "RESET", "RAM"})   # LOAD mode sets it
        f.lines(0, 0, 0); self.assertIn("RAM", lit())                            # a DMA request in LOAD mode: not a boot reset
        f.lines(0, 1, 1); f.lines(1, 1, 1); self.assertEqual(lit(), {"PWR", "RAM"})   # RESET, RUN: START FROM RAM stays
        f.lines(0, 1, 1); f.lines(1, 1, 1); self.assertIn("RAM", lit())          # a plain reset from the bus keeps it
        f.lines(1, 1, 0); self.assertIn("RAM", lit())                            # -DMAIN alone: nothing
        f.lines(0, 1, 0); self.assertNotIn("RAM", lit())                         # a boot reset clears it
        f.show({"LED_Q_K": 0, "ROM_LED_L": 0}); self.assertEqual(lit() & {"Q", "ROM"}, {"Q", "ROM"})
        f.show({"LED_Q_K": 1, "ROM_LED_L": None}); self.assertEqual(lit() & {"Q", "ROM"}, set())

    def test_reset_button_is_a_boot_reset_unless_load_is_on(self):
        f = NetlistFrontPanel(); self.assertEqual(f.pulls(), set())
        f.set(reset=True); self.assertEqual(f.pulls(), {"-RESET", "-DMAIN"})     # both lines, together
        self.assertTrue(f.leds()["RESET"])
        f.set(reset=False); self.assertEqual(f.pulls(), set())
        f.set(load=True); f.set(reset=True); self.assertEqual(f.pulls(), {"-PAUSE"})   # LOAD on: the button does nothing
        f.set(reset=False, load=False)
        f.lines(1, 0, 1); f.set(reset=True); self.assertEqual(f.pulls(), set())  # nor while another card holds -PAUSE
        f.set(reset=False); f.lines(1, 1, 1)

    def test_run_load_input_and_the_toggles(self):
        f = NetlistFrontPanel()
        f.set(run=False); self.assertEqual(f.pulls(), {"-RESET"}); f.set(load=True); self.assertEqual(f.pulls(), {"-RESET", "-PAUSE"})
        f.set(run=True, load=False); self.assertEqual(f.pulls(), set())
        val = lambda net: f.c.val.get(net)
        f.set(switches=0x81); self.assertEqual([val(n) for n in f.sw_nets], [1, None, None, None, None, None, None, 1])
        self.assertIsNone(val(f.input_net)); f.set(pressed=True); self.assertEqual(val(f.input_net), 0)

    def test_the_switches_are_played_as_the_netlist_wires_them(self):
        """each control's contact is read from the netlist (hw.switch_contact), and the IO panel card is given what the
        panel's own nets put on the ribbon (ribbon_in), not the positions of the controls: a switch wired to the wrong
        place fails here as it would on the bench (2026-11-23, after the pcb-check session's damaged-netlist runs)"""
        from s5emu import hw
        name = lambda k: (k[0].split("/")[-1], k[1])
        f = NetlistFrontPanel()
        self.assertEqual([name(k) for k in f.k_bits], [("SW%d" % k, 1) for k in range(8)])        # +5V, through RN2
        self.assertEqual([name(k) for k in (f.k_reset_sw, f.k_load, f.k_input, f.k_boot)],
                         [("-RESET", 0), ("-PAUSE", 0), ("INPUT_L", 0), ("BTN_RC", 0)])
        self.assertEqual(f.ribbon_in(), (0x00, False))
        f.set(switches=0xA5, pressed=True); self.assertEqual(f.ribbon_in(), (0xA5, True))

        def damaged(*rework):
            hw.FRONTPANEL_REVS["damaged"] = dict(hw.FRONTPANEL_REVS["A"], rework=list(rework))
            try: return NetlistFrontPanel(rev="damaged")
            finally: del hw.FRONTPANEL_REVS["damaged"]
        q = damaged(("wire", "RN2", "1", "SW9", "2"))                # the toggles' resistors to ground, not +5V
        q.set(switches=0xFF); self.assertEqual(q.ribbon_in()[0], 0x00)
        q = damaged(("wire", "SW3", "1", "SW9", "2"))                # one toggle to ground, not to its resistor
        q.set(switches=0xFF); self.assertEqual(q.ribbon_in()[0], 0xFB)
        q = damaged(("lift", "SW11", "1"))                           # INPUT's button off its line
        q.set(pressed=True); self.assertEqual(q.ribbon_in()[1], False)
        q = damaged(("wire", "SW12", "2", "RN2", "1"))               # RESET's button to +5V: BTN_RC is never pulled low
        q.lines(1, 1, 1); q.set(reset=True); self.assertEqual(q.pulls(), set())
        q = damaged(("lift", "SW9", "1"))                            # RUN/RESET's toggle off -RESET
        q.set(run=False); self.assertEqual(q.pulls(), set())
        with self.assertRaises(ValueError): damaged(("lift", "SW3", "1"))     # a toggle to nothing: no supply either side

    def test_displays(self):
        f = NetlistFrontPanel(); self.assertIsNone(f.address()); self.assertIsNone(f.data())
        f.show({**{"ADR%d" % k: (0xC0DE >> k) & 1 for k in range(16)}, **{"OUT%d" % k: (0x5A >> k) & 1 for k in range(8)}})
        self.assertEqual((f.address(), f.data()), (0xC0DE, 0x5A))


@unittest.skipUnless(os.path.exists(ROM108), "run tools/mkrom.py first")
class System(unittest.TestCase):
    """CPU Rev D, the IO panel card (built without its own data toggles) and the front panel, from their netlists"""
    def test_power_on_boots_the_eprom(self):
        m = machine(); s = m.front.leds()
        self.assertEqual({k for k, v in s.items() if v}, {"PWR", "ROM"})          # the boot map: the EPROM answers at 0000
        self.assertEqual((m.run_mode, m.ccard.loaded()), ("run", False)); self.assertTrue(prompt(m))
        m.front_text(); self.assertTrue(m.ccard.booted())                         # the boot map has ended: RAM is at 0000
        self.assertGreaterEqual(m.front.address(), 0xF000)                        # HBIOS's monitor waits in the EPROM's own
        self.assertTrue(m.front.leds()["ROM"])                                    # window, F000-FFFF: the ROM LED is lit there

    def test_toggle_a_program_in_and_run_it(self):
        m = machine(); d = Shell(m).d
        m.front_set(run=False); self.assertEqual(m.run_mode, "reset")
        m.front_set(load=True); self.assertEqual(m.run_mode, "load")
        self.assertTrue(m.front.leds()["RAM"]); self.assertTrue(m.ccard.loaded())  # the copy and the flag itself
        for b in PROG: m.front_set(switches=b); m.front_set(input=True); m.front_set(input=False)
        self.assertEqual(m.cpu.R[0], len(PROG)); self.assertEqual(m.log.events, {})   # one byte a press, no bus events
        self.assertEqual(m.front.address() & 0xFF, len(PROG))                     # the low byte follows R(0) in LOAD mode
        m.front_set(load=False); self.assertEqual((m.run_mode, m.cpu.R[0]), ("reset", 0))
        self.assertEqual([m.read(a) for a in range(len(PROG))], PROG)
        m.front_set(switches=0x3C, run=True); d.run(max_instructions=2000)
        self.assertEqual(m.run_mode, "run"); m.front_text()
        self.assertEqual(m.front.data(), 0x3C)                                    # INP 4 read the front panel's toggles,
        s = m.front.leds()                                                        # OUT 4 put them on its displays and LEDs
        self.assertEqual({k for k, v in s.items() if v}, {"PWR", "Q", "RAM"})     # Q set by the program; RAM runs, not the ROM
        m.front_set(switches=0xC3); d.run(max_instructions=2000); m.front_text(); self.assertEqual(m.front.data(), 0xC3)

    def test_reset_button_boots_hbios(self):
        m = machine(); d = Shell(m).d
        m.front_set(run=False); m.front_set(load=True)
        for b in PROG: m.front_set(switches=b); m.front_set(input=True); m.front_set(input=False)
        m.front_set(load=False); m.front_set(run=True); d.run(max_instructions=500)
        self.assertTrue(m.ccard.loaded()); self.assertLess(m.cpu.R[m.cpu.P], 0x100)   # the loaded program runs
        m.front_set(run=False); m.front_set(run=True); d.run(max_instructions=500)    # RUN off and on: it runs again
        self.assertTrue(m.ccard.loaded()); self.assertLess(m.cpu.R[m.cpu.P], 0x100)
        m.front_set(reset=True)                                                   # RESET: a boot reset on the bus
        self.assertEqual(m.bus_lines, {"-RESET": 0, "-PAUSE": 1, "-DMAIN": 0}); self.assertEqual(m.run_mode, "reset")
        self.assertFalse(m.ccard.loaded()); self.assertFalse(m.front.leds()["RAM"]); self.assertTrue(m.front.leds()["RESET"])
        m.front_set(reset=False); self.assertEqual(m.run_mode, "run")
        self.assertTrue(m.front.leds()["ROM"]); self.assertTrue(prompt(m))        # HBIOS, from the EPROM

    def test_reset_does_nothing_while_load_is_on(self):
        m = machine()
        m.front_set(load=True); self.assertEqual(m.run_mode, "pause")
        m.front_set(reset=True); self.assertEqual((m.run_mode, m.bus_lines["-RESET"], m.bus_lines["-DMAIN"]), ("pause", 1, 1))
        m.front_set(reset=False, load=False); self.assertEqual(m.run_mode, "run")
        m.front_set(run=False); m.front_set(load=True); m.front_set(reset=True)   # in LOAD mode: no DMA request of it either
        self.assertEqual((m.run_mode, m.cpu.R[0], m.bus_lines["-DMAIN"]), ("load", 0, 1))

    def test_the_cpu_cards_switch_and_the_bus_driver(self):
        """a boot reset made anywhere clears both the flag and the front panel's copy of it"""
        from s5emu.buslink import BusLink
        m = machine(); load = lambda: (m.front_set(run=False), m.front_set(load=True), m.front_set(load=False), m.front_set(run=True))
        load(); self.assertTrue(m.ccard.loaded() and m.front.leds()["RAM"])
        m.reset(); self.assertFalse(m.ccard.loaded() or m.front.leds()["RAM"])    # the CPU card's RESET/RUN switch
        load(); bd = BusLink(m, lambda: False, pty=False)
        self.assertEqual(bd.run("MODE:1")[-1], "Complete"); bd.run("MODE:0")      # a plain reset from the bus driver
        self.assertTrue(m.ccard.loaded() and m.front.leds()["RAM"])
        self.assertEqual(bd.run("MODE:4")[-1], "Complete")                        # BOOT
        self.assertEqual((m.run_mode, m.bus_lines["-DMAIN"]), ("reset", 0))
        self.assertFalse(m.ccard.loaded() or m.front.leds()["RAM"])
        bd.run("MODE:0"); self.assertEqual(m.run_mode, "run"); self.assertTrue(prompt(m))


if __name__ == "__main__":
    unittest.main()
