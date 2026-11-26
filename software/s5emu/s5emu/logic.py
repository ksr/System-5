# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-06
"""Gate-level logic for one card, built from its KiCad netlist (see netlist.py).

Net values: 0, 1, None (nothing drives it: floating) and X (unknown, or two drivers fighting).
Inputs that float read as 1 on LS TTL parts and as X on CMOS parts.

Logic models, chosen by the KiCad lib part name and checked against the pin names in the netlist:
  74x00 74x32   quad NAND / OR (standard 14-pin quad pinout)
  74x02         quad NOR (outputs on pins 1, 4, 10, 13)
  74x04 74x05   hex inverter (the 05 open collector: high or floating, pulled up by a resistor)
  74x74         dual D flip-flop, asynchronous PRE/CLR, rising-edge clock
  74x85         4-bit comparator with cascade inputs
  74x138        3-to-8 decoder (G1 high, G2A/G2B low enable; outputs active low)
  74x151        8-to-1 mux: strobe G high forces Y low and W high; else Y = D[CBA], W = not Y
  74x373        octal latch: transparent while ENC is high; OC high = outputs off
  74x374        octal D flip-flop, rising-edge clock (pin 11)
  74x75         4-bit latch: D1-2 transparent while C12 is high, D3-4 while C34 is high
  4042          quad latch: transparent while CLK = POL, holds on the other level
  4050          hex buffer
Bus devices (the card reads their pins after the logic settles; they drive only the bus data lines):
  62256 27256   memory chips (CE/OE/WE); 2732 the CPU card's boot EPROM (a 2732 whose data pins are not on the bus,
                like the 6845 card's character ROM, is left unmodelled)
  7134          dual-port RAM, the bus side (right port: CER/OER/R-W); the left port is the display's
  6845          CRTC register interface: CS low and E high; R/W; RS = register select
  1852          CDP1852 input port: drives the bus while CS1 and CS2 are high (MODE low)
  1861          CDP1861: listens only; the card's DISPON / DISPOFF pins are read
  D_Schottky    a diode whose anode (pin 2) is on a net with a pull-up: it takes that net low while its cathode (pin 1)
                is low, and lets it go otherwise (the IO panel's D1, 2026-11-25). Any other diode is outside the logic
Pull networks (G09R, RNX4): a weak pull of each pin to whatever pin 1 is on; a resistor with one end on a supply is a
weak pull of its other end. C30 = the System-5 bus connector.

KiCad's own 74xx library (VIDEO-G 1.0, 2026-11-20: its two boards are drawn with the stock symbols, lib part "74LSnn"
whatever family is fitted). The gate packages there number their pins and do not name them, and the other parts name
them their own way (74LS138: A0-A2, E1, E2, E3, O0-O7), so each has a model of its own below, with the same logic as
the model above it where there is one:
  74LS04 74LS05 (and the 7416)   hex inverter; the 05 / 7416 open collector
  74LS08 74LS32 74LS86           quad 2-input AND / OR / XOR
  74LS10 74LS20                  triple 3-input / dual 4-input NAND
  74LS74 74LS85 74LS138 74LS373  as above, by KiCad's pin names
  74LS157                        quad 2-to-1 multiplexer: E high forces every Z low; else Z = I1 if S else I0

Any other chip is left unmodelled, which is allowed only off the bus path: Circuit traces back from every
control and address pin of the bus devices through the modelled logic, and refuses to build if that trace reaches an
output of an unmodelled chip (or a non-data output of a bus device). The 6845 card's character generator and dot
clock are such parts.
"""
import contextlib, random, re

X = 2
PASSIVE = ("C-US", "CPOL", "R-US", "LED", "MA0", "CRYTAL", "cdp_RCA", "PINHD", "jumper_", "switch-")
DRIVING = ("output", "tri_state", "bidirectional", "open_collector", "open_emitter", "power_out")


def ttl(v): return 1 if v is None else v
def cmos(v): return X if v is None else v
def inv(v): return v if v == X else 1 - v


class Model:
    def __init__(self, nl, ref): self.ref = ref; self.nl = nl; self.f = nl.part_pins(ref)

    def n(self, pin, function):
        """the net on `pin`, after checking the netlist names that pin `function`; None if the netlist leaves the pin
        out (a gate the schematic never placed)"""
        if (self.ref, str(pin)) not in self.nl.pins: return None
        fn = self.nl.function(self.ref, pin)
        if fn != function: raise ValueError("%s pin %s is %s in the netlist, the %s model expects %s" % (self.ref, pin, fn, type(self).__name__, function))
        return self.nl.net(self.ref, pin)

    def deps(self):
        """[(output net, [input nets])] for the bus-path trace"""
        return []


class Quad(Model):
    GATES = (("3", "1", "2"), ("6", "4", "5"), ("8", "9", "10"), ("11", "12", "13"))

    def __init__(self, nl, ref, op):
        super().__init__(nl, ref); self.op = op
        self.gates = [g for g in ((self.n(o, "O"), self.n(a, "I0"), self.n(b, "I1")) for o, a, b in self.GATES) if g[0]]

    def outputs(self, val):
        for o, a, b in self.gates:
            x, y = ttl(val.get(a)), ttl(val.get(b))
            if self.op == "or": r = 1 if 1 in (x, y) else 0 if x == y == 0 else X
            else: r = 1 if 0 in (x, y) else 0 if x == y == 1 else X
            yield o, r

    def deps(self): return [(o, [a, b]) for o, a, b in self.gates]


class Nor02(Quad):
    GATES = (("1", "2", "3"), ("4", "5", "6"), ("10", "8", "9"), ("13", "11", "12"))      # 74LS02: outputs on 1, 4, 10, 13

    def __init__(self, nl, ref): super().__init__(nl, ref, "nor")

    def outputs(self, val):
        for o, a, b in self.gates:
            x, y = ttl(val.get(a)), ttl(val.get(b))
            yield o, 0 if 1 in (x, y) else 1 if x == y == 0 else X


