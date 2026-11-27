# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-25
"""Cards and a program on the bus board's own netlist (the bus Rev D backplane, hardware/bus/kicad/rev-d).

backplane.py and s5emu's HWMachine carry a bus line from card to card by its NAME, and have the backplane's resistors
typed in, so neither sees how the bus board is wired. Here the board is read from the netlist KiCad wrote for it
(reports/netlist.net; not from gen/netlist.py, which made it) and five cards are plugged into its sockets: each card's
connector pin is joined to the socket pin it stands on, and nothing is joined by name. What reaches a card is what the
board's copper carries to its slot.

  The cards     CPU Rev D, memory Rev E, the 6845 card Rev B-Clean-Keyboard, the IO panel Rev A and IDE/CF Rev A, each
                from its own netlist, in any slots. System() makes one circuit of the board and the cards.
  On the gates  every chip logic.py has a model for, the bus board's and the cards' resistors, and two more models
                here (the '244s and the key latch). All in one circuit: the byte an OUT sends goes from the RAM's pins
                over the board to the IO panel's latch, and not through the emulator.
  Played        the 1802 (cpupins.Pins1802: its pins, clock edge by clock edge), the memories' cells, the dual-port RAM's
                bus port, the 6845's registers, the DS12885, the 16C550, the ATmega328P and the drive on the IDE header,
                each on the levels its pins have.
  Unknown is    a net with no driver and no resistor is X here (in logic.py it is a 1 to a TTL input). So is a net with
  not a 1       a pull-up and a pull-down, or with two outputs that disagree.
  Power         the board's +5V is taken to be on; power_path() follows it from the two inputs. A card whose +5V or GND
                does not reach the board's is not powered: it does nothing. A board with +5V on GND runs nothing.

The program (bus_program.asm, in the CPU card's EPROM) uses every line of the bus; then the IO panel's LOAD mode loads a
second one by DMA, RUN runs it from RAM, and its RESET button boots the EPROM again. Every machine cycle is compared, as
it ends, with what the instruction-level machine (s5emu/machine.py, Video6845KbdMachine with the IO panel) did with the
same program: same kind of cycle, same address, same byte. That machine has no board and no slots: it is here the
statement of what the program must do. run() stops at the first difference (Noticed).

Limits: no time (a 10k against 4.7k is the same here; a resistor's value is not looked at), no analogue levels, no
capacitors (a bypass capacitor missing cannot show), no latch-up or phantom supply of an unpowered card. VIDEO-G and
BUSDRV-C are not fitted. test_busboard.py says which faults in the board this notices, and which it cannot.
"""
import datetime, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "s5emu"))
from s5emu import hw                                                         # noqa: E402
from s5emu.logic import Circuit, Latch, MemChip, WiredDiode, Model, ROM2732, DualPort, CRTC, X, classify, inv, ttl   # noqa: E402
from s5emu.machine import IDE, Keyboard, Video6845, Video6845KbdMachine      # noqa: E402
from s5emu.netlist import Netlist                                            # noqa: E402
from s5emu.rtc import DS12885                                                # noqa: E402
from s5emu.uart import UART16550                                             # noqa: E402
from cpupins import Pins1802                                                 # noqa: E402

ROOT = hw.ROOT
BUS_NET = "hardware/bus/kicad/rev-d/reports/netlist.net"
SLOTS = ["J%d" % k for k in range(1, 9)]
# which socket position (1 = the GND end) each connector's pad stands on. A 30-pin card ends flush with the GND end and
# its pad 1 is +5V (docs/manual/bus.md, "Mechanics"); the generated 36-pin cards number their pads by position; the 6845
# card keeps Rev B's numbers for pads 1-30. test_busboard.Geometry measures it on each board's pads.
POS30 = lambda n: 31 - n
POS36 = lambda n: n
POS30_6 = lambda n: 31 - n if n <= 30 else n
CARDS = {           # name: (its board's folder, its bus connector, pad -> socket position)
    "cpu":   ("hardware/cpu/kicad/rev-d", "J1", POS36),
    "mem":   ("hardware/memory/kicad/rev-e", "U$1", POS30),
    "video": ("hardware/video-6845/kicad/rev-b-clean-keyboard", "J1", POS30_6),
    "panel": ("hardware/io-panel/kicad/rev-a", "J1", POS36),
    "ide":   ("hardware/ide-cf/kicad/rev-a", "U$1", POS30),
}
ORDER = ("cpu", "mem", "video", "panel", "ide")
# the four ways the flag lines' jumpers are set (INPUT's line, the keyboard's), so that each of the four flag lines
# carries each of the two. The CPU card brings INPUT's to EF1, the keyboard's to EF3, the other two to EF2 and EF4
FLAGS = {"A": ("-EF1", "-EF"), "B": ("-EF2", "-EF3"), "C": ("-EF3", "-EF2"), "D": ("-EF", "-EF1")}
MEM_JUMPERS = "RRRRRRR-EEEEEEE-"
TOGGLES = 0xA6
RAM_PROGRAM = bytes([0xE0, 0x64, 0xC3, 0x7B, 0x30, 0x04])    # SEX 0; OUT 4,C3; SEQ; BR 4: toggled in, run from RAM
UART_IN = b"r"
KEYS = [0x41, 0xB5]                                          # two key codes, every bit both ways


class Noticed(Exception):
    """the first thing that is not as it should be"""


# ============================================================================================== the netlists, joined
def bus_netlist(): return Netlist(os.path.join(ROOT, BUS_NET))


# the IO panel as it was drawn until 2026-11-25, for the tests that must notice it: REQ cleared by ACK alone, DRIVE not
# gated with LOAD mode. {card: [netlist edits]}, made on a card's netlist before its jumpers
AS_DRAWN = {"panel": [("lift", "U10", "1"), ("wire", "U10", "1", "U10", "8"), ("lift", "U6", "2"), ("wire", "U6", "2", "U11", "6")]}
REWORK = {}


def card_netlist(name, flags="A"):
    """a card's netlist with its jumpers fitted as the test's machine has them (and REWORK's edits for it)"""
    folder, _, _ = CARDS[name]; nl = Netlist(os.path.join(ROOT, folder, "reports", "netlist.net"))
    for op, *a in REWORK.get(name, ()): getattr(nl, op)(*a)
    inp, key = FLAGS[flags]; rows = ("-EF1", "-EF2", "-EF3", "-EF")
    row = lambda ref, k: nl.jumper(ref, str(2 * k - 1), ref, str(2 * k))
    if name == "cpu":                                                                          # EF1 = INPUT, EF3 = the key
        rest = [r for r in rows if r not in (inp, key)]
        for ref, line in zip(("JP2", "JP4", "JP3", "JP5"), (inp, key, rest[0], rest[1])): row(ref, rows.index(line) + 1)
    elif name == "panel":
        row("JP1", 4); row("JP2", 4); row("JP3", rows.index(inp) + 1); row("JP4", 3); row("JP4", 6)   # ports 4; 6 / 7
        nl.jumper("JP7", "2", "JP7", "1")                                                       # UART INT on -INT
    elif name == "video": nl.jumper("SV1", "1", "SV1", "2"); row("JP1", rows.index(key) + 1)    # block 7
    elif name == "ide":
        for op, *a in hw.IDE_REVS["A"]["rework"]: getattr(nl, op)(*a)                          # ports 2 and 3
    elif name == "mem":
        for net in _mem_card().c.forced: nl.short("GND", net)                                  # the block jumpers
    return nl


