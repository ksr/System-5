# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-18
"""DS12885 real-time clock as behaviour: the IO panel card's U13 (hardware/io-panel/kicad/rev-a; Maxim's DS12885 data
sheet, Rev 3 2/07; the chip is MC146818-compatible).

On the card it has two ports (JP4; 6 and 7 as set): an OUT to the address port latches a register number (AS), an OUT
to the data port writes that register, an INP of the data port reads it. The registers:

  00 seconds  01 seconds alarm  02 minutes  03 minutes alarm  04 hours  05 hours alarm
  06 day of the week (1 = Sunday)  07 date  08 month  09 year (00-99: 2000-2099)
  0A  A: UIP (bit 7, read only), DV2-DV0 (bits 6-4; 010 = the oscillator runs and the clock counts), RS3-RS0
  0B  B: SET (bit 7: the clock stops so it can be set), PIE, AIE, UIE, SQWE, DM (bit 2: 1 = binary, 0 = BCD),
      24/12 (bit 1: 1 = 24-hour), DSE
  0C  C: IRQF, PF, AF, UF (read only; a read clears them)       0D  D: VRT (bit 7: the battery is good)
  0E-7F  114 bytes of RAM, kept by the battery

The clock runs from the host's clock plus an offset, as the chip runs from its crystal: it counts while DV is 010 and
SET is clear, and stands still otherwise. A new chip has its oscillator off (DV = 000), as the DS12885 is shipped, so
software has to start it (HBIOS v1.0.8 does, when it sets the time).

Not modelled: the alarms and interrupts (IRQ stays high), the square wave, daylight saving, UIP (always 0: an update is
never in progress when software looks).
"""
import datetime


def bcd(v): return (v // 10) << 4 | v % 10
def unbcd(b): return (b >> 4) * 10 + (b & 0x0F)


class DS12885:
    TIME = (0x00, 0x02, 0x04, 0x06, 0x07, 0x08, 0x09)       # the registers the clock counts

    def __init__(self, now=None, start=None):
        """now: the host's clock (a function returning a datetime; for tests). start: a datetime to start the clock
        at, running in binary 24-hour mode, as if software had set it; None = a new chip, oscillator off"""
        self.now = now or datetime.datetime.now
        self.ram = bytearray(128); self.ram[0x0D] = 0x80        # VRT: the battery is good
        self.addr = 0
        self.base = datetime.datetime(2000, 1, 1)                # the clock's time at host time self.at (or stopped)
        self.at = None
        self.dow = 0                                             # what software wrote to the day-of-week register, less
        if start is not None:                                    # the day the date gives
            self.ram[0x0A] = 0x20; self.ram[0x0B] = 0x06; self.base = start; self.at = self.now()

    # ---- the clock
    def running(self): return (self.ram[0x0A] >> 4) & 7 == 2 and not self.ram[0x0B] & 0x80

    def time(self):
        """the clock's date and time now"""
        return self.base + (self.now() - self.at) if self.at is not None else self.base

    def _stop(self): self.base = self.time(); self.at = None
    def _go(self):
        if self.running() and self.at is None: self.at = self.now()

    def _enc(self, v): return v if self.ram[0x0B] & 0x04 else bcd(v)
    def _dec(self, b): return b if self.ram[0x0B] & 0x04 else unbcd(b)

    def _read_time(self, r):
        t = self.time()
        if r == 0x00: return self._enc(t.second)
        if r == 0x02: return self._enc(t.minute)
        if r == 0x04:
            if self.ram[0x0B] & 0x02: return self._enc(t.hour)
            return self._enc(t.hour % 12 or 12) | (0x80 if t.hour >= 12 else 0)
        if r == 0x06: return (t.isoweekday() % 7 + self.dow) % 7 + 1          # Sunday = 1
        if r == 0x07: return self._enc(t.day)
        if r == 0x08: return self._enc(t.month)
        return self._enc(t.year % 100)

    def _write_time(self, r, b):
        was = self.running(); self._stop(); t = self.base
        try:
            if r == 0x00: t = t.replace(second=self._dec(b))
            elif r == 0x02: t = t.replace(minute=self._dec(b))
            elif r == 0x04:
                if self.ram[0x0B] & 0x02: h = self._dec(b)
                else: h = self._dec(b & 0x7F) % 12 + (12 if b & 0x80 else 0)
                t = t.replace(hour=h)
            elif r == 0x06: self.dow = ((b - 1) - t.isoweekday() % 7) % 7
            elif r == 0x07: t = t.replace(day=self._dec(b))
            elif r == 0x08: t = t.replace(month=self._dec(b))
            elif r == 0x09: t = t.replace(year=2000 + self._dec(b))
        except ValueError:
            pass                                                # no such date (31 June ...): the model keeps the old one
        self.base = t
        if was: self._go()

    # ---- the bus side: the card's two ports
    def write_addr(self, v): self.addr = v & 0x7F

    def write_data(self, v):
        r, v = self.addr, v & 0xFF
        if r in self.TIME: self._write_time(r, v); return
        if r == 0x0A:
            self._stop(); self.ram[r] = v & 0x7F; self._go(); return             # UIP is read only
        if r == 0x0B:
            self._stop(); self.ram[r] = v; self._go(); return
        if r in (0x0C, 0x0D): return                                             # read only
        self.ram[r] = v                                                          # the alarms and the RAM

    def read_data(self):
        r = self.addr
        if r in self.TIME: return self._read_time(r)
        if r == 0x0C: v = self.ram[r]; self.ram[r] = 0; return v
        return self.ram[r]

    def describe(self):
        t = self.time()
        return "DS12885 at %s, %s; register %02X selected" % (t.strftime("%Y-%m-%d %H:%M:%S"),
                                                             "running" if self.running() else "stopped", self.addr)