class Nand03(Quad):
    """74HC03 quad 2-input NAND with open-drain outputs (2026-11-22: CPU Rev D's boot reset, the IO panel's DMA request,
    the front panel's RESET button): both inputs high pull the output low; otherwise it is let go, for a pull-up or
    another card's gate on the same line"""
    def __init__(self, nl, ref): super().__init__(nl, ref, "nand")

    def outputs(self, val):
        for o, a, b in self.gates:
            x, y = ttl(val.get(a)), ttl(val.get(b))
            yield o, (None if 0 in (x, y) else 0 if x == y == 1 else X)


class Nand3(Model):
    """74HCT10 triple 3-input NAND (the IO panel's OUT 4 strobe)"""
    GATES = (("12", "1", "2", "13"), ("6", "3", "4", "5"), ("8", "9", "10", "11"))

    def __init__(self, nl, ref):
        super().__init__(nl, ref)
        self.gates = [g for g in ((self.n(o, "O"),) + tuple(self.n(i, "I%d" % k) for k, i in enumerate(ins))
                                  for o, *ins in self.GATES) if g[0]]

    def outputs(self, val):
        for o, *ins in self.gates:
            v = [ttl(val.get(i)) for i in ins]
            yield o, 1 if 0 in v else 0 if all(x == 1 for x in v) else X

    def deps(self): return [(o, list(ins)) for o, *ins in self.gates]


class Nand4(Model):
    """74HCT20 dual 4-input NAND (CPU Rev D's F000 window decode)"""
    GATES = (("6", "1", "2", "4", "5"), ("8", "9", "10", "12", "13"))

    def __init__(self, nl, ref):
        super().__init__(nl, ref)
        self.gates = [g for g in ((self.n(o, "O"),) + tuple(self.n(i, "I%d" % k) for k, i in enumerate(ins))
                                  for o, *ins in self.GATES) if g[0]]

    def outputs(self, val):
        for o, *ins in self.gates:
            v = [ttl(val.get(i)) for i in ins]
            yield o, 1 if 0 in v else 0 if all(x == 1 for x in v) else X

    def deps(self): return [(o, list(ins)) for o, *ins in self.gates]


class Hex05(Model):
    """74LS05 hex inverter, open collector: a high input pulls the output low, a low input lets it float (pull-ups)"""
    PAIRS = (("2", "1"), ("4", "3"), ("6", "5"), ("8", "9"), ("10", "11"), ("12", "13"))

    def __init__(self, nl, ref):
        super().__init__(nl, ref); self.pairs = [p for p in ((self.n(o, "O"), self.n(i, "I")) for o, i in self.PAIRS) if p[0]]

    def outputs(self, val):
        for o, i in self.pairs:
            v = ttl(val.get(i)); yield o, (0 if v == 1 else None if v == 0 else X)

    def deps(self): return [(o, [i]) for o, i in self.pairs]


class DFF74(Model):
    """74LS74 dual D flip-flop: PRE / CLR active low and asynchronous (both low = Q and /Q high); otherwise Q takes D
    on a rising CLK edge"""
    HALVES = (("1", "2", "3", "4", "5", "6"), ("13", "12", "11", "10", "9", "8"))      # CLR D CLK PRE Q /Q
    NAMES = ("CLR", "D", "CLK", "PRE", "Q", "~{Q}")                                     # what the symbol calls them

    def __init__(self, nl, ref):
        super().__init__(nl, ref); self.ff = []
        for half in self.HALVES:
            nets = [self.n(pin, name) for pin, name in zip(half, self.NAMES)]
            if nets[4] or nets[5]: self.ff.append(nets)
        self.state = {i: X for i in range(len(self.ff))}; self.last = {i: None for i in range(len(self.ff))}

    def outputs(self, val):
        for i, (clr, d, clk, pre, q, nq) in enumerate(self.ff):
            c, p, k = ttl(val.get(clr)), ttl(val.get(pre)), ttl(val.get(clk))
            if c == 0 and p == 0: qv, nqv = 1, 1
            else:
                if c == 0: self.state[i] = 0
                elif p == 0: self.state[i] = 1
                elif X in (c, p): self.state[i] = X
                elif self.last[i] == 0 and k == 1: self.state[i] = ttl(val.get(d))
                qv, nqv = self.state[i], inv(self.state[i])
            self.last[i] = k
            if q: yield q, qv
            if nq: yield nq, nqv

    def deps(self):
        out = []
        for clr, d, clk, pre, q, nq in self.ff:
            ins = [n for n in (clr, d, clk, pre) if n]
            out += [(n, ins) for n in (q, nq) if n]
        return out


class WiredDiode(Model):
    """a diode onto a pulled-up net: the anode's net is low while the cathode's is"""
    def __init__(self, nl, ref): super().__init__(nl, ref); self.k, self.a = self.n("1", "K"), self.n("2", "A")
    def outputs(self, val):
        v = val.get(self.k); yield self.a, 0 if v == 0 else X if v == X else None

    def deps(self): return [(self.a, [self.k])]


class Hex04(Model):
    PAIRS = (("2", "1"), ("4", "3"), ("6", "5"), ("8", "9"), ("10", "11"), ("12", "13"))

    def __init__(self, nl, ref):
        super().__init__(nl, ref); self.pairs = [p for p in ((self.n(o, "O"), self.n(i, "I")) for o, i in self.PAIRS) if p[0]]

    def outputs(self, val):
        for o, i in self.pairs: yield o, inv(ttl(val.get(i)))

    def deps(self): return [(o, [i]) for o, i in self.pairs]


