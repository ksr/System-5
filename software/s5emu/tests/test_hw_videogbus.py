# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-24
"""VIDEO-G TEXT's 6845 on the bus, inside a machine cycle, at the gates of its netlist: what tests/test_hw_videog.py cannot
see, for it looks at the card once per bus edge. The 6845 is write-only since 2026-11-24 (Ken: "write-only for row 1"): R/W on
ground, E the whole -MRW time of a write to 7800 / 7801. As first drawn E was TPB within -MRW (284 ns at 1.76 MHz on paper,
109 ns with each strobe as late as it may be, against the HD68B45's 220) and the 6845 could be read.

Every test must pass on the card's netlist (TheCard). On FIRST, the same netlist with the five pins put back where they were,
the tests of what was wrong must FAIL (TheCardAsFirstDrawn), which is the proof that they see it; and each of MUTATIONS, one
wrong wire of the change, must be caught (Mutations). The pattern is test_hw_crtcbus.py's (the 6845 card
Rev B-Clean-Keyboard). The other ways to wire it: test_videog_candidates.py.

  Phases   every bus edge of a cycle in order, the gates settled after each: E, who drives D0-D7, what the 6845 takes, the
           GFX board's two register strobes (they were cut to TPB by the same gate)
  Static   the 6845's data sheet against the card's slowest gates and the 1802's slowest and fastest strobes, each strobe on
           its own (s5emu.timing_videog), 1.76, 1.79 and 2 MHz, 1 MHz and 2 MHz parts
  Random   the cycles in time: every gate with a random delay up to its maximum, every 1802 output with a random delay of its
           own on each edge; the 6845's pins watched as its data sheet has them, and the GFX strobes"""
import heapq, os, random, sys, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from s5emu import timing as TM, timing_videog as V                        # noqa: E402
from s5emu.logic import X                                                 # noqa: E402,F401

FIRST = V.AS_DRAWN                                                        # the netlist to 2026-11-24
REGS = (0x7800, 0x7801, 0x7808, 0x79F1, 0x7A00, 0x7BF9)                   # the 6845's addresses
OTHERS = (0x7802, 0x7803, 0x7804, 0x7806, 0x7A04, 0x7000, 0x7001, 0x77FF, 0x7C00, 0x7FFF, 0x0000, 0x6800, 0x8801, 0xF800)
MRD, MRW, TPB_PIN = ("J1", "18"), ("J1", "17"), ("IC17", "3")
MUTATIONS = {
    "R/W on IC24A as it was": [V.w("IC4", 22, ("IC24", "5")), V.w("IC24", 1, MRW), V.w("IC24", 4, MRD)],
    "R/W on -MRW": [V.w("IC4", 22, MRW)], "R/W on -MRD": [V.w("IC4", 22, MRD)], "R/W on +5V": [V.w("IC4", 22, V.V5)], "R/W open": [("lift", "IC4", "22")],
    "E's IC21.9 on -RDCRTC (a read writes)": [V.w("IC21", 9, ("IC6", "15"))], "E's IC21.9 on GND": [V.w("IC21", 9, V.GND)],
    "E's IC21.9 on the key's read": [V.w("IC21", 9, ("IC6", "14"))],
    "IC7.3 on TPBN": [V.w("IC7", 3, V.TPBN)], "IC7.3 on TPB": [V.w("IC7", 3, TPB_PIN)], "IC7.3 on +5V": [V.w("IC7", 3, V.V5)],
    "IC7.3 on A3": [V.w("IC7", 3, V.A3)], "IC7.5 on -MRD": [V.w("IC7", 5, MRD)], "IC7.5 on GND": [V.w("IC7", 5, V.GND)],
    "E open": [("lift", "IC4", "23")], "E from Y2": [V.w("IC21", 10, ("IC7", "13"))]}


