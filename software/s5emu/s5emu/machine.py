# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-06
"""System-5 machine: 1802 CPU card, memory card, 6845 video card, IO card (1861 + keyboard), IDE/CF card.

Hardware facts used (see hardware/*/README, hardware/memory/REVIEW.md, firmware/hbios, Mike Riley's BIOS):
  CPU card   4K EPROM (default F000-FFFF, HBIOS + BIOS). At reset it is also seen at 0000 (the VMA remap) until the
             first access with A15 high; the ROM's first instructions (LDI F0 / PHI R0) make that jump.
  Memory     Rev C/D: 2x 32K RAM + 2x 32K EPROM, every 4K block jumpered to RAM, ROM or nothing (open = floats).
  Video      6845 card: 2K video RAM 7000-77FF, CRTC address/data registers at 7800/7801; HBIOS uses 64x16.
  IO card    keyboard: INP 1 reads the character, EF3 = character waiting. 1861: INP n on = display on, OUT n = off,
             EF1 = frame marker, interrupt + DMA every frame (port jumpered on the real card; default here 4).
  IDE/CF     OUT 2 = register select, port 3 = data (Mike Riley's 8-bit IDE). 8-bit mode, LBA28, sectors of 512.
  Bus lines with nothing driving them read 0xFF.
"""
import datetime, os
from .cpu import CPU1802
from .rtc import DS12885
from .uart import UART16550

FLOAT = 0xFF


def load_image(path, base=None):
    """-> {addr: byte} from Intel hex (.hex/.ihx/.intel/.img) or a binary file at base"""
    data = open(path, "rb").read()
    if data[:1] == b":":
        mem = {}; ext = 0
        for line in data.decode("ascii", "replace").splitlines():
            line = line.strip()
            if not line.startswith(":"): continue
            raw = bytes.fromhex(line[1:]); n, a, t = raw[0], raw[1] << 8 | raw[2], raw[3]
            if t == 0:
                for i, b in enumerate(raw[4:4 + n]): mem[(ext + a + i) & 0xFFFF] = b
            elif t == 1: break
            elif t == 4: ext = (raw[4] << 8 | raw[5]) << 16
        return mem
    if base is None: raise ValueError("binary image needs a load address")
    return {(base + i) & 0xFFFF: b for i, b in enumerate(data)}


class MemoryCard:
    """jumpers: 16 entries, one per 4K block, each 'RAM', 'ROM' or None"""
    def __init__(self, jumpers=None):
        self.jumpers = jumpers or (["RAM"] * 7 + [None] + ["ROM"] * 8)
        self.ram = bytearray(0x10000); self.rom = bytearray([FLOAT]) * 0x10000

    def owns(self, a): return self.jumpers[a >> 12] is not None
    def read(self, a):
        j = self.jumpers[a >> 12]
        return self.ram[a] if j == "RAM" else self.rom[a] if j == "ROM" else None
    def write(self, a, v):
        if self.jumpers[a >> 12] == "RAM": self.ram[a] = v


class CPUCardROM:
    def __init__(self, base=0xF000, size=0x1000):
        self.base, self.size = base, size; self.data = bytearray([FLOAT]) * size; self.remap = True; self.loaded = False
    def read(self, a):
        if self.base <= a < self.base + self.size: return self.data[a - self.base]
        if self.remap and a < self.size: return self.data[a]
        return None


