#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-06. After the YACC1 tools/busdrv.py.
"""Host tool for the System-5 bus driver cards (BUSDRV-B and BUSDRV-C, firmware embedded/bus-driver/s5-bus-driver).

Wire protocol: host sends CMD:OPERAND#, the card answers with optional "Data: ..." lines, "Complete" or "Error: ...",
then the ">>" prompt. See the sketch header for the command list.

Usage (port auto-detected: the Nano's USB serial; --port to choose, --sim to run against a simulated card):
  s5busdrv.py status                      bus power and mode
  s5busdrv.py master on|off               take / give up the bus (pull the CPU card first)
  s5busdrv.py snap | watch [ms]           bus lines now / on every change
  s5busdrv.py peek ADDR [N]               read N bytes (hex dump)
  s5busdrv.py poke ADDR BYTE [BYTE...]    write bytes
  s5busdrv.py dump ADDR LEN               hex dump of LEN bytes
  s5busdrv.py load FILE [ADDR]            .hex (Intel hex, addresses from the file) or .bin (at ADDR); verified
  s5busdrv.py save ADDR LEN FILE          read LEN bytes to a binary file
  s5busdrv.py memtest START END           RAM test: address-in-address, walking ones, 55/AA (destroys contents)
  s5busdrv.py out PORT BYTE | inp PORT    1802 OUT / INP on N=PORT (1..7)
  s5busdrv.py spare MASK | xrst | cmd TEXT
  s5busdrv.py walk [LINE low|high]        the short finder's one step (CPU card out): LINE driven alone for a moment, every
                                          other bus pin an input with the expander's 100k pull-up on; the lines that
                                          moved with it. No LINE: every line at rest. bringup.py's plan "shorts" walks
                                          them all and names the shorts.
Numbers accept 0x.. / $.. / plain decimal. "master on" is needed before memory and I/O commands; the tool turns it
on for them when --auto-master is given.

BUSDRV-C only (the 36-pin card; --sim --rev C simulates one with CPU Rev D and a memory card). These work with the
CPU card in place, the DEBUG cable joining the two cards and the CPU card's JP1 on EXT:
  s5busdrv.py mode run|reset|pause|load   the 1802's mode, by -RESET and -PAUSE
  s5busdrv.py dmaload FILE [ADDR]         LOAD mode: the file into RAM from 0000 by DMA IN, the clock stepped by the
                                          card; leaves the machine in LOAD mode. A file that does not start at 0000 gets
                                          zeros below it and a jump to its start at 0000.
  s5busdrv.py loadrun FILE [ADDR] [HZ]    dmaload, then RUN with the card's clock at HZ (default 2000000; 0 = leave
                                          the clock stopped, for "clk N")
  s5busdrv.py clkhz HZ | clkstop          the card's clock on CLK OUT, steady or stopped
  s5busdrv.py clk N [--cycles]            N clock edges (16 = one machine cycle); the bus changes they made, or with
                                          --cycles one line a machine cycle (address, R/W, data), as cputrace.py
  s5busdrv.py dbg | clktest               the DEBUG cable's CLOCK, SC0, SC1; does CLK OUT reach the 1802?
  s5busdrv.py line NAME on|off            pull an open-collector line low, or let it go: -EF1 -EF2 -EF3 -PAUSE -DMAIN
                                          (and -RESET -INT -EF)
  s5busdrv.py probe | pcount MS | ptime [MS] | pdelay 0|1     the two probe inputs: levels, edge counts, PROBE1's
                                          period and high time, the time from a clock edge to PROBE1's next edge
  s5busdrv.py spdir MASK | spin           SPARE5-9: which are outputs; their levels
"""
import sys, os, time, glob, argparse

