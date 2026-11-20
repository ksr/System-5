# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-20
"""The CDP1802's pins, clock edge by clock edge, for the simulated 36-pin backplane (backplane.Backplane36).

The bus driver Rev C (BUSDRV-C) steps the 1802's clock from its Nano and reads the bus between edges; LOAD mode by the
clock (hardware/bus-driver/kicad/rev-c/DESIGN.md) depends on which edge moves which pin. This is that: one call of
edge() is one transition of the CLOCK pin, and the pins change as the data sheet's timing diagram has them.

A machine cycle is 8 clock periods = 16 edges, numbered 0-15 from the start of the cycle (the data sheet's clock 00):
   0  the high address byte on A0-A7; -MRD high; N0-N2 (an I/O cycle); the state code SC1 SC0
   2  TPA high                4  TPA low               (TPA: 1.0 T to 2.0 T)
   3  -MRD low, in a cycle that reads memory           (1.5 T)
   4  the 1802's own data on D0-D7, in a cycle where it writes (2.0 T)
   5  the low address byte on A0-A7                    (2.5 T)
  10  -MRW low, in a cycle that writes memory          (5.0 T)
  13  TPB high               15  TPB low               (6.5 T to 7.5 T)
  14  -MRW high                                        (7.0 T)
  15  the 1802 takes the data bus (a read), and looks at its DMA IN pin
These places were checked against the real 1802: the clock-stepped trace of CPU Rev A of 2026-10-31
(hardware/cpu/eagle/rev-a/bringup/, 26,002 machine cycles of HBIOS from power-on) has TPA, TPB, -MRD, -MRW and both
address bytes changing on exactly these edges, every cycle. The same numbers are in s5emu/timing.py (from the data
sheet's Figure 4). And the whole model was run beside that trace: given the data bus the real 1802 had, it makes the
same TPA, TPB, -MRD, -MRW, N0-N2, Q and address bytes on every clock edge of the first 25,280 machine cycles (fetches,
reads, writes and the cycles that use no memory). After that the two differ in a register's contents, not in a
strobe: that bench had no memory card, so a byte "popped" from the stack at 00FA was the floating data bus, and the
1802 took 52 where the bus driver, reading one edge earlier, had 72. test_busdrv_c.py replays the first 6,000 cycles.

State codes (SC1 SC0): S0 fetch 00, S1 execute 01, S2 DMA 10, S3 interrupt 11.

Modes, from CLEAR and WAIT (the data sheet's table):
  RESET  CLEAR low, WAIT high   I, N, Q cleared, IE set; TPA and TPB held off; S1; the data bus driven to 00
  RUN    both high              after RESET one initialization cycle of 9 clock pulses (X, P and R(0) cleared), then S0
  PAUSE  CLEAR high, WAIT low   the timing generator stops: clock edges are ignored and every pin holds
  LOAD   both low               the idle S1 cycle over and over (M(R(0)) read, -MRD low); a DMA IN request is answered
                                by one S2 cycle (the bus byte written to M(R(0)), R(0) + 1), then idle again
Instructions are the emulator's (s5emu/cpu.py): each is worked out on a copy of the registers from the bytes the pins
have delivered so far, which tells what the next cycle is (a read, a write, an input, nothing); the copy becomes the
registers when the instruction's last cycle is over. Memory is never touched from here: reads are what is on D0-D7 at
edge 15, writes are what the memory card makes of -MRW and the data lines.

From that trace too, where the data sheet says less:
  - A cycle that uses no memory shows R(N) on the address lines (N = the opcode's low digit), as the register stands
    before the instruction changes it, and no strobe.
  - IRX (60) reads M(R(X)) in its execute cycle, -MRD low, and throws the byte away.
  - The initialization cycle after RESET (9 clock pulses: 18 edges) ends as an ordinary S1 cycle with TPA and TPB and
    no strobe: the trace's first cycle, before the fetch at 0000. Here: two edges where nothing moves, then that cycle,
    with RESET's 00 still on the data lines.

Not from a measurement, so stated as what they are (the trace has no RESET, PAUSE, LOAD or DMA in it):
  - DMA IN is taken as sampled once a cycle at one edge, `dma_sample` (15, TPB's trailing edge; 13 is its leading
    edge). The data sheet says "between the leading edge of TPB and the leading edge of TPA". A request seen there
    makes the next cycle S2 (in RUN: after the instruction's last cycle). The state code and -MRD are taken to
    change at edge 0, with the address.
  - PAUSE stops at once (the data sheet: on the clock's first high-to-low transition).
  - LOAD entered without passing through RESET is treated as a reset followed by LOAD.
  - RESET clears all sixteen registers here (the emulator's reset), where the 1802 clears only R(0), X, P, I, N, Q.
  - The long skips and NOP (C4-CF) are two cycles with no strobe; the real 1802 may read memory in them (the trace
    has none).
  - Interrupts are an S3 cycle with no strobes; DMA OUT is not on the System-5 bus.
"""
import copy, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "s5emu"))
from s5emu.cpu import CPU1802                                                # noqa: E402