class Video6845:
    """2K video RAM + CRTC. Text is read straight from video RAM; the CRTC start address (R12/R13) and cursor
    (R14/R15) are honoured; geometry comes from R1 (columns) and R6 (rows), 64x16 until the software sets them."""
    BASE, SIZE, CRTC = 0x7000, 0x800, 0x7800

    def __init__(self):
        self.vram = bytearray([0x20]) * self.SIZE; self.reg = [0] * 18; self.sel = 0
        self.reg[1], self.reg[6] = 64, 16; self.dirty = True

    def read(self, a):
        if self.BASE <= a < self.BASE + self.SIZE: return self.vram[a - self.BASE]
        if a == self.CRTC + 1 and self.sel in (14, 15, 16, 17): return self.reg[self.sel]
        if a in (self.CRTC, self.CRTC + 1): return FLOAT
        return None

    def write(self, a, v):
        if self.BASE <= a < self.BASE + self.SIZE: self.vram[a - self.BASE] = v; self.dirty = True; return True
        if a == self.CRTC: self.sel = v & 31; return True
        if a == self.CRTC + 1:
            if self.sel < 18: self.reg[self.sel] = v; self.dirty = True
            return True
        return False

    def geometry(self):
        cols = self.reg[1] or 64; rows = self.reg[6] or 16
        return min(cols, 80), min(rows, 32)

    def lines(self):
        cols, rows = self.geometry(); start = ((self.reg[12] << 8) | self.reg[13]) & 0x7FF
        out = []
        for r in range(rows):
            row = bytes(self.vram[(start + r * cols + c) & 0x7FF] for c in range(cols))
            out.append("".join(chr(b & 0x7F) if 32 <= (b & 0x7F) < 127 else " " for b in row))
        return out

    def cursor(self):
        """(row, col) of the cursor, or None"""
        cols, rows = self.geometry(); start = ((self.reg[12] << 8) | self.reg[13]) & 0x7FF
        pos = (((self.reg[14] << 8) | self.reg[15]) - start) & 0x7FF
        r, c = divmod(pos, cols)
        return (r, c) if r < rows else None


class Video6845Kbd(Video6845):
    """the 6845 card Rev B-Clean-Keyboard as the software sees it (hardware/video-6845/kicad/rev-b-clean-keyboard): Rev
    B's text RAM at 7000-77FF; in 7800-7BFF, by A1-A2, the 6845 (7800 / 7801), the key (7802: the read takes the next
    key into the latch and clears KEY-READY) and the status (7804: bit 0 KEY-READY, bit 7 = 1; VSYNC and DE, bits 2
    and 3, are not counted and read 0, as in the netlist model, hw.NetlistVideoKbdCard); the same every 8 addresses.
    Nothing at 7806 or in 7C00-7FFF, and nothing takes a write to the key or the status."""
    REGS, REGS_END = 0x7800, 0x7C00

    def __init__(self, kbd):
        super().__init__(); self.kbd = kbd; self.latch = 0

    def read(self, a):
        if self.BASE <= a < self.BASE + self.SIZE: return self.vram[a - self.BASE]
        if self.REGS <= a < self.REGS_END:
            r = (a >> 1) & 3
            if r == 0: return (self.reg[self.sel] if self.sel in (14, 15, 16, 17) else 0) if a & 1 else FLOAT
            if r == 1:                                  # the key latch keeps its byte until the ATmega loads the next
                if self.kbd.queue: self.latch = self.kbd.queue.pop(0)
                return self.latch
            if r == 2: return 0x80 | (1 if self.kbd.ready() else 0)
        return None

    def write(self, a, v):
        if self.BASE <= a < self.BASE + self.SIZE: self.vram[a - self.BASE] = v; self.dirty = True; return True
        if self.REGS <= a < self.REGS_END and (a >> 1) & 3 == 0:
            if a & 1:
                if self.sel < 18: self.reg[self.sel] = v; self.dirty = True
            else: self.sel = v & 31
            return True
        return False


class Keyboard:
    """the PS/2 -> PAK-VI -> PIC -> 1852 path, as the software sees it: INP 1 reads a character, EF3 = waiting"""
    def __init__(self, port=1):
        self.port = port; self.queue = []
    def press(self, text):
        for ch in text:
            self.queue.append(0x0D if ch == "\n" else ord(ch) & 0x7F)
    def ready(self): return bool(self.queue)
    def read(self): return self.queue.pop(0) if self.queue else FLOAT


