#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-06. After the YACC1 tools/busdrv.py.
"""Host tool for the System-5 bus driver card (BUSDRV-B, firmware embedded/bus-driver/s5-bus-driver).

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
Numbers accept 0x.. / $.. / plain decimal. "master on" is needed before memory and I/O commands; the tool turns it
on for them when --auto-master is given.
"""
import sys, os, time, glob, argparse

BAUD = 115200


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
        data = []
        for l in lines:
            if l.startswith("Error"): raise CardError("%s -> %s" % (msg, l))
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
    ap.add_argument("--auto-master", action="store_true", help="take the bus for memory/I-O commands and give it back after")
    ap.add_argument("--log", action="store_true", help="show the serial traffic")
    ap.add_argument("command"); ap.add_argument("args", nargs="*")
    a = ap.parse_args(argv)
    transport = None
    if a.sim:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import simcard; transport = simcard.SimCard()
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
        elif c == "spare": bd.cmd("SPARE", num(x[0]))
        elif c == "xrst": bd.cmd("XRST")
        elif c == "cmd":
            op, _, operand = " ".join(x).rstrip("#").partition(":"); [print(l) for l in bd.cmd(op, operand or 0)]
        else: ap.error("unknown command " + c)
    except CardError as e:
        sys.exit("card: %s" % e)
    finally:
        if needs_bus and a.auto_master: bd.master(False)


if __name__ == "__main__":
    main()