_MEM = []
def _mem_card():
    """the emulator's memory Rev D (Rev E's circuit: the two netlists are the same, pin for pin, which is checked),
    for its jumper finder and its EPROM programmer"""
    if not _MEM:
        c = hw.NetlistMemoryCard("D", MEM_JUMPERS)
        e = Netlist(os.path.join(ROOT, CARDS["mem"][0], "reports", "netlist.net"))
        if c.nl.pins != e.pins: raise ValueError("memory Rev E's netlist is not Rev D's: the jumpers must be found again")
        _MEM.append(c)
    return _MEM[0]


class Joined:
    """the bus board and the cards in their slots as one netlist (what logic.py's models need of a Netlist): refs and
    nets under "bus." or the card's name; the nets a slot joins are one net. Only +5V and GND of the BOARD are supplies:
    a card's are, if its pins bring it to them."""
    def __init__(self, bus, slots, cards):
        """slots: {card name: socket ref}; cards: {card name: Netlist}"""
        self.path = "bus + " + ", ".join(cards); self.parts, self.pins, self.pintype, self.edits = {}, {}, {}, []
        parent = {}

        def find(x):
            parent.setdefault(x, x)
            while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
            return x
        self._raw = {}
        for name, nl in [("bus", bus)] + list(cards.items()):
            for ref, p in nl.parts.items(): self.parts[name + "." + ref] = p._replace(ref=name + "." + ref)
            for (ref, pin), (net, fn) in nl.pins.items():
                self._raw[(name + "." + ref, pin)] = (name + "." + net, fn)
                self.pintype[(name + "." + ref, pin)] = nl.pintype.get((ref, pin), "")
        self.conn = {}                                                # (card, pad) -> (socket ref, position)
        for name, nl in cards.items():
            _, jref, where = CARDS[name]
            for (ref, pin) in nl.pins:
                if ref != jref: continue
                at = (slots[name], str(where(int(pin))))
                self.conn[(name, int(pin))] = at
                parent[find(name + "." + nl.net(ref, pin))] = find("bus." + bus.net(*at))
        v, g = find("bus.+5V"), find("bus.GND")
        if v == g: raise Noticed("+5V and GND are one net: nothing runs")
        label = {v: "VCC", g: "GND"}; named = {}
        for net in {n for n, _ in self._raw.values()}:
            root = find(net); named.setdefault(root, []).append(net)
        for root, names in named.items():                            # a board net's own name first, else the card's
            label.setdefault(root, sorted(names, key=lambda n: (not n.startswith("bus."), n))[0])
        for key, (net, fn) in self._raw.items(): self.pins[key] = (label[find(net)], fn)
        self.unpowered = [name for name, nl in cards.items()
                          if any(label[find(name + "." + s)] != want for s, want in
                                 (("VCC" if "VCC" in nl.nets else "+5V", "VCC"), ("GND", "GND")))]
        self._by_ref = {}
        for (ref, pin), (net, fn) in self.pins.items(): self._by_ref.setdefault(ref, {})[fn] = net

    def net(self, ref, pin): return self.pins[(ref, str(pin))][0]
    def function(self, ref, pin): return self.pins[(ref, str(pin))][1]
    def part_pins(self, ref): return self._by_ref.get(ref, {})

    @property
    def nets(self):
        out = {}
        for key, (net, _) in self.pins.items(): out.setdefault(net, []).append(key)
        return out

    def partition(self):
        """the joined circuit without the sockets and the cards' connectors: which of the other pins are one net. Two boards with the same
        partition are the same circuit, whatever slots the cards are in"""
        groups = {}
        for (ref, pin), (net, _) in self.pins.items():
            card, _, r = ref.partition(".")
            if not (ref.startswith("bus.J") or (card in CARDS and r == CARDS[card][1])): groups.setdefault(net, []).append((ref, pin))
        return frozenset(frozenset(g) for g in groups.values()), tuple(sorted(self.unpowered))


# ============================================================================================== models
class Buf244(Model):
    """74HCT244: two halves of four buffers, each with its enable (low = on). Pins by number (TI SN74HCT244)"""
    HALVES = (("1", (("2", "18"), ("4", "16"), ("6", "14"), ("8", "12"))), ("19", (("11", "9"), ("13", "7"), ("15", "5"), ("17", "3"))))

    def __init__(self, nl, ref):
        super().__init__(nl, ref)
        self.h = [(nl.net(ref, e), [(nl.net(ref, a), nl.net(ref, y)) for a, y in ab]) for e, ab in self.HALVES]

    def outputs(self, val):
        for e, ab in self.h:
            en = ttl(val.get(e))
            for a, y in ab: yield y, None if en == 1 else X if en == X else ttl(val.get(a))


class Key374(Latch):
    """the 74HCT374 as KiCad's symbol names it (Cp, OE, D0-D7, O0-O7)"""
    def __init__(self, nl, ref):
        super().__init__(nl, ref); f = self.f; self.clk, self.off = f["Cp"], f["OE"]
        self.bits = [(f["D%d" % i], f["O%d" % i]) for i in range(8)]; self.state = {q: X for _, q in self.bits}; self.last = None

    def outputs(self, val):
        k, off = ttl(val.get(self.clk)), ttl(val.get(self.off))
        for d, q in self.bits:
            if self.last == 0 and k == 1: self.state[q] = ttl(val.get(d))
            yield q, None if off == 1 else X if off == X else self.state[q]
        self.last = k


class Dev:
    """a played part: outputs(val) -> (net, level); after(val) looks at its pins once the circuit has settled"""
    def __init__(self, sys_, ref, nets): self.s, self.ref, self.listen, self.hold = sys_, ref, set(nets), None
    def outputs(self, val): return ()
    def after(self, val): pass

    def byte(self, val, nets):
        b = [val.get(n) for n in nets]
        return None if any(x not in (0, 1) for x in b) else sum(x << i for i, x in enumerate(b))


class Chip(Dev):
    """a memory or the 6845's bus side, on logic.py's own reading of its pins (access()). A byte is written when the
    strobe ends, as it was on the bus while the strobe was on"""
    def __init__(self, sys_, d, rd, wr):
        super().__init__(sys_, d.ref, list(d.controls()) + list(d.data)); self.d, self.rd, self.wr = d, rd, wr; self.pend = None

    def outputs(self, val):
        r = self.d.access(val)
        if isinstance(r, str): v = [X] * 8 if self.on_the_bus(val) else [None] * 8
        elif r and r[0] == "r":
            b = self.rd(r[1]); v = [(b >> i) & 1 for i in range(8)]
        else: v = [None] * 8
        return zip(self.d.data, v)

    def on_the_bus(self, val):
        """a chip whose pins are undefined drives nothing for certain only while its select or its enable is off"""
        d = self.d
        if hasattr(d, "e"): return val.get(d.cs) != 1 and val.get(d.e) != 0 and val.get(d.rw) != 0        # the 6845
        return val.get(d.ce) != 1 and val.get(d.oe) != 1

    def after(self, val):
        r = self.d.access(val)
        if isinstance(r, str):
            if (val.get(self.d.cs) != 1 and val.get(self.d.e) != 0) if hasattr(self.d, "e") else val.get(self.d.ce) != 1: self.s.event("undefined: " + r)
        if isinstance(r, tuple) and r[0] == "w":
            a, b = r[1], self.byte(val, self.d.data)
            if self.pend and self.pend[0] != a: self.s.event("%s: its address changes while it is written" % self.ref)
            self.pend = (a, b)
        elif self.pend:
            a, b = self.pend; self.pend = None
            if b is None: self.s.event("%s: an undefined byte is written" % self.ref); b = 0
            if self.wr: self.wr(a, b)


