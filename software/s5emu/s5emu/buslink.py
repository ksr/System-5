# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-06
"""Bus-driver link: the bus driver card's serial protocol (embedded/bus-driver/s5-bus-driver.ino) answered from the
emulated machine, on a pseudo-terminal, so software/busdrv/s5busdrv.py --port <pty> works as with the real card.

Two cards, as the sketch is one sketch for two boards:

BUSDRV-B (rev "B"; any machine whose CPU card is not Rev D). As on the real card: MONITOR until MASTER:1#; MASTER
is refused while the emulated CPU is running (the firmware refuses when it sees TPA/TPB toggling); memory cycles go
through the machine's bus exactly as CPU accesses do. Taking MASTER stands for pulling the CPU card.

BUSDRV-C (rev "C", 2026-11-20; a machine with CPU Rev D: --hw --cpu-rev D). The 36-pin card works with the CPU card in
place, so here it never becomes bus master (the real one refuses too: its DEBUG cable shows it the CPU card). It has:
  MODE:n#        0 RUN, 1 RESET, 2 PAUSE, 3 LOAD, by -RESET and -PAUSE, which the CPU card's gates (hw.NetlistCPUCard)
                 see as from any card: LOAD sets LOADED, a reset from the bus keeps it, and the machine stands still
                 in every mode but RUN
  DMA / LOADBLK  LOAD mode: each byte one DMA IN cycle into M(R(0)) through the machine's bus, so the memory card's
                 netlist decides where it lands (with LOADED set: RAM, not the boot EPROM)
  -EF1 -EF2 -EF3 (and -EF, -INT) pulled low reach the 1802's flag inputs through the CPU card's EF jumpers
  STATUS, SNAP   with BUSDRV-C's added fields
What the emulator does not have is the clock: it runs instructions, not clock edges. So DBG:1# always finds the cable,
CLKHZ / CLKSTOP only remember the rate, CLK:n# runs whole instructions for at least n / 16 machine cycles and prints
no trace lines, and the probes read 0. The firmware's steps on the real pins, edge for edge, are in
software/busdrv/fwsim.py with backplane.Backplane36.
The IO panel's RUN and LOAD toggles pull the same two lines: whichever of the two last changed mode wins here.
"""
import os, threading, tty

BANNER = "s5-bus-driver blocks-1 2026-10-06 (EMULATED)"
BANNER_C = "s5-bus-driver blocks-1 io-2 clk-2 ext-1 mode-1 load-1 probe-1 2026-11-20 BUSDRV-C (EMULATED)"
C_COMMANDS = ("MODE", "DMA", "LOADBLK", "CLKHZ", "CLKSTOP", "PROBE", "PCOUNT", "PTIME", "PDELAY", "DBG", "SPDIR", "SPIN")
C_LINES = ("-EF1", "-EF2", "-EF3", "-PAUSE", "-DMAIN")
OC_LINES = ("-RESET", "-INT", "-EF") + C_LINES
MODES = ("RUN", "RESET", "PAUSE", "LOAD")
NEEDS_C = "Error: needs BUSDRV-C (no U3 at 0x22)"
MONITOR = "Error: MONITOR mode: send MASTER:1# first (CPU card out)"


def card_for(machine):
    """'C' for a machine with CPU Rev D (the 36-pin CPU card, with LOADED), else 'B'"""
    c = getattr(machine, "ccard", None)
    return "C" if c is not None and hasattr(c, "mode") and len(getattr(c, "flops", ())) > 1 else "B"