CYCLE = 16                      # clock edges in a machine cycle
INIT_EDGES = 18                 # the initialization cycle after RESET: 9 clock pulses
READS = ("fetch", "read", "idle")
WRITES = ("write", "inp", "dma")
SC = {"fetch": (0, 0), "read": (0, 1), "write": (0, 1), "inp": (0, 1), "none": (0, 1), "idle": (0, 1), "init": (0, 1),
      "dma": (1, 0), "int": (1, 1)}
MODES = {(0, 1): "reset", (1, 1): "run", (1, 0): "pause", (0, 0): "load"}       # (CLEAR, WAIT) -> mode


class _NeedData(Exception):
    pass


class _Replay:
    """the bus the emulator's CPU sees while an instruction is worked out: reads come from the bytes the pins have
    already delivered (`script`); the first read past them stops the attempt and says what the next cycle must be"""
    def __init__(self, script, ef):
        self.script, self._ef, self.ops, self.reads = list(script), ef, [], 0

    def _rd(self, kind, a):
        self.ops.append([kind, a, None, 0]); self.reads += 1
        if self.reads > len(self.script): raise _NeedData()
        self.ops[-1][2] = self.script[self.reads - 1]
        return self.ops[-1][2]

    def fetch(self, a): return self._rd("F", a)
    def read(self, a): return self._rd("R", a)
    def inp(self, n): v = self._rd("I", None); self.ops[-1][3] = n; return v
    def write(self, a, v):
        if self.ops and self.ops[-1][0] == "I" and self.ops[-1][1] is None: self.ops[-1][1] = a   # the INP's own cycle
        else: self.ops.append(["W", a, v, 0])
    def out(self, n, v): self.ops[-1][0] = "O"; self.ops[-1][3] = n
    def ef(self, n): return self._ef(n)
    def q(self, level): pass


class _NoBus:
    def read(self, a): return 0xFF
    def write(self, a, v): pass
    def out(self, n, v): pass
    def inp(self, n): return 0xFF
    def ef(self, n): return False


