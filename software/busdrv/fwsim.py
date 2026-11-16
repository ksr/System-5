# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-11
"""The bus driver firmware (embedded/bus-driver/s5-bus-driver/s5-bus-driver.ino) in Python, driving a Backplane.

The functions below follow the sketch line for line: the same expander register shadows (olat, iodir), the same
port writes in the same order. Every port write is one I2C transaction on the real card, so each one changes the bus
pins here too (Backplane.set_pins), and the cards see every in-between state the real card produces.
Keep it in step with the sketch: a change to a bus cycle there must be made here as well.

legacy=True runs the bus cycles as the sketch had them before 2026-10-11 (no TPB in memory cycles; OUT/INP without
-MRD or TPA), to show what they did wrong.

FwCard wraps it in the serial wire protocol, so s5busdrv.BusDriver(transport=FwCard(...)) talks to it exactly as it
talks to the real card.
"""
BANNER = "s5-bus-driver blocks-1 io-2 clk-1 2026-10-31 (SIMULATED)"
LEGACY_BANNER = "s5-bus-driver blocks-1 2026-10-06 (SIMULATED, the old bus cycles)"
BLOCK_MAX, WBLOCK_MAX = 64, 32

# (chip, port, bit, flags) as in the sketch's SIGS table
LOW_ACTIVE, OPEN_COLL = 1, 2
SIGS = {"TPA": (1, 0, 2, 0), "TPB": (1, 0, 3, 0), "-MRD": (1, 0, 4, LOW_ACTIVE), "-MRW": (1, 0, 5, LOW_ACTIVE),
        "-VMA": (1, 0, 6, LOW_ACTIVE), "Q": (1, 1, 0, 0), "-RESET": (1, 1, 1, LOW_ACTIVE | OPEN_COLL),
        "-INT": (1, 1, 2, LOW_ACTIVE | OPEN_COLL), "-EF": (1, 1, 3, LOW_ACTIVE | OPEN_COLL)}
PIN_OF = {"TPA": "TPA", "TPB": "TPB", "-MRD": "MRD", "-MRW": "MRW", "-VMA": "VMA", "Q": "Q", "-RESET": "RESET",
          "-INT": "INT", "-EF": "EF"}