class Buffer4050(Model):
    PAIRS = (("2", "3"), ("4", "5"), ("6", "7"), ("10", "9"), ("12", "11"), ("15", "14"))

    def __init__(self, nl, ref):
        super().__init__(nl, ref); self.pairs = [p for p in ((self.n(o, "O"), self.n(i, "I")) for o, i in self.PAIRS) if p[0]]

    def outputs(self, val):
        for o, i in self.pairs: yield o, cmos(val.get(i))

    def deps(self): return [(o, [i]) for o, i in self.pairs]


class Mux151(Model):
    def __init__(self, nl, ref):
        super().__init__(nl, ref); f = self.f
        self.d = [f["D%d" % i] for i in range(8)]; self.sel = [f["A"], f["B"], f["C"]]; self.g = f["G"]; self.y = f["Y"]; self.w = f["W"]

    def outputs(self, val):
        g = ttl(val.get(self.g))
        if g == 1: yield self.y, 0; yield self.w, 1; return
        s = [ttl(val.get(n)) for n in self.sel]
        cands = {ttl(val.get(self.d[i])) for i in range(8) if all(s[b] in (X, (i >> b) & 1) for b in range(3))}
        y = cands.pop() if len(cands) == 1 else X
        if g == X: y = 0 if y == 0 else X
        yield self.y, y; yield self.w, inv(y)

    def deps(self):
        ins = self.d + self.sel + [self.g]; return [(self.y, ins), (self.w, ins)]


class Dec138(Model):
    SEL, EN, OUT = ("A", "B", "C"), ("G1", "G2A", "G2B"), "Y%d"                         # what the symbol calls the pins

    def __init__(self, nl, ref):
        super().__init__(nl, ref); f = self.f
        self.sel = [f[k] for k in self.SEL]; self.g = [f[k] for k in self.EN]; self.y = [f[self.OUT % i] for i in range(8)]

    def outputs(self, val):
        g1, g2a, g2b = (ttl(val.get(n)) for n in self.g); s = [ttl(val.get(n)) for n in self.sel]
        on = 1 if (g1, g2a, g2b) == (1, 0, 0) else 0 if 1 in (g2a, g2b) or g1 == 0 else X
        for i, y in enumerate(self.y):
            hit = 1 if all(s[b] == (i >> b) & 1 for b in range(3)) else 0 if any(s[b] not in (X, (i >> b) & 1) for b in range(3)) else X
            yield y, 1 if on == 0 or hit == 0 else 0 if on == 1 and hit == 1 else X

    def deps(self): return [(y, self.sel + self.g) for y in self.y]


class Comp85(Model):
    CI, CO = ("A<B_I", "A=B_I", "A>B_I"), ("A<B_O", "A=B_O", "A>B_O")                  # what the symbol calls the pins

    def __init__(self, nl, ref):
        super().__init__(nl, ref); f = self.f
        self.a = [f["A%d" % i] for i in range(4)]; self.b = [f["B%d" % i] for i in range(4)]
        self.ci = [f[k] for k in self.CI]; self.co = [f[k] for k in self.CO]

    def outputs(self, val):
        a = [ttl(val.get(n)) for n in self.a]; b = [ttl(val.get(n)) for n in self.b]
        lt_i, eq_i, gt_i = (ttl(val.get(n)) for n in self.ci)
        if X in a or X in b: res = (X, X, X)
        else:
            A = sum(v << i for i, v in enumerate(a)); B = sum(v << i for i, v in enumerate(b))
            if A > B: res = (0, 0, 1)
            elif A < B: res = (1, 0, 0)
            elif eq_i == 1: res = (0, 1, 0)                             # equal: the cascade inputs decide
            elif X in (lt_i, eq_i, gt_i): res = (X, X, X)
            else: res = (inv(gt_i), 0, inv(lt_i))                       # SN74LS85 table: A=B_I low
        for n, v in zip(self.co, res): yield n, v

    def deps(self): return [(o, self.a + self.b + self.ci) for o in self.co]


class Latch(Model):
    """level latches: [(enable net, active level, [(d, q, nq or None)])]; output-off net (active high) optional"""
    rd = staticmethod(ttl)                                              # how a floating input reads

    def _setup(self, groups, off=None):
        self.groups = groups; self.off = off; self.state = {q: X for _, _, bits in groups for _, q, _ in bits}

    def outputs(self, val):
        rd = self.rd; off = rd(val.get(self.off)) if self.off else 0
        for en, level, bits in self.groups:
            e = rd(val.get(en))
            for d, q, nq in bits:
                dv = rd(val.get(d))
                if e == level: self.state[q] = dv
                elif e == X and self.state[q] != dv: self.state[q] = X
                s = self.state[q]
                yield q, (None if off == 1 else X if off == X else s)
                if nq: yield nq, inv(s)

    def deps(self):
        out = []
        for en, _, bits in self.groups:
            for d, q, nq in bits:
                ins = [d, en] + ([self.off] if self.off else [])
                out.append((q, ins))
                if nq: out.append((nq, ins))
        return out


class Latch4042(Latch):
    """transparent while CLK = POL: modelled with POL tied (both System-5 memory cards tie it to VCC). CMOS inputs."""
    rd = staticmethod(cmos)

    def __init__(self, nl, ref):
        super().__init__(nl, ref); f = self.f
        if nl.net(ref, "6") not in ("VCC", "GND"): raise ValueError("%s: 4042 POL must be tied to a supply" % ref)
        level = 1 if nl.net(ref, "6") == "VCC" else 0
        self._setup([(f["CLK"], level, [(f["D%d" % i], f["Q%d" % i], f["~{Q%d}" % i]) for i in range(4)])])


class Latch373(Latch):
    def __init__(self, nl, ref):
        super().__init__(nl, ref); f = self.f
        self._setup([(f["ENC"], 1, [(f["%dD" % i], f["%dQ" % i], None) for i in range(1, 9)])], off=f["OC"])


