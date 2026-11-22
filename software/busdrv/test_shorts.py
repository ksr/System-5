#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-21
"""Tests for the short finder (Ken, 2026-11-21: the bus driver reaches every bus line, so it "can be used as a short
detector"): the firmware's WALK command (fwsim.py, the sketch in Python), the simulated backplanes' line-by-line
model with its shorts (backplane.py: set_lines) and bringup.py's plan "shorts", on BUSDRV-B and BUSDRV-C.

  Model   the simulator's own arithmetic: a 100k pull-up against a 10k pull-down reads low, a 10k against a 10k reads
          either way, a supply beats the bus driver's pin, a shorted pair moves as one
  Walk    the command: every line alone moves no other on a sound backplane; what it refuses; that it leaves the card
          as it found it; that a pin held the other way is let go within two expander transactions
  Plan    the bring-up plan: sound backplanes, each kind of short named with where the two lines are neighbours, a
          short to a supply, a CPU card left in, cards in the bus (none answers a single line), one line taking another
          one way only (a card's logic: a warning, not a short), a firmware without WALK

Run: python3 test_shorts.py   (a few seconds)"""
import argparse, contextlib, io, os, sys, unittest
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import s5busdrv as S, bringup as B                                             # noqa: E402
from backplane import Backplane, Backplane36, LINES30, LINES36                 # noqa: E402
from fwsim import FwCard, LINEMAP                                              # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
JUMPERS = "RR------E-------"
DOWN = ("TPA", "TPB", "N0", "N1", "N2")                 # the bus Rev D's pull-downs
bare = lambda name: name.lstrip("-")                    # the host's "-MRD" is the simulator's "MRD"


def card(rev="C", fw=None, **kw):
    """a bus driver alone in a backplane -> (BusDriver, backplane, FwCard). C: the bus Rev D; B: the 2009 backplane"""
    kw.setdefault("cards", ())
    if rev == "C": kw.setdefault("cpu", False)
    bp = (Backplane36 if rev == "C" else Backplane)(**kw); fc = FwCard(bp, rev=rev, **(fw or {}))
    return S.BusDriver(transport=fc), bp, fc


def err(test, bd, op, operand=0):
    with test.assertRaises(S.CardError) as cm: bd.cmd(op, operand)
    return str(cm.exception)


