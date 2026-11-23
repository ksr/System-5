# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-06
"""Hardware-faithful System-5 (python3 -m s5emu --hw).

Every memory cycle is put on a modelled bus. Each card says whether it drives the data lines; two drivers at once
are bus contention, and the log records them (`bus` in the debugger).

  Netlist cards  gate level, from the card's KiCad netlist (hardware/<card>/kicad/<rev>/reports/netlist.net):
                   memory   Rev D (card of record), C, B-built (Ken's reworked board), B-drawn
                   6845     Rev B (the built card)
                 One bus cycle = three phases, as the 1802 runs them:
                   1. TPA high, the high address byte on A0-A7: the address latches (4042 / 74LS373) are transparent
                   2. TPA low: the latches hold A8-A15
                   3. the low address byte on A0-A7, -MRD / -MRW as the cycle needs, TPB high (the 6845's E)
                 then the control and address pins of each bus device (memory chips, the dual-port video RAM's bus
                 port, the 6845's register interface) decide who reads, writes or drives the bus.
                 Data never feeds back into a card's logic (checked at load), so a decode is a pure function of
                 (address, -VMA, -MRD, -MRW, jumpers) and is cached.
  CPU card       -VMA and the EPROM enable as the CPU Rev A notes describe them (hardware/cpu/eagle/rev-a/ops.html):
                 a flip-flop reset by -RESET is set by the first access with A15 high. Before that the EPROM answers at
                 every address (A0-A11) and -VMA is high. After it, in Boot/REMAP mode, the EPROM answers only in its
                 4K window (SV2/SV4, default F000) and -VMA is high there; Boot-only and No-ROM modes as documented.
                 Behavioural until the CPU card's netlist exists (Fusion export pending). Assumption: the flip-flop
                 changes at the end of the cycle, so the first A15 access itself still sees the boot map.
  IO, IDE        I/O ports only, as in machine.py: they never drive the bus in a memory cycle.
  VIDEO-G 1.0    HWMachine(videog="1.0") / --hw --video g: the TEXT and GFX boards from their two netlists, joined by
                 the ribbon, in place of the 6845 card and the IO card: hwvideog.py (its own notes say how a cycle
                 is run there: sub-phase by sub-phase as the 1802 times it, the high address byte still on A0-A7
                 when -MRD falls). videog="none" puts the behavioural model (videog.py) on the modelled bus instead.

Contention is resolved as the AND of the drivers (a low usually wins a TTL fight); the log keeps every case.
"""
import datetime, os
from .machine import Machine, FLOAT, CPUCardROM
from .rtc import DS12885
from .uart import UART16550
from .netlist import Netlist
from .logic import Circuit, classify, X

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
MEM_NET = "hardware/memory/kicad/rev-%s/reports/netlist.net"

# Rev F's EEPROM sockets (hardware/memory/kicad/rev-f): a 2 x 3 jumper block per socket, JP2 for IC3 (EPROM LO) and JP1
# for IC5 (EPROM HI): pin 1 VCC, 3 the socket's pin 1, 5 A14; 2 A14, 4 the socket's pin 27, 6 WR. Each jumper names the
# net that keeps its name first.
_REV_F = {
    "27C256 LO": [("jumper", "JP2", "1", "JP2", "3"), ("jumper", "JP2", "2", "JP2", "4")],
    "27C256 HI": [("jumper", "JP1", "1", "JP1", "3"), ("jumper", "JP1", "2", "JP1", "4")],
    "28C256 HI": [("refit", "IC5", "28C256", {"1": "A14", "27": "~{WE}"}), ("jumper", "JP1", "5", "JP1", "3")],
    "write HI": [("jumper", "JP1", "6", "JP1", "4")],
}
# Per-revision cards. 'rework' = netlist edits in order (lift / wire / jumper / refit); 'fitted' = parts in their sockets
# (None = all).
MEMORY_REVS = {
    "D": dict(net=MEM_NET % "d", note="Rev D, the 2026 KiCad master: the card of record for hardware emulation (Ken, 2026-10-06)."),
    "F": dict(net=MEM_NET % "f", rework=_REV_F["27C256 LO"] + _REV_F["27C256 HI"],
              note="Rev F (MEM3-F, 2026-11-18): Rev E's circuit with EEPROM sockets, the silkscreen fixed and the bus "
                   "connector named J1; not built. A 27C256 in IC3 and IC5, JP2 and JP1 set for it (shunts 1-3: pin 1 VPP "
                   "on VCC; 2-4: pin 27 on A14), so it decodes, reads and writes as Rev D."),
    "F-28C256": dict(net=MEM_NET % "f", rework=_REV_F["27C256 LO"] + _REV_F["28C256 HI"],
                     note="Rev F with a 28C256 EEPROM in IC5 (EPROM HI: 8000-EFFF with the usual jumpers), read-only: JP1 "
                          "3-5 puts A14 on its pin 1, and with no shunt on 4-6 R6 (47k) holds its !WE (pin 27) high. "
                          "IC3 a 27C256."),
    "F-28C256-W": dict(net=MEM_NET % "f", rework=_REV_F["27C256 LO"] + _REV_F["28C256 HI"] + _REV_F["write HI"],
                       note="Rev F with a 28C256 EEPROM in IC5 that the CPU can write: JP1 3-5 and 4-6 (its !WE on WR, the "
                            "RAMs' write strobe). A write lands at once here; a real 28C256 is busy for up to 10 ms "
                            "after it. IC3 a 27C256."),
    "C": dict(net=MEM_NET % "c", note="Rev C (2005): every !CE = Y OR bank select."),
    "B-built": dict(net=MEM_NET % "b", fitted={"IC1", "IC2", "IC5", "IC6", "IC7", "IC8", "IC9", "IC13", "IC14"},
                    rework=[("lift", "IC1", "20"), ("wire", "IC1", "20", "IC14", "3"),
                            ("lift", "IC5", "20"), ("wire", "IC5", "20", "IC14", "6")],
                    note="Ken's Rev B board (PCB Fab Express FXA5474) from the 2026-10-05 photos: RAM in IC1, EPROM in "
                         "IC5, muxes IC2/IC13; red wires put the 74LS32 bank selects on IC1/IC5 !CE (hardware/memory/"
                         "REVIEW.md). Which IC14 pins carry them is the likeliest reading, not yet confirmed; logically "
                         "a spare gate used as a buffer is the same wire."),
    "B-drawn": dict(net=MEM_NET % "b", note="Rev B exactly as drawn and ordered, all sockets filled: the 74LS151 strobe "
                                            "enables the deselected bank (REVIEW.md finding 1)."),
}
VIDEO_REVS = {
    "B": dict(net="hardware/video-6845/kicad/rev-b/reports/netlist.net",
              rework=[("jumper", "SV1", "1", "SV1", "2")],
              note="6845 Rev B, Ken's working card (Fusion export 2026-10-08; = the April 2005 CAM files). Its bus side is Rev A's, unchanged. A 74LS85 compares "
                   "the latched A12-A15 with SV1 and only matches while -VMA is low; in that 4K block A11 = 0 is the "
                   "IDT7134 (2K used), A11 = 1 the 6845 (RS = A0, so mirrored through x800-xFFF). SV1 1-2 fitted = "
                   "block 7 (7000), where HBIOS puts the screen: seen in the 2026-10-07 photos."),
    "B-Clean": dict(net="hardware/video-6845/kicad/rev-b-clean/reports/netlist.net",
                    rework=[("jumper", "SV1", "1", "SV1", "2")],
                    note="6845 Rev B-Clean (2026-11-20, not built): Rev B without the DE-9 and with the 6845's light-pen input on "
                         "ground; on the bus it is Rev B. SV1 1-2 fitted = block 7."),
    "B-Clean-Keyboard": dict(
        net="hardware/video-6845/kicad/rev-b-clean-keyboard/reports/netlist.net",
        rework=[("jumper", "SV1", "1", "SV1", "2")],
        keyboard=dict(latch="IC19", status="IC20", ready="IC18", mcu="IC21", drv=("IC22", "9", "8"), flag="JP1"),
        played=("IC19", "IC20"), controls=(("IC19", "1"), ("IC20", "1"), ("IC20", "19"), ("IC18", "13")),
        note="6845 Rev B-Clean-Keyboard (2026-11-20, not built): Rev B-Clean on the 36-pin bus with VIDEO-G TEXT's PS/2 "
             "keyboard section. The video RAM is at 7000-77FF as on Rev B. A 74HCT138, enabled by Rev B's upper-half select "
             "and A10 low, picks by A1-A2: the 6845 (7800/7801), the key latch (7802: the read clears KEY-READY at TPB) and "
             "the status buffer (7804: bit 0 KEY-READY, bit 7 = 1); the same every 8 addresses through 7BFF. KEY-READY "
             "pulls the bus flag line JP1 picks. SV1 1-2 fitted = block 7; the key latch, the status buffer and the "
             "ATmega are played on the enables the card's gates make."),
}
IDE_REVS = {
    "A": dict(net="hardware/ide-cf/kicad/rev-a/reports/netlist.net",
              rework=[("jumper", "SV1", "3", "SV1", "4"), ("jumper", "SV2", "5", "SV2", "6")],
              note="IDE/CF Rev A, the built card (Fusion export 2026-10-06; no copper gerbers survive to check it against). "
                   "A 74LS138 decodes N0-N2; SV1 picks the register-select port, SV2 the data port. SV1 3-4 (port 2) and "
                   "SV2 5-6 (port 3): derived from the code, not yet seen on the board - Mike Riley's BIOS reaches the "
                   "drive only by OUT 2 (register) and OUT 3 / INP 3 (data), and its register codes 0-7 and 0E match "
                   "the 74LS75 latch (D0-2 = DA0-2, D3 = CS1)."),
}
# the drive end of a 40-pin ATA cable, by header pin (standard ATA pinout)
ATA_PINS = {"17": "DD0", "15": "DD1", "13": "DD2", "11": "DD3", "9": "DD4", "7": "DD5", "5": "DD6", "3": "DD7",
            "35": "DA0", "33": "DA1", "36": "DA2", "37": "CS0", "38": "CS1", "23": "DIOW", "25": "DIOR"}
DEFAULT_JUMPERS = "RRRRRRR-EEEEEEE-"
_JUMPER_MAPS = {}                                        # rev -> map, shared: probing a card takes about a second


def jumper_list(j):
    """'RRRRRRR-EEEEEEE-' or machine.py's list form -> 16 chars"""
    if j is None: return DEFAULT_JUMPERS
    if isinstance(j, str): return j.upper()
    return "".join({"RAM": "R", "ROM": "E", None: "-"}[x] for x in j)


class NetlistCard:
    """one card on the bus, simulated from its netlist. store = {device ref: (read(addr), write(addr, byte))}"""
    def __init__(self, name, rev, spec, root=ROOT):
        self.name, self.rev, self.note = name, rev, spec["note"]
        self.nl = Netlist(os.path.join(root, spec["net"]))
        for op, *args in spec.get("rework", []): getattr(self.nl, op)(*args)
        # controls: pins (ref, pin) whose nets the bus-path proof must also cover; played: parts on the data lines that
        # the card's class plays itself (a latch, a buffer), on the enables the gates make
        self.played = set(spec.get("played", ()))
        self.c = Circuit(self.nl, spec.get("fitted"), [self.nl.net(r, pn) for r, pn in spec.get("controls", ())])
        self.devices = self.c.mem; self.store = {}; self.cache = {}
        self._check_data_path()

    def _check_data_path(self):
        """device data pins -> bus data bit, and proof that the data lines reach nothing but bus devices and the connector"""
        bus_d = {self.c.bus.sig["D%d" % i]: i for i in range(8)}
        devs = {r for r, p in self.nl.parts.items() if classify(p.lib) in ("RAM", "ROM", "DPRAM", "CRTC")}   # fitted or not
        conn = self.c.bus.ref; self.bitmap = {}
        for d in self.devices:
            bits = []
            for net in d.data:
                if net not in bus_d: raise ValueError("%s data pin on %s, not a bus data line" % (d.ref, net))
                bits.append(bus_d[net])
            self.bitmap[d.ref] = bits
        for net in bus_d:
            for ref, _ in self.nl.nets.get(net, []):
                if ref not in devs and ref != conn and ref not in self.played:
                    raise ValueError("bus data line %s also reaches %s: the decode cache would not be valid" % (net, ref))

    # ------------------------------------------------------------------ one bus cycle
    def _run(self, a, vma, mrd, mrw):
        c = self.c
        c.drive(TPA=1, TPB=0, A=a >> 8, VMA=vma, MRD=1, MRW=1); c.settle()
        c.drive(TPA=0); c.settle()
        c.drive(A=a & 0xFF, MRD=mrd, MRW=mrw, TPB=1); v = c.settle()
        acts = []; faults = []
        for d in self.devices:
            r = d.access(v)
            if isinstance(r, str): faults.append(r)
            elif r: acts.append((d.ref, d.kind, r[0], r[1]))
        return acts, faults

    def decode(self, a, vma, mrd, mrw):
        key = (a, vma, mrd, mrw); r = self.cache.get(key)
        if r is None:
            acts, faults = self._run(a, vma, mrd, mrw); r = self.cache[key] = (tuple(acts), tuple(faults))
        return r

    def bus_read(self, a, vma):
        """-> [(driver name, byte)], [faults]"""
        acts, faults = self.decode(a, vma, 0, 1); out = []
        for ref, kind, op, ca in acts:
            if op != "r": continue
            b = self.store[ref][0](ca); bits = self.bitmap[ref]
            out.append(("%s %s" % (self.name, ref), sum(((b >> i) & 1) << bits[i] for i in range(8))))
        return out, faults

    def bus_write(self, a, vma, v):
        """-> [receiver names], [faults]"""
        acts, faults = self.decode(a, vma, 1, 0); out = []
        for ref, kind, op, ca in acts:
            if op != "w": continue
            bits = self.bitmap[ref]
            self.store[ref][1](ca, sum(((v >> bits[i]) & 1) << i for i in range(8))); out.append("%s %s" % (self.name, ref))
        return out, faults

    def describe(self):
        out = ["%s card %s: %s" % (self.name, self.rev, os.path.relpath(self.nl.path, ROOT)), "  " + self.note]
        out += ["  rework: " + e for e in self.nl.edits]
        if self.c.empty: out.append("  empty sockets: " + " ".join(self.c.empty))
        if self.c.unmodelled:
            out.append("  off the bus path (checked from the netlist, not simulated): " +
                       " ".join("%s %s" % (r, self.nl.parts[r].value) for r in self.c.unmodelled))
        return "\n".join(out)