class Reg374(Latch):
    """74LS374 octal D flip-flop: Q takes D on the rising edge of CLK (pin 11; the 373 symbol calls it ENC); OC high =
    outputs off. Same pinout as the 373."""
    def __init__(self, nl, ref):
        super().__init__(nl, ref); f = self.f
        self._setup([(f["ENC"], 1, [(f["%dD" % i], f["%dQ" % i], None) for i in range(1, 9)])], off=f["OC"])
        self.clk_last = None

    def outputs(self, val):
        rd = self.rd; off = rd(val.get(self.off)); (clk, _, bits), = self.groups; k = rd(val.get(clk))
        edge = self.clk_last == 0 and k == 1
        for d, q, _ in bits:
            if edge: self.state[q] = rd(val.get(d))
            elif k == X and self.state[q] != rd(val.get(d)): self.state[q] = X
            yield q, (None if off == 1 else X if off == X else self.state[q])
        self.clk_last = k


class Latch75(Latch):
    def __init__(self, nl, ref):
        super().__init__(nl, ref); f = self.f
        b = lambda i: (f["D%d" % i], f["Q%d" % i], f["~{Q%d}" % i])
        self._setup([(f["C12"], 1, [b(1), b(2)]), (f["C34"], 1, [b(3), b(4)])])


# ---------------------------------------------------------------------------------------------- KiCad's 74xx symbols
def _and(v): return 0 if 0 in v else 1 if all(x == 1 for x in v) else X
def _or(v): return 1 if 1 in v else 0 if all(x == 0 for x in v) else X


class KGates(Model):
    """a package of gates drawn with KiCad's 74xx symbol, whose pins carry their numbers and no names. TABLES: the
    function and ((output pin, input pins), ...) of each type, from the TI data sheets' connection diagrams (SN7404 /
    SN7405 / SN7416: 1A 1Y 2A 2Y 3A 3Y GND 4Y 4A 5Y 5A 6Y 6A VCC; SN7408 / SN7432 / SN7486: 1A 1B 1Y 2A 2B 2Y GND 3Y 3A
    3B 4Y 4A 4B VCC; SN7410: 1A 1B 2A 2B 2C 2Y GND 3Y 3A 3B 3C 1Y 1C VCC; SN7420: 1A 1B NC 1C 1D 1Y GND 2Y 2A 2B NC 2C
    2D VCC). 'inv_oc' (7405, 7416): a high input pulls the output low, a low input lets it go (a pull-up makes the 1)."""
    _HEX = ((2, (1,)), (4, (3,)), (6, (5,)), (8, (9,)), (10, (11,)), (12, (13,)))
    _QUAD = ((3, (1, 2)), (6, (4, 5)), (8, (9, 10)), (11, (12, 13)))
    TABLES = {"k04": ("inv", _HEX), "k05": ("inv_oc", _HEX), "kand": ("and", _QUAD), "kor": ("or", _QUAD), "knand": ("nand", _QUAD),
              "kxor": ("xor", _QUAD), "knand3": ("nand", ((12, (1, 2, 13)), (6, (3, 4, 5)), (8, (9, 10, 11)))),
              "knand4": ("nand", ((6, (1, 2, 4, 5)), (8, (9, 10, 12, 13))))}

    def __init__(self, nl, ref, kind):
        super().__init__(nl, ref); self.op, table = self.TABLES[kind]
        self.gates = []
        for o, ins in table:
            out = self.n(o, str(o))
            if out: self.gates.append((out, [self.n(i, str(i)) for i in ins]))

    def outputs(self, val):
        op = self.op
        for o, ins in self.gates:
            v = [ttl(val.get(i)) for i in ins]
            if op == "and": r = _and(v)
            elif op == "or": r = _or(v)
            elif op == "nand": r = inv(_and(v))
            elif op == "xor": r = X if X in v else v[0] ^ v[1]
            elif op == "inv": r = inv(v[0])
            else: r = 0 if v[0] == 1 else None if v[0] == 0 else X      # inv_oc
            yield o, r

    def deps(self): return [(o, list(ins)) for o, ins in self.gates]


class KDFF74(DFF74):
    """the 74LS74 as KiCad's symbol names it: ~{R} (clear), D, C (clock), ~{S} (preset), Q, ~{Q}; the same pins"""
    NAMES = ("~{R}", "D", "C", "~{S}", "Q", "~{Q}")


class KComp85(Comp85):
    """the 74LS85 as KiCad's symbol names it: the cascade inputs Ia<b Ia=b Ia>b, the outputs Oa<b Oa=b Oa>b"""
    CI, CO = ("Ia<b", "Ia=b", "Ia>b"), ("Oa<b", "Oa=b", "Oa>b")


class KDec138(Dec138):
    """the 74LS138 as KiCad's symbol names it: A0 A1 A2, E3 (G1, active high), E1 E2 (G2A G2B, active low), O0-O7"""
    SEL, EN, OUT = ("A0", "A1", "A2"), ("E3", "E1", "E2"), "O%d"


class KLatch373(Latch):
    """the 74LS373 as KiCad's symbol names it: D0-D7, O0-O7, LE (transparent while high), OE (high = outputs off)"""
    def __init__(self, nl, ref):
        super().__init__(nl, ref); f = self.f
        self._setup([(f["LE"], 1, [(f["D%d" % i], f["O%d" % i], None) for i in range(8)])], off=f["OE"])


class KMux157(Model):
    """74LS157 quad 2-to-1 multiplexer (TI SN74LS157 function table: strobe high -> every output low; else select low
    -> the A input, high -> the B input), as KiCad's symbol names it: S, E (the strobe, active low), I0a-I0d (A), I1a-I1d
    (B), Za-Zd"""
    def __init__(self, nl, ref):
        super().__init__(nl, ref); f = self.f
        self.s, self.e = f["S"], f["E"]
        self.sect = [(f["Z" + k], f["I0" + k], f["I1" + k]) for k in "abcd" if "Z" + k in f]

    def outputs(self, val):
        s, e = ttl(val.get(self.s)), ttl(val.get(self.e))
        for z, i0, i1 in self.sect:
            a, b = ttl(val.get(i0)), ttl(val.get(i1))
            y = a if s == 0 else b if s == 1 else a if a == b else X
            yield z, 0 if e == 1 or y == 0 else y if e == 0 else X

    def deps(self): return [(z, [i0, i1, self.s, self.e]) for z, i0, i1 in self.sect]