class IDE:
    """8-bit IDE as the BIOS drives it: OUT 2 selects a register, port 3 reads/writes it.
    Registers 0 data, 1 error/features, 2 sector count, 3-5 the address, 6 drive/head, 7 status/command,
    0x0E device control. Commands: 20 read, 30 write, EC identify, EF set features, 91/10/E0-E1 accepted.

    As a real card (2026-11-15): register 6 bit 6 picks the addressing. Set (E0h, as HBIOS and ELF/OS 0.2.6 send),
    registers 3-5 and the low nibble of 6 are LBA 0-27. Clear, they are sector (3, counting from 1), cylinder (4-5)
    and head (6), in the geometry IDENTIFY reports. A read or a write of an address that is not on the card sets
    ERR, with ID not found (10h) in the error register, and no DRQ. This model once read every address as an LBA,
    so Elf/OS v5, which sends 00 in register 6, booted here while the real card refused it: HBIOS 1.0.6 sets E0h
    for it (firmware/hbios/v1.0.6/README.md)."""
    BSY, DRDY, DRQ, ERR = 0x80, 0x40, 0x08, 0x01
    IDNF = 0x10                                        # error register: the address is not on the card
    HEADS, SPT = 16, 63                                # the geometry IDENTIFY reports

    def __init__(self, image=None, sectors=65536):
        self.sel = 0; self.regs = [0] * 8; self.status = self.DRDY; self.buf = bytearray(); self.pos = 0
        self.writing = False; self.path = image; self.error = 0
        if image and os.path.exists(image):
            with open(image, "rb") as fh: self.disk = bytearray(fh.read())
        else:
            self.disk = bytearray(512 * sectors)
        self.dirty = False
        self.cyls = min(len(self.disk) // 512 // (self.HEADS * self.SPT), 16383)

    def lba(self):
        """the sector registers 3-6 name, or None if it is not on the card"""
        r = self.regs
        if r[6] & 0x40:
            l = ((r[6] & 0x0F) << 24) | (r[5] << 16) | (r[4] << 8) | r[3]
        else:
            cyl, head, sec = r[5] << 8 | r[4], r[6] & 0x0F, r[3]
            if not (1 <= sec <= self.SPT and head < self.HEADS and cyl < self.cyls): return None
            l = (cyl * self.HEADS + head) * self.SPT + sec - 1
        return l if l < len(self.disk) // 512 else None

    def _fail(self):
        """the address is not on the card: ERR and ID not found, as a real card answers"""
        self.status = self.DRDY | self.ERR; self.error = self.IDNF; self.writing = False; self.buf = bytearray(); self.pos = 0

    def out(self, port, v):
        if port == 2: self.sel = v; return
        r = self.sel
        if r == 0 and self.writing:
            self.buf[self.pos] = v; self.pos += 1
            if self.pos >= 512: self._commit()
        elif r == 7: self._command(v)
        elif r == 0x0E: self.status = self.DRDY; self.error = 0
        elif 1 <= r <= 6: self.regs[r] = v

    def inp(self, port):
        if port == 2: return FLOAT
        r = self.sel
        if r == 0:
            if self.status & self.DRQ and not self.writing:
                v = self.buf[self.pos]; self.pos += 1
                if self.pos >= len(self.buf):
                    self.regs[2] = (self.regs[2] - 1) & 0xFF
                    if self.regs[2]: self._next_read()
                    else: self.status = self.DRDY
                return v
            return FLOAT
        if r == 7: return self.status
        if r == 1: return self.error if self.status & self.ERR else 0
        if 2 <= r <= 6: return self.regs[r]
        return FLOAT

    def _next_read(self):
        self.regs_advance()
        l = self.lba()
        if l is None: self._fail(); return
        self.buf = self.disk[l * 512:(l + 1) * 512]; self.pos = 0; self.status = self.DRDY | self.DRQ

    def regs_advance(self):
        """on to the next sector of a multi-sector command, in the addressing register 6 picked"""
        r = self.regs; l = self.lba()
        if l is None: return
        l += 1
        if r[6] & 0x40:
            r[3], r[4], r[5] = l & 0xFF, (l >> 8) & 0xFF, (l >> 16) & 0xFF; r[6] = (r[6] & 0xF0) | ((l >> 24) & 0x0F)
        else:
            cyl, rest = divmod(l, self.HEADS * self.SPT); head, sec = divmod(rest, self.SPT)
            r[3], r[4], r[5] = sec + 1, cyl & 0xFF, (cyl >> 8) & 0xFF; r[6] = (r[6] & 0xF0) | head

    def _command(self, c):
        if c in (0x20, 0x30) and self.lba() is None:  # read or write of an address that is not on the card
            self._fail(); return
        if c == 0x20:                                  # read sectors
            l = self.lba()
            self.buf = self.disk[l * 512:(l + 1) * 512]; self.pos = 0; self.writing = False
            self.status = self.DRDY | self.DRQ; self.error = 0
        elif c == 0x30:                                # write sectors
            self.buf = bytearray(512); self.pos = 0; self.writing = True; self.status = self.DRDY | self.DRQ; self.error = 0
        elif c == 0xEC:                                # identify
            ident = bytearray(512); n = len(self.disk) // 512
            ident[120:124] = n.to_bytes(4, "little"); ident[98] = 0x00; ident[99] = 0x02     # LBA supported
            model = b"System-5 emulated CF".ljust(40)
            ident[54:94] = bytes(b for i in range(0, 40, 2) for b in (model[i + 1], model[i]))
            ident[2:4] = self.cyls.to_bytes(2, "little"); ident[6:8] = self.HEADS.to_bytes(2, "little"); ident[12:14] = self.SPT.to_bytes(2, "little")
            self.buf = ident; self.pos = 0; self.writing = False; self.regs[2] = 1; self.status = self.DRDY | self.DRQ; self.error = 0
        else:                                          # set features, init, recalibrate...: just ready
            self.status = self.DRDY; self.error = 0

    def _commit(self):
        l = self.lba()                                 # on the card: checked when the command came, and after each step
        self.disk[l * 512:(l + 1) * 512] = self.buf; self.dirty = True
        self.regs[2] = (self.regs[2] - 1) & 0xFF
        if self.regs[2]:
            self.regs_advance()
            if self.lba() is None: self._fail(); return
            self.buf = bytearray(512); self.pos = 0; self.status = self.DRDY | self.DRQ
        else:
            self.writing = False; self.status = self.DRDY

    def save(self):
        if self.path and self.dirty:
            open(self.path, "wb").write(self.disk); self.dirty = False


class CDP1861:
    """1861 Pixie: 64 x 128 (displayed as 64 x 32 by the usual 4x line repeat in software) via DMA from R0.
    Frame = 262 lines x 14 machine cycles. Interrupt 2 lines before display (line 78); display lines 80-207 each take
    8 DMA-out cycles; EF1 is active lines 76-79 and 204-207. INP port turns the display on, OUT port turns it off."""
    LINES, CPL = 262, 14

    def __init__(self, port=4):
        self.port = port; self.on = False; self.frame = bytearray(8 * 128); self.cyc = 0; self.line = 0; self.frames = 0

    def ef1(self): return self.on and (76 <= self.line <= 79 or 204 <= self.line <= 207)

    def advance(self, cpu, cycles):
        """run the 1861 for `cycles` machine cycles of CPU time (interrupt and DMA happen here)"""
        self.cyc += cycles
        while self.cyc >= self.CPL:
            self.cyc -= self.CPL; self.line += 1
            if self.line >= self.LINES: self.line = 0; self.frames += 1
            if not self.on: continue
            if self.line == 78: cpu.int_line = True
            elif self.line == 79: cpu.int_line = False
            if 80 <= self.line < 208:
                row = self.line - 80
                for i in range(8): self.frame[row * 8 + i] = cpu.dma_out()

    def bitmap(self):
        """-> 128 rows of 64 booleans"""
        return [[bool(self.frame[r * 8 + c // 8] & (0x80 >> (c % 8))) for c in range(64)] for r in range(128)]


PANEL_MODES = {(True, False): "run", (True, True): "pause", (False, False): "reset", (False, True): "load"}


class IOPanel:
    """The IO panel card (hardware/io-panel/kicad/rev-a, designed 2026-10-30, not built) as behaviour, for the fast
    machine (--panel A; --hw --panel A runs it from its netlist instead). OUT 4 latches the byte the 8 LEDs and the two
    TIL311s show; INP 4 reads the 8 toggles; INPUT pulls -EF1 (the 1802's EF1) while it is held; RUN off holds the
    machine in reset, LOAD on pauses it, and both together are LOAD mode, where each INPUT press stores the toggles at
    M(R0) (one DMA IN). The real card needs the 36-pin bus and CPU Rev D for INPUT, RUN and LOAD.
    Its real-time clock (2026-11-18), a DS12885 (rtc.py), answers on ports 6 (the register number) and 7 (the register),
    as JP4 is set; here it starts running at the host's time, as if it had been set before.
    Its serial port (2026-11-20), a 16C550 (uart.py), shares those two ports: a byte with
    bit 7 set written to port 6 picks the UART's register (80h-87h), one with bit 7 clear the clock's, and port 7 then
    reads or writes the chip picked. `uart.receive()` puts characters on its line; `uart.tx` is what it has sent."""
    name = "panel"
    port = 4
    rtc_ports = (6, 7)

    def __init__(self, rtc=None, uart=None):
        self.switches, self.pressed, self.run_on, self.load_on = 0, False, True, False
        self.latch = None                               # the '374 powers up undefined
        self.rtc = rtc if rtc is not None else DS12885(start=datetime.datetime.now())
        self.uart = uart if uart is not None else UART16550()
        self.select = 0x00                              # the byte last written to the address port (U22 holds bits 7 and
        #                                                 2-0; the real latch powers up undefined: here the clock is picked)

    def out_addr(self, v):
        self.select = v & 0xFF; self.rtc.write_addr(v)  # the DS12885 latches every address, selected or not

    def out_data(self, v):
        if self.select & 0x80: self.uart.write(self.select & 7, v)
        else: self.rtc.write_data(v)

    def inp_data(self):
        return self.uart.read(self.select & 7) if self.select & 0x80 else self.rtc.read_data()

    def mode(self): return PANEL_MODES[(self.run_on, self.load_on)]

    def leds(self):
        if self.latch is None: return "LEDs ????????  TIL311 ??"
        return "LEDs %s  TIL311 %02X" % ("".join("*" if self.latch >> k & 1 else "." for k in range(7, -1, -1)), self.latch)


class Machine:
    def __init__(self, cpu_rom=None, rom_lo=None, rom_hi=None, disk=None, jumpers=None, rom_base=0xF000, pixie_port=4,
                 panel=None):
        self.memory = MemoryCard(jumpers); self.cpurom = CPUCardROM(rom_base); self.video = Video6845()
        self.panel = IOPanel() if panel else None       # the IO panel card on port 4
        if self.panel and pixie_port == IOPanel.port: pixie_port = 0    # the 1861 off port 4, as on the real IO card
        self.held = False                               # the panel's RUN off or LOAD on: the 1802 is not running
        self.loaded = False                             # LOAD mode since the last reset (CPU Rev D's LOADED flag)
        self.kbd = Keyboard(); self.ide = IDE(disk); self.pixie = CDP1861(pixie_port)
        self.q_level = 0; self.watch = None           # watch(kind, addr, value) hook for the debugger
        self.rom_name = None                            # the CPU card ROM's file, for the page
        self.cpu = CPU1802(self)
        self.cpurom.remap = False
        if cpu_rom: self.load_cpu_rom(cpu_rom)
        for path in (rom_lo, rom_hi):
            if path: self.load_rom(path)

    # ------------------------------------------------------------------ images
    def load_cpu_rom(self, path):
        img = load_image(path, self.cpurom.base) if os.path.getsize(path) else {}
        for a, b in img.items():
            if self.cpurom.base <= a < self.cpurom.base + self.cpurom.size: self.cpurom.data[a - self.cpurom.base] = b
        self.cpurom.loaded = bool(img); self.cpurom.remap = self.cpurom.loaded     # no EPROM fitted: nothing to remap
        self.rom_name = os.path.basename(path) if img else None
        return len(img)

    def load_rom(self, path, base=0x8000):
        img = load_image(path, base)
        for a, b in img.items(): self.memory.rom[a] = b
        return len(img)

    def load_ram(self, path, base=0):
        img = load_image(path, base)
        for a, b in img.items(): self.write(a, b)
        return img

    # ------------------------------------------------------------------ bus (the CPU calls these)
    def peek(self, a):
        """what a read returns, without side effects (no remap change, no watch)"""
        v = self.cpurom.read(a)
        if v is not None and (self.cpurom.base <= a or self.cpurom.remap): return v
        v = self.video.read(a)
        if v is not None: return v
        v = self.memory.read(a)
        return FLOAT if v is None else v

    def read(self, a):
        if a & 0x8000: self.cpurom.remap = False
        v = self.peek(a)
        if self.watch: self.watch("r", a, v)
        return v

    def fetch(self, a):
        if a & 0x8000: self.cpurom.remap = False
        return self.peek(a)

    def write(self, a, v):
        if a & 0x8000: self.cpurom.remap = False
        if self.watch: self.watch("w", a, v)
        if self.video.write(a, v): return
        if self.cpurom.base <= a < self.cpurom.base + self.cpurom.size: return
        self.memory.write(a, v)

    def out(self, n, v):
        if n in (2, 3): self.ide.out(n, v)
        if n == self.pixie.port: self.pixie.on = False
        if self.panel and n == self.panel.port: self.panel.latch = v
        if self.panel and n == self.panel.rtc_ports[0]: self.panel.out_addr(v)
        if self.panel and n == self.panel.rtc_ports[1]: self.panel.out_data(v)
        if self.watch: self.watch("o", n, v)

    def inp(self, n):
        v = FLOAT
        if n in (2, 3): v = self.ide.inp(n)
        if n == self.kbd.port: v = self.kbd.read()
        if n == self.pixie.port: self.pixie.on = True
        if self.panel and n == self.panel.port: v = self.panel.switches
        if self.panel and n == self.panel.rtc_ports[1]: v = self.panel.inp_data()
        if self.watch: self.watch("i", n, v)
        return v

    def ef(self, n):
        if n == 3: return self.kbd.ready()
        if n == 1: return bool(self.panel and self.panel.pressed) or self.pixie.ef1()
        return False

    # ------------------------------------------------------------------ the IO panel's hand controls
    def panel_set(self, switches=None, input=None, run=None, load=None):
        """the IO panel's toggles (byte), INPUT (pressed), RUN and LOAD, as a person at the front panel would. RUN off
        resets and holds the 1802; LOAD on pauses it; both = LOAD mode, where each INPUT press stores the toggles at M(R0)
        and R0 counts on. After LOAD mode, RUN runs RAM from 0000 (CPU Rev D's LOADED flag); otherwise a reset boots the
        ROM as the Reset button does."""
        p = self.panel; was_pressed = p.pressed; before = p.mode()
        if switches is not None: p.switches = switches & 0xFF
        if input is not None: p.pressed = bool(input)
        if run is not None: p.run_on = bool(run)
        if load is not None: p.load_on = bool(load)
        now = p.mode()
        if now == "load": self.loaded = True; self.cpurom.remap = False    # LOADED: the boot map is off, 0000 is RAM
        if now == "reset" and before != "reset":       # CLEAR low, WAIT high: the 1802 resets (R0 = 0000)
            self.cpu.reset(); self.pixie.on = False     # (in LOAD mode R0 counts the bytes instead)
            p.uart.reset()                              # -RESET low: the UART's MR
            self.cpurom.remap = self.cpurom.loaded and not self.loaded
        self.held = now != "run"
        if now == "load" and p.pressed and not was_pressed: self.cpu.dma_in(p.switches)
        return self.panel_text()

    def panel_text(self):
        p = self.panel
        return "%s  Q %s   toggles %s (%02X)  INPUT %s  RUN %s  LOAD %s   mode %s" % (
            p.leds(), "*" if self.cpu.Q else ".", "".join("1" if p.switches >> k & 1 else "0" for k in range(7, -1, -1)),
            p.switches, "down" if p.pressed else "up", "on" if p.run_on else "off", "on" if p.load_on else "off",
            p.mode() if p.mode() != "load" else "LOAD")

    def q(self, level): self.q_level = level

    # ------------------------------------------------------------------ running
    def reset(self):
        self.cpu.reset(); self.cpurom.remap = self.cpurom.loaded; self.pixie.on = False; self.loaded = False
        if self.panel: self.panel.uart.reset()          # the bus -RESET is the UART's MR (inverted on the card)

    def step(self):
        if self.panel and self.held:                    # reset or paused by the IO panel: no instruction
            self.cpu.cycles += 1; return None
        c0 = self.cpu.cycles; op = self.cpu.step()
        self.pixie.advance(self.cpu, self.cpu.cycles - c0)
        return op


class Video6845KbdMachine(Machine):
    """System-5 with the 6845 card Rev B-Clean-Keyboard in place of the 6845 card and the IO card: Rev B's video with
    the PS/2 keyboard on the same card, the key at 7802 and the status at 7804 (Video6845Kbd). No 1861 and nothing on
    INP 1; EF3 is KEY-READY (the card's JP1 on the bus -EF). Use it with the VIDEO-G HBIOS (roms/hbios-video-g.rom),
    which polls 7804 and reads 7802; the IO panel may be fitted (panel=True)."""
    def __init__(self, **kw):
        kw["pixie_port"] = 0                               # no IO card: port 0 is never an INP / OUT
        super().__init__(**kw)
        self.kbd.port = None                               # the key is memory-mapped: not on INP 1
        self.video = Video6845Kbd(self.kbd)