class RTC(Dev):
    """the DS12885 (U13): AS latches the register number, R/W's rise writes, DS low reads; CS low selects"""
    def __init__(self, sys_, ref, chip):
        n = lambda p: sys_.nl.net(ref, p); self.chip = chip
        self.d = [n(p) for p in range(4, 12)]; self.cs, self.as_, self.wr, self.ds = n(13), n(14), n(15), n(17)
        super().__init__(sys_, ref, self.d + [self.cs, self.as_, self.wr, self.ds]); self.la = self.lw = None; self.da = self.dw = None

    def outputs(self, val):
        ds, cs = val.get(self.ds), val.get(self.cs)
        if ds == 1 or cs == 1: self.hold = None; return [(n, None) for n in self.d]
        if ds != 0 or cs != 0: return [(n, X) for n in self.d]
        if self.hold is None: self.hold = self.chip.read_data()
        return [(n, self.hold >> i & 1) for i, n in enumerate(self.d)]

    def after(self, val):
        a, w = val.get(self.as_), val.get(self.wr)
        if a == 1: self.da = self.byte(val, self.d)
        if w == 0: self.dw = self.byte(val, self.d)
        if self.la == 1 and a == 0:
            if self.da is None: self.s.event("DS12885: an undefined register number")
            else: self.chip.write_addr(self.da)
        if self.lw == 0 and w == 1 and val.get(self.cs) == 0:
            if self.dw is None: self.s.event("DS12885: an undefined byte is written")
            else: self.chip.write_data(self.dw)
        for x, what in ((a, "AS"), (w, "R/W"), (val.get(self.ds), "DS")):
            if x not in (0, 1): self.s.event("DS12885: %s is undefined" % what)
        self.la, self.lw = a, w


class UART(Dev):
    """the 16C550 (U20): CS0, A0-A2, WR (falls: the byte is written), -RD low (reads), MR, INTR"""
    def __init__(self, sys_, ref, chip):
        n = lambda p: sys_.nl.net(ref, p); self.chip = chip
        self.d = [n(p) for p in range(1, 9)]; self.cs, self.wr, self.rd, self.mr, self.intr = n(12), n(19), n(21), n(35), n(30)
        self.a = [n(28), n(27), n(26)]
        super().__init__(sys_, ref, self.d + self.a + [self.cs, self.wr, self.rd, self.mr]); self.lw = None; self.dw = None; self.lm = None

    def outputs(self, val):
        rd, cs = val.get(self.rd), val.get(self.cs)
        out = [(self.intr, 1 if self.chip.intr() else 0)]
        if rd == 1 or cs == 0: self.hold = None; return out + [(n, None) for n in self.d]
        a = self.byte(val, self.a)
        if rd != 0 or cs != 1 or a is None: return out + [(n, X) for n in self.d]
        if self.hold is None: self.hold = self.chip.read(a); out[0] = (self.intr, 1 if self.chip.intr() else 0)
        return out + [(n, self.hold >> i & 1) for i, n in enumerate(self.d)]

    def after(self, val):
        w, m = val.get(self.wr), val.get(self.mr)
        if w == 1: self.dw = (self.byte(val, self.a), self.byte(val, self.d))
        if self.lw == 1 and w == 0 and val.get(self.cs) == 1:
            if None in self.dw: self.s.event("16C550: an undefined register or byte is written")
            else: self.chip.write(*self.dw); self.s.kick(self)
        if m == 1 and self.lm != 1: self.chip.reset(); self.s.kick(self)
        for x, what in ((w, "WR"), (m, "MR"), (val.get(self.rd), "-RD")):
            if x not in (0, 1): self.s.event("16C550: %s is undefined" % what)
        self.lw, self.lm = w, m


class Drive(Dev):
    """the drive on the IDE card's header: DIOR low reads a register, DIOW's rise writes one; its RESET (pin 1)"""
    def __init__(self, sys_, ref, chip):
        pin = {v: k for k, v in hw.ATA_PINS.items()}; n = lambda k: sys_.nl.net(ref, pin[k]); self.chip = chip
        self.d = [n("DD%d" % i) for i in range(8)]; self.c = [n(k) for k in ("DA0", "DA1", "DA2", "CS0", "CS1")]
        self.rd, self.wr, self.rst = n("DIOR"), n("DIOW"), sys_.nl.net(ref, 1)
        super().__init__(sys_, ref, self.d + self.c + [self.rd, self.wr, self.rst]); self.lw = None; self.pend = None

    def reg(self, val):
        c = [val.get(n) for n in self.c]
        if any(x not in (0, 1) for x in c) or c[3] == c[4]: return None
        return (8 if c[3] else 0) + (c[0] | c[1] << 1 | c[2] << 2)

    def outputs(self, val):
        rd = val.get(self.rd)
        if rd == 1: self.hold = None; return [(n, None) for n in self.d]
        r = self.reg(val)
        if rd != 0 or r is None: return [(n, X) for n in self.d]
        if self.hold is None: self.chip.sel = r; self.hold = self.chip.inp(3)
        return [(n, self.hold >> i & 1) for i, n in enumerate(self.d)]

    def after(self, val):
        w = val.get(self.wr)
        if w == 0: self.pend = (self.reg(val), self.byte(val, self.d))
        if self.lw == 0 and w == 1 and self.pend:
            r, b = self.pend; self.pend = None
            if r is None or b is None: self.s.event("the drive: an undefined register or byte is written")
            else: self.chip.sel = r; self.chip.out(3, b)
        for x, what in ((w, "DIOW"), (val.get(self.rd), "DIOR"), (val.get(self.rst), "RESET")):
            if x not in (0, 1): self.s.event("the drive: %s is undefined" % what)
        self.lw = w


class ATmega(Dev):
    """the keyboard's ATmega328P (IC21): a key waits and KEY-READY has been low for a machine cycle (its firmware polls):
    the code on MD0-MD7, then LDDATA up and down"""
    MD = ("23", "24", "25", "26", "27", "28", "14", "15")

    def __init__(self, sys_, ref, kbd):
        n = lambda p: sys_.nl.net(ref, p); self.kbd = kbd; self.md = [n(p) for p in self.MD]; self.ld, self.ready, self.rst = n(12), n(16), n(1)
        super().__init__(sys_, ref, [self.ready, self.rst]); self.code = 0; self.level = 0; self.low_at = None

    def outputs(self, val): return [(n, self.code >> i & 1) for i, n in enumerate(self.md)] + [(self.ld, self.level)]

    def after(self, val):
        if self.level: self.level = 0; self.s.kick(self); return
        if val.get(self.rst) != 1 or val.get(self.ready) != 0: self.low_at = None; return
        if self.low_at is None: self.low_at = self.s.clock
        if self.kbd.queue and self.s.clock >= self.low_at + 16:
            self.code = self.kbd.queue.pop(0); self.s.kick(self); self.s.settle_now(); self.level = 1; self.s.kick(self)


