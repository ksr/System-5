# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-07
"""Static timing analysis of the System-5 cards, from the same KiCad netlists the --hw emulator runs.

    python3 -m s5emu.timing [--cpu A-built|A|D] [MHz]   (from software/s5emu; default CPU A-built, 1.76 MHz)

How it works
  Events.  A machine cycle is a set of bus events, each a window [earliest, latest] in ns from the clock edge that
           starts the cycle, from the CDP1802A datasheet (CPU below; ../private-resources/elf/reference/datasheets/cdp1802.pdf, Figure 4):
           the high address byte, TPA rising/falling, the low address byte, MRD, MWR, TPB, N0-N2, CPU write data.
           -VMA is not a 1802 pin: it is computed on the CPU card and handed to the other cards as an event.
  Arcs.    Every gate output depends on its inputs through the model's deps() (logic.py), with the part's delay from
           PARTS. An event's arrival at each net is propagated along every path; the latest arrival keeps a trace of
           the gates it came through.
  Latches. Which bus event opens and which closes each latch or register is found by simulating the card's logic
           through the cycle's phases. A data event that settles before the closing edge (less setup) passes, as the
           latched value; one that changes only after it (plus hold) is blocked; one that overlaps it is a setup or
           hold violation. An edge-triggered register passes nothing combinationally: its output follows the edge.
  Loops.   Gates in a feedback loop (an SR latch built from NAND gates) are found as strongly connected sets and
           bounded: an event leaves the loop within one gate delay per gate in it.
  Checks.  Each bus device on a card gets the checks its datasheet needs (memory access, 6845 bus timing, the
           CDP1852 select, the ATA strobes), with the dominating path printed.

Limits: maximum delays only for gates (minimum 0, so hold checks are conservative); the 1802 has no minimum delays
(typical values stand in); delays are per part type, not per edge; wiring delay and loading are not modelled. Part
delays were typed in from the datasheets named in PARTS, not read from copies in ../private-resources/elf/reference/datasheets.
"""
import os, sys
from .logic import (Circuit, classify, Quad, Hex04, Hex05, Buffer4050, Mux151, Dec138, Comp85, Latch, Reg374,
                    DFF74, X)

# ---------------------------------------------------------------------------------------------- the 1802 (CDP1802A, 5 V)
CPU = dict(
    hi_addr_max=850, hi_addr_typ=600,        # clock 00 -> high-order address byte valid
    tpa_max=300, tpa_typ=200,                # clock -> TPA / TPB edges (no minimum given: typical is the fast bound)
    lo_addr_max=350,                         # clock 21 -> low-order address byte valid
    mrd_max=300, mwr_max=300,                # clock -> MRD / MWR edges
    data_out_max=450,                        # clock 20 -> CPU data valid on the bus (write cycles)
    n_max=550,                               # clock 00 -> N0-N2 valid (I/O cycles)
    din_setup=25, din_hold=200,              # data bus input set up / hold, at clock 71 (7.5 T), worst-case required
)

