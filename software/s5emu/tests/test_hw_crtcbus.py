# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-24
"""The 6845 on the bus, inside a machine cycle: what tests/test_hw_videokbd.py cannot see, for the emulator's cards settle
once per cycle. 6845 card Rev B-Clean-Keyboard, gate level, from its netlist:

  F1  a register write must not end in a read. (hardware/TIMING-REVIEW.md T2: on Rev B's wiring R/W = -MRW rises half a
      clock before E = TPB falls)
  F2  the 6845 must be off the bus in a cycle with no memory access (GLO, GHI, PLO, PHI, SEP, SEX put RN on the address
      lines and a byte on the data bus, with -MRD and -MWR high)

The card's 6845 is write-only since 2026-11-24 (Ken: "Write-only"): R/W on ground, E = NOT -MRW. Every test must pass on
the card's netlist (TheCard). On DRAWN, the same netlist with R/W and E put back where Rev B has them, the tests of the two
faults must FAIL (TheCardAsFirstDrawn), which is the proof that they see them; and each of MUTATIONS, one wrong wire of
the change, must be caught (Mutations).

  Phases   every bus edge of a cycle in order, the gates settled after each; who drives D0-D7
  Static   the 6845's data sheet against the card's slowest gates and the 1802's slowest and fastest strobes
           (s5emu.timing.crtc_rows), 1 MHz and 2 MHz parts
  Random   the cycles in time: every gate with a random delay up to its maximum, every 1802 output with a random delay of
           its own, on each edge; the 6845's pins watched as its data sheet has them
"""
import heapq, os, random, sys, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from s5emu.hw import NetlistVideoKbdCard, VIDEO_REVS                                  # noqa: E402
from s5emu.logic import X                                                 # noqa: E402
from s5emu.machine import Keyboard, Video6845                             # noqa: E402
from s5emu import timing as TM                                            # noqa: E402

CARD, DRAWN, MUTANT = "B-Clean-Keyboard", "B-Clean-Keyboard as drawn 2026-11-20", "B-Clean-Keyboard, a wrong wire"
VIDEO_REVS[DRAWN] = dict(VIDEO_REVS[CARD], rework=VIDEO_REVS[CARD]["rework"] + [
    ("wire", "IC3", "22", "J1", "14"), ("wire", "IC3", "23", "J1", "12")])              # R/W = -MRW, E = TPB
MUTATIONS = {                                                            # (wire: pin to the net of a pin; lift: the pin open)
    "R/W on -MRW": [("wire", "IC3", "22", "J1", "14")], "R/W on VCC": [("wire", "IC3", "22", "IC3", "20")], "R/W open": [("lift", "IC3", "22")],
    "E on TPB": [("wire", "IC3", "23", "J1", "12")], "E from /Q": [("wire", "IC18", "5", "IC18", "14"), ("wire", "IC3", "23", "IC18", "6")],
    "IC18A never cleared (pin 1 on VCC)": [("wire", "IC18", "1", "IC18", "14")], "IC18A never set (pin 4 on VCC)": [("wire", "IC18", "4", "IC18", "14")],
    "IC18A set by -MRD": [("wire", "IC18", "4", "J1", "13")], "IC18A's Q open": [("lift", "IC18", "5")]}
REGS = (0x7800, 0x7801, 0x7808, 0x7BF9)                                   # the 6845's addresses
OTHERS = (0x7802, 0x7803, 0x7804, 0x7806, 0x7000, 0x7001, 0x77FF, 0x7C00, 0x7FFF, 0x0000, 0x6800, 0x8801, 0xF800)


def card(rev):
    k = Keyboard(); k.port = None; c = NetlistVideoKbdCard(Video6845(), k, rev)
    d = next(x for x in c.c.mem if x.kind == "CRTC"); c.c.drive(RESET=1)
    return c, d


