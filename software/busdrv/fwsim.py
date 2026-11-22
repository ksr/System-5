# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-11
"""The bus driver firmware (embedded/bus-driver/s5-bus-driver/s5-bus-driver.ino) in Python, driving a Backplane.

The functions below follow the sketch line for line: the same expander register shadows (olat, iodir), the same
port writes in the same order. Every port write is one I2C transaction on the real card, so each one changes the bus
pins here too (Backplane.set_pins), and the cards see every in-between state the real card produces.
Keep it in step with the sketch: a change to a bus cycle there must be made here as well.

rev="B" (the default) is BUSDRV-B: two expanders, the 30-pin bus (backplane.Backplane).
rev="C" is BUSDRV-C (2026-11-20): a third expander (U3) with the 36-pin extension, the DEBUG cable's inputs and the
spares, CLK OUT on the Nano's D9 and the probes, against backplane.Backplane36. Each change of D9 is
Backplane36.clock(), one edge of the 1802's clock, and every expander read is taken from the bus as it stands then, so
LOAD mode by the clock runs here edge for edge as the sketch runs it. The sketch finds its board by looking for U3;
here rev says which it is.

legacy=True runs the bus cycles as the sketch had them before 2026-10-11 (no TPB in memory cycles; OUT/INP without
-MRD or TPA), to show what they did wrong.
load_fault, for the tests of the simulator itself (a check that has never failed on a wrong sequence proves nothing):
  "hold-dmain"   -DMAIN is let go only after the DMA cycle is over, as an expander at the 1802's own clock would do
  "early-data"   the byte is put on D0-D7 with the request, while the idle cycle's memory read is still on them
  "walk-hold"    WALK keeps driving a pin that does not follow (held against a supply) until it has read every port

WALK (2026-11-21) is the one command that drives a single pin of the address, data or N lines: with the expanders'
pull-ups on bus pins, _apply() hands the backplane every line by itself (Backplane.set_lines), not the grouped pins.

What the simulator has no time for: a steady clock (CLKHZ) moves the simulated 1802 CLOCK_EDGES_A_COMMAND edges before
each later command, not hz of them a second; PCOUNT counts the edges those make on the line a probe is hooked to;
PTIME and PDELAY answer only for PROBE1 on CLK OUT itself.

FwCard wraps it in the serial wire protocol, so s5busdrv.BusDriver(transport=FwCard(...)) talks to it exactly as it
talks to the real card.
"""
DATE = "2026-11-21"
BANNER = "s5-bus-driver blocks-1 io-2 clk-1 walk-1 %s BUSDRV-B (SIMULATED)" % DATE
BANNER_C = "s5-bus-driver blocks-1 io-2 clk-2 ext-1 mode-1 load-1 probe-1 walk-1 %s BUSDRV-C (SIMULATED)" % DATE
LEGACY_BANNER = "s5-bus-driver blocks-1 2026-10-06 (SIMULATED, the old bus cycles)"
BLOCK_MAX, WBLOCK_MAX = 64, 32
CLOCK_EDGES_A_COMMAND = 640             # a steady clock: 40 machine cycles of the simulated 1802 before each command

# (chip, port, bit, flags) as in the sketch's SIGS table
LOW_ACTIVE, OPEN_COLL = 1, 2
SIGS = {"TPA": (1, 0, 2, 0), "TPB": (1, 0, 3, 0), "-MRD": (1, 0, 4, LOW_ACTIVE), "-MRW": (1, 0, 5, LOW_ACTIVE),
        "-VMA": (1, 0, 6, LOW_ACTIVE), "Q": (1, 1, 0, 0), "-RESET": (1, 1, 1, LOW_ACTIVE | OPEN_COLL),
        "-INT": (1, 1, 2, LOW_ACTIVE | OPEN_COLL), "-EF": (1, 1, 3, LOW_ACTIVE | OPEN_COLL),
        "-EF1": (2, 0, 0, LOW_ACTIVE | OPEN_COLL), "-EF2": (2, 0, 1, LOW_ACTIVE | OPEN_COLL),       # BUSDRV-C: U3
        "-EF3": (2, 0, 2, LOW_ACTIVE | OPEN_COLL), "-PAUSE": (2, 0, 3, LOW_ACTIVE | OPEN_COLL),
        "-DMAIN": (2, 0, 4, LOW_ACTIVE | OPEN_COLL)}
PIN_OF = {"TPA": "TPA", "TPB": "TPB", "-MRD": "MRD", "-MRW": "MRW", "-VMA": "VMA", "Q": "Q", "-RESET": "RESET",
          "-INT": "INT", "-EF": "EF", "-EF1": "EF1", "-EF2": "EF2", "-EF3": "EF3", "-PAUSE": "PAUSE", "-DMAIN": "DMAIN"}