# ---------------------------------------------------------------------------------------------- bus devices
class Device(Model):
    """a part that drives the bus data lines. access(val) -> ('r'|'w', address) | None | 'fault text'"""
    def outputs(self, val): return ()
    def controls(self): return []                                       # nets the bus-path trace starts from

    def _bits(self, val, nets):
        bits = [val.get(n) for n in nets]
        return None if X in bits or None in bits else sum(b << i for i, b in enumerate(bits))


class MemChip(Device):
    """62256 RAM (I/O0-7, CE, OE, WE) or 27256 EPROM (O0-7, CE, OE). A 28C256 EEPROM in a 27256 socket (Netlist.refit:
    pin 1 A14, pin 27 ~{WE}) is a ROM with a WE: it reads like the EPROM and takes a write at once (a real one is busy
    for up to 10 ms after it, which software finds by polling)"""
    def __init__(self, nl, ref, kind):
        super().__init__(nl, ref); f = self.f; self.kind = kind
        self.addr = [f["A%d" % i] for i in range(15)]
        self.data = [f[("I/O%d" if kind == "RAM" else "O%d") % i] for i in range(8)]
        self.ce = f["~{CE}"]; self.oe = f["~{OE}"]; self.we = f.get("~{WE}")

    def controls(self): return [self.ce, self.oe] + ([self.we] if self.we else []) + self.addr

    def access(self, val):
        ce, oe = val.get(self.ce), val.get(self.oe); we = val.get(self.we) if self.we else 1
        if X in (ce, oe, we) or None in (ce, oe, we): return "%s control undefined (CE=%s OE=%s WE=%s)" % (self.ref, ce, oe, we)
        if ce: return None
        op = "w" if not we else "r" if not oe else None
        if op is None: return None
        a = self._bits(val, self.addr)
        return "%s enabled with an undefined address" % self.ref if a is None else (op, a)


class ROM2732(Device):
    """2732 4K EPROM (O0-7, CE, OE/VPP) on the bus: the CPU card's boot ROM"""
    kind = "ROM"

    def __init__(self, nl, ref):
        super().__init__(nl, ref); f = self.f
        self.addr = [f["A%d" % i] for i in range(12)]; self.data = [f["O%d" % i] for i in range(8)]
        self.ce = f["~{CE}"]; self.oe = f["~{OE}/VPP"]; self.we = None

    def controls(self): return [self.ce, self.oe] + self.addr

    def access(self, val):
        ce, oe = val.get(self.ce), val.get(self.oe)
        if X in (ce, oe) or None in (ce, oe): return "%s control undefined (CE=%s OE=%s)" % (self.ref, ce, oe)
        if ce or oe: return None
        a = self._bits(val, self.addr)
        return "%s enabled with an undefined address" % self.ref if a is None else ("r", a)


class DualPort(Device):
    """IDT7134 4K x 8 dual-port RAM, right (bus) port"""
    kind = "DPRAM"

    def __init__(self, nl, ref):
        super().__init__(nl, ref); f = self.f
        self.addr = [f["A%dR" % i] for i in range(12)]; self.data = [f["I/O%dR" % i] for i in range(8)]
        self.ce = f["~{CER}"]; self.oe = f["~{OER}"]; self.rw = f["R/~{WR}"]

    def controls(self): return [self.ce, self.oe, self.rw] + self.addr

    def access(self, val):
        ce, oe, rw = (val.get(n) for n in (self.ce, self.oe, self.rw))
        if X in (ce, oe, rw) or None in (ce, oe, rw): return "%s control undefined (CER=%s OER=%s R/W=%s)" % (self.ref, ce, oe, rw)
        if ce: return None
        op = "w" if not rw else "r" if not oe else None
        if op is None: return None
        a = self._bits(val, self.addr)
        return "%s enabled with an undefined address" % self.ref if a is None else (op, a)


class CRTC(Device):
    """MC6845 CPU interface: selected while CS is low and E is high; R/W high = read; address = RS (0 = address
    register, 1 = the selected register)"""
    kind = "CRTC"

    def __init__(self, nl, ref):
        super().__init__(nl, ref); f = self.f
        self.data = [f["D%d" % i] for i in range(8)]; self.cs = f["CS"]; self.e = f["E"]; self.rw = f["R/~{W}"]; self.rs = f["RS"]
        self.addr = [self.rs]

    def controls(self): return [self.cs, self.e, self.rw, self.rs]

    def access(self, val):
        cs, e, rw, rs = (val.get(n) for n in (self.cs, self.e, self.rw, self.rs))
        if X in (cs, e) or None in (cs, e): return "%s CS/E undefined (CS=%s E=%s)" % (self.ref, cs, e)
        if cs or not e: return None
        if rw not in (0, 1) or rs not in (0, 1): return "%s selected with R/W=%s RS=%s" % (self.ref, rw, rs)
        return ("r" if rw else "w", rs)


class Port1852(Device):
    """CDP1852 8-bit I/O port in input mode (MODE low): drives DO0-7 while CS1 and CS2 are both high. Pin 1 is active
    high as Ken's k1_1852 symbol names it ('CS1', no bar); not yet checked against an RCA datasheet."""
    kind = "PORT"

    def __init__(self, nl, ref):
        super().__init__(nl, ref); f = self.f
        self.data = [f["DO%d" % i] for i in range(8)]; self.cs1 = f["CS1"]; self.cs2 = f["CS2"]; self.mode = f["MODE"]; self.addr = []

    def controls(self): return [self.cs1, self.cs2, self.mode]

    def access(self, val):
        cs1, cs2, mode = (val.get(n) for n in (self.cs1, self.cs2, self.mode))
        if mode != 0: return "%s is not in input mode (MODE=%s)" % (self.ref, mode)
        if X in (cs1, cs2) or None in (cs1, cs2): return "%s select undefined (CS1=%s CS2=%s)" % (self.ref, cs1, cs2)
        return ("r", 0) if cs1 == 1 and cs2 == 1 else None


