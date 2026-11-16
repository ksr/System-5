# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-06
"""RCA CDP1802 instruction-level CPU.

The bus is an object with read(addr), write(addr, val), out(n, val), inp(n) -> val, ef(n) -> bool (n = 1..4) and an
optional fetch(addr) used for opcode/operand fetches (defaults to read). Every instruction is 2 machine cycles
(16 clocks), long branches and skips 3 (24 clocks); `cycles` counts machine cycles.
Interrupts: set cpu.int_line = True; taken between instructions when IE = 1 (T <- X,P; X = 2; P = 1; IE = 0).
Opcode 0x68 is not an 1802 instruction (it is the 1804/5/6's prefix), but the 1802 runs it: as an INP with no port
selected (N = 0), so whatever is on the data bus goes to M(R(X)) and D. Programs use that to tell the processors
apart (Elf/OS v5's sysinfo: 68 B7 is RNX R7 on an 1805, and that stray write followed by PHI R7 on an 1802). The CPU
does the same; with cpu.stop_on_68 = True it raises IllegalOp there instead, so a debugger can catch a program
that has run off into data.
"""


class IllegalOp(Exception):
    pass


BUS_FLOATS = 0xFF             # a data bus nobody drives reads FF (pull-ups; machine.FLOAT says the same)