class NetlistMemoryCard(NetlistCard):
    def __init__(self, rev="D", jumpers=None, root=ROOT):
        if rev not in MEMORY_REVS: raise ValueError("memory revision %r: one of %s" % (rev, ", ".join(MEMORY_REVS)))
        super().__init__("mem", rev, MEMORY_REVS[rev], root)
        self.chips = self.devices
        self.contents = {m.ref: bytearray(0x8000) if m.kind == "RAM" else bytearray([FLOAT]) * 0x8000 for m in self.chips}
        for ref, mem in self.contents.items():
            self.store[ref] = (mem.__getitem__, mem.__setitem__)
        self.rom = None                                  # (machine.py's MemoryCard has a flat .rom; this card has chips)
        self.set_jumpers(jumpers)

    # ------------------------------------------------------------------ jumpers
    def jumper_map(self):
        """{net: [(chip ref, kind, 4K block), ...]}: what grounding each header net enables, found by trying each one
        on the netlist. Nets that change nothing (a rework took the chip off its mux) are left out."""
        if self.rev in _JUMPER_MAPS: return _JUMPER_MAPS[self.rev]
        hdr = {r for r, p in self.nl.parts.items() if "MA08" in p.lib}
        cands = sorted({net for (r, _), (net, _) in self.nl.pins.items() if r in hdr and net not in Circuit.POWER})
        saved = self.c.forced; self.c.forced = {}
        base = {b: self._enabled(b << 12) for b in range(16)}
        out = {}
        for net in cands:
            self.c.forced = {net: ("jumper", 0)}
            got = [(ref, kind, b) for b in range(16) for ref, kind in self._enabled(b << 12) - base[b]]
            if got: out[net] = got
        self.c.forced = saved; _JUMPER_MAPS[self.rev] = out
        return out

    def _enabled(self, a):
        acts, _ = self._run(a, 0, 0, 1)
        return {(ref, kind) for ref, kind, _, _ in acts}

    def set_jumpers(self, jumpers):
        """jumpers: 16 chars from 0000, R = the RAM for that block, E = the EPROM, - = none"""
        self.jumpers = jumper_list(jumpers)
        if len(self.jumpers) != 16 or set(self.jumpers) - set("RE-"): raise ValueError("jumpers: 16 of R/E/-")
        want = {(("RAM" if ch == "R" else "ROM"), b) for b, ch in enumerate(self.jumpers) if ch != "-"}
        forced = {}; self.jumpers_fitted = []; served = set()
        for net, hits in self.jumper_map().items():
            hit = [(kind, b) for _, kind, b in hits if (kind, b) in want]
            if hit:
                forced[net] = ("jumper", 0); served.update(hit)
                pins = ["%s.%s" % k for k in self.nl.nets[net] if "MA08" in self.nl.parts[k[0]].lib]
                self.jumpers_fitted.append("%s (%s)" % ("/".join(pins), ", ".join("%s %X000" % (r, b) for r, _, b in hits)))
        self.jumpers_unused = sorted(want - served)        # asked for, but nothing on this card answers to it
        self.c.forced = forced; self.cache.clear()

    def program(self, a, v):
        """an EPROM programmer's view: put byte v where a read of bus address a (-VMA low) finds an EPROM"""
        for ref, kind, op, ca in self.decode(a, 0, 0, 1)[0]:
            if kind == "ROM":
                bits = self.bitmap[ref]; self.contents[ref][ca] = sum(((v >> bits[i]) & 1) << i for i in range(8)); return True
        return False

    def describe(self):
        out = [super().describe()]
        out.append("  jumpers %s:" % self.jumpers + ("" if self.jumpers_fitted else " none take effect on this card"))
        out += ["    " + j for j in self.jumpers_fitted]
        if self.jumpers_unused:
            out.append("    asked for but not on this card: " + ", ".join("%s %X000" % kb for kb in self.jumpers_unused))
        return "\n".join(out)


class NetlistVideoCard(NetlistCard):
    """the 6845 card; its video RAM and CRTC registers are the Video6845 object the screen is drawn from"""
    def __init__(self, video, rev="B", root=ROOT, spec=None):
        if rev not in VIDEO_REVS: raise ValueError("6845 card revision %r: one of %s" % (rev, ", ".join(VIDEO_REVS)))
        super().__init__("6845", rev, spec or VIDEO_REVS[rev], root)
        self.v = video
        for d in self.devices:
            self.store[d.ref] = (self._vram_rd, self._vram_wr) if d.kind == "DPRAM" else (self._crtc_rd, self._crtc_wr)

    def _vram_rd(self, a): return self.v.vram[a % len(self.v.vram)]
    def _vram_wr(self, a, b): self.v.vram[a % len(self.v.vram)] = b; self.v.dirty = True

    def _crtc_rd(self, rs):
        """MC6845: R14-R17 read back; the address register and the other registers are write-only and read as 0"""
        return self.v.reg[self.v.sel] if rs and self.v.sel in (14, 15, 16, 17) else 0

    def _crtc_wr(self, rs, b):
        if not rs: self.v.sel = b & 31
        elif self.v.sel < 18: self.v.reg[self.v.sel] = b; self.v.dirty = True


class NetlistVideoKbdCard(NetlistVideoCard):
    """the 6845 card with the PS/2 keyboard section (Rev B-Clean-Keyboard). The video RAM and the 6845 are Rev B's,
    through Rev B's gates and the new decoder; the keyboard section's gates are simulated too (the '138, the '32, the
    '00, the KEY-READY '74), and three parts are played on the pins those gates drive:
      the key latch ('374)    its byte goes on the data lines while its enable (-RDKEY, from the gates) is low; which
                              bus bit each code bit lands on is followed through the netlist (ATmega pin -> MD net ->
                              latch D -> latch Q -> bus line)
      the status buffer ('244) while its two enables (-RDSTAT) are low: each section's input level on its output's bus
                              line. KEY-READY is this model's flag; a supply pin is its level; VSYNC and DE, the 6845's
                              counter outputs, are not counted for this card and read 0
      the ATmega328P          when a key waits and KEY-READY is low it loads the latch and sets KEY-READY (its LDDATA
                              edge clocks both); a cycle in which the gates take the '74's clear low (a read of the key
                              at TPB) clears KEY-READY
    KEY-READY pulls the bus line low that JP1 KBD FLAG picks, through a gate of the card's second 7416 (ef())."""
    FLAG_PAIRS = {"-EF1": ("1", "2"), "-EF2": ("3", "4"), "-EF3": ("5", "6"), "-EF": ("7", "8")}
    MCU_MD = ("23", "24", "25", "26", "27", "28", "14", "15")            # the ATmega's pins for MD0-MD7 (PC0-5, PB0-1)
    REG_374 = (("3", "2"), ("4", "5"), ("7", "6"), ("8", "9"), ("13", "12"), ("14", "15"), ("17", "16"), ("18", "19"))   # D, Q
    BUF_244 = (("2", "18", "1"), ("4", "16", "1"), ("6", "14", "1"), ("8", "12", "1"),                # A, Y, its enable
               ("11", "9", "19"), ("13", "7", "19"), ("15", "5", "19"), ("17", "3", "19"))

    def __init__(self, video, kbd, rev="B-Clean-Keyboard", kbd_flag="-EF", root=ROOT):
        spec = dict(VIDEO_REVS[rev]); k = spec["keyboard"]
        if kbd_flag is not None and kbd_flag not in self.FLAG_PAIRS:
            raise ValueError("KBD FLAG %r: one of %s, or None for no shunt" % (kbd_flag, ", ".join(self.FLAG_PAIRS)))
        if kbd_flag:
            a, b = self.FLAG_PAIRS[kbd_flag]; spec["rework"] = list(spec.get("rework", [])) + [("jumper", k["flag"], a, k["flag"], b)]
        super().__init__(video, rev, root, spec)
        nl = self.nl; self.kb = kbd; self.k = k; self.kbd_flag = kbd_flag; self.ready = False; self.latch = 0
        bus_d = {self.c.bus.sig["D%d" % i]: i for i in range(8)}
        # the key latch: code bit i is on the ATmega's MDi pin; the latch's D pin on that net; its Q pin's bus line
        d_of = {nl.net(k["latch"], d): q for d, q in self.REG_374}; bits = []
        for i, pin in enumerate(self.MCU_MD):
            md = nl.net(k["mcu"], pin)
            if md not in d_of: raise ValueError("%s: the ATmega's MD%d (pin %s) reaches no input of the key latch" % (rev, i, pin))
            q = nl.net(k["latch"], d_of[md])
            if q not in bus_d: raise ValueError("%s: the key latch's output for MD%d is on %s, not a bus data line" % (rev, i, q))
            bits.append(bus_d[q])
        if sorted(bits) != list(range(8)): raise ValueError("%s: the key latch does not reach all eight data lines" % rev)
        self.bitmap[k["latch"]] = bits; self.store[k["latch"]] = (lambda ca: self.latch, None)
        # the status buffer: section i's output is a bus line; its input a level
        self.status_in = []; bits = []
        for a, y, _ in self.BUF_244:
            yn = nl.net(k["status"], y)
            if yn not in bus_d: raise ValueError("%s: the status buffer's pin %s is on %s, not a bus data line" % (rev, y, yn))
            bits.append(bus_d[yn]); self.status_in.append(nl.net(k["status"], a))
        self.bitmap[k["status"]] = bits; self.store[k["status"]] = (lambda ca: self._status(), None)
        self.n_rdkey = nl.net(k["latch"], "1"); self.n_rdstat = sorted({nl.net(k["status"], e) for _, _, e in self.BUF_244})
        self.n_kclr = nl.net(k["ready"], "13"); self.n_kready = nl.net(k["ready"], "9")       # the '74's second half
        if nl.net(k["ready"], "11") != nl.net(k["latch"], "11"):
            raise ValueError("%s: KEY-READY's clock and the key latch's clock are not one net (the ATmega's LDDATA)" % rev)
        d_ref, d_in, d_out = k["drv"]                                      # the open-collector gate onto the flag line
        if nl.net(d_ref, d_in) != self.n_kready: raise ValueError("%s: the flag driver's input (%s pin %s) is not on KEY-READY" % (rev, d_ref, d_in))
        self.n_flag = nl.net(d_ref, d_out)                                 # its output: the line JP1 joins to the bus

    def _status(self):
        """the '244's eight sections' inputs, bit i = section i (the bitmap puts each on its bus line)"""
        s = 0
        for i, n in enumerate(self.status_in):
            if (self.ready if n == self.n_kready else Circuit.POWER.get(n, 0)): s |= 1 << i
        return s

    def _atmega(self):
        if not self.ready and self.kb.queue:
            self.latch = self.kb.queue.pop(0); self.ready = True

    def reset(self): self.ready = False                                    # -RESET clears KEY-READY (and restarts the ATmega)

    def ef(self, line):
        """True while KEY-READY pulls this bus flag line low (line: '-EF1', '-EF2', '-EF3' or '-EF')"""
        self._atmega()
        return self.ready and self.c.bus.sig.get("-EF4" if line == "-EF" else line) == self.n_flag

    def _run(self, a, vma, mrd, mrw):
        acts, faults = super()._run(a, vma, mrd, mrw); v = self.c.val
        def low(net, what):
            x = v.get(net)
            if x not in (0, 1): faults.append("%s is neither on nor off" % what)
            return x == 0
        if low(self.n_rdkey, "the key latch's enable"): acts.append((self.k["latch"], "KEY", "r", 0))
        st = [low(n, "the status buffer's enable") for n in self.n_rdstat]
        if any(st):
            if not all(st): faults.append("half of the status buffer is enabled")
            acts.append((self.k["status"], "STATUS", "r", 0))
        if low(self.n_kclr, "the KEY-READY clear"): acts.append((self.k["ready"], "READY", "c", 0))
        return acts, faults

    def bus_read(self, a, vma, log=True):
        """log off is a look (the debugger's, the bus map's): it clears nothing"""
        self._atmega()
        out, faults = super().bus_read(a, vma)
        if log and any(op == "c" for _, _, op, _ in self.decode(a, vma, 0, 1)[0]): self.ready = False
        return out, faults

    def bus_write(self, a, vma, v):
        out, faults = super().bus_write(a, vma, v); acts = self.decode(a, vma, 1, 0)[0]
        if any(op == "c" for _, _, op, _ in acts): self.ready = False; faults = list(faults) + ["a write cleared KEY-READY"]
        if any(op == "r" and kind in ("KEY", "STATUS") for _, kind, op, _ in acts):
            faults = list(faults) + ["the keyboard section drives the bus while the 1802 writes"]
        return out, faults


