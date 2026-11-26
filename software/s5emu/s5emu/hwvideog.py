# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-20
"""VIDEO-G 1.0 from its two netlists, for the hardware machine (python3 -m s5emu --hw --video g; hw.HWMachine).

The TEXT board and, if fitted, the GFX board are read from their KiCad netlists (hardware/video-g/kicad/text-1.0 and
gfx-1.0, reports/netlist.net) and joined into one circuit: the 40-pin ribbon conductor for conductor (TEXT J6 pin n =
GFX J4 pin n), the bus lines both boards take from the backplane, and the supplies. What is simulated and what is played:

  Through the cards' own gates (logic.py), in every memory cycle that can reach the card
    TEXT  IC1 the A8-A15 latch (TPA); IC2 + SV1 the block compare with -VMA (IC16D) -> BOARDSEL; IC17C / IC20D the text
          RAM's -CE; IC18D UPPER (7800-7FFF); IC19D WSEL (the window); IC5, IC6, IC7 the three register decoders; IC21C
          the 6845's E (the whole -MRW time: it is write-only, R/-W on ground, since 2026-11-24); IC17B NOT TPB; IC20C /
          IC19B the KEY-READY clear; IC24B KEY-READY; IC23D and JP3, KEY-READY onto a bus flag line; IC16F, IC20B, IC22D the character clock, QC OR RCO and the -WE phase
          that go down the ribbon
    GFX   IC14 NMUX, MEMRD, MEMWR, NOT TPB; IC16A GWR (a window write); IC17B the read latch's output enable; IC13A WRQ,
          IC17A -WE, IC16B the RAM's -OE (the write slot); IC2-IC5 the RAM's address multiplexers; IC18A / IC16C the
          MOUSE-READY clear; IC13B MOUSE-READY
  Played, on the pins the gates drive (as hw.NetlistIOPanel plays its '244, clock and UART)
    the text RAM's and the graphics RAM's contents, the 6845's registers and its counters (VSYNC, DE), the key and
    mouse latches' bytes, the control and Y registers' bytes, the status buffer (it puts the levels on its inputs on the
    bus), the two ATmega328Ps (each loads its latch and clocks its READY flip-flop with LDDATA when it has a byte and
    READY is low) and the 12 MHz character counter. Their contents are the behavioural model's (videog.VideoG), so the
    screen, the pictures and the keyboard and mouse queues are the same objects in both machines.
  Not simulated: the dot chain (code latch, character ROM, shifters, the combine gates, the syncs). Circuit proves from
    the netlist that nothing there reaches a pin that decides a bus cycle.

One memory cycle is run as the 1802 times it (software/s5emu/s5emu/timing.py, from the CDP1802 data sheet), in these
sub-phases, each settled through the gates:
    read:   idle (0 to T: the latch still holds the last cycle's high byte, -VMA not yet settled), tpa (T), mrd (-MRD
            low at 1.5 T, the HIGH address byte still on A0-A7), hold (TPA low, 2 T), low (the low byte, 2.5 T), tpb
            (6.5 T; the 1802 takes the data as TPB falls), end (TPB low, -MRD still low)
    write:  idle, tpa, hold, low, mrw (-MRW low, 5 T), tpb (6.5 T), mrwend (-MRW high at 7 T, TPB still high), end
At each sub-phase the pins of every part that can drive D0-D7, take a byte from them or change a flip-flop are read:
who drives, who is written, which register clock rises, which READY flip-flop is cleared.

Speed, without giving up the gates. The decode is a function of the address, -VMA and the kind of cycle alone: every
cycle is run from a card whose flip-flops, registers, counter and played outputs are all UNKNOWN (X), and an answer
that came out definite cannot depend on them. The answer is kept as a plan:
  - per high address byte, the cycle is first run with the low byte unknown too. If nothing on the card can then be
    enabled, the whole page is idle (every address outside the card's block: one probe, then a table look-up); if the
    same parts are enabled whatever the low byte (the text RAM's pages, the window's), the page has one plan, with the
    chip's address pins followed back to the bus lines they sit on;
  - otherwise (the registers at 7800-7BFF) each address gets its own plan, from a run with its real low byte.
The graphics RAM's address is not settled per access either: which bus line, Y bit or page bit reaches each address pin
through the four 74HCT157s is found once, by trying each input alone with all the others unknown, on the CPU side and
on the display side; and the write slot (WRQ, -WE at counts 9-10, the write buffer, the RAM's -OE, the read latch on
QC) is run through the gates with the character counter stepped, from each of its eight phases, the first time the
window is used (slot_check). A window access then goes straight to the cell those two findings name.

Bus events. Two drivers at the 1802's latch point, or a byte landing in two places, are logged by the machine from
what bus_read / bus_write return, like the other cards'. Anything this card finds wrong in a cycle (an enable that is
neither on nor off, two parts on the bus in another sub-phase, a part driving while the 1802 writes, a register clocked
twice) comes back as a fault text, which the machine logs as 'undefined'. A part that is enabled only in the
high-byte time of a read and is off again before the low byte (see early()) is not an event: it is how the card is
drawn, and the 1802 does not look at the bus then.
"""
import os
from collections import deque
from .machine import FLOAT
from .netlist import Netlist
from .logic import Circuit, DRIVING, X

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
G = "GFX."                                               # the GFX board's parts and nets in the joined netlist

VIDEOG_REVS = {
    "1.0": dict(text="hardware/video-g/kicad/text-1.0/reports/netlist.net",
                gfx="hardware/video-g/kicad/gfx-1.0/reports/netlist.net",
                note="VIDEO-G 1.0 (2026-11-01, memory-mapped 2026-11-17, TEXT on the 36-pin connector 2026-11-18, its 6845 "
                     "write-only 2026-11-24; not "
                     "built; hardware/video-g/DESIGN.md): TEXT decodes everything in the card's 4K block (SV1; 7 = "
                     "7000): the IDT7134 text RAM at x000-x7FF, the registers at x800-xBFF (the 6845 at x800/x801, write-only, the "
                     "key at x802, status / control at x804, mouse / Y at x806, each pair repeating) and the graphics "
                     "window at xC00-xFFF; GFX holds the control and Y registers, the 62256 and the mouse latch, on "
                     "strobes TEXT sends down the 40-pin ribbon."),
}
BLOCK_SHUNTS = ((3, "1", "2"), (2, "3", "4"), (1, "5", "6"), (0, "7", "8"))     # SV1: a shunt = that address bit 0
FLAG_SHUNTS = {"-EF1": ("1", "2"), "-EF2": ("3", "4"), "-EF3": ("5", "6"), "-EF": ("7", "8")}   # JP3 KBD FLAG
MONITOR_SHUNTS = {"ntsc": ("1", "2"), "mda": ("2", "3")}                         # JP1: MONITOR to GND / to +5V
SERIES = ("R11", "R12", "R13")                           # 33 ohm in the ribbon's three clocks: a wire, to the logic