# ------------------------------------------------------------------------------------------------ edge by edge, no delays
class Bus:
    """one card, machine cycle by machine cycle; log = the fights; took = what the 6845 took on E's fall"""
    def __init__(self, ops):
        self.card, self.pins = V.card(ops, gfx=True); self.c = self.card.c; self.log = []; self.took = []; self.lost = []
        self.drove = []; self.es = []; self.pend = None; list(V.edges(self.c, "read", 0)); self.low = {"control": [], "Y": []}

    def access(self, val):
        cs, e, rw, rs = (val.get(self.pins[k]) for k in ("CS", "E", "RW", "RS"))
        if cs == 1 or e == 0: return None
        if (cs, e) != (0, 1) or rw not in (0, 1) or rs not in (0, 1): return "undefined: CS %s E %s R/W %s RS %s" % (cs, e, rw, rs)
        return ("r" if rw else "w"), rs

    def cycle(self, kind, a, v=None):
        for edge, val in V.edges(self.c, kind, a):
            acc = self.access(val)
            for k in self.low:
                if val.get(self.card.clocks[k]) != 1: self.low[k].append((kind, a, edge))
            if isinstance(acc, str): self.log.append((kind, a, edge, acc)); continue
            data = kind in ("write", "none") and v is not None                   # the 1802's byte is on the bus
            if acc: self.es.append((kind, a, edge))
            if acc and acc[0] == "r":
                self.drove.append((kind, a, edge))
                if data: self.log.append((kind, a, edge, "the 6845 and the 1802 both drive D0-D7"))
                elif kind not in ("read", "idle"): self.log.append((kind, a, edge, "the 6845 drives D0-D7"))
            if acc and acc[0] == "w" and not data: self.log.append((kind, a, edge, "the 6845 is written"))
            if self.pend and not (acc and acc[0] == "w"):
                (self.took if val.get(self.pins["E"]) == 0 and val.get(self.pins["RW"]) == 0 else self.lost).append(self.pend); self.pend = None
            if acc and acc[0] == "w": self.pend = (acc[1], v)


class Phases:
    """(mixin: ops)"""
    def test_E_is_the_whole_write_strobe(self):
        for a in REGS:
            b = Bus(self.ops); b.cycle("write", a, 0x2A)
            self.assertEqual([e for k, _, e in b.es], ["MWR_fall", "TPB_rise"], "%04X" % a)    # (until MWR_rise)
            self.assertEqual((b.took, b.lost, b.log), ([(a & 1, 0x2A)], [], []), "%04X" % a)

    def test_a_write_then_anything_writes_once(self):
        """the cycle after a write (a fetch, a non-memory execute, S3, a DMA-in, the LOAD mode's idle cycle without TPA, another
        write) does not write again, nor fight"""
        for nxt in ("read", "idle", "none", "write"):
            for a2 in REGS + OTHERS:
                b = Bus(self.ops); b.cycle("write", 0x7801, 0x55); b.cycle(nxt, a2, None if nxt in ("read", "idle") else 0xC3)
                want = [(1, 0x55)] + ([(a2 & 1, 0xC3)] if nxt == "write" and a2 in REGS else [])
                self.assertEqual((b.took, b.lost, b.log), (want, [], []), "%s %04X" % (nxt, a2))

    def test_never_driven_in_any_cycle(self):
        """no read, no write, no cycle without a memory access, pointing at the 6845 or not, has it on the bus; and no cycle but
        a write to it has E"""
        b = Bus(self.ops)
        for a in REGS + OTHERS:
            for kind in ("read", "idle", "none", "write", "read"):
                b.cycle(kind, a, 0x3C if kind in ("write", "none") else None)
        self.assertEqual((b.drove, b.log), ([], [])); self.assertEqual({k for k, a, e in b.es}, {"write"})
        self.assertEqual({a for k, a, e in b.es}, set(REGS)); self.assertEqual(b.pins["RW"], "GND")

    def test_the_gfx_boards_strobes(self):
        """-WRCTL and -WRY: low from -MRW's fall to its rise in a write to 7804 / 7806 (repeated), once; high in every other cycle"""
        for a in REGS + OTHERS + (0x7807, 0x780C, 0x79F6, 0x7BFC):
            reg = {4: "control", 6: "Y"}.get(a & 6) if a & 0xFC00 == 0x7800 else None
            b = Bus(self.ops)
            for kind in ("read", "none", "idle", "write"): b.cycle(kind, a, 1 if kind == "write" else None)
            for k in b.low:
                self.assertEqual(b.low[k], [("write", a, e) for e in ("MWR_fall", "TPB_rise")] if k == reg else [], "%s %04X" % (k, a))

    def test_the_key_is_still_cleared_at_tpb_of_its_read_only(self):
        b = Bus(self.ops); net = b.card.kff["clr"]
        for kind in ("read", "write", "none"):
            for a in REGS + OTHERS:
                lows = [v.get(net) for e, v in V.edges(b.c, kind, a)]
                want = [0 if kind == "read" and a in (0x7802, 0x7803) and e == "TPB_rise" else 1 for e in V.CYCLES[kind]]
                self.assertEqual(lows, want, "%s %04X" % (kind, a))

    def test_every_order_of_power_up_and_reset(self):
        """no state: whatever the bus did before, the first cycles are right"""
        for n in range(32):
            b = Bus(self.ops); bit = [n >> i & 1 for i in range(5)]
            b.c.drive(MRD=bit[0], MRW=bit[1], TPA=bit[2], TPB=bit[3], RESET=bit[4], A=0x78); b.c.settle()
            b.c.drive(RESET=1, MRD=1, MRW=1, TPA=0, TPB=0); b.c.settle(); b.pend = None; b.log.clear(); b.took.clear(); b.lost.clear()
            b.cycle("none", 0x7801, 0x11); b.cycle("write", 0x7800, 14); b.cycle("read", 0x7801); b.cycle("idle", 0x7801)
            self.assertEqual((b.took, b.lost, b.log), ([(0, 14)], [], []))


