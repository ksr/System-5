# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-11
"""A System-5 backplane at pin level, for testing the bus driver firmware and the bring-up scripts without hardware.

The cards are the emulator's gate-level models, built from each card's KiCad netlist (software/s5emu/s5emu/hw.py):
  mem    memory Rev D (or mem_rev C / B-built), jumpers as a 16-character string (R = RAM, E = EPROM, - = empty, block 0 first)
  video  6845 Rev B, SV1 1-2 (block 7: video RAM 7000-77FF, CRTC 7800-7FFF)
  ide    IDE/CF Rev A, SV1 = port 2 (register select), SV2 = port 3 (data), with a CF drive on its header
         (machine.py's IDE model, optionally holding a disk image)

set_pins() is called every time the bus driver's expanders change a pin, in the same order the firmware does it.
Each card's logic settles; the backplane then works out who drives the data lines, commits writes on the trailing
edge of each write strobe (RAM WE, the 6845's E, the drive's DIOW) and logs every moment two parts drive the data
lines at once ("fights"). Real hardware cannot report a fight; the simulator can, which is what catches a firmware
bus cycle in the wrong order.

Faults, for testing that the bring-up steps find them:
  empty=["IC5"]                 a chip left out of its socket (memory card refs)
  stuck={"mem": (bit, level)}   a data line of one card stuck at 0 or 1 whenever that card drives the bus
  drive=False                   the IDE card with nothing on its header (no CF adapter or no card in it)
  addr=(bit, level)             bus address line A<bit> stuck (the cards see it; so does a latched high byte)

Backplane36, at the end (2026-11-20), is the bus Rev D's 36-pin slot for BUSDRV-C: the same cards, the six extension
lines, the bus's pull resistors, and CPU Rev D in place (CpuCardD: its gates from the netlist, the 1802 as
cpupins.Pins1802, clocked edge by edge from the bus driver's CLK OUT through the DEBUG cable).
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "s5emu"))
from s5emu.hw import NetlistMemoryCard, NetlistVideoCard, NetlistIDECard     # noqa: E402
from s5emu.machine import Video6845, IDE, FLOAT                               # noqa: E402
from s5emu.logic import Circuit                                               # noqa: E402

SIGNALS = ("TPA", "TPB", "MRD", "MRW", "VMA", "Q", "RESET", "INT", "EF")


class BusCard:
    """one card: its circuit, the devices that drive the data lines, and edge tracking for writes"""
    def __init__(self, name, card, store, stuck=None):
        self.name, self.card, self.c, self.store, self.stuck = name, card, card.c, store, stuck
        self.prev = {}                 # device ref -> its access last step ('r'|'w', addr) or None
        self.wdata = {}                # device ref -> the data bus value while its write strobe is active

    def devices(self): return self.c.mem

    def byte_out(self, ref, b):
        """chip data pins -> bus bits (the netlist may wire D0 of a chip to any bus data line)"""
        bits = self.card.bitmap[ref]; v = sum(((b >> i) & 1) << bits[i] for i in range(8))
        if self.stuck:
            bit, level = self.stuck; v = (v | (1 << bit)) if level else (v & ~(1 << bit))
        return v

    def byte_in(self, ref, v):
        bits = self.card.bitmap[ref]; return sum(((v >> bits[i]) & 1) << i for i in range(8))


class Backplane:
    def __init__(self, cards=("mem", "video", "ide"), jumpers="RRRRRRR-EEEEEEE-", empty=(), stuck=None, drive=True,
                 image=None, rom=None, rom_base=0x8000, addr=None, mem_rev="D"):
        stuck = stuck or {}; self.cards = []; self.addr_fault = addr; self.events = []; self.context = ""
        self.mem = self.video = self.ide = None
        if "mem" in cards:
            m = NetlistMemoryCard(mem_rev, jumpers)
            if empty:                                       # rebuild the circuit with those sockets empty
                from s5emu.hw import MEMORY_REVS
                fitted = set(MEMORY_REVS[mem_rev].get("fitted") or m.nl.parts) - set(empty)
                m.c = Circuit(m.nl, fitted); m.devices = m.chips = m.c.mem; m._check_data_path(); m.set_jumpers(jumpers)
            self.mem = m
            if rom: self.load_rom(rom, rom_base)
            self.cards.append(BusCard("mem", m, {r: m.store[r] for r in m.store}, stuck.get("mem")))
        if "video" in cards:
            self.screen = Video6845(); v = NetlistVideoCard(self.screen, "B"); self.video = v
            self.cards.append(BusCard("video", v, v.store, stuck.get("video")))
        if "ide" in cards:
            self.ide = NetlistIDECard("A"); self.drive = IDE(image, sectors=2048) if drive else None
            self.ide_stuck = stuck.get("ide"); self.ide_prev = (None, None); self.ide_w = None; self.ide_r = None
        self.pins = None; self.d_driver = None; self.dbus = 0xFF

    # ------------------------------------------------------------------ setup helpers
    def load_rom(self, data, base=0x8000):
        """program the memory card's EPROMs: data (bytes) as it should read at bus address base onward"""
        for i, b in enumerate(data): self.mem.program(base + i, b)

    def log(self, kind, text):
        self.events.append((kind, self.context, text))

    def fights(self): return [e for e in self.events if e[0] == "fight"]

    # ------------------------------------------------------------------ the bus
    def set_pins(self, pins, d_driver):
        """pins: {signal: 0|1|None, 'A': byte|None, 'N': 0-7}; d_driver: the byte the bus driver puts on D0-D7, or None"""
        if pins == self.pins and d_driver == self.d_driver: return     # a port write that changed no bus pin
        self.pins, self.d_driver = dict(pins), d_driver
        self._resolve()

    def _drive_card(self, c, dbus):
        p = self.pins; kw = {k: p.get(k) for k in SIGNALS}
        if p.get("A") is not None:
            kw["A"] = p["A"]
            if self.addr_fault:
                bit, lv = self.addr_fault; kw["A"] = (kw["A"] | (1 << bit)) if lv else (kw["A"] & ~(1 << bit))
        if p.get("N") is not None: kw["N"] = p["N"]
        kw["D"] = dbus
        c.drive(**kw); return c.settle()

    def _resolve(self):
        dbus = self.dbus if self.d_driver is None else self.d_driver
        for _ in range(4):                                  # the data bus feeds the IDE card's register latch: iterate
            drivers = [("bus driver", self.d_driver)] if self.d_driver is not None else []
            states = []
            for bc in self.cards:
                val = self._drive_card(bc.c, dbus); now = {}
                for d in bc.devices():
                    r = d.access(val)
                    if isinstance(r, str):
                        if "(CE=1 " not in r and "(CER=1 " not in r and "CS=1 " not in r:   # a deselected chip: harmless
                            self.log("undefined", "%s %s" % (bc.name, r))
                        r = None
                    now[d.ref] = r
                    if r and r[0] == "r":
                        b = bc.store[d.ref][0](r[1])
                        drivers.append(("%s %s" % (bc.name, d.ref), bc.byte_out(d.ref, b)))
                states.append((bc, now))
            ide_now = None
            if self.ide:
                val = self._drive_card(self.ide.c, dbus); ide_now = self.ide.sample(val)
                if ide_now[1] == "undefined": self.log("undefined", "ide drive register lines undefined"); ide_now = (None, None)
                if ide_now[0] == "r" and self.drive is not None:
                    if self.ide_r is None:                  # DIOR just went active: the drive puts out one byte
                        self.drive.sel = ide_now[1]; self.ide_r = self.ide.to_bus(self.drive.inp(3))
                    v = self.ide_r
                    if self.ide_stuck: bit, lv = self.ide_stuck; v = (v | (1 << bit)) if lv else (v & ~(1 << bit))
                    drivers.append(("ide drive", v))
            drivers += self._extra_drivers(dbus)           # (Backplane36: the CPU card's EPROM and the 1802 itself)
            new = self._floating() if not drivers else 0xFF
            for _, b in drivers: new &= b                   # a TTL fight: a low usually wins
            if new == dbus: break
            dbus = new
        if len(drivers) > 1:
            self.log("fight", " + ".join("%s=%02X" % d for d in drivers))
        self.dbus = dbus; self.driven = bool(drivers)
        # trailing edges: a write lands when its strobe ends, with the data that was on the bus while it was active
        for bc, now in states:
            for ref, r in now.items():
                was = bc.prev.get(ref)
                if r and r[0] == "w": bc.wdata[ref] = (r[1], dbus)
                if was and was[0] == "w" and r != was and ref in bc.wdata:
                    a, v = bc.wdata.pop(ref); bc.store[ref][1](a, bc.byte_in(ref, v))
                bc.prev[ref] = r
        if self.ide:
            was = self.ide_prev
            if ide_now[0] == "w": self.ide_w = (ide_now[1], dbus)
            if was[0] == "w" and ide_now != was and self.ide_w is not None:
                reg, v = self.ide_w; self.ide_w = None
                if self.drive is not None: self.drive.sel = reg; self.drive.out(3, self.ide.to_drive(v))
            if ide_now[0] != "r": self.ide_r = None
            self.ide_prev = ide_now

    def _extra_drivers(self, dbus): return []

    def _floating(self): return 0xFF                        # D0-D7 with nobody driving them

    def tick(self): pass                                    # one expander transaction of the bus driver has gone by

    def data_in(self):
        """what the bus driver reads on D0-D7 (lines nobody drives float high: no pull-ups assumed)"""
        return self.dbus