# the parts this module plays, and why the netlist check may let their outputs into the bus path
PLAYED_TEXT = {
    "IC4": "the HD68B45: written (never read: R/-W is on ground) on its own pins (CS, E, R/-W, RS); its registers and counters are the behavioural model's",
    "IC8": "the 74LS244 status buffer: it puts the levels on its inputs on D0-D7 while its enables, from IC6, are low",
    "IC9": "the 74HCT374 key latch: it drives D0-D7 while its OE, from IC6, is low; the ATmega loads it",
    "IC10": "the keyboard ATmega328P: it loads IC9 and sets KEY-READY with LDDATA when a key waits and KEY-READY is low",
    "IC15": "the 74F163A character counter (and the 12 MHz oscillator): its outputs are stepped by this module",
}
PLAYED_GFX = {
    "IC1": "the 62256: its cells are the behavioural model's pages; address, -OE and -WE are read on its pins",
    "IC6": "the 74HCT374 read latch: it loads the RAM's byte on QC's rise and drives D0-D7 while its OE (IC17B) is low",
    "IC7": "the 74HCT244 write buffer: D0-D7 onto the RAM's data pins while its enables (-WE) are low",
    "IC10": "the 74HCT374 Y register: it takes D0-D7 on -WRY's rise",
    "IC11": "the mouse ATmega328P: it loads IC12 and sets MOUSE-READY with LDDATA",
    "IC12": "the 74HCT374 mouse latch: it drives D0-D7 while its OE (-RDMOUSE) is low",
    "IC19": "the 74HCT273 control register: it takes D0-D7 on -WRCTL's rise; -RESET clears it",
}
OUTPUTS_UNKNOWN = ("IC4", "IC15", G + "IC10", G + "IC19")    # every output pin of these is X while a plan is made
LISTENS = {("IC10", "16"), (G + "IC11", "16")}               # the ATmegas' PB2: an input in the firmware (it reads its
#                                                            READY flip-flop: embedded/video-g-ps2), though the symbol
#                                                            calls every port pin bidirectional
READ = ("idle", "tpa", "mrd", "hold", "low", "tpb", "end")
WRITE = ("idle", "tpa", "hold", "low", "mrw", "tpb", "mrwend", "end")
WHEN = {"idle": "before TPA", "tpa": "while TPA is high", "mrd": "from -MRD's fall, the high address byte still on A0-A7",
        "hold": "after TPA, the high address byte still on A0-A7", "low": "with the low address byte, before TPB",
        "mrw": "while -MRW is low, before TPB", "tpb": "at TPB", "mrwend": "after -MRW has risen, TPB still high",
        "end": "after TPB"}


def _open(net):
    """a pin KiCad left unconnected (its net is named for the pin), on either board"""
    return net.startswith(("unconnected", G + "unconnected"))


class Sample:
    """what the card's pins say at one settled sub-phase. reads / writes: [(part, op argument recipe)]; clocks: {register:
    its clock pin's level}; clears: the READY flip-flops held clear; unknown: parts whose state cannot be told (an
    enable depends on something that is X)"""
    __slots__ = ("reads", "writes", "clocks", "clears", "window", "unknown", "faults")

    def __init__(self):
        self.reads = []; self.writes = []; self.clocks = {}; self.clears = []; self.window = None; self.unknown = []; self.faults = []

    def quiet(self):
        return not (self.reads or self.writes or self.clears or self.window or self.unknown or self.faults) and \
            all(v == 1 for v in self.clocks.values())


class Plan:
    """one memory cycle's effect on the card, whatever its flip-flops and registers hold. drive: the parts on the bus at
    the 1802's latch point, [(part, recipe)]; writes: the parts that take the byte; regs: the registers whose clock
    rises once; clears: the READY flip-flops cleared; window: 'r' / 'w' (the graphics RAM, through its slot); early:
    [(sub-phase, part)] enabled before the low address byte and off again by the latch point; shifts: [(sub-phase,
    part)] a part that stays enabled through a read while the number on its address pins changes (the high byte's
    lines becoming the low byte's: nothing to an asynchronous RAM, but the 6845 wants RS steady before E rises);
    faults: texts"""
    __slots__ = ("drive", "writes", "regs", "clears", "window", "early", "shifts", "faults", "steps")

    def idle(self): return not (self.drive or self.writes or self.regs or self.clears or self.window or self.faults)