class Level(Dev):
    """pins held at levels from outside: the 1802's outputs, a switch's contact, an output nobody plays. Two of its
    pins may be on one net (a fault), so the levels are kept by pin"""
    def __init__(self, sys_, ref): super().__init__(sys_, ref, ()); self.v = {}

    def set(self, levels):
        """{pin key: (net, level)}; a pin not named is let go"""
        new = {k: (n, None) for k, (n, _) in self.v.items()}; new.update(levels)
        if new != self.v: self.v = new; self.s.kick(self)

    def outputs(self, val): return list(self.v.values())


# ============================================================================================== the machine
class System:
    """the bus board with cards in its slots. bus: the board's Netlist (bus_netlist(), or a damaged copy);
    slots: {card: socket ref}. flags: FLAGS' key"""
    def __init__(self, bus, slots, rom=None, flags="A", clock=None):
        self.slots = dict(slots); self.flags = flags; self.val = {}; self.live = self.let_go = False; self.clock = 0
        cards = {n: _cards(n, flags) for n in ORDER if n in slots}
        self.nl = nl = Joined(bus, slots, cards); self.on = [n for n in cards if n not in nl.unpowered]
        self.rom = bytes(rom or b"").ljust(4096, b"\xff")
        self.models, self.devs = [], []
        self.cells = {}; self.video = Video6845(); self.kbd = Keyboard(); self.kbd.queue = list(KEYS)
        now = clock or (lambda: datetime.datetime(2026, 11, 25, 12, 0, 0))
        self.rtc, self.uart, self.ide = DS12885(now=now, start=now()), UART16550(), IDE(None, sectors=64)
        self.ide.disk[512:1024] = bytes((i * 37 + 11) & 0xFF for i in range(512))
        self.pulls = {}; self.dirty = set(); self._down = {}; self._bits = {}
        for ref in sorted(nl.parts): self._fit(ref)
        for ref in sorted(nl.parts):                                    # a diode onto a pulled-up net (the panel's D1)
            if classify(nl.parts[ref].lib) == "diode" and ref.partition(".")[0] not in nl.unpowered and self.pulls.get(nl.net(ref, "2")) == {1}:
                self.models.append(WiredDiode(nl, ref))
        self.pins = None
        if "cpu" in self.on:
            self.cpu = self._dev(Level(self, "cpu.U1")); self.pins = Pins1802(13)
            n = lambda p: nl.net("cpu.U1", p)
            self.n_d = [n(p) for p in (15, 14, 13, 12, 11, 10, 9, 8)]; self.n_a = [n(p) for p in range(25, 33)]
            self.n_out = dict(Q=n(4), SC1=n(5), SC0=n(6), MRD=n(7), TPB=n(33), TPA=n(34), MRW=n(35))
            self.n_n = [n(19), n(18), n(17)]; self.n_ef = [n(p) for p in (24, 23, 22, 21)]
            self.n_int, self.n_dma, self.n_wait, self.n_clear = n(36), n(38), n(2), n(3)
            self.pins.ef = self._ef; self.cpu_sw = self._dev(Level(self, "cpu.SW1"))
            self.n_bus_dmain = nl.net("bus.J1", LINES.index("-DMAIN") + 1)
        if "panel" in self.on:
            self.hand = self._dev(Level(self, "panel switches"))
            find = lambda name: next(nl.net("panel." + r, pin) for (r, pin), (net, _) in cards["panel"].pins.items() if net == "/" + name and r != "J1")
            self.n_adr = [find("ADR%d" % i) for i in range(16)]; self.n_led = [find("OUT%d" % i) for i in range(8)]
            self.n_q_led, self.n_rom_led = find("LED_Q_K"), find("ROM_LED_L")
            self.toggles(TOGGLES)
        self._wire()

    # ------------------------------------------------------------------ building
    def _fit(self, ref):
        nl = self.nl; card, _, r = ref.partition("."); part = nl.parts[ref]; kind = classify(part.lib)
        if card in nl.unpowered: return
        if ref == "ide.JP1": self._dev(Drive(self, ref, self.ide)); return
        if kind == "pull":
            self._pull([p for (x, p) in nl.pins if x == ref and p != "1"], ref); return
        if kind is None:
            if "R-US" in part.lib or part.lib == "R":
                (_, a), (_, b) = [(p, nl.net(x, p)) for (x, p) in nl.pins if x == ref]
                for one, other in ((a, b), (b, a)):
                    if one in Circuit.POWER and other not in Circuit.POWER: self.pulls.setdefault(other, set()).add(Circuit.POWER[one])
            return
        if ref == "video.IC20" or ref == "panel.U3": self.models.append(Buf244(nl, ref))
        elif ref == "video.IC19": self.models.append(Key374(nl, ref))
        elif ref == "video.IC21": self._dev(ATmega(self, ref, self.kbd))
        elif ref == "panel.U13": self._dev(RTC(self, ref, self.rtc))
        elif ref == "panel.U20": self._dev(UART(self, ref, self.uart))
        elif kind in ("RAM", "ROM"):
            d = MemChip(nl, ref, kind); chip = self.cells[ref] = bytearray(0x8000)
            if kind == "ROM": chip[:] = _mem_card().contents[r]
            self._dev(Chip(self, d, chip.__getitem__, chip.__setitem__ if kind == "RAM" else None))
        elif ref == "cpu.U3": self._dev(Chip(self, ROM2732(nl, ref), self.rom.__getitem__, None))
        elif kind == "DPRAM":
            v = self.video.vram; self._dev(Chip(self, DualPort(nl, ref), lambda a: v[a % len(v)], lambda a, b: v.__setitem__(a % len(v), b)))
        elif kind == "CRTC":
            d = CRTC(nl, ref); self._dev(Chip(self, d, lambda rs: 0, self._crtc))
            out = self._dev(Level(self, ref + " outputs")); f = nl.part_pins(ref)
            out.v = {"VS": (f["VS"], 0), "DE": (f["DE"], 0)}; self.n_crtc_reset = f["RESET"]
        elif kind in Circuit.LOGIC: self.models.append(Circuit.LOGIC[kind](nl, ref))

    def _pull(self, pins, ref):
        common = self.nl.net(ref, "1")
        if common not in Circuit.POWER: return
        for p in pins:
            net = self.nl.net(ref, p)
            if net not in Circuit.POWER: self.pulls.setdefault(net, set()).add(Circuit.POWER[common])

    def _dev(self, d): self.devs.append(d); return d

    def _crtc(self, rs, b):
        v = self.video
        if not rs: v.sel = b & 31
        elif v.sel < 18: v.reg[v.sel] = b

    def _wire(self):
        self.listen = {}; self.contrib = {}; by_ref = {}
        for i, m in enumerate(self.models + self.devs): m.order = i
        for (ref, pin), (net, _) in self.nl.pins.items(): by_ref.setdefault(ref, set()).add(net)
        for m in self.models:
            for n in by_ref[m.ref]: self.listen.setdefault(n, []).append(m)
        for d in self.devs:
            for n in d.listen: self.listen.setdefault(n, []).append(d)
        for net in {n for n, _ in self.nl.pins.values()}: self.val[net] = self._resolve(net)
        self.dirty = set(self.models) | set(self.devs)

    # ------------------------------------------------------------------ settling
    def _resolve(self, net):
        vs = {v for v in self.contrib.get(net, {}).values() if v is not None}
        if net in Circuit.POWER: vs.add(Circuit.POWER[net])
        if len(vs) == 1: return next(iter(vs))
        if vs: return X
        p = self.pulls.get(net)
        return next(iter(p)) if p and len(p) == 1 else X

    def fights(self):
        """nets on which two outputs disagree now"""
        return sorted(n for n, c in self.contrib.items()
                      if len({v for v in list(c.values()) + ([Circuit.POWER[n]] if n in Circuit.POWER else []) if v is not None}) > 1)

    def settle_now(self, limit=200):
        one = False; by = lambda m: m.order
        for k in range(limit):
            if not self.dirty: return
            batch = sorted(self.dirty, key=by) if not one else [min(self.dirty, key=by)]
            if one: self.dirty.discard(batch[0])
            else: self.dirty = set()
            changed = set()
            for m in batch:
                for i, (net, v) in enumerate(m.outputs(self.val)):
                    c = self.contrib.setdefault(net, {}); key = (m.order, i)
                    if c.get(key, "none") != v: c[key] = v; changed.add(net)
            for net in changed:
                v = self._resolve(net)
                if v != self.val.get(net):
                    self.val[net] = v; self.dirty.update(self.listen.get(net, ()))
            one = k > 30                                    # a symmetric latch: one at a time (see logic.py)
        raise Noticed("the logic does not settle (an oscillation)")

    def kick(self, d): self.dirty.add(d)
    def event(self, text):
        if self.live: raise Noticed(text)

    def settle(self):
        for _ in range(12):
            self.settle_now()
            for d in self.devs: d.after(self.val)
            if self.pins:
                w, c = self.val.get(self.n_wait), self.val.get(self.n_clear)
                if w in (0, 1) and c in (0, 1):
                    if self.pins.set_mode(c, w): self._put_pins()
                elif self.live: raise Noticed("the 1802's CLEAR or WAIT is undefined")
            if not self.dirty: return
        raise Noticed("the cards do not settle")

    # ------------------------------------------------------------------ the 1802
    def _put_pins(self):
        o = self.pins.outputs(); v = {("A", i): (n, o["A"] >> i & 1) for i, n in enumerate(self.n_a)}
        v.update({("D", i): (n, None if o["D"] is None else o["D"] >> i & 1) for i, n in enumerate(self.n_d)})
        v.update({("N", i): (n, o["N"] >> i & 1) for i, n in enumerate(self.n_n)})
        v.update({k: (n, o[k]) for k, n in self.n_out.items()}); self.cpu.set(v)

    def _ef(self, n):
        v = self.val.get(self.n_ef[n - 1])
        if v not in (0, 1): raise Noticed("the 1802's EF%d is undefined" % n)
        return v == 0

    def data(self):
        b = [self.val.get(n) for n in self.n_d]
        return None if any(x not in (0, 1) for x in b) else sum(x << i for i, x in enumerate(b))

    def power_on(self, state=None):
        """SW_RST held low (U12 and the RESET/RUN switch), the clock running, then let go. state: {(ref, key): 0 | 1}, how
        flip-flops came up (a flip-flop or latch not named: unknown; a number in place of the dict: every one so). The
        IO panel as it was drawn until 2026-11-25 did not start from every state: its REQ (U10A) up as 1 was a bus fight
        in every memory write, its DRIVE (U11A) up as 1 one through the reset: test_busboard.PowerUp"""
        if not self.pins: raise Noticed("the CPU card has no supply")
        self._put_pins(); sw = self.nl.net("cpu.U12", 1)
        self.cpu_sw.set({"SW": (sw, 0)}); self.settle()
        for _ in range(8): self.edge()
        for _ in range(2 if state is not None else 0):                  # twice: one flip-flop may hold another
            for m in self.models:
                for k in (m.state if isinstance(getattr(m, "state", None), dict) else ()):
                    v = state if isinstance(state, int) else state.get((m.ref, k))
                    if v is not None: m.state[k] = v; self.kick(m)
            self.settle()
        f = [n for n in self.fights() if n.startswith("bus.")]
        if f and state is not None: raise Noticed("two outputs disagree on %s in the power-on reset" % f[0])
        self.cpu_sw.set({}); self.settle(); self.let_go = True

    def cpu_switch(self, reset):
        self.cpu_sw.set({"SW": (self.nl.net("cpu.SW1", 3), 0)} if reset else {}); self.settle()

    def edge(self):
        """one transition of the 1802's clock -> the cycle that ended with it (kind, address, byte, N), or None"""
        self.clock += 1; p = self.pins; e = p.e; n0 = len(p.cycles); kind = p.cyc["kind"] if p.cyc else None
        running = p.mode not in ("reset", "pause") and not p.init > 16
        if running and self.live:
            i, d = self.val.get(self.n_int), self.val.get(self.n_dma)
            if i not in (0, 1): raise Noticed("the 1802's INTERRUPT is undefined")
            if d not in (0, 1): raise Noticed("the 1802's DMA IN is undefined")
            p.core.int_line = i == 0
            if p.mode == "run" and self.val.get(self.n_bus_dmain) != 1:
                # nothing pulls -DMAIN while the machine runs (a boot reset and LOAD mode are the only times it is low), and
                # CPU Rev D takes it only when paused, so no card would notice; a logic probe or the bus driver reading the
                # line does. A short to -INT shows when the UART's interrupt comes in (2026-11-27)
                raise Noticed("-DMAIN is %s in RUN (-INT %s), must be high" % (self.val.get(self.n_bus_dmain), i))
        b = self.data()
        if running and self.live and e in (13, 14, 15):
            f = self.fights()
            if f: raise Noticed("two outputs disagree on %s at %s cycle, address %04X" % (f[0], kind, p.cyc["addr"]))
        if running and self.live and e == 15 and kind in ("fetch", "read", "write", "inp", "dma") and b is None:
            raise Noticed("%s at %04X: an undefined bit on the 1802's data lines" % (kind, p.cyc["addr"]))
        p.edge(self.val.get(self.n_dma), 0xFF if b is None else b)
        if self.let_go and not self.live and p.mode == "run" and not p.init: self.live = True
        self._put_pins(); self.settle()
        return p.cycles[-1] if len(p.cycles) > n0 else None

    # ------------------------------------------------------------------ the IO panel's hands and lamps
    def _contact(self, ref, a, b):
        """a closed contact: the net on one pin takes the level of the supply on the other (hw.switch_contact)"""
        na, nb = self.nl.net("panel." + ref, a), self.nl.net("panel." + ref, b)
        for net, other in ((na, nb), (nb, na)):
            if other in Circuit.POWER: return net, Circuit.POWER[other]
        raise Noticed("the panel's %s has no supply on its contact" % ref)

    def toggles(self, byte):
        """the data toggles SW1-SW8 (2 = the line, 1 = its level at 1, 3 = at 0)"""
        self._bits = {"SW%d" % (k + 1): self._contact("SW%d" % (k + 1), 2, 1 if byte >> k & 1 else 3) for k in range(8)}
        self.hand.set({**self._bits, **self._down})

    def press(self, *refs):
        """the controls held closed now: SW9 INPUT, SW10 RUN/RESET at RESET, SW11 LOAD on, SW12 RESET"""
        self._down = {r: self._contact(r, 1, 2) for r in refs}
        self.hand.set({**self._bits, **self._down}); self.settle()

    def lamps(self):
        """what a person sees on the IO panel: the byte on its LEDs, the address on its TIL311s, Q, ROM"""
        bits = lambda nets: [self.val.get(n) for n in nets]
        num = lambda b: None if any(x not in (0, 1) for x in b) else sum(x << i for i, x in enumerate(b))
        return dict(out=num(bits(self.n_led)), addr=num(bits(self.n_adr)), q=self.val.get(self.n_q_led) == 0, rom=self.val.get(self.n_rom_led) == 0)