# ---------------------------------------------------------------------------------------------- parts (max ns, 5 V)
PARTS = {
    "74LS00": dict(tpd=15, src="TI SN74LS00"),
    "74LS02": dict(tpd=15, src="TI SN74LS02"),
    "74LS04": dict(tpd=15, src="TI SN74LS04"),
    "74LS05": dict(tpd=28, tpd_hl=28, src="TI SN74LS05 (open collector: the low-to-high edge is the pull-up's RC)"),
    "74LS32": dict(tpd=22, src="TI SN74LS32"),
    "74LS85": dict(tpd=45, cascade=30, src="TI SN74LS85 (data -> A=B 45; A=B input -> A=B output 30)"),
    "74LS138": dict(sel=41, en=40, src="TI SN74LS138"),
    "74LS151": dict(sel=43, data=32, strobe=32, src="TI SN74LS151"),
    "74LS373": dict(d_q=18, le_q=30, setup=5, hold=20, src="TI SN74LS373"),
    "74LS374": dict(clk_q=28, setup=20, hold=0, src="TI SN74LS374"),
    "74LS74": dict(clk_q=40, setup=20, hold=5, src="TI SN74LS74A"),
    "74LS75": dict(d_q=30, le_q=30, setup=20, hold=5, src="TI SN74LS75"),
    # CPU Rev D's HCT logic: max at 4.5 V, -40..85 C, CL = 50 pF (TI SN74HCTxx data sheets; typed in, to verify)
    "74HCT00": dict(tpd=25, src="TI SN74HCT00 (4.5 V, 85 C)"),
    "74HCT14": dict(tpd=40, src="TI SN74HCT14 (4.5 V, 85 C; Schmitt)"),
    "74HCT20": dict(tpd=30, src="TI SN74HCT20 (4.5 V, 85 C)"),
    "74HCT74": dict(clk_q=44, setup=31, hold=0, src="TI SN74HCT74 (4.5 V, 85 C)"),
    "74HCT373": dict(d_q=48, le_q=51, setup=16, hold=8, src="TI SN74HCT373 (4.5 V, 85 C)"),
    "CD4050B": dict(tpd=140, tpd_min=55, src="TI/RCA CD4050B, VDD = 5 V, CL = 50 pF (typ 55-70)"),
    "CD4042B": dict(d_q=220, le_q=300, clk_q=300, setup=100, hold=120, src="TI/RCA CD4042B, VDD = 5 V"),
    "62256-70": dict(taa=70, tace=70, toe=35, tdw=30, tdh=0, thz=25, src="Cypress CY62256LL-70 (memory Rev D RAM)"),
    "27C256-20": dict(taa=200, tace=200, toe=75, tdf=60, thz=60, src="Atmel AT27C256R-20"),
    "2732A-30": dict(taa=300, tace=300, toe=120, tdf=100, thz=100, src="Fujitsu MBM2732A-30 (CPU boot EPROM, as fitted)"),
    "IDT7134-35": dict(taa=35, tace=35, toe=25, tdw=20, thz=20, src="IDT7134SA35 (6845 card video RAM, as fitted)"),
    "MC6845": dict(e_high=450, tas=140, tah=10, tddr=320, tdhr=20, tdsw=195, tdhw=10,
                   src="Motorola MC6845 / Hitachi HD6845 (HD46505RP fitted), 1 MHz grade"),
    "CDP1852": dict(cs_data=400, src="RCA CDP1852, VDD = 5 V (estimate: chip select to data out)"),
    "ATA-PIO0": dict(dior_min=165, setup_addr=70, dior_data=125, dior_hold=5, dw_setup=60, src="ATA PIO mode 0 (the 16 MB CF card)"),
}
LOGIC_PART = {"nand": "74LS00", "02": "74LS02", "04": "74LS04", "05": "74LS05", "or": "74LS32", "85": "74LS85",
              "138": "74LS138", "151": "74LS151", "373": "74LS373", "374": "74LS374", "74": "74LS74", "75": "74LS75",
              "4042": "CD4042B", "4050": "CD4050B"}


def part_of(nl, ref):
    """the PARTS entry for a chip: its own type where PARTS has it (CPU Rev D's 74HCT parts), else its family's"""
    lib = nl.parts[ref].lib
    return lib if lib in PARTS else LOGIC_PART.get(classify(lib))


# ---------------------------------------------------------------------------------------------- bus events
def bus_events(T, cycle, vma=None, mem_data=None):
    """{event name: (signals, tmin, tmax)} for one machine cycle. cycle: read, write, inp N, out N.
    signals are bus connector pin names; 'A' = A0-A7, 'D' = D0-D7, 'N' = N0-N2."""
    c = CPU; fast, slow = c["tpa_typ"], c["tpa_max"]
    ev = {"A_hi": ("A", 0, c["hi_addr_max"]),
          "TPA_rise": ("TPA", T + fast, T + slow), "TPA_fall": ("TPA", 2 * T + fast, 2 * T + slow),
          "A_lo": ("A", 2 * T + fast + (T / 2 - 25), 2.5 * T + c["lo_addr_max"]),
          "TPB_rise": ("TPB", 6.5 * T + fast, 6.5 * T + slow), "TPB_fall": ("TPB", 7.5 * T + fast, 7.5 * T + slow)}
    kind = cycle.split()[0]
    if kind in ("read", "out"): ev["MRD_fall"] = ("-MRD", 1.5 * T + fast, 1.5 * T + c["mrd_max"])
    if kind in ("write", "inp"):
        ev["MWR_fall"] = ("-MRW", 5 * T + fast, 5 * T + c["mwr_max"]); ev["MWR_rise"] = ("-MRW", 7 * T + fast, 7 * T + c["mwr_max"])   # the bus pin is named -MRW
    if kind == "write": ev["D_cpu"] = ("D", 2 * T + fast, 2 * T + c["data_out_max"])
    if kind in ("inp", "out"): ev["N"] = ("N", fast, c["n_max"])
    if kind == "out" and mem_data: ev["D_mem"] = ("D", mem_data[0], mem_data[1])
    if vma: ev["VMA"] = ("-VMA", vma[0], vma[1])
    return ev


