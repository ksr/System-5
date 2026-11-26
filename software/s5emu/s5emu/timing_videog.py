# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-24
"""VIDEO-G TEXT's 6845 on the bus: the card's (write-only since 2026-11-24, Ken: "write-only for row 1"), as first drawn, and
the other ways to wire it that were weighed, each a change to the board's netlist; the 6845's data sheet against the card's
slowest gates and the 1802's slowest and fastest strobes.

    python3 -m s5emu.timing_videog [MHz ...]         (from software/s5emu: the table of hardware/video-g/DESIGN.md section 4)

Which bus edge starts and ends E in a cycle, and which move R/W, CS and RS, comes from simulating the card's logic through
the cycle before, the cycle and the cycle after (trace); when, from the static analysis (timing.CardTiming). Every strobe is
late or early on its own: 200 to 300 ns after its clock edge (the data sheet's typical and maximum), -MRD's rise to 350, the
high address byte to 850; every gate 0 ns to its maximum.

Where the 6845 is read is part of the wiring (READ_AT): RS is the bus line A0, which carries A8 in the high-byte time, so an
address with A8 = A0 keeps RS still."""
import contextlib, sys
from . import hwvideog, timing as TM
from .machine import CPUCardROM, Keyboard
from .netlist import Part

GND, V5, TPA, NTPA, TPBN, A0, A3, A9 = ("IC7", "8"), ("IC7", "16"), ("IC1", "11"), ("IC17", "2"), ("IC17", "4"), ("IC1", "3"), ("IC1", "8"), ("IC1", "5")


def w(ref, pin, to): return ("wire", ref, str(pin)) + to


AS_DRAWN = [w("IC4", 22, ("IC24", "5")), w("IC24", 1, ("J1", "17")), w("IC24", 4, ("J1", "18")),      # as it was first drawn
            w("IC21", 9, ("IC6", "15")), w("IC7", 3, TPBN)]                  # (to 2026-11-24): E = TPB within -MRW on a
#                                                  write, the -MRD time on a read; IC24A: -PRE = -MRD, -CLR = -MRW
NO_TPB = [w("IC7", 3, GND)]                      # E = the whole -MRW time on a write
CS_STILL = [w("IC5", 1, GND), w("IC5", 2, GND)]  # -CS low through 7800-7BFF: A1 and A2 are in E
READS_LATE = [w("IC6", 3, A3)]                   # A3 carries A11 = 1 in the high-byte time: no read enable before the low byte
TPA_CLOCK = [w("IC24", 1, V5), w("IC17", 1, TPA), w("IC24", 3, NTPA)]       # R/W = 0 clocked by TPA's fall, set by -MRD
TPA_LEVEL = [w("IC17", 1, TPA), w("IC24", 1, NTPA)]                         # R/W cleared while TPA is high, set by -MRD
ADDRESS_RW = [w("IC4", 22, A9), w("IC7", 3, A9), w("IC6", 3, A9),            # R/W = A9, latched: writes at A9 = 0, reads at
              w("IC6", 11, ("IC6", "15")), ("lift", "IC6", "15"),           # A9 = 1 (IC6's Y4 is the 6845's read)
              w("IC24", 1, V5), w("IC24", 4, V5)]                           # IC24A free: its inputs tied
READS_END_AT_TPB = [w("IC17", 1, TPA), w("IC24", 1, NTPA), w("IC24", 2, V5), w("IC24", 3, TPBN),      # IC24A = TPB has fallen
                    w("IC17", 11, ("IC21", "9")), w("IC18", 9, ("IC17", "10")), w("IC18", 10, ("IC24", "6")),   # (cleared at
                    w("IC17", 13, ("IC18", "8")), w("IC21", 9, ("IC17", "12"))]                      # TPA): ends the read's E
def rs_one_while(b, inverter):
    """RS = A0 OR b, b high in reads of the 6845: RS stands still in a read, whatever A0's line does (only the data register
    can be read). Of the spare gates: an inverter of IC17, IC18C and IC22C: (A0 AND NOT b) XOR b"""
    i, o = inverter
    return [w("IC17", i, b), w("IC18", 9, A0), w("IC18", 10, ("IC17", o)), w("IC22", 9, ("IC18", "8")), w("IC22", 10, b), w("IC4", 24, ("IC22", "8"))]