# ============================================================================================== the program, and what it must do
_ROM = []
def program():
    """bus_program.asm as the CPU card's EPROM holds it"""
    if not _ROM:
        sys.path.insert(0, os.path.join(ROOT, "tools")); import asm1802
        a = asm1802.assemble_file(os.path.join(HERE, "bus_program.asm"))
        if a.errors: raise ValueError("bus_program.asm: " + "; ".join(a.errors))
        rom = bytearray(b"\xff" * 4096)
        for addr, b in a.image().items(): rom[addr - 0xF000] = b
        _ROM.append(bytes(rom))
    return _ROM[0]


EPROM_AT = sorted({0x8000, 0xE5A5} | {0x8000 | 1 << k for k in range(15)} | {0xE5A5 ^ 1 << k for k in range(13)})


def eprom(a):
    """the byte the memory card's EPROMs hold at bus address a (EPROM_AT: the addresses the program reads, and those one
    address line away from E5A5; FF elsewhere)"""
    return ((a & 0xFF) * 3 ^ (a >> 8) * 5 ^ (a >> 4) ^ 0x5C) & 0xFF


def _program_eproms():
    c = _mem_card()
    if not hasattr(c, "_test_pattern"):
        for a in EPROM_AT: c.program(a, eprom(a))
        c._test_pattern = True


