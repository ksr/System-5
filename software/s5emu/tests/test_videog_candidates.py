# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-24
"""VIDEO-G TEXT's 6845: the ways to wire it that were weighed before Ken chose the write-only one (s5emu.timing_videog's
CANDIDATES, each a change to TEXT's netlist; the table is in hardware/video-g/DESIGN.md section 4). What each does to the write
and the read half, so that the table cannot go stale. The card itself, and the proof that its tests see what was wrong:
test_hw_videogbus.py, whose random-delay cycles (Timed) are used here.

  Static   every candidate against the data sheets, each strobe on its own (timing_videog.rows)
  Random   cycles in time, every gate and strobe with a random delay: 1802 cycles, and the bus driver's order
  Phases   the address map and the read-back of AO, the one readable circuit that passes everything; its mutations"""
import os, random, re, sys, unittest                                       # noqa: F401

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from s5emu import timing as TM, timing_videog as V                        # noqa: E402,F401
from test_hw_videogbus import Timed                                       # noqa: E402

KEYS = {"write-only (the card)": "write-only", "as first drawn": "as drawn"}
C = {KEYS.get(n, n.split()[0]): n for n in V.CANDIDATES}
WRITES_PASS = ("write-only", "L", "Lv", "T", "K", "A", "AT", "KO", "AO")
WRITES_FAIL = ("as drawn", "G", "F")
READS_PASS = {"AT": (0x7B01,), "KO": (0x7801, 0x7901), "AO": (0x7A01, 0x7B01)}       # the only ones that pass strictly
MHZ = (1.76, 1.79, 2.0)


class Static(unittest.TestCase):
    def fails(self, key, half_starts):
        out = {}
        for mhz in MHZ:
            for half, (r, text) in V.study(C[key], mhz).items():
                if half.startswith(half_starts): out[(mhz, half)] = [k for k, m in r if m < 0] if r else None
        return out

    def test_writes(self):
        for key in WRITES_PASS: self.assertEqual(set(map(str, self.fails(key, "write").values())), {"[]"}, key)
        for mhz in MHZ: self.assertEqual(self.fails("as drawn", "write")[(mhz, "write 7801")], ["E width"])
        for key in ("G", "F"): self.assertEqual(self.fails(key, "write")[(2.0, "write 7801")], ["R/W setup"])

    def test_reads(self):
        for key, name in C.items():
            for a in V.READ_AT.get(name, V.REGS_READ):
                got = self.fails(key, "read %04X" % a)
                if key == "write-only": self.assertEqual(set(got.values()), {None}); continue
                ok = all(v == [] for v in got.values())
                self.assertEqual(ok, a in READS_PASS.get(key, ()), "%s %04X %s" % (key, a, got))


WR = (0x7800, 0x7801, 0x7808, 0x79F1)                                      # written (A9 = 0 for A, AT, AO)
OTHER_W = (0x7804, 0x7806, 0x7000, 0x7001, 0x77FF, 0x7C00, 0x6800, 0xF800)
OTHER_R = (0x7802, 0x7804, 0x7806, 0x7000, 0x7C00, 0x6800, 0x0000, 0xF800)


def sequences(r, reads):
    """what the machine does: fetches, executes that read, write, or do neither, S3, the LOAD mode's DMA-ins and idle cycles"""
    out = []
    for _ in range(60):
        if r.random() < 0.15:                                              # LOAD mode: DMA-in, then idle reads without TPA
            a = r.choice(WR[:2] + (0x6800, 0x7804)); out += [("write", a, r.randrange(256)), ("idle", (a & 0xFF00) | ((a + 1) & 0xFF), None)]
            continue
        out.append(("read", r.choice((0x0123, 0x2AF0, 0xF801)), None))      # the fetch
        k = r.choice(("read", "write", "write", "none", "s3"))
        if k == "read": out.append(("read", r.choice(reads + OTHER_R), None))
        elif k == "write": out.append(("write", r.choice(WR + OTHER_W), r.randrange(256)))
        elif k == "none": out.append(("none", r.choice(WR + OTHER_R), r.randrange(256) if r.random() < 0.8 else None))
        else: out += [("none", r.choice(WR), None), ("none", 0x7801, None)]
    return out


def trial(key, mhz, seed, reads=None, driver=False):
    name = C[key]; t = Timed(V.CANDIDATES[name], mhz, seed); r = random.Random(seed * 7 + 1)
    if reads is None: reads = READS_PASS.get(key, (0x7801, 0x7901))
    seq = sequences(r, reads)
    if driver: seq = [("bd-write", r.choice(WR + OTHER_W), r.randrange(256)) if r.random() < 0.5 else ("bd-read", r.choice(reads + OTHER_R), None) for _ in range(80)]
    want, regs = [], []
    for kind, a, v in seq:
        t.cycle(kind, a, v)
        if kind.endswith("write"):
            if 0x7800 <= a < 0x7C00 and not a & 6: want.append((a & 1, v))
            if 0x7800 <= a < 0x7C00 and a & 6 in (4, 6): regs.append((("control", "Y")[(a & 6) == 6], v))
    t.run(); return t, want, regs


