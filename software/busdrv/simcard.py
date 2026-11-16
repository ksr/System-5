# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-06
"""A simulated bus driver card + System-5 bus for testing s5busdrv.py without hardware.

Speaks the s5-bus-driver wire protocol over an in-memory serial-like object. Behind it: a Memory Rev D card jumpered
the usual way (RAM 0000-6FFF, 7000 open for the video card, EPROM 8000-FFFF holding a pattern), an I/O port 4 that
echoes its last OUT on INP, and the same safety rules as the firmware (MONITOR until MASTER:1#, no bus power -> errors).
"""
BANNER = "s5-bus-driver blocks-1 2026-10-06 (SIMULATED)"


class SimCard:
    def __init__(self, bus_on=True, cpu_running=False):
        self.bus_on, self.cpu_running, self.master = bus_on, cpu_running, False
        self.ram = bytearray(0x7000)
        self.rom = bytes((a * 7 + 3) & 0xFF for a in range(0x8000))
        self.port4 = 0; self.out_buf = bytearray(); self.rx = ""
        self._emit([BANNER, ">>"])

    # serial-like interface used by BusDriver
    def write(self, b):
        self.rx += b.decode("ascii")
        while "#" in self.rx:
            c, self.rx = self.rx.split("#", 1); self._emit(self._run(c) + [">>"])
    def read(self, n=1):
        b = bytes(self.out_buf[:n]); del self.out_buf[:n]; return b
    def reset_input_buffer(self): pass
    def _emit(self, lines): self.out_buf += ("\r\n".join(lines) + "\r\n").encode()

    def _mem_rd(self, a):
        if a < 0x7000: return self.ram[a]
        if a < 0x8000: return 0xFF            # nobody drives the bus there: floats high
        return self.rom[a - 0x8000]
    def _mem_wr(self, a, v):
        if a < 0x7000: self.ram[a] = v       # writes to ROM or the hole go nowhere

    def _run(self, c):
        op, _, arg = c.partition(":")
        if not self.bus_on and op not in ("HELP", "STATUS"): return ["Error: bus has no power"]
        if op == "STATUS": return ["Data: bus=%s mode=%s" % ("on" if self.bus_on else "off", "MASTER" if self.master else "MONITOR"), "Complete"]
        if op == "MASTER":
            if int(arg or 0):
                if self.cpu_running: return ["Error: TPA/TPB toggling: a CPU is running - pull the CPU card"]
                self.master = True
            else: self.master = False
            return ["Complete"]
        if op == "SNAP": return ["Data: D=FF A=00 TPA=0 TPB=0 -MRD=1 -MRW=1 -VMA=1 Q=0 N=0 -RESET=1 -INT=1 -EF=1 SP=0", "Complete"]
        if op in ("SPARE", "XRST", "HELP"): return ["Complete"]
        if not self.master: return ["Error: MONITOR mode: send MASTER:1# first (CPU card out)"]
        a = [int(x, 16) if i == 2 and op == "WRBLK" else x for i, x in enumerate(arg.split(","))]
        if op == "RDMEM": return ["Data: %d" % self._mem_rd(int(a[0])), "Complete"]
        if op == "WRMEM": self._mem_wr(int(a[0]), int(a[1])); return ["Complete"]
        if op == "RDBLK":
            s, n = int(a[0]), int(a[1])
            if not 1 <= n <= 64: return ["Error: block addr 0..65535, count 1..64"]
            return ["Data:" + "".join(" %02X" % self._mem_rd(s + i) for i in range(n)), "Complete"]
        if op == "WRBLK":
            s, n, hx = int(a[0]), int(a[1]), arg.split(",")[2]
            if not 1 <= n <= 32: return ["Error: WRBLK count 1..32"]
            for i in range(n): self._mem_wr(s + i, int(hx[2 * i:2 * i + 2], 16))
            return ["Data: %d" % n, "Complete"]
        if op == "OUT":
            if int(a[0]) == 4: self.port4 = int(a[1])
            return ["Complete"]
        if op == "INP": return ["Data: %d" % (self.port4 if int(a[0]) == 4 else 0xFF), "Complete"]
        return ["Error: Bad opcode"]