VA_A7, VA_TPA, VA_MRD, VA_MRW, VB_RESET, WA_PAUSE, WA_SC0 = 0x02, 0x04, 0x10, 0x20, 0x02, 0x08, 0x20
C_COMMANDS = ("MODE", "DMA", "LOADBLK", "CLKHZ", "CLKSTOP", "PROBE", "PCOUNT", "PTIME", "PDELAY", "DBG", "SPDIR", "SPIN")
# WALK: the bus lines of each port [chip][port] and which of them are open collector, as in the sketch; and every bus
# line's pin, by the backplane's name for it (backplane.LINES30 / LINES36): (chip, port, bit)
BUSPINS = ((0x7F, 0x7F), (0x7F, 0x7F), (0x3F, 0x00))
OCPINS = ((0x00, 0x00), (0x00, 0x0E), (0x1F, 0x00))
LINEMAP = dict([("D%d" % i, (0, 0, i)) for i in range(7)] + [("D7", (1, 0, 0))] +
               [("A%d" % i, (0, 1, i)) for i in range(7)] + [("A7", (1, 0, 1))] +
               [("TPA", (1, 0, 2)), ("TPB", (1, 0, 3)), ("MRD", (1, 0, 4)), ("MRW", (1, 0, 5)), ("VMA", (1, 0, 6)),
                ("Q", (1, 1, 0)), ("RESET", (1, 1, 1)), ("INT", (1, 1, 2)), ("EF", (1, 1, 3)),
                ("N0", (1, 1, 4)), ("N1", (1, 1, 5)), ("N2", (1, 1, 6)),
                ("EF1", (2, 0, 0)), ("EF2", (2, 0, 1)), ("EF3", (2, 0, 2)), ("PAUSE", (2, 0, 3)), ("DMAIN", (2, 0, 4)),
                ("SC0", (2, 0, 5))])
MODE_NAMES = ("RUN", "RESET", "PAUSE", "LOAD")
NEEDS_C = "Error: needs BUSDRV-C (no U3 at 0x22)"
NO_CLOCK = "CLK OUT does not reach the 1802: DEBUG cable, or the CPU card's JP1 not on EXT"