# ------------------------------------------------------------------------------------------------ the data sheets, worst case
class Static:
    def study(self, mhz, grade):
        T = 1000.0 / mhz; c, pins = V.card(self.ops); ct = TM.CardTiming("TEXT", c.nl, c.c)
        return V.rows(ct, pins, T, TM.PARTS[grade], "write", 0x7801, before="none", vma=V.cpu_vma(T))[0]

    def test_every_write_check_holds_for_either_grade(self):
        for mhz in (1.76, 1.79, 2.0):
            for grade in ("MC6845", "MC68B45"):
                r = self.study(mhz, grade); self.assertIsNotNone(r)
                self.assertEqual([(k, round(m)) for k, m in r if m < 0], [], "%s %g" % (grade, mhz))
                self.assertEqual(len(r), 9)

    def test_E_width_whatever_the_fastest_strobe(self):
        """the data sheet gives no minimum for a strobe's delay: 200 ns (typical) is the analysis's, here 0 to 200"""
        was = TM.CPU["tpa_typ"]
        try:
            for fast in (0, 50, 100, 150, 200):
                TM.CPU["tpa_typ"] = fast
                for mhz in (1.76, 1.79, 2.0):
                    r = self.study(mhz, "MC68B45"); self.assertGreaterEqual(dict(r)["E width"], 0, "%d %g" % (fast, mhz))
        finally: TM.CPU["tpa_typ"] = was