class Reference(Video6845KbdMachine):
    """the instruction-level machine, with the cycles it makes written down: (kind, address, byte, N), as Pins1802 does"""
    def __init__(self):
        super().__init__(panel=True)
        self.trace = []; self.cpurom.data[:] = program(); self.cpurom.loaded = True; self.cpurom.remap = True
        for a in EPROM_AT: self.memory.rom[a] = eprom(a)
        now = datetime.datetime(2026, 11, 25, 12, 0, 0); self.panel.rtc = DS12885(now=lambda: now, start=now)
        self.ide = IDE(None, sectors=64); self.ide.disk[512:1024] = bytes((i * 37 + 11) & 0xFF for i in range(512))
        self.kbd.queue = list(KEYS); self.panel.uart.receive(UART_IN); self.panel.switches = TOGGLES; self.dma = False; self._in = None

    def fetch(self, a):                                           # an operand is read in an execute cycle (S1)
        v = super().fetch(a); self.trace.append(("fetch" if self.first else "read", a, v, 0)); self.first = False; return v

    def read(self, a): v = super().read(a); self.trace.append(("read", a, v, 0)); return v
    def out(self, n, v): super().out(n, v); k, a, b, _ = self.trace[-1]; self.trace[-1] = (k, a, b, n)
    def inp(self, n): self._in = n; return super().inp(n)

    def write(self, a, v):
        super().write(a, v); n, self._in = self._in or 0, None
        self.trace.append(("dma" if self.dma else "inp" if n else "write", a, v, n))

    def step(self):
        self.cpu.int_line = self.panel.uart.intr(); self.first = True; return super().step()


HANDS = {"INPUT": "SW9", "RESET": "SW10", "LOAD": "SW11", "BOOT": "SW12"}


def reference(limit=6000):
    """what the program must do, from the instruction-level machine: {'run': its cycles to the end, 'load': the DMA
    cycles, 'ram': RAM's program, 'boot': the first cycles after the RESET button; what is left in the machine}"""
    m = Reference(); out = {}; t = m.trace

    def go(mark, n=limit):
        for _ in range(n):
            k = len(t); m.step()
            for c in t[k:]:
                if c[3] == 4 and c[0] == "read":
                    if c[2] == 0xE1: m.panel_set(input=True)
                    elif c[2] == 0xE2: m.panel_set(input=False)
                    if c[2] == mark: return
        raise ValueError("the program does not come to its marker %02X" % mark)
    go(0xED); out["run"] = list(t); del t[:]
    out["vram"] = bytes(m.video.vram); out["crtc"] = list(m.video.reg); out["rtc"] = bytes(m.panel.rtc.ram); out["tx"] = m.panel.uart.sent()
    out["q"] = m.cpu.Q; out["latch"] = m.panel.latch; out["regs"] = list(m.ide.regs)
    m.panel_set(run=False); m.panel_set(load=True); m.dma = True
    for b in RAM_PROGRAM: m.panel_set(switches=b); m.panel_set(input=True); m.panel_set(input=False)
    out["load"] = list(t); del t[:]; m.dma = False
    m.panel_set(load=False); m.panel_set(run=True); go(0xC3); out["ram"] = list(t); del t[:]
    for _ in range(3): m.step()
    out["q2"] = m.cpu.Q; del t[:]
    m.panel_set(reset=True); m.panel_set(reset=False)
    while len(t) < 40: m.step()
    out["boot"] = t[:40]
    return out


_REF = []
def expected():
    if not _REF: _REF.append(reference())
    return _REF[0]


CYCLES = ("fetch", "read", "write", "inp", "dma")