class CPU1802:
    stop_on_68 = False        # True: stop on opcode 68 (IllegalOp) and not run it as the 1802 does

    def __init__(self, bus):
        self.bus = bus
        self.reset()

    def reset(self):
        self.R = [0] * 16
        self.D = 0; self.DF = 0; self.X = 0; self.P = 0; self.T = 0; self.IE = 1; self.Q = 0
        self.N = 0; self.I = 0
        self.idle = False; self.int_line = False
        self.cycles = 0; self.instructions = 0

    # ------------------------------------------------------------------ helpers
    def _fetch(self):
        r = self.R[self.P]
        v = self.bus.fetch(r) if hasattr(self.bus, "fetch") else self.bus.read(r)
        self.R[self.P] = (r + 1) & 0xFFFF
        return v

    def _cond(self, n):
        """branch/skip condition for the low 3 bits of a short/long branch opcode (bit 3 inverts)"""
        c = n & 7
        if c == 0: t = True
        elif c == 1: t = self.Q == 1
        elif c == 2: t = self.D == 0
        elif c == 3: t = self.DF == 1
        else: t = bool(self.bus.ef(c - 3))           # 4..7 -> EF1..EF4
        return t if not (n & 8) else not t

    def dma_out(self):
        """one DMA-out cycle (1861 video): the byte at R0 goes to the device, R0 + 1"""
        v = self.bus.read(self.R[0]); self.R[0] = (self.R[0] + 1) & 0xFFFF; self.cycles += 1; self.idle = False
        return v

    def dma_in(self, v):
        """one DMA-in cycle (LOAD mode, the IO panel's INPUT): the byte goes to M(R0), R0 + 1"""
        self.bus.write(self.R[0], v); self.R[0] = (self.R[0] + 1) & 0xFFFF; self.cycles += 1

    def interrupt(self):
        self.T = (self.X << 4) | self.P
        self.X = 2; self.P = 1; self.IE = 0; self.idle = False
        self.cycles += 1

    # ------------------------------------------------------------------ one instruction
    def step(self):
        """execute one instruction (or take a pending interrupt); returns the opcode executed, or None"""
        if self.int_line and self.IE:
            self.interrupt()
            return None
        if self.idle:
            self.cycles += 1
            return None
        pc = self.R[self.P]
        op = self._fetch()
        self.I = op >> 4; self.N = n = op & 15
        R = self.R; bus = self.bus
        self.cycles += 2; self.instructions += 1
        hi = self.I
        if hi == 0:
            if n == 0: self.idle = True
            else: self.D = bus.read(R[n])
        elif hi == 1: R[n] = (R[n] + 1) & 0xFFFF
        elif hi == 2: R[n] = (R[n] - 1) & 0xFFFF
        elif hi == 3:
            if n == 8:                                # SKP (NBR): skip one byte
                R[self.P] = (R[self.P] + 1) & 0xFFFF
            else:
                target = self._fetch()
                if self._cond(n):                     # the target replaces the low byte of the operand's address
                    R[self.P] = ((pc + 1) & 0xFF00) | target
        elif hi == 4:
            self.D = bus.read(R[n]); R[n] = (R[n] + 1) & 0xFFFF
        elif hi == 5: bus.write(R[n], self.D)
        elif hi == 6:
            if n == 0: R[self.X] = (R[self.X] + 1) & 0xFFFF                 # IRX
            elif n < 8: bus.out(n, bus.read(R[self.X])); R[self.X] = (R[self.X] + 1) & 0xFFFF   # OUT n
            elif n == 8 and self.stop_on_68:
                R[self.P] = pc; self.instructions -= 1; self.cycles -= 2
                raise IllegalOp("opcode 68 at %04X (1806 prefix, not an 1802 instruction)" % pc)
            else:                                     # INP n-8
                # 68 selects no port (N = 0), so no card sees an input cycle and nothing drives the bus: it floats.
                # Not bus.inp(0): a machine may park a card that is on no port there (the 1861 with the IO panel).
                v = bus.inp(n - 8) & 0xFF if n > 8 else BUS_FLOATS
                bus.write(R[self.X], v); self.D = v
        elif hi == 7: self._op7(n)
        elif hi == 8: self.D = R[n] & 0xFF
        elif hi == 9: self.D = R[n] >> 8
        elif hi == 10: R[n] = (R[n] & 0xFF00) | self.D
        elif hi == 11: R[n] = (R[n] & 0x00FF) | (self.D << 8)
        elif hi == 12: self._long(n)
        elif hi == 13: self.P = n
        elif hi == 14: self.X = n
        else: self._opF(n)
        return op

    def _long(self, n):
        R = self.R; P = self.P
        self.cycles += 1
        if n == 4: return                             # NOP (3 cycles)
        if n & 4:                                     # long skips: C5 LSNQ C6 LSNZ C7 LSNF C8 LSKP CC LSIE CD LSQ CE LSZ CF LSDF
            c = {5: self.Q == 0, 6: self.D != 0, 7: self.DF == 0, 12: self.IE == 1, 13: self.Q == 1, 14: self.D == 0,
                 15: self.DF == 1}[n]
            if c: R[P] = (R[P] + 2) & 0xFFFF
            return
        if n == 8:                                    # LSKP
            R[P] = (R[P] + 2) & 0xFFFF; return
        hi = self._fetch(); lo = self._fetch()
        if self._cond(n): R[self.P] = (hi << 8) | lo

    def _op7(self, n):
        R = self.R; bus = self.bus; X = self.X
        if n in (0, 1):                               # RET / DIS
            v = bus.read(R[X]); R[X] = (R[X] + 1) & 0xFFFF
            self.X = v >> 4; self.P = v & 15; self.IE = 1 if n == 0 else 0
        elif n == 2: self.D = bus.read(R[X]); R[X] = (R[X] + 1) & 0xFFFF        # LDXA
        elif n == 3: bus.write(R[X], self.D); R[X] = (R[X] - 1) & 0xFFFF         # STXD
        elif n == 4: self._add(bus.read(R[X]), self.DF)                          # ADC
        elif n == 5: self._sub(bus.read(R[X]), self.D, self.DF)                  # SDB  M - D - !DF
        elif n == 6:                                                             # SHRC
            c = self.D & 1; self.D = (self.D >> 1) | (self.DF << 7); self.DF = c
        elif n == 7: self._sub(self.D, bus.read(R[X]), self.DF)                  # SMB  D - M - !DF
        elif n == 8: bus.write(R[X], self.T)                                     # SAV
        elif n == 9:                                                             # MARK
            self.T = (X << 4) | self.P; bus.write(R[2], self.T); self.X = self.P; R[2] = (R[2] - 1) & 0xFFFF
        elif n == 10: self.Q = 0; self._q()                                      # REQ
        elif n == 11: self.Q = 1; self._q()                                      # SEQ
        elif n == 12: self._add(self._fetch(), self.DF)                          # ADCI
        elif n == 13: self._sub(self._fetch(), self.D, self.DF)                  # SDBI
        elif n == 14:                                                            # SHLC
            c = self.D >> 7; self.D = ((self.D << 1) & 0xFF) | self.DF; self.DF = c
        else: self._sub(self.D, self._fetch(), self.DF)                          # SMBI

    def _opF(self, n):
        R = self.R; bus = self.bus
        if n in (8, 9, 10, 11, 12, 13, 15): m = self._fetch()                    # immediate forms
        elif n in (6, 14): m = 0
        else: m = bus.read(R[self.X])
        if n == 0 or n == 8: self.D = m                                          # LDX / LDI
        elif n == 1 or n == 9: self.D |= m                                       # OR / ORI
        elif n == 2 or n == 10: self.D &= m                                      # AND / ANI
        elif n == 3 or n == 11: self.D ^= m                                      # XOR / XRI
        elif n == 4 or n == 12: self._add(m, 0)                                  # ADD / ADI
        elif n == 5 or n == 13: self._sub(m, self.D, 1)                          # SD / SDI   M - D
        elif n == 6: self.DF = self.D & 1; self.D >>= 1                          # SHR
        elif n == 7 or n == 15: self._sub(self.D, m, 1)                          # SM / SMI   D - M
        elif n == 14: self.DF = self.D >> 7; self.D = (self.D << 1) & 0xFF       # SHL

    def _add(self, m, c):
        s = self.D + m + c; self.D = s & 0xFF; self.DF = s >> 8

    def _sub(self, a, b, df):
        """a - b - (not df); DF = 1 when there was no borrow"""
        s = a - b - (1 - df); self.D = s & 0xFF; self.DF = 1 if s >= 0 else 0

    def _q(self):
        if hasattr(self.bus, "q"): self.bus.q(self.Q)

    # ------------------------------------------------------------------ state
    def state(self):
        return dict(R=list(self.R), D=self.D, DF=self.DF, X=self.X, P=self.P, T=self.T, IE=self.IE, Q=self.Q,
                    idle=self.idle, cycles=self.cycles, instructions=self.instructions)