# ------------------------------------------------------------------------------------------------ in time, at random
class Timed:
    """the gates between the bus and the 6845's pins (and the two GFX strobes), each change after a random part of its
    maximum delay; the 1802 with a random delay on every edge"""
    def __init__(self, ops, mhz, seed, grade="MC68B45"):
        self.rnd = random.Random(seed); self.T = 1000.0 / mhz; self.P = TM.PARTS[grade]
        card, self.pins = V.card(ops, gfx=True); c = self.c = card.c; self.nl = card.nl
        self.strobes = {card.ctrl["clk"]: "control", card.yreg["clk"]: "Y"}
        watched = set(self.pins.values()) | set(self.strobes)
        cone = set(watched); self.models = []
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
        c.drive(A=0, TPA=0, TPB=0, MRD=1, MRW=1, VMA=0, RESET=1); c.settle()
        list(V.edges(c, "read", 0)); self.val = dict(c.settle())
        self.q = []; self.seq = 0; self.due = {}; self.bad = []; self.took = []; self.clocked = []; self.elsewhere = 0.0
        self.last = {k: -1e9 for k in ("CS", "E", "RW", "RS")}; self.on = None
        self.now = 0.0; self.t0 = 0.0; self.drives = []; self.kinds = []; self.low = {}

    def put(self, t, net, v): self.seq += 1; heapq.heappush(self.q, (t, self.seq, net, v))
    def d(self, hi=300): return self.rnd.uniform(200, hi)                  # (the data sheet's typical to its maximum)

    def cycle(self, kind, a, v=None):
        if kind.startswith("bd"): return self.driver_cycle(kind[3:], a, v)
        T, t, s, r = self.T, self.t0, self.c.bus.sig, self.rnd
        def lines(b, lo, hi):
            for i in range(8): self.put(t + r.uniform(lo, hi), s["A%d" % i], (b >> i) & 1)
        hold = max(getattr(self, "mwr_end", 0) + T - 30 - t, 0)
        lines(a >> 8, max(200, hold), 850); fetchlike = kind in ("read", "idle")
        if kind != "idle":
            tf = 2 * T + self.d(); self.put(t + T + self.d(), s["TPA"], 1); self.put(t + tf, s["TPA"], 0)
        else: tf = 2 * T + self.d()
        if fetchlike:                                                      # (-MRD's set-up to TPA's fall is T/2 - 25, given)
            self.put(t + min(1.5 * T + self.d(), tf - T / 2 + 25), s["-MRD"], 0); self.put(t + 8 * T + self.d(350), s["-MRD"], 1)
        lines(a & 255, tf + T / 2 - 25, max(tf + T / 2 - 25, 2.5 * T + 350)); self.mwr_end = 0
        if kind == "write":
            self.put(t + 5 * T + self.d(), s["-MRW"], 0); m = t + 7 * T + self.d(); self.put(m, s["-MRW"], 1); self.mwr_end = m
        self.put(t + 6.5 * T + self.d(), s["TPB"], 1); self.put(t + 7.5 * T + self.d(), s["TPB"], 0)
        if not fetchlike and v is not None:
            end = (m + T - 200) if kind == "write" else t + 8 * T
            self.drives.append((t + 2 * T, t + 2 * T + r.uniform(300, 450), end, v))
        self.kinds.append((t, t + 8 * T + (350 if fetchlike else 0), kind, a, v, 8 * T)); self.t0 += 8 * T

    def driver_cycle(self, kind, a, v):
        """a cycle as the bus driver makes it (embedded/bus-driver: cycleAddr, memRead, memWrite), 2 us a step"""
        s = self.c.bus.sig; t = self.t0 + 2000; step = 2000
        def lines(b, at):
            for i in range(8): self.put(at + i, s["A%d" % i], (b >> i) & 1)
        lines(a >> 8, t); self.put(t + step, s["TPA"], 1); self.put(t + 2 * step, s["TPA"], 0); lines(a & 255, t + 3 * step)
        strobe = {"read": "-MRD", "write": "-MRW"}[kind]
        self.put(t + 4 * step, s[strobe], 0); self.put(t + 5 * step, s["TPB"], 1); self.put(t + 6 * step, s["TPB"], 0); self.put(t + 7 * step, s[strobe], 1)
        if kind == "write": self.drives.append((t + 3 * step, t + 3 * step + 100, t + 8 * step, v))
        self.kinds.append((self.t0, t + 9 * step, kind, a, v, 9 * step)); self.t0 = t + 9 * step; self.mwr_end = 0

    def cyc(self, t): return next((x for x in self.kinds if x[0] <= t < x[1]), None)

    # ---- the 6845's pins
    def pin(self, t, k, v):
        P, L = self.P, self.last; get = lambda x: v if x == k else self.val.get(self.pins[x]); e, cs, rw = get("E"), get("CS"), get("RW")
        c = self.cyc(self.on[0] if self.on else t); kind = c[2] if c else "?"
        if c and kind in ("read", "idle") and t - c[0] > 7.9 * self.T and c[5] < 9 * self.T and not (self.on and k == "E"): kind += "'s end"
        err = lambda s: self.bad.append("%s: %s" % (kind, s))
        if self.on:
            on_t, on_rw, on_rs = self.on
            if k != "E": err("%s changes while E is high" % k)
            elif v == 0:
                if t - on_t < P["e_high"]: err("E too short")
                if on_rw == 0 and rw == 0:
                    hit = [x for x in self.drives if x[1] <= t - P["tdsw"] and x[2] >= t + P["tdhw"]]
                    self.took.append((get("RS"), hit[0][3] if hit else None))
                    if not hit: err("the byte is not steady round E's fall")
                elif on_rw == 0: err("write lost")
                else:                                                      # (the cycle it began in)
                    c0 = self.cyc(on_t); self.elsewhere += (t - on_t) if c0 and (c0[3] & 6 or not 0x7800 <= c0[3] < 0x7C00) else 0
                self.on = None
        if not self.on and e == 1 and cs == 0 and k in ("E", "CS"):
            for x in ("CS", "RS", "RW"):
                if t - (t if x == k else L[x]) < P["tas"]: err("%s set up too late" % x)
            self.on = (t, rw, get("RS"))
        if k != "E" and cs == 0 and e == 0 and t - L["E"] < P["tah"]: err("%s not held past E" % k)
        if e == 1 and cs == 0 and rw == 1:
            if not c or c[2] not in ("read", "idle"): err("the 6845 drives the bus")
            if any(a <= t < b for a, _, b, _ in self.drives): err("the 6845 fights the 1802")
        L[k] = t

    def strobe(self, t, which, v):
        c = self.cyc(t)
        if v == 0: self.low[which] = t
        elif which in self.low:
            if t - self.low[which] < 100: self.bad.append("%s strobe too short" % which)
            hit = [x for x in self.drives if x[1] <= t - 25 and x[2] >= t + 5]
            self.clocked.append((which, hit[0][3] if hit else None))

    def run(self):
        while self.q:
            t, _, net, v = heapq.heappop(self.q)
            if net in self.due and (t, v) not in self.due[net]: continue
            if net in self.due: self.due[net].remove((t, v))
            if self.val.get(net) == v: continue
            for k, n in self.pins.items():
                if n == net: self.pin(t, k, v)
            if net in self.strobes: self.strobe(t, self.strobes[net], v)
            self.val[net] = v
            for m in self.readers.get(net, ()):
                for o, nv in list(m.outputs(self.val)):
                    if nv is None: nv = self.c.pulls.get(o)
                    pend = self.due.setdefault(o, []); target = pend[-1][1] if pend else self.val.get(o)
                    if nv == target or nv is None: continue
                    at = t + self.rnd.uniform(0, self.maxd[m.ref])
                    pend[:] = [p for p in pend if p[0] < at]
                    last = pend[-1][1] if pend else self.val.get(o)
                    if last != nv: pend.append((at, nv)); self.put(at, o, nv)