def phase_drive(cycle, port=0):
    """the bus levels of the cycle's phases, for finding which event opens / closes each latch (polarity probe)"""
    kind = cycle.split()[0]
    base = dict(A=0x12, VMA=0, N=port if kind in ("inp", "out") else 0, TPA=0, TPB=0, MRD=0 if kind in ("read", "out") else 1,
                MRW=1, RESET=1)
    return [("start", dict(base)), ("TPA_rise", dict(TPA=1)), ("TPA_fall", dict(TPA=0)), ("TPB_rise", dict(TPB=1)),
            ("TPB_fall", dict(TPB=0))]


# ---------------------------------------------------------------------------------------------- the analyser
class CardTiming:
    def __init__(self, name, nl, circuit):
        self.name, self.nl, self.c = name, nl, circuit
        self.arcs = {}                                   # out net -> [(in net, model, arc kind, delay)]
        self.latch = {}                                  # out net -> (model, kind 'level'|'edge'|'ff', d net, en net)
        sig = circuit.bus.sig
        self.sig = sig
        for m in circuit.models:
            part = part_of(nl, m.ref); p = PARTS[part]
            for out, ins in m.deps():
                for i in ins:
                    if i in Circuit.POWER: continue
                    k, d = self._arc(m, p, out, i)
                    self.arcs.setdefault(out, []).append((i, m, k, d))
        self.loops = self._sccs()

    def _arc(self, m, p, out, i):
        """-> (arc kind, max delay) for input net i -> output net out of model m"""
        if isinstance(m, Mux151): k = "sel" if i in m.sel else "strobe" if i == m.g else "data"
        elif isinstance(m, Dec138): k = "sel" if i in m.sel else "en"
        elif isinstance(m, Comp85): k = "cascade" if i in m.ci else "tpd"
        elif isinstance(m, Reg374): k = "d_edge" if i not in (m.groups[0][0], m.off) else "clk_q"
        elif isinstance(m, DFF74):
            h = next(h for h in m.ff if out in h[4:])
            k = "d_edge" if i == h[1] else "clk_q"
        elif isinstance(m, Latch):
            en = {g[0] for g in m.groups}
            k = "le_q" if i in en or i == m.off else "d_q"
        elif isinstance(m, Hex05): k = "tpd_hl"
        else: k = "tpd"
        d = p.get(k, p.get("tpd", p.get("clk_q", 0))) if k != "d_edge" else 0
        return k, d

    def _sccs(self):
        """strongly connected sets of nets through combinational arcs (latch data arcs excluded): {net: loop id}"""
        g = {o: [i for i, m, k, d in a if k not in ("d_q", "d_edge")] for o, a in self.arcs.items()}
        index, low, stack, on, out, n = {}, {}, [], set(), {}, [0]
        sys.setrecursionlimit(10000)

        def visit(v):
            index[v] = low[v] = n[0]; n[0] += 1; stack.append(v); on.add(v)
            for w in g.get(v, []):
                if w not in index: visit(w); low[v] = min(low[v], low[w])
                elif w in on: low[v] = min(low[v], index[w])
            if low[v] == index[v]:
                comp = []
                while True:
                    w = stack.pop(); on.discard(w); comp.append(w)
                    if w == v: break
                if len(comp) > 1:
                    for w in comp: out[w] = (v, len(comp))
        for v in list(g):
            if v not in index: visit(v)
        return out

    # ---- which bus event opens / closes each latch, by simulating the cycle's phases
    def latch_edges(self, cycle, port=0):
        """{(model ref, en net): (open event, close event)} for the latches active in this cycle"""
        c = self.c; saved = dict(c.val), {id(m): dict(m.state) for m in c.models if hasattr(m, "state")}
        seq = []
        phases = phase_drive(cycle, port)
        for name, drive in phases + phases:                 # one warm-up cycle first: latches built from gates start
            c.drive(**drive); v = c.settle(); seq.append((name, dict(v)))     # undefined, as at power-up
        seq = seq[len(phases):]
        c.val = saved[0]
        for m in c.models:
            if hasattr(m, "state"): m.state = dict(saved[1][id(m)])
        out = {}
        for m in c.models:
            if isinstance(m, (Latch,)) and not isinstance(m, Reg374):
                for en, level, bits in m.groups:
                    act = [(name, v.get(en) == level) for name, v in seq]
                    opn = next((act[k][0] for k in range(1, len(act)) if act[k][1] and not act[k - 1][1]), None)
                    cls = next((act[k][0] for k in range(1, len(act)) if not act[k][1] and act[k - 1][1]), None)
                    if act[0][1] and opn is None: opn = "start"
                    out[(m.ref, en)] = (opn, cls)
            elif isinstance(m, Reg374):
                en = m.groups[0][0]; vals = [(name, v.get(en)) for name, v in seq]
                edge = next((vals[k][0] for k in range(1, len(vals)) if vals[k][1] == 1 and vals[k - 1][1] == 0), None)
                out[(m.ref, en)] = (edge, edge)
        return out

    # ---- propagation
    def propagate(self, cycle, events, port=0):
        """-> arrivals {net: {event: (tmin, tmax, trace)}}, violations [...]"""
        edges = self.latch_edges(cycle, port)
        arr = {}
        sig = self.sig
        src = {}
        for e, (s, t0, t1) in events.items():
            nets = [sig["%s%d" % (s, i)] for i in range(8 if s in "AD" else 3)] if s in ("A", "D", "N") else [sig[s]] if s in sig else []
            for net in nets: src.setdefault(net, []).append((e, t0, t1))
        for net, lst in src.items():
            for e, t0, t1 in lst: arr.setdefault(net, {})[e] = (t0, t1, [e])
        viol = []
        order = self._topo()
        for _ in range(3):                                   # latch outputs feed more logic: a few passes settle it
            for out in order:
                for i, m, k, d in self.arcs.get(out, []):
                    for e, (t0, t1, tr) in list(arr.get(i, {}).items()):
                        if i in self.loops and out in self.loops and self.loops[i][0] == self.loops[out][0]:
                            continue                                  # inside a feedback loop: bounded on entry instead
                        if k in ("d_q", "d_edge"):
                            r = self._capture(m, k, i, out, e, t0, t1, edges, arr, events, viol)
                            if r is None: continue
                            n0, n1, ntr = r
                        else:
                            if k in ("clk_q", "le_q") and isinstance(m, Latch):
                                opn, cls = edges.get((m.ref, i), (None, None))
                                if e != opn: continue                 # a register changes on its clock edge, a latch when it opens
                            n0 = t0 + PARTS[part_of(self.nl, m.ref)].get("tpd_min", 0); n1 = t1 + d
                            ntr = tr + ["%s(%s %s)" % (m.ref, part_of(self.nl, m.ref), k)]
                        if out in self.loops:
                            n1 += self.loops[out][1] * max(PARTS[part_of(self.nl, m.ref)].get("tpd", 15), 15)
                            ntr = ntr + ["(feedback loop of %d nets: +1 gate each)" % self.loops[out][1]]
                        old = arr.setdefault(out, {}).get(e)
                        if old is None or n1 > old[1] or n0 < old[0]:
                            arr[out][e] = (min(n0, old[0]) if old else n0, max(n1, old[1]) if old else n1,
                                           ntr + [self.nl_name(out)] if (old is None or n1 > old[1]) else old[2])
        return arr, viol

    def nl_name(self, net):
        return net.split("/")[-1]

    def _capture(self, m, k, d_net, out, e, t0, t1, edges, arr, events, viol):
        """a data event at a latch / register input: pass it as the latched value, block it, or record a violation"""
        part = part_of(self.nl, m.ref); p = PARTS[part]
        if isinstance(m, DFF74):
            return None                                       # D is tied (VCC) in System-5; the clock arc carries it
        en = m.groups[0][0] if isinstance(m, Reg374) else next(g[0] for g in m.groups if any(d_net == b[0] for b in g[2]))
        opn, cls = edges.get((m.ref, en), (None, None))
        if cls is None: return None                           # never closes in this cycle: not latched here
        ea = arr.get(en, {})
        close = ea.get(cls);
        if close is None: return None
        c0, c1 = close[0], close[1]
        setup, hold = p.get("setup", 0), p.get("hold", 0)
        key = (self.name, m.ref, e)
        if t1 <= c0 - setup:                                  # settled before the closing edge: latched
            if isinstance(m, Reg374):
                return (c0, c1 + p["clk_q"], close[2] + ["%s(%s clk_q, latches %s)" % (m.ref, part, e)])
            o = ea.get(opn)
            q1 = max(t1 + p["d_q"], (o[1] + p["le_q"]) if o else 0)
            return (t0, q1, (o[2] if o and o[1] + p["le_q"] > t1 + p["d_q"] else ["%s" % e]) +
                    ["%s(%s %s, latched on %s)" % (m.ref, part, "le_q" if o and o[1] + p["le_q"] > t1 + p["d_q"] else "d_q", cls)])
        if t0 >= c1 + hold: return None                       # changes only after the latch closed: blocked
        if not any(v[:3] == key for v in viol):
            viol.append((self.name, m.ref, e, "%s %s: input %s %s changes at %.0f-%.0f ns, the latch closes on %s at "
                         "%.0f-%.0f ns (setup %d, hold %d)" % (m.ref, part, self.nl_name(d_net), e, t0, t1, cls, c0, c1, setup, hold),
                         (c0 - setup) - t1))
        if t0 < c0:                                           # it was meant to be latched: the output still moves at
            q = (c1 + p["clk_q"]) if isinstance(m, Reg374) else max(t1 + p["d_q"], c1 + p.get("le_q", 0))   # the edge
            return (min(t0, c0), q, close[2] + ["%s(%s, VIOLATED: latches %s)" % (m.ref, part, e)])
        return None

    def _topo(self):
        """nets in an order where most drivers come before their loads (loops and latches are handled by repeat passes)"""
        seen, order = set(), []

        def visit(n, depth=0):
            if n in seen or depth > 200: return
            seen.add(n)
            for i, m, k, d in self.arcs.get(n, []): visit(i, depth + 1)
            order.append(n)
        for n in list(self.arcs): visit(n)
        return order