# ====================================================================== the 36-pin bus (bus Rev D), for BUSDRV-C
# What the bus Rev D holds a line at when nothing drives it (hardware/bus/kicad/rev-d: RN1-RN4, 10k): pull-ups on
# D0-D7, -EF, -EF1..-EF3, -PAUSE, -DMAIN, -INT, -RESET, -VMA, -MRD, -MRW; pull-downs on N0-N2, TPA, TPB. A0-A7, Q and
# SC0 have none. A line whose resistor is missing keeps the level it was last driven to (its own capacitance).
BUS_D_PULLS = dict(TPA=0, TPB=0, MRD=1, MRW=1, VMA=1, RESET=1, INT=1, EF=1, EF1=1, EF2=1, EF3=1, PAUSE=1, DMAIN=1, N=0)
OPEN_COLLECTOR = ("RESET", "INT", "EF", "EF1", "EF2", "EF3", "PAUSE", "DMAIN")
EXT_LINES = ("EF1", "EF2", "EF3", "PAUSE", "DMAIN")        # the extension's open-collector lines (SC0 is the CPU card's)


class CpuCardD:
    """CPU Rev D in a 36-pin slot: its gates from the card's netlist (the boot map, LOADED, CLEAR / WAIT / DMA IN from
    the bus lines, the clock jumper JP1, SC0 onto the bus), with the 1802 itself as cpupins.Pins1802, moved one clock
    edge at a time. jp1: 'EXT' (the DEBUG header's EXT CLK, through the Schmitt inverter U7A) or 'INT' (the card's own
    2 MHz: not simulated; the 1802 then runs by itself and its CLOCK pin reads as noise)."""
    def __init__(self, rom=None, jp1="EXT", dma_sample=15):
        from s5emu.hw import CPU_REVS, ROOT
        from s5emu.netlist import Netlist
        from cpupins import Pins1802
        spec = CPU_REVS["D"]; nl = Netlist(os.path.join(ROOT, spec["net"]))
        for j in spec["jumpers"]: nl.jumper(*j)
        nl.jumper("JP1", "2", "JP1", "3" if jp1 == "EXT" else "1")
        self.nl, self.jp1 = nl, jp1
        self.c = Circuit(nl, None, external=spec["external"])
        net = lambda name: next(n for n in nl.nets if n.split("/")[-1] == name)
        self.n_clock, self.n_wait, self.n_clear, self.n_dma = net("CLOCK"), net("WAIT"), net("CLEAR"), net("DMA_IN")
        self.n_ext, self.n_sc0raw, self.n_sc1, self.n_swrst = net("EXT_CLK"), net("SC0_RAW"), net("SC1"), net("SW_RST")
        self.n_ef = [nl.net("U1", p) for p in ("24", "23", "22", "21")]     # the 1802's EF1-EF4 pins, as jumpered (JP2-JP5)
        self.n_vma, self.n_sc0 = self.c.bus.sig["-VMA"], self.c.bus.sig["SC0"]
        self.eprom = next(d for d in self.c.mem if d.kind == "ROM")
        bus_d = {self.c.bus.sig["D%d" % i]: i for i in range(8)}
        self.bits = [bus_d[n] for n in self.eprom.data]
        self.rom = bytearray(rom) if rom else bytearray([0xFF]) * 4096
        self.pins = Pins1802(dma_sample); self.pins.ef = lambda n: self.val.get(self.n_ef[n - 1]) == 0
        self.last_clock = None; self.val = {}; self.edges = 0
        flop = next(m for m in self.c.models if type(m).__name__ == "DFF74" and any(h[3].split("/")[-1] == "LOAD_L" for h in m.ff))
        self._loaded = (flop, next(i for i, h in enumerate(flop.ff) if h[3].split("/")[-1] == "LOAD_L"))
        self.switch(True); self.drive({"RESET": 0}, None, 0xFF); self.switch(False)      # power-on: LOADED cleared

    def switch(self, reset):
        """SW1, the RESET/RUN switch (and power-on): RESET clears LOADED, so the next RUN boots the EPROM.
        (Its pull on the bus -RESET through D1 is the backplane's business: Backplane36.press_sw1.)"""
        if reset: self.c.forced[self.n_swrst] = ("SW1", 0)
        else: self.c.forced.pop(self.n_swrst, None)

    def loaded(self):
        """the LOADED flag (U8A): set by LOAD mode, it keeps the boot map off so that RUN starts in RAM"""
        return self._loaded[0].state.get(self._loaded[1]) == 1

    def drive(self, lines, ext_clk, dbus):
        """lines: the bus's open-collector lines ({'RESET': 0, ...}: 0 = held low, absent or None = let go, the card's
        own RN1 pulls it up); ext_clk: the level on J2 pin 1 (None = no cable: R2 holds it low); dbus: D0-D7 now.
        The gates settle; an edge on the 1802's CLOCK pin, or CLEAR / WAIT changing, moves the 1802's pins, and the
        gates settle again. -> the settled nets"""
        c = self.c; v = self.val
        for _ in range(4):
            o = self.pins.outputs()
            c.drive(A=o["A"], TPA=o["TPA"], TPB=o["TPB"], MRD=o["MRD"], MRW=o["MRW"], N=o["N"], Q=o["Q"], D=dbus,
                    **{"-" + k: lines.get(k) for k in OPEN_COLLECTOR})
            c.forced[self.n_sc0raw] = ("U1", o["SC0"]); c.forced[self.n_sc1] = ("U1", o["SC1"])
            if ext_clk is None: c.forced.pop(self.n_ext, None)
            else: c.forced[self.n_ext] = ("cable", ext_clk)
            v = self.val = c.settle()
            self.pins.core.int_line = lines.get("INT") == 0
            clear, wait, clk = v.get(self.n_clear), v.get(self.n_wait), v.get(self.n_clock)
            changed = clear in (0, 1) and wait in (0, 1) and self.pins.set_mode(clear, wait)
            if self.jp1 == "EXT" and clk in (0, 1):
                if self.last_clock in (0, 1) and clk != self.last_clock:
                    self.pins.edge(dma_in=v.get(self.n_dma), dbus=dbus); self.edges += 1; changed = True
                self.last_clock = clk
            if not changed: break
        return v

    def data_drivers(self):
        """what this card puts on D0-D7 now: the 1802 (a write, or the 00 of RESET) and the EPROM when it is read"""
        out = []; o = self.pins.outputs()
        if o["D"] is not None: out.append(("cpu U1 (1802)", o["D"]))
        r = self.eprom.access(self.val)
        if isinstance(r, tuple) and r[0] == "r":
            b = self.rom[r[1] & 0xFFF]; out.append(("cpu %s" % self.eprom.ref, sum(((b >> i) & 1) << self.bits[i] for i in range(8))))
        return out


