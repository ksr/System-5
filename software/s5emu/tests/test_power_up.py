# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-25
"""The states flip-flops and latches come up in (Ken, 2026-11-25, through the Product Manager: "Yes, all ten"). Until that
day no test of the netlist machines chose them: they began unknown, or as the first settle happened to leave them (see
logic.Circuit, power_up), and an unknown open-collector line read as let go. So the IO panel's REQ and DRIVE, which came
up in no known state and could put the toggles on the bus against the 1802, passed every test.

  Start      logic.Circuit's power_up itself; an undefined line raises; the front panel sees the power-on boot reset; the
             IO panel as it was drawn fails when REQ comes up as 1
  ...Up0 / ...Up1   the IO panel's, CPU Rev D's, the front panel's and the bus link's own tests again, with every
             flip-flop and latch of every card at 0, and at 1 (wherever its own clear, preset or enable does not hold it)
"""
import os, sys, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..")); sys.path.insert(0, HERE)
from s5emu.hw import FRONTPANEL_REVS, IOPANEL_REVS, HWMachine, NetlistIOPanel, ROOT          # noqa: E402
from s5emu.logic import Circuit, powering_up                                                  # noqa: E402
from s5emu.netlist import Netlist                                                             # noqa: E402
import test_buslink_c, test_front_panel, test_hw                                              # noqa: E402  (as modules: their tests run where they are)


class Start(unittest.TestCase):
    def ffs(self, power_up):
        """the panel's U10 (REQ, ACK) and U11 (DRIVE) as they were drawn, the bus at rest, after the start"""
        spec = IOPANEL_REVS["A-powerup"]; nl = Netlist(os.path.join(ROOT, spec["net"]))
        for op, *a in spec["rework"]: getattr(nl, op)(*a)
        c = Circuit(nl, power_up=power_up); s = c.bus.sig
        for n in ("-RESET", "-PAUSE", "-MRD", "-MRW", "-VMA", "SC0"): c.ext[s[n]] = 1
        c.drive(TPA=0, TPB=0, A=0, N=0); c.settle()
        u = {m.ref: m for m in c.models}; return u["U10"].state[0], u["U10"].state[1], u["U11"].state[0]

    def test_a_flip_flop_comes_up_as_asked(self):
        self.assertEqual(self.ffs(0), (0, 0, 0)); self.assertEqual(self.ffs(1), (1, 0, 1))   # ACK is held clear: INPUT is up
        self.assertEqual({self.ffs("seed %d" % k) for k in range(12)} - {(q, 0, d) for q in (0, 1) for d in (0, 1)}, set())
        self.assertGreater(len({self.ffs("seed %d" % k) for k in range(12)}), 1)
        self.assertEqual(self.ffs("seed 3"), self.ffs("seed 3"))

    def test_what_the_first_settle_does_without_it(self):
        """REQ and ACK both started at 1: the first settle, from no net values, clears REQ (INPUT_H begins as 1, so ACK is
        not held clear for a pass). power_up puts it back: the test above"""
        spec = IOPANEL_REVS["A-powerup"]; nl = Netlist(os.path.join(ROOT, spec["net"]))
        for op, *a in spec["rework"]: getattr(nl, op)(*a)
        c = Circuit(nl); m = next(x for x in c.models if x.ref == "U10"); m.state = {0: 1, 1: 1}
        for n in ("-RESET", "-PAUSE", "-MRD", "-MRW"): c.ext[c.bus.sig[n]] = 1
        c.settle(); self.assertEqual(m.state[0], 0)                       # the start-up effect, as it still is without power_up

    def test_an_undefined_line_raises(self):
        p = NetlistIOPanel("A-powerup")                                   # REQ unknown: its -DMAIN cannot be told
        with self.assertRaisesRegex(ValueError, "neither pulled nor let go"): p.pulls()
        self.assertEqual(NetlistIOPanel().pulls(), set())                 # the card as it is: nothing to ask

    def test_the_panel_as_drawn_puts_the_toggles_on_the_bus(self):
        for rev, want in (("A-powerup", True), ("A", False)):
            with powering_up(1): p = NetlistIOPanel(rev)
            p.set(switches=0xFF); p.c.drive(N=0, MRD=1, MRW=0, TPB=1); p.c.settle()          # a memory write in RUN
            self.assertEqual(p.c.val.get(p.oe244) == 0, want, rev)

    def test_the_front_panel_sees_the_power_on_boot_reset(self):
        for up in (0, 1, "seed 1", "seed 2"):
            m = HWMachine(cpu_rom=test_front_panel.ROM108, cpu_rev="D", video_rev=None, io_rev=None, panel_rev="A", front_rev="A",
                          pixie_port=0, power_up=up)
            self.assertEqual((m.front.leds()["RAM"], m.ccard.loaded(), m.run_mode), (False, False, "run"), up)


def at(base, up):
    """base's tests with every circuit powering up at `up`"""
    def setUp(self):
        c = powering_up(up); c.__enter__(); self.addCleanup(c.__exit__, None, None, None); base.setUp(self)
    return type("%s_%sUp%d" % (base.__module__.split(".")[-1].replace("test_", ""), base.__name__, up), (base,), {"setUp": setUp, "__module__": __name__})


for _base in (test_hw.IOPanel, test_hw.CPURevD, test_front_panel.Card, test_front_panel.System, test_buslink_c.RevC):
    for _up in (0, 1):
        _t = at(_base, _up); globals()[_t.__name__] = _t
del _base, _t

if __name__ == "__main__":
    unittest.main()