class Pixie1861(Device):
    """CDP1861: on the bus it only listens (DMA data); the card drives DISPON / DISPOFF, read here"""
    kind = "PIXIE"

    def __init__(self, nl, ref):
        super().__init__(nl, ref); f = self.f
        self.data = []; self.on = f["DISPON"]; self.off = f["DISPOFF"]; self.addr = []

    def controls(self): return [self.on, self.off]

    def access(self, val):
        on, off = val.get(self.on), val.get(self.off)
        if X in (on, off) or None in (on, off): return "%s DISPON/DISPOFF undefined (%s, %s)" % (self.ref, on, off)
        if on and off: return "%s DISPON and DISPOFF both high" % self.ref
        return ("on", 0) if on else ("off", 0) if off else None


class BusConnector(Model):
    def __init__(self, nl, ref):
        super().__init__(nl, ref); self.sig = self.f                    # {'A0': net, 'TPA': net, '-VMA': net, 'D3': net, ...}
        if all(re.match(r"Pin_\d+$", k) for k in self.f):              # a stock connector symbol (CPU Rev D's 36-pin J1):
            self.sig = {}                                               # the signals by net name
            for (r, p), (net, _) in nl.pins.items():
                if r == ref: self.sig[net.split("/")[-1]] = net
    def outputs(self, val): return ()


# CPU Rev D (2026-10-30) is generated, not converted from Eagle: its parts carry KiCad stock names (Device:R, the
# 36-pin bus as Conn_01x36) and project symbols named by type (74HCT00 ...), with the 2005 symbols' pin names
REV_D_PASSIVE = ("R", "C", "C_Polarized", "LED", "SW_SPDT", "Conn_01x02", "Conn_01x03", "Conn_01x06",
                 "Conn_02x03_Odd_Even", "Conn_02x04_Odd_Even", "Conn_02x07_Odd_Even", "OSC_DIP8", "DS1813", "SW_Push",
                 "TIL311", "Crystal", "Battery_Cell",      # TIL311: the IO panel's displays; jumper blocks: fitted as shorts
                 "Conn_02x25_Odd_Even", "MountingHole", "R_Pack08",   # the front panel's ribbon header (the front
                 # panel's own Circuit names it as its bus: bus="J1"), its holes, the LEDs' isolated resistors
                 "MAX232", "DE9_Socket_MountingHoles",     # the IO panel's serial line (2026-11-20): outside the logic.
                 "Polyfuse", "RCA", "DE9_SHIELD", "MINIDIN6", "Conn_02x20_Odd_Even", "Conn_01x30")   # VIDEO-G: jacks, the
#                ribbon's headers (hwvideog.py joins the two boards' netlists pin for pin) and GFX's own bus connector
#                (Its 16550 and its DS12885 are "unmodelled" here: hw.NetlistIOPanel plays them on the pins the gates drive.)


def classify(lib):
    if lib == "D_Schottky": return "diode"
    m = re.match(r"74HCT?(\d+)$", lib)                                 # CPU Rev D, the IO panel (74HCTxx, 74HC05)
    if m:
        return {"00": "nand", "02": "02", "03": "nand03", "05": "05", "10": "nand3", "14": "04", "20": "nand4", "74": "74", "373": "373",
                "573": "373", "374": "374", "138": "138"}.get(m.group(1), "unmodelled")   # 573: the 373's latch, pins by name
    m = re.match(r"74LS(\d+)$", lib)                                   # KiCad's own 74xx symbols (VIDEO-G)
    if m:
        return {"00": "knand", "04": "k04", "05": "k05", "08": "kand", "32": "kor", "86": "kxor", "10": "knand3", "20": "knand4",
                "74": "k74", "85": "k85", "138": "k138", "157": "k157", "373": "k373"}.get(m.group(1), "unmodelled")
    if lib == "Conn_01x36": return "bus"
    if lib.startswith("R_Network"): return "pull"
    if lib in REV_D_PASSIVE: return None
    m = re.search(r"74x(\d+)", lib)
    if m:
        return {"151": "151", "32": "or", "00": "nand", "02": "02", "04": "04", "05": "05", "74": "74", "85": "85",
                "138": "138", "373": "373", "374": "374", "75": "75"}.get(m.group(1), "unmodelled")
    if "4042" in lib: return "4042"
    if "4050" in lib: return "4050"
    if "58C256" in lib or "62256" in lib: return "RAM"
    if "27256" in lib: return "ROM"
    if "2732" in lib: return "ROM2732"
    if "7134" in lib: return "DPRAM"
    if "6845" in lib: return "CRTC"
    if "1852" in lib: return "PORT"
    if "1861" in lib: return "PIXIE"
    if "G09R" in lib or "RNX4" in lib: return "pull"
    if "C30" in lib or "C36" in lib: return "bus"                      # (C36: the 6845 card Rev B-Clean-Keyboard's)
    if any(p in lib for p in PASSIVE): return None
    return "unmodelled"


@contextlib.contextmanager
def powering_up(state):
    """every Circuit made inside starts with its flip-flops and latches at `state` (Circuit's power_up)"""
    was, Circuit.POWER_UP = Circuit.POWER_UP, state
    try: yield
    finally: Circuit.POWER_UP = was


