# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-06
"""Bus-driver link: the BUSDRV-B card's serial protocol (embedded/bus-driver/s5-bus-driver.ino) answered from the
emulated machine, on a pseudo-terminal, so software/busdrv/s5busdrv.py --port <pty> works as with the real card.

As on the real card: MONITOR until MASTER:1#; MASTER is refused while the emulated CPU is running (the firmware
refuses when it sees TPA/TPB toggling); memory cycles go through the machine's bus exactly as CPU accesses do.
"""
import os, threading, tty

BANNER = "s5-bus-driver blocks-1 2026-10-06 (EMULATED)"


class BusLink:
    def __init__(self, machine, cpu_running):
        self.m = machine; self.cpu_running = cpu_running; self.master = False
        self.fd, slave = os.openpty(); tty.setraw(slave); self.path = os.ttyname(slave); self._slave = slave
        self.port4 = 0; self.log = []
        threading.Thread(target=self._serve, daemon=True).start()

    def _send(self, lines):
        os.write(self.fd, ("\r\n".join(lines) + "\r\n").encode())

    def _serve(self):
        """the real Nano resets and prints its banner when the port is opened; a pty has no such event (and pyserial
        flushes input on open), so the banner repeats every 0.5 s until the host's first command arrives"""
        import select
        buf = ""; greeted = False
        while True:
            if not greeted:
                r, _, _ = select.select([self.fd], [], [], 0.5)
                if not r: self._send([BANNER, ">>"]); continue
                greeted = True
            try: data = os.read(self.fd, 1024)
            except OSError: return
            buf += data.decode("ascii", "replace")
            while "#" in buf:
                c, buf = buf.split("#", 1); c = c.strip()
                self.log.append(c); self.log = self.log[-50:]
                try: out = self.run(c)
                except Exception as e: out = ["Error: %s" % e]
                self._send(out + [">>"])

    def _snap(self):
        return "Data: D=FF A=00 TPA=0 TPB=0 -MRD=1 -MRW=1 -VMA=1 Q=%d N=0 -RESET=1 -INT=%d -EF=1 SP=0" % (self.m.q_level, 0 if self.m.cpu.int_line else 1)

    def run(self, c):
        op, _, arg = c.partition(":"); m = self.m
        if op == "HELP": return ["Data: emulated BUSDRV-B: STATUS MASTER SNAP RDMEM WRMEM RDBLK WRBLK OUT INP SPARE XRST", "Complete"]
        if op == "STATUS": return ["Data: bus=on mode=%s" % ("MASTER" if self.master else "MONITOR"), "Complete"]
        if op == "MASTER":
            if int(arg or 0):
                if self.cpu_running(): return ["Error: TPA/TPB toggling: a CPU is running - pull the CPU card"]
                self.master = True
            else: self.master = False
            return ["Complete"]
        if op == "SNAP": return [self._snap(), "Complete"]
        if op in ("SPARE", "XRST", "WATCH"): return ["Complete"]
        if not self.master: return ["Error: MONITOR mode: send MASTER:1# first (CPU card out)"]
        a = arg.split(",")
        if op == "RDMEM": return ["Data: %d" % m.read(int(a[0]) & 0xFFFF), "Complete"]
        if op == "WRMEM": m.write(int(a[0]) & 0xFFFF, int(a[1]) & 0xFF); return ["Complete"]
        if op == "RDBLK":
            s, n = int(a[0]), int(a[1])
            if not 1 <= n <= 64 or s + n > 65536: return ["Error: block addr 0..65535, count 1..64"]
            return ["Data:" + "".join(" %02X" % m.read(s + i) for i in range(n)), "Complete"]
        if op == "WRBLK":
            s, n, hx = int(a[0]), int(a[1]), a[2]
            if not 1 <= n <= 32: return ["Error: WRBLK count 1..32"]
            for i in range(n): m.write(s + i, int(hx[2 * i:2 * i + 2], 16))
            return ["Data: %d" % n, "Complete"]
        if op == "OUT": m.out(int(a[0]), int(a[1])); return ["Complete"]
        if op == "INP": return ["Data: %d" % m.inp(int(a[0])), "Complete"]
        return ["Error: Bad opcode"]