def kinds_of(bad): return {re.sub(r"^\S+:", lambda m: m.group(0), b) for b in bad}


class Random(unittest.TestCase):
    N = 6

    def bad(self, key, keep, **kw):
        got = set()
        for mhz in MHZ:
            for seed in range(self.N):
                t, want, regs = trial(key, mhz, seed, **kw)
                got |= {b for b in t.bad if keep(b)}
                if not got and t.took != want: got.add("the 6845 took other bytes than were written")
                if t.clocked != regs: got.add("GFX's registers took other bytes than were written")
        return got

    writes = staticmethod(lambda b: b.startswith(("write", "none", "control", "Y")) and "'s end" not in b)

    def test_writes(self):
        for key in ("write-only", "L", "Lv", "K", "A", "AT", "KO", "AO"): self.assertEqual(self.bad(key, self.writes), set(), key)

    def test_writes_as_drawn_are_seen_to_fail(self):
        self.assertIn("write: E too short", self.bad("as drawn", self.writes))
        self.assertIn("write: RW set up too late", self.bad("G", self.writes))

    def test_reads(self):
        for key in ("AT", "AO"): self.assertEqual(self.bad(key, lambda b: True), set(), key)
        self.assertEqual({b.split(": ")[1] for b in self.bad("KO", lambda b: True)}, {"E too short"})    # (runts, R/W high:
                                                                           # A3 falls before A1 rises, in a read of 7802)
        for key in ("as drawn", "L"):
            got = self.bad(key, lambda b: b.startswith("read"))
            self.assertIn("read: RS changes while E is high", got, key)

    def test_write_only_is_never_on_the_bus(self):
        self.assertEqual(self.bad("write-only", lambda b: True), set())

    def test_the_bus_driver(self):
        for key in ("write-only", "AO"): self.assertEqual(self.bad(key, lambda b: True, driver=True), set(), key)
        for key in ("as drawn", "L", "KO"): self.assertIn("read: RW set up too late", self.bad(key, lambda b: True, driver=True), key)

    def test_the_6845_in_reads_of_other_registers(self):
        on = {}
        for key in ("as drawn", "KO", "AO"):
            on[key] = sum(trial(key, 2.0, s)[0].elsewhere for s in range(self.N))
        self.assertGreater(on["as drawn"], 5000)
        self.assertEqual(on["AO"], 0); self.assertLess(on["KO"], on["as drawn"] / 10)     # (KO: runts)


class Phases(unittest.TestCase):
    """every bus edge of a cycle through hwvideog's plans, the whole block, with GFX: who drives, who takes the byte"""
    def board(self, ops):
        from s5emu.videog import VideoG
        vg = VideoG(V.Bench())
        with V.wired(ops) as rev: return vg, V.hwvideog.NetlistVideoG(vg, rev)

    def answers(self, ops):
        """{address: (drivers, parts written, faults, enabled in the high-byte time, RS moved under E)} of 7000-7FFF, sampled"""
        vg, c = self.board(ops); out = {}
        vg.m.kbd.queue[:] = [65] * 5000; vg.mouse.extend([1] * 5000)
        for a in [0x7000, 0x77FF, 0x7C00, 0x7FFF] + [p + x for p in (0x7800, 0x7900, 0x7A00, 0x7B00) for x in list(range(16)) + [0xF0, 0xFF]]:
            d, f = c.bus_read(a, 0); wr, g = c.bus_write(a, 0, 0)
            out[a] = ([n.replace("video-g ", "") for n, _ in d], [n.replace("video-g ", "") for n in wr], f + g, c.early(a), c.shifts(a))
        return out

    def test_the_map_of_AO(self):
        """a write to 7800-79FF lands as it did; 7A00-7BFF takes none; a read of the 6845 is at 7Ax0/1 (A1 = A2 = 0, A9 = 1);
        nothing is enabled in the high-byte time and no RS moves"""
        was = self.answers(V.AS_DRAWN); got = self.answers(V.CANDIDATES[C["AO"]])
        for a, (d, wr, f, early, shifts) in got.items():
            regs = 0x7800 <= a < 0x7C00
            self.assertEqual((f, early), ([], []), "%04X" % a)
            self.assertEqual([s for s in shifts if s[1] == "IC4"], [], "%04X" % a)
            if not regs: self.assertEqual((d, wr), was[a][:2]); continue
            if a & 0x200: self.assertEqual((d, wr), (["IC4"] if not a & 6 else [], []), "%04X" % a)
            else: self.assertEqual((d, wr), ([] if not a & 6 else was[a][0], was[a][1]), "%04X" % a)
        self.assertTrue(any(x[3] for x in was.values()))                   # (as drawn, section 10's finding 1)

    def test_a_register_written_is_read_back(self):
        vg, c = self.board(V.CANDIDATES[C["AO"]])
        c.bus_write(0x7800, 0, 14); c.bus_write(0x7801, 0, 0x12); c.bus_write(0x7800, 0, 15); c.bus_write(0x7801, 0, 0x34)
        self.assertEqual((vg.reg[14], vg.reg[15]), (0x12, 0x34))
        for a in (0x7A00, 0x7A01, 0x7B01): self.assertEqual([b for _, b in c.bus_read(a, 0)[0]], [0x34])
        self.assertEqual(c.bus_read(0x7801, 0), ([], []))

    def test_never_on_the_bus_without_a_memory_access(self):
        for key, name in C.items():
            c, pins = V.card(V.CANDIDATES[name])
            for before in ("read", "write"):
                for a in WR + OTHER_R + (0x7A01, 0x7B01):
                    for k, e, v in V.trace(c.c, pins, [(before, a), ("none", a), ("none", a ^ 1)]):
                        if k: self.assertNotEqual((v["CS"], v["E"]), (0, 1), "%s %04X %s" % (key, a, e))