class Pins1802:
    def __init__(self, dma_sample=15):
        if dma_sample not in (13, 15): raise ValueError("dma_sample: 13 (TPB rising) or 15 (TPB falling)")
        self.dma_sample = dma_sample
        self.core = CPU1802(_NoBus())
        self.mode = "reset"; self.ef = lambda n: False
        self.cycles = []                # (kind, address, data on the bus at edge 15, N) of every finished cycle
        self._reset_pins()

    # ------------------------------------------------------------------ the pins
    def _reset_pins(self):
        self.A = 0; self.TPA = 0; self.TPB = 0; self.MRD = 1; self.MRW = 1; self.N = 0; self.Q = 0
        self.SC1, self.SC0 = 0, 1; self.D = 0x00            # RESET: S1, and 0's on the data bus
        self.e = 0; self.init = INIT_EDGES; self.cyc = None; self.dma_latch = False
        self._clear_instruction()

    def _clear_instruction(self):
        self.script = []; self.opcode = None; self.need = 0; self.next_exec = None; self.done = None

    def outputs(self):
        """what the 1802 puts on its pins now; D is None when it does not drive the data lines"""
        return dict(A=self.A, TPA=self.TPA, TPB=self.TPB, MRD=self.MRD, MRW=self.MRW, N=self.N, Q=self.Q, SC0=self.SC0,
                    SC1=self.SC1, D=self.D)

    # ------------------------------------------------------------------ CLEAR and WAIT (asynchronous)
    def set_mode(self, clear, wait):
        """the levels on the CLEAR and WAIT pins; -> True if any pin of the 1802 changed"""
        new = MODES[(1 if clear else 0, 1 if wait else 0)]
        if new == self.mode: return False
        old, self.mode = self.mode, new
        if new == "reset" or (new == "load" and old != "reset"):
            self.core.reset(); self._reset_pins(); return True
        return False                                        # out of RESET: the initialization cycle runs on the clock;
        #                                                     into or out of PAUSE: the pins hold

    # ------------------------------------------------------------------ one transition of CLOCK
    def edge(self, dma_in=1, dbus=0xFF):
        """dma_in: the level on the DMA IN pin (0 = a request); dbus: what is on D0-D7 as this edge arrives"""
        if self.mode in ("reset", "pause"): return
        if self.init > CYCLE: self.init -= 1; return        # the initialization cycle's first two edges: nothing moves
        e = self.e
        if e == 0: self._start_cycle()
        c = self.cyc; kind = c["kind"]
        if e == 2: self.TPA = 1
        elif e == 3:
            if kind in READS: self.MRD = 0
        elif e == 4:
            self.TPA = 0
            if kind == "write": self.D = c["wd"]
        elif e == 5: self.A = c["addr"] & 0xFF
        elif e == 10:
            if kind in WRITES: self.MRW = 0
        elif e == 13:
            self.TPB = 1
            if self.dma_sample == 13 and not dma_in: self.dma_latch = True
        elif e == 14: self.MRW = 1
        elif e == 15:
            self.TPB = 0
            if self.dma_sample == 15 and not dma_in: self.dma_latch = True
            self._finish_cycle(dbus & 0xFF)
        self.e = (e + 1) % CYCLE

    def _start_cycle(self):
        core = self.core; boundary = self.next_exec is None and self.need == 0 and self.done is None
        if self.init: c = dict(kind="init", addr=0, n=0)    # the rest of the initialization cycle: TPA and TPB, no strobe
        elif self.dma_latch and (boundary or self.mode == "load"):
            self.dma_latch = False; c = dict(kind="dma", addr=core.R[0], n=0)
        elif self.mode == "load": c = dict(kind="idle", addr=core.R[0], n=0)
        elif self.next_exec is not None: c = self.next_exec; self.next_exec = None
        elif self.need > 0:                                 # no memory in this cycle: R(N) on the address lines, as it
            n = (self.opcode or 0) & 15; r = core.R[n]      # stands before the instruction changes it (the program
            if n == core.P: r = (r + len(self.script)) & 0xFFFF      # counter has already moved past what was fetched)
            c = dict(kind="none", addr=r, n=0)
        elif core.int_line and core.IE: c = dict(kind="int", addr=core.R[core.P], n=0)
        elif core.idle: c = dict(kind="idle", addr=core.R[0], n=0)
        else:
            self.snap = self._save(); self._clear_instruction()
            c = dict(kind="fetch", addr=core.R[core.P], n=0)
        self.cyc = c
        self.SC1, self.SC0 = SC[c["kind"]]
        self.A = c["addr"] >> 8; self.N = c["n"]; self.MRD = 1; self.MRW = 1; self.TPA = 0; self.TPB = 0
        self.D = 0x00 if c["kind"] == "init" else None      # (RESET's 00 stays on the data lines through that cycle)

    def _finish_cycle(self, data):
        c = self.cyc; kind = c["kind"]; core = self.core
        self.cycles.append((kind, c["addr"], data, c["n"]))
        if kind == "init": self.init = 0
        elif kind == "fetch":
            self.script = [data]; self.opcode = data; self.need = 2 if data >> 4 == 0xC else 1; self._work_out()
        elif c.get("thrown"):                               # opcode 68: the byte went to memory, the copy assumed FF;
            self.need -= 1; self._commit()                  # IRX: the byte read is thrown away
        elif kind in ("read", "inp"):
            self.script.append(data); self.need -= 1; self._work_out()
        elif kind in ("write", "none"):
            self.need -= 1
            if self.need <= 0 and self.done is not None: self._commit()
        elif kind == "dma":
            core.R[0] = (core.R[0] + 1) & 0xFFFF
            if self.mode == "run": core.idle = False
        elif kind == "int":
            core.T = (core.X << 4) | core.P; core.X = 2; core.P = 1; core.IE = 0; core.idle = False

    # ------------------------------------------------------------------ the instruction, from the bytes seen so far
    def _save(self):
        core = self.core
        return {k: (list(v) if isinstance(v, list) else v) for k, v in vars(core).items() if k != "bus"}

    def _work_out(self):
        clone = CPU1802(_NoBus())
        for k, v in self.snap.items(): setattr(clone, k, list(v) if isinstance(v, list) else v)
        bus = _Replay(self.script, self.ef); clone.bus = bus
        clone.int_line = False; clone.idle = False          # (an interrupt is its own S3 cycle here, not the copy's)
        op = self.opcode; n_io = op & 7 if op >> 4 == 6 else 0
        try:
            clone.step()
        except _NeedData:
            k = bus.ops[-1]
            if k[0] == "I": self.next_exec = dict(kind="inp", addr=clone.R[clone.X], n=n_io)
            else: self.next_exec = dict(kind="read", addr=k[1], n=n_io if 0x61 <= op <= 0x67 else 0)
            return
        writes = [k for k in bus.ops if k[0] == "W"]
        self.done = clone
        if op == 0x68 and writes:                           # the 1802 runs 68 as an input from no port: -MRW, nobody drives
            self.next_exec = dict(kind="inp", addr=writes[0][1], n=0, thrown=True)
        elif op == 0x60:                                    # IRX: the real 1802 reads M(R(X)) and throws the byte away
            self.next_exec = dict(kind="read", addr=self.snap["R"][self.snap["X"]], n=0, thrown=True)
        elif writes: self.next_exec = dict(kind="write", addr=writes[0][1], wd=writes[0][2], n=0)
        elif self.need <= 0: self._commit()

    def _commit(self):
        core = self.core; clone = self.done
        for k, v in vars(clone).items():
            if k != "bus": setattr(core, k, v)
        self.Q = core.Q; self.need = 0; self.done = None; self.next_exec = None; self.script = []
