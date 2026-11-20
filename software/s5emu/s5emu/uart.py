# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-20
"""16C550 UART as behaviour: the IO panel card's U20 (hardware/io-panel/kicad/rev-a, 2026-11-20; the registers are
the NS16550A's, which the XR16C550, TL16C550C and PC16550D share).

On the card it sits on the RTC's port pair (JP4; 6 and 7 as set). The byte written to the address port picks the chip
and the register: 80h-87h = the UART's register 0-7 (bit 7 set), 00h-7Fh = the DS12885's. An OUT to the data port
then writes that register, an INP reads it. The registers:

  0  RBR (read): the received character      THR (write): a character to send      DLAB = 1: DLL, the divisor's low byte
  1  IER: interrupt enables (bit 0 received data, bit 1 THR empty, 2 line status, 3 modem status)   DLAB = 1: DLM
  2  IIR (read): bit 0 = 0 while an interrupt is pending, bits 3-1 which (010 received data, 001 THR empty),
     bits 7-6 set with the FIFOs on              FCR (write): bit 0 FIFOs on, bit 1 clear the receive FIFO, 2 the send
  3  LCR: word length, stop bits, parity; bit 7 = DLAB
  4  MCR: DTR, RTS, OUT1, OUT2, bit 4 = loop (what is sent comes back in; the modem inputs follow MCR's outputs)
  5  LSR (read): bit 0 DR (a character is waiting), bit 5 THRE, bit 6 TEMT
  6  MSR (read): the modem inputs. On the card -CTS, -DSR, -DCD and -RI are tied high (off): 00, except in loop mode
  7  SCR: a scratch byte

The clock is the card's X1, 1.8432 MHz: baud = 1843200 / 16 / divisor (12 = 9600, 3 = 38400).

What it leaves out: time. A character written to THR is sent at once (it is in `tx`, what a terminal on J2 would have
got), so THRE and TEMT are always set; received characters wait in a queue of any length and never overrun; no parity,
framing or break errors; the word length and the baud rate change nothing.
"""
import collections


class UART16550:
    CLOCK = 1843200

    def __init__(self):
        self.tx = bytearray()                  # every character sent, in order (the line to the terminal)
        self.rx = collections.deque()          # characters received and not yet read
        self.dll, self.dlm, self.scr = 0, 0, 0   # not touched by a reset (MR)
        self.reset()

    def reset(self):
        """MR, the card's RESET_H: the registers as the data sheet's reset table has them"""
        self.ier, self.lcr, self.mcr, self.fcr = 0, 0, 0, 0
        self.thre_pending = False              # the THR-empty interrupt waits to be seen

    # ---- the line side
    def receive(self, data):
        """characters arriving on the line (bytes or a str)"""
        if isinstance(data, str): data = data.encode("latin-1")
        self.rx.extend(data)

    def sent(self):
        """what the UART has sent since the last call"""
        b = bytes(self.tx); del self.tx[:]
        return b

    def baud(self):
        d = self.dlm << 8 | self.dll
        return self.CLOCK / 16 / d if d else None

    # ---- the interrupt pin
    def _cause(self):
        """the interrupt pending now, highest priority first: 0x04 received data, 0x02 THR empty; None"""
        if self.ier & 0x01 and self.rx: return 0x04
        if self.ier & 0x02 and self.thre_pending: return 0x02
        return None

    def intr(self): return self._cause() is not None

    # ---- the bus side
    def write(self, reg, v):
        reg &= 7; v &= 0xFF; dlab = self.lcr & 0x80
        if reg == 0:
            if dlab: self.dll = v; return
            self.thre_pending = True           # sent at once: the holding register is empty again
            if self.mcr & 0x10: self.rx.append(v)   # loop mode: it comes back in, and nothing leaves
            else: self.tx.append(v)
        elif reg == 1:
            if dlab: self.dlm = v; return
            if v & 0x02 and not self.ier & 0x02: self.thre_pending = True    # enabling it with THR empty raises it
            self.ier = v & 0x0F
        elif reg == 2:
            self.fcr = v & 0xC9 if v & 0x01 else 0
            if v & 0x02: self.rx.clear()       # (turning the FIFOs on or off alone keeps the queue: it is the line too)
        elif reg == 3: self.lcr = v
        elif reg == 4: self.mcr = v & 0x1F
        elif reg == 7: self.scr = v
        # 5 and 6 (LSR, MSR): writes do nothing

    def read(self, reg):
        reg &= 7; dlab = self.lcr & 0x80
        if reg == 0:
            if dlab: return self.dll
            return self.rx.popleft() if self.rx else 0x00
        if reg == 1: return self.dlm if dlab else self.ier
        if reg == 2:
            c = self._cause(); v = (0xC0 if self.fcr & 0x01 else 0) | (0x01 if c is None else c)
            if c == 0x02: self.thre_pending = False     # reading IIR while it reports THR empty clears that
            return v
        if reg == 3: return self.lcr
        if reg == 4: return self.mcr
        if reg == 5: return 0x60 | (0x01 if self.rx else 0)
        if reg == 6:
            if self.mcr & 0x10:                # loop: CTS = RTS, DSR = DTR, RI = OUT1, DCD = OUT2
                m = self.mcr; return (m & 0x02) << 3 | (m & 0x01) << 5 | (m & 0x04) << 4 | (m & 0x08) << 4
            return 0x00
        return self.scr

    def describe(self):
        b = self.baud()
        return "16C550: %s baud, %d character(s) waiting, %d sent, FIFOs %s, interrupt %s" % (
            "%d" % b if b else "no", len(self.rx), len(self.tx), "on" if self.fcr & 1 else "off", "pending" if self.intr() else "none")