class Firmware:
    def __init__(self, backplane, bus_on=True, cpu_running=False, legacy=False, rev="B", load_fault=None):
        self.bp, self.bus_on, self.cpu_running, self.legacy = backplane, bus_on, cpu_running, legacy
        self.rev_c = rev == "C"; self.nchips = 3 if self.rev_c else 2; self.load_fault = load_fault
        self.olat = [[0, 0] for _ in range(3)]; self.iodir = [[0xFF, 0xFF] for _ in range(3)]; self.master = False
        self.gppu = [[0, 0], [0, 0], [0, 0x07]]            # the pull-up registers: off, but for U3's three DEBUG inputs
        self.i2c_ops = 0; self._driving = False
        self.spdir = 0; self.load_synced = False; self.clk_hz = 0; self.clk = 0; self.why = ""
        if bus_on: self.expanders_init()

    # ---------------------------------------------------------------- MCP23017 access -> bus pins
    def _apply(self):
        """what the expanders put on the bus now; nothing is driven until the card is master or pulls a line"""
        self.i2c_ops += 1; self.bp.tick()
        def out(c, p, b):
            return None if (self.iodir[c][p] >> b) & 1 else (self.olat[c][p] >> b) & 1
        if any(self.gppu[c][p] & BUSPINS[c][p] for c in range(self.nchips) for p in range(2)):
            # WALK: pull-ups on bus pins. The backplane works each line out by itself (one may be driven alone)
            mine = {n: cpb for n, cpb in LINEMAP.items() if cpb[0] < self.nchips}
            drv = {n: out(*cpb) for n, cpb in mine.items() if out(*cpb) is not None}
            self.bp.set_lines(drv, {n for n, (c, p, b) in mine.items() if (self.gppu[c][p] >> b) & 1})
            self._driving = True; return
        idle = not self.master and all(self._is_input(c, p) for c in range(self.nchips) for p in range(2))
        if idle and not self._driving: return
        self._driving = not idle
        pins = {}
        for name, (c, p, b, f) in SIGS.items():
            if c < self.nchips: pins[PIN_OF[name]] = out(c, p, b)
        a = [out(0, 1, i) for i in range(7)] + [out(1, 0, 1)]
        pins["A"] = None if None in a else sum(v << i for i, v in enumerate(a))
        n = [out(1, 1, 4 + i) for i in range(3)]
        pins["N"] = None if None in n else sum(v << i for i, v in enumerate(n))
        d = [out(0, 0, i) for i in range(7)] + [out(1, 0, 0)]
        dd = None if None in d else sum(v << i for i, v in enumerate(d))
        self.bp.set_pins(pins, dd)

    def _is_input(self, c, p):
        """every bus pin of this port an input (the spares are not on the bus)"""
        mask = 0x7F if c < 2 else (0x1F if p == 0 else 0x00)
        return self.iodir[c][p] & mask == mask

    def put_lat(self, c, p): self._apply()
    def put_dir(self, c, p): self._apply()
    def put_pu(self, c, p): self._apply()

    def gpio(self, c, p):
        """one GPIO port as the expander reads it: the bus as it stands, and the latch of an output-only spare"""
        self.i2c_ops += 1; self.bp.tick()
        bp = self.bp; pins = bp.pins or {}
        g = lambda k, d: d if pins.get(k) is None else pins[k]
        spare = self.olat[c][p] & 0x80
        w = getattr(bp, "walk", None)
        if w is not None and (c, p) != (2, 1):              # WALK: each line as the backplane worked it out
            v = spare | sum(w[n] << b for n, (cc, pp, b) in LINEMAP.items() if (cc, pp) == (c, p) and n in w)
            return v | ((self.olat[2][0] if self.spdir & 1 else 0x40) & 0x40) if c == 2 else v
        if c == 0: return spare | ((bp.data_in() if p == 0 else g("A", 0xFF)) & 0x7F)
        if c == 1 and p == 0:
            return (spare | (bp.data_in() >> 7) | ((g("A", 0xFF) >> 7) << 1) | g("TPA", 0) << 2 | g("TPB", 0) << 3 |
                    g("MRD", 1) << 4 | g("MRW", 1) << 5 | g("VMA", 1) << 6)
        if c == 1: return spare | g("Q", 0) | g("RESET", 1) << 1 | g("INT", 1) << 2 | g("EF", 1) << 3 | g("N", 0) << 4
        if p == 0:
            e = bp.ext_in()
            return (spare | e["EF1"] | e["EF2"] << 1 | e["EF3"] << 2 | e["PAUSE"] << 3 | e["DMAIN"] << 4 | e["SC0"] << 5 |
                    ((self.olat[2][0] if self.spdir & 1 else 0x40) & 0x40))
        dbg = bp.debug_in(); sp = sum(0x08 << i for i in range(4) if not (self.spdir >> (i + 1)) & 1)   # spare inputs float high
        return spare | dbg["CLOCK"] | dbg["SC0"] << 1 | dbg["SC1"] << 2 | sp | (self.olat[2][1] & 0x78 & ~sp)

    def all_inputs(self):
        for c in range(self.nchips):
            for p in range(2):
                self.iodir[c][p] = 0x7F
                if c == 2:
                    self.iodir[c][p] = (0x07 | ((~(self.spdir >> 1) & 0x0F) << 3)) if p else (0x3F | (0 if self.spdir & 1 else 0x40))
                self.put_dir(c, p)
        self.master = False; self.load_synced = False

    def expanders_init(self):
        self.spdir = 0
        for c in range(self.nchips): self.olat[c] = [0, 0]; self.gppu[c] = [0, 0x07 if c == 2 else 0]
        self.all_inputs()

    def walk_pulls(self, on):
        """the expanders' own pull-ups (100k) on every bus line, or off again (U3's DEBUG inputs keep theirs)"""
        for c in range(self.nchips):
            self.gppu[c][0] = BUSPINS[c][0] if on else 0; self.put_pu(c, 0)
            self.gppu[c][1] = (BUSPINS[c][1] if on else 0) | (0x07 if c == 2 else 0); self.put_pu(c, 1)

    # ---------------------------------------------------------------- BUSDRV-C: the clock on D9
    def clk_edge(self):
        self.clk ^= 1; self.bp.clock(self.clk)

    def clk_stop(self): self.clk_hz = 0

    def clk_start(self, hz):
        for pre in (1, 8, 64, 256, 1024):
            half = 16_000_000 // 2 // pre; top = (half + hz // 2) // hz
            if 1 <= top <= 65536: self.clk_hz = (half + top // 2) // top; return self.clk_hz
        return 0

    def run_clock(self, edges=CLOCK_EDGES_A_COMMAND):
        """the steady clock, for the simulated 1802: `edges` more of it (the real one runs by itself)"""
        for _ in range(edges): self.clk_edge()

    def clock_ours(self):
        last = self.gpio(2, 1) & 1
        for _ in range(8):
            self.clk_edge(); a = self.gpio(2, 1) & 1; b = self.gpio(2, 1) & 1
            if a == last or b != a: return False
            last = a
        return True

    # ---------------------------------------------------------------- bus primitives
    def set_bit(self, c, p, b, v):
        if v: self.olat[c][p] |= 1 << b
        else: self.olat[c][p] &= ~(1 << b) & 0xFF

    def sig_write(self, name, asserted):
        c, p, b, f = SIGS[name]
        level = (not asserted) if f & LOW_ACTIVE else asserted
        if f & OPEN_COLL:
            self.set_bit(c, p, b, False); self.put_lat(c, p)
            if level: self.iodir[c][p] |= 1 << b
            else: self.iodir[c][p] &= ~(1 << b) & 0xFF
            self.put_dir(c, p)
        else:
            self.set_bit(c, p, b, level); self.put_lat(c, p)

    sig = sig_write

    def addr_out(self, v):
        self.olat[0][1] = (self.olat[0][1] & 0x80) | (v & 0x7F); self.put_lat(0, 1)
        self.set_bit(1, 0, 1, v & 0x80); self.put_lat(1, 0)

    def data_dir(self, out):
        self.iodir[0][0] = 0x00 if out else 0x7F; self.put_dir(0, 0)
        if out: self.iodir[1][0] &= ~1 & 0xFF
        else: self.iodir[1][0] |= 1
        self.put_dir(1, 0)

    def data_out(self, v):
        self.olat[0][0] = (self.olat[0][0] & 0x80) | (v & 0x7F); self.put_lat(0, 0)
        self.set_bit(1, 0, 0, v & 0x80); self.put_lat(1, 0)

    def data_in(self): self.i2c_ops += 2; return self.bp.data_in()

    def bus_free(self):
        """may this card drive bus lines? Not with a CPU on the bus. -> None, or why not (MASTER:1# and WALK ask)"""
        if not self.bus_on: return "bus has no power"
        if self.cpu_running: return "TPA/TPB toggling: a CPU is running - pull the CPU card"
        if self.rev_c:
            if self.clk_hz: return "the clock is running: CLKSTOP:0# first"
            if self.clock_ours(): return "a CPU card answers on the DEBUG cable - pull the CPU card"
        return None

    def take_bus(self):
        why = self.bus_free()
        if why: return why
        self.olat[1][0] = (self.olat[1][0] & 0x80) | 0x70
        self.olat[1][1] = self.olat[1][1] & 0x80
        self.olat[0][1] &= 0x80; self.put_lat(0, 1); self.put_lat(1, 0); self.put_lat(1, 1)
        self.master = True                                  # (set before the directions here so _apply runs them)
        self.iodir[0][1] = 0x00; self.iodir[1][0] = 0x01; self.iodir[1][1] = 0x0E; self.iodir[0][0] = 0x7F
        self.put_dir(0, 0); self.put_dir(0, 1); self.put_dir(1, 0); self.put_dir(1, 1)
        self.load_synced = False
        return None

    def set_n(self, n):
        self.olat[1][1] = (self.olat[1][1] & 0x8F) | ((n & 7) << 4); self.put_lat(1, 1)

    def cycle_addr(self, a):
        self.addr_out(a >> 8); self.sig("TPA", 1); self.sig("TPA", 0)
        self.addr_out(a & 0xFF); self.sig("-VMA", 1)

    def mem_read(self, a):
        self.cycle_addr(a); self.data_dir(False)
        self.sig("-MRD", 1)
        if not self.legacy: self.sig("TPB", 1)              # the 6845's E: its bus port answers only while E is high
        v = self.data_in()
        if not self.legacy: self.sig("TPB", 0)
        self.sig("-MRD", 0); self.sig("-VMA", 0)
        return v

    def mem_write(self, a, v):
        self.cycle_addr(a); self.data_out(v); self.data_dir(True)
        self.sig("-MRW", 1)
        if not self.legacy: self.sig("TPB", 1); self.sig("TPB", 0)   # the 6845 latches on E falling, R/W still low
        self.sig("-MRW", 0)
        self.data_dir(False); self.sig("-VMA", 0)

    def io_out(self, n, b):
        if self.legacy:
            self.set_n(n); self.data_out(b); self.data_dir(True); self.sig("TPB", 1); self.sig("TPB", 0)
            self.data_dir(False); self.set_n(0); return
        self.data_out(b); self.data_dir(True)
        self.sig("-MRD", 1)                                 # OUT is a memory read on the 1802: -MRD low says "to the port"
        self.set_n(n); self.sig("TPA", 1); self.sig("TPA", 0); self.sig("TPB", 1); self.sig("TPB", 0)
        self.set_n(0); self.sig("-MRD", 0); self.data_dir(False)

    def io_inp(self, n):
        self.data_dir(False); self.set_n(n)
        if not self.legacy: self.sig("TPA", 1); self.sig("TPA", 0)
        self.sig("TPB", 1); d = self.data_in(); self.sig("TPB", 0); self.set_n(0)
        return d

    # ---------------------------------------------------------------- BUSDRV-C: the 1802's mode, LOAD mode by the clock
    def cpu_mode(self):
        return (0 if self.gpio(1, 1) & VB_RESET else 1) | (0 if self.gpio(2, 0) & WA_PAUSE else 2)

    def set_mode(self, m):
        self.load_synced = False
        if m == 2:
            self.sig("-RESET", 0)
            for _ in range(3000):                           # (the sketch: for half a second; here, 3000 expander reads)
                if self.gpio(1, 1) & VB_RESET: break
            else: return False
            self.sig("-PAUSE", 1); return True
        self.sig("-PAUSE", 0)
        self.sig("-RESET", m != 0)
        if m and not self.clk_hz:
            for _ in range(32): self.clk_edge()
        if m == 3: self.sig("-PAUSE", 1)
        return True

    def load_ready(self):
        if self.cpu_mode() != 3: self.why = "not in LOAD mode: MODE:3# first"; self.load_synced = False; return False
        if self.load_synced: return True
        self.clk_stop()
        if not self.clock_ours(): self.why = NO_CLOCK; return False
        rises = 0; last = self.gpio(1, 0)
        for _ in range(200):
            if rises >= 2: break
            self.clk_edge(); va = self.gpio(1, 0)
            if va & VA_TPA and not last & VA_TPA: rises += 1
            last = va
        if rises < 2: self.why = "no TPA from the 1802 in LOAD mode"; return False
        self.load_synced = True; return True

    def dma_byte(self, v):
        """-> the address written, or None with self.why set"""
        hi = lo = 0; low = done = False
        i = 0
        while i < 40 and not self.gpio(2, 0) & WA_SC0: self.clk_edge(); i += 1
        if i == 40: self.why = "SC0 stays low: DMA cycles with no request (-DMAIN held low?)"; return None
        self.sig("-DMAIN", 1)
        if self.load_fault == "early-data": self.data_out(v); self.data_dir(True)
        i = 0
        while i < 40:
            self.clk_edge()
            if not self.gpio(2, 0) & WA_SC0: break
            i += 1
        late = self.load_fault == "hold-dmain"              # (the sketch lets go here, at once, on every path)
        if not late: self.sig("-DMAIN", 0)
        if i == 40:
            if late: self.sig("-DMAIN", 0)
            self.why = "no DMA cycle: -DMAIN does not reach the 1802"; return None
        i = 0
        while i < 6:
            va = self.gpio(1, 0)
            if va & VA_MRD: break
            self.clk_edge(); i += 1
        if i == 6:
            if late: self.sig("-DMAIN", 0)
            self.why = "-MRD low in the DMA cycle"; return None
        self.data_out(v); self.data_dir(True)
        for i in range(40):
            if va & VA_TPA: hi = (self.gpio(0, 1) & 0x7F) | ((va & VA_A7) << 6)
            if not va & VA_MRW:
                if not low: lo = (self.gpio(0, 1) & 0x7F) | ((va & VA_A7) << 6)
                low = True
            elif low: done = True; break
            self.clk_edge(); va = self.gpio(1, 0)
        self.data_dir(False)
        if not done:
            if late: self.sig("-DMAIN", 0)
            self.why = "no -MRW pulse in the DMA cycle"; return None
        i = 0
        while i < 12:
            self.clk_edge()
            if self.gpio(2, 0) & WA_SC0: break
            i += 1
        if late: self.sig("-DMAIN", 0)                      # (too late: the 1802 has seen it at TPB again)
        if i == 12: self.why = "a second DMA cycle followed (-DMAIN held low?)"; self.load_synced = False; return None
        return (hi << 8) | lo

    # ---------------------------------------------------------------- reporting
    def snap_line(self):
        ua, ub, va, vb = self.gpio(0, 0), self.gpio(0, 1), self.gpio(1, 0), self.gpio(1, 1)
        d = (ua & 0x7F) | ((va & 1) << 7); a = (ub & 0x7F) | ((va & 2) << 6)
        s = "Data: D=%02X A=%02X TPA=%d TPB=%d -MRD=%d -MRW=%d -VMA=%d Q=%d N=%d -RESET=%d -INT=%d -EF=%d SP=%X" % (
            d, a, va >> 2 & 1, va >> 3 & 1, va >> 4 & 1, va >> 5 & 1, va >> 6 & 1, vb & 1, vb >> 4 & 7, vb >> 1 & 1, vb >> 2 & 1,
            vb >> 3 & 1, (self.olat[0][0] >> 7) | (self.olat[0][1] >> 7) << 1 | (self.olat[1][0] >> 7) << 2 | (self.olat[1][1] >> 7) << 3)
        if self.rev_c:
            wa, wb = self.gpio(2, 0), self.gpio(2, 1)
            s += " -EF1=%d -EF2=%d -EF3=%d -PAUSE=%d -DMAIN=%d SC0=%d DBG=%d%d%d S5=%02X" % (
                wa & 1, wa >> 1 & 1, wa >> 2 & 1, wa >> 3 & 1, wa >> 4 & 1, wa >> 5 & 1, wb & 1, wb >> 1 & 1, wb >> 2 & 1,
                (wa >> 6 & 1) | (wb >> 2 & 0x1E))
        return s

    # ---------------------------------------------------------------- BUSDRV-C's commands (the sketch's runC())
    def run_c(self, op, arg, v):
        if not self.rev_c: return [NEEDS_C]
        out = []
        if op == "MODE":
            if not 0 <= v <= 3: return ["Error: MODE 0 RUN, 1 RESET, 2 PAUSE, 3 LOAD"]
            if self.master: return ["Error: MODE is for a CPU card in place: MASTER:0# first"]
            if not self.set_mode(v): return ["Error: -RESET stays low (the CPU card's switch, another card): -PAUSE now would be LOAD"]
        elif op in ("DMA", "LOADBLK"):
            parts = arg.split(","); count = 1 if op == "DMA" else v
            if self.master: return ["Error: LOAD mode is for a CPU card in place: MASTER:0# first"]
            if op == "DMA":
                if not 0 <= v <= 255: return ["Error: value 0..255"]
                data = [v]
            else:
                hx = parts[1] if len(parts) > 1 else ""
                if not 1 <= count <= WBLOCK_MAX or len(parts) < 2 or len(hx) < 2 * count:
                    return ["Error: LOADBLK:count,hh.. count 1..32, 2 hex digits per byte"]
                try: data = [int(hx[2 * i:2 * i + 2], 16) for i in range(count)]
                except ValueError: return ["Error: bad hex in LOADBLK"]
            if not self.load_ready(): return ["Error: " + self.why]
            first = 0
            for i, b in enumerate(data):
                a = self.dma_byte(b)
                if a is None: return ["Error: byte %d: %s" % (i, self.why)]
                if i == 0: first = a
                elif a != (first + i) & 0xFFFF: return ["Error: byte %d went to %04X, not the next address" % (i, a)]
            out.append("Data: %04X" % first if op == "DMA" else "Data: %d %04X" % (count, first))
        elif op == "CLKHZ":
            if not 1 <= v <= 2000000: return ["Error: CLKHZ 1..2000000 (the cards are timed for 2 MHz)"]
            self.load_synced = False; out.append("Data: %d" % self.clk_start(v))
        elif op == "CLKSTOP": self.clk_stop()
        elif op == "PROBE": out.append("Data: P1=%d P2=%d" % (self.bp.probe_in(1), self.bp.probe_in(2)))
        elif op == "PCOUNT":
            if not 1 <= v <= 10000: return ["Error: PCOUNT 1..10000 ms"]
            t = self.bp.transitions; names = [self.bp.probe.get(k) for k in (1, 2)]; before = [t.get(n, 0) for n in names]
            if self.clk_hz: self.run_clock()                # (the simulator's stand-in for ms of a running clock)
            out.append("Data: P1=%d P2=%d" % tuple(t.get(n, 0) - b for n, b in zip(names, before)))
        elif op in ("PTIME", "PDELAY"):
            if self.clk_hz: return ["Error: Timer 1 is making the clock: CLKSTOP:0# first"]
            if op == "PTIME": return ["Error: no rising-falling-rising on PROBE1 in that time"]   # (nothing moves by itself here)
            before = self.bp.probe_in(1); self.clk_edge(); self.load_synced = False; now = self.bp.probe_in(1)
            if now == before or now != (1 if v else 0): return ["Error: no such edge on PROBE1 within 4 ms of the clock edge"]
            out.append("Data: 0")                           # (the simulator has no time: the real card gives ns)
        elif op == "DBG":
            if v:
                if self.clk_hz: return ["Error: the clock is running: CLKSTOP:0# first"]
                self.load_synced = False
                if not self.clock_ours(): return ["Error: " + NO_CLOCK]
                out.append("Data: CLK OUT reaches the 1802")
            else:
                wb = self.gpio(2, 1); out.append("Data: CLOCK=%d SC0=%d SC1=%d" % (wb & 1, wb >> 1 & 1, wb >> 2 & 1))
        elif op == "SPDIR":
            self.spdir = v & 0x1F
            self.iodir[2][0] = (self.iodir[2][0] & 0xBF) | (0 if self.spdir & 1 else 0x40)
            self.iodir[2][1] = (self.iodir[2][1] & 0x87) | ((~(self.spdir >> 1) & 0x0F) << 3)
            self.put_dir(2, 0); self.put_dir(2, 1)
        else:                                               # SPIN
            out.append("Data: %d" % ((self.gpio(2, 0) >> 6 & 1) | (self.gpio(2, 1) >> 2 & 0x1E)))
        return out + ["Complete"]

    # ---------------------------------------------------------------- commands (the sketch's run())
    def run(self, c):
        op, colon, arg = c.partition(":")
        if not colon: return ["Error: format is CMD:OPERAND#"]
        try: v = int(arg.split(",")[0] or 0)
        except ValueError: v = 0
        no_master = op in ("HELP", "STATUS", "MASTER", "SNAP", "WATCH", "SPARE", "XRST", "RD-ADDRBUS", "RD-DATABUS", "DATABUS-RD-MODE", "WALK")
        if not self.bus_on and op not in ("HELP", "STATUS"): return ["Error: bus has no power"]
        if self.clk_hz and op != "CLKSTOP": self.run_clock()     # (the steady clock has been running meanwhile)
        if op in C_COMMANDS: return self.run_c(op, arg, v)
        if op in SIGS and SIGS[op][0] >= self.nchips: return [NEEDS_C]
        if op in SIGS and SIGS[op][3] & OPEN_COLL: no_master = True   # clk-1: pulling an open-collector line is safe with a CPU
        if op == "CLK": no_master = True
        if not no_master and not self.master: return ["Error: MONITOR mode: send MASTER:1# first (CPU card out)"]
        out = []
        if op == "HELP": out.append("(simulated) see the sketch header")
        elif op == "STATUS":
            s = "Data: bus=%s mode=%s" % ("on" if self.bus_on else "off", "MASTER" if self.master else "MONITOR")
            if self.bus_on and self.rev_c: s += " board=C cpu=%s clk=%d" % (MODE_NAMES[self.cpu_mode()], self.clk_hz)
            out.append(s)
        elif op == "MASTER":
            if v:
                why = self.take_bus()
                if why: return ["Error: " + why]
            else: self.all_inputs()
        elif op == "SNAP": out.append(self.snap_line())
        elif op in SIGS:
            self.sig(op, v != 0)
            if SIGS[op][0] == 2 or op == "-RESET": self.load_synced = False
        elif op == "N": self.set_n(v)
        elif op == "WR-ADDRBUS": self.addr_out(v)
        elif op == "RD-ADDRBUS": out.append("Data: %d" % ((self.gpio(0, 1) & 0x7F) | ((self.gpio(1, 0) & 2) << 6)))
        elif op == "WR-DATABUS": self.data_out(v); self.data_dir(True)
        elif op == "RD-DATABUS": out.append("Data: %d" % self.data_in())
        elif op == "DATABUS-RD-MODE":
            if self.master: self.data_dir(False)
        elif op == "RDMEM":
            if not 0 <= v <= 65535: return ["Error: addr 0..65535"]
            out.append("Data: %d" % self.mem_read(v))
        elif op in ("WRMEM", "OUT"):
            if "," not in arg: return ["Error: needs a,b"]
            a, b = (int(x) for x in arg.split(",")[:2])
            if not 0 <= b <= 255: return ["Error: value 0..255"]
            if op == "WRMEM":
                if not 0 <= a <= 65535: return ["Error: addr 0..65535"]
                self.mem_write(a, b)
            else:
                if not 1 <= a <= 7: return ["Error: port 1..7"]
                self.io_out(a, b)
        elif op == "INP":
            if not 1 <= v <= 7: return ["Error: port 1..7"]
            out.append("Data: %d" % self.io_inp(v))
        elif op in ("RDBLK", "WRBLK"):
            parts = arg.split(",")
            if len(parts) < 2: return ["Error: block needs addr,count"]
            addr, count = int(parts[0]), int(parts[1])
            if not (0 <= addr <= 65535 and 1 <= count <= BLOCK_MAX and addr + count <= 65536): return ["Error: block addr 0..65535, count 1..64"]
            if op == "WRBLK":
                if count > WBLOCK_MAX: return ["Error: WRBLK count 1..32"]
                hx = parts[2] if len(parts) > 2 else ""
                if len(hx) < 2 * count: return ["Error: WRBLK needs 2 hex digits per byte"]
                for i in range(count): self.mem_write(addr + i, int(hx[2 * i:2 * i + 2], 16))
                out.append("Data: %d" % count)
            else:
                out.append("Data:" + "".join(" %02X" % self.mem_read(addr + i) for i in range(count)))
        elif op in ("INBLK", "OUTBLK"):
            parts = arg.split(",")
            if len(parts) < 2: return ["Error: needs port,count"]
            n, count = int(parts[0]), int(parts[1])
            if not 1 <= n <= 7: return ["Error: port 1..7"]
            if not 1 <= count <= (BLOCK_MAX if op == "INBLK" else WBLOCK_MAX): return ["Error: INBLK count 1..64, OUTBLK 1..32"]
            if op == "OUTBLK":
                hx = parts[2] if len(parts) > 2 else ""
                if len(hx) < 2 * count: return ["Error: OUTBLK needs 2 hex digits per byte"]
                for i in range(count): self.io_out(n, int(hx[2 * i:2 * i + 2], 16))
                out.append("Data: %d" % count)
            else:
                out.append("Data:" + "".join(" %02X" % self.io_inp(n) for _ in range(count)))
        elif op == "SPARE":
            for k, (c, p) in enumerate(((0, 0), (0, 1), (1, 0), (1, 1))): self.set_bit(c, p, 7, v >> k & 1)
            if self.rev_c:
                self.olat[2][0] = (v >> 4 & 1) << 6 | (v >> 9 & 1) << 7; self.olat[2][1] = (v >> 5 & 0x0F) << 3 | (v >> 10 & 1) << 7
        elif op == "CLK":
            if self.master: return ["Error: CLK is for MONITOR mode (the CPU card drives the bus)"]
            if v < 1: return ["Error: CLK:n, n >= 1"]
            if not self.rev_c:                # clk-1: SPARE1 steps CPU Rev A's clock; the 30-pin backplane has no CPU card
                out.append("Data: %d" % v)
            else:                             # clk-2: every edge is one change of CLK OUT, and the bus is read after it
                self.clk_stop(); self.load_synced = False; last = None
                for e in range(1, v + 1):
                    self.clk_edge(); now = [self.gpio(c, p) for c in range(3) for p in range(2)]
                    now[5] &= 0xFE                # (the DEBUG cable's CLOCK changes on every edge: left out)
                    if now != last: out.append("T %d %s" % (e, " ".join("%02X" % x for x in now))); last = now
                out.append("Data: %d" % v)
        elif op in ("XRST", "WATCH"):
            if op == "XRST": self.expanders_init()
        elif op == "WALK":
            parts = arg.split(",")
            try: lv = int(parts[1]) if len(parts) > 1 else 2
            except ValueError: lv = 0                       # (the sketch's toInt)
            c, p, b = v >> 4 & 0x0F, v >> 3 & 1, v & 7
            if not 0 <= v <= 47 or c >= self.nchips or not BUSPINS[c][p] >> b & 1 or not 0 <= lv <= 2:
                return ["Error: WALK:pin,level  pin = chip*16 + port*8 + bit of a bus line; level 0, 1, or 2 (drive nothing)"]
            if lv == 1 and OCPINS[c][p] >> b & 1: return ["Error: an open-collector line is only ever pulled low: WALK level 0 or 2"]
            if self.master: return ["Error: WALK is for MONITOR mode: MASTER:0# first"]
            self.walk_pulls(True)                           # on before the look for a CPU, as in the sketch
            why = self.bus_free()
            if why: self.walk_pulls(False); return ["Error: " + why]
            held = lv < 2; dir0, lat0 = self.iodir[c][p], self.olat[c][p]
            if held:
                self.set_bit(c, p, b, lv); self.put_lat(c, p)
                self.iodir[c][p] &= ~(1 << b) & 0xFF; self.put_dir(c, p)
                if self.gpio(c, p) >> b & 1 != lv and self.load_fault != "walk-hold":   # it does not follow: let go at once
                    self.iodir[c][p] |= 1 << b; self.put_dir(c, p); held = False
            now = [self.gpio(cc, pp) for cc in range(self.nchips) for pp in range(2)]
            if lv < 2:                                      # the pin as it was before: an input (a line this card holds
                if dir0 >> b & 1: self.iodir[c][p] |= 1 << b; self.put_dir(c, p)    # low stays low all through)
                self.olat[c][p] = lat0; self.put_lat(c, p)
                if self.iodir[c][p] != dir0: self.iodir[c][p] = dir0; self.put_dir(c, p)
            self.walk_pulls(False)
            out.append("Data: " + " ".join("%02X" % x for x in now))
        else: return ["Error: Bad opcode"]
        return out + ["Complete"]


class FwCard:
    """the serial side: what s5busdrv.BusDriver reads and writes"""
    def __init__(self, backplane, **kw):
        self.fw = Firmware(backplane, **kw); self.rx = ""; self.out_buf = bytearray()
        self._emit([LEGACY_BANNER if self.fw.legacy else BANNER_C if self.fw.rev_c else BANNER, ">>"])

    def write(self, b):
        self.rx += b.decode("ascii")
        while "#" in self.rx:
            c, self.rx = self.rx.split("#", 1); self.fw.bp.context = c[:40]; self._emit(self.fw.run(c) + [">>"])

    def read(self, n=1):
        b = bytes(self.out_buf[:n]); del self.out_buf[:n]; return b

    def reset_input_buffer(self): pass
    def _emit(self, lines): self.out_buf += ("\r\n".join(lines) + "\r\n").encode()