_CPU_EXTERNAL = {"U$1": "the CDP1802: the emulator's CPU core drives its address, data and strobe pins",
                 "U1": "the CM1232/DS1232 reset chip: the emulator's reset drives -RESET"}
_CPU_NOTE = ("A 74LS373 latches A8-A15 on TPA; a 74LS138 (SV2 = upper/lower 32K, SV4 = 4K bank) decodes the EPROM "
             "window; SV5 makes -VMA from the 74LS74 boot flip-flop (IC8B, cleared by -RESET); a 74LS05 enables the "
             "2732 while -VMA is high; JP1-JP4 route the bus -EF line and the card flags to EF1-4. Jumpers as built "
             "(photos 2026-10-07): SV2 H, SV4 bank 7, SV5 Boot/REMAP, JP1 row 3 (bus -EF to EF3), JP2-JP4 empty.")
CPU_REVS = {
    "A-built": dict(net="hardware/cpu/kicad/rev-a/reports/netlist.net", external=_CPU_EXTERNAL,
                    rework=[("retype", "IC1", "74xx-us_74x374_N_pwrhidden", "74LS374"),
                            ("lift", "IC8", "10"), ("wire", "IC8", "10", "SV2", "5"),     # PRE -> VCC: no window preset
                            ("lift", "IC8", "11"), ("wire", "IC8", "11", "SV2", "6"),     # CLK -> ADDR15 (latched A15)
                            ("lift", "IC8", "12"), ("wire", "IC8", "12", "SV2", "5")],    # D   -> VCC
                    note="CPU Rev A as built. " + _CPU_NOTE + " Rework (photos 2026-10-07, wiring derived "
                         "2026-10-07): IC1 is a 74LS374 (TPA rising edge); IC8 pins 10/11/12 are lifted and wired to "
                         "SV2 pin 5 (VCC) and the ADDR15 net, the only signals the red wires reach - so PRE = VCC, "
                         "D = VCC, CLK = ADDR15: the first rising edge of the latched A15 (the boot code's PHI R0 jump "
                         "to F003) ends the boot map, as YACC1's FORCE-ROM does and as the 2005 ops notes describe. "
                         "Which wire is which is inferred, not traced. The reset-circuit rework (IC5 pins 1/3, U1 pin "
                         "7) is off the bus path. See hardware/cpu/eagle/rev-a/rework/README.md."),
    "A": dict(net="hardware/cpu/kicad/rev-a/reports/netlist.net", external=_CPU_EXTERNAL,
              note="CPU Rev A as drawn (Fusion export 2026-10-06; = the 2005 order gerbers, holes and copper). " + _CPU_NOTE +
                   " As drawn, the boot flip-flop is set by the first access to the EPROM window (PRE = the window "
                   "select; D, CLK grounded)."),
}
CPU_REVS["D"] = dict(
    net="hardware/cpu/kicad/rev-d/reports/netlist.net", cpu="U1",
    external={"U1": "the CDP1802: the emulator's CPU core drives its address, data and strobe pins",
              "U10": "the DS1813 on -RESET: it only holds the line low longer (150 ms); the lines here have no time",
              "U12": "the DS1813 on SW_RST (power-on, the RESET/RUN switch's debounce): the emulator's reset holds SW_RST low",
              "X1": "the 4 MHz oscillator: the emulator's clock"},
    jumpers=[("JP2", "1", "JP2", "2"), ("JP3", "3", "JP3", "4"),     # EF1's block on -EF1, EF2's on -EF2
             ("JP4", "7", "JP4", "8")],                              # EF3's on -EF: the 2005 IO card's keyboard
    note="CPU Rev D (2026-10-30, not built; hardware/cpu/kicad/rev-d/DESIGN.md): a 74HCT373 latches A8-A15 while TPA is "
         "high; the boot map (the 2732 at every address, -VMA high) ends on the first A15 rising edge (U4B, cleared by "
         "CLEAR = -RESET through two 74HCT14s) unless LOADED (U8A: set by LOAD mode, cleared by a boot reset); a "
         "74HCT20 decodes F000-FFFF; -VMA and the EPROM's CE come from a 74HCT00. Since 2026-11-22 a boot reset is a "
         "state of the bus, -RESET and -DMAIN low with -PAUSE high: the RESET/RUN switch and power-on make it through "
         "the card's own open-drain gates (U11, a 74HC03, from SW_RST), the front panel's RESET button and the bus "
         "driver from outside; U6B decodes it and clears LOADED. The 1802's DMA IN is -DMAIN only once DMA_ARMED "
         "(U8B): -PAUSE low, and -DMAIN seen high since. Jumpers for the machine "
         "as it is today: EF1 -EF1, EF2 -EF2 and EF3 -EF on the EF blocks JP2-JP4 (the 2005 IO card's keyboard flag). A machine reset is the "
         "RESET/RUN switch: a boot reset, so it boots HBIOS.")


_IO_NOTE = ("IO Rev A, the built card (Fusion export 2026-10-06; = the 2005 order gerbers, holes and copper). A 74LS138 "
            "decodes N0-N2; SV2 picks the keyboard's CDP1852 port, SV6 the 1861's (a 74LS02 makes DISPON from INP, "
            "DISPOFF from OUT); SV1 sends the 1852's service request to EFK or the bus -EF line. As built (photo "
            "2026-10-07): SV2 13-14 (keyboard = port 1), SV1 2-3 (bus -EF, which the CPU card's JP1 puts on EF3), "
            "SV6 empty - the 1861 is on no port (it was never tested). The PIC16F84 + PAK-VI keyboard path and the "
            "1861's video timing stay behavioural.")
IO_REVS = {
    "A": dict(net="hardware/io-1861-keyboard/kicad/rev-a/reports/netlist.net",
              rework=[("jumper", "SV2", "13", "SV2", "14"), ("jumper", "SV1", "2", "SV1", "3")], note=_IO_NOTE),
    "A-1861": dict(net="hardware/io-1861-keyboard/kicad/rev-a/reports/netlist.net",
                   rework=[("jumper", "SV2", "13", "SV2", "14"), ("jumper", "SV1", "2", "SV1", "3"), ("jumper", "SV6", "7", "SV6", "8")],
                   note=_IO_NOTE + " This variant adds SV6 7-8: the 1861 on port 4 (INP 4 on, OUT 4 off)."),
}


class NetlistCPUCard:
    """the CPU card's address latch, EPROM window, boot flip-flop and -VMA, from its netlist; the 1802 itself is the
    emulator's CPU core. A memory cycle runs in the three bus phases with -RESET high; cycle() -> (-VMA, EPROM address
    or None). Its state (the boot flip-flop) carries from cycle to cycle. Jumpers come from the SV5 mode and the
    EPROM base: SV2 picks the 32K half (H: 1-3/2-4, L: 3-5/4-6), SV4 the 4K bank (pins 15-2b/16-2b), SV5 the mode
    (Boot/REMAP 3-4, Boot only 1-2, No ROM 5-6); JP1 5-6 = the bus -EF line on EF3 (as built)."""
    MODES = {"remap": ("SV5", "3", "SV5", "4"), "boot": ("SV5", "1", "SV5", "2"), "norom": ("SV5", "5", "SV5", "6")}

    def __init__(self, rom, rev="A-built", vma_mode="remap", root=ROOT):
        if rev not in CPU_REVS: raise ValueError("CPU card revision %r: one of %s" % (rev, ", ".join(CPU_REVS)))
        spec = CPU_REVS[rev]; self.name, self.rev, self.note, self.rom = "cpu", rev, spec["note"], rom
        self.nl = Netlist(os.path.join(root, spec["net"])); self.cpu_ref = spec.get("cpu", "U$1")
        if "jumpers" in spec: jumpers = spec["jumpers"]                 # Rev D: the EPROM is fixed at F000, no mode jumper
        else:
            b = rom.base >> 12
            jumpers = ([("SV2", "1", "SV2", "3"), ("SV2", "2", "SV2", "4")] if b & 8 else [("SV2", "3", "SV2", "5"), ("SV2", "4", "SV2", "6")])
            k = b & 7; jumpers += [("SV4", str(15 - 2 * k), "SV4", str(16 - 2 * k)), self.MODES[vma_mode],
                                   ("JP1", "5", "JP1", "6")]            # bus -EF -> EF3 (photo 2026-10-07; JP2-JP4 empty)
        for j in jumpers: self.nl.jumper(*j)
        for op, *args in spec.get("rework", []): getattr(self.nl, op)(*args)
        self.c = Circuit(self.nl, None, external=spec["external"])
        self.eprom = next(d for d in self.c.mem if d.kind == "ROM")
        self.vma = self.c.bus.sig["-VMA"]
        halves = [(m, i, h) for m in self.c.models if type(m).__name__ == "DFF74" for i, h in enumerate(m.ff)]
        if "jumpers" in spec:                                           # Rev D: boot flip-flop cleared by CLEAR, and LOADED
            boot = next((m, i) for m, i, h in halves if h[0].split("/")[-1] == "CLEAR")
            loaded = next((m, i) for m, i, h in halves if h[3].split("/")[-1] == "LOAD_L")
            self.flops = [boot, loaded]; named = lambda name: next((n for n in self.nl.nets if n.split("/")[-1] == name), None)
            self.sw_rst, self.n_clear, self.n_wait, self.n_dma = named("SW_RST"), named("CLEAR"), named("WAIT"), named("DMA_IN")
            self.own_reset = any(type(m).__name__ == "Nand03" for m in self.c.models)   # the card pulls -RESET itself (2026-11-22)
        else:                                                           # Rev A: the half -RESET clears
            rst = self.c.bus.sig["-RESET"]
            self.flops = [next((m, i) for m, i, h in halves if h[0] == rst)]; self.sw_rst = None
        self.ff, self.ffi = self.flops[0]
        self.cache = {}; self.ef_map = self.ef_routes(); self.reset()

    def ef_routes(self):
        """{EF number: 'KEF' | 'VEF' | ...}: which card flag each 1802 EF input is jumpered to"""
        out = {}
        for n in range(1, 5):
            try: pin = self.nl.pin_by_function(self.cpu_ref, "EF%d" % n)
            except KeyError: pin = self.nl.pin_by_function(self.cpu_ref, "~{EF%d}" % n)     # KiCad's stock 1802 symbol
            net = self.nl.net(self.cpu_ref, pin)
            for src in ("KEF", "VEF", "FEF", "-EF4", "-EF", "-EF1", "-EF2", "-EF3"):
                if net.endswith("/" + src) or net == src: out[n] = "-EF4" if src == "-EF" else src   # -EF = the 2005 -EF4
        return out

    def reset(self):
        """-RESET low, one bus cycle at 0000 (the 1802's initialization cycle: TPA loads 00 into the 74LS373, so the
        EPROM-window decode is defined), then -RESET high. On the real card the latch holds whatever it powered up with
        until that first TPA."""
        c = self.c
        if self.sw_rst and self.own_reset:
            # Rev D since 2026-11-22: the RESET/RUN switch (or U12 at power-on) holds SW_RST low, and the card's own
            # gates (U11) pull -RESET and, unless -PAUSE is low, -DMAIN: a boot reset on the bus, which U6B decodes to
            # clear LOADED. Nothing else drives -RESET here; U10 then holds it a little longer by itself (no boot
            # reset: -DMAIN is high again), which must leave LOADED clear
            c.forced[self.sw_rst] = ("SW1", 0)
            c.drive(TPA=1, TPB=0, MRD=1, MRW=1, A=0); c.settle(); c.drive(TPA=0); c.settle()
            c.drive(TPB=1); c.settle(); c.drive(TPB=0); c.settle()
            c.forced.pop(self.sw_rst); held = c.ext.get(c.bus.sig["-RESET"])
            c.drive(RESET=0); c.settle(); c.drive(RESET=held); c.settle()
        else:
            if self.sw_rst: c.forced[self.sw_rst] = ("SW1", 0)           # Rev D as first drawn: SW1 cleared LOADED by a line of its own
            c.drive(RESET=0, TPA=1, TPB=0, MRD=1, MRW=1, A=0); c.settle(); c.drive(TPA=0); c.settle()
            c.drive(TPB=1); c.settle(); c.drive(TPB=0); c.settle()
            if self.sw_rst: c.forced.pop(self.sw_rst); c.settle()
            c.drive(RESET=1); c.settle()
        self._snap0 = self._snapshot()

    def mode(self, reset, pause, dmain=1):
        """Rev D: -RESET, -PAUSE and -DMAIN as the other cards hold them (0 = pulled low, 1 = let go: the card's own
        gates may still pull the line, and its pull-ups set it otherwise); e.g. mode(0, 0) = LOAD, mode(0, 1, 0) = a
        boot reset from the front panel or the bus driver"""
        self.c.drive(**{"-RESET": None if reset else 0, "-PAUSE": None if pause else 0, "-DMAIN": None if dmain else 0})
        self.c.settle(); self.cache.clear()

    lines = mode                                                        # (HWMachine's name for it, on every card)

    def sw1(self, reset):
        """Rev D's RESET/RUN switch held at RESET (True) or put back to RUN"""
        if reset: self.c.forced[self.sw_rst] = ("SW1", 0)
        else: self.c.forced.pop(self.sw_rst, None)
        self.c.settle(); self.cache.clear()

    def pulls(self):
        """the open-collector lines this card itself holds low: -RESET and -DMAIN in a boot reset it makes (U11)"""
        s = self.c.bus.sig
        return {n for n in ("-RESET", "-PAUSE", "-DMAIN") if n in s and self.c.drives_low(s[n])}

    def cpu_mode(self):
        """the 1802's mode from its CLEAR and WAIT pins, as the card's gates drive them: 'run', 'reset', 'pause',
        'load' (None while either is undefined)"""
        v = self.c.val
        return {(0, 0): "load", (0, 1): "reset", (1, 0): "pause", (1, 1): "run"}.get((v.get(self.n_clear), v.get(self.n_wait)))

    def dma_request(self):
        """the 1802's DMA IN pin low: a request it would take at clock 7 of this cycle"""
        return self.c.val.get(self.n_dma) == 0

    def loaded(self):
        return len(self.flops) > 1 and self.flops[1][0].state.get(self.flops[1][1]) == 1

    def _snapshot(self):
        """every bit of sequential state: net values, latch / flip-flop contents and their last clock levels"""
        return dict(self.c.val), [{k: dict(v) if isinstance(v, dict) else v for k, v in vars(m).items()
                                   if k in ("state", "last", "clk_last")} for m in self.c.models]

    def _restore(self, snap):
        self.c.val = dict(snap[0])
        for m, attrs in zip(self.c.models, snap[1]):
            for k, v in attrs.items(): setattr(m, k, dict(v) if isinstance(v, dict) else v)

    def booted(self): return self.ff.state.get(self.ffi) == 1
    def set_booted(self, b): self.ff.state[self.ffi] = 1 if b else 0

    def _key(self): return tuple(m.state.get(i) for m, i in self.flops)

    def cycle(self, a, mrd, mrw, commit=True):
        key = (a, mrd, mrw, self._key()); hit = self.cache.get(key)
        if hit:
            res, st = hit
        else:
            # A computed cycle starts from the state right after reset, with the boot flip-flop as it is now. That is
            # exact: while the flip-flop is clear every earlier cycle had A15 low (the latch's A15 is 0, as after
            # reset); once it is set nothing can clear it but -RESET. So the result depends only on the key.
            saved = self._snapshot(); now = [m.state[i] for m, i in self.flops]
            self._restore(self._snap0)
            for (m, i), v in zip(self.flops, now): m.state[i] = v
            c = self.c
            c.drive(TPA=1, TPB=0, A=a >> 8, MRD=1, MRW=1); c.settle()
            c.drive(TPA=0); c.settle()
            c.drive(A=a & 0xFF, MRD=mrd, MRW=mrw, TPB=1); v = c.settle()
            r = self.eprom.access(v); vma = v.get(self.vma)
            res = (vma, r[1] if isinstance(r, tuple) else None, r if isinstance(r, str) else None)
            c.drive(TPB=0); c.settle()
            st = [m.state[i] for m, i in self.flops]; self.cache[key] = (res, st)
            self._restore(saved)
        if commit:
            for (m, i), v in zip(self.flops, st): m.state[i] = v
        return res

    def describe(self):
        out = ["%s card %s: %s" % (self.name, self.rev, os.path.relpath(self.nl.path, ROOT)), "  " + self.note]
        out += ["  jumper: " + e for e in self.nl.edits]
        out.append("  played by the emulator: " + "; ".join("%s = %s" % kv for kv in self.c.external.items()))
        out.append("  off the bus path (checked from the netlist, not simulated): " +
                   " ".join("%s %s" % (r, self.nl.parts[r].value) for r in self.c.unmodelled))
        out.append("  EF routing: " + ", ".join("EF%d = %s" % kv for kv in sorted(self.ef_routes().items())))
        return "\n".join(out)