class Model(unittest.TestCase):
    def test_pulls_and_thresholds(self):
        bp = Backplane36(cards=(), cpu=False)
        bp.set_lines({}, set())                                           # no expander pull-ups: the bus Rev D's own levels
        self.assertEqual({n: bp.walk[n] for n in DOWN}, {n: 0 for n in DOWN})
        self.assertTrue(all(bp.walk[n] for n in ("MRD", "MRW", "VMA", "RESET", "D0", "D7", "EF1", "PAUSE", "DMAIN")))
        bp.set_lines({}, set(LINES36))                                    # 100k up against 10k down: 0.45 V, still low
        self.assertEqual({n: bp.walk[n] for n in DOWN}, {n: 0 for n in DOWN})
        self.assertTrue(all(v for n, v in bp.walk.items() if n not in DOWN))      # A0-A7, Q and SC0 by the 100k alone

    def test_a_line_with_nothing_on_it_keeps_its_charge(self):
        bp = Backplane36(cards=(), cpu=False)
        bp.set_lines({"A3": 0}, set()); bp.set_lines({}, set()); self.assertEqual(bp.walk["A3"], 0)
        bp.set_lines({"A3": 1}, set()); bp.set_lines({}, set()); self.assertEqual(bp.walk["A3"], 1)
        bp.set_lines({"A3": 0}, set()); bp.set_lines({}, {"A3"}); self.assertEqual(bp.walk["A3"], 1)    # the pull-up lifts it

    def test_a_pull_up_shorted_to_a_pull_down_reads_either_way(self):
        bp = Backplane36(cards=(), cpu=False, shorts=[("N1", "RESET")])
        seen = set()
        for _ in range(40): bp.set_lines({}, set(LINES36)); seen.add(bp.walk["N1"]); self.assertEqual(bp.walk["N1"], bp.walk["RESET"])
        self.assertEqual(seen, {0, 1})                                    # 2.7 V: between the thresholds
        for level in (0, 1):
            bp = Backplane36(cards=(), cpu=False, shorts=[("N1", "RESET")], between=level)
            bp.set_lines({}, set(LINES36)); self.assertEqual((bp.walk["N1"], bp.walk["RESET"]), (level, level))

    def test_a_supply_beats_the_pin_and_is_counted(self):
        bp = Backplane36(cards=(), cpu=False, shorts=[("D0", "+5V"), ("N0", "GND")])
        bp.set_lines({"D0": 0}, set(LINES36)); self.assertEqual(bp.walk["D0"], 1); self.assertTrue(bp.walk_fight)
        bp.tick(); bp.tick(); self.assertEqual(bp.overload, 2)
        bp.set_lines({}, set(LINES36)); self.assertFalse(bp.walk_fight)
        bp.set_lines({"N0": 1}, set(LINES36)); self.assertEqual(bp.walk["N0"], 0); self.assertTrue(bp.walk_fight)
        self.assertEqual(len(bp.fights()), 2)
        bp.set_pins({}, None); self.assertIsNone(bp.walk); self.assertFalse(bp.walk_fight)

    def test_a_short_must_name_real_lines(self):
        with self.assertRaises(ValueError): Backplane(cards=(), shorts=[("D0", "EF1")])       # no -EF1 on the 30-pin bus
        with self.assertRaises(ValueError): Backplane36(cards=(), cpu=False, shorts=[("D0", "D8")])

    def test_two_open_collector_lines_shorted_go_low_together_everywhere(self):
        """outside WALK too: the bus36 plan's own test of the open-collector lines names such a short"""
        b, bp, out = plan("bus36", "short:EF1:EF2")
        self.assertEqual(status(b)["X2"], "FAIL"); self.assertIn("pulling -EF1 low also takes -EF2 low", text(b, "X2"))