# ---------------------------------------------------------------------------------------------- per-card checks
def latest(arr, net, only=None):
    """the latest (tmax, event, trace) of any event at net (optionally only some events)"""
    best = None
    for e, (t0, t1, tr) in arr.get(net, {}).items():
        if only and e not in only: continue
        if best is None or t1 > best[0]: best = (t1, e, tr)
    return best


def chain(tr): return " > ".join(tr)


def analyse(f_mhz=1.76, root=None, cpu_rev="A-built"):
    """-> list of result rows (card, check, budget, need, path)"""
    from .hw import (NetlistMemoryCard, NetlistVideoCard, NetlistIDECard, NetlistIOBoard, NetlistCPUCard, _NetlistROM)
    from .machine import Video6845, CPUCardROM
    T = 1000.0 / f_mhz; c = CPU; rows = []; viol_all = []
    deadline = 7.5 * T - c["din_setup"]

    def row(card, check, budget, need, path=""):
        rows.append((card, check, budget, need, path))

    # ---- CPU card: -VMA and the boot EPROM
    rom = CPUCardROM(); rom.loaded = True; cpu = NetlistCPUCard(rom, cpu_rev); cn = "CPU " + cpu_rev
    ct = CardTiming(cn, cpu.nl, cpu.c)
    arr, viol = ct.propagate("read", bus_events(T, "read")); viol_all += viol
    v = latest(arr, ct.sig["-VMA"])
    vma = (min(t0 for t0, t1, tr in arr[ct.sig["-VMA"]].values()), v[0])
    row(cn, "-VMA settles (latest event at the bus pin)", 2.5 * T + c["lo_addr_max"], v[0], chain(v[2]))
    for d in cpu.c.mem:
        data = max(x for x in [_lat(arr, d.addr, PARTS["2732A-30"]["taa"]), _lat(arr, [d.ce], PARTS["2732A-30"]["tace"]),
                               _lat(arr, [d.oe], PARTS["2732A-30"]["toe"])] if x)
        row(cn, "%s 2732 read: data on the bus by the 1802's latch point" % d.ref, deadline, data[0], chain(data[1]))

    # ---- memory card Rev D: read and write cycles
    mem = NetlistMemoryCard("D"); mt = CardTiming("memory D", mem.nl, mem.c)
    arr, viol = mt.propagate("read", bus_events(T, "read", vma=vma)); viol_all += viol
    mem_data = None
    for d in mem.chips:
        part = "62256-70" if d.kind == "RAM" else "27C256-20"; P = PARTS[part]
        data = max(x for x in [_lat(arr, d.addr, P["taa"]), _lat(arr, [d.ce], P["tace"]), _lat(arr, [d.oe], P["toe"])] if x)
        row("memory D", "%s %s read: data on the bus by the 1802's latch point" % (d.ref, part), deadline, data[0], chain(data[1]))
        mem_data = (2.5 * T, max(mem_data[1], data[0]) if mem_data else data[0])
    arr, viol = mt.propagate("write", bus_events(T, "write", vma=vma)); viol_all += viol
    for d in mem.chips:
        if d.kind != "RAM": continue
        P = PARTS["62256-70"]
        we_rise = arr[d.we].get("MWR_rise"); we_fall = arr[d.we].get("MWR_fall")
        sel = max(x for x in [_lat(arr, d.addr, 0, skip=("MWR_rise",)), _lat(arr, [d.ce], 0, skip=("MWR_rise", "MWR_fall"))] if x)
        row("memory D", "%s write: address and CE settled before WE falls" % d.ref, we_fall[0], sel[0], chain(sel[1]))
        dat = _lat(arr, d.data, P["tdw"], only=("D_cpu",))
        row("memory D", "%s write: data set up before WE rises" % d.ref, we_rise[0], dat[0], chain(dat[1]))

    # ---- 6845 card
    vid = NetlistVideoCard(Video6845(), "B"); vt = CardTiming("6845 B", vid.nl, vid.c)
    P = PARTS["MC6845"]
    for cyc in ("read", "write"):
        arr, viol = vt.propagate(cyc, bus_events(T, cyc, vma=vma)); viol_all += viol
        for d in vid.c.mem:
            if d.kind == "CRTC":
                e_rise = arr[d.e]["TPB_rise"]; e_fall = arr[d.e]["TPB_fall"]
                sel = max(x for x in [_lat(arr, [d.cs], 0), _lat(arr, [d.rs], 0)] if x)
                if cyc == "read":
                    row("6845 B", "%s CS and RS set up before E rises (tAS %d)" % (d.ref, P["tas"]), e_rise[0], sel[0] + P["tas"], chain(sel[1]))
                    row("6845 B", "%s E high time (min %d)" % (d.ref, P["e_high"]), e_fall[0] - e_rise[1], P["e_high"], chain(e_rise[2]))
                    row("6845 B", "%s register read: data on the bus by the 1802's latch point" % d.ref, deadline,
                        e_rise[1] + P["tddr"], chain(e_rise[2]))
                    row("6845 B", "%s register read: data held past the 1802's latch point (hold %d)" % (d.ref, c["din_hold"]),
                        e_fall[0] + P["tdhr"] - 7.5 * T, c["din_hold"], chain(e_fall[2]))
                else:
                    rw = arr[d.rw].get("MWR_rise")
                    row("6845 B", "%s register write: R/W held low until E falls (tAH %d)" % (d.ref, P["tah"]),
                        rw[0], e_fall[1] + P["tah"], chain(rw[2]) + "   vs   " + chain(e_fall[2]))
            elif d.kind == "DPRAM" and cyc == "read":
                Pd = PARTS["IDT7134-35"]
                data = max(x for x in [_lat(arr, d.addr, Pd["taa"]), _lat(arr, [d.ce], Pd["tace"]), _lat(arr, [d.oe], Pd["toe"])] if x)
                row("6845 B", "%s 7134 read: data on the bus by the 1802's latch point" % d.ref, deadline, data[0], chain(data[1]))

    # ---- IO card: keyboard port (INP 1)
    io = NetlistIOBoard("A"); it = CardTiming("IO A", io.nl, io.c)
    arr, viol = it.propagate("inp 1", bus_events(T, "inp 1"), port=1); viol_all += viol
    for d in io.c.mem:
        if d.kind == "PORT":
            sel = max(x for x in [_lat(arr, [d.cs1], 0), _lat(arr, [d.cs2], 0)] if x)
            row("IO A", "%s CDP1852 (INP 1): data on the bus by the 1802's latch point" % d.ref, deadline,
                sel[0] + PARTS["CDP1852"]["cs_data"], chain(sel[1]))

    # ---- IDE card: register select (OUT 2) and data (INP 3, OUT 3)
    ide = NetlistIDECard("A"); dt = CardTiming("IDE A", ide.nl, ide.c); A = PARTS["ATA-PIO0"]
    arr, viol = dt.propagate("out 2", bus_events(T, "out 2", mem_data=mem_data), port=2); viol_all += viol
    arr, viol = dt.propagate("inp 3", bus_events(T, "inp 3"), port=3); viol_all += viol
    dior = ide.ata["DIOR"]
    on = latest(arr, dior, only=("N", "TPA_rise", "TPA_fall", "MRD_fall"))
    off = arr.get(dior, {}).get("TPB_fall")
    if on and off:
        row("IDE A", "DIOR pulse width (INP 3; ATA PIO 0 min %d)" % A["dior_min"], off[0] - on[0], A["dior_min"], chain(on[2]))
        row("IDE A", "drive data on the bus by the 1802's latch point (INP 3)", deadline, on[0] + A["dior_data"], chain(on[2]))
        we = 7 * T + c["mwr_max"] + PARTS["CD4050B"]["tpd"]
        row("IDE A", "INP 3 into RAM: drive data held until memory D's WE rises", off[0] + A["dior_hold"], we,
            chain(off[2]) + "  (WE: -MWR + CD4050B)")
    arr, viol = dt.propagate("out 3", bus_events(T, "out 3", mem_data=mem_data), port=3); viol_all += viol
    diow = ide.ata["DIOW"]; w_on = latest(arr, diow, only=("TPB_rise",)); w_off = arr.get(diow, {}).get("TPB_fall")
    if w_on and w_off:
        row("IDE A", "DIOW pulse width (OUT 3; ATA PIO 0 min %d)" % A["dior_min"], w_off[0] - w_on[0], A["dior_min"], chain(w_on[2]))
        row("IDE A", "write data (from memory D) set up before DIOW rises", w_off[0], mem_data[1] + A["dw_setup"], "memory D read path")
    for card, ref, e, text, margin in viol_all:
        rows.append((card, "LATCH " + text, margin, 0, ""))
    return rows, T


