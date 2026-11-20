# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-01
"""VIDEO-G 1.0 (hardware/video-g/DESIGN.md), a behavioural model: the TEXT board and, if fitted, the GFX board.

As the software sees it (DESIGN.md sections 2 and 3): memory-mapped, no I/O ports (Ken, 2026-11-17)
  7000-77FF   text RAM (the IDT7134's bus port, 2K); row r, column c at 7000 + 64r + c
  7800        write: the 6845's address register        7801  the 6845's data register (reads R14-R17)
  7802        read: the key (ASCII; reading it clears KEY-READY); EF3 = a key waits (the bus -EF: the TEXT board's
              JP3 KBD FLAG as set; it can pick -EF1, -EF2 or -EF3 instead, which this model does not follow)
  7804        read: status: 0 KEY-READY, 1 MOUSE-READY, 2 VSYNC, 3 DE, 4 MONITOR (1 = IBM 5151, 512 x 256),
              5 GFX-PRESENT, 7..6 = 10 (card ID)
              write: control: 0 TEXT-OFF, 1 GFX-ON, 2 XOR, 3 DPAGE, 4 CPAGE, 5 MOUSE-ON; -RESET clears it.  The register
              is on the GFX board: with TEXT alone a write does nothing (text always on)
  7806        GFX: read: the mouse byte (3-byte PS/2 packets while MOUSE-ON); write: the Y register (pixel line)
              (7800-7807 repeat through 7BFF: the card decodes A1-A2 there, A0 only for the 6845)
  7C00-7C3F   graphics window: pixel line Y of the page CPAGE, 64 bytes, bit 7 of byte 0 = x 0; repeated to 7FFF
Graphics RAM: two pages of 16K (512 x 256 bits); NTSC shows lines 0-199. The CPU-side address is the RA:MA layout
{page, Y2..Y0, Y7..Y3, A5..A0}; that is a fixed permutation the software never sees, so pages are stored by line here
(line y at y*64), which is what page_bitmap() and the PNG show. At power-up the RAM holds noise (seeded, so runs repeat).
Without the GFX board (gfx=False): status bit 5 = 0, the window and the mouse float (FF), writes to 7804 and 7806 do nothing.
Keys (the VIDEO-G PS/2 firmware): ASCII (Enter 0D, Backspace 08, Esc 1B, Ctrl-C 03, Delete 7F); F1-F12 = 80-8B;
Home, Up, PgUp, Left, keypad 5, Right, End, Down, PgDn, Ins, Del = 90-9A; with Shift + 40h (C0-DA).  KEYS names them.
Mouse: the GFX board's ATmega sends 3-byte packets only while MOUSE-ON; MOUSE-READY says a byte waits in its latch,
which keeps the last byte when MOUSE-ON goes off (a stale byte: read 7806 once before turning MOUSE-ON back on).
VSYNC and DE in the status come from the CPU's cycle count (NTSC: 262 lines x 95 characters at 1.5 MHz; 5151: 370 x 81).
"""
import random, struct, zlib, os
from collections import deque
from .machine import Machine, FLOAT

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
FONT = os.path.join(ROOT, "firmware/char-rom-fonts/goodfont")   # the 6845 Rev B character ROM (128 x 8 rows, bits 7-3)

FORMATS = {   # lines/frame, characters/line (R0+1), displayed lines, VSYNC start line, VSYNC lines
    "ntsc": dict(lines=262, chars=95, shown=200, vs=224, vsl=16, rows=25),
    "mda": dict(lines=370, chars=81, shown=256, vs=312, vsl=16, rows=32),
}