# ------------------------------------------------------------------------------------------------ edge by edge, no delays
class Bus:
    """one card, machine cycle by machine cycle; log = the fights; writes = what the 6845 took on E's fall"""
    def __init__(self, rev):
        self.card, self.d = card(rev); self.c = self.card.c; self.log = []; self.took = []; self.lost = []; self.drove = []
        self.pend = None; self.c.drive(A=0, TPA=0, TPB=0, MRD=1, MRW=1, VMA=0); self.c.settle(); self.cycle("read", 0)
        self.log.clear()

    def cycle(self, kind, a, v=None):
        for edge in TM.CRTC_CYCLES[kind]:
            kw = dict(A=a >> 8) if edge == "A_hi" else dict(A=a & 255) if edge == "A_lo" else TM._EDGE[edge]
            self.c.drive(**kw); val = self.c.settle(); acc = self.d.access(val)
            if isinstance(acc, str): self.log.append((kind, a, edge, acc)); continue
            data = kind != "read" and v is not None                          # the 1802's byte is on the bus from 2 T to 8 T
            if acc and acc[0] == "r":
                self.drove.append((kind, a, edge))
                if data: self.log.append((kind, a, edge, "the 6845 and the 1802 both drive D0-D7"))
                elif kind != "read": self.log.append((kind, a, edge, "the 6845 drives D0-D7"))
            if acc and acc[0] == "w" and not data: self.log.append((kind, a, edge, "the 6845 is written"))
            if self.pend and not (acc and acc[0] == "w"):                    # the write condition has ended: how?
                (self.took if val.get(self.d.e) == 0 and val.get(self.d.rw) == 0 else self.lost).append(self.pend)
                self.pend = None
            if acc and acc[0] == "w": self.pend = (acc[1], v)


class Phases:
    """(mixin: rev)"""
    def test_F1_no_fight_at_the_end_of_a_register_write(self):
        b = Bus(self.rev)
        for a in REGS: b.cycle("write", a, 0x2A)
        self.assertEqual(b.log, [])

    def test_F1_a_6845_that_takes_the_byte_on_E_falling_is_written(self):
        b = Bus(self.rev)
        for a in REGS: b.cycle("write", a, a & 0x7F)
        self.assertEqual((b.took, b.lost), ([(a & 1, a & 0x7F) for a in REGS], []))

    def test_F1_a_write_then_anything_writes_once(self):
        """the cycle after a write (a fetch, a non-memory execute, DMA in, DMA out, an interrupt's S3, another write) does not
        write again, nor fight"""
        for nxt in ("read", "none", "write"):
            for a2 in REGS + OTHERS:
                b = Bus(self.rev); b.cycle("write", 0x7801, 0x55); b.cycle(nxt, a2, None if nxt == "read" else 0xC3)
                want = [(1, 0x55)] + ([(a2 & 1, 0xC3)] if nxt == "write" and a2 in REGS else [])
                self.assertEqual((b.took, b.lost, b.log), (want, [], []), "%s %04X" % (nxt, a2))

    def test_F2_not_on_the_bus_without_a_memory_access(self):
        b = Bus(self.rev)
        for a in REGS + OTHERS:
            for v in (0x3C, None): b.cycle("none", a, v)
        self.assertEqual((b.log, b.drove, b.took), ([], [], []))

    def test_reads_nothing(self):
        """the 6845 never drives the bus: in no read, its own addresses too"""
        b = Bus(self.rev)
        for a in REGS + OTHERS: b.cycle("read", a)
        self.assertEqual((b.drove, b.log, b.took), ([], [], [])); self.assertEqual(b.d.rw, "GND")

    def test_the_key_is_still_cleared_at_tpb_of_its_read_only(self):
        b = Bus(self.rev); kclr = b.card.n_kclr; lows = []
        real = b.c.settle
        def settle(*a, **k):
            v = real(*a, **k); lows.append(v.get(kclr)); return v
        b.c.settle = settle
        for kind, a in [(k, a) for k in ("read", "write", "none") for a in REGS + OTHERS]:
            lows.clear(); b.cycle(kind, a, None if kind == "read" else 0)
            want = [0 if kind == "read" and a in (0x7802, 0x7803) and e == "TPB_rise" else 1 for e in TM.CRTC_CYCLES[kind]]
            self.assertEqual(lows, want, "%s %04X" % (kind, a))
        b.c.drive(RESET=0); self.assertEqual(real().get(kclr), 0); b.c.drive(RESET=1); self.assertEqual(real().get(kclr), 1)

    def test_every_order_of_power_up_and_reset(self):
        """no state: whatever the bus did before, the first cycles are right"""
        for mrd, mrw, tpa, tpb, res in [(i & 1, i >> 1 & 1, i >> 2 & 1, i >> 3 & 1, i >> 4 & 1) for i in range(32)]:
            b = Bus(self.rev); b.c.drive(MRD=mrd, MRW=mrw, TPA=tpa, TPB=tpb, RESET=res, A=0x78); b.c.settle()
            b.c.drive(RESET=1, MRD=1, MRW=1, TPA=0, TPB=0); b.c.settle(); b.pend = None; b.log.clear(); b.took.clear()
            b.cycle("none", 0x7801, 0x11); b.cycle("write", 0x7800, 14); b.cycle("read", 0x7801)
            self.assertEqual((b.took, b.log), ([(0, 14)], []))