def sequences(r, reads):
    """what the machine does: fetches, executes that read, write or do neither, S3, the LOAD mode's DMA-ins and idle cycles"""
    out = []
    for _ in range(60):
        if r.random() < 0.15:                                              # LOAD mode: DMA-in, then idle reads without TPA
            a = r.choice(REGS[:2] + (0x6800, 0x7804)); out += [("write", a, r.randrange(256)), ("idle", (a & 0xFF00) | ((a + 1) & 0xFF), None)]
            continue
        out.append(("read", r.choice((0x0123, 0x2AF0, 0xF801)), None))     # the fetch
        k = r.choice(("read", "write", "write", "none", "s3"))
        if k == "read": out.append(("read", r.choice(reads + OTHERS), None))
        elif k == "write": out.append(("write", r.choice(REGS + OTHERS), r.randrange(256)))
        elif k == "none": out.append(("none", r.choice(REGS + OTHERS), r.randrange(256) if r.random() < 0.8 else None))
        else: out += [("none", r.choice(REGS), None), ("none", 0x7801, None)]
    return out


def trial(ops, mhz, seed, reads=REGS, driver=False, grade="MC68B45"):
    """-> (Timed run, the bytes written to the 6845, the bytes written to GFX's registers)"""
    t = Timed(ops, mhz, seed, grade); r = random.Random(seed * 7 + 1); seq = sequences(r, reads)
    if driver: seq = [("bd-write", r.choice(REGS + OTHERS), r.randrange(256)) if r.random() < 0.5 else ("bd-read", r.choice(reads + OTHERS), None) for _ in range(80)]
    want, regs = [], []
    for kind, a, v in seq:
        t.cycle(kind, a, v)
        if kind.endswith("write") and a & 0xFC00 == 0x7800:
            if not a & 6: want.append((a & 1, v))
            elif a & 4: regs.append(("Y" if a & 2 else "control", v))
    t.run(); return t, want, regs