class NetlistIOCard:
    """a card that answers I/O instructions, from its netlist. An INP/OUT is simulated in four phases (TPA high,
    TPA low, TPB high, TPB low) with N0-N2, -MRD/-MRW and (OUT) the data byte as the 1802 drives them; the card's
    latches carry state from one instruction to the next. Subclasses read the pins at TPB (sample)."""
    revs = {}
    name = "io"

    def __init__(self, rev, root=ROOT):
        if rev not in self.revs: raise ValueError("%s card revision %r: one of %s" % (self.name, rev, ", ".join(self.revs)))
        spec = self.revs[rev]; self.rev, self.note = rev, spec["note"]
        self.nl = Netlist(os.path.join(root, spec["net"]))
        for op, *args in spec.get("rework", []): getattr(self.nl, op)(*args)
        self.c = Circuit(self.nl, None, self.header_controls()); self.cache = {}

    def header_controls(self): return []

    def _state(self):
        from .logic import Latch
        return frozenset(self.c.val.items()), tuple(tuple(m.state.items()) for m in self.c.models if isinstance(m, Latch))

    def _restore(self, st):
        from .logic import Latch
        self.c.val = dict(st[0])
        for m, saved in zip([m for m in self.c.models if isinstance(m, Latch)], st[1]): m.state = dict(saved)

    def cycle(self, n, out, v=None):
        """an OUT n with byte v on the bus (out=True) or an INP n -> what sample() makes of the pins at TPB"""
        key = (n, out, v if out else None, self._state()); hit = self.cache.get(key)
        if hit: self._restore(hit[1]); return hit[0]
        c = self.c
        c.drive(N=n, MRD=0 if out else 1, MRW=1 if out else 0, D=v if out else None, A=0, VMA=0, TPA=1, TPB=0); c.settle()
        c.drive(TPA=0); c.settle()
        c.drive(TPB=1); res = self.sample(c.settle())
        c.drive(TPB=0); c.settle()
        c.drive(N=0, MRD=1, MRW=1); c.settle()                     # the next machine cycle: N back to 0
        self.cache[key] = (res, self._state())
        return res

    def describe(self):
        out = ["%s card %s: %s" % (self.name, self.rev, os.path.relpath(self.nl.path, ROOT)), "  " + self.note]
        out += ["  rework: " + e for e in self.nl.edits]
        if self.c.unmodelled:
            out.append("  off the bus path (checked from the netlist, not simulated): " +
                       " ".join("%s %s" % (r, self.nl.parts[r].value) for r in self.c.unmodelled))
        return "\n".join(out)


class NetlistIDECard(NetlistIOCard):
    """the IDE/CF card; the drive on its 40-pin header is machine.py's IDE (the CF image). At TPB the drive sees
    DIOW/DIOR and the register on DA0-2/CS0/CS1 (CS1 selects the control block: register 8 + DA, e.g. 0E = device
    control). sample -> (op 'w'|'r'|None, register)"""
    revs = IDE_REVS
    name = "ide"

    def __init__(self, rev="A", root=ROOT):
        super().__init__(rev, root)
        bus_d = {self.c.bus.sig["D%d" % i]: i for i in range(8)}
        self.dmap = [bus_d.get(self.ata["DD%d" % k]) for k in range(8)]     # drive bit k <-> bus bit dmap[k]
        if None in self.dmap: raise ValueError("IDE data lines DD0-7 are not all bus data lines")

    def header_controls(self):
        hdr = next(r for r, p in self.nl.parts.items() if "2X20" in p.lib)
        self.ata = {ATA_PINS[p]: net for (r, p), (net, _) in self.nl.pins.items() if r == hdr and p in ATA_PINS}
        return [self.ata[k] for k in ("DIOW", "DIOR", "DA0", "DA1", "DA2", "CS0", "CS1")]

    def sample(self, val):
        g = lambda k: val.get(self.ata[k])
        op = "w" if g("DIOW") == 0 else "r" if g("DIOR") == 0 else None
        if not op: return (None, None)
        da = [g("DA%d" % i) for i in range(3)]; cs0, cs1 = g("CS0"), g("CS1")
        if None in da or 2 in da or (cs0, cs1) not in ((0, 1), (1, 0)): return (op, "undefined")
        return (op, (8 if cs0 else 0) + sum(b << i for i, b in enumerate(da)))

    def to_drive(self, v): return sum(((v >> self.dmap[k]) & 1) << k for k in range(8))
    def to_bus(self, b): return sum(((b >> k) & 1) << self.dmap[k] for k in range(8))


class NetlistIOBoard(NetlistIOCard):
    """the IO card (1861 + keyboard). sample -> (keyboard 1852 drives the bus, 1861 DISPON, 1861 DISPOFF, faults)"""
    revs = IO_REVS
    name = "io"

    def __init__(self, rev="A", root=ROOT):
        super().__init__(rev, root)
        self.port = next(d for d in self.c.mem if d.kind == "PORT"); self.pixie = next(d for d in self.c.mem if d.kind == "PIXIE")
        sr = self.nl.net(self.port.ref, self.nl.pin_by_function(self.port.ref, "SR"))
        self.sr_on_bus = sr == self.c.bus.sig.get("-EF4")                      # SV1 2-3: the keyboard flag drives bus -EF
        bus_d = {self.c.bus.sig["D%d" % i]: i for i in range(8)}
        self.dmap = [bus_d.get(n) for n in self.port.data]                    # 1852 DO k <-> bus bit dmap[k]
        if None in self.dmap: raise ValueError("1852 DO0-7 are not all bus data lines")

    def sample(self, val):
        faults = []; k = self.port.access(val); p = self.pixie.access(val)
        if isinstance(k, str): faults.append(k); k = None
        if isinstance(p, str): faults.append(p); p = None
        return (bool(k), bool(p and p[0] == "on"), bool(p and p[0] == "off"), tuple(faults))

    def to_bus(self, b): return sum(((b >> k) & 1) << self.dmap[k] for k in range(8))


IOPANEL_REVS = {
    "A": dict(net="hardware/io-panel/kicad/rev-a/reports/netlist.net",
              note="IO panel Rev A (2026-10-30, not built; hardware/io-panel/kicad/rev-a/DESIGN.md): a 74HCT138 decodes "
                   "N0-N2, and jumpers pick the IN port (JP1), the OUT port (JP2), INPUT's EF line (JP3) and the RTC's "
                   "port pair (JP4; fitted here as set: 4, 4, -EF1, 6/7, IRQ off); OUT latches the byte in a 74HCT374 on "
                   "TPB's fall (the LEDs and two TIL311s show it); INP and this card's DMA IN put the eight toggles on the "
                   "bus through a 74HCT244 (played here: it drives exactly when its OE, from the card's gates, is low); "
                   "ELF-style RUN and LOAD on -RESET / -PAUSE; one DMA IN per INPUT press in LOAD mode (REQ, ACK, DRIVE "
                   "flip-flops; since 2026-11-22 the bus line is -DMAIN = NAND(REQ, SC0), U9B, so the request is gone as "
                   "the DMA cycle starts: the 1802 samples it at clock 7, before -MWR rises, and REQ alone made two "
                   "cycles of a press); J3, the front panel's ribbon (the displays' and LEDs' lines, the data lines "
                   "with pull-downs, INPUT, and the bus -RESET, -PAUSE, -DMAIN); a DS12885 real-time clock (rtc.py, played on the strobes the card's gates make: AS, "
                   "R/W, DS); since 2026-11-20 a 16C550 UART on the same port pair (uart.py, "
                   "played on its own pins: CS0 from the select latch U22, WR, -RD from U11B, A0-A2, MR; the byte "
                   "written to the address port picks it with bit 7 set, the DS12885 with bit 7 clear)."),
}
IOPANEL_REVS["A-req"] = dict(
    net=IOPANEL_REVS["A"]["net"], rework=[("lift", "U9", "5"), ("wire", "U9", "5", "U9", "14")],
    note="IO panel Rev A with its DMA request as it was drawn until 2026-11-22: -DMAIN = REQ alone (here: U9B's SC0 "
         "input lifted and tied high), which lasts until -MWR rises, past clock 7 of the DMA cycle, where the 1802 "
         "samples it again. Kept to show what that does: two DMA IN cycles for a press.")