# ------------------------------------------------------------------------------------------------ the data sheets, worst case
class Static:
    def rows(self, mhz, grade, **kw):
        ct, pins, T, vma = TM.crtc_card(self.rev, mhz, **kw); return TM.crtc_rows(ct, pins, T, TM.PARTS[grade], 0x7800, vma)

    def test_F1_F2_every_write_check_holds_for_any_grade(self):
        for mhz in (1.76, 1.79, 2.0):
            for grade in ("MC6845", "MC68B45"):
                rows, info = self.rows(mhz, grade)
                self.assertEqual(([w for w, h, n, _ in rows if w.startswith("write") and h < n], info["faults"], info["viol"]), ([], [], []), "%s %g" % (grade, mhz))


# ------------------------------------------------------------------------------------------------ in time, at random
class Timed:
    """the gates between the bus and the 6845's CS, E, R/W and RS, each change of an output after a random part of its
    maximum delay; the 1802 with a random delay on every edge. The 6845's pins are checked as its data sheet has them"""
    def __init__(self, rev, mhz, grade, seed, slow=False):
        self.rnd = random.Random(seed); self.T = 1000.0 / mhz; self.P = TM.PARTS[grade]; self.slow = slow
        ct, self.pins, _, _ = TM.crtc_card(rev, mhz); c = self.c = ct.c; self.nl = ct.nl
        cone = set(self.pins.values()); self.models = []
        while True:
            more = [m for m in c.models if m not in self.models and any(o in cone for o, _ in m.deps())]
            if not more: break
            self.models += more
            for m in more:
                for o, ins in m.deps():
                    if o in cone: cone |= set(ins)
        self.readers = {}; self.maxd = {}
        for m in self.models:
            p = TM.PARTS[TM.part_of(self.nl, m.ref)]
            self.maxd[m.ref] = max(v for k, v in p.items() if k in ("tpd", "sel", "en", "cascade", "d_q", "le_q", "clk_q"))
            for o, ins in m.deps():
                for i in ins: self.readers.setdefault(i, set()).add(m)
        c.drive(A=0, D=0, TPA=0, TPB=0, MRD=1, MRW=1, VMA=0, RESET=1); self.val = dict(c.settle())
        c.drive(TPA=1); c.settle(); c.drive(TPA=0); self.val = dict(c.settle())
        self.q = []; self.seq = 0; self.due = {}; self.bad = []; self.took = []
        self.last = {k: -1e9 for k in ("CS", "E", "RW", "RS")}; self.on = None
        self.now = 0.0; self.t0 = 0.0; self.drives = []; self.kinds = []

    def put(self, t, net, v):
        self.seq += 1; heapq.heappush(self.q, (t, self.seq, net, v))

    # ---- the 1802
    def d(self, hi=300): return hi if self.slow else self.rnd.uniform(100, hi)

    def cycle(self, kind, a, v=None):
        """put one machine cycle's edges in the queue"""
        T, t, s, r = self.T, self.t0, self.c.bus.sig, self.rnd
        def lines(a, lo, hi):
            for i in range(8): self.put(t + r.uniform(lo, hi), s["A%d" % i], (a >> i) & 1)
        hold = max(self.mwr_end + T - 30 - t, 0) if getattr(self, "mwr_end", None) else 0
        lines(a >> 8, max(200, hold), 850)                                  # (no faster than the fastest strobe; its typical is 600)
        tf = 2 * T + self.d()
        self.put(t + T + self.d(), s["TPA"], 1); self.put(t + tf, s["TPA"], 0)
        lines(a & 255, tf + T / 2 - 25, max(tf + T / 2 - 25, 2.5 * T + 350))
        if kind == "read": self.put(t + 1.5 * T + self.d(), s["-MRD"], 0); self.put(t + 8 * T + self.d(350), s["-MRD"], 1)
        self.mwr_end = None
        if kind == "write":
            self.put(t + 5 * T + self.d(), s["-MRW"], 0); m = t + 7 * T + self.d(); self.put(m, s["-MRW"], 1); self.mwr_end = m
        self.put(t + 6.5 * T + self.d(), s["TPB"], 1); self.put(t + 7.5 * T + self.d(), s["TPB"], 0)
        if kind != "read" and v is not None:                                # the byte, as long as the 1802 drives it
            end = (m + T - 200) if kind == "write" else t + 8 * T
            self.drives.append((t + 2 * T, t + 2 * T + r.uniform(300, 450), end, v))
        self.kinds.append((t, t + 8 * T + (350 if kind == "read" else 0), kind, a, v)); self.t0 += 8 * T

    # ---- the 6845's pins
    def pin(self, t, k, v):
        P, L = self.P, self.last; get = lambda x: v if x == k else self.val.get(self.pins[x]); e, cs, rw = get("E"), get("CS"), get("RW")
        name = lambda: next(("%s %04X" % x[2:4] for x in self.kinds if x[0] <= t < x[1]), "?")
        def err(s): self.bad.append("%s: %s" % (name(), s))
        if self.on:                                                          # E is high, the 6845 selected
            on_t, on_rw = self.on
            if k != "E": err("%s changes while E is high" % k)
            elif v == 0:
                if t - on_t < P["e_high"] and (on_rw == 0 or P["e_high"] < 400): err("E high %.0f ns" % (t - on_t))     # (a 1 MHz part's reads: not here)
                if on_rw == 0 and get("RW") == 0:
                    hit = [x for x in self.drives if x[1] <= t - P["tdsw"] and x[2] >= t + P["tdhw"]]
                    self.took.append((get("RS"), hit[0][3] if hit else None))
                    if not hit: err("the byte is not steady round E's fall")
                elif on_rw == 0: err("write lost")
                self.on = None
        if not self.on and e == 1 and cs == 0 and (k in ("E", "CS")):
            for x in ("CS", "RS", "RW"):
                at = t if x == k else L[x]
                if t - at < P["tas"]: err("%s set up %.0f ns" % (x, t - at))
            self.on = (t, rw)
        if k != "E" and cs == 0 and e == 0 and t - L["E"] < P["tah"]: err("%s held %.0f ns past E" % (k, t - L["E"]))
        if e == 1 and cs == 0 and rw == 1:                                    # it drives D0-D7
            kind = [x for x in self.kinds if x[0] <= t < x[1]]
            if not any(x[2] == "read" for x in kind): err("drives the bus in a %s" % (kind and kind[0][2]))
            if any(a <= t < b for a, _, b, _ in self.drives): err("fights the 1802")
        L[k] = t

    def run(self):
        while self.q:
            t, _, net, v = heapq.heappop(self.q); self.now = t
            if net in self.due and (t, v) not in self.due[net]: continue      # overtaken by a later change of the gate's inputs
            if net in self.due: self.due[net].remove((t, v))
            if self.val.get(net) == v: continue
            for k, n in self.pins.items():
                if n == net: self.pin(t, k, v)
            self.val[net] = v
            for m in self.readers.get(net, ()):
                for o, nv in list(m.outputs(self.val)):
                    if nv is None: nv = self.c.pulls.get(o)
                    pend = self.due.setdefault(o, []); target = pend[-1][1] if pend else self.val.get(o)
                    if nv == target or nv is None: continue
                    if nv == X: self.bad.append("X on %s" % o)
                    at = t + (self.rnd.uniform(0, self.maxd[m.ref]))
                    pend[:] = [p for p in pend if p[0] < at]                  # a change due later than this one never shows
                    last = pend[-1][1] if pend else self.val.get(o)
                    if last != nv: pend.append((at, nv)); self.put(at, o, nv)