class VideoG:
    TEXT_BASE, TEXT_SIZE, REGS, WIN = 0x7000, 0x800, 0x7800, 0x7C00

    def __init__(self, machine, monitor="ntsc", gfx=True, mhz=1.76, seed=1802):
        self.m = machine; self.monitor = monitor.lower(); self.gfx = gfx; self.mhz = mhz
        if self.monitor not in FORMATS: raise ValueError("monitor: ntsc or mda")
        self.fmt = FORMATS[self.monitor]
        self.vram = bytearray([0x20]) * self.TEXT_SIZE
        self.reg = [0] * 18; self.sel = 0
        self.reg[1], self.reg[6] = 64, self.fmt["rows"]
        self.ctrl = 0; self.yreg = 0
        rnd = random.Random(seed)
        self.pages = [bytearray(rnd.getrandbits(8) for _ in range(16384)) for _ in range(2)]
        self.mouse = deque(); self.dirty = True
        self.writes = 0                                        # window writes (for tests and speed counts)

    # ---------------------------------------------------------------- control bits
    def text_on(self): return not self.ctrl & 0x01
    def gfx_on(self): return bool(self.ctrl & 0x02)
    def xor_mode(self): return bool(self.ctrl & 0x04)
    def dpage(self): return (self.ctrl >> 3) & 1
    def cpage(self): return (self.ctrl >> 4) & 1
    def height(self): return self.fmt["shown"]

    # ---------------------------------------------------------------- memory
    def read(self, a):
        if self.TEXT_BASE <= a < self.TEXT_BASE + self.TEXT_SIZE: return self.vram[a - self.TEXT_BASE]
        if self.WIN <= a <= 0x7FFF:                               # the window (A10 = 1)
            if not self.gfx: return FLOAT
            return self.pages[self.cpage()][self.yreg * 64 + (a & 0x3F)]
        if self.REGS <= a < self.WIN:                             # the registers (A10 = 0), chosen by A1-A2
            r = (a >> 1) & 3
            if r == 0:                                            # the 6845: 7801 reads R14-R17
                return (self.reg[self.sel] if self.sel in (14, 15, 16, 17) else 0) if a & 1 else FLOAT
            if r == 1: return self.m.kbd.read()                   # 7802: the key (the read clears KEY-READY)
            if r == 2: return self.status()                       # 7804
            if not self.gfx: return FLOAT                         # 7806: the mouse byte (GFX)
            return self.mouse.popleft() if self.mouse else 0
        return None

    def write(self, a, v):
        if self.TEXT_BASE <= a < self.TEXT_BASE + self.TEXT_SIZE:
            self.vram[a - self.TEXT_BASE] = v; self.dirty = True; return True
        if self.WIN <= a <= 0x7FFF:
            if self.gfx:
                self.pages[self.cpage()][self.yreg * 64 + (a & 0x3F)] = v; self.dirty = True; self.writes += 1
            return True
        if self.REGS <= a < self.WIN:
            r = (a >> 1) & 3
            if r == 0:                                            # the 6845: 7800 address register, 7801 data
                if a & 1:
                    if self.sel < 18: self.reg[self.sel] = v; self.dirty = True
                else: self.sel = v & 31
            elif r == 2 and self.gfx:                             # 7804: control (the register is on GFX)
                if self.ctrl & 0x20 and not v & 0x20: self.mouse = deque(list(self.mouse)[:1])   # the latch keeps one
                self.ctrl = v; self.dirty = True
            elif r == 3 and self.gfx: self.yreg = v               # 7806: the Y register
            return True
        return False

    def frame_position(self):
        """(line, character) of the beam, from the CPU's machine cycles (8 clocks each)"""
        f = self.fmt; chars = f["lines"] * f["chars"]
        cpu_chars = self.m.cpu.cycles * 8 * 1.5 / self.mhz        # character clock 1.5 MHz
        pos = int(cpu_chars) % chars
        return divmod(pos, f["chars"])

    def status(self):
        f = self.fmt; line, ch = self.frame_position()
        s = 0x80
        if self.m.kbd.ready(): s |= 0x01
        if self.mouse and self.gfx: s |= 0x02                     # a byte in the mouse latch (even with MOUSE-ON off)
        if f["vs"] <= line < f["vs"] + f["vsl"]: s |= 0x04
        if line < f["shown"] and ch < 64: s |= 0x08
        if self.monitor == "mda": s |= 0x10
        if self.gfx: s |= 0x20
        return s

    def mouse_packet(self, dx, dy, buttons=0):
        """queue one PS/2 packet (only while MOUSE-ON, as the GFX board's ATmega reports only then)"""
        if not (self.gfx and self.ctrl & 0x20): return False
        b0 = 0x08 | (buttons & 7) | (0x10 if dx < 0 else 0) | (0x20 if dy < 0 else 0)
        self.mouse.extend([b0, dx & 0xFF, dy & 0xFF]); return True

    # ---------------------------------------------------------------- the picture
    def geometry(self):
        cols = self.reg[1] or 64; rows = self.reg[6] or self.fmt["rows"]
        return min(cols, 80), min(rows, 32)

    def lines(self):
        cols, rows = self.geometry(); start = ((self.reg[12] << 8) | self.reg[13]) & 0x7FF
        out = []
        for r in range(rows):
            row = bytes(self.vram[(start + r * cols + c) & 0x7FF] for c in range(cols))
            out.append("".join(chr(b & 0x7F) if 32 <= (b & 0x7F) < 127 else " " for b in row))
        return out

    def cursor(self):
        cols, rows = self.geometry(); start = ((self.reg[12] << 8) | self.reg[13]) & 0x7FF
        pos = (((self.reg[14] << 8) | self.reg[15]) - start) & 0x7FF
        r, c = divmod(pos, cols)
        return (r, c) if r < rows else None

    def page_bitmap(self, page=None):
        """-> list of `height` rows of 512 ints (0/1) for a graphics page (default: the one shown)"""
        p = self.pages[self.dpage() if page is None else page]
        return [[(p[y * 64 + (x >> 3)] >> (7 - (x & 7))) & 1 for x in range(512)] for y in range(self.height())]

    def count_pixels(self, page=None, y0=0, y1=None):
        p = self.pages[self.cpage() if page is None else page]
        y1 = self.height() if y1 is None else y1
        return sum(bin(b).count("1") for b in p[y0 * 64:y1 * 64])

    def pixel(self, x, y, page=None):
        p = self.pages[self.cpage() if page is None else page]
        return (p[y * 64 + (x >> 3)] >> (7 - (x & 7))) & 1

    def picture(self, mode="screen"):
        """-> rows of 512 ints: 'screen' = what the monitor shows (text and graphics combined by the control bits),
        'gfx' = the shown graphics page alone, 'text' = the text alone"""
        h = self.height(); font = open(FONT, "rb").read() if os.path.exists(FONT) else bytes(1024)
        cols, rows = self.geometry(); start = ((self.reg[12] << 8) | self.reg[13]) & 0x7FF
        cur = self.cursor()
        def text_dot(x, y):
            r, sl = divmod(y, 8); c = x >> 3
            if r >= rows or c >= cols: return 0
            ch = self.vram[(start + r * cols + c) & 0x7FF]
            bits = font[(ch & 0x7F) * 8 + sl]
            d = (bits >> (7 - (x & 7))) & 1
            if ch & 0x80: d ^= 1                                 # bit 7 = reverse video
            if cur == (r, c): d ^= 1                             # a solid block cursor (no blink)
            return d
        gp = self.pages[self.dpage()]
        out = []
        for y in range(h):
            row = []
            for x in range(512):
                g = (gp[y * 64 + (x >> 3)] >> (7 - (x & 7))) & 1
                if mode == "gfx": row.append(g); continue
                t = text_dot(x, y)
                if mode == "text": row.append(t); continue
                t = t if self.text_on() else 0
                g = g if self.gfx_on() else 0
                row.append(t ^ g if self.xor_mode() else t | g)
            out.append(row)
        return out

    def save_png(self, path, mode="screen", scale=1):
        write_png(path, self.picture(mode), scale)
        return path