def switch_contact(c, ref, a, b):
    """what closing the contact between pins a and b of switch `ref` does, read from the card's netlist. -> (net,
    level): the net the contact sets, and the level its other pin gives it: the supply that pin is on (+5V 1, ground
    0), or the supply its net is pulled to through a resistor (the front panel's data toggles reach +5V through RN2).
    c: the card's Circuit. A contact between two supplies, or with a supply on neither side, raises ValueError.
    (2026-11-23: until then each panel model set the net it knew a switch was on to the level it knew, so a switch
    wired to the wrong rail passed every test. Found by the pcb-check session, which ran the IO panel's tests on
    damaged copies of its netlist: SW12 between ground and BTN_H, in place of +5V, was not caught.)"""
    na, nb = c.nl.net(ref, a), c.nl.net(ref, b)
    for net, other in ((na, nb), (nb, na)):
        if net not in c.POWER and other in c.POWER: return net, c.POWER[other]
    for net, other in ((na, nb), (nb, na)):
        if net not in c.POWER and net not in c.pulls and other in c.pulls: return net, c.pulls[other]
    raise ValueError("switch %s: its contact between pins %s and %s joins %s and %s, which is no supply against a "
                     "signal: a wiring fault, or a switch this model cannot play" % (ref, a, b, na, nb))


class NetlistIOPanel:
    """the IO panel card from its netlist. The hand controls are held on the card: toggles (byte), INPUT (pressed), RUN
    and LOAD; out() / inp() run an OUT n / INP n through the card's gates; dma_in() runs the DMA IN cycle of LOAD mode."""
    name = "panel"

    EFROWS = ("-EF1", "-EF2", "-EF3", "-EF")                 # JP3's rows

    def __init__(self, rev="A", root=ROOT, in_port=4, out_port=4, ef="-EF1", rtc_ports=6, rtc_int=False, rtc=None,
                 uart_int=False, uart=None, toggles=True):
        """the jumpers as set on the card (Ken, 2026-11-17/18): in_port / out_port 1-7 (JP1 / JP2; None = no jumper),
        ef = INPUT's bus line (JP3), rtc_ports = the RTC's address port 2, 4 or 6 (JP4: data on the next; the UART's
        too), rtc_int = its IRQ on -INT (JP4's last row), uart_int = the UART's INTR on -INT (JP7). rtc: a DS12885
        (rtc.py) to play the clock; None = a new one at the host's time. uart: a UART16550 (uart.py); None = a new one.
        toggles: the card's own data toggles SW1-SW8 are fitted (False: a card built for the front panel, whose toggles
        reach the data lines through the ribbon)"""
        if rev not in IOPANEL_REVS: raise ValueError("IO panel revision %r: one of %s" % (rev, ", ".join(IOPANEL_REVS)))
        spec = IOPANEL_REVS[rev]; self.rev, self.note = rev, spec["note"]
        self.nl = Netlist(os.path.join(root, spec["net"]))
        for op, *args in spec.get("rework", []): getattr(self.nl, op)(*args)
        int_pin = next(pin for (r, pin), (n, _) in self.nl.pins.items() if r == "J1" and n.split("/")[-1] == "-INT")
        fit = lambda ref, row: self.nl.jumper(ref, str(2 * row - 1), ref, str(2 * row))       # a jumper across row n
        if in_port: fit("JP1", in_port)
        if out_port: fit("JP2", out_port)
        if ef: fit("JP3", self.EFROWS.index(ef) + 1)
        if rtc_ports:
            k = {2: 1, 4: 2, 6: 3}[rtc_ports]; fit("JP4", k); fit("JP4", k + 3)                 # A2/A4/A6, D3/D5/D7
        if rtc_int: fit("JP4", 7)
        self.has_uart = "U20" in self.nl.parts               # the serial port (2026-11-20)
        if uart_int and self.has_uart: self.nl.jumper("JP7", "2", "JP7", "1")
        self.int_net = self.nl.net("J1", int_pin)            # the bus -INT, whatever a fitted jumper has joined it to
        self.ports = dict(in_port=in_port, out_port=out_port, ef=ef, rtc_ports=rtc_ports, rtc_int=rtc_int, uart_int=uart_int)
        self.rtc = rtc if rtc is not None else DS12885(start=datetime.datetime.now())
        self.uart = uart if uart is not None else UART16550()
        self.c = Circuit(self.nl, None)
        net = lambda name: next(n for n in self.nl.nets if n.split("/")[-1] == name)
        self.out_nets = [net("OUT%d" % k) for k in range(8)]; self.sw_nets = [net("SW%d" % k) for k in range(8)]
        self.oe244, self.button, self.req = net("OE244_L"), net("INPUT_RC"), net("REQ")
        self.rtc_as, self.rtc_wr, self.rtc_rd = net("RTC_AS"), net("RTC_WR_L"), net("RTC_RD_L")
        self.adr_nets = [net("ADR%d" % k) for k in range(16)]   # the address display's latches (U18 high, U19 low)
        self.rtc_cs = self.nl.net("U13", "13")              # the DS12885's CS: GND, or the select latch's bit 7 (the UART's card)
        if self.has_uart:                                   # the 16C550's own pins: CS0, WR, -RD, A0-A2, MR, INTR
            u = lambda pin: self.nl.net("U20", pin)
            self.u_cs0, self.u_wr, self.u_rd, self.u_mr, self.u_int = u("12"), u("19"), u("21"), u("35"), u("30")
            self.u_a = [u("28"), u("27"), u("26")]
        self.sig = self.c.bus.sig
        self.switches, self.pressed, self.run_on, self.load_on = 0, False, True, False
        self.sw_fitted, self.remote_sw, self.remote_input = toggles, 0, False     # the front panel's, through the ribbon
        self.reset_pressed = False                          # the card's own RESET button, SW12 (2026-11-23)
        self.btn_h = next((n for n in self.nl.nets if n.split("/")[-1] == "BTN_H"), None)
        # each hand control's contact as the netlist has it wired (switch_contact): the net it sets, and to what
        sw = lambda ref, a, b: switch_contact(self.c, ref, a, b)
        self.k_bits = [(sw("SW%d" % (k + 1), 2, 3), sw("SW%d" % (k + 1), 2, 1)) for k in range(8)]   # a data toggle at 0, at 1
        self.k_input, self.k_reset_sw, self.k_load = sw("SW9", 1, 2), sw("SW10", 1, 2), sw("SW11", 1, 2)   # INPUT; RUN off; LOAD on
        self.k_boot = sw("SW12", 1, 2) if "SW12" in self.nl.parts else None                  # the RESET button
        self._switched = ({net for pair in self.k_bits for net, _ in pair} | set(self.sw_nets) | {self.button} |
                          {k[0] for k in (self.k_input, self.k_reset_sw, self.k_load, self.k_boot) if k})
        self.load_h = next((n for n in self.nl.nets if n.split("/")[-1] == "LOAD_H"), None)
        # what J3 sends to the front panel: the displays' and bit LEDs' lines, and the two LED sinks
        names = ["ADR%d" % k for k in range(16)] + ["OUT%d" % k for k in range(8)] + ["LED_Q_K", "ROM_LED_L"]
        self.ribbon_out = {n: x for n in names for x in self.nl.nets if x.split("/")[-1] == n}
        self.latch = None                                   # the '374 powers up undefined
        self.c.drive(SC0=1, VMA=0, Q=0)                     # the 1802 not in a fetch or DMA cycle; the EPROM off; Q low
        self._apply(); self._idle(); self._uart_int()       # (the UART holds its INTR pin low from the start)

    # ---- the hand controls, as the card's nets see them
    def _apply(self):
        """each closed contact sets its net to the level its other pin gives it, both as the netlist has the switch
        wired (switch_contact); an open contact sets nothing, and the card's resistors then say what the net is"""
        want = {}
        def close(contact, who): want[contact[0]] = (who, contact[1])
        for k in range(8):
            if self.sw_fitted: close(self.k_bits[k][(self.switches >> k) & 1], "SW%d" % (k + 1))   # SPDT: driven both ways
            elif (self.remote_sw >> k) & 1: want[self.sw_nets[k]] = ("J3", 1)                    # the front panel's toggle, through 1k
        if self.pressed: close(self.k_input, "SW9")        # (released: R9 pulls the line up)
        elif self.remote_input: want[self.button] = ("J3", 0)                                    # the front panel's INPUT button
        if self.reset_pressed: close(self.k_boot, "SW12")  # RESET: +5V on BTN_H (R4 holds it low otherwise)
        # RUN and LOAD are toggles on the bus lines themselves: what this card pulls, apart from what the other cards
        # do (lines()). Let go, a line has no pull-up on this card: the gates read it as high
        if not self.run_on: close(self.k_reset_sw, "SW10")
        if self.load_on: close(self.k_load, "SW11")
        f = self.c.forced
        for n in self._switched - set(want): f.pop(n, None)
        f.update(want)

    def lines(self, reset=1, pause=1, dmain=1):
        """-RESET, -PAUSE and -DMAIN as the other cards hold them (0 = pulled low, 1 = let go)"""
        self.c.drive(**{"-RESET": None if reset else 0, "-PAUSE": None if pause else 0, "-DMAIN": None if dmain else 0})
        self.c.settle()

    def pulls(self):
        """the open-collector lines this card itself holds low: its RUN and LOAD toggles, its DMA request, and its
        RESET button's boot reset (-RESET and -DMAIN together, unless -PAUSE is low)"""
        return {n for n in ("-RESET", "-PAUSE", "-DMAIN") if self.c.drives_low(self.sig[n])}

    def remote(self, switches, pressed):
        """the front panel's data toggles and INPUT button, as they reach this card through the ribbon (J3)"""
        self.remote_sw, self.remote_input = switches & 0xFF, bool(pressed); self._apply(); self.c.settle()

    def sw_byte(self):
        """the byte on the data lines SW0-SW7, as the '244 sees it: this card's toggles, or the front panel's"""
        return sum(1 << k for k, n in enumerate(self.sw_nets) if self.c.val.get(n) == 1)

    def _idle(self):
        """a bus cycle with nothing for this card: N = 0, -MRD low (a fetch), TPA/TPB pulsed"""
        c = self.c; c.drive(N=0, MRD=0, MRW=1, TPA=1, TPB=0); c.settle(); c.drive(TPA=0); c.settle()
        c.drive(TPB=1); c.settle(); c.drive(TPB=0); c.settle()

    def set(self, switches=None, pressed=None, run=None, load=None, reset=None):
        """the card's hand controls; reset: its own RESET button (SW12), a boot reset through U23's two gates"""
        if switches is not None: self.switches = switches & 0xFF
        if pressed is not None: self.pressed = pressed
        if run is not None: self.run_on = run
        if load is not None: self.load_on = load
        if reset is not None:
            if reset and not self.btn_h: raise ValueError("IO panel %s has no RESET button" % self.rev)
            self.reset_pressed = bool(reset)
        self._apply(); self.c.settle()
        if self.has_uart and self.c.val.get(self.u_mr) == 1: self.uart.reset(); self._uart_int()   # MR = RESET_H

    # ---- the serial port (2026-11-20)
    def _uart_int(self):
        """the 16C550's INTR pin as the UART model has it now, onto its net (U9 inverts it; JP7 puts it on -INT)"""
        if self.has_uart: self.c.forced[self.u_int] = ("U20", 1 if self.uart.intr() else 0); self.c.settle()

    def serial_in(self, data):
        """characters arriving at J2 from the terminal"""
        self.uart.receive(data); self._uart_int()

    def serial_out(self):
        """what the card has sent out of J2 since the last call"""
        return self.uart.sent()

    def int_low(self): return self.c.val.get(self.int_net) == 0         # the bus -INT pulled low by this card

    def ef(self, line): return self.c.val.get(self.sig[line]) == 0     # a bus EF line pulled low (open collector)
    def ef1(self): return self.ef("-EF1")
    def dmain(self): return self.c.val.get(self.sig["-DMAIN"]) == 0
    def load_mode(self):
        """LOAD mode on the bus (-RESET and -PAUSE low), whichever card made it: the card's own LOAD_H"""
        if self.load_h is None: return not self.run_on and self.load_on
        return self.c.val.get(self.load_h) == 1

    def _io(self, n, out, v=None):
        """one INP / OUT cycle through the card's gates, in the order the 1802 makes it (data sheet, figures 10 and 11):
        N from the start of the cycle with -MRD still high (clock 0 to 1.5, in an OUT as in an INP); then -MRD low in
        an OUT; in an INP -MWR low (clock 5), TPB (6.5), -MWR high (7), TPB low (7.5); N and -MRD off at the end.
        -> {'drive': the '244 on the bus at TPB, 'as' / 'wr': the RTC's AS / R/W (at TPB, after it), 'rd': its DS at
        TPB, 'rd_early': its DS in the first phase (low = a read strobe before the cycle is known to be an OUT),
        'uwr': the UART's WR (at TPB, after it), 'urd': its -RD at TPB, 'urd_low': the phases in which its -RD was
        low, 'usel' / 'ureg': the UART selected (its CS0) and its register (A2-A0) at TPB, 'rtc_sel': the DS12885's CS
        low at TPB}"""
        c = self.c; seen = {}
        c.drive(N=n, MRD=1, MRW=1, D=None, TPA=1, TPB=0); seen["early"] = dict(c.settle())
        c.drive(MRD=0 if out else 1, D=v if out else None); c.settle(); c.drive(TPA=0); seen["mid"] = dict(c.settle())
        if not out: c.drive(MRW=0); seen["mwr"] = dict(c.settle())
        c.drive(TPB=1); at = seen["tpb"] = dict(c.settle())
        if not out: c.drive(MRW=1); c.settle()
        c.drive(TPB=0); after = seen["after"] = dict(c.settle()); c.drive(N=0, MRD=1, MRW=1, D=None); seen["end"] = dict(c.settle())
        s = {"drive": at.get(self.oe244) == 0, "as": (at.get(self.rtc_as), after.get(self.rtc_as)),
             "wr": (at.get(self.rtc_wr), after.get(self.rtc_wr)), "rd": at.get(self.rtc_rd),
             "rd_early": seen["early"].get(self.rtc_rd), "rtc_sel": at.get(self.rtc_cs) == 0}
        if self.has_uart:
            a = [at.get(x) for x in self.u_a]
            s.update(uwr=(at.get(self.u_wr), after.get(self.u_wr)), urd=at.get(self.u_rd),
                     urd_low=[ph for ph, val in seen.items() if val.get(self.u_rd) == 0],
                     usel=at.get(self.u_cs0) == 1, ureg=None if None in a or X in a else a[0] | a[1] << 1 | a[2] << 2)
        return s

    def out(self, n, v):
        """an OUT n with byte v from memory: -> (True if the '244 drove the bus (it must not), the byte the LEDs /
        TIL311s show). The RTC latches v as its register number on AS's fall (whatever its CS), or writes it on R/W's
        rise while its CS is low; the UART writes its register as its WR falls while its CS0 is high."""
        s = self._io(n, True, v)
        q = [self.c.val.get(x) for x in self.out_nets]
        if None not in q and X not in q: self.latch = sum(b << k for k, b in enumerate(q))
        if s["as"] == (1, 0): self.rtc.write_addr(v)
        if s["wr"] == (0, 1) and s["rtc_sel"]: self.rtc.write_data(v)
        if self.has_uart:
            if s["urd_low"] and s["usel"]: self.uart.read(s["ureg"] or 0)       # a read strobe in an OUT: it must not be
            if s["uwr"] == (1, 0) and s["usel"] and s["ureg"] is not None: self.uart.write(s["ureg"], v)
            self._uart_int()
        return s["drive"], self.latch

    def inp(self, n):
        """an INP n: -> the byte this card put on the bus (the toggles through the '244, or the RTC's register while
        its DS is low; both at once is a fight: their AND, as the bus would settle), None if it drove nothing"""
        s = self._io(n, False); bytes_ = []
        if s["drive"]: bytes_.append(self.sw_byte())
        if s["rd"] == 0 and s["rtc_sel"]: bytes_.append(self.rtc.read_data())
        if self.has_uart and s["urd"] == 0 and s["usel"] and s["ureg"] is not None:
            bytes_.append(self.uart.read(s["ureg"])); self._uart_int()
        if not bytes_: return None
        v = 0xFF
        for b in bytes_: v &= b
        return v

    def strobes(self, n, out):
        """the RTC's strobes in one cycle, for tests: (AS pulsed, R/W pulsed, DS low)"""
        s = self._io(n, out, 0 if out else None)
        return s["as"] == (1, 0), s["wr"] == (0, 1), s["rd"] == 0

    def s2_begin(self, a=None):
        """a DMA IN cycle (S2) as the 1802 runs it (data sheet, figures 4 and 12), up to the point where the 1802
        samples its DMA request again, clock 7: SC0 low and -MRD high from the start, TPA, -MWR low at clock 5, TPB
        high at 6.5. Whether the request still stands then decides what follows: another DMA cycle, or IDLE.
        a: the address the byte goes to, R(0), for the address display (the high byte on A0-A7 during TPA)"""
        c = self.c
        if a is not None: c.drive(A=a >> 8)
        c.drive(SC0=0, N=0, MRD=1, MRW=1, TPA=1, TPB=0); c.settle(); c.drive(TPA=0); c.settle()
        if a is not None: c.drive(A=a & 0xFF); c.settle()
        c.drive(MRW=0); self._during = c.settle().get(self.oe244) == 0
        c.drive(TPB=1); c.settle()

    def s2_end(self, again=False):
        """the rest of the cycle: -MWR high at clock 7 (the write ends), TPB low; then, unless another DMA cycle
        follows (again), the next IDLE: SC0 high, -MRD low. -> the byte the card had on the bus through the write
        and past it, None if it did not drive"""
        c = self.c
        c.drive(MRW=1); held = c.settle().get(self.oe244) == 0                                # past the write: still on?
        b = self.sw_byte() if self._during and held else None
        c.drive(TPB=0); c.settle()
        if not again: c.drive(SC0=1); c.settle(); c.drive(MRD=0); c.settle()
        return b

    def dma_in(self, limit=4):
        """LOAD mode, the card by itself: the DMA IN cycles its request makes, the request being what the bus line
        -DMAIN shows at clock 7 of each cycle (no CPU card between). -> the bytes it put on the bus, one for each
        cycle: [] with no request, one byte for a press as the card is drawn; two would be the same byte loaded
        twice (the card as drawn until 2026-11-22: its request lasted until -MWR rose)"""
        out = []; again = self.dmain()                      # the request at clock 7 of an IDLE cycle
        while again and len(out) < limit:                   # (once sampled, the cycle follows whatever the line does next)
            self.s2_begin(); again = self.dmain(); out.append(self.s2_end(again))
        return out

    def cycle(self, a, n=0, read=True, tpa=True):
        """one machine cycle putting address a on the bus as the 1802 does: the high byte on A0-A7 while TPA is high,
        then the low byte until TPB has fallen. -> the address the four TIL311s show (address()). tpa=False: an IDLE
        cycle of LOAD mode, where the 1802 leaves TPA out (data sheet: "TPA is suppressed in IDLE when the CPU is in
        the load mode"), so the high byte's latch keeps what it had"""
        c = self.c
        c.drive(N=n, MRD=0 if read else 1, MRW=1, A=a >> 8, TPA=1 if tpa else 0, TPB=0); c.settle(); c.drive(TPA=0); c.settle()
        c.drive(A=a & 0xFF); c.settle(); c.drive(TPB=1); c.settle(); c.drive(TPB=0); c.settle()
        return self.address()

    def address(self):
        """the 16-bit address on the four TIL311s (Ken, 2026-11-18): U18's outputs (latched at TPA) and U19's (at TPB),
        as the displays' inputs see them; None while any bit is undefined (both latches power up so)"""
        q = [self.c.val.get(x) for x in self.adr_nets]
        return None if None in q or X in q else sum(b << k for k, b in enumerate(q))

    def leds(self):
        a = self.address(); addr = "ADDR ????" if a is None else "ADDR %04X" % a
        if self.latch is None: return "%s  LEDs ????????  TIL311 ??" % addr
        return "%s  LEDs %s  TIL311 %02X" % (addr, "".join("*" if self.latch >> k & 1 else "." for k in range(7, -1, -1)), self.latch)

    def describe(self):
        return "IO panel %s: %s\n  %s" % (self.rev, os.path.relpath(self.nl.path, ROOT), self.note)