BAUD = 115200
# Every bus line's expander pin, for WALK: pin = chip * 16 + port * 8 + bit (U1 = chip 0, U2 = 1, U3 = 2; port A = 0).
# U1: D0-D6 on GPA0-6, A0-A6 on GPB0-6. U2: D7 A7 TPA TPB -MRD -MRW -VMA on GPA0-6, Q -RESET -INT -EF N0 N1 N2 on GPB0-6.
# U3 (BUSDRV-C): -EF1 -EF2 -EF3 -PAUSE -DMAIN SC0 on GPA0-5.
WALK_PINS = dict([("D%d" % i, i) for i in range(7)] + [("D7", 16)] + [("A%d" % i, 8 + i) for i in range(7)] + [("A7", 17)] +
                 [("TPA", 18), ("TPB", 19), ("-MRD", 20), ("-MRW", 21), ("-VMA", 22), ("Q", 24), ("-RESET", 25),
                  ("-INT", 26), ("-EF", 27), ("N0", 28), ("N1", 29), ("N2", 30),
                  ("-EF1", 32), ("-EF2", 33), ("-EF3", 34), ("-PAUSE", 35), ("-DMAIN", 36), ("SC0", 37)])
OPEN_COLLECTOR = ("-RESET", "-INT", "-EF", "-EF1", "-EF2", "-EF3", "-PAUSE", "-DMAIN")


def num(s):
    s = str(s).strip()
    if s.startswith("$"): return int(s[1:], 16)
    return int(s, 0)


class CardError(RuntimeError):
    pass