def ops_of(key): return V.CANDIDATES[C[key]]
def without(key, ref, pin):                                               # (the pin stays where the first drawing had it)
    n = len(V.AS_DRAWN); return V.AS_DRAWN + [o for o in ops_of(key)[n:] if not (o[1] == ref and o[2] == str(pin))]


MUTATIONS = {                                                              # of AO: one wire not moved, or moved wrongly
    "R/W still on IC24A": without("AO", "IC4", 22), "R/W on GND": ops_of("AO") + [V.w("IC4", 22, V.GND)],
    "R/W on +5V": ops_of("AO") + [V.w("IC4", 22, V.V5)], "R/W on A8": ops_of("AO") + [V.w("IC4", 22, ("IC1", "2"))],
    "R/W on the bus A1": ops_of("AO") + [V.w("IC4", 22, ("IC1", "4"))],
    "IC7.3 still on TPBN": without("AO", "IC7", 3), "IC7.3 on GND (writes at A9 = 1)": ops_of("AO") + [V.w("IC7", 3, V.GND)],
    "IC6.3 still on GND": without("AO", "IC6", 3), "IC6.3 on A8": ops_of("AO") + [V.w("IC6", 3, ("IC1", "2"))],
    "the read on IC6's Y0": [o for o in ops_of("AO") if o[1:3] not in (("IC6", "11"), ("IC6", "15"))],
    "-CS on A1 (IC5.1)": without("AO", "IC5", 1), "-CS on A2 (IC5.2)": without("AO", "IC5", 2),
    "RS straight from A0": without("AO", "IC4", 24), "RS on +5V": ops_of("AO") + [V.w("IC4", 24, V.V5)],
    "RS's AND on A9, not its inverse": ops_of("AO") + [V.w("IC18", 10, V.A9)],
    "RS's XOR on GND": ops_of("AO") + [V.w("IC22", 10, V.GND)],
    "A9 from the bus A1 to the RS gates": ops_of("AO") + [V.w("IC22", 10, ("IC1", "4")), V.w("IC17", 1, ("IC1", "4"))],
}


class Mutations(unittest.TestCase):
    def verdict(self, ops):
        """what sees the wiring: the static rows, the random cycles, or the read-back through the plans"""
        name = "a wrong wire"; V.CANDIDATES[name] = ops; C["mut"] = name; seen = []; V.READ_AT[name] = (0x7A01, 0x7B01)
        try:
            st = V.study(name, 2.0)
            for half, (r, text) in st.items():
                if r is None or any(m < 0 for _, m in r): seen.append("static"); break
            for seed in range(4):
                t, want, regs = trial("mut", 2.0, seed, reads=(0x7A01, 0x7B01))
                if t.bad or t.took != want or t.clocked != regs: seen.append("random"); break
            p = Phases()
            try: vg, c = p.board(ops)
            except ValueError: seen.append("model"); return seen
            try:
                good = all(b[:3] == a[:3] for a, b in zip(GOOD.values(), p.answers(ops).values()))
                c.bus_write(0x7800, 0, 14); c.bus_write(0x7801, 0, 0x12)
                if not good or vg.reg[14] != 0x12 or [b for _, b in c.bus_read(0x7A01, 0)[0]] != [0x12]: seen.append("phases")
            except Exception as e: seen.append("phases (%s)" % type(e).__name__)
        finally: V.CANDIDATES.pop(name); C.pop("mut"); V.READ_AT.pop(name)
        return seen

    def test_every_wrong_wire_is_caught(self):
        GOOD.update(Phases().answers(ops_of("AO")))
        self.assertEqual(self.verdict(ops_of("AO")), [])
        for name, ops in MUTATIONS.items():
            got = self.verdict(ops)
            if os.environ.get("SHOW"): print(name, got)
            self.assertTrue(got, name)


GOOD = {}

if __name__ == "__main__":
    unittest.main()
