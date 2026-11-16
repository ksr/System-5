# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-07
"""Static timing analysis from the netlists (s5emu/timing.py): the review's known results come out of the netlists."""
import os, sys, unittest
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, ".."))
from s5emu.timing import analyse, CardTiming, bus_events


def find(rows, card, text):
    hits = [r for r in rows if r[0] == card and text in r[1]]
    assert hits, "no check %r on %s" % (text, card)
    return hits[0][2] - hits[0][3]                           # margin


class RevDAt2MHz(unittest.TestCase):
    """CPU Rev D at 2 MHz (hardware/TIMING-REVIEW.md, 2026-10-30)"""
    @classmethod
    def setUpClass(cls):
        cls.rows, cls.T = analyse(2.0, cpu_rev="D")

    def test_t1_is_gone_with_the_74hct373(self):
        self.assertFalse([r for r in self.rows if r[0] == "CPU D" and r[1].startswith("LATCH")])

    def test_cpu_card_paths_have_hundreds_of_ns(self):
        self.assertGreater(find(self.rows, "CPU D", "-VMA settles"), 500)
        self.assertGreater(find(self.rows, "CPU D", "2732 read"), 1500)

    def test_t3_the_6845_e_high_time_fails_at_2_mhz(self):
        self.assertAlmostEqual(find(self.rows, "6845 B", "E high time"), -50, delta=1)


class Timing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows, cls.T = analyse(1.76)

    def test_t1_cpu_374_setup_violation_found_from_the_netlist(self):
        self.assertAlmostEqual(find(self.rows, "CPU A-built", "IC1 74LS374"), -102, delta=1)

    def test_t2_6845_rw_rises_during_e(self):
        self.assertLess(find(self.rows, "6845 B", "R/W held low until E falls"), -300)

    def test_memory_rev_d_has_microseconds_to_spare(self):
        for chip in ("IC1 62256-70 read", "IC5 27C256-20 read", "IC1 write: data set up"):
            self.assertGreater(find(self.rows, "memory D", chip), 2000)

    def test_vma_path_goes_through_the_cpu_latch_decode(self):
        r = next(r for r in self.rows if r[0] == "CPU A-built" and "-VMA settles" in r[1])
        self.assertIn("IC1(74LS374", r[4]); self.assertIn("IC9(74LS138", r[4]); self.assertAlmostEqual(r[3], 952, delta=2)

    def test_ide_nand_latch_found_as_a_feedback_loop(self):
        from s5emu.hw import NetlistIDECard
        ide = NetlistIDECard("A"); t = CardTiming("IDE A", ide.nl, ide.c)
        self.assertTrue(t.loops)                             # the NAND latch that makes the INP window
        self.assertEqual({n for n, (_, k) in t.loops.items()}, {n for n, (_, k) in t.loops.items() if k == 2})

    def test_memory_latch_edges_found_by_simulation(self):
        from s5emu.hw import NetlistMemoryCard
        mem = NetlistMemoryCard("D"); t = CardTiming("memory D", mem.nl, mem.c)
        edges = t.latch_edges("read")
        self.assertEqual(set(edges.values()), {("TPA_rise", "TPA_fall")})   # the 4042s: open on TPA, latch as it falls


class Contention(unittest.TestCase):
    def test_cross_card_handover(self):
        from s5emu.timing import contention
        rows, T = contention(1.76)
        ov = {(a.split(" (")[0], b.split(" (")[0]): o for a, b, o, why, tr in rows}
        self.assertAlmostEqual(ov[("CPU A-built IC2", "6845 B IC1")], 28, delta=2)      # the 2732A's 100 ns float time
        self.assertGreater(ov[("memory D IC1", "6845 B IC1")], 150)                     # the CMOS address path
        self.assertFalse(any("memory D IC3" in a for a, b, o, w, t in rows))            # never selected by the jumpers
        rows10, _ = contention(1.76, r13_ohms=10000)
        ov10 = {(a.split(" (")[0], b.split(" (")[0]): o for a, b, o, why, tr in rows10}
        self.assertGreater(ov10[("CPU A-built IC2", "memory D IC1")], 90)                # R13's RC on the EPROM's CE


if __name__ == "__main__":
    unittest.main(verbosity=1)