class BusDriver:
    """One System-5 bus driver card on a serial port (or a SimCard when transport is given)."""
    retries = 3

    def __init__(self, port=None, baud=BAUD, log=None, timeout=5.0, transport=None):
        self.log = log; self.timeout = timeout; self.banner = []
        if transport is not None:
            self.ser = transport
        else:
            import serial
            port = port or find_port()
            self.ser = serial.Serial(port, baud, timeout=0.1)
        self.wait_prompt(timeout=10)                       # the Nano resets when the port opens
        if not any("s5-bus-driver" in l for l in self.banner):
            raise CardError("no System-5 bus driver banner (got %r)" % self.banner)
        self.blocks = any("blocks-" in l for l in self.banner)
        self.ioblocks = any("io-2" in l for l in self.banner)       # firmware 2026-10-11: INBLK/OUTBLK, fixed I/O cycles
        self.walkable = any("walk-1" in l for l in self.banner)     # firmware 2026-11-21: WALK, one line driven alone
        self.lines = []                                             # every line of the last answer
        # the board: BUSDRV-C says so in its banner, or (the bus was off when the Nano started) in STATUS
        self.rev = "C" if any("BUSDRV-C" in l for l in self.banner) else "B" if any("BUSDRV-B" in l for l in self.banner) else None

    # ---- protocol
    def _readline(self, deadline):
        buf = b""
        while time.time() < deadline:
            c = self.ser.read(1)
            if not c: continue
            if c in b"\r\n":
                if buf: return buf.decode("ascii", "replace")
                continue
            buf += c
            if buf.endswith(b">>"): return buf.decode("ascii", "replace")
        raise TimeoutError("no reply from the card (partial %r)" % buf)

    def wait_prompt(self, timeout=None):
        deadline = time.time() + (timeout or self.timeout); lines = []
        while True:
            line = self._readline(deadline)
            if self.log: self.log.write("  < %s\n" % line)
            if line.strip().endswith(">>"):
                if not self.banner and lines: self.banner = list(lines)
                return lines
            lines.append(line)

    def cmd(self, op, operand=0, timeout=None):
        """send OP:OPERAND#; return the list of 'Data:' payload strings. Raises CardError on 'Error:'."""
        msg = "%s:%s#" % (op, operand)
        for attempt in range(self.retries + 1):
            try:
                if self.log: self.log.write("> %s\n" % msg)
                self.ser.reset_input_buffer(); self.ser.write(msg.encode("ascii"))
                lines = self.wait_prompt(timeout); break
            except TimeoutError:
                if attempt == self.retries: raise
                time.sleep(0.3)
        data = []; self.lines = lines
        for l in lines:
            if l.startswith("Error"): raise CardError("%s -> %s" % (msg if len(msg) < 60 else msg[:57] + "...", l))
            if l.startswith("Data:"): data.append(l.split(":", 1)[1].strip())
        return data

    def value(self, op, operand=0):
        d = self.cmd(op, operand); return int(d[0]) if d else None

    # ---- card state
    def status(self):
        return self.cmd("STATUS")[0]

    def master(self, on=True):
        self.cmd("MASTER", 1 if on else 0)

    def snap(self):
        return self.cmd("SNAP")[0]

    # ---- one line at a time: the short finder's step (WALK)
    def walk_lines(self):
        """the bus lines this card reaches, in expander order: 28 on BUSDRV-B, 34 on BUSDRV-C"""
        top = 48 if self.board() == "C" else 32
        return [n for n, p in WALK_PINS.items() if p < top]

    def walk(self, line=None, level=0):
        """`line` driven alone to `level` (0 or 1) for a moment, every other bus pin an input with its expander's pull-up
        (100k) on; no line: nothing driven, every line at rest. CPU card out. -> {line: the level read}. A line that
        does not reach its level is let go at once by the card, and reads as it rests."""
        d = self.cmd("WALK", "%d,%d" % (WALK_PINS[line] if line else 0, 2 if line is None else level))[0]
        ports = [int(h, 16) for h in d.split()]
        return {n: ports[p >> 3] >> (p & 7) & 1 for n, p in WALK_PINS.items() if p >> 3 < len(ports)}

    # ---- memory
    def read(self, addr, n):
        out = bytearray()
        while n > 0:
            k = min(n, 64)
            if self.blocks:
                out += bytes(int(h, 16) for h in self.cmd("RDBLK", "%d,%d" % (addr, k))[0].split())
            else:
                out += bytes(self.value("RDMEM", addr + i) for i in range(k))
            addr += k; n -= k
        return bytes(out)

    def write(self, addr, data):
        data = bytes(data); i = 0
        while i < len(data):
            chunk = data[i:i + 32]
            if self.blocks:
                self.cmd("WRBLK", "%d,%d,%s" % (addr + i, len(chunk), chunk.hex().upper()))
            else:
                for j, b in enumerate(chunk): self.cmd("WRMEM", "%d,%d" % (addr + i + j, b))
            i += len(chunk)

    def out(self, port, val):
        self.cmd("OUT", "%d,%d" % (port, val))

    def inp(self, port):
        return self.value("INP", port)

    def inp_block(self, port, n):
        """n INPs from one port (a CF sector: 512 from the data port)"""
        out = bytearray()
        while n > 0:
            k = min(n, 64)
            if self.ioblocks: out += bytes(int(h, 16) for h in self.cmd("INBLK", "%d,%d" % (port, k))[0].split())
            else: out += bytes(self.inp(port) for _ in range(k))
            n -= k
        return bytes(out)

    def out_block(self, port, data):
        data = bytes(data)
        for i in range(0, len(data), 32):
            chunk = data[i:i + 32]
            if self.ioblocks: self.cmd("OUTBLK", "%d,%d,%s" % (port, len(chunk), chunk.hex().upper()))
            else:
                for b in chunk: self.out(port, b)

    # ---- BUSDRV-C: the 36-pin extension, the 1802's mode, LOAD mode by the clock, the clock, the probes
    MODES = ("RUN", "RESET", "PAUSE", "LOAD", "BOOT")      # BOOT: firmware mode-2 (2026-11-22), a boot reset

    def board(self):
        """'B' or 'C' (None: the bus is off, so the card cannot tell yet)"""
        if self.rev is None and "board=C" in self.status(): self.rev = "C"
        return self.rev

    def fields(self, text):
        """'a=1 b=x' -> {'a': '1', 'b': 'x'}"""
        return dict(f.split("=", 1) for f in text.split() if "=" in f)

    def mode(self, name):
        """the 1802's mode: run, reset, pause or load; or boot, a boot reset (-RESET and -DMAIN low with -PAUSE high:
        CPU Rev D clears its LOADED flag, so mode('run') after it starts the machine in the EPROM)"""
        n = self.MODES.index(name.upper())
        if n == 4 and not any("mode-2" in l for l in self.banner):
            raise CardError("MODE BOOT needs firmware mode-2 (2026-11-22) or later")
        self.cmd("MODE", n)

    def cpu_mode(self):
        """the mode as -RESET and -PAUSE stand on the bus (another card may hold them too)"""
        return self.fields(self.status()).get("cpu")

    def line(self, name, on):
        """an open-collector line: on = pulled low"""
        self.cmd(name, 1 if on else 0)

    def dma(self, byte):
        """LOAD mode: one byte to M(R(0)); -> the address it went to"""
        return int(self.cmd("DMA", byte & 0xFF, timeout=20)[0], 16)

    def dma_load(self, data, progress=None):
        """LOAD mode: the bytes to M(R(0)) on, 32 to a command; -> the address of the first. The card reads the
        address of every write off the bus and refuses a block that does not run on from one to the next; this checks
        the blocks against each other."""
        data = bytes(data); first = None; i = 0
        while i < len(data):
            chunk = data[i:i + 32]
            n, a = self.cmd("LOADBLK", "%d,%s" % (len(chunk), chunk.hex().upper()), timeout=30)[0].split(); a = int(a, 16)
            if first is None: first = a
            elif a != (first + i) & 0xFFFF:
                raise CardError("LOADBLK: the block of byte %d went to %04X, not %04X" % (i, a, (first + i) & 0xFFFF))
            i += len(chunk)
            if progress: progress(i, len(data))
        return first

    def clk_hz(self, hz):
        """a steady clock on CLK OUT; -> the rate the card could make"""
        return int(self.cmd("CLKHZ", int(hz))[0])

    def clk_stop(self): self.cmd("CLKSTOP")

    def clk(self, edges):
        """`edges` clock edges; -> [(edge, [the GPIO ports, hex])] for every change of the bus"""
        out = []; left = edges; base = 0
        while left > 0:
            k = min(left, 20000); self.cmd("CLK", k, timeout=30 + k / 50)
            for l in self.lines:
                if l.startswith("T "):
                    _, e, *h = l.split(); out.append((base + int(e), [int(x, 16) for x in h]))
            base += k; left -= k
        return out

    def dbg(self): return self.fields(self.cmd("DBG", 0)[0])
    def clock_test(self): return self.cmd("DBG", 1)[0]
    def probe(self): return {k: int(v) for k, v in self.fields(self.cmd("PROBE")[0]).items()}
    def pcount(self, ms): return {k: int(v) for k, v in self.fields(self.cmd("PCOUNT", int(ms), timeout=ms / 1000 + 5)[0]).items()}
    def ptime(self, ms=1000): return {k: int(v) for k, v in self.fields(self.cmd("PTIME", int(ms), timeout=ms / 1000 + 5)[0]).items()}
    def pdelay(self, rising): return int(self.cmd("PDELAY", 1 if rising else 0)[0])