def drivers(f_mhz=1.76, r13_ohms=None, c_pf=30.0, cpu_rev="A-built"):
    """the chips that drive the data bus in a memory read, card by card:
    [(card, chip, part, oe_on_min, ce_settled_max, off_time, ce_trace, oe_trace)]
    oe_on_min       earliest -MRD-driven output enable (the new chip can start driving from here)
    ce_settled_max  latest arrival at its chip enable in this cycle: a chip selected last cycle may drive until then
    off_time        its output turn-off delay; for the CPU EPROM plus the 74LS05/R13 pull-up rise to 2.0 V"""
    from .hw import NetlistMemoryCard, NetlistVideoCard, NetlistCPUCard
    from .machine import Video6845, CPUCardROM
    T = 1000.0 / f_mhz; out = []
    rom = CPUCardROM(); rom.loaded = True; cpu = NetlistCPUCard(rom, cpu_rev); cn = "CPU " + cpu_rev
    ct = CardTiming(cn, cpu.nl, cpu.c); arr, _ = ct.propagate("read", bus_events(T, "read"))
    vma = (min(t0 for t0, t1, tr in arr[ct.sig["-VMA"]].values()), latest(arr, ct.sig["-VMA"])[0])
    rc = 0.0 if r13_ohms is None else 0.43 * r13_ohms * c_pf * 1e-3      # ns: 0.4 V to 2.0 V on 5 V, t = RC ln(4.6/3)
    if cpu_rev == "D": rc = 0.0                                         # Rev D: the EPROM's CE is a push-pull 74HCT00 output, no R13
    cards = [(cn, ct, arr, cpu.c.mem, lambda d: "2732A-30", rc)]
    mem = NetlistMemoryCard("D"); mt = CardTiming("memory D", mem.nl, mem.c)
    cards.append(("memory D", mt, mt.propagate("read", bus_events(T, "read", vma=vma))[0], mem.chips,
                  lambda d: "62256-70" if d.kind == "RAM" else "27C256-20", 0.0))
    vid = NetlistVideoCard(Video6845(), "B"); vt = CardTiming("6845 B", vid.nl, vid.c)
    cards.append(("6845 B", vt, vt.propagate("read", bus_events(T, "read", vma=vma))[0],
                  [d for d in vid.c.mem if d.kind == "DPRAM"], lambda d: "IDT7134-35", 0.0))
    reachable = {ref for b in range(16) for ref, kind, op, ca in mem.decode(b << 12, 0, 0, 1)[0]}   # under the jumpers
    for card, t, a, devs, partof, extra in cards:
        for d in devs:
            if card == "memory D" and d.ref not in reachable: continue      # never selected: no fight possible
            p = PARTS[partof(d)]
            oe = a.get(d.oe, {}).get("MRD_fall"); ce = latest(a, d.ce)
            out.append((card, d.ref, partof(d), oe[0], ce[0], p["thz"] + extra, ce[2], oe[2]))
    return out, T