class Circuit:
    """the active parts of one card. `fitted` = the refs actually in their sockets (None = all); an empty socket's
    pins float. drive(signal=value, ...) sets the bus connector's pins; settle() returns {net: value}."""
    POWER = {"VCC": 1, "+5V": 1, "GND": 0}
    LOGIC = {"or": lambda nl, r: Quad(nl, r, "or"), "nand": lambda nl, r: Quad(nl, r, "nand"), "02": Nor02, "04": Hex04, "05": Hex05, "74": DFF74, "85": Comp85,
             "nand3": Nand3, "nand4": Nand4, "nand03": Nand03, "138": Dec138, "151": Mux151, "373": Latch373, "374": Reg374, "75": Latch75, "4042": Latch4042, "4050": Buffer4050,
             "k74": KDFF74, "k85": KComp85, "k138": KDec138, "k157": KMux157, "k373": KLatch373}
    LOGIC.update({k: (lambda nl, r, k=k: KGates(nl, r, k)) for k in KGates.TABLES})

    POWER_UP = None                                                     # what power_up is when it is not given

    def __init__(self, nl, fitted=None, controls=(), external=None, bus=None, power_up=None):
        """controls: more nets the bus-path check starts from (e.g. a drive's strobes on a header).
        external: {ref: reason} for parts the emulator plays itself (the 1802, the reset chip): their outputs may feed
        the bus path; the nets they drive are set with drive().
        bus: the reference of the connector drive() sets, for a board whose "bus" is a cable header (the front panel's
        J1, the ribbon from the IO panel card); None = the System-5 bus connector, found by its symbol.
        power_up: the state every flip-flop and latch comes up in: 0, 1, or "seed N" (each its own, reproducibly). It is put
        there once the first settle() has ended, wherever the part's own clear, preset or enable does not hold it, and the
        circuit settles again. (The first settle begins from no net values, which a TTL input reads as 1, so an inverter
        gives a 0 for a pass and a clear fed by it can clear a flip-flop before anything has happened: the ELF II session's
        finding, 2026-11-25, and true here.) None, as until 2026-11-25: whatever the first settle leaves, mostly unknown."""
        self.power_up = Circuit.POWER_UP if power_up is None else power_up; self._started = False
        self.nl = nl; self.extra_controls = list(controls); self.external = dict(external or {}); self.models = []; self.mem = []; self.empty = []; self.unmodelled = []; self.pulls = {}; self.bus = None
        for ref, part in nl.parts.items():
            if ref == bus or (bus is None and classify(part.lib) == "bus"): self.bus = BusConnector(nl, ref)
        diodes = []
        for ref, part in sorted(nl.parts.items()):
            kind = classify(part.lib)
            if ref == bus: continue
            if kind is None:
                if "R-US" in part.lib or part.lib == "R": self._resistor(ref)
                continue
            if kind == "bus": continue
            if ref in self.external: continue
            if kind == "pull": self._pull(ref); continue
            if kind == "diode": diodes.append(ref); continue
            if fitted is not None and ref not in fitted: self.empty.append(ref); continue
            if kind == "unmodelled": self.unmodelled.append(ref)
            elif kind in ("RAM", "ROM"): self.mem.append(MemChip(nl, ref, kind))
            elif kind == "DPRAM": self.mem.append(DualPort(nl, ref))
            elif kind == "ROM2732":
                d = ROM2732(nl, ref); bus_d = {self.bus.sig["D%d" % i] for i in range(8)} if self.bus else set()
                if self.bus and set(d.data) <= bus_d: self.mem.append(d)
                else: self.unmodelled.append(ref)                       # e.g. the 6845 card's character ROM
            elif kind == "CRTC": self.mem.append(CRTC(nl, ref))
            elif kind == "PORT": self.mem.append(Port1852(nl, ref))
            elif kind == "PIXIE": self.mem.append(Pixie1861(nl, ref))
            else: self.models.append(self.LOGIC[kind](nl, ref))
        for ref in diodes:                                              # once every resistor is known
            if self.pulls.get(nl.net(ref, "2")) == 1: self.models.append(WiredDiode(nl, ref))
        if self.bus is None: raise ValueError("no System-5 bus connector (C30) in " + nl.path)
        self.ext = {}; self.forced = {}; self.val = {}; self.fights = {}
        self.cone = self._check_bus_path()

    def _resistor(self, ref):
        """a resistor with one end on a supply is a weak pull of the net at its other end"""
        pins = [(p, net) for (r, p), (net, _) in self.nl.pins.items() if r == ref]
        if len(pins) != 2: return
        (_, a), (_, b) = pins
        if a in self.POWER and b not in self.POWER: self.pulls.setdefault(b, self.POWER[a])
        elif b in self.POWER and a not in self.POWER: self.pulls.setdefault(a, self.POWER[b])

    def _pull(self, ref):
        common = self.nl.net(ref, "1")
        if common not in self.POWER: return
        for (r, p), (net, _) in self.nl.pins.items():
            if r == ref and p != "1" and not net.startswith("unconnected"): self.pulls[net] = self.POWER[common]

    def _check_bus_path(self):
        """every net that can change a bus device's control or address pin must be driven only by modelled logic,
        the bus connector, a supply or a pull-up. -> the set of those nets"""
        drivers = {}
        for m in self.models:
            for out, ins in m.deps(): drivers.setdefault(out, []).append(ins)
        data = {n for d in self.mem for n in d.data}
        todo = [n for d in self.mem for n in d.controls()] + self.extra_controls; seen = set()
        while todo:
            net = todo.pop()
            if net in seen: continue
            seen.add(net)
            for ins in drivers.get(net, []): todo.extend(ins)
        bad = []
        for (ref, pin), (net, fn) in self.nl.pins.items():
            if net not in seen or net in self.POWER: continue
            if ref in self.external: continue
            if ref in self.unmodelled and self.nl.pintype.get((ref, pin)) in DRIVING:
                bad.append("%s.%s (%s, unmodelled %s)" % (ref, pin, fn, self.nl.parts[ref].value))
            if any(d.ref == ref for d in self.mem) and net not in data and self.nl.pintype.get((ref, pin)) in DRIVING:
                bad.append("%s.%s (%s, a bus device's own output)" % (ref, pin, fn))
        if bad: raise ValueError("%s: the bus path reaches parts with no model: %s" % (self.nl.path, "; ".join(sorted(bad))))
        return seen

    def drives_low(self, net):
        """True while this card itself holds `net` low: a gate's output or a forced part (a switch), not what drive()
        put on the bus pins. For the open-collector bus lines, where the level alone does not say who pulls. An output
        that is neither pulling nor let go (it depends on something undefined) raises: until 2026-11-25 it read as let go,
        which hid that the IO panel's -DMAIN came up unknown"""
        if any(n == net and v == 0 for n, (_, v) in self.forced.items()): return True
        out = [v for m in self.models for n, v in m.outputs(self.val) if n == net]
        if 0 not in out and X in out: raise ValueError("%s: %s is neither pulled nor let go" % (self.nl.path, net))
        return 0 in out

    def drive(self, **sig):
        """bus pins by name: A=byte (A0-A7), N=0-7 (N0-N2), TPA, TPB, MRD, MRW, VMA (the active-low ones by their plain
        name), or a pin's own name ("-PAUSE", "SC0", "ADR7"). A value of None lets the pin go (an open-collector line
        that no other card pulls: the card's own pull-up, if it has one, then sets it)"""
        s = self.bus.sig
        for k, v in sig.items():
            if k in ("A", "D"):                                         # D=None: nothing drives the data lines
                for i in range(8):
                    if k == "D" and v is None: self.ext.pop(s["D%d" % i], None)
                    else: self.ext[s["%s%d" % (k, i)]] = (v >> i) & 1
            elif k == "N":
                for i in range(3):
                    if "N%d" % i in s: self.ext[s["N%d" % i]] = (v >> i) & 1
            else:
                name = {"MRD": "-MRD", "MRW": "-MRW", "VMA": "-VMA", "RESET": "-RESET"}.get(k, k)
                if name in s: self.ext[s[name]] = v

    def settle(self, limit=50):
        if not self._started:
            self._started = True; self._settle(limit)
            if self.power_up is not None: self._come_up(limit)
            return self.val
        return self._settle(limit)

    def _come_up(self, limit):
        """the flip-flops and latches in their power_up states (see __init__)"""
        rnd = random.Random(str(self.power_up)) if not isinstance(self.power_up, int) else None
        want = {}
        pick = lambda key: want.setdefault(key, rnd.getrandbits(1) if rnd else self.power_up)
        for _ in range(8):
            moved = False
            for n, m in enumerate(self.models):
                if isinstance(m, DFF74): free = [(i, i) for i, ff in enumerate(m.ff) if ttl(self.val.get(ff[0])) != 0 and ttl(self.val.get(ff[3])) != 0]
                elif isinstance(m, Reg374): free = [(q, q) for _, _, bits in m.groups for _, q, _ in bits]
                elif isinstance(m, Latch): free = [(q, q) for en, level, bits in m.groups if m.rd(self.val.get(en)) != level for _, q, _ in bits]
                else: continue
                for key, k in free:
                    v = pick((n, key))
                    if m.state[k] != v: m.state[k] = v; moved = True
            if not moved: return
            self._settle(limit)

    def _settle(self, limit=50):
        val = self.val
        for _ in range(limit):
            drv = {}
            for net, v in self.ext.items(): drv.setdefault(net, []).append(("bus", v))
            for net, (who, v) in self.forced.items(): drv.setdefault(net, []).append((who, v))
            for m in self.models:
                for net, v in m.outputs(val): drv.setdefault(net, []).append((m.ref, v))
            new = {}; fights = {}
            for net, ds in drv.items():
                vs = {v for _, v in ds if v is not None}
                if net in self.POWER: vs.add(self.POWER[net])
                if len(vs) > 1: fights[net] = ds                       # two drivers disagree (or one is unknown)
                new[net] = next(iter(vs)) if len(vs) == 1 else None if not vs else X
            for net, v in self.POWER.items(): new.setdefault(net, v)
            for net, v in self.pulls.items():
                if new.get(net) is None: new[net] = v
            if new == val: self.val = val; self.fights = fights; return val
            val = new
            if _ == 20: return self._settle_one_by_one(val, limit)
        raise RuntimeError("%s: logic did not settle in %d passes (oscillating?)" % (self.nl.path, limit))

    def _settle_one_by_one(self, val, limit):
        """Updating every gate at once can make a symmetric NAND latch flip forever (both outputs 1, then both 0...).
        Real gates are never equally fast: the latch falls into one state. So, after 20 simultaneous passes, update
        one model at a time, each seeing the outputs of the ones before it."""
        val = dict(val); contrib = {}
        for net, v in self.ext.items(): contrib.setdefault(net, {})["bus"] = v
        for net, (who, v) in self.forced.items(): contrib.setdefault(net, {})[who] = v

        def resolve(net):
            vs = {v for v in contrib.get(net, {}).values() if v is not None}
            if net in self.POWER: vs.add(self.POWER[net])
            r = next(iter(vs)) if len(vs) == 1 else None if not vs else X
            return self.pulls.get(net) if r is None and net in self.pulls else r
        for _ in range(limit):
            changed = False
            for m in self.models:
                for net, v in m.outputs(val):                 # a generator: each gate sees the gates before it
                    contrib.setdefault(net, {})[m.ref] = v; r = resolve(net)
                    if val.get(net) != r: val[net] = r; changed = True
            if not changed:
                self.val = val; self.fights = {n: [(w, v) for w, v in d.items()] for n, d in contrib.items()
                                               if len({v for v in d.values() if v is not None}) > 1}
                return val
        raise RuntimeError("%s: logic did not settle, even one gate at a time (a real oscillator?)" % self.nl.path)