class Random:
    N = 8

    def run_trials(self, **kw):
        for mhz, grade in ((1.76, "MC6845"), (2.0, "MC6845"), (1.79, "MC68B45"), (2.0, "MC68B45")):
            for seed in range(self.N):
                t, want, regs = trial(self.ops, mhz, seed, grade=grade, **kw)
                self.assertEqual(t.bad[:3], [], "%s at %g MHz, seed %d: %d" % (grade, mhz, seed, len(t.bad)))
                self.assertEqual(t.took, want); self.assertEqual(t.clocked, regs)

    def test_random_delays(self): self.run_trials()
    def test_random_delays_from_the_bus_driver(self): self.run_trials(driver=True)


class TheCard(Phases, Static, Random, unittest.TestCase): ops = []


def failures(mixin, ops, names=None, **kw):
    """{test: it failed} of a mixin's tests on another netlist (an error, not a failure, is no proof)"""
    case = type("Other", (mixin, unittest.TestCase), dict({"ops": ops, "N": 4}, **kw)); out = {}
    for n in names or [n for n in dir(mixin) if n.startswith("test_")]:
        r = unittest.TestResult(); case(n).run(r)
        if r.errors: raise AssertionError("%s broke: %s" % (n, r.errors[0][1]))
        out[n] = bool(r.failures)
    return out


class TheCardAsFirstDrawn(unittest.TestCase):
    """reports/netlist.net to 2026-11-24: E = TPB within -MRW, the 6845 readable through IC24A's R/W; the tests see it there"""
    def test_each_test_of_the_change_fails_on_it_and_the_others_pass(self):
        got = {}
        for mixin in (Phases, Static, Random): got.update(failures(mixin, FIRST))
        must_fail = {"test_E_is_the_whole_write_strobe", "test_never_driven_in_any_cycle", "test_the_gfx_boards_strobes",
                     "test_every_write_check_holds_for_either_grade", "test_E_width_whatever_the_fastest_strobe",
                     "test_random_delays", "test_random_delays_from_the_bus_driver"}
        self.assertEqual({n for n, failed in got.items() if failed}, must_fail)

    def test_what_fails_on_it_is_the_short_E(self):
        """not only something else: the static rows name E's width, at every speed; a random run sees "E too short" in a write"""
        case = type("Other", (Static, unittest.TestCase), {"ops": FIRST})()
        for mhz in (1.76, 1.79, 2.0): self.assertEqual([k for k, m in case.study(mhz, "MC68B45") if m < 0], ["E width"])
        seen = set()
        for seed in range(6): seen |= set(trial(FIRST, 2.0, seed)[0].bad)
        self.assertIn("write: E too short", seen)


class Mutations(unittest.TestCase):
    def test_every_wrong_wire_is_caught(self):
        """by the edge-by-edge or the random tests (not only the static timing's reading of the netlist)"""
        for name, ops in MUTATIONS.items():
            hits = [n for n, f in failures(Phases, ops).items() if f]
            if os.environ.get("SHOW"): print(name, len(hits), "phases")
            self.assertTrue(hits or any(failures(Random, ops).values()), name)

    def test_no_change_is_no_failure(self):
        self.assertFalse(any(failures(Phases, [V.w("IC4", 22, V.GND), V.w("IC24", 1, V.V5)]).values()))


if __name__ == "__main__":
    unittest.main()