def load_image(runs):
    """[(addr, bytes)] -> the bytes LOAD mode must send, from 0000 up. LOAD mode fills memory from 0000 only, and RUN
    starts there; so a file that begins higher gets zeros below it and, at 0000, a long branch (C0 hh ll) to its start."""
    runs = sorted(runs); end = max(a + len(d) for a, d in runs); img = bytearray(end); start = runs[0][0]
    for a, d in runs: img[a:a + len(d)] = d
    if start >= 3: img[0:3] = bytes([0xC0, start >> 8, start & 0xFF])
    elif start: raise SystemExit("the file starts at %04X: no room below it for a jump at 0000" % start)
    return bytes(img)


def find_port():
    pats = ["/dev/cu.usbserial*", "/dev/cu.wchusbserial*", "/dev/cu.usbmodem*", "/dev/ttyUSB*", "/dev/ttyACM*"]
    for p in pats:
        hits = sorted(glob.glob(p))
        if hits: return hits[0]
    raise SystemExit("no USB serial port found: plug the Nano in or give --port")


def hexdump(addr, data):
    for i in range(0, len(data), 16):
        row = data[i:i + 16]
        print("%04X  %-48s %s" % (addr + i, " ".join("%02X" % b for b in row),
                                  "".join(chr(b) if 32 <= b < 127 else "." for b in row)))


def read_intel_hex(path):
    """-> list of (addr, bytes) records merged into contiguous runs"""
    mem = {}
    base = 0
    with open(path) as fh:
        lines = fh.read().splitlines()
    for ln, line in enumerate(lines, 1):
        line = line.strip()
        if not line: continue
        if not line.startswith(":"): raise SystemExit("%s:%d: not Intel hex" % (path, ln))
        raw = bytes.fromhex(line[1:])
        if sum(raw) & 0xFF: raise SystemExit("%s:%d: checksum" % (path, ln))
        n, a, t = raw[0], raw[1] << 8 | raw[2], raw[3]
        if t == 0:
            for i, b in enumerate(raw[4:4 + n]): mem[base + a + i] = b
        elif t == 1: break
        elif t == 4: base = (raw[4] << 8 | raw[5]) << 16
        elif t == 2: base = (raw[4] << 8 | raw[5]) << 4
    runs = []
    for a in sorted(mem):
        if runs and runs[-1][0] + len(runs[-1][1]) == a: runs[-1][1].append(mem[a])
        else: runs.append((a, bytearray([mem[a]])))
    return [(a, bytes(b)) for a, b in runs]