CANDIDATES = {
    "write-only (the card)": [],
    "as first drawn": AS_DRAWN,
    "G  TPB off E only": AS_DRAWN + NO_TPB,
    "F  E after R/W (IC7.3 on R/W)": AS_DRAWN + [w("IC7", 3, ("IC24", "5"))],
    "L  TPA's fall clocks R/W low": AS_DRAWN + NO_TPB + TPA_CLOCK,
    "Lv TPA high clears R/W": AS_DRAWN + NO_TPB + TPA_LEVEL,
    "T  L, E on reads = TPB": AS_DRAWN + NO_TPB + TPA_CLOCK + [w("IC6", 3, TPBN)],
    "K  Lv, reads wait for A3, CS still": AS_DRAWN + NO_TPB + TPA_LEVEL + READS_LATE + CS_STILL,
    "A  R/W = A9, CS still": AS_DRAWN + ADDRESS_RW + CS_STILL,
    "AT A, reads end at TPB's fall": AS_DRAWN + ADDRESS_RW + CS_STILL + READS_END_AT_TPB,
    "KO K, RS = A0 OR R/W": AS_DRAWN + NO_TPB + TPA_LEVEL + READS_LATE + CS_STILL + rs_one_while(("IC24", "5"), (11, "10")),
    "AO A, RS = A0 OR A9": AS_DRAWN + ADDRESS_RW + CS_STILL + rs_one_while(A9, (1, "2")),
}
READ_AT = {n: (0x7A01, 0x7B01) for n in CANDIDATES if n[0] == "A"}
REGS_READ = (0x7801, 0x7901)
CYCLES = {"read": ("A_hi", "TPA_rise", "MRD_fall", "TPA_fall", "A_lo", "TPB_rise", "TPB_fall", "MRD_rise"),
          "write": ("A_hi", "TPA_rise", "TPA_fall", "A_lo", "MWR_fall", "TPB_rise", "MWR_rise", "TPB_fall"),
          "none": ("A_hi", "TPA_rise", "TPA_fall", "A_lo", "TPB_rise", "TPB_fall"),
          "idle": ("A_hi", "MRD_fall", "A_lo", "TPB_rise", "TPB_fall", "MRD_rise")}        # LOAD mode: TPA is suppressed
DRIVE = dict(TPA_rise=dict(TPA=1), TPA_fall=dict(TPA=0), MRD_fall=dict(MRD=0), MRD_rise=dict(MRD=1), MWR_fall=dict(MRW=0),
             MWR_rise=dict(MRW=1), TPB_rise=dict(TPB=1), TPB_fall=dict(TPB=0))
NOMINAL = dict(A_hi=0, TPA_rise=1, MRD_fall=1.5, TPA_fall=2, A_lo=2.5, MWR_fall=5, TPB_rise=6.5, MWR_rise=7, TPB_fall=7.5, MRD_rise=8)


class Bench:
    def __init__(self): self.kbd = Keyboard(None); self.cpu = type("CPU", (), {"cycles": 0})()


@contextlib.contextmanager
def wired(ops):
    """VIDEO-G 1.0 with TEXT changed, as a revision name for NetlistVideoG"""
    name = "1.0, changed"
    hwvideog.VIDEOG_REVS[name] = dict(hwvideog.VIDEOG_REVS["1.0"], rework=list(ops))
    try: yield name
    finally: del hwvideog.VIDEOG_REVS[name]


def card(ops, gfx=False):
    """-> (NetlistVideoG, {CS, E, RW, RS: net}) of TEXT changed by ops, the parts by what is fitted, its card in no state"""
    from .videog import VideoG
    with wired(ops) as rev: c = hwvideog.NetlistVideoG(VideoG(Bench(), gfx=gfx), rev, gfx=gfx)
    for ref, p in list(c.nl.parts.items()):
        if p.value in TM.PARTS and p.value != p.lib: c.nl.parts[ref] = Part(ref, p.value, p.value)
    c._unknown(); c.c.drive(TPA=0, TPB=0, A=0, MRD=1, MRW=1, VMA=0, RESET=1)
    return c, dict(CS=c.crtc["cs"], E=c.crtc["e"], RW=c.crtc["rw"], RS=c.crtc["rs"])


def cpu_vma(T):
    rom = CPUCardROM(); rom.loaded = True
    from .hw import NetlistCPUCard
    cpu = NetlistCPUCard(rom, "D"); ct = TM.CardTiming("CPU", cpu.nl, cpu.c)
    arr, _ = ct.propagate("read", TM.bus_events(T, "read")); v = arr[ct.sig["-VMA"]]
    return min(t0 for t0, t1, tr in v.values()), TM.latest(arr, ct.sig["-VMA"])[0]