class BusLink:
    def __init__(self, machine, cpu_running, rev=None, pty=True):
        """rev: 'B', 'C' or None = by the machine fitted. pty=False: no pseudo-terminal (the tests call run())"""
        self.m = machine; self.cpu_running = cpu_running; self.master = False
        self.rev = rev or card_for(machine)
        if self.rev == "C" and card_for(machine) != "C":
            raise ValueError("the BUSDRV-C link needs a machine with CPU Rev D (--hw --cpu-rev D)")
        self.port4 = 0; self.log = []; self.pull = {n: False for n in OC_LINES}; self.clk_hz = 0; self.spdir = 0
        self.hold = False; self.path = None
        if self.rev == "C": self._hook()
        if pty:
            self.fd, slave = os.openpty(); tty.setraw(slave); self.path = os.ttyname(slave); self._slave = slave
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
                if not r: self._send([self.banner(), ">>"]); continue
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

    def banner(self): return BANNER_C if self.rev == "C" else BANNER

    # ------------------------------------------------------------------ BUSDRV-C: its lines on the emulated machine
    def _hook(self):
        """the machine stands still while this card holds -RESET or -PAUSE, and the 1802's flag inputs see the lines
        this card pulls (through the CPU card's EF jumpers, as hw.HWMachine.ef reads them for the other cards)"""
        m = self.m; step, ef = m.step, m.ef
        def held_step():
            if self.hold: m.cpu.cycles += 1; return None
            return step()
        def flags(n):
            src = m.ccard.ef_map.get(n)
            return bool(self.pull.get("-EF" if src == "-EF4" else src)) or ef(n)
        m.step, m.ef = held_step, flags

    def cpu_mode(self):
        """0 RUN, 1 RESET, 2 PAUSE, 3 LOAD: as -RESET and -PAUSE stand, this card's pull or the IO panel's toggles"""
        p = getattr(self.m, "panel", None)
        rst = self.pull["-RESET"] or (p is not None and not p.run_on)
        pse = self.pull["-PAUSE"] or (p is not None and p.load_on)
        return (1 if rst else 0) | (2 if pse else 0)

    def _lines_changed(self, before):
        """-RESET or -PAUSE moved: the CPU card's gates see it, the 1802 resets when it enters RESET, and the machine
        stands still in every mode but RUN"""
        m = self.m; now = self.cpu_mode()
        m.ccard.mode(0 if now & 1 else 1, 0 if now & 2 else 1)
        if now == 1 and before != 1:
            m.cpu.reset()
            if hasattr(m, "pixie"): m.pixie.on = False
        self.hold = bool(self.pull["-RESET"] or self.pull["-PAUSE"])

    def _set(self, name, low):
        before = self.cpu_mode(); self.pull[name] = bool(low)
        if name in ("-RESET", "-PAUSE"): self._lines_changed(before)
        elif name == "-INT": self.m.cpu.int_line = bool(low)

    def set_mode(self, n):
        """as the sketch's setMode(): -RESET and -PAUSE are low together only for LOAD, which goes through RESET"""
        if n == 2: self._set("-RESET", False); self._set("-PAUSE", True); return
        self._set("-PAUSE", False); self._set("-RESET", n != 0)
        if n == 3: self._set("-PAUSE", True)

    def _snap(self):
        m = self.m
        s = "Data: D=FF A=00 TPA=0 TPB=0 -MRD=1 -MRW=1 -VMA=1 Q=%d N=0 -RESET=%d -INT=%d -EF=%d SP=0" % (
            m.q_level if self.rev != "C" else m.cpu.Q, 0 if self.cpu_mode() & 1 and self.rev == "C" else 1,
            0 if m.cpu.int_line else 1, 0 if self.pull["-EF"] else 1)
        if self.rev == "C":
            s += " -EF1=%d -EF2=%d -EF3=%d -PAUSE=%d -DMAIN=%d SC0=1 DBG=010 S5=1F" % (
                0 if self.pull["-EF1"] else 1, 0 if self.pull["-EF2"] else 1, 0 if self.pull["-EF3"] else 1,
                0 if self.cpu_mode() & 2 else 1, 0 if self.pull["-DMAIN"] else 1)
        return s

    def run_c(self, op, arg):
        m = self.m; a = arg.split(","); v = int(a[0] or 0) if a[0].lstrip("-").isdigit() or not a[0] else 0
        if op == "MODE":
            if not 0 <= v <= 3: return ["Error: MODE 0 RUN, 1 RESET, 2 PAUSE, 3 LOAD"]
            self.set_mode(v); return ["Complete"]
        if op in ("DMA", "LOADBLK"):
            if op == "DMA":
                if not 0 <= v <= 255: return ["Error: value 0..255"]
                data = [v]
            else:
                hx = a[1] if len(a) > 1 else ""
                if not 1 <= v <= 32 or len(hx) < 2 * v: return ["Error: LOADBLK:count,hh.. count 1..32, 2 hex digits per byte"]
                try: data = [int(hx[2 * i:2 * i + 2], 16) for i in range(v)]
                except ValueError: return ["Error: bad hex in LOADBLK"]
            if self.cpu_mode() != 3: return ["Error: not in LOAD mode: MODE:3# first"]
            first = m.cpu.R[0]
            for b in data: m.cpu.dma_in(b)                  # one DMA IN cycle each: M(R(0)) through the machine's bus
            return ["Data: %04X" % first if op == "DMA" else "Data: %d %04X" % (len(data), first), "Complete"]
        if op == "CLKHZ":
            if not 1 <= v <= 2000000: return ["Error: CLKHZ 1..2000000 (the cards are timed for 2 MHz)"]
            self.clk_hz = v; return ["Data: %d" % v, "Complete"]
        if op == "CLKSTOP": self.clk_hz = 0; return ["Complete"]
        if op == "DBG":
            return ["Data: CLK OUT reaches the 1802" if v else "Data: CLOCK=0 SC0=1 SC1=0", "Complete"]
        if op == "PROBE": return ["Data: P1=0 P2=0", "Complete"]
        if op == "PCOUNT": return ["Data: P1=0 P2=0", "Complete"]
        if op in ("PTIME", "PDELAY"): return ["Error: the emulator has no clock edges to time (software/busdrv/fwsim.py has the firmware's own steps)"]
        if op == "SPDIR": self.spdir = v & 0x1F; return ["Complete"]
        return ["Data: 31", "Complete"]                     # SPIN: nothing on the spare pins

    def run(self, c):
        op, _, arg = c.partition(":"); m = self.m; rev_c = self.rev == "C"
        if op == "HELP":
            return ["Data: emulated BUSDRV-%s: STATUS MASTER SNAP RDMEM WRMEM RDBLK WRBLK OUT INP SPARE XRST%s" % (
                self.rev, " MODE DMA LOADBLK CLK CLKHZ CLKSTOP DBG -EF1 -EF2 -EF3 -PAUSE -DMAIN" if rev_c else ""), "Complete"]
        if op == "STATUS":
            s = "Data: bus=on mode=%s" % ("MASTER" if self.master else "MONITOR")
            if rev_c: s += " board=C cpu=%s clk=%d" % (MODES[self.cpu_mode()], self.clk_hz)
            return [s, "Complete"]
        if op in C_COMMANDS: return self.run_c(op, arg) if rev_c else [NEEDS_C]
        if op in C_LINES and not rev_c: return [NEEDS_C]
        if op == "MASTER":
            if int(arg or 0):
                if rev_c: return ["Error: a CPU card answers on the DEBUG cable - pull the CPU card"]
                if self.cpu_running(): return ["Error: TPA/TPB toggling: a CPU is running - pull the CPU card"]
                self.master = True
            else:
                self.master = False
                if rev_c:                                   # every pin an input again: the open-collector lines let go
                    for n in OC_LINES:
                        if self.pull[n]: self._set(n, False)
            return ["Complete"]
        if op == "SNAP": return [self._snap(), "Complete"]
        if op == "XRST" and rev_c:
            for n in OC_LINES:
                if self.pull[n]: self._set(n, False)
            self.spdir = 0; return ["Complete"]
        if op in ("SPARE", "XRST", "WATCH"): return ["Complete"]
        if rev_c and op in OC_LINES: self._set(op, int(arg or 0) != 0); return ["Complete"]
        if rev_c and op == "CLK":                           # whole instructions for at least n / 16 machine cycles
            n = int(arg or 0)
            if n < 1: return ["Error: CLK:n, n >= 1"]
            if not self.hold and not self.cpu_running():
                target = m.cpu.cycles + n // 16
                while m.cpu.cycles < target: m.step()
            return ["Data: %d" % n, "Complete"]
        if not self.master: return [MONITOR]
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