FRONTPANEL_REVS = {
    "A": dict(net="hardware/front-panel/kicad/rev-a/reports/netlist.net",
              note="Front panel Rev A (2026-11-22, not built; hardware/front-panel/kicad/rev-a/DESIGN.md): the hand "
                   "controls and displays on a board that mounts as the front of a case, on a 50-way ribbon from the IO "
                   "panel card's J3 (pin n to pin n; tools/s5panel.py). Six TIL311s and eight LEDs show what the IO "
                   "card sends (the bus address, its output port); the data toggles switch the IO card's data lines to "
                   "+5V through 1k; RUN and LOAD pull the bus -RESET and -PAUSE; INPUT is the IO card's button. RESET "
                   "pulls -RESET and -DMAIN together through a 74HC03, unless -PAUSE is low: a boot reset. Six status "
                   "LEDs: PWR, Q, PAUSE, RESET, ROM, and START FROM RAM, a copy of the CPU card's LOADED flag made "
                   "from the same three bus lines by the same two gates."),
}


class NetlistFrontPanel:
    """the front panel from its netlist. Its "bus" is J1, the ribbon's header: lines() and show() set what the IO panel
    card and the bus put on it, pulls() says which of -RESET, -PAUSE and -DMAIN the panel itself holds low. The hand
    controls are held here: toggles (byte), INPUT and RESET (pressed), RUN and LOAD."""
    name = "front"
    STATUS = (("PWR", None), ("Q", "Q_LED_L"), ("PAUSE", "PAUSE_N"), ("RESET", "RESET_N"), ("ROM", "ROM_LED_L"),
              ("RAM", "LED_RAM_K"))                           # each LED and the line that sinks it (PWR: ground)

    def __init__(self, rev="A", root=ROOT):
        if rev not in FRONTPANEL_REVS: raise ValueError("front panel revision %r: one of %s" % (rev, ", ".join(FRONTPANEL_REVS)))
        spec = FRONTPANEL_REVS[rev]; self.rev, self.note = rev, spec["note"]
        self.nl = Netlist(os.path.join(root, spec["net"]))
        for op, *args in spec.get("rework", []): getattr(self.nl, op)(*args)
        self.c = Circuit(self.nl, None, bus="J1"); self.sig = self.c.bus.sig
        net = lambda name: next(n for n in self.nl.nets if n.split("/")[-1] == name)
        self.sw_nets = [net("SW%d" % k) for k in range(8)]; self.input_net, self.btn_net = net("INPUT_L"), net("BTN_RC")
        self.adr_nets = [net("ADR%d" % k) for k in range(16)]; self.out_nets = [net("OUT%d" % k) for k in range(8)]
        self.sinks = {label: net(n) for label, n in self.STATUS if n}
        self.switches, self.pressed, self.run_on, self.load_on, self.reset_pressed = 0, False, True, False, False
        # each hand control's contact as the netlist has it wired (switch_contact): the net it sets, and to what.
        # Read before the bus's pull-ups are added below: those are not this board's resistors
        sw = lambda ref: switch_contact(self.c, ref, 1, 2)
        self.k_bits = [sw("SW%d" % (k + 1)) for k in range(8)]         # a data toggle, on: its line to +5V through RN2
        self.k_reset_sw, self.k_load, self.k_input, self.k_boot = sw("SW9"), sw("SW10"), sw("SW11"), sw("SW12")
        self._switched = {k[0] for k in self.k_bits + [self.k_reset_sw, self.k_load, self.k_input, self.k_boot]}
        for n in ("-RESET", "-PAUSE", "-DMAIN"): self.c.pulls[self.sig[n]] = 1   # the bus's pull-ups, through the ribbon
        self._apply(); self.c.settle()

    def _apply(self):
        """each closed contact sets its net to the level its other pin gives it, both as the netlist has the switch
        wired (switch_contact). A data toggle that is off leaves its line open (the IO card's RN3 pulls it down);
        BTN_RC, let go, is pulled up by R7"""
        want = {}
        for k, contact in enumerate(self.k_bits):
            if (self.switches >> k) & 1: want[contact[0]] = ("SW%d" % (k + 1), contact[1])
        for contact, closed, who in ((self.k_reset_sw, not self.run_on, "SW9"), (self.k_load, self.load_on, "SW10"),
                                     (self.k_input, self.pressed, "SW11"), (self.k_boot, self.reset_pressed, "SW12")):
            if closed: want[contact[0]] = (who, contact[1])
        f = self.c.forced
        for n in self._switched - set(want): f.pop(n, None)
        f.update(want)

    def ribbon_in(self):
        """what the panel's own nets put on the ribbon's switch lines: (the byte of the data lines SW7-SW0 its toggles
        hold high, True while its INPUT line is held low). The IO panel card takes these, not the positions of the
        controls: a toggle or a button wired to the wrong place then shows as it would on the bench"""
        return (sum(1 << k for k, n in enumerate(self.sw_nets) if self.c.val.get(n) == 1),
                self.c.drives_low(self.input_net))

    def set(self, switches=None, pressed=None, run=None, load=None, reset=None):
        if switches is not None: self.switches = switches & 0xFF
        if pressed is not None: self.pressed = pressed
        if run is not None: self.run_on = run
        if load is not None: self.load_on = load
        if reset is not None: self.reset_pressed = reset
        self._apply(); self.c.settle()

    def lines(self, reset=1, pause=1, dmain=1):
        """-RESET, -PAUSE and -DMAIN as the other cards hold them (0 = pulled low, 1 = let go: the bus's pull-ups,
        unless the panel pulls the line itself)"""
        self.c.drive(**{"-RESET": None if reset else 0, "-PAUSE": None if pause else 0, "-DMAIN": None if dmain else 0})
        self.c.settle()

    def pulls(self):
        """the open-collector lines the panel itself holds low: RUN off, LOAD on, the RESET button's two gates"""
        return {n for n in ("-RESET", "-PAUSE", "-DMAIN") if self.c.drives_low(self.sig[n])}

    def show(self, values):
        """{name: level} from the IO panel card's J3: ADR15-ADR0, OUT7-OUT0, LED_Q_K (here Q_LED_L), ROM_LED_L"""
        d = {{"LED_Q_K": "Q_LED_L"}.get(k, k): (None if v == X else v) for k, v in values.items()}
        self.c.drive(**{k: v for k, v in d.items() if k in self.sig}); self.c.settle()

    def _hex(self, nets):
        q = [self.c.val.get(n) for n in nets]
        return None if None in q or X in q else sum(b << k for k, b in enumerate(q))

    def address(self): return self._hex(self.adr_nets)       # what the four address TIL311s show
    def data(self): return self._hex(self.out_nets)          # the two data TIL311s and the eight bit LEDs

    def leds(self):
        """{'PWR', 'Q', 'PAUSE', 'RESET', 'ROM', 'RAM'}: True = lit (its sink line low)"""
        return {label: True if label == "PWR" else self.c.val.get(self.sinks[label]) == 0 for label, _ in self.STATUS}

    def text(self):
        a, d, s = self.address(), self.data(), self.leds()
        return "ADDR %s  DATA %s  %s   toggles %s (%02X)  INPUT %s  RUN %s  LOAD %s  RESET %s" % (
            "????" if a is None else "%04X" % a, "??" if d is None else "%02X" % d,
            " ".join("%s%s" % ("START FROM RAM" if k == "RAM" else k, "*" if v else ".") for k, v in s.items()),
            "".join("1" if self.switches >> k & 1 else "0" for k in range(7, -1, -1)), self.switches,
            "down" if self.pressed else "up", "on" if self.run_on else "off", "on" if self.load_on else "off",
            "down" if self.reset_pressed else "up")

    def describe(self):
        return "front panel %s: %s\n  %s" % (self.rev, os.path.relpath(self.nl.path, ROOT), self.note)