def edges(circuit, kind, a):
    """one cycle's bus edges in order, the gates settled after each: (edge, values)"""
    for e in CYCLES[kind]:
        circuit.drive(**(dict(A=a >> 8) if e == "A_hi" else dict(A=a & 255) if e == "A_lo" else DRIVE[e])); yield e, circuit.settle()


def trace(circuit, pins, cycles):
    """[(cycle number, edge, {CS, E, RW, RS})] of several cycles [(kind, address)] one after the other, from a fetch"""
    list(edges(circuit, "read", 0)); out = []
    for k, (kind, a) in enumerate(cycles):
        out += [(k, e, {p: v.get(n) for p, n in pins.items()}) for e, v in edges(circuit, kind, a)]
    return out


def rows(ct, pins, T, P, kind, a, before="read", after="write", vma=None):
    """the 6845's timing in one cycle -> ([(check, margin)], text). before / after: the kinds of the cycles round it"""
    c = TM.CPU; fast, slow = c["tpa_typ"], c["tpa_max"]
    tr = trace(ct.c, pins, [(before, 0x0000 if before != "write" else 0x6000), (kind, a), (after, 0x6000)])
    mine = [(e, v) for k, e, v in tr if k == 1]; prev = [v for k, e, v in tr if k == 0][-1]; nxt = [(e, v) for k, e, v in tr if k == 2]
    ev = TM.bus_events(T, kind, vma=vma)
    if kind == "read": ev["MRD_rise"] = ("-MRD", 8 * T + fast, 8 * T + 350)
    elif before == "read": ev["MRD_rise"] = ("-MRD", fast, 350)
    arr, _ = ct.propagate(kind, ev)
    act = lambda v: v["CS"] == 0 and v["E"] == 1
    ons = [i for i, (e, v) in enumerate(mine) if act(v) and (i == 0 or not act(mine[i - 1][1]))]
    if not ons: return None, "the 6845 is not touched"
    i = ons[0]; on = mine[i][0]; offs = [e for e, v in mine[i:] if not act(v)]
    if not offs: return None, "E does not end in the cycle"
    off = offs[0]; er, ef = arr[pins["E"]][on], arr[pins["E"]][off]; out = []
    want = 1 if kind == "read" else 0; high = [v for e, v in mine[i:] if act(v)]
    for p in ("RS", "CS"):
        if any(v[p] != high[-1][p] for v in high): out.append(("%s still while E is high" % p, float("-inf")))
    if any(v["RW"] != want for v in high): out.append(("R/W wrong while E is high", float("-inf")))
    # set-up: every event up to E's that reaches the pin; on A0 only the bytes that change it. CS and RS one check, R/W one
    upto = CYCLES[kind][:CYCLES[kind].index(on) + 1] + ("VMA",)
    other = trace(ct.c, pins, [(before, 0x0000 if before != "write" else 0x6000), (kind, a ^ 1), (after, 0x6000)])
    free = pins["RS"] not in ct.c.bus.sig.values() and {v["RS"] for k, e, v in other if k == 1 and act(v)} == {v["RS"] for v in high}
    same_rs = free or (a >> 8) & 1 == a & 1
    lv = [prev] + [v for e, v in mine]                                    # R/W: the edges that move it (a flip-flop's clock
    moves = [mine[j][0] for j in range(i + 1) if lv[j + 1]["RW"] != lv[j]["RW"]]      # edges that do not are no events)
    latched = any(isinstance(m, TM.DFF74) and pins["RW"] in [o for o, _ in m.deps()] for m in ct.c.models)
    def settled(pin, only=None):
        if pins[pin] in ("GND", "+5V", "VCC"): return 0.0
        got = [t1 for e, (t0, t1, _) in arr.get(pins[pin], {}).items()
               if e in (only or upto) and not (pin == "RS" and e == "A_lo" and same_rs) and not (pin == "RS" and free and latched and e not in moves)]
        return max(got, default=0.0)
    t_rw = settled("RW", moves) if latched else settled("RW")
    if latched and not moves: t_rw = 0.0
    out.append(("CS setup", er[0] - settled("CS") - P["tas"])); out.append(("RS setup", er[0] - settled("RS") - P["tas"]))
    out.append(("R/W setup", er[0] - t_rw - P["tas"]))
    if on == off: out.append(("E width", float("-inf")))
    out.append(("E width", ef[0] - er[1] - P["e_high"]))
    # hold: what moves next
    t_next = {"A_hi": 8 * T + fast, "TPA_rise": 9 * T + fast, "MRD_fall": 9.5 * T + fast, "TPA_fall": 10 * T + fast,
              "A_lo": 10 * T + fast + T / 2 - 25, "MWR_fall": 13 * T + fast}
    t_next["A_hi"] = 7 * T + fast + T - 30 if kind == "write" else 8 * T + fast      # (a write's: T - 30 past -MWR)
    last = mine[-1][1]["RW"]; rw_moves = [arr[pins["RW"]][e][0] for e, v in mine[[e for e, _ in mine].index(off):] if v["RW"] != want and e in arr.get(pins["RW"], {})]
    end = rw_moves[0] if rw_moves else next((t_next.get(e, 1e9) for e, v in nxt if v["RW"] != last), 16 * T)
    if off in ("MWR_rise", "MRD_rise") and not rw_moves: pass
    out.append(("R/W hold", end - ef[1] - P["tah"]))
    late = (lambda t: t - ((ef[1] - ef[0]) if kind == "read" else 0))
    g_off = ef[1] - (NOMINAL[off] * T + (350 if off == "MRD_rise" else slow))
    # the low byte's hold is given from the write strobe itself; after a read it is a fresh strobe's
    if free: out.append(("RS hold", 9 * T + fast - ef[1] - P["tah"]))        # (nothing of A0's is in RS then)
    else: out.append(("RS hold", (t_next["A_hi"] - (7 * T + fast) - g_off if kind == "write" and off == "MWR_rise" else t_next["A_hi"] - ef[1]) - P["tah"]))
    if any(e in arr.get(pins["CS"], {}) for e in ("A_lo",)): out.append(("CS hold", out[-1][1]))
    else: out.append(("CS hold", 9 * T + fast - ef[1] - P["tah"]))
    if kind == "read":
        out.append(("data by 7.5T - 25", 7.5 * T - c["din_setup"] - er[1] - P["tddr"]))
        out.append(("data held 7.5T + 200", ef[0] + P["tdhr"] - 7.5 * T - c["din_hold"]))
    else:
        out.append(("data setup", ef[0] - 2 * T - c["data_out_max"] - P["tdsw"]))
        # both from -MRW: T - 200 past its rise
        if off == "MWR_rise": out.append(("data hold", T - 200 - g_off - P["tdhw"]))
        else: out.append(("data hold", 7 * T + fast + T - 200 - ef[1] - P["tdhw"]))
    return out, "E from %s to %s" % (on, off)


