# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-01
"""Drive GBASIC in the emulator: an ELF/OS disk with GBASIC on it, System-5 with VIDEO-G (or the 6845 card), boot,
start GBASIC, type lines, read what it printed.

    gb = GBasic()                  # boots (once per process; later instances start from a snapshot)
    out = gb.cmd('PRINT 2+2')      # types the line + Enter, runs until GBASIC waits for a key again
    gb.video.count_pixels()        # the VIDEO-G model (software/s5emu/s5emu/videog.py)

Output is captured at the BIOS type vector (FF03), so it is everything GBASIC sent to the screen, in order.
"""
import copy, os, re, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
GB = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(GB, "..", ".."))
EMU = os.path.join(ROOT, "software", "s5emu")
sys.path.insert(0, EMU)
from s5emu.machine import Machine                      # noqa: E402
from s5emu.videog import VideoGMachine                 # noqa: E402
sys.path.insert(0, os.path.join(EMU, "tools"))
import mkelfos                                         # noqa: E402  ELF/OS 0.2.6 and disktool: Mike Riley's, kept in
                                                       # the private-resources repository (mkelfos.missing())

VG_ROM = os.path.join(EMU, "roms", "hbios-video-g.rom")
ROM104 = os.path.join(EMU, "roms", "hbios-1.0.4.rom")
BINARY = os.path.join(GB, "gbasic")
F_TYPE = 0xFF03
_cache = {}


def symbols():
    s = {}
    for line in open(os.path.join(GB, "gbasic.sym")):
        a, n = line.split(); s[n.lower()] = int(a, 16)
    return s


def disktool():
    dt = os.path.join(tempfile.gettempdir(), "s5emu-disktool")
    src = mkelfos.DT_SRC
    if not os.path.exists(dt) or os.path.getmtime(dt) < os.path.getmtime(src):
        subprocess.run(["cc", "-std=gnu89", "-w", "-o", dt, src], check=True)
    return dt


def make_disk(path, extra=()):
    """a 4 MB ELF/OS disk (tools/mkelfos.py) with GBASIC (and extra (host path, name) files) in /"""
    subprocess.run([sys.executable, os.path.join(EMU, "tools", "mkelfos.py"), path, "--mb", "4"], check=True,
                   capture_output=True)
    cmds = ["copy [%s] GBASIC" % BINARY] + ["copy [%s] %s" % (h, n) for h, n in extra] + ["quit"]
    subprocess.run([disktool(), path], input="\n".join(cmds) + "\n", capture_output=True, text=True, timeout=60)


class GBasic:
    def __init__(self, video="g", gfx=True, monitor="ntsc", fresh=False):
        key = (video, gfx, monitor)
        self.sym = symbols()
        if key in _cache and not fresh:
            m, out = _cache[key]
            self.m = copy.deepcopy(m); self.out = list(out)
        else:
            self.m = self._boot(video, gfx, monitor)
            _cache[key] = (copy.deepcopy(self.m), list(self.out))

    @property
    def video(self): return self.m.video

    def _boot(self, video, gfx, monitor):
        img = tempfile.mktemp(suffix=".img", prefix="gbasic-")
        make_disk(img)
        if video == "g":
            m = VideoGMachine(cpu_rom=VG_ROM, disk=img, gfx=gfx, monitor=monitor)
        else:
            m = Machine(cpu_rom=ROM104, disk=img, pixie_port=0)
        os.remove(img)
        self.m = m; self.out = []
        self.run_until_text("test>", 2_000_000, 0)
        self.type_text("@FF00\n"); self.run_until_text("$ ", 8_000_000)
        self.type_text("GBASIC\n")
        if not self.run_until_waiting(20_000_000): raise RuntimeError("GBASIC did not start:\n" + self.screen())
        return m

    # ---------------------------------------------------------------- running
    def type_text(self, s):
        self.m.kbd.press(s)

    def run_until_text(self, text, limit, start=None):
        """run until `text` has been printed (after output position `start`, default: from now)"""
        m = self.m; cpu = m.cpu; R = cpu.R; step = m.step; out = self.out; n = 0
        start = len(out) if start is None else start
        while n < limit:
            for _ in range(20000):
                if R[cpu.P] == F_TYPE: out.append(cpu.D)
                step()
            n += 20000
            if text in self.text(start): return True
        return False

    def run_until_waiting(self, limit=50_000_000):
        """run until GBASIC is in its key wait with nothing typed ahead; True if it got there"""
        m = self.m; cpu = m.cpu; R = cpu.R; step = m.step; out = self.out; kw = self.sym["kwait"]
        q = m.kbd.queue
        for _ in range(limit):
            pc = R[cpu.P]
            if pc == F_TYPE: out.append(cpu.D)
            elif pc == kw and not q: return True
            step()
        return False

    def cmd(self, line, limit=50_000_000):
        """type a line (or several, joined by newlines), run until GBASIC waits again, return what it printed after
        echoing the input (with CR LF -> newline)"""
        start = len(self.out)
        for l in line.split("\n"):
            self.type_text(l + "\n")
            if not self.run_until_waiting(limit):
                raise TimeoutError("still running after %d instructions:\n%s" % (limit, self.screen()))
        text = self.text(start)
        return text

    def text(self, start=0):
        return bytes(self.out[start:]).decode("latin-1").replace("\r\n", "\n").replace("\r", "")

    def screen(self):
        return "\n".join(l.rstrip() for l in self.m.video.lines())

    def program(self, src):
        """type a program (lines) after NEW"""
        self.cmd("NEW")
        for l in src.strip().splitlines():
            self.cmd(l.strip())

    def run_prog(self, src, limit=200_000_000):
        self.program(src)
        out = self.cmd("RUN", limit)
        return out

    def peek(self, a): return self.m.peek(a)
    def instructions(self): return self.m.cpu.instructions
    def cycles(self): return self.m.cpu.cycles


def lines_of(out):
    """the printed lines, without the echoed command line (the first) and the Ready line"""
    ls = out.split("\n")[1:]
    return [l for l in ls if l.strip() and l.strip() != "Ready"]
