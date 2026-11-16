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
            new = 0xFF
            for _, b in drivers: new &= b                   # a TTL fight: a low usually wins
            if new == dbus: break
            dbus = new
        if len(drivers) > 1:
            self.log("fight", " + ".join("%s=%02X" % d for d in drivers))
        self.dbus = dbus
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

    def data_in(self):
        """what the bus driver reads on D0-D7 (lines nobody drives float high: no pull-ups assumed)"""
        return self.dbus