class Walk(unittest.TestCase):
    def test_every_line_alone_on_a_sound_bus_rev_d(self):
        bd, bp, fc = card()
        self.assertTrue(bd.walkable); self.assertIn("walk-1", bd.banner[0])
        lines = bd.walk_lines(); self.assertEqual(len(lines), 34); self.assertEqual({bare(n) for n in lines}, set(LINES36))
        rest = bd.walk()
        self.assertEqual({n for n in lines if rest[n] == 0}, set(DOWN))
        for n in lines:
            got = bd.walk(n, 0); self.assertEqual(got[n], 0, n)
            self.assertEqual({k: v for k, v in got.items() if k != n}, {k: v for k, v in rest.items() if k != n}, n)
        for n in DOWN:
            got = bd.walk(n, 1); self.assertEqual(got[n], 1, n)
            self.assertEqual({k: v for k, v in got.items() if k != n}, {k: v for k, v in rest.items() if k != n}, n)
        self.assertEqual(bp.fights(), []); self.assertEqual(bp.overload, 0)

    def test_busdrv_b(self):
        bd, bp, fc = card("B")                                            # the 2009 backplane: no resistors at all
        self.assertTrue(bd.walkable); lines = bd.walk_lines(); self.assertEqual({bare(n) for n in lines}, set(LINES30))
        self.assertEqual(set(bd.walk().values()), {1})                    # the 100k pull-ups hold every line high
        self.assertEqual([n for n, v in bd.walk("A5", 0).items() if v == 0], ["A5"])
        self.assertIn("WALK:pin,level", err(self, bd, "WALK", "32,0"))    # U3's pins: no such chip on BUSDRV-B
        bp36 = Backplane36(cards=(), cpu=False); bd = S.BusDriver(transport=FwCard(bp36, rev="B"))    # BUSDRV-B in a bus Rev D slot
        self.assertEqual({n for n, v in bd.walk().items() if v == 0}, set(DOWN)); self.assertEqual(len(bd.walk()), 28)

    def test_what_it_refuses(self):
        bd, bp, fc = card()
        for pin in (7, 15, 23, 31, 38, 39, 40, 43, 47, 48, -1):          # the spares, the DEBUG inputs, no such pin
            self.assertIn("WALK:pin,level", err(self, bd, "WALK", "%d,0" % pin), pin)
        self.assertIn("level 0, 1, or 2", err(self, bd, "WALK", "3,3"))
        for n in S.OPEN_COLLECTOR:                                        # never driven high
            self.assertIn("only ever pulled low", err(self, bd, "WALK", "%d,1" % S.WALK_PINS[n]), n)
            self.assertEqual(bd.walk(n, 0)[n], 0)
        bd.master(True); self.assertIn("MONITOR mode", err(self, bd, "WALK", "3,0")); bd.master(False)
        bd.clk_hz(1000); self.assertIn("the clock is running", err(self, bd, "WALK", "3,0")); bd.clk_stop()
        bd2, bp2, fc2 = card(cpu=True)                                    # CPU Rev D in the bus, its DEBUG cable on
        self.assertIn("a CPU card answers on the DEBUG cable", err(self, bd2, "WALK", "0,2"))
        bd3, bp3, fc3 = card(fw=dict(cpu_running=True))
        self.assertIn("TPA/TPB toggling", err(self, bd3, "WALK", "0,2"))
        bd4, bp4, fc4 = card(fw=dict(bus_on=False))
        self.assertIn("bus has no power", err(self, bd4, "WALK", "0,2"))
        self.assertEqual(bp.fights() + bp2.fights() + bp3.fights(), [])

    def test_it_leaves_the_card_as_it_found_it(self):
        bd, bp, fc = card(); fw = fc.fw
        before = ([list(x) for x in fw.iodir], [list(x) for x in fw.olat], [list(x) for x in fw.gppu])
        self.assertEqual(before[2], [[0, 0], [0, 0], [0, 0x07]])
        for n in bd.walk_lines(): bd.walk(n, 0)
        for n in DOWN: bd.walk(n, 1)
        bd.walk()
        self.assertEqual(([list(x) for x in fw.iodir], [list(x) for x in fw.olat], [list(x) for x in fw.gppu]), before)
        self.assertIsNone(bp.walk); self.assertFalse(fw.master)
        self.assertEqual(bd.status(), "bus=on mode=MONITOR board=C cpu=RUN clk=0")
        bd.line("-RESET", True)                                           # a line the card holds low stays held, through a walk of it
        seen = []; inner = bp.set_lines                                   # ... and is never let go on the way, not for one write
        bp.set_lines = lambda drv, pull: (inner(drv, pull), seen.append(bp.walk["RESET"]))[0]
        self.assertEqual(bd.walk("-RESET", 0)["-RESET"], 0); self.assertEqual(bd.walk("D0", 0)["-RESET"], 0)
        self.assertEqual(bd.walk()["-RESET"], 0); self.assertTrue(seen); self.assertEqual(set(seen), {0})
        bp.set_lines = inner
        self.assertEqual(bd.fields(bd.snap())["-RESET"], "0")
        bd.line("-RESET", False); self.assertEqual(bd.fields(bd.snap())["-RESET"], "1")

    def test_a_pin_held_the_other_way_is_let_go_at_once(self):
        bd, bp, fc = card(shorts=[("D0", "+5V"), ("N0", "GND")], stuck_lines={"MRD": 1})
        got = bd.walk("D0", 0); self.assertEqual(got["D0"], 1)            # read after it was let go: it did not follow
        self.assertLessEqual(bp.overload, 2); n = bp.overload             # held against +5V for two expander transactions
        got = bd.walk("N0", 1); self.assertEqual(got["N0"], 0); self.assertLessEqual(bp.overload - n, 2); n = bp.overload
        got = bd.walk("-MRD", 0); self.assertEqual(got["-MRD"], 1); self.assertLessEqual(bp.overload - n, 2)   # a card driving it
        self.assertEqual(len(bp.fights()), 3)
        self.assertEqual(fc.fw.iodir[0][0], 0x7F); self.assertEqual(fc.fw.iodir[1][1], 0x7F)                  # all inputs again

    def test_the_simulator_catches_a_pin_held_too_long(self):
        """a firmware that kept driving D0 against +5V while it read the ports: the count of transactions shows it"""
        bd, bp, fc = card(shorts=[("D0", "+5V")], fw=dict(load_fault="walk-hold"))
        self.assertEqual(bd.walk("D0", 0)["D0"], 1); self.assertGreater(bp.overload, 6)

    def test_the_host_tool(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(SystemExit) as cm: S.main(["--sim", "--rev", "C", "walk"])
        self.assertIn("a CPU card answers on the DEBUG cable", str(cm.exception))     # --sim --rev C has CPU Rev D in the bus
        self.assertEqual(S.WALK_PINS["-MRD"], 20)
        for n, p in S.WALK_PINS.items(): self.assertEqual(LINEMAP[bare(n)], (p >> 4, p >> 3 & 1, p & 7), n)


def plan(name, *faults, busdrv="C", cards=None, bus="auto", fw=None):
    a = argparse.Namespace(plan=name, port=None, log=False, sim=True, fault=list(faults) or None, jumpers=JUMPERS, full=False,
                           rom=None, rom_base=0x8000, save_rom=None, ide_sel=2, ide_data=3, image=None, sectors=1,
                           cf_write_lba=None, video_base=0x7000, interactive=False, keep=False, report=None, mem_rev="D",
                           busdrv=busdrv, cards=cards, bus=bus)
    bd, bp = B.sim_driver(a); out = io.StringIO()
    b = B.Bringup(bd, a, out=lambda s: out.write(s + "\n")); b.plan(name); b.summary()
    return b, bp, out.getvalue()


def status(b): return {s.code: s.status for s in b.steps}
def text(b, code): s = next(s for s in b.steps if s.code == code); return "\n".join(s.lines + s.hints)
def found(b): return sorted(tuple(g) for g in b.shorts_found)


class Plan(unittest.TestCase):
    def test_sound_backplanes(self):
        for busdrv, n in (("C", 34), ("B", 28)):
            b, bp, out = plan("shorts", busdrv=busdrv)
            self.assertEqual(status(b), {"S1": "PASS", "S2": "PASS", "S3": "PASS", "S4": "PASS", "S5": "PASS"}, out)
            self.assertIn("no short between any of the %d lines" % n, text(b, "S5"))
            self.assertEqual(bp.fights(), []); self.assertEqual(bp.overload, 0)
        self.assertIn("the bus Rev D", text(plan("shorts", busdrv="C")[0], "S2"))
        self.assertIn("the 2009 backplane", text(plan("shorts", busdrv="B")[0], "S2"))
        self.assertIn("none to drive high", text(plan("shorts", busdrv="B")[0], "S4"))

    def test_the_slot_table_is_the_bus_rev_ds(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("bus_rev_d", os.path.join(ROOT, "hardware/bus/kicad/rev-d/gen/netlist.py"))
        m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        self.assertEqual(list(B.Bringup.SLOT), list(m.POS))
        self.assertEqual(set(B.Bringup.SLOT) - {"GND", "+5V"}, set(S.WALK_PINS))        # the 34 signals, each with its pin

    def test_two_lines_that_rest_high(self):
        b, bp, out = plan("shorts", "short:D0:D1", "short:MRD:MRW", "short:A3:A4", "short:EF3:DMAIN")
        self.assertEqual(found(b), [("-EF3", "-DMAIN"), ("-MRD", "-MRW"), ("A3", "A4"), ("D0", "D1")], out)
        t = text(b, "S5")
        self.assertIn("D0 and D1 are shorted together", t)
        self.assertIn("D0 / D1: neighbours in every slot (positions 28 and 29 from the GND end) and neighbours on the bus driver's U1 (pins 21 and 22)", t)
        self.assertIn("-EF3 / -DMAIN: neighbours in every slot (positions 33 and 34 from the GND end)", t)
        self.assertEqual(status(b)["S5"], "FAIL"); self.assertEqual(status(b)["S2"], "PASS"); self.assertEqual(bp.fights(), [])

    def test_two_pulled_down_lines(self):
        b, bp, out = plan("shorts", "short:TPA:TPB", "short:N0:N1")
        self.assertEqual(found(b), [("N0", "N1"), ("TPA", "TPB")], out)
        self.assertIn("TPA high: TPB high too", text(b, "S4")); self.assertNotIn("low too", text(b, "S3"))

    def test_a_pulled_up_line_shorted_to_a_pulled_down_one(self):
        """N1 and -RESET are neighbours in the slots, one with a pull-down and one with a pull-up: the pair sits
        between the input thresholds. Found whether the expander then reads it high, low, or now one and now the other"""
        for fault, s2 in ((None, "WARN"), ("between:1", "FAIL"), ("between:0", "FAIL")):
            b, bp, out = plan("shorts", "short:N1:RESET", *([fault] if fault else []))
            self.assertEqual(found(b), [("-RESET", "N1")], out); self.assertEqual(status(b)["S2"], s2, out)
            self.assertIn("neighbours in every slot (positions 3 and 4 from the GND end)", text(b, "S5"))
        self.assertIn("N1 rests high", text(plan("shorts", "short:N1:RESET", "between:1")[0], "S2"))
        self.assertIn("-RESET rests low", text(plan("shorts", "short:N1:RESET", "between:0")[0], "S2"))
        self.assertIn("no clear level at rest", text(plan("shorts", "short:N1:RESET")[0], "S2"))

    def test_three_lines_together_and_lines_that_are_not_neighbours(self):
        b, bp, out = plan("shorts", "short:D5:D6", "short:D6:D7", "short:A0:Q")
        self.assertEqual(found(b), [("A0", "Q"), ("D5", "D6", "D7")], out)
        self.assertIn("D5, D6 and D7 are shorted together", text(b, "S5"))
        self.assertIn("A0 / Q: not neighbours in the slots or on the bus driver: look at the card in the bus", text(b, "S5"))

    def test_a_short_to_a_supply(self):
        b, bp, out = plan("shorts", "short:D0:+5V", "short:N0:GND", "short:A2:GND")
        self.assertEqual(status(b), {"S1": "PASS", "S2": "FAIL", "S3": "FAIL", "S4": "FAIL", "S5": "PASS"}, out)
        self.assertIn("A2 rests low", text(b, "S2")); self.assertNotIn("N0 rests", text(b, "S2"))    # N0 rests low anyway
        self.assertIn("D0 will not go low", text(b, "S3"))
        self.assertIn("D0 and +5V are neighbours in every slot (positions 29 and 30 from the GND end)", text(b, "S3"))
        self.assertIn("N0 will not go high", text(b, "S4")); self.assertIn("GND's neighbour", text(b, "S4"))
        self.assertEqual(found(b), []); self.assertLessEqual(bp.overload, 4)      # two pins, two transactions each
        self.assertNotIn("A2", " ".join(k for k in b.low))                        # a line held low is not driven

    def test_one_line_taking_another_one_way_is_not_called_a_short(self):
        """a card's logic between two bus lines: A3 low takes A4 low, A4 low leaves A3 alone. Named, as a warning"""
        b, bp, out = plan("shorts", "oneway:A3:A4", "short:D0:D1")
        self.assertEqual(found(b), [("D0", "D1")], out); self.assertEqual(status(b)["S5"], "FAIL")
        self.assertIn("A3 low takes A4 low, but not the other way round", text(b, "S5"))
        self.assertIn("Not a plain short", text(b, "S5")); self.assertIn("A3 low: A4 low too", text(b, "S3"))
        b, bp, out = plan("shorts", "oneway:A3:A4")
        self.assertEqual(found(b), []); self.assertEqual(status(b)["S5"], "WARN", out)

    def test_a_missing_pull_down_is_not_called_a_short(self):
        b, bp, out = plan("shorts", "nopull:TPB")
        self.assertEqual(status(b)["S2"], "FAIL"); self.assertIn("TPB rests high", text(b, "S2")); self.assertIn("RN3", text(b, "S2"))
        self.assertEqual(found(b), []); self.assertEqual(status(b)["S5"], "PASS")

    def test_a_cpu_card_left_in(self):
        b, bp, out = plan("shorts", "cpu-in")                             # no DEBUG cable, so the card cannot see it
        self.assertEqual(status(b), {"S1": "PASS", "S2": "FAIL"}, out)    # ... but Q rests low: nothing is driven
        self.assertIn("Q rests low", text(b, "S2")); self.assertIn("a CPU card is in the bus", text(b, "S2"))
        self.assertEqual(bp.fights(), [])
        b, bp, out = plan("load")                                         # the cable on: the card itself refuses
        b2 = B.Bringup(b.bd, b.a, out=lambda s: None); b2.plan("shorts")
        self.assertEqual(status(b2), {"S1": "FAIL"}); self.assertIn("a CPU card answers on the DEBUG cable", text(b2, "S1"))

    def test_with_the_cards_in_the_bus_no_single_line_wakes_one(self):
        """memory Rev D, the 6845 card and the IDE card from their netlists: with each bus line driven alone, low
        or high, none of them drives the data lines or moves another line. So the test may run with them in place."""
        for busdrv in ("C", "B"):
            b, bp, out = plan("shorts", busdrv=busdrv, cards="mem,video,ide")
            self.assertEqual(set(status(b).values()), {"PASS"}, out); self.assertEqual(found(b), [])
            self.assertEqual([e for e in bp.events if e[0] == "fight"], [], busdrv)
        b, bp, out = plan("shorts", "short:A3:A4", "short:MRD:MRW", busdrv="B", cards="mem")
        self.assertEqual(found(b), [("-MRD", "-MRW"), ("A3", "A4")], out)

    def test_busdrv_b_on_each_backplane(self):
        b, bp, out = plan("shorts", "short:TPA:TPB", "short:Q:D7", busdrv="B")       # the 2009 backplane: every line rests high
        self.assertEqual(found(b), [("D7", "Q"), ("TPA", "TPB")], out); self.assertIn("TPA low: TPB low too", text(b, "S3"))
        bp36 = Backplane36(cards=(), cpu=False, shorts=[("TPA", "TPB")]); bd = S.BusDriver(transport=FwCard(bp36, rev="B"))
        a = argparse.Namespace(bus="auto", interactive=False); b = B.Bringup(bd, a, out=lambda s: None); b.plan("shorts")
        self.assertIn("the bus Rev D", text(b, "S2")); self.assertEqual(found(b), [("TPA", "TPB")])
        self.assertIn("TPA high: TPB high too", text(b, "S4"))

    def test_a_firmware_without_walk(self):
        b, bp, out = plan("shorts", "legacy", busdrv="B")
        self.assertEqual(status(b), {"S1": "FAIL"}); self.assertIn("no WALK command", text(b, "S1"))


if __name__ == "__main__":
    with contextlib.redirect_stdout(io.StringIO()): r = unittest.main(exit=False, verbosity=0).result
    print("%d tests, %d failures, %d errors" % (r.testsRun, len(r.failures), len(r.errors)))
    for f in r.failures + r.errors: print(f[1])
    sys.exit(0 if r.wasSuccessful() else 1)