class _NetlistROM(CPUCardROM):
    """the CPU card's EPROM when the card runs from its netlist: `remap` (machine.py's 'still in the boot map') is the
    boot flip-flop itself"""
    @property
    def remap(self):
        return not self.card.booted() if "card" in self.__dict__ else self.__dict__.get("_remap", True)

    @remap.setter
    def remap(self, v):
        if "card" in self.__dict__: self.card.set_booted(not v)
        else: self.__dict__["_remap"] = v


class BusLog:
    """contention and other bus events, grouped by (kind, who, 4K block)"""
    def __init__(self): self.events = {}

    def add(self, kind, names, a, detail, pc):
        key = (kind, tuple(names), a >> 12); e = self.events.get(key)
        if e: e[0] += 1
        else: self.events[key] = [1, pc, a, detail]
        return e is None

    def clear(self): self.events.clear()

    def text(self):
        if not self.events: return "no bus events"
        out = []
        for (kind, names, blk), (n, pc, a, detail) in sorted(self.events.items(), key=lambda kv: (kv[0][0], kv[0][2])):
            out.append("%-11s %-26s %X000-%XFFF  x%-7d first: R(P)=%04X addr %04X  %s" % (kind, " + ".join(names), blk, blk, n, pc, a, detail))
        return "\n".join(out)