class Firmware:
    def __init__(self, backplane, bus_on=True, cpu_running=False, legacy=False):
        self.bp, self.bus_on, self.cpu_running, self.legacy = backplane, bus_on, cpu_running, legacy
        self.olat = [[0, 0], [0, 0]]; self.iodir = [[0xFF, 0xFF], [0xFF, 0xFF]]; self.master = False
        self.i2c_ops = 0
        if bus_on: self.expanders_init()

    # ---------------------------------------------------------------- MCP23017 access -> bus pins
    def _apply(self):
        """what the expanders put on the bus now; nothing is driven until the card is master"""
        self.i2c_ops += 1
        if not self.master and all(d == 0x7F for row in self.iodir for d in row): return
        def out(c, p, b):
            return None if (self.iodir[c][p] >> b) & 1 else (self.olat[c][p] >> b) & 1
        pins = {}
        for name, (c, p, b, f) in SIGS.items(): pins[PIN_OF[name]] = out(c, p, b)
        a = [out(0, 1, i) for i in range(7)] + [out(1, 0, 1)]
        pins["A"] = None if None in a else sum(v << i for i, v in enumerate(a))
        n = [out(1, 1, 4 + i) for i in range(3)]
        pins["N"] = None if None in n else sum(v << i for i, v in enumerate(n))
        d = [out(0, 0, i) for i in range(7)] + [out(1, 0, 0)]
        dd = None if None in d else sum(v << i for i, v in enumerate(d))
        self.bp.set_pins(pins, dd)

    def put_lat(self, c, p): self._apply()
    def put_dir(self, c, p): self._apply()

    def all_inputs(self):
        for c in range(2):
            for p in range(2): self.iodir[c][p] = 0x7F; self.put_dir(c, p)
        self.master = False

    def expanders_init(self):
        for c in range(2): self.olat[c] = [0, 0]
        self.all_inputs()

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

    def take_bus(self):
        if not self.bus_on: return "bus has no power"
        if self.cpu_running: return "TPA/TPB toggling: a CPU is running - pull the CPU card"
        self.olat[1][0] = (self.olat[1][0] & 0x80) | 0x70
        self.olat[1][1] = self.olat[1][1] & 0x80
        self.olat[0][1] &= 0x80; self.put_lat(0, 1); self.put_lat(1, 0); self.put_lat(1, 1)
        self.master = True                                  # (set before the directions here so _apply runs them)
        self.iodir[0][1] = 0x00; self.iodir[1][0] = 0x01; self.iodir[1][1] = 0x0E; self.iodir[0][0] = 0x7F
        self.put_dir(0, 0); self.put_dir(0, 1); self.put_dir(1, 0); self.put_dir(1, 1)
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

    # ---------------------------------------------------------------- commands (the sketch's run())
    def run(self, c):
        op, colon, arg = c.partition(":")
        if not colon: return ["Error: format is CMD:OPERAND#"]
        try: v = int(arg.split(",")[0] or 0)
        except ValueError: v = 0
        no_master = op in ("HELP", "STATUS", "MASTER", "SNAP", "WATCH", "SPARE", "XRST", "RD-ADDRBUS", "RD-DATABUS", "DATABUS-RD-MODE")
        if op in SIGS and SIGS[op][3] & OPEN_COLL: no_master = True   # clk-1: pulling an open-collector line is safe with a CPU
        if op == "CLK": no_master = True
        if not self.bus_on and op not in ("HELP", "STATUS"): return ["Error: bus has no power"]
        if not no_master and not self.master: return ["Error: MONITOR mode: send MASTER:1# first (CPU card out)"]
        out = []
        if op == "HELP": out.append("(simulated) see the sketch header")
        elif op == "STATUS": out.append("Data: bus=%s mode=%s" % ("on" if self.bus_on else "off", "MASTER" if self.master else "MONITOR"))
        elif op == "MASTER":
            if v:
                why = self.take_bus()
                if why: return ["Error: " + why]
            else: self.all_inputs()
        elif op == "SNAP":
            p = self.bp.pins or {}; g = lambda k, d=1: d if p.get(k) is None else p[k]
            out.append("Data: D=%02X A=%02X TPA=%d TPB=%d -MRD=%d -MRW=%d -VMA=%d Q=%d N=%d -RESET=%d -INT=%d -EF=%d SP=0" % (
                self.bp.data_in(), g("A", 0xFF), g("TPA", 0), g("TPB", 0), g("MRD"), g("MRW"), g("VMA"), g("Q", 0), g("N", 0),
                g("RESET"), g("INT"), g("EF")))
        elif op in SIGS: self.sig(op, v != 0)
        elif op == "N": self.set_n(v)
        elif op == "WR-ADDRBUS": self.addr_out(v)
        elif op == "RD-ADDRBUS": out.append("Data: %d" % ((self.bp.pins or {}).get("A") or 0xFF))
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
        elif op == "CLK":                     # clk-1: steps a CPU card's clock; the simulated backplane has no CPU card
            if self.master: return ["Error: CLK is for MONITOR mode (the CPU card drives the bus)"]
            if v < 1: return ["Error: CLK:n, n >= 1"]
            out.append("Data: %d" % v)
        elif op in ("SPARE", "XRST", "WATCH"):
            if op == "XRST": self.expanders_init()
        else: return ["Error: Bad opcode"]
        return out + ["Complete"]


class FwCard:
    """the serial side: what s5busdrv.BusDriver reads and writes"""
    def __init__(self, backplane, **kw):
        self.fw = Firmware(backplane, **kw); self.rx = ""; self.out_buf = bytearray()
        self._emit([LEGACY_BANNER if self.fw.legacy else BANNER, ">>"])

    def write(self, b):
        self.rx += b.decode("ascii")
        while "#" in self.rx:
            c, self.rx = self.rx.split("#", 1); self.fw.bp.context = c[:40]; self._emit(self.fw.run(c) + [">>"])

    def read(self, n=1):
        b = bytes(self.out_buf[:n]); del self.out_buf[:n]; return b

    def reset_input_buffer(self): pass
    def _emit(self, lines): self.out_buf += ("\r\n".join(lines) + "\r\n").encode()