class Run:
    """the whole test on one board: raises Noticed at the first thing that is not as it must be"""
    def __init__(self, bus=None, slots=None, flags="A"):
        _program_eproms()
        self.s = System(bus or bus_netlist(), slots or dict(zip(ORDER, SLOTS)), program(), flags); self.s.uart.receive(UART_IN)
        self.ref = expected(); self.cycles = 0; self.edges = 0

    def check(self, what, got, want):
        if got != want: raise Noticed("%s: %s, must be %s" % (what, got, want))

    def play(self, phase, limit=40):
        """run until the phase's cycles have all been made, each as it must be; limit: edges with none"""
        want = self.ref[phase]; i = 0; idle = 0; s = self.s
        while i < len(want):
            c = s.edge(); self.edges += 1; idle += 1
            if idle > limit * 16: raise Noticed("%s: no cycle after %d of %d (the 1802 is in %s)" % (phase, i, len(want), s.pins.mode))
            if c is None or c[0] not in CYCLES: continue
            idle = 0; self.cycles += 1
            if c != want[i]: raise Noticed("%s, cycle %d: %s %04X %02X N=%d, must be %s %04X %02X N=%d" % ((phase, i) + c + want[i]))
            i += 1; self.look(c)
            if c[0] == "read" and c[3] == 4:
                if c[2] == 0xE1: s.press("SW9")
                elif c[2] == 0xE2: s.press()

    def look(self, c):
        """the IO panel's lamps, after a cycle that shows on them"""
        s = self.s; l = s.lamps()
        self.check("the address on the IO panel", l["addr"], c[1])
        if c[0] == "read" and c[3] == 4: self.check("the IO panel's LEDs", l["out"], c[2])
        if c[0] == "fetch":
            self.check("the IO panel's Q LED", l["q"], bool(s.pins.Q))
            self.check("the IO panel's ROM LED", l["rom"], c[1] >= 0xF000 or not self.booted)
        if c[1] & 0x8000: self.booted = True
    booted = False

    def all(self, state=None):
        s, r = self.s, self.ref
        for n in ORDER:
            if n in s.slots and n not in s.on: raise Noticed("the %s card has no supply" % n)
        s.power_on(state); self.play("run")
        self.check("the video RAM", bytes(s.video.vram).hex(), r["vram"].hex()); self.check("the 6845's registers", s.video.reg, r["crtc"])
        self.check("the clock's RAM", bytes(s.rtc.ram).hex(), r["rtc"].hex()); self.check("what the UART sent", s.uart.sent(), r["tx"])
        self.check("the drive's registers", s.ide.regs, r["regs"]); self.check("Q", s.pins.Q, r["q"])
        # LOAD mode: RESET, then LOAD too; the toggles and INPUT, a byte at a time
        s.press("SW10"); self.spin(8)
        self.check("the 1802's mode with RUN off", s.pins.mode, "reset"); self.check("the drive's reset", s.val.get(s.nl.net("ide.JP1", 1)), 0)
        s.press("SW10", "SW11"); self.spin(40); self.check("the 1802's mode in LOAD", s.pins.mode, "load")
        n0 = len(s.pins.cycles)
        for b in RAM_PROGRAM:
            s.toggles(b); s.settle(); s.press("SW10", "SW11", "SW9"); self.spin(64); s.press("SW10", "SW11"); self.spin(32)
        self.check("LOAD mode's DMA cycles", [c for c in s.pins.cycles[n0:] if c[0] == "dma"], r["load"])
        s.toggles(TOGGLES); s.press("SW10"); self.spin(8); s.press(); self.booted = True; self.play("ram")
        for _ in range(6): self.spin(16)
        self.check("Q, from the program in RAM", s.pins.Q, r["q2"])
        s.press("SW11"); self.check("the 1802's mode with LOAD on alone", s.pins.mode, "pause"); s.press()
        # the RESET button: -RESET and -DMAIN together, a boot reset
        s.press("SW12"); self.spin(8); self.check("the 1802's mode with RESET down", s.pins.mode, "reset"); s.press(); self.booted = False; self.play("boot")
        return self

    def spin(self, n):
        for _ in range(n): self.s.edge(); self.edges += 1



# ============================================================================================== the board by itself
# what each line rests at with no card driving it (docs/manual/bus.md): the enabling lines off, the data FF, the
# open-collector lines let go. A0-A7, Q and SC0 rest at nothing: the 1802 always drives them
IDLE = {**{"D%d" % i: 1 for i in range(8)}, "N0": 0, "N1": 0, "N2": 0, "TPA": 0, "TPB": 0, "-MRD": 1, "-MRW": 1, "-VMA": 1,
        "-RESET": 1, "-INT": 1, "-PAUSE": 1, "-DMAIN": 1, "-EF": 1, "-EF1": 1, "-EF2": 1, "-EF3": 1}
NO_IDLE = ["A%d" % i for i in range(8)] + ["Q", "SC0"]
# position -> line, as docs/manual/bus.md gives the slot (GND 1 ... +5V 30, then the six lines beyond it)
LINES = (["GND", "N0", "N1", "-RESET", "-VMA", "-EF", "N2", "-INT"] + ["A%d" % i for i in range(7, -1, -1)] + ["-MRW", "-MRD", "TPB", "TPA", "Q"] +
         ["D%d" % i for i in range(7, -1, -1)] + ["+5V", "-EF1", "-EF2", "-EF3", "-DMAIN", "SC0", "-PAUSE"])


def idle(bus):
    """the board with no cards: what each slot's pins rest at. Raises Noticed at the first that is not as IDLE says"""
    s = System(bus, {}); s.settle_now()
    for j in SLOTS:
        for pos, line in enumerate(LINES, 1):
            net = "VCC" if bus.net(j, pos) == "+5V" else "GND" if bus.net(j, pos) == "GND" else s.nl.net("bus." + j, pos)
            want = 1 if line == "+5V" else 0 if line == "GND" else IDLE.get(line, X)
            got = s.val.get(net, X)
            if got != want: raise Noticed("%s position %d (%s) rests at %s, must be %s" % (j, pos, line, "nothing" if got == X else got, "nothing" if want == X else want))


def idle_cards(bus, slots):
    """the memory, video, panel and IDE cards in the bus with the CPU card out: none drives the data lines, and each line
    rests as it must (SC0: the panel's RN1 pulls it up)"""
    s = System(bus, slots, program()); s.kbd.queue = []; s.settle()
    s.press("SW10"); s.press()                                       # RUN/RESET: KEY-READY cleared
    for j in SLOTS:
        for pos, line in enumerate(LINES, 1):
            if line not in IDLE: continue
            got = s.val.get(s.nl.net("bus." + j, pos), X)
            if got != IDLE[line]: raise Noticed("CPU card out: %s position %d (%s) rests at %s, must be %s" % (j, pos, line, "nothing" if got == X else got, IDLE[line]))
    f = [n for n in s.fights() if "/D" in n]
    if f: raise Noticed("CPU card out: two outputs disagree on " + f[0])


def power_path(bus, source):
    """the supply's way from an input ('REG': J9's centre pin, 'EXT': J10 pin 1) to the bus +5V with JP1's shunt set for it
    and SW1 on, part by part as the netlist joins them -> the list of nets. Raises Noticed where it does not go on"""
    net = bus.net; path = []
    if source == "REG":
        at = net("J9", "1")
        if net("D2", "2") != at: raise Noticed("REG: J9's centre pin does not reach D2's anode")
        path.append(at); at = net("D2", "1")
        if net("U1", "1") != at: raise Noticed("REG: D2's cathode does not reach U1's input")
        path.append(at); at = net("U1", "3"); pin = "1"
    else: at = net("J10", "1"); pin = "3"
    path.append(at)
    if net("JP1", pin) != at: raise Noticed("%s: the supply does not reach JP1 pin %s" % (source, pin))
    at = net("JP1", "2"); path.append(at)
    if net("SW1", "2") != at: raise Noticed("JP1's common does not reach SW1's common")
    at = net("SW1", "3"); path.append(at)
    for j in SLOTS:
        if net(j, "30") != at: raise Noticed("SW1's output does not reach %s position 30" % j)
    steps = [net("J9", "1"), net("D2", "1"), net("U1", "3"), net("J10", "1"), net("JP1", "2"), net("SW1", "3")]
    if len(set(steps)) != len(steps): raise Noticed("two steps of the supply are one net: %s" % steps)
    grounds = [("J9", "2"), ("J9", "MP"), ("J10", "2"), ("U1", "2"), ("C10", "2"), ("C1", "2"), ("D1", "1")] + [(j, "1") for j in SLOTS]
    for g in grounds:
        if net(*g) != net("J1", "1"): raise Noticed("%s pin %s is not on ground" % g)
    if at == net("J1", "1"): raise Noticed("+5V is on ground")
    for part, pin in (("C10", path[1] if source == "REG" else net("C10", "1")), ("C1", at)):
        if net(part, "1") != pin: raise Noticed("%s pin 1 is not on the supply" % part)
    for k in range(2, 10):
        if {net("C%d" % k, "1"), net("C%d" % k, "2")} != {at, net("J1", "1")}: raise Noticed("C%d is not across the supply" % k)
    if net("R1", "1") != at or net("R1", "2") != net("D1", "2"): raise Noticed("the power LED is not from +5V through R1")
    return path