def read_bin(path):
    with open(path, "rb") as fh: return fh.read()


def memtest(bd, start, end):
    n = end - start + 1; errors = 0
    def check(name, expect):
        nonlocal errors
        got = bd.read(start, n); bad = [(start + i, e, g) for i, (e, g) in enumerate(zip(expect, got)) if e != g]
        print("%-22s %s" % (name, "ok" if not bad else "%d errors, first %04X wrote %02X read %02X" % ((len(bad),) + bad[0])))
        errors += len(bad)
    pat = bytes(((a >> 8) ^ a) & 0xFF for a in range(start, end + 1)); bd.write(start, pat); check("address in address", pat)
    for bit in range(8):
        pat = bytes([1 << bit]) * n; bd.write(start, pat); check("walking one %02X" % (1 << bit), pat)
    for v in (0x55, 0xAA, 0x00, 0xFF):
        pat = bytes([v]) * n; bd.write(start, pat); check("fill %02X" % v, pat)
    print("memtest %04X-%04X: %s" % (start, end, "PASS" if not errors else "FAIL (%d errors)" % errors))
    return errors == 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="System-5 bus driver card host tool", formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("--port"); ap.add_argument("--baud", type=int, default=BAUD)
    ap.add_argument("--sim", action="store_true", help="talk to a simulated card (software/busdrv/simcard.py)")
    ap.add_argument("--rev", choices=("B", "C"), default="B", help="--sim: which card. C = BUSDRV-C's firmware (fwsim.py) "
                    "on the 36-pin backplane with CPU Rev D and a memory card (backplane.Backplane36)")
    ap.add_argument("--cycles", action="store_true", help="clk: one line a machine cycle, not every bus change")
    ap.add_argument("--auto-master", action="store_true", help="take the bus for memory/I-O commands and give it back after")
    ap.add_argument("--log", action="store_true", help="show the serial traffic")
    ap.add_argument("command"); ap.add_argument("args", nargs="*")
    a = ap.parse_args(argv)
    transport = None
    if a.sim:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        if a.rev == "C":
            import backplane, fwsim; transport = fwsim.FwCard(backplane.Backplane36(cards=("mem",)), rev="C")
        else:
            import simcard; transport = simcard.SimCard()
    bd = BusDriver(a.port, a.baud, log=sys.stderr if a.log else None, transport=transport)
    c, x = a.command, a.args
    needs_bus = c in ("peek", "poke", "dump", "load", "save", "memtest", "out", "inp")
    if needs_bus and a.auto_master: bd.master(True)
    try:
        if c == "status": print(bd.status())
        elif c == "master": bd.master(x[0].lower() in ("on", "1", "yes")); print(bd.status())
        elif c == "snap": print(bd.snap())
        elif c == "watch":
            for l in bd.cmd("WATCH", num(x[0]) if x else 5000, timeout=(num(x[0]) / 1000 + 5) if x else 15): print(l)
        elif c in ("peek", "dump"):
            addr = num(x[0]); n = num(x[1]) if len(x) > 1 else (1 if c == "peek" else 256); hexdump(addr, bd.read(addr, n))
        elif c == "poke": bd.write(num(x[0]), bytes(num(v) for v in x[1:]))
        elif c == "load":
            path = x[0]
            runs = read_intel_hex(path) if path.lower().endswith((".hex", ".ihx")) else [(num(x[1]) if len(x) > 1 else 0, read_bin(path))]
            for addr, data in runs:
                bd.write(addr, data); back = bd.read(addr, len(data))
                bad = [i for i in range(len(data)) if data[i] != back[i]]
                print("%04X-%04X %d bytes %s" % (addr, addr + len(data) - 1, len(data), "verified" if not bad else "VERIFY FAILED at %04X" % (addr + bad[0])))
        elif c == "save":
            with open(x[2], "wb") as fh: fh.write(bd.read(num(x[0]), num(x[1])))
            print("saved", x[2])
        elif c == "memtest": sys.exit(0 if memtest(bd, num(x[0]), num(x[1])) else 1)
        elif c == "out": bd.out(num(x[0]), num(x[1]))
        elif c == "inp": print("%02X" % bd.inp(num(x[0])))
        elif c == "walk":
            rest = bd.walk()
            if not x: print("at rest (pull-ups on):", " ".join("%s=%d" % kv for kv in rest.items()))
            else:
                name = next((n for n in WALK_PINS if n.lstrip("-") == x[0].upper().lstrip("-")), None)
                if name is None or name not in rest: ap.error("walk: no bus line %s on this card (%s)" % (x[0], " ".join(rest)))
                level = 1 if len(x) > 1 and x[1].lower() in ("high", "1", "hi") else 0
                got = bd.walk(name, level); moved = [n for n in got if n != name and got[n] != rest[n]]
                if got[name] != level: print("%s does not go %s: something holds it the other way (the card let go at once)" % (name, "high" if level else "low"))
                else: print("%s %s: %s" % (name, "high" if level else "low", "no other line moves" if not moved else "moves with it: " + " ".join("%s=%d" % (n, got[n]) for n in moved)))
        elif c == "spare": bd.cmd("SPARE", num(x[0]))
        elif c == "xrst": bd.cmd("XRST")
        elif c == "mode": bd.mode(x[0]); print(bd.status())
        elif c in ("dmaload", "loadrun"):
            path = x[0]; rest = [num(v) for v in x[1:]]
            if path.lower().endswith((".hex", ".ihx")): runs = read_intel_hex(path)
            else: runs = [(rest.pop(0) if rest else 0, read_bin(path))]
            img = load_image(runs); bd.mode("load")
            first = bd.dma_load(img, progress=lambda i, n: print("\r%d of %d bytes" % (i, n), end="", file=sys.stderr))
            print("", file=sys.stderr)
            print("%04X-%04X %d bytes by DMA IN%s" % (first, first + len(img) - 1, len(img),
                  "" if runs[0][0] == 0 else " (the file starts at %04X: a jump to it at 0000)" % runs[0][0]))
            if c == "loadrun":
                hz = rest[0] if rest else 2000000
                bd.mode("run")
                if hz: print("clock %d Hz" % bd.clk_hz(hz))
                print(bd.status())
        elif c == "clkhz": print("%d Hz" % bd.clk_hz(num(x[0])))
        elif c == "clkstop": bd.clk_stop(); print(bd.status())
        elif c == "clk":
            st = bd.clk(num(x[0]))
            if a.cycles:
                import cputrace
                for cy in cputrace.cycles([(e, cputrace.bits(*h)) for e, h in st]): print(cputrace.fmt(cy))
            else:
                for e, h in st: print(e, " ".join("%02X" % v for v in h))
        elif c == "dbg": print(" ".join("%s=%s" % kv for kv in bd.dbg().items()))
        elif c == "clktest": print(bd.clock_test())
        elif c == "line": bd.line(x[0], x[1].lower() in ("on", "1", "low", "yes")); print(bd.snap())
        elif c == "probe": print(" ".join("%s=%d" % kv for kv in bd.probe().items()))
        elif c == "pcount": print(" ".join("%s=%d" % kv for kv in bd.pcount(num(x[0])).items()))
        elif c == "ptime": print(" ".join("%s=%d" % kv for kv in bd.ptime(num(x[0]) if x else 1000).items()))
        elif c == "pdelay": print("%d ns" % bd.pdelay(num(x[0])))
        elif c == "spdir": bd.cmd("SPDIR", num(x[0]))
        elif c == "spin": print("%02X" % int(bd.cmd("SPIN")[0]))
        elif c == "cmd":
            op, _, operand = " ".join(x).rstrip("#").partition(":"); [print(l) for l in bd.cmd(op, operand or 0)]
        else: ap.error("unknown command " + c)
    except CardError as e:
        sys.exit("card: %s" % e)
    finally:
        if needs_bus and a.auto_master: bd.master(False)


if __name__ == "__main__":
    main()