class Random:
    N = 12

    def trial(self, mhz, grade, seed):
        t = Timed(self.rev, mhz, grade, seed); r = random.Random(seed * 7 + 1); want = []
        t.cycle("read", 0x0000)
        for _ in range(120):
            kind = r.choice(("read", "write", "none", "none", "write")); a = r.choice(REGS + REGS + OTHERS)
            v = r.randrange(256) if kind == "write" or (kind == "none" and r.random() < 0.8) else None
            t.cycle(kind, a, v)
            if kind == "write" and a in REGS: want.append((a & 1, v))
        t.run(); return t, want

    def test_F1_F2_random_delays(self):
        for mhz, grade in ((1.76, "MC6845"), (2.0, "MC6845"), (1.79, "MC68B45"), (2.0, "MC68B45")):
            for seed in range(self.N):
                t, want = self.trial(mhz, grade, seed)
                self.assertEqual(t.bad[:3], [], "%s at %g MHz, seed %d: %d" % (grade, mhz, seed, len(t.bad)))
                self.assertEqual(t.took, want)


class TheCard(Phases, Static, Random, unittest.TestCase): rev = CARD


def failures(mixin, rev, names=None):
    """{test: it failed} of a mixin's tests on another netlist (an error, not a failure, is no proof)"""
    case = type("Other", (mixin, unittest.TestCase), {"rev": rev, "N": 4}); out = {}
    for n in names or [n for n in dir(mixin) if n.startswith("test_")]:
        r = unittest.TestResult(); case(n).run(r)
        if r.errors: raise AssertionError("%s broke: %s" % (n, r.errors[0][1]))
        out[n] = bool(r.failures)
    return out