# ============================================================================================== faults in the board
def _set(bus, ref, pin, net): bus.pins[(ref, str(pin))] = (net, bus.pins[(ref, str(pin))][1])


def fault(kind, *a):
    """a copy of the board's netlist with one fault: ('open', ref, pin) a pin off its net; ('swap', ref, pin, pin) two pins'
    nets exchanged; ('short', net, net) two nets joined; ('move', ref, pin, net) a pin on another net; ('turn', socket) and ('shift', socket)"""
    bus = bus_netlist()
    if kind == "open": _set(bus, a[0], a[1], "open:%s.%s" % a)
    elif kind == "swap":
        n, m = bus.net(a[0], a[1]), bus.net(a[0], a[2]); _set(bus, a[0], a[1], m); _set(bus, a[0], a[2], n)
    elif kind == "short": bus.short(*a)
    elif kind in ("turn", "shift"):                              # a socket end for end, or drawn one position along
        was = [bus.net(a[0], p) for p in range(1, 37)]
        for p, n in enumerate(was[::-1] if kind == "turn" else was[1:] + was[:1], 1): _set(bus, a[0], p, n)
    elif kind == "move": _set(bus, a[0], a[1], a[2])
    else: raise ValueError(kind)
    return bus


def arrangement(k): return {c: SLOTS[(k + i) % 8] for i, c in enumerate(ORDER)}


def used(card):
    """the socket positions at which this card takes a line: its connector's pads that go on to another part"""
    _, jref, where = CARDS[card]; nl = _cards(card, "A"); nets = nl.nets
    return sorted(where(int(p)) for r, p in nl.pins if r == jref and any(x != jref for x, _ in nets[nl.net(r, p)]))


_MEMO = {}
def program_on(bus, slots, flags):
    """the test on this board -> None, or what it noticed. Two joined circuits that are the same one run once"""
    try: key = (Joined(bus, slots, {n: _cards(n, flags) for n in ORDER}).partition(), flags)
    except Noticed as e: return str(e)
    if key not in _MEMO:
        try: Run(bus, slots, flags).all(); _MEMO[key] = None
        except Noticed as e: _MEMO[key] = str(e)
    return _MEMO[key]


_NL = {}
def _cards(name, flags):
    if (name, flags) not in _NL: _NL[(name, flags)] = card_netlist(name, flags)
    return _NL[(name, flags)]


def notice(f):
    """a fault (fault()'s arguments) through every check -> [(check, what it said)], the first that notices in each of the
    three: 'program' (a slot fault: with each card in that slot, the CPU card first), 'idle' and 'power'"""
    bus = fault(*f); out = []; ks = [0]
    if f[0] in ("open", "swap", "move", "turn", "shift") and f[1] in SLOTS:
        s = SLOTS.index(f[1]); ks = [(s - i) % 8 for i in range(len(ORDER))]
    for k in ks:
        for flags in sorted(FLAGS):
            w = program_on(bus, arrangement(k), flags)
            if w: out.append(("program", "%s in %s: %s" % (ORDER[ks.index(k)], f[1], w) if len(ks) > 1 else w)); break
        if out: break
    for name, t in (("idle", lambda: idle(bus)), ("power", lambda: [power_path(bus, x) for x in ("REG", "EXT")])):
        try: t()
        except Noticed as e: out.append((name, str(e)))
    return out


def open_under(card, pos):
    """position pos of slot J1 open with this card in it, the other cards in the next slots: what the program notices, or
    None (each way the flag lines' jumpers are set)"""
    for flags in sorted(FLAGS):
        w = program_on(fault("open", "J1", str(pos)), arrangement(-ORDER.index(card) % 8), flags)
        if w: return w


def all_faults():
    """{group: [faults]}: every pin of every slot open; every two neighbours of every slot swapped; every slot
    turned end for end, or one position along; every two neighbouring lines shorted, then every other two; every resistor pin open, moved to its neighbour's line, or the network's common on the other supply"""
    bus = bus_netlist(); out = {"open": [], "swap": [], "short": [], "slot": [], "short, others": [], "resistor open": [], "resistor moved": [], "resistor common": []}
    for j in SLOTS:
        out["open"] += [("open", j, str(p)) for p in range(1, 37)]
        out["slot"] += [("turn", j), ("shift", j)]
        out["swap"] += [("swap", j, str(p), str(p + 1)) for p in range(1, 36)]
    nets = [bus.net("J1", p) for p in range(1, 37)]
    out["short"] = [("short", a, b) for a, b in zip(nets, nets[1:])]
    out["short, others"] = [("short", a, b) for i, a in enumerate(nets) for b in nets[i + 2:]]
    for rn, n in (("RN1", 9), ("RN2", 9), ("RN3", 6), ("RN4", 4)):
        out["resistor open"] += [("open", rn, str(p)) for p in range(1, n + 1)]
        out["resistor moved"] += [("move", rn, str(p), bus.net("J1", (nets.index(bus.net(rn, p)) + 1) % 36 + 1)) for p in range(2, n + 1)]
        out["resistor common"].append(("move", rn, "1", "GND" if bus.net(rn, "1") == "+5V" else "+5V"))
    return out


def survey(groups=None, verbose=True):
    """every fault of the groups through notice() -> {group: (how many, noticed by the program, by any check, [those not])}"""
    res = {}
    for g, fs in all_faults().items():
        if groups and g not in groups: continue
        prog = any_ = 0; missed = []; only = []
        for f in fs:
            w = notice(f); by = {n for n, _ in w}
            prog += "program" in by; any_ += bool(by)
            if not by: missed.append(f)
            elif "program" not in by: only.append((f, sorted(by)))
        res[g] = (len(fs), prog, any_, missed, only)
        if verbose: print("%-16s %4d faults: %4d by the program, %4d by any check; missed %s; not by the program %s" % (g, len(fs), prog, any_, missed, only), flush=True)
    return res


if __name__ == "__main__":
    import time
    if sys.argv[1:2] == ["survey"]: t = time.time(); survey(sys.argv[2:]); print("%.0f s" % (time.time() - t)); sys.exit()
    for flags in sorted(FLAGS):
        t = time.time(); r = Run(flags=flags)
        try: r.all(); print("flags %s: as it must be, %d cycles" % (flags, r.cycles))
        except Noticed as e: print("flags %s: %s (after %d cycles)" % (flags, e, r.cycles))
        print("  %.1f s, %d edges" % (time.time() - t, r.edges))
