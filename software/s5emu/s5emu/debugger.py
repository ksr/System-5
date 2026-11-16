# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-06
"""Debug engine shared by the terminal and browser front ends.

Breakpoints (PC), watchpoints (memory read/write, I/O port in/out), step, step over (CALL via SEP or the SCRT
'SEP R4' convention), run until a stop or a cycle budget, a trace ring, symbols from rcasm/A18 listings, and the
SCRT call stack (R2 stack, R6 return addresses, as Mike Riley's BIOS/ELF-OS use: SEP R4 = call, SEP R5 = return).
"""
import re, collections
from .disasm import disasm


class Stop(Exception):
    pass


class Debugger:
    def __init__(self, machine):
        self.m = machine; self.cpu = machine.cpu
        self.breaks = set(); self.watches = {}      # (kind, addr) -> 'r'/'w'/'i'/'o'
        self.trace = collections.deque(maxlen=2000); self.tracing = True
        self.symbols = {}; self.addr_of = {}
        self.reason = ""; self._hit = None
        machine.watch = self._on_access
        self.running = False

    # ------------------------------------------------------------------ symbols
    def load_symbols(self, path):
        """rcasm '.lst' / A18 '.prn' style: lines 'ADDR  bytes  LABEL: ...' or 'LABEL: equ VALUE'"""
        n = 0
        for line in open(path, errors="replace"):
            e = re.search(r'([A-Za-z_]\w*):?\s+equ\s+([0-9][0-9A-Fa-f]*)[hH]\b', line)
            if e:                                     # 'name: equ 0ff54h' - the value, not the listing address
                a = int(e.group(2), 16) & 0xFFFF; self.symbols.setdefault(a, e.group(1)); self.addr_of[e.group(1).lower()] = a; n += 1
                continue
            if re.search(r'\bequ\b', line, re.I): continue          # an equ with an expression: no reliable address
            m = re.match(r'^\s*(?:\d+\s+)?([0-9A-Fa-f]{4})[:\s]+(?:[0-9A-Fa-f]{2}\s+)*\s*([A-Za-z_][\w]*):', line)
            if m:
                a = int(m.group(1), 16); self.symbols.setdefault(a, m.group(2)); self.addr_of[m.group(2).lower()] = a; n += 1
        return n

    def sym(self, a):
        return self.symbols.get(a)

    def addr(self, text):
        t = text.strip().lower()
        if t in self.addr_of: return self.addr_of[t]
        if t.startswith("r") and t[1:] and all(c in "0123456789abcdef" for c in t[1:]) and len(t) <= 3:
            return self.cpu.R[int(t[1:], 16)]
        if t in ("pc", "rp"): return self.pc()
        if t.startswith("$"): return int(t[1:], 16)
        if t.startswith("0x"): return int(t, 16)
        if t.endswith("h"): return int(t[:-1], 16)
        return int(t, 16)

    # ------------------------------------------------------------------ state
    def pc(self): return self.cpu.R[self.cpu.P]

    def dis(self, a=None, count=1):
        a = self.pc() if a is None else a; out = []
        for _ in range(count):
            ln, text = disasm(self.m.peek, a, self.symbols)
            out.append((a, bytes(self.m.peek((a + k) & 0xFFFF) for k in range(ln)), text)); a = (a + ln) & 0xFFFF
        return out

    def regs_text(self):
        c = self.cpu
        r = "  ".join("R%X=%04X" % (i, c.R[i]) for i in range(16))
        return ("D=%02X DF=%d X=%X P=%X T=%02X IE=%d Q=%d %s  cyc=%d ins=%d" %
                (c.D, c.DF, c.X, c.P, c.T, c.IE, c.Q, "IDLE" if c.idle else "", c.cycles, c.instructions), r)

    def call_stack(self, depth=8):
        """SCRT return addresses: R6 = current return address, older ones pushed on the R2 stack (hi, lo)"""
        out = [self.cpu.R[6]]; sp = self.cpu.R[2]
        for _ in range(depth - 1):
            lo = self.m.peek((sp + 1) & 0xFFFF); hi = self.m.peek((sp + 2) & 0xFFFF)
            if hi == 0xFF and lo == 0xFF: break
            out.append(hi << 8 | lo); sp = (sp + 2) & 0xFFFF
        return out

    # ------------------------------------------------------------------ watch hook
    def _on_access(self, kind, a, v):
        k = self.watches.get((kind, a))
        if k is not None and self._hit is None:
            self._hit = "%s %s%04X = %02X" % ({"r": "read", "w": "write", "i": "INP", "o": "OUT"}[kind], "" if kind in "rw" else "port ", a, v)

    # ------------------------------------------------------------------ execution
    def step(self):
        pc = self.pc(); p = self.cpu.P
        if self.tracing:
            ln, text = disasm(self.m.peek, pc, self.symbols)
            self.trace.append((pc, p, self.cpu.D, self.cpu.DF, text))
        try:
            self.m.step()
        except Exception as e:
            self.reason = "stopped: %s" % e; raise Stop(self.reason)

    def run(self, max_instructions=None, until=None):
        """run until a breakpoint, watchpoint, `until` address, max_instructions, or self.running = False.
        Returns the reason it stopped."""
        self.running = True; self._hit = None; n = 0; first = True
        try:
            while self.running:
                pc = self.pc()
                if not first and (pc in self.breaks or pc == until):
                    self.reason = ("breakpoint" if pc in self.breaks else "reached") + " %04X%s" % (pc, " <%s>" % self.sym(pc) if self.sym(pc) else "")
                    return self.reason
                first = False
                self.step(); n += 1
                if getattr(self.m, "fault", None):
                    self.reason = "bus: " + self.m.fault; self.m.fault = None; return self.reason
                if self._hit:
                    self.reason = "watchpoint: " + self._hit; self._hit = None; return self.reason
                if max_instructions and n >= max_instructions:
                    self.reason = "ran %d instructions" % n; return self.reason
            self.reason = "paused"; return self.reason
        except Stop as e:
            return str(e)
        finally:
            self.running = False

    def step_over(self):
        """step, but run through a subroutine call: SEP Rn with n != current P (SCRT: SEP R4 ... returns to the
        instruction after the inline address word)"""
        pc = self.pc(); op = self.m.peek(pc)
        if op >> 4 == 0xD and (op & 15) != self.cpu.P:
            nxt = (pc + 3) & 0xFFFF if (op & 15) == 4 else (pc + 1) & 0xFFFF   # SCRT call carries a 2-byte address
            return self.run(until=nxt, max_instructions=5_000_000)
        self.step(); self.reason = "stepped"; return self.reason