class NetlistVideoG:
    """the VIDEO-G card (TEXT, and GFX when fitted) from its netlists; `video` is the videog.VideoG whose text RAM,
    6845 registers, control and Y registers, pages and queues it reads and writes. block: the card's 4K block (SV1);
    kbd_flag: the bus line JP3 puts KEY-READY on (-EF1, -EF2, -EF3, -EF, or None for no shunt)."""
    name = "video-g"

    def __init__(self, video, rev="1.0", gfx=None, block=7, kbd_flag="-EF", root=ROOT):
        if rev not in VIDEOG_REVS: raise ValueError("VIDEO-G revision %r: one of %s" % (rev, ", ".join(VIDEOG_REVS)))
        if kbd_flag is not None and kbd_flag not in FLAG_SHUNTS: raise ValueError("kbd_flag: one of %s, or None" % ", ".join(FLAG_SHUNTS))
        spec = VIDEOG_REVS[rev]; self.rev, self.note, self.v = rev, spec["note"], video
        self.gfx = video.gfx if gfx is None else gfx; self.block, self.kbd_flag = block & 15, kbd_flag
        nl = self.nl = Netlist(os.path.join(root, spec["text"]))
        for op, *args in spec.get("rework", []): getattr(nl, op)(*args)      # (a modified TEXT: netlist.py's lift, wire ...)
        for bit, a, b in BLOCK_SHUNTS:
            if not (self.block >> bit) & 1: nl.jumper("SV1", a, "SV1", b)
        if kbd_flag: nl.jumper("JP3", FLAG_SHUNTS[kbd_flag][0], "JP3", FLAG_SHUNTS[kbd_flag][1])
        nl.jumper("JP1", MONITOR_SHUNTS[video.monitor][0], "JP1", MONITOR_SHUNTS[video.monitor][1])
        for r in SERIES: nl.jumper(r, "1", r, "2")
        played = dict(PLAYED_TEXT)
        if self.gfx: self._join(Netlist(os.path.join(root, spec["gfx"]))); played.update({G + r: why for r, why in PLAYED_GFX.items()})
        self.played = played
        self._pins()
        self.c = Circuit(nl, None, controls=self.watched, external=played)
        self.sig = self.c.bus.sig
        self.a_line = {self.sig["A%d" % i]: i for i in range(8)}
        self.d_line = {self.sig["D%d" % i]: i for i in range(8)}
        self._wiring()
        self.base_forced = {}
        for ref in OUTPUTS_UNKNOWN:
            if ref not in nl.parts: continue
            for (r, p), (net, _) in nl.pins.items():
                if r == ref and nl.pintype[(r, p)] in ("output", "tri_state") and net not in self.d_line and not _open(net):
                    self.base_forced[net] = (ref, X)
        for net in self.lddata: self.base_forced[net] = ("ATmega", X)
        loose = sorted("%s.%s (%s)" % (r.replace(G, "GFX "), p, net) for (r, p), (net, _) in nl.pins.items()
                       if r in played and net in self.c.cone and nl.pintype[(r, p)] in DRIVING and (r, p) not in LISTENS
                       and net not in self.base_forced and net not in self.c.POWER)
        if loose: raise ValueError("played parts' outputs in the bus path that a plan would not hold unknown: " + ", ".join(loose))
        self.kready = self.mready = False; self.key = self.mbyte = FLOAT       # the two latches power up undefined
        self.held = set()                                            # what -RESET holds clear, while it is low
        self.pages = [None] * 1024; self.plans = {}; self.slot_fault = None; self.slot_checked = False
        self._ready_check(); self.flags = self._flag_lines()
        if self.gfx: self._mux_wiring()
        self.bus_reset()

    # ------------------------------------------------------------------ the netlist: two boards, one circuit
    def _join(self, gfx):
        """the GFX board: its parts and nets under GFX., the ribbon conductor for conductor, and the bus lines it takes
        from the backplane joined to TEXT's"""
        nl = self.nl; bus = {net.split("/")[-1]: net for (r, p), (net, _) in nl.pins.items() if r == "J1"}
        nl.join(gfx, G)
        for pin in range(1, 41):
            a, b = nl.net("J6", pin), nl.net(G + "J4", pin)
            if a != b and a in nl.SUPPLIES and b in nl.SUPPLIES: raise ValueError("the ribbon's pin %d joins %s to %s" % (pin, a, b))
            nl.jumper("J6", str(pin), G + "J4", str(pin))
        for (r, p), (net, _) in sorted(nl.pins.items()):
            if r != G + "J1" or net in nl.SUPPLIES or _open(net): continue
            name = net.split("/")[-1]
            if name not in bus: raise ValueError("GFX takes %s from the bus, which TEXT's connector does not have" % name)
            nl.short(bus[name], net)

    def _pins(self):
        """the pins this module reads or plays, by part and pin name, as the netlist has them (a KeyError here means a
        symbol or a pin name changed: the model must then be read again against the schematic)"""
        nl = self.nl; f = lambda ref, name: nl.net(ref, nl.pin_by_function(ref, name))
        self.ram_t = dict(ce=f("IC3", "~{CER}"), oe=f("IC3", "~{OER}"), rw=f("IC3", "R/~{WR}"),
                          addr=[f("IC3", "A%dR" % i) for i in range(12)], data=[f("IC3", "I/O%dR" % i) for i in range(8)])
        self.crtc = dict(cs=f("IC4", "~{CS}"), e=f("IC4", "E"), rw=f("IC4", "R/~{W}"), rs=f("IC4", "RS"),
                         data=[f("IC4", "D%d" % i) for i in range(8)], reset=f("IC4", "~{RESET}"),
                         vs=f("IC4", "VS"), de=f("IC4", "DE"),
                         ma=[f("IC4", "MA%d" % i) for i in range(12)], ra=[f("IC4", "RA%d" % i) for i in range(3)])
        self.status = dict(oe=[f("IC8", "OEa"), f("IC8", "OEb")],
                           pairs=[(f("IC8", "I%d%s" % (k, h)), f("IC8", "O%d%s" % (k, h))) for h in "ab" for k in range(4)])
        self.keyl = dict(oe=[f("IC9", "OE")], clk=f("IC9", "Cp"), data=[f("IC9", "O%d" % i) for i in range(8)])
        self.kff = dict(q=nl.net("IC24", 9), clr=nl.net("IC24", 13), clk=nl.net("IC24", 11), d=nl.net("IC24", 12))
        if not (self.kff["clk"] == self.keyl["clk"] == nl.net("IC10", 12)):
            raise ValueError("LDDATA: the ATmega's pin 12, IC9's clock and IC24B's clock are not one net")
        self.lddata = [self.kff["clk"]]
        self.watched = [self.crtc[k] for k in ("cs", "e", "rw", "rs")] + self.status["oe"] + self.keyl["oe"] + \
                       [self.kff["q"], self.kff["clr"]] + [net for (r, p), (net, _) in nl.pins.items() if r == "J1" and net.split("/")[-1].startswith("-EF")]
        self.readers = [("IC8", self.status["oe"]), ("IC9", self.keyl["oe"])]
        self.clears = [("KEY-READY", self.kff["clr"])]
        self.clocks = {}
        if not self.gfx: return
        g = lambda ref, name: f(G + ref, name)
        self.ram_g = dict(cs=g("IC1", "~{CS}"), oe=g("IC1", "~{OE}"), we=g("IC1", "~{WE}"),
                          addr=[g("IC1", "A%d" % i) for i in range(15)], data=[g("IC1", "Q%d" % i) for i in range(8)])
        self.rdl = dict(oe=[g("IC6", "OE")], clk=g("IC6", "Cp"), d=[g("IC6", "D%d" % i) for i in range(8)], q=[g("IC6", "O%d" % i) for i in range(8)])
        self.wrb = dict(oe=[g("IC7", "OEa"), g("IC7", "OEb")],
                        pairs=[(g("IC7", "I%d%s" % (k, h)), g("IC7", "O%d%s" % (k, h))) for h in "ab" for k in range(4)])
        self.yreg = dict(clk=g("IC10", "Cp"), oe=g("IC10", "OE"), d=[g("IC10", "D%d" % i) for i in range(8)], q=[g("IC10", "O%d" % i) for i in range(8)])
        self.ctrl = dict(clk=g("IC19", "Cp"), mr=g("IC19", "~{Mr}"), d=[g("IC19", "D%d" % i) for i in range(8)], q=[g("IC19", "Q%d" % i) for i in range(8)])
        self.mousel = dict(oe=[g("IC12", "OE")], clk=g("IC12", "Cp"), data=[g("IC12", "O%d" % i) for i in range(8)])
        self.mff = dict(q=nl.net(G + "IC13", 9), clr=nl.net(G + "IC13", 13), clk=nl.net(G + "IC13", 11))
        self.wrq = dict(q=nl.net(G + "IC13", 5), d=nl.net(G + "IC13", 2), clk=nl.net(G + "IC13", 3))
        if not (self.mff["clk"] == self.mousel["clk"] == nl.net(G + "IC11", 12)):
            raise ValueError("GFX LDDATA: the ATmega's pin 12, IC12's clock and IC13B's clock are not one net")
        if self.yreg["oe"] != "GND": raise ValueError("GFX IC10 (the Y register): its OE is on %s, not GND" % self.yreg["oe"])
        self.lddata.append(self.mff["clk"])
        self.counter = dict(qa=f("IC15", "Q0"), qb=f("IC15", "Q1"), qc=f("IC15", "Q2"), rco=f("IC15", "TC"))
        self.watched += self.rdl["oe"] + [self.rdl["clk"]] + self.wrb["oe"] + self.mousel["oe"] + \
                        [self.yreg["clk"], self.ctrl["clk"], self.ctrl["mr"], self.mff["q"], self.mff["clr"], self.wrq["d"]] + \
                        [self.ram_g[k] for k in ("cs", "oe", "we")] + self.ram_g["addr"]
        self.readers += [(G + "IC6", self.rdl["oe"]), (G + "IC12", self.mousel["oe"])]
        self.clears.append(("MOUSE-READY", self.mff["clr"]))
        self.clocks = {"control": self.ctrl["clk"], "Y": self.yreg["clk"]}

    def _wiring(self):
        """which bus data line each data pin of the played parts sits on; the status buffer's eight inputs"""
        d = self.d_line
        def bits(nets, what):
            out = [d.get(n) for n in nets]
            if None in out: raise ValueError("%s: a data pin is not on a bus data line (%s)" % (what, ", ".join(nets)))
            return out
        self.bit = {"IC3": bits(self.ram_t["data"], "IC3"), "IC4": bits(self.crtc["data"], "IC4"), "IC9": bits(self.keyl["data"], "IC9")}
        self.status_in = {}                                          # bus bit -> the net on the buffer's input
        for i, o in self.status["pairs"]: self.status_in[bits([o], "IC8")[0]] = i
        if sorted(self.status_in) != list(range(8)): raise ValueError("IC8 does not put eight inputs on D0-D7")
        if not self.gfx: return
        self.bit.update({G + "IC12": bits(self.mousel["data"], "GFX IC12"), "control": bits(self.ctrl["d"], "GFX IC19"),
                         "Y": bits(self.yreg["d"], "GFX IC10")})
        ram = {n: j for j, n in enumerate(self.ram_g["data"])}       # the RAM's data pins by net (GD0-GD7)
        self.wr_bit = [None] * 8; self.rd_bit = [None] * 8           # RAM bit j <- bus bit (IC7);  RAM bit j -> bus bit (IC6)
        for i, o in self.wrb["pairs"]:
            if o in ram: self.wr_bit[ram[o]] = bits([i], "GFX IC7")[0]
        for dn, qn in zip(self.rdl["d"], self.rdl["q"]):
            if dn in ram: self.rd_bit[ram[dn]] = bits([qn], "GFX IC6")[0]
        if None in self.wr_bit or None in self.rd_bit: raise ValueError("GFX: the RAM's data pins do not all reach D0-D7 through IC7 and IC6")

    # ------------------------------------------------------------------ the circuit, driven
    def _unknown(self):
        """every flip-flop and latch on the card unknown, the played parts' outputs unknown, the bus idle"""
        c = self.c
        for m in c.models:
            for attr, blank in (("state", X), ("last", None)):
                d = getattr(m, attr, None)
                if isinstance(d, dict):
                    for k in d: d[k] = blank
        c.forced = dict(self.base_forced); c.val = {}
        c.ext.clear()

    def _set(self, model_pin_net, value):
        """put a flip-flop whose Q is on this net in a known state (for the checks that need one)"""
        for m in self.c.models:
            for i, ff in enumerate(getattr(m, "ff", [])):
                if ff[4] == model_pin_net: m.state[i] = value; return
        raise ValueError("no flip-flop drives %s" % model_pin_net)

    def _cycle(self, a, vma, write, xlow=False):
        """one memory cycle at address a, from an unknown card, sub-phase by sub-phase -> [(name, Sample)]. xlow: the
        low address byte unknown too (A0-A7 are X from 2.5 T on)"""
        c = self.c; hi, lo = (a >> 8) & 0xFF, a & 0xFF; out = []; self._unknown()
        def step(name):
            s = self._sample(c.settle(), xlow and name not in ("idle", "tpa", "mrd", "hold"))
            s.faults += ["two outputs disagree on %s" % n.replace(G, "GFX ") for n in c.fights if n in c.cone]   # (none do)
            out.append((name, s))
        c.drive(TPA=0, TPB=0, A=hi, MRD=1, MRW=1, RESET=1); c.ext[self.sig["-VMA"]] = X; step("idle")
        c.drive(TPA=1); step("tpa")
        c.drive(VMA=vma)                                             # the CPU card's -VMA has settled by -MRD's fall
        if not write: c.drive(MRD=0); step("mrd")
        c.drive(TPA=0); step("hold")
        if xlow:
            for net in self.a_line: c.ext[net] = X
        else: c.drive(A=lo)
        step("low")
        if write: c.drive(MRW=0); step("mrw")
        c.drive(TPB=1); step("tpb")
        if write: c.drive(MRW=1); step("mrwend")
        c.drive(TPB=0); step("end")
        return out

    def _recipe(self, nets, v, xlow, what, s):
        """the number on a part's address pins as ((source, bit), ...): ('K', level), or ('A', i) for a pin that sits on
        bus line Ai while the low byte is unknown. None (and a note in the sample) if a pin is unknown otherwise"""
        out = []
        for n in nets:
            x = v.get(n)
            if x in (0, 1): out.append(("K", x))
            elif xlow and n in self.a_line: out.append(("A", self.a_line[n]))
            else: s.unknown.append(what); return None
        return tuple(out)

    def _sample(self, v, xlow):
        s = Sample(); g = v.get
        # the text RAM's bus port: IDT7134, -CER with R/-WR (a write) or with -OER (a read)
        ce, oe, rw = g(self.ram_t["ce"]), g(self.ram_t["oe"]), g(self.ram_t["rw"])
        if ce == 1 or (oe == 1 and rw == 1): pass
        elif ce == 0 and rw == 0:
            r = self._recipe(self.ram_t["addr"], v, xlow, "IC3", s)
            if r: s.writes.append(("IC3", r))
        elif ce == 0 and rw == 1 and oe == 0:
            r = self._recipe(self.ram_t["addr"], v, xlow, "IC3", s)
            if r: s.reads.append(("IC3", r))
        else: s.unknown.append("IC3")
        # the 6845: selected while -CS is low and E high
        cs, e, rw, rs = (g(self.crtc[k]) for k in ("cs", "e", "rw", "rs"))
        if cs == 1 or e == 0: pass
        elif cs == 0 and e == 1:
            r = self._recipe([self.crtc["rs"]], v, False, "IC4", s) if rw in (0, 1) else None
            if rw not in (0, 1): s.unknown.append("IC4")
            elif r: (s.reads if rw else s.writes).append(("IC4", r))
        else: s.unknown.append("IC4")
        # the parts with an output enable: the status buffer, the key latch, and on GFX the read latch and the mouse latch
        for ref, nets in self.readers:
            lv = [g(n) for n in nets]
            if all(x == 1 for x in lv): continue
            if all(x == 0 for x in lv): s.reads.append((ref, ()))
            elif any(x not in (0, 1) for x in lv): s.unknown.append(ref)
            else: s.faults.append("%s: one enable low and one high" % ref.replace(G, "GFX "))
        for name, net in self.clears:
            x = g(net)
            if x == 0: s.clears.append(name)
            elif x != 1: s.unknown.append(name)
        for name, net in self.clocks.items():
            x = g(net); s.clocks[name] = x
            if x not in (0, 1): s.unknown.append(name)
        if self.gfx:
            x = g(self.wrq["d"])                                     # GWR: a write to the window is asking for a slot
            if x == 1: s.window = "w"
            elif x != 0: s.unknown.append("GWR")
        return s

    # ------------------------------------------------------------------ plans
    def _make(self, samples, write):
        p = Plan(); p.drive = []; p.writes = []; p.regs = []; p.clears = []; p.window = None; p.early = []; p.faults = []
        by = dict(samples); p.steps = samples; p.shifts = []
        for (_, s0), (ph, s1) in zip(samples, samples[1:]):
            was = dict(s0.reads)
            p.shifts += [(ph, r) for r, recipe in s1.reads if r in was and was[r] != recipe]
        part = lambda ref: ref.replace(G, "GFX ")
        for ph, s in samples:
            p.faults += ["%s: %s" % (WHEN[ph], f) for f in s.faults]
            p.faults += ["%s: %s neither on nor off (an input it needs is undefined)" % (WHEN[ph], part(u)) for u in s.unknown]
            for name in s.clears:
                if name not in p.clears: p.clears.append(name)
        if not write:
            final = by["tpb"].reads; after = {r for r, _ in by["end"].reads}
            p.drive = list(final)
            for ref, _ in final:
                if ref not in after: p.faults.append("%s leaves the bus as TPB falls: the 1802 wants the byte 200 ns longer" % part(ref))
            for ph, s in samples:
                if ph != "tpb" and len(s.reads) > 1:
                    p.faults.append("%s: %s on the bus together" % (WHEN[ph], " and ".join(part(r) for r, _ in s.reads)))
                if ph in ("mrd", "hold"):
                    p.early += [(ph, r) for r, _ in s.reads if r not in {x for x, _ in final} and (ph, r) not in p.early]
                for ref, _ in s.writes: p.faults.append("%s: %s is written in a read cycle" % (WHEN[ph], part(ref)))
                if s.window: p.faults.append("%s: a window write is asked for in a read cycle" % WHEN[ph])
            if any(by[ph].clocks.get(k) != 1 for ph in READ for k in self.clocks):
                p.faults.append("a register's clock moves in a read cycle")
            if self.gfx and (G + "IC6", ()) in final: p.window = "r"
        else:
            seen = {}
            for ph in ("mrw", "tpb"):
                for ref, r in by[ph].writes:
                    if ref in seen and seen[ref] != r: p.faults.append("%s: its address changes while -MRW is low" % part(ref))
                    seen[ref] = r
            p.writes = list(seen.items())
            for ph, s in samples:
                if ph not in ("idle", "tpa") and s.reads:
                    p.faults.append("%s: %s drives the bus in a write cycle" % (WHEN[ph], " and ".join(part(r) for r, _ in s.reads)))
                if ph not in ("mrw", "tpb"):
                    for ref, _ in s.writes: p.faults.append("%s: %s is written outside -MRW" % (WHEN[ph], part(ref)))
            for k in self.clocks:
                seq = [by[ph].clocks.get(k) for ph in WRITE]; rises = sum(1 for a, b in zip(seq, seq[1:]) if a == 0 and b == 1)
                if rises == 1: p.regs.append(k)
                elif rises: p.faults.append("the %s register is clocked %d times" % (k, rises))
            w = [by[ph].window for ph in ("mrw", "tpb")]
            if w == ["w", "w"]: p.window = "w"
            elif any(w): p.faults.append("the window write request does not last through -MRW")
            if any(by[ph].window for ph in WRITE if ph not in ("mrw", "tpb")): p.faults.append("the window write request is up outside -MRW")
        p.drive = tuple(p.drive); p.writes = tuple(p.writes); p.faults = tuple(dict.fromkeys(p.faults))
        return p

    def page(self, hi, vma, write):
        """the plan for a whole page (one high address byte): 'idle', a Plan good for every low byte, or None (each
        address its own). From one cycle with the low byte unknown"""
        k = hi | (vma << 8) | (0x200 if write else 0); r = self.pages[k]
        if r is None:
            samples = self._cycle(hi << 8, vma, write, xlow=True)
            if all(s.quiet() for _, s in samples): r = "idle"
            elif any(s.unknown or s.faults for _, s in samples): r = "each"
            else: r = self._make(samples, write)
            self.pages[k] = r
        return r

    def plan(self, a, vma, write):
        """the Plan for one cycle, or None if it cannot touch the card"""
        r = self.page(a >> 8, vma, write)
        if r == "idle": return None
        if r != "each": return r
        k = (a, vma, write); p = self.plans.get(k)
        if p is None: p = self.plans[k] = self._make(self._cycle(a, vma, write), write)
        return None if p.idle() else p

    @staticmethod
    def _number(recipe, lo):
        return sum((b if k == "K" else (lo >> b) & 1) << i for i, (k, b) in enumerate(recipe))

    # ------------------------------------------------------------------ the played parts
    def _atmegas(self):
        """each ATmega, as its firmware does: with a byte to send and its READY flip-flop low, it puts the byte on the
        latch's inputs and pulses LDDATA (the latch takes it, READY goes high). The byte stays at the head of the
        behavioural model's queue until the CPU's read clears READY."""
        if self.held: return                                     # -RESET is low: the ATmegas are in reset, READY held clear
        q = self.v.m.kbd.queue
        if not self.kready and q: self.key = q[0] & 0xFF; self.kready = True
        if self.gfx and not self.mready and self.v.mouse: self.mbyte = self.v.mouse[0] & 0xFF; self.mready = True

    def _clear(self, name):
        if name == "KEY-READY":
            if self.kready and self.v.m.kbd.queue: self.v.m.kbd.queue.pop(0)
            self.kready = False
        elif self.mready:
            if self.v.mouse: self.v.mouse.popleft()
            self.mready = False
        else: self.mready = False

    def _level(self, net, beam):
        """the level on one of the status buffer's inputs, now: a READY flip-flop's Q, the 6845's VSYNC or DE (played:
        the behavioural model's beam), or a level the jumpers, the pull resistors and the ribbon fix"""
        if net == self.kff["q"]: return 1 if self.kready else 0
        if self.gfx and net == self.mff["q"]: return 1 if self.mready else 0
        if net == self.crtc["vs"]: return (beam >> 2) & 1
        if net == self.crtc["de"]: return (beam >> 3) & 1
        return self.static.get(net)

    def status_byte(self):
        """-> (the byte the 74LS244 puts on D0-D7, [bits whose input is undefined])"""
        b = 0; bad = []; beam = self.v.status()
        for bit, net in self.status_in.items():
            x = self._level(net, beam)
            if x == 1: b |= 1 << bit
            elif x != 0: bad.append(bit); b |= 1 << bit
        return b, bad

    def _spread(self, ref, b):
        bits = self.bit[ref]
        return b if bits == [0, 1, 2, 3, 4, 5, 6, 7] else sum(((b >> i) & 1) << bits[i] for i in range(8))

    def _gather(self, ref, v):
        bits = self.bit[ref]
        return v if bits == [0, 1, 2, 3, 4, 5, 6, 7] else sum(((v >> bits[i]) & 1) << i for i in range(8))

    # ------------------------------------------------------------------ the bus (hw.HWMachine calls these)
    def bus_read(self, a, vma, commit=True):
        """a read cycle at a -> [(driver, byte)], [faults]. commit=False: look only (no READY flip-flop is cleared)"""
        if vma not in (0, 1): vma = 1                            # (the CPU card logs an undefined -VMA itself)
        if self.pages[(a >> 8) | (vma << 8)] == "idle": return [], []
        p = self.plan(a, vma, False)
        if p is None: return [], []
        self._atmegas(); out = []; faults = list(p.faults); v = self.v; lo = a & 0xFF
        for ref, recipe in p.drive:
            if ref == "IC3": b = self._spread(ref, v.vram[self._number(recipe, lo) % len(v.vram)])
            elif ref == "IC4":                                   # (as first drawn: the card's 6845 is write-only, so this
                rs = self._number(recipe, lo)                    # is for other wirings) R14-R17 read back, the others 0
                b = self._spread(ref, (v.reg[v.sel] if v.sel in (14, 15, 16, 17) else 0) if rs else FLOAT)
            elif ref == "IC8":
                b, bad = self.status_byte()
                if bad: faults.append("status: bit%s %s undefined" % ("s" if len(bad) > 1 else "", ", ".join(map(str, bad))))
            elif ref == "IC9": b = self._spread(ref, self.key)
            elif ref == G + "IC12": b = self._spread(ref, self.mbyte)
            else:                                                # GFX IC6: the window
                b, f = self._window(lo, None); faults += f
            out.append(("video-g %s" % ref.replace(G, "GFX "), b))
        if commit:
            for name in p.clears: self._clear(name)
            if p.clears: self._atmegas()
        return out, faults

    def bus_write(self, a, vma, byte):
        """a write cycle at a -> [the parts the byte lands in], [faults]"""
        if vma not in (0, 1): vma = 1
        if self.pages[(a >> 8) | (vma << 8) | 0x200] == "idle": return [], []
        p = self.plan(a, vma, True)
        if p is None: return [], []
        self._atmegas(); out = []; faults = list(p.faults); v = self.v; lo = a & 0xFF
        for ref, recipe in p.writes:
            if ref == "IC3":
                v.vram[self._number(recipe, lo) % len(v.vram)] = self._gather(ref, byte); v.dirty = True
            else:                                                # the 6845: the address register, or the register picked
                b = self._gather(ref, byte)
                if not self._number(recipe, lo): v.sel = b & 31
                elif v.sel < 18: v.reg[v.sel] = b; v.dirty = True
            out.append("video-g %s" % ref)
        for k in p.regs:
            b = self._gather(k, byte)
            if k in self.held: continue                          # clocked with its -MR low (-RESET): it stays clear
            if k == "control": self._control(b)
            else: v.yreg = b
            out.append("video-g GFX %s" % ("IC19" if k == "control" else "IC10"))
        if p.window == "w":
            _, f = self._window(lo, byte); faults += f; out.append("video-g GFX IC1")
        for name in p.clears: self._clear(name)
        return out, faults

    def _control(self, b):
        v = self.v
        if v.ctrl & 0x20 and not b & 0x20: v.mouse = deque(list(v.mouse)[:1])     # MOUSE-ON off: the latch keeps its byte
        v.ctrl = b; v.dirty = True

    def reset_line(self, level):
        """the bus -RESET taken low (0) or let go (1), through the gates. Low: the READY flip-flops and the control
        register are cleared and held clear, as the nets on their clear pins say (the ATmegas are held in reset too, so
        nothing is loaded; a write to x804 clocks a register whose -MR is low, and changes nothing). High: they are let
        go, and a key still queued is loaded again."""
        c = self.c; self._unknown()
        c.drive(TPA=0, TPB=0, A=0, VMA=1, MRD=1, MRW=1, RESET=level); val = c.settle()
        self.held = set(); self.reset_low = not level
        if val.get(self.kff["clr"]) == 0: self.kready = False; self.held.add("KEY-READY")
        if self.gfx:
            if val.get(self.mff["clr"]) == 0: self.mready = False; self.held.add("MOUSE-READY")
            if val.get(self.ctrl["mr"]) == 0: self._control(0); self.held.add("control")
        if level:
            self.static = dict(val)                                  # (the jumper and pull levels the status buffer reads)
            self._atmegas()

    def bus_reset(self):
        """a -RESET pulse on the bus: low, then high again"""
        self.reset_line(0); self.reset_line(1)

    def ef(self, line):
        """True while this card pulls the bus flag line (-EF, -EF1, -EF2, -EF3) low: KEY-READY, on the line JP3 picks"""
        self._atmegas()
        return self.kready and line in self.flags

    # ------------------------------------------------------------------ checks through the gates, once
    def _ready_check(self):
        """the played ATmegas rest on this: a rising LDDATA sets the READY flip-flop (its D is high, its clear is off)"""
        for q, clk, what in [(self.kff["q"], self.kff["clk"], "KEY-READY (IC24B)")] + \
                            ([(self.mff["q"], self.mff["clk"], "MOUSE-READY (GFX IC13B)")] if self.gfx else []):
            c = self.c; self._unknown(); self._set(q, 0)
            c.drive(TPA=0, TPB=0, A=0, VMA=1, MRD=1, MRW=1, RESET=1)
            c.forced[clk] = ("ATmega", 0); c.settle(); c.forced[clk] = ("ATmega", 1)
            if c.settle().get(q) != 1: raise ValueError("%s is not set by LDDATA's rise with the bus idle" % what)

    def _flag_lines(self):
        """the bus flag lines KEY-READY pulls low, found by setting the flip-flop and looking at the connector"""
        c = self.c; lines = [n for n in ("-EF", "-EF1", "-EF2", "-EF3") if n in self.sig]; low = {}
        for level in (0, 1):
            self._unknown(); self._set(self.kff["q"], level)
            c.drive(TPA=0, TPB=0, A=0, VMA=1, MRD=1, MRW=1, RESET=1); val = c.settle()
            low[level] = [n for n in lines if val.get(self.sig[n]) == 0]
        if low[0]: raise ValueError("%s low with no key waiting" % ", ".join(low[0]))
        return low[1]

    def _mux_wiring(self):
        """which input reaches each of the graphics RAM's address pins through IC2-IC5: on the CPU side (NMUX high: bus
        A0-A7, the Y register, CPAGE) and on the display side (the 6845's MA and RA, DPAGE). Each input is tried alone,
        0 then 1, with every other input unknown: a pin that follows it then follows nothing else."""
        c = self.c; f = lambda ref, name: self.nl.net(ref, self.nl.pin_by_function(ref, name))
        reg = [(("C", i), n) for i, n in enumerate(self.ctrl["q"]) if not _open(n)]          # the control register's bits
        cpu = [(("A", i), self.sig["A%d" % i]) for i in range(8)] + [(("Y", i), n) for i, n in enumerate(self.yreg["q"])] + reg
        disp = [(("MA", i), f("IC4", "MA%d" % i)) for i in range(12)] + [(("RA", i), f("IC4", "RA%d" % i)) for i in range(3)] + reg
        self.cpu_map = self._follow(cpu, qc=0, rco=0); self.disp_map = self._follow(disp, qc=1, rco=0)

    def _follow(self, sources, qc, rco):
        c = self.c; found = {}
        for src, net in sources:
            got = []
            for level in (0, 1):
                self._unknown(); c.drive(TPA=0, TPB=0, MRD=1, MRW=1, VMA=1, RESET=1)
                for n in self.a_line: c.ext[n] = X
                c.forced[self.counter["qc"]] = ("IC15", qc); c.forced[self.counter["rco"]] = ("IC15", rco)
                if net in self.a_line: c.ext[net] = level
                else: c.forced[net] = ("probe", level)
                val = c.settle(); got.append({j for j, n in enumerate(self.ram_g["addr"]) if val.get(n) == level})
            for j in got[0] & got[1]:
                if j in found: raise ValueError("GFX RAM A%d follows %s and %s" % (j, found[j], src))
                found[j] = src
        missing = [j for j in range(15) if j not in found]
        if missing: raise ValueError("GFX RAM address pins that follow no input: %s" % ", ".join("A%d" % j for j in missing))
        return [found[j] for j in range(15)]

    def cell(self, lo, ctrl=None, y=None):
        """the graphics RAM's address for a CPU access at low address byte lo, as the multiplexers make it from the bus
        lines, the Y register and CPAGE -> (RAM address, page, index of that cell in the behavioural model's page).
        The index is what the display side makes of the same RAM address: scan line RA of the character row MA / 64,
        column MA % 64 (64 characters a row, 8 lines a row), so line = 8 * row + RA, stored 64 bytes a line."""
        ctrl = self.v.ctrl if ctrl is None else ctrl; y = self.v.yreg if y is None else y; ga = 0
        for j, src in enumerate(self.cpu_map):
            ga |= (((lo if src[0] == "A" else y if src[0] == "Y" else ctrl) >> src[1]) & 1) << j
        ma = ra = page = 0
        for j, src in enumerate(self.disp_map):
            b = (ga >> j) & 1
            if src[0] == "MA": ma |= b << src[1]
            elif src[0] == "RA": ra |= b << src[1]
            else: page = b
        return ga, page, ((ma >> 6) * 8 + ra) * 64 + (ma & 63)

    def _window(self, lo, byte):
        """a window access through the slot: read (byte None) -> (the byte on the bus, faults); write -> (None, faults)"""
        if not self.slot_checked: self.slot_check()
        faults = [self.slot_fault] if self.slot_fault else []
        ga, page, i = self.cell(lo); mem = self.v.pages[page]
        if i >= len(mem): return FLOAT, faults + ["the window reaches RAM address %04X, past the %d lines the model keeps" % (ga, len(mem) // 64)]
        if byte is None:
            return sum(((mem[i] >> j) & 1) << self.rd_bit[j] for j in range(8)), faults
        mem[i] = sum(((byte >> self.wr_bit[j]) & 1) << j for j in range(8)); self.v.dirty = True; self.v.writes += 1
        return None, faults

    # ------------------------------------------------------------------ the slot, through the gates
    def slot(self, lo, byte=None, start=8, counts=16, cells=None, ctrl=0, y=0, after=8, ma=0x155, ra=2):
        """a window cycle with the character counter stepped through `counts` counts from `start` (8-15), the CPU's
        address and strobes held as they are from 2.5 T (a read: -MRD low; a write: -MRW low, the byte on D0-D7), then
        `after` more counts with the strobe released. The counter's outputs, the control and Y registers, the 6845's
        refresh address (ma, ra: what the display half reads) and the RAM's data pins are played on their nets;
        everything else is the gates. cells: {RAM address: byte} (the RAM, RAM bit
        order). -> dict(writes=[(step, count, RAM address, byte)], latch=the read latch's byte (RAM bit order) or None,
        drives=the read latch is on the bus at the end of the strobe, faults=[...])"""
        c = self.c; cells = {} if cells is None else cells; write = byte is not None; a = (self.block << 12) | 0xC00 | lo
        self._unknown(); self._set(self.wrq["q"], 0)                 # no window write in the cycles before this one
        for i, n in enumerate(self.ctrl["q"]): c.forced[n] = ("IC19", (ctrl >> i) & 1)
        for i, n in enumerate(self.yreg["q"]): c.forced[n] = ("IC10", (y >> i) & 1)
        for i, n in enumerate(self.crtc["ma"]): c.forced[n] = ("IC4", (ma >> i) & 1)
        for i, n in enumerate(self.crtc["ra"]): c.forced[n] = ("IC4", (ra >> i) & 1)
        res = dict(writes=[], latch=None, drives=False, faults=[])
        def count(k):
            for name, lv in (("qa", k & 1), ("qb", (k >> 1) & 1), ("qc", (k >> 2) & 1), ("rco", 1 if k == 15 else 0)):
                c.forced[self.counter[name]] = ("IC15", lv)
            return c.settle()
        def data(val, k, n):
            """what is on the RAM's data pins now: the write buffer's byte, the RAM's, both (a fight) or the pull-ups'"""
            we, oe, cs = (val.get(self.ram_g[x]) for x in ("we", "oe", "cs")); buf = [val.get(x) for x in self.wrb["oe"]]
            ga = [val.get(x) for x in self.ram_g["addr"]]; adr = None if any(x not in (0, 1) for x in ga) else sum(b << j for j, b in enumerate(ga))
            if any(x not in (0, 1) for x in (we, oe, cs) + tuple(buf)):
                res["faults"].append("count %d: the RAM's or the write buffer's enables undefined (-WE %s -OE %s buffer %s)" % (k, we, oe, buf)); return None
            buffer_on = buf == [0, 0]; ram_on = cs == 0 and oe == 0 and we == 1
            if buf[0] != buf[1]: res["faults"].append("count %d: half of the write buffer is on" % k)
            if buffer_on and ram_on: res["faults"].append("count %d: the write buffer and the RAM both drive the RAM's data pins" % k)
            if buffer_on and not (write and n < counts): res["faults"].append("count %d: the write buffer is on with no byte from the CPU on D0-D7" % k)
            if (ram_on or (cs == 0 and we == 0)) and adr is None: res["faults"].append("count %d: the RAM is used with an undefined address" % k); return None
            d = sum(((byte >> self.wr_bit[j]) & 1) << j for j in range(8)) if buffer_on and write else 0xFF if buffer_on else \
                cells.get(adr, 0xFF) if ram_on else 0xFF
            if cs == 0 and we == 0:
                if not buffer_on: res["faults"].append("count %d: -WE is low with the write buffer off" % k)
                cells[adr] = d; res["writes"].append((n, k, adr, d))
            return d
        c.drive(TPA=1, TPB=0, A=a >> 8, VMA=0, MRD=1, MRW=1, RESET=1); count(start); c.drive(TPA=0); c.settle(); c.drive(A=lo)
        if write: c.drive(MRW=0, D=byte)
        else: c.drive(MRD=0)
        k = start; val = count(k); d = data(val, k, 0); qc = val.get(self.rdl["clk"])
        for n in range(1, counts + after):
            if n == counts: c.drive(MRD=1, MRW=1, D=None)
            k = 8 + (k - 7) % 8; val = count(k); before = d; d = data(val, k, n)
            now = val.get(self.rdl["clk"])
            if qc == 0 and now == 1 and n < counts: res["latch"] = before      # the '374 takes what was there at the edge
            qc = now
            if n == counts - 1: res["drives"] = [val.get(x) for x in self.rdl["oe"]] == [0]
        return res

    def slot_check(self, write_counts=12):
        """run the slot through the gates for one cell from each of the counter's eight phases, a write and then a read:
        each write must put the byte in the cell the multiplexer wiring names, with a whole -WE (counts 9 and 10) at
        least once and nowhere else, with the RAM off its own data pins; nothing may be written once -MRW is back up;
        each read must leave that byte in the read latch, and the latch on the bus. write_counts: how long -MRW is low,
        in dot clocks of 83 ns (12 = 1 us, its 2 T at a 2 MHz 1802; the design's limit, DESIGN.md section 5, is 11).
        What it finds wrong is kept in slot_fault and comes back with every window access."""
        self.slot_checked = True; bad = []
        if not self.gfx: return None
        lo, y, ctrl = 0x2A, 0xA5, 0x10; ga = self.cell(lo, ctrl, y)[0]; byte = 0x5A
        ram_byte = sum(((byte >> self.wr_bit[j]) & 1) << j for j in range(8))
        for start in range(8, 16):
            cells = {}; r = self.slot(lo, byte, start=start, counts=write_counts, cells=cells, ctrl=ctrl, y=y); bad += r["faults"]
            at = [k for n, k, adr, d in r["writes"]]
            if not any(a == 9 and b == 10 for a, b in zip(at, at[1:])): bad.append("a write from count %d gets no whole -WE (counts 9 and 10): %s" % (start, at or "none"))
            for n, k, adr, d in r["writes"]:
                if adr != ga or d != ram_byte: bad.append("a write from count %d puts %02X at RAM %04X at count %d (wanted %02X at %04X)" % (start, d, adr, k, ram_byte, ga))
                if n >= write_counts: bad.append("a write from count %d: -WE is low after -MRW has risen" % start)
            r = self.slot(lo, None, start=start, cells={ga: ram_byte}, ctrl=ctrl, y=y); bad += r["faults"]
            if r["writes"]: bad.append("a read from count %d writes the RAM" % start)
            if r["latch"] != ram_byte: bad.append("a read from count %d leaves %r in the read latch (the cell holds %02X)" % (start, r["latch"], ram_byte))
            if not r["drives"]: bad.append("a read from count %d: the read latch is not on the bus" % start)
        bad = list(dict.fromkeys(bad))
        self.slot_fault = ("the graphics window's slot: " + "; ".join(bad[:4]) + (" (and %d more)" % (len(bad) - 4) if len(bad) > 4 else "")) if bad else None
        return self.slot_fault

    # ------------------------------------------------------------------ for people and tests
    def early(self, a, vma=0):
        """the parts a read at a enables before the low address byte is on the bus and that are off again by the latch
        point: [(sub-phase, part)]. The 1802 takes -MRD low at 1.5 T, with the high byte still on A0-A7 until 2.5 T."""
        if self.page(a >> 8, vma, False) == "idle": return []
        samples = self._cycle(a, vma, False); final = {r for r, _ in dict(samples)["tpb"].reads}
        return [(ph, r) for ph, s in samples if ph in ("mrd", "hold") for r, _ in s.reads if r not in final]

    def shifts(self, a, vma=0):
        """the parts that stay on the bus through a read at a while their address pins change: [(sub-phase, part)].
        The text RAM does (its address lines carry the high byte until 2.5 T), which an asynchronous RAM does not mind;
        the 6845 does in a read of an odd register address (x801): its E is high from -MRD's fall, with A8 on RS, and
        A0 arrives a clock later."""
        if self.page(a >> 8, vma, False) == "idle": return []
        return list(self._make(self._cycle(a, vma, False), False).shifts)

    def trace(self, a, vma=0, write=False):
        """one cycle sub-phase by sub-phase: [(name, parts on the bus, parts written, flip-flops cleared, {register clock
        levels})], from an unknown card (for the tests and for reading the design)"""
        return [(ph, [r for r, _ in s.reads], [r for r, _ in s.writes], list(s.clears), dict(s.clocks)) for ph, s in self._cycle(a, vma, write)]

    def describe(self):
        nl = self.nl; out = ["VIDEO-G %s: %s%s" % (self.rev, os.path.relpath(nl.path, ROOT), " + GFX on the ribbon" if self.gfx else ", TEXT alone (the ribbon unplugged)"),
                             "  " + self.note]
        out.append("  jumpers: SV1 block %X; JP3 KEY-READY on %s; JP1 %s" % (
            self.block, ", ".join(self.flags) or "no flag line", "IBM 5151 (MDA)" if self.v.monitor == "mda" else "NTSC"))
        out.append("  played on the pins the gates drive: " + "; ".join("%s = %s" % (r.replace(G, "GFX "), why.split(":")[0]) for r, why in self.played.items()))
        out.append("  off the bus path (checked from the netlist, not simulated): " +
                   " ".join("%s %s" % (r.replace(G, "GFX "), nl.parts[r].value) for r in self.c.unmodelled))
        if self.gfx:
            name = lambda s: s[0] + (str(s[1]) if len(s) > 1 else "")
            out.append("  graphics RAM address A14..A0, CPU side: " + " ".join(name(s) for s in reversed(self.cpu_map)))
            out.append("  graphics RAM address A14..A0, display:  " + " ".join(name(s) for s in reversed(self.disp_map)))
            out.append("  the slot through the gates: " + ("not run yet (it runs at the first window access)" if not self.slot_checked else self.slot_fault or "a byte written from any counter phase lands once in its cell; a read brings it back"))
        return "\n".join(out)