def write_png(path, rows, scale=1, fg=(0x33, 0xFF, 0x66), bg=(0, 0, 0)):
    """rows of 0/1 -> an RGB PNG (green on black, like a P1 phosphor), each dot scale x scale (scale 2 doubles lines
    too, so 512 x 200 becomes 1024 x 400, about the shape of the picture on a TV)"""
    h = len(rows); w = len(rows[0]) if rows else 0
    raw = bytearray()
    for r in rows:
        line = bytearray()
        for d in r: line += bytes(fg if d else bg) * scale
        for _ in range(scale): raw += b"\x00" + line
    def chunk(t, data): return struct.pack(">I", len(data)) + t + data + struct.pack(">I", zlib.crc32(t + data) & 0xFFFFFFFF)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w * scale, h * scale, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b"")
    open(path, "wb").write(png)


KEYS = dict({"F%d" % (i + 1): 0x80 + i for i in range(12)},
            **{k: 0x90 + i for i, k in enumerate(["HOME", "UP", "PGUP", "LEFT", "KP5", "RIGHT", "END", "DOWN", "PGDN",
                                                    "INS", "DEL"])})


class VideoGMachine(Machine):
    """System-5 with VIDEO-G in place of the 6845 card and the IO card (no 1861; the keyboard is on TEXT). VIDEO-G uses
    no I/O port (memory-mapped, 2026-11-17): the ports are the base machine's, the IDE card's 2 and 3 and, with the IO
    panel fitted, its 4; nothing answers INP 1 (the key is read at 7802). EF3 is still KEY-READY (bus -EF)."""
    def __init__(self, monitor="ntsc", gfx=True, mhz=1.76, **kw):
        kw["pixie_port"] = 0                                   # no IO card: port 0 is never an INP/OUT
        super().__init__(**kw)
        self.kbd.port = None                                   # the key is memory-mapped: not on INP 1
        self.video = VideoG(self, monitor, gfx, mhz)

    def reset(self):
        super().reset(); self.video.ctrl = 0                  # -RESET clears the control register