def contention(f_mhz=1.76, r13_ohms=None, c_pf=30.0, cpu_rev="A-built"):
    """bus fights when a read moves from a chip on one card to a chip on another: the old chip may still be selected
    (its enable has not settled for the new address) when -MRD turns the outputs back on. -> rows
    (old card/chip, new card/chip, overlap ns, explanation). Chips on the same card switch together from one decode
    (only gate skew), so only pairs on different cards are reported."""
    drv, T = drivers(f_mhz, r13_ohms, c_pf, cpu_rev); rows = []
    for a in drv:
        for b in drv:
            if a[0] == b[0]: continue
            a_stops = a[4] + a[5]                          # old chip: its enable settles, then its outputs float
            b_starts = b[3]                                # new chip: drives once -MRD reaches its output enable
            a_starts = a[3]                                # (the old chip only drives once -MRD is low again too)
            overlap = a_stops - max(b_starts, a_starts)
            rows.append(("%s %s (%s)" % (a[0], a[1], a[2]), "%s %s (%s)" % (b[0], b[1], b[2]), overlap,
                         "old chip enable settles at %.0f + off %.0f; new chip's -MRD output enable from %.0f"
                         % (a[4], a[5], b_starts), chain(a[6])))
    return rows, T


def contention_report(f_mhz=1.76, r13_values=(None, 1000, 2200, 4700, 10000), c_pf=30.0, cpu_rev="A-built"):
    out = ["Start-of-cycle contention at %.3f MHz: a read that moves from a chip on one card to a chip on another. "
           "Overlap = how long both may drive the data bus (worst case); <= 0 means none." % f_mhz, ""]
    for r in r13_values:
        if cpu_rev == "D" and r is not None: continue                   # Rev D has no R13
        rows, T = contention(f_mhz, r, c_pf, cpu_rev)
        tag = "R13 not counted" if r is None else "R13 = %g k, %g pF on the EPROM's CE" % (r / 1000.0, c_pf)
        out.append("-- %s" % tag)
        seen = set()
        for old, new, ov, why, tr in sorted(rows, key=lambda x: -x[2]):
            key = (old.split(" (")[0].rsplit(" ", 1)[0], new.split(" (")[0].rsplit(" ", 1)[0])
            if ov <= 0 or key in seen: continue
            seen.add(key)
            out.append("  %-34s -> %-34s overlap %5.0f ns   (%s)" % (old, new, ov, why))
            out.append("  %-34s    old chip's enable path: %s" % ("", tr))
        if not seen: out.append("  no overlaps")
    return "\n".join(out)