class TheCardAsFirstDrawn(unittest.TestCase):
    """reports/netlist.net of 2026-11-20 had R/W = -MRW and E = TPB, as Rev B has: both faults, and the tests see them there"""
    def test_each_fault_test_fails_on_it_and_the_others_pass(self):
        got = {}
        for mixin in (Phases, Static, Random): got.update(failures(mixin, DRAWN))
        for n, failed in sorted(got.items()):
            if n.startswith(("test_F1", "test_F2", "test_reads_nothing")): self.assertTrue(failed, "%s passes on the card as first drawn: it sees nothing" % n)
        self.assertFalse(got["test_the_key_is_still_cleared_at_tpb_of_its_read_only"])


class Mutations(unittest.TestCase):
    def test_every_wrong_wire_is_caught(self):
        """by the edge-by-edge or the random tests (not only the static timing's reading of the netlist)"""
        try:
            for name, ops in MUTATIONS.items():
                VIDEO_REVS[MUTANT] = dict(VIDEO_REVS[CARD], rework=VIDEO_REVS[CARD]["rework"] + ops)
                self.assertTrue(any(failures(Phases, MUTANT).values()) or any(failures(Random, MUTANT).values()), name)
        finally: VIDEO_REVS.pop(MUTANT, None)

    def test_no_change_is_no_failure(self):
        VIDEO_REVS[MUTANT] = dict(VIDEO_REVS[CARD], rework=VIDEO_REVS[CARD]["rework"] + [("wire", "IC18", "1", "IC18", "7")])     # GND to GND
        try: self.assertFalse(any(failures(Phases, MUTANT).values()))
        finally: VIDEO_REVS.pop(MUTANT, None)


if __name__ == "__main__":
    unittest.main()
