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
  shorts=[("D0", "D1")]         two bus lines joined (a solder bridge), or a line joined to a supply ("N0", "GND"),
                                ("D0", "+5V"). Lines by their name without the dash: D0-D7 A0-A7 TPA TPB MRD MRW VMA Q
                                RESET INT EF N0-N2, and on the 36-pin bus EF1 EF2 EF3 PAUSE DMAIN SC0. A short acts on
                                the firmware's WALK command (set_lines, below) and, between two open-collector lines
                                of the 36-pin bus, on everything else; the bus cycles of a bus master do not see it
  diodes=[("TPB", "MRW")]       one line follows another one way only (WALK): while the first is low the second is
                                pulled low too, and not the other way round; what a card's logic between two bus
                                lines looks like from outside, where a solder bridge joins them both ways

set_lines() is the WALK command's state (2026-11-21): the bus driver drives ONE line, every other pin an input with its
expander pull-up on, to find shorts. There each line is worked out by itself, from all that is on it: the driver, a
short, a supply, the backplane's resistor, the 100k pull-up, a card. Between the expander's input thresholds (1.0 V
and 4.0 V: a pull-up shorted to a pull-down) a line reads either way, a new toss for each state (between=0 or 1: that
level every time, as one real chip would read it). The cards see the
result, so the run also shows whether one line driven alone wakes a card. set_pins() ends that state.

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
# every signal of the 30-pin bus, one line each (set_lines); the 36-pin extension's six
LINES30 = tuple("D%d" % i for i in range(8)) + tuple("A%d" % i for i in range(8)) + SIGNALS + ("N0", "N1", "N2")
LINES36 = LINES30 + ("EF1", "EF2", "EF3", "PAUSE", "DMAIN", "SC0")
RAILS = {"GND": 0, "+5V": 1}
G10K, G100K = 1e-4, 1e-5                      # a 10k resistor of the backplane, an expander's pull-up (100k), as conductances
V_LOW, V_HIGH = 1.0, 4.0                      # an MCP23017 input at 5 V: low below 0.2 VDD, high above 0.8 VDD


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
    LINES = LINES30

    def __init__(self, cards=("mem", "video", "ide"), jumpers="RRRRRRR-EEEEEEE-", empty=(), stuck=None, drive=True,
                 image=None, rom=None, rom_base=0x8000, addr=None, mem_rev="D", shorts=(), between=None, diodes=()):
        import random
        stuck = stuck or {}; self.cards = []; self.addr_fault = addr; self.events = []; self.context = ""
        self.shorts = [tuple(s) for s in shorts]; self.diodes = [tuple(d) for d in diodes]
        for s in self.shorts + self.diodes:
            for n in s:
                if n not in self.LINES and n not in RAILS: raise ValueError("short: no bus line %r here (%s, GND, +5V)" % (n, " ".join(self.LINES)))
        self.walk = None                  # set_lines(): {line: level} while the bus driver walks one line; None otherwise
        self.wdrv, self.wpull, self.wkeep, self._walk_d = {}, set(), {}, None
        self.walk_fight = False; self.overload = 0; self.wrng = random.Random(1802); self.between = between
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
        self._walk_end()
        if pins == self.pins and d_driver == self.d_driver: return     # a port write that changed no bus pin
        self.pins, self.d_driver = dict(pins), d_driver
        self._resolve()

    # ------------------------------------------------------------------ one line at a time (the firmware's WALK)
    def _walk_end(self):
        self.walk = None; self._walk_d = None; self.walk_fight = False

    def _pulls(self, line):
        """(up, down): what holds this line when nothing drives it, as conductances. The 2009 backplane: nothing"""
        return 0.0, 0.0

    def _walk_strong(self):
        """[(line, who, level)]: what else drives a line hard. Here: an address line stuck (the addr fault)"""
        return [("A%d" % self.addr_fault[0], "stuck", self.addr_fault[1])] if self.addr_fault else []

    def set_lines(self, drv, pullups):
        """the firmware's WALK: drv {line: 0|1}, the lines the bus driver's expanders drive (WALK drives one, or none);
        pullups, the lines whose expander pull-up (100k) is on. Every line is worked out from all that is on it, the
        cards see the result, and self.walk holds it: {line: 0|1}."""
        self.wdrv, self.wpull = dict(drv), set(pullups)
        card_d = None
        for _ in range(4):                                  # a card that answers drives D0-D7, which a short may tie to a control line
            lv = self._walk_levels(card_d)
            pulled = [(a, "through a card from " + k, 0) for k, a in self.diodes if lv[k] == 0 and lv[a] == 1]
            if pulled: lv = self._walk_levels(card_d, pulled)     # one way: the first line low takes the second low
            self._walk_show(lv)
            now = self.dbus if self.driven else None
            if now == card_d: break
            card_d = now
        self.walk = lv
        for k, v in lv.items(): self.wkeep[k] = v

    def _walk_levels(self, card_d, more=()):
        parent = {}
        def find(x):
            parent.setdefault(x, x)
            while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
            return x
        for a, b in self.shorts: parent[find(a)] = find(b)
        strong = {}                                         # group -> [(who, level)]
        def src(line, who, v): strong.setdefault(find(line), []).append((who, v))
        for r, v in RAILS.items():
            if r in parent: src(r, r, v)
        for line, v in self.wdrv.items(): src(line, "bus driver", v)
        if card_d is not None:
            for i in range(8): src("D%d" % i, "a card", card_d >> i & 1)
        for line, who, v in list(self._walk_strong()) + list(more): src(line, who, v)
        up, dn, members = {}, {}, {}
        for line in self.LINES:
            g = find(line); members.setdefault(g, []).append(line)
            u, d = self._pulls(line)
            up[g] = up.get(g, 0.0) + u + (G100K if line in self.wpull else 0.0); dn[g] = dn.get(g, 0.0) + d
        lv = {}; self.walk_fight = False
        for g, names in members.items():
            s = strong.get(g)
            if s:
                vals = {v for _, v in s}
                if len(vals) > 1:
                    self.log("fight", "%s: %s" % (" + ".join(names), " + ".join("%s=%d" % x for x in s)))
                    rail = [v for w, v in s if w in RAILS or w == "held"]
                    v = rail[0] if rail else 0              # a supply (or a line held: stuck_lines) wins; between two
                                                            #  outputs a low usually does
                    if any(w == "bus driver" for w, _ in s): self.walk_fight = True
                else: v = vals.pop()
            elif not up[g] and not dn[g]: v = self.wkeep.get(names[0], 1)       # nothing holds it: it keeps its charge
            else:
                volts = 5.0 * up[g] / (up[g] + dn[g])
                v = 1 if volts >= V_HIGH else 0 if volts <= V_LOW else (                    # between the thresholds
                    self.wrng.getrandbits(1) if self.between is None else self.between)
            for n in names: lv[n] = v
        return lv

    def _walk_show(self, lv):
        """the cards see every line at its level; D0-D7 rest where the lines put them unless a card drives them"""
        byte = lambda p, n: sum(lv["%s%d" % (p, i)] << i for i in range(n))
        self.pins = {k: lv[k] for k in SIGNALS}; self.pins["A"] = byte("A", 8); self.pins["N"] = byte("N", 3)
        self.d_driver = None; self._walk_d = byte("D", 8)
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

    def _floating(self):                                    # D0-D7 with nobody driving them
        return 0xFF if self._walk_d is None else self._walk_d

    def tick(self):                                         # one expander transaction of the bus driver has gone by
        if self.walk_fight: self.overload += 1              # ... with one of its pins held against a supply or an output

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
        """SW1, the RESET/RUN switch (and power-on, through U12): SW_RST low. The card's own open-drain gates (U11,
        since 2026-11-22) then pull the bus -RESET and, unless -PAUSE is low, -DMAIN: a boot reset, which clears
        LOADED, so the next RUN boots the EPROM. pulls() says which lines; Backplane36 puts them on the bus"""
        if reset: self.c.forced[self.n_swrst] = ("SW1", 0)
        else: self.c.forced.pop(self.n_swrst, None)

    def pulls(self):
        """the open-collector bus lines the card's own gates hold low now: RESET and DMAIN in a boot reset it makes"""
        s = self.c.bus.sig
        return {n for n in ("RESET", "DMAIN") if self.c.drives_low(s["-" + n])}

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
    LINES = LINES36

    def __init__(self, cards=("mem",), cpu=True, cable=True, jp1="EXT", cpu_rom=None, dma_sample=15, nopull=(),
                 stuck_lines=None, reset_stretch=0, **kw):
        import random
        self.cpu = None; self.drv = {}; self.clk_out = 0; self.lines = {}; self.keep = {}; self.dkeep = 0xFF
        self.reset_stretch = reset_stretch; self._stretch = 0; self._reset_pulled = False
        self.nopull = set(nopull); self.stuck_lines = dict(stuck_lines or {}); self.rng = random.Random(1802)
        self.sw1 = False; self._own = set(); self.writes = {}; self.transitions = {}; self.probe = {1: None, 2: None}
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
        self._walk_end()
        self.drv, self.d_driver = dict(pins), d_driver
        self._resolve36()

    # ------------------------------------------------------------------ one line at a time (the firmware's WALK)
    def _pulls(self, line):
        """the bus Rev D's 10k on this line (RN1-RN4), and the CPU card's own RN1 (10k up) on the open-collector lines"""
        group = "D" if line[0] == "D" and line[1:].isdigit() else "N" if line in ("N0", "N1", "N2") else line
        up = dn = 0.0
        if line not in self.nopull and group not in self.nopull:
            if group == "D" or BUS_D_PULLS.get(group) == 1: up += G10K
            elif BUS_D_PULLS.get(group) == 0: dn += G10K
        if self.cpu and line in OPEN_COLLECTOR: up += G10K
        return up, dn

    def _walk_strong(self):
        out = super()._walk_strong() + [(n, "held", v) for n, v in self.stuck_lines.items() if n in self.LINES]
        out += [(n, "cpu U11 (SW1)", 0) for n in sorted(self._own)]
        if self._stretch: out.append(("RESET", "cpu U10 (DS1813)", 0))
        if self.cpu:                                        # the 1802 drives its lines whatever its mode, and the card -VMA and SC0
            o = self.cpu.pins.outputs(); v = self.cpu.val
            out += [(n, "cpu", o[n]) for n in ("TPA", "TPB", "MRD", "MRW", "Q")]
            out += [("A%d" % i, "cpu", o["A"] >> i & 1) for i in range(8)] + [("N%d" % i, "cpu", o["N"] >> i & 1) for i in range(3)]
            out += [(n, "cpu", v.get(net)) for n, net in (("VMA", self.cpu.n_vma), ("SC0", self.cpu.n_sc0)) if v.get(net) in (0, 1)]
        return out

    def _walk_show(self, lv):
        if self.cpu:
            self.cpu.drive({n: (0 if lv[n] == 0 else None) for n in OPEN_COLLECTOR}, self.clk_out if self.cable else None, self.dbus)
        super()._walk_show(lv)
        for n in EXT_LINES + ("SC0",): self.pins[n] = lv[n]
        if self.driven: self.dkeep = self.dbus

    def clock(self, level):
        """the Nano's D9 (CLK OUT): through R7 and the DEBUG cable to the CPU card's EXT CLK"""
        if level == self.clk_out: return
        self.clk_out = level; self._note("CLK_OUT", level); self._resolve36()

    def press_sw1(self, reset):
        """the CPU card's RESET/RUN switch: at RESET the card's U11 pulls the bus -RESET and, unless -PAUSE is low,
        -DMAIN: a boot reset, which clears LOADED (until 2026-11-22: -RESET alone, through a diode)"""
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
        super().tick()
        if self._stretch:
            self._stretch -= 1
            if not self._stretch: self._resolve36()             # the DS1813 lets -RESET go

    def _resolve36(self):
        d = self.drv; own = self._own                            # own: what the CPU card's gates pull themselves (U11)
        for _ in range(4):                                      # (-PAUSE moving changes what U11 pulls: settle the two)
            pulled = d.get("RESET") == 0 or "RESET" in own      # -RESET held from outside the DS1813
            if self._reset_pulled and not pulled and self.cpu: self._stretch = self.reset_stretch
            self._reset_pulled = pulled
            oc = {n: self._line(n, [("bus driver", d.get(n)), ("cpu U11 (SW1)", 0 if n in own else None),
                                    ("cpu U10 (DS1813)", 0 if (n == "RESET" and self._stretch) else None)])
                  for n in OPEN_COLLECTOR}
            for a, b in self.shorts:                            # a short between two open-collector lines: low together
                if a in oc and b in oc and 0 in (oc[a], oc[b]): oc[a] = oc[b] = 0
            o = None; vma = sc0 = None; now = set()
            if self.cpu:
                v = self.cpu.drive({n: (0 if oc[n] == 0 else None) for n in OPEN_COLLECTOR},
                                   self.clk_out if self.cable else None, self.dbus)
                o = self.cpu.pins.outputs(); vma, sc0 = v.get(self.cpu.n_vma), v.get(self.cpu.n_sc0); now = self.cpu.pulls()
            if now == own: break
            own = now
        self._own = own
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

    def _floating(self):
        if self._walk_d is not None: return self._walk_d
        return self.dkeep if "D" in self.nopull else 0xFF

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