def _lat(arr, nets, extra, only=None, skip=()):
    """(latest arrival + extra, trace) over nets"""
    best = None
    for n in nets:
        for e, (t0, t1, tr) in arr.get(n, {}).items():
            if (only and e not in only) or e in skip: continue
            if best is None or t1 + extra > best[0]: best = (t1 + extra, tr)
    return best


def report(f_mhz=1.76, paths=True, cpu_rev="A-built"):
    rows, T = analyse(f_mhz, cpu_rev=cpu_rev)
    out = ["System-5 timing from the netlists at %.3f MHz (T = %.0f ns); budget and needs in ns from the cycle start "
           "(or as stated), margin = budget - needs" % (f_mhz, T), ""]
    for card, check, budget, need, path in rows:
        m = budget - need
        v = "OK" if m >= 50 else "MARGINAL" if m >= 0 else "FAILS (worst case)"
        out.append("%-12s %-80s budget %6.0f  needs %6.0f  margin %6.0f  %s" % (card, check[:80], budget, need, m, v))
        if len(check) > 80: out.append("%-12s   %s" % ("", check[80:]))
        if paths and path: out.append("%-12s   path: %s" % ("", path))
    return "\n".join(out)


if __name__ == "__main__":
    args = sys.argv[1:]; cpu_rev = "A-built"
    if "--cpu" in args:                                                 # python3 -m s5emu.timing --cpu D 2
        k = args.index("--cpu"); cpu_rev = args[k + 1]; del args[k:k + 2]
    for a in args or ["1.76"]:
        print(report(float(a), cpu_rev=cpu_rev)); print(); print(contention_report(float(a), cpu_rev=cpu_rev)); print()