def study(name, mhz, grade="MC68B45"):
    """-> {half: (rows, text)} for the candidate: write; read after a fetch; read after a cycle without -MRD, at each READ_AT"""
    T = 1000.0 / mhz; P = TM.PARTS[grade]
    c, pins = card(CANDIDATES[name]); ct = TM.CardTiming(name, c.nl, c.c); vma = cpu_vma(T); out = {}
    out["write 7801"] = rows(ct, pins, T, P, "write", 0x7801, vma=vma)
    for a in READ_AT.get(name, REGS_READ):
        out["read %04X after a read" % a] = rows(ct, pins, T, P, "read", a, vma=vma)
        out["read %04X after a write" % a] = rows(ct, pins, T, P, "read", a, before="write", vma=vma)
        out["read %04X after no access" % a] = rows(ct, pins, T, P, "read", a, before="none", vma=vma)
    return out


def report(mhz):
    out = ["VIDEO-G TEXT's 6845 (2 MHz grade), %.2f MHz: ns of margin, every strobe on its own worst" % mhz]
    for name in CANDIDATES:
        out.append(name)
        for half, (r, text) in study(name, mhz).items():
            if r is None: out.append("    %-26s %s" % (half, text)); continue
            out.append("    %-26s %-27s %s" % (half, text, "FAIL " + ", ".join("%s%s" % (k, "" if m == float("-inf") else " %+.0f" % m) for k, m in r if m < 0)
                                               if any(m < 0 for _, m in r) else "passes; least %s %+.0f" % min(r, key=lambda x: x[1])))
    return "\n".join(out)


if __name__ == "__main__":
    for m in sys.argv[1:] or ["1.76", "2.0"]: print(report(float(m))); print()