class Backplane36(Backplane):
    """the bus Rev D with its 36-pin slots, as BUSDRV-C sees it: the 30-pin cards of Backplane, the six extension
    lines, the bus's pull-ups and pull-downs, and (cpu=True) CPU Rev D, its DEBUG header cabled to the bus driver's
    (cable=True) and its clock jumper JP1 on EXT.

    The bus driver's expander pins arrive through set_pins() as before, with the extension's lines added
    (EF1 EF2 EF3 PAUSE DMAIN: 0 = pulled low, None = let go); its CLK OUT (the Nano's D9) through clock(). Each line is
    then worked out from everything on it: the open-collector lines are low if anything pulls them; a line both the
    bus driver and the 1802 drive to different levels is logged as a fight.

    More faults, for the Rev C tests:
      cable=False              the DEBUG ribbon left off: CLK OUT does not reach the CPU card, CLOCK / SC0 / SC1 read 1
      jp1='INT'                the CPU card's clock jumper on its own oscillator
      stuck_lines={'DMAIN': 0} a bus line held at a level by something else on the bus
      nopull=('PAUSE', 'D')    a pull resistor of the bus Rev D missing on that line (a line's name, 'D' or 'N')
    And one thing the real CPU card does that the gates alone do not show:
      reset_stretch=n          its DS1813 (U10) holds the bus -RESET low for 150 ms after whatever pulled it lets go.
                               There is no time here: n is that hold counted in the bus driver's expander transactions
                               (tick(): about 0.15 ms each on the real card, so 1000 for the real part; 0 = none)
    """
    def __init__(self, cards=("mem",), cpu=True, cable=True, jp1="EXT", cpu_rom=None, dma_sample=15, nopull=(),
                 stuck_lines=None, reset_stretch=0, **kw):
        import random
        self.cpu = None; self.drv = {}; self.clk_out = 0; self.lines = {}; self.keep = {}; self.dkeep = 0xFF
        self.reset_stretch = reset_stretch; self._stretch = 0; self._reset_pulled = False
        self.nopull = set(nopull); self.stuck_lines = dict(stuck_lines or {}); self.rng = random.Random(1802)
        self.sw1 = False; self.writes = {}; self.transitions = {}; self.probe = {1: None, 2: None}
        self._decoder = None; self._mem_args = (kw.get("mem_rev", "D"), kw.get("jumpers", "RRRRRRR-EEEEEEE-"))
        super().__init__(cards=cards, **kw)
        for bc in self.cards: self._count_writes(bc)
        if cpu: self.cpu = CpuCardD(cpu_rom, jp1, dma_sample)
        self.cable = bool(cable and cpu)
        self.set_pins({}, None)

    def _count_writes(self, bc):
        """count every byte a memory chip takes, by card, chip and chip address (the tests ask for one write a byte)"""
        for ref, (rd, wr) in list(bc.store.items()):
            def counted(a, v, ref=ref, wr=wr, name=bc.name):
                self.writes[(name, ref, a)] = self.writes.get((name, ref, a), 0) + 1; wr(a, v)
            bc.store[ref] = (rd, counted)

    # ------------------------------------------------------------------ what the bus driver does
    def set_pins(self, pins, d_driver):
        self.drv, self.d_driver = dict(pins), d_driver
        self._resolve36()

    def clock(self, level):
        """the Nano's D9 (CLK OUT): through R7 and the DEBUG cable to the CPU card's EXT CLK"""
        if level == self.clk_out: return
        self.clk_out = level; self._note("CLK_OUT", level); self._resolve36()

    def press_sw1(self, reset):
        """the CPU card's RESET/RUN switch: RESET pulls the bus -RESET low (through D1) and clears LOADED"""
        self.sw1 = bool(reset)
        if self.cpu: self.cpu.switch(reset)
        self._resolve36()

    # ------------------------------------------------------------------ the lines
    def _note(self, name, level):
        if name in self.lines and self.lines[name] != level: self.transitions[name] = self.transitions.get(name, 0) + 1
        self.lines[name] = level

    def _line(self, name, sources, width=1):
        """one bus line from what drives it: sources = [(who, level)], level None = not driving"""
        if name in self.stuck_lines: return self.stuck_lines[name]
        live = [(w, v) for w, v in sources if v is not None]
        if name in OPEN_COLLECTOR:
            if any(v == 0 for _, v in live): v = 0
            elif name not in self.nopull: v = 1
            elif self.cpu is not None: v = 1                    # the CPU card's own RN1 pulls the same eight lines up
            else: v = self.keep.get(name, 1)
        elif live:
            if len({v for _, v in live}) > 1: self.log("fight", "%s: %s" % (name, " + ".join("%s=%X" % s for s in live)))
            v = live[0][1]
            for _, x in live[1:]: v &= x
        elif name in BUS_D_PULLS and name not in self.nopull: v = BUS_D_PULLS[name] * ((1 << width) - 1)
        else: v = self.keep.get(name, (1 << width) - 1)        # no resistor: the line holds what it was last driven to
        self.keep[name] = v
        return v

    def tick(self):
        if self._stretch:
            self._stretch -= 1
            if not self._stretch: self._resolve36()             # the DS1813 lets -RESET go

    def _resolve36(self):
        d = self.drv
        pulled = d.get("RESET") == 0 or self.sw1                # -RESET held from outside the DS1813
        if self._reset_pulled and not pulled and self.cpu: self._stretch = self.reset_stretch
        self._reset_pulled = pulled
        oc = {n: self._line(n, [("bus driver", d.get(n)), ("cpu SW1", 0 if (n == "RESET" and self.sw1) else None),
                                ("cpu U10 (DS1813)", 0 if (n == "RESET" and self._stretch) else None)])
              for n in OPEN_COLLECTOR}
        o = None; vma = sc0 = None
        if self.cpu:
            v = self.cpu.drive({n: (0 if oc[n] == 0 else None) for n in OPEN_COLLECTOR},
                               self.clk_out if self.cable else None, self.dbus)
            o = self.cpu.pins.outputs(); vma, sc0 = v.get(self.cpu.n_vma), v.get(self.cpu.n_sc0)
        cpu = lambda k: None if o is None else o[k]
        pins = dict(oc)
        for n in ("TPA", "TPB", "MRD", "MRW", "Q"): pins[n] = self._line(n, [("bus driver", d.get(n)), ("cpu", cpu(n))])
        pins["VMA"] = self._line("VMA", [("bus driver", d.get("VMA")), ("cpu", vma if vma in (0, 1) else None)])
        pins["A"] = self._line("A", [("bus driver", d.get("A")), ("cpu", cpu("A"))], 8)
        pins["N"] = self._line("N", [("bus driver", d.get("N")), ("cpu", cpu("N"))], 3)
        pins["SC0"] = self._line("SC0", [("cpu", sc0 if sc0 in (0, 1) else None)])
        for k, v in pins.items(): self._note(k, v)
        self.pins = pins
        self._resolve()                                         # the 30-pin cards and the data lines (Backplane)
        if self.driven: self.dkeep = self.dbus

    def _extra_drivers(self, dbus): return self.cpu.data_drivers() if self.cpu else []

    def _floating(self): return self.dkeep if "D" in self.nopull else 0xFF

    # ------------------------------------------------------------------ what the bus driver reads
    def ext_in(self):
        """-EF1 -EF2 -EF3 -PAUSE -DMAIN SC0 as U3's GPA0-5 read them"""
        return {n: self.pins.get(n, 1) for n in EXT_LINES + ("SC0",)}

    def debug_in(self):
        """the DEBUG header's CLOCK, SC0 and SC1 as U3's GPB0-2 read them (its pull-ups are on: 1 with no cable)"""
        if not self.cable: return dict(CLOCK=1, SC0=1, SC1=1)
        c = self.cpu
        clk = c.val.get(c.n_clock) if c.jp1 == "EXT" else self.rng.getrandbits(1)
        return dict(CLOCK=clk if clk in (0, 1) else 1, SC0=self.pins["SC0"], SC1=c.pins.outputs()["SC1"])

    def probe_in(self, k):
        """PROBE1 / PROBE2: the level of the line a test has hooked it to (bp.probe[1] = 'TPA'), else 0"""
        name = self.probe.get(k)
        return 0 if name is None else self.lines.get(name, 0)

    # ------------------------------------------------------------------ for the tests: what the memory card holds
    def _where(self, addr):
        """(chip ref, chip address, data-bit map) the memory card's own decode gives a bus address, or None. Worked out
        on a second copy of the card, so the one on the bus is not disturbed."""
        if self._decoder is None:
            self._decoder = NetlistMemoryCard(self._mem_args[0], self._mem_args[1])
        for ref, kind, op, ca in self._decoder.decode(addr, 0, 0, 1)[0]:
            if op == "r": return ref, ca, self.mem.bitmap[ref]
        return None

    def peek(self, addr):
        """the byte a read of bus address addr would get from the memory card (None where no chip answers)"""
        w = self._where(addr)
        if w is None: return None
        b = self.mem.contents[w[0]][w[1]]
        return sum(((b >> i) & 1) << w[2][i] for i in range(8))

    def writes_at(self, addr):
        """how many times the chip behind bus address addr has taken a byte since the backplane was built"""
        w = self._where(addr)
        return 0 if w is None else self.writes.get(("mem", w[0], w[1]), 0)