class HWMachine(Machine):
    """Machine with the bus modelled; see the module notes. vma_mode: remap (Boot/REMAP), boot (Boot only), norom.
    video_rev: a VIDEO_REVS key for the 6845 card from its netlist, or None for machine.py's behavioural model.
    videog: fit VIDEO-G in place of the 6845 card and the IO card (video_rev and io_rev are then not looked at): a
    hwvideog.VIDEOG_REVS key ('1.0') for TEXT and GFX from their netlists, or 'none' for the behavioural model
    (videog.VideoG) on the modelled bus. monitor ('ntsc' / 'mda'), gfx (False = TEXT alone, the ribbon unplugged),
    videog_block (SV1) and kbd_flag (JP3: the bus line KEY-READY pulls low, '-EF', '-EF1', '-EF2', '-EF3' or None) are
    the card's jumpers; mhz is the 1802's clock, which the behavioural 6845's VSYNC and DE are counted from."""
    VMA_MODES = ("remap", "boot", "norom")

    LINES = ("-RESET", "-PAUSE", "-DMAIN")                               # the open-collector lines the cards share

    def __init__(self, mem_rev="D", vma_mode="remap", cpu_rev="A-built", video_rev="B", ide_rev="A", io_rev="A", jumpers=None,
                 rom_lo=None, rom_hi=None, panel_rev=None, videog=None, monitor="ntsc", gfx=True, videog_block=7,
                 kbd_flag="-EF", mhz=1.76, front_rev=None, panel_toggles=None, **kw):
        """front_rev: fit the front panel (a FRONTPANEL_REVS key) on the IO panel card's ribbon; it needs panel_rev.
        panel_toggles: the IO panel card's own data toggles are fitted (None: yes, unless a front panel is)"""
        if vma_mode not in self.VMA_MODES: raise ValueError("vma mode: one of " + ", ".join(self.VMA_MODES))
        if videog: kw["pixie_port"] = 0; video_rev = io_rev = None       # no 6845 card and no IO card (no 1861)
        elif video_rev and VIDEO_REVS.get(video_rev, {}).get("keyboard"):
            kw["pixie_port"] = 0; io_rev = None                          # the keyboard is on the video card: no IO card
        super().__init__(**kw)
        self.memory = NetlistMemoryCard(mem_rev, jumpers); self.vma_mode = vma_mode
        self.ccard = NetlistCPUCard(self.cpurom, cpu_rev, vma_mode) if cpu_rev else None
        if self.ccard:
            loaded = self.cpurom.loaded; self.cpurom.__class__ = _NetlistROM; self.cpurom.__dict__.pop("remap", None)
            self.cpurom.card = self.ccard; self.ccard.reset()
            if not loaded: self.ccard.set_booted(True)                # no EPROM fitted: nothing to boot from
        self.vcard = NetlistVideoCard(self.video, video_rev) if video_rev else None
        if video_rev and VIDEO_REVS.get(video_rev, {}).get("keyboard"):  # the 6845 card with the keyboard on it: the key is
            self.kbd.port = None                                         # read at x802, not on INP 1
            self.vcard = NetlistVideoKbdCard(self.video, self.kbd, video_rev, kbd_flag)
        self.cards = [self.memory] + ([self.vcard] if self.vcard else [])
        self.vg = None; self.video_name = "6845"                         # (the behavioural video's name in the bus log)
        if videog:
            from .videog import VideoG
            self.kbd.port = None                                         # the key is read at x802, not on INP 1
            self.video = VideoG(self, monitor, gfx, mhz); self.video_name = "video-g"
            if str(videog).lower() != "none":
                from .hwvideog import NetlistVideoG
                self.vg = NetlistVideoG(self.video, str(videog), block=videog_block, kbd_flag=kbd_flag)
        self.icard = NetlistIDECard(ide_rev) if ide_rev else None
        self.iocard = NetlistIOBoard(io_rev) if io_rev else None
        if front_rev and not panel_rev: raise ValueError("the front panel hangs on the IO panel card's ribbon: fit that card too")
        if panel_toggles is None: panel_toggles = not front_rev
        self.panel = NetlistIOPanel(panel_rev, toggles=panel_toggles) if panel_rev else None   # the IO panel card (port 4, -EF1, RUN/LOAD)
        self.front = NetlistFrontPanel(front_rev) if front_rev else None # the front panel, on that card's J3
        self.held = False                                                # -RESET or -PAUSE low: the 1802 is not running
        self.run_mode = "run"; self.ext_pull = {}                        # {who: lines it holds low}: cards with no netlist here
        self.bus_lines = {n: 1 for n in self.LINES}
        if self.panel or self.front: self.lines_update()
        self.log = BusLog(); self.stop_on = set(); self.fault = None
        for path in (rom_lo, rom_hi):
            if path: self.load_rom(path)

    def describe(self):
        vg = self.video_name == "video-g"
        return "\n".join([c.describe() for c in [self.ccard] + self.cards + [self.vg, self.icard, self.iocard, self.panel, self.front] if c] +
                         (["VIDEO-G: behavioural (videog.py) on the modelled bus"] if vg and not self.vg else []) +
                         ([] if self.vcard or vg else ["6845 card: behavioural (machine.py)"]) +
                         ([] if self.icard else ["IDE card: behavioural (machine.py)"]) +
                         (["no IO card (VIDEO-G has the keyboard; no 1861)"] if vg else
                          ["no IO card (the 6845 card has the keyboard; no 1861)"] if isinstance(self.vcard, NetlistVideoKbdCard) else
                          [] if self.iocard else ["IO card: behavioural (machine.py)"]) +
                         ([] if self.ccard else ["CPU card: -VMA and the boot EPROM behavioural (hardware/cpu/eagle/rev-a/ops.html)"]))

    # ------------------------------------------------------------------ the CPU card
    def cpu_card(self, a, mrd=0, mrw=1, commit=False):
        """-> (-VMA level, CPU EPROM byte or None) for an access to a; commit = let the boot flip-flop change"""
        if self.ccard:
            vma, ea, fault = self.ccard.cycle(a, mrd, mrw, commit)
            if fault and commit: self._event("undefined", ["cpu"], a, fault)
            return vma, (None if ea is None or not self.cpurom.loaded else self.cpurom.data[ea & 0xFFF])
        vma, rom = self._cpu_behavioural(a)
        return vma, (self.cpurom.data[a & 0xFFF] if rom else None)

    def _cpu_behavioural(self, a):
        if self.vma_mode == "norom" or not self.cpurom.loaded: return 0, False
        if self.cpurom.remap: return 1, True               # flip-flop still reset: boot map
        if self.vma_mode == "boot": return 0, False
        return (1, True) if (a >> 12) == (self.cpurom.base >> 12) else (0, False)

    def _flipflop(self, a):
        if not self.ccard and a & 0x8000: self.cpurom.remap = False

    # ------------------------------------------------------------------ bus
    def _event(self, kind, names, a, detail):
        pc = self.cpu.R[self.cpu.P]
        self.log.add(kind, names, a, detail, pc)
        if kind in self.stop_on and self.fault is None:
            self.fault = "%s %s at %04X: %s" % (kind, " + ".join(names), a, detail)

    def _drivers(self, a, log):
        vma, rom = self.cpu_card(a, 0, 1, commit=log); drv = []; faults = []
        if rom is not None: drv.append(("CPU EPROM", rom))
        if self.vg:                                                      # VIDEO-G from its netlists (hwvideog.py): a
            d, f = self.vg.bus_read(a, vma, log); drv += d; faults += f  # look (log off) clears no READY flip-flop
        elif not self.vcard:
            v = self.video.read(a)
            if v is not None: drv.append((self.video_name, v))
        for card in self.cards:
            d, f = card.bus_read(a, vma, log) if isinstance(card, NetlistVideoKbdCard) else card.bus_read(a, vma)
            drv += d; faults += f                                        # (a look, log off, clears no KEY-READY)
        if log:
            for f in faults: self._event("undefined", ["bus"], a, f)
        return vma, drv

    def _read(self, a, log):
        vma, drv = self._drivers(a, log)
        if log and len(drv) > 1:
            names = [n for n, _ in drv]; detail = " ".join("%s=%02X" % d for d in drv)
            self._event("fight" if len({b for _, b in drv}) > 1 else "double", names, a, detail)
        if not drv: return FLOAT
        r = 0xFF
        for _, b in drv: r &= b
        return r

    def peek(self, a): return self._read(a, False)

    def read(self, a):
        v = self._read(a, True); self._flipflop(a)
        if self.watch: self.watch("r", a, v)
        return v

    def fetch(self, a):
        v = self._read(a, True); self._flipflop(a); return v

    def write(self, a, v):
        if self.watch: self.watch("w", a, v)
        vma, _ = self.cpu_card(a, 1, 0, commit=True); got = []
        if self.vg:
            g, faults = self.vg.bus_write(a, vma, v); got += g
            for f in faults: self._event("undefined", ["video-g"], a, f)
        elif not self.vcard and self.video.write(a, v): got.append(self.video_name)
        for card in self.cards:
            g, faults = card.bus_write(a, vma, v); got += g
            for f in faults: self._event("undefined", ["bus"], a, f)
        if len(got) > 1: self._event("multi-write", got, a, "%02X lands in %d places" % (v, len(got)))
        self._flipflop(a)

    def load_rom(self, path, base=0x8000):
        from .machine import load_image
        img = load_image(path, base); n = sum(self.memory.program(a, b) for a, b in img.items())
        return n

    def bus_map(self):
        """which drivers answer a read at each 4K block (and its upper half, where the 6845 card splits; with VIDEO-G,
        each register pair and the window too), right now"""
        out = []; block = self.vg.block if self.vg else 7
        split = (0x800, 0x802, 0x804, 0x806, 0xC00) if self.vg else (0x800, 0xC00) if self.video_name == "video-g" else (0x800,)
        for a in sorted({b << 12 for b in range(16)} | {(block << 12) | s for s in split}):
            vma, drv = self._drivers(a, False)
            out.append("%04X  -VMA=%d  %s" % (a, vma, " + ".join(n for n, _ in drv) or "(nothing: floats FF)"))
        return "\n".join(out)

    # ------------------------------------------------------------------ I/O instructions
    def out(self, n, v):
        if self.icard:
            op, reg = self.icard.cycle(n, True, v)
            if reg == "undefined": self._event("undefined", ["ide"], n, "OUT %d: drive register lines undefined" % n)
            elif op == "w": self.ide.sel = reg; self.ide.out(3, self.icard.to_drive(v))
            elif op == "r": self._event("undefined", ["ide"], n, "OUT %d raised DIOR" % n)
        elif n in (2, 3): self.ide.out(n, v)
        if self.iocard:
            kbd, on, off, faults = self.iocard.cycle(n, True, v)
            for f in faults: self._event("undefined", ["io"], n, "OUT %d: %s" % (n, f))
            if off: self.pixie.on = False
            if on: self.pixie.on = True
            if kbd: self._event("undefined", ["io"], n, "OUT %d enabled the keyboard 1852 onto the bus" % n)
        elif n == self.pixie.port: self.pixie.on = False
        if self.panel: self.panel.out(n, v)
        if self.watch: self.watch("o", n, v)

    def inp(self, n):
        drv = []
        if self.icard:
            op, reg = self.icard.cycle(n, False)
            if reg == "undefined": self._event("undefined", ["ide"], n, "INP %d: drive register lines undefined" % n)
            elif op == "r": self.ide.sel = reg; drv.append(("ide drive", self.icard.to_bus(self.ide.inp(3))))
            elif op == "w": self._event("undefined", ["ide"], n, "INP %d raised DIOW" % n)
        elif n in (2, 3): drv.append(("ide", self.ide.inp(n)))
        if self.iocard:
            kbd, on, off, faults = self.iocard.cycle(n, False)
            for f in faults: self._event("undefined", ["io"], n, "INP %d: %s" % (n, f))
            if kbd: drv.append(("io 1852", self.iocard.to_bus(self.kbd.read())))
            if on: self.pixie.on = True
            if off: self.pixie.on = False
        else:
            if n == self.kbd.port: drv.append(("keyboard", self.kbd.read()))
            if n == self.pixie.port: self.pixie.on = True
        if self.panel:
            b = self.panel.inp(n)
            if b is not None: drv.append(("io panel", b))
        if len(drv) > 1:
            self._event("fight" if len({b for _, b in drv}) > 1 else "double", [d for d, _ in drv], n,
                        "INP %d: " % n + " ".join("%s=%02X" % d for d in drv))
        v = FLOAT
        for _, b in drv: v &= b
        if self.watch: self.watch("i", n, v)
        return v

    def ef(self, n):
        if not self.ccard: return super().ef(n)
        src = self.ccard.ef_map.get(n)
        kbd_on_bus = self.iocard.sr_on_bus if self.iocard else True
        panel = self.panel.ef("-EF" if src == "-EF4" else src) if self.panel and src in ("-EF1", "-EF2", "-EF3", "-EF4") else False
        if self.vg:                                                      # VIDEO-G: KEY-READY on the bus line its JP3 picks
            return panel or (src in ("-EF1", "-EF2", "-EF3", "-EF4") and self.vg.ef("-EF" if src == "-EF4" else src))
        if isinstance(self.vcard, NetlistVideoKbdCard):                  # the 6845 card's keyboard: the line its JP1 picks
            return panel or (src in ("-EF1", "-EF2", "-EF3", "-EF4") and self.vcard.ef("-EF" if src == "-EF4" else src))
        if src == "-EF4": return (kbd_on_bus and self.kbd.ready()) or panel   # the bus -EF: the IO card's 1852 (SV1 2-3), or
        if src == "KEF": return not kbd_on_bus and self.kbd.ready()       # the panel's INPUT; KEF: the IO card's EFK, over the SV3 cable
        if src == "VEF": return self.pixie.ef1()
        return panel                                                    # the IO panel's INPUT on the line JP3 picks

    # ------------------------------------------------------------------ the IO panel's hand controls
    def panel_set(self, switches=None, input=None, run=None, load=None, reset=None):
        """the IO panel's toggles (byte), INPUT (pressed), RUN and LOAD, as a person at the front panel would. RUN off holds
        the machine in reset (-RESET), LOAD on pauses it (-PAUSE); both = LOAD mode, where each INPUT press is one DMA IN
        of the toggles to M(R0). The CPU card (Rev D) sees the same lines: its LOADED flag then keeps the boot map off.
        reset: the card's own RESET button (2026-11-23), a boot reset: the machine starts in the EPROM when it is let go"""
        self.panel.set(switches=switches, pressed=input, run=run, load=load, reset=reset)
        self._controls(); return self.panel_text()

    def front_set(self, switches=None, input=None, run=None, load=None, reset=None):
        """the front panel's controls: the data toggles (byte), INPUT, RUN and LOAD as the IO panel's (through the
        ribbon), and RESET (pressed): a boot reset, which starts the machine in the EPROM when it is let go"""
        self.front.set(switches=switches, pressed=input, run=run, load=load, reset=reset)
        self._controls(); return self.front_text()

    def _controls(self):
        """after a hand control has moved: the ribbon, the three bus lines, the 1802's mode, and the DMA IN an INPUT
        press in LOAD mode asks for"""
        if self.front: self.panel.remote(*self.front.ribbon_in())
        self.lines_update(); self._panel_dma()

    def _rev_d(self): return bool(self.ccard) and getattr(self.ccard, "sw_rst", None) is not None

    def _settle_lines(self):
        """-RESET, -PAUSE and -DMAIN are open collector: a line is low while any card pulls it. Each card with a netlist
        here (CPU Rev D, the IO panel, the front panel) is told what the others hold low and asked what it holds
        itself, round and round until nothing changes (the CPU card and the front panel let -DMAIN go when -PAUSE
        falls, so one line can move another). ext_pull: the pulls of cards played without a netlist (the bus driver).
        -> {line: 0 | 1}"""
        cards = [c for c in (self.ccard if self._rev_d() else None, self.panel, self.front) if c]
        own = {id(c): set() for c in cards}; ext = set().union(*self.ext_pull.values())
        for _ in range(8):
            moved = False
            for c in cards:
                others = ext.union(*(own[id(o)] for o in cards if o is not c))
                c.lines(*(0 if n in others else 1 for n in self.LINES)); p = c.pulls()
                if p != own[id(c)]: own[id(c)] = p; moved = True
            if not moved: break
        low = ext.union(*own.values())
        return {n: 0 if n in low else 1 for n in self.LINES}

    def lines_update(self):
        """call after anything that pulls or lets go -RESET, -PAUSE or -DMAIN: the lines settle, the 1802 takes the
        mode its CLEAR and WAIT pins give it (from the CPU card's gates on Rev D), resets as it enters RESET, and
        stands still in every mode but RUN. -> the mode: 'run', 'reset', 'pause' or 'load'"""
        before = self.run_mode; lv = self.bus_lines = self._settle_lines()
        mode = (self.ccard.cpu_mode() if self._rev_d() else None) or \
            {(1, 1): "run", (1, 0): "pause", (0, 1): "reset", (0, 0): "load"}[(lv["-RESET"], lv["-PAUSE"])]
        if mode == "reset" and before != "reset":                        # CLEAR low, WAIT high: the 1802 resets (R0 = 0000)
            self.cpu.reset(); self.pixie.on = False                      # (in LOAD mode R0 counts the bytes instead)
        self._video_reset(low=lv["-RESET"] == 0)                         # the bus -RESET held low: VIDEO-G sees it
        self.run_mode = mode; self.held = mode != "run"
        self._ribbon(); return mode

    def _dma_request(self):
        """the DMA request as the 1802 has it at clock 7 of a cycle: its DMA IN pin on CPU Rev D (the card's gates:
        only in pause, and only once -DMAIN has been high since), else the bus line"""
        lv = self.bus_lines = self._settle_lines()
        return self.ccard.dma_request() if self._rev_d() else lv["-DMAIN"] == 0

    def _panel_dma(self):
        """LOAD mode: the DMA IN cycles the IO panel's request makes. The 1802 samples the request at clock 7 of
        every cycle, the DMA cycle's own too: one that still stands there gets another cycle, the same byte at the
        next address. More than one cycle for a press goes in the bus log ('double')"""
        p = self.panel; n = 0
        again = bool(p) and self.run_mode == "load" and "-DMAIN" in p.pulls() and self._dma_request()
        while again and n < 4:
            p.s2_begin(self.cpu.R[0]); again = self._dma_request(); b = p.s2_end(again); n += 1
            if b is None: self._event("undefined", ["panel"], 0, "INPUT in LOAD mode: the card did not drive the bus")
            else: self.cpu.dma_in(b)
        if n > 1: self._event("double", ["panel"], 0, "%d DMA IN cycles for one request: it outlasted the DMA cycle's clock 7" % n)
        if n: self.lines_update()
        return n

    def _ribbon(self):
        """what the IO panel card's J3 sends down the ribbon, onto the front panel's displays and LEDs: the address
        and output latches, the Q LED's sink, and the ROM LED's (-VMA as a fetch at the 1802's program counter has it)"""
        if not self.front: return
        self._show_address()
        p = self.panel; vma = self.cpu_card(self.cpu.R[self.cpu.P])[0] if self.ccard else 0
        p.c.drive(Q=1 if self.cpu.Q else 0, VMA=vma); p.c.settle()
        self.front.show({name: p.c.val.get(net) for name, net in p.ribbon_out.items()})

    def _show_address(self):
        """the IO panel's address latches as the 1802's cycles leave them, for the displays: in RUN and PAUSE the last
        cycle's address (taken as a fetch at the program counter); in LOAD mode the 1802 idles on R(0) with TPA left
        out, so only the low byte's latch follows (the high byte's holds the page of the last byte loaded); in RESET
        neither pulse comes and the displays keep what they had"""
        p = self.panel
        if self.run_mode in ("run", "pause"): p.cycle(self.cpu.R[self.cpu.P])
        elif self.run_mode == "load": p.cycle(self.cpu.R[0], tpa=False)

    def panel_text(self):
        p = self.panel; self._show_address()
        return "%s  Q %s   toggles %s (%02X)  INPUT %s  RUN %s  LOAD %s%s   mode %s" % (
            p.leds(), "*" if self.cpu.Q else ".", "".join("1" if p.switches >> k & 1 else "0" for k in range(7, -1, -1)),
            p.switches, "down" if p.pressed else "up", "on" if p.run_on else "off", "on" if p.load_on else "off",
            "  RESET down" if p.reset_pressed else "", "LOAD" if self.run_mode == "load" else self.run_mode)

    def front_text(self):
        self._ribbon(); return "%s   mode %s" % (self.front.text(), "LOAD" if self.run_mode == "load" else self.run_mode)

    def step(self):
        if self.held:                                                    # -RESET or -PAUSE low: no instruction
            self.cpu.cycles += 1; return None
        return super().step()

    def _video_reset(self, low=None):
        """-RESET on the bus, as VIDEO-G sees it. low None: a pulse (the CPU card's reset); True / False: the level the
        IO panel's RUN toggle holds the line at. From its netlists the READY flip-flops and the control register clear
        through the card's own gates, and stay clear while the line is low; the behavioural model's control register
        is cleared here (as videog.VideoGMachine does)"""
        if self.vg:
            if low is None: self.vg.bus_reset()
            elif low != self.vg.reset_low: self.vg.reset_line(0 if low else 1)
        elif isinstance(self.vcard, NetlistVideoKbdCard):
            if low is not False: self.vcard.reset()                      # the 6845 card's KEY-READY (and its ATmega)
        elif self.video_name == "video-g" and low is not False: self.video.ctrl = 0

    def reset(self):
        """the CPU card's RESET/RUN switch to RESET and back (or the power coming up). On CPU Rev D that is a boot
        reset on the bus, which the front panel's copy of the LOADED flag follows"""
        super().reset(); self.fault = None
        if self.ccard:
            shared = self._rev_d() and (self.panel or self.front or self.ext_pull)
            if shared: self.ccard.sw1(True); self.lines_update()
            self.ccard.reset()
            if shared: self.lines_update()
        self._video_reset()
