#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-31
"""Trace the CPU card's bus cycle by cycle with the bus driver stepping its clock, and compare with the emulator.

Set-up (bench, 2026-10-31): the bus driver's SPARE1 (J2 pin 1) wired to the CPU card's IC8 pin 3 (the 74x74 that
halves the oscillator into the 1802's CLOCK; pin 3 lifted from IC7), so every rising edge on SPARE1 is one 1802 clock
edge and the CPU stands still in between. The bus driver stays in MONITOR mode; the CPU card drives the bus.
Firmware clk-1 or later (CLK:n#, and -RESET in MONITOR mode).

  python3 cputrace.py [--cycles N] [--no-reset] [--save FILE] [--compare] [--jumpers ----------------]

(That set-up is BUSDRV-B with CPU Rev A. BUSDRV-C steps CPU Rev D's clock itself, through the DEBUG cable: there
`s5busdrv.py clk N --cycles` gives the same one line a machine cycle, with the state code, from bits() and cycles() here.)

Resets the CPU (bus -RESET low while clocking, then released: the CPU card's IC5 one-shot starts it running), steps
the clock and prints one line per machine cycle: the 16-bit address (high byte at TPA, low byte after it), the data at
TPB, R (-MRD low) / W (-MRW low) / - , N, Q and whether -VMA was asserted. With --compare the emulator (s5emu --hw,
the same cards from their netlists) runs the same number of cycles from reset and the first difference is shown.
"""
import argparse, gzip, os, sys, time, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import s5busdrv as S


def bits(ua, ub, va, vb, wa=None, wb=None):
    """the GPIO ports of a trace line as bus signals. BUSDRV-C's lines carry U3's two ports as well: the 36-pin
    extension (wa) and the DEBUG cable's CLOCK, SC0, SC1 (wb); sc = the state code SC1 SC0 (0 fetch, 1 execute, 2 DMA,
    3 interrupt), SC0 from the bus and SC1 from the cable"""
    s = dict(d=(ua & 0x7F) | ((va & 1) << 7), a=(ub & 0x7F) | ((va & 2) << 6), tpa=va >> 2 & 1, tpb=va >> 3 & 1,
             mrd=va >> 4 & 1, mrw=va >> 5 & 1, vma=va >> 6 & 1, q=vb & 1, rst=vb >> 1 & 1, n=vb >> 4 & 7)
    if wa is not None and wb is not None:
        s.update(ef1=wa & 1, ef2=wa >> 1 & 1, ef3=wa >> 2 & 1, pause=wa >> 3 & 1, dmain=wa >> 4 & 1,
                 sc=(wb >> 2 & 1) << 1 | (wa >> 5 & 1))
    return s


def cycles(states):
    """states: [(edge, dict)] changes only. A machine cycle starts when TPA rises; its address high byte is A while
    TPA is high, the low byte A after TPA falls; data, strobes and N are taken while TPB is high (the last such state)."""
    out = []; cur = None
    prev = None
    for e, s in states:
        if s["tpa"] and not (prev and prev["tpa"]):
            if cur: out.append(cur)
            cur = dict(edge=e, hi=s["a"], lo=None, d=None, rd=0, wr=0, n=0, q=s["q"], vma=0)
        if cur is not None:
            if s["tpa"]: cur["hi"] = s["a"]
            if not s["vma"]: cur["vma"] = 1
            if s["tpb"]: cur.update(d=s["d"], n=s["n"], q=s["q"], lo=s["a"])
            if s["tpb"] and "sc" in s: cur["sc"] = s["sc"]
            if not s["mrd"] and not s["tpa"]: cur["rd"] = 1
            if not s["mrw"]:                    # the 1802 raises MWR while TPB is still high (timing finding T2), and the
                cur["wr"] = 1                   # 6845 then drives the bus for the rest of TPB: a write's data is what
                if s["tpb"] or cur.get("wd") is None: cur["wd"] = s["d"]   # was there while -MRW was low
        prev = s
    if cur and cur["d"] is not None: out.append(cur)
    for c in out:
        if c["wr"] and c.get("wd") is not None: c["d"] = c["wd"]
    return out


def fmt(c):
    kind = "W" if c["wr"] else "R" if c["rd"] else "-"
    return "%04X %s %02X N%d Q%d%s%s" % ((c["hi"] << 8) | (c["lo"] or 0), kind, c["d"], c["n"], c["q"], " VMA" if c["vma"] else "",
                                       " S%d" % c["sc"] if "sc" in c else "")


def run_card(bd, edges, reset=True):
    if reset:
        bd.cmd("-RESET", 1); time.sleep(0.05)
        if "-RESET=0" not in bd.snap(): raise S.CardError("-RESET did not go low")
        bd.ser.reset_input_buffer(); bd.ser.write(b"CLK:48#"); bd.wait_prompt(30)
        bd.cmd("-RESET", 0); time.sleep(0.3)          # the IC5 one-shot (-RUN) after -RESET rises
    states = []; left = edges; base = 0
    while left > 0:
        k = min(left, 20000)
        bd.ser.reset_input_buffer(); bd.ser.write(("CLK:%d#" % k).encode()); lines = bd.wait_prompt(30 + k / 50)
        for l in lines:
            if l.startswith("T "):
                _, e, *h = l.split(); states.append((base + int(e), bits(*[int(x, 16) for x in h])))
            elif l.startswith("Error"): raise S.CardError(l)
        base += k; left -= k
    return states


def run_emu(ncycles, jumpers="----------------", video=True, ide=False, io=False, max_ins=2_000_000, mem_rom=None, rom_base=0x8000):
    """the emulator's memory and I/O cycles from reset: [(kind, addr, data, n)], kind R W O (OUT) I (INP).
    The emulator works by instruction, so only cycles that touch the bus are listed (no execute-only cycles)."""
    sys.path.insert(0, os.path.join(HERE, "..", "s5emu")); cwd = os.getcwd(); os.chdir(os.path.join(HERE, "..", "s5emu"))
    try:
        import contextlib, io as _io
        from s5emu.hw import HWMachine
        from s5emu.__main__ import DEF_ROM, parse_jumpers
        with contextlib.redirect_stderr(_io.StringIO()):
            m = HWMachine(mem_rev="D", vma_mode="remap", cpu_rev="A-built", video_rev="B" if video else None,
                          ide_rev="A" if ide else None, io_rev="A" if io else None,
                          cpu_rom=DEF_ROM, rom_base=0xF000, jumpers=parse_jumpers(jumpers), disk=None, pixie_port=4)
    finally:
        os.chdir(cwd)
    if mem_rom:                                          # the memory card's EPROM, programmed as the bus sees it
        img = open(mem_rom, "rb").read()
        for i, v in enumerate(img):
            if rom_base + i < 0x10000: m.memory.program(rom_base + i, v)
    log = []
    f0, r0, w0, o0, i0 = m.fetch, m.read, m.write, m.out, m.inp
    m.fetch = lambda a: (lambda v: (log.append(("R", a, v, 0)), v)[1])(f0(a))
    m.read = lambda a: (lambda v: (log.append(("R", a, v, 0)), v)[1])(r0(a))
    m.write = lambda a, v: (log.append(("W", a, v, 0)), w0(a, v))[1]
    def out(n, v):
        if log and log[-1][0] == "R": k, a, d, _ = log.pop(); log.append(("O", a, d, n))
        return o0(n, v)
    def inp(n):
        v = i0(n); log.append(("I", None, v, n)); return v
    m.out, m.inp = out, inp
    m.reset() if hasattr(m, "reset") else m.cpu.reset()
    k = 0
    while len(log) < ncycles and k < max_ins: m.cpu.step(); k += 1
    # an INP writes the byte to memory: the emulator logs I then W; on the bus it is one cycle (-MRW low, N set)
    out_l = []
    for e in log:
        if e[0] == "W" and out_l and out_l[-1][0] == "I" and out_l[-1][1] is None:
            out_l[-1] = ("I", e[1], e[2], out_l[-1][3]); continue
        out_l.append(e)
    return out_l


def card_bus_cycles(cy):
    """the card's cycles that touch the bus, in the emulator's terms"""
    out = []
    for c in cy:
        a = (c["hi"] << 8) | (c["lo"] or 0)
        if c["wr"]: out.append(("I" if c["n"] else "W", a, c["d"], c["n"]))
        elif c["rd"]: out.append(("O" if c["n"] else "R", a, c["d"], c["n"]))
    return out


def same(c, e):
    """address, kind and N must agree; data too, except for reads of addresses nothing answers (a floating bus)"""
    if c[0] != e[0] or c[1] != e[1] or c[3] != e[3]: return False
    if c[0] == "R" and not (0xF000 <= c[1] or 0x7000 <= c[1] < 0x8000): return True
    return c[2] == e[2]


def compare(card, emu, window=6):
    """find where the card's first cycles sit in the emulator's run (the card may not start at reset), then compare.
    The emulator logs only the reads an instruction uses; the 1802 also reads in some execute cycles whose data it
    throws away (IRX: -MRD low with R(X) on the bus). A card read the emulator lacks is skipped and listed when the
    next cycles line up again. Returns (start, index of the first real difference or None, cycles matched, skipped)."""
    start = next((i for i in range(len(emu) - window) if all(same(card[j], emu[i + j]) for j in range(window))), None)
    if start is None: return None, None, 0, []
    n = 0; k = start; skipped = []
    for j, c in enumerate(card):
        if k >= len(emu): break
        if not same(c, emu[k]):
            if c[0] == "R" and all(j + 1 + i < len(card) and k + i < len(emu) and same(card[j + 1 + i], emu[k + i])
                                   for i in range(window)):
                skipped.append(j); continue
            return start, j, n, skipped
        n += 1; k += 1
    return start, None, n, skipped


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port"); ap.add_argument("--cycles", type=int, default=40)
    ap.add_argument("--no-reset", action="store_true"); ap.add_argument("--save")
    ap.add_argument("--raw", action="store_true", help="print every bus change, not machine cycles")
    ap.add_argument("--compare", action="store_true", help="compare with the emulator (CPU + 6845 cards, nothing else)")
    ap.add_argument("--quiet", action="store_true", help="with --compare: print only the result")
    ap.add_argument("--jumpers", default="----------------", help="memory card jumpers for the emulator, e.g. RRRRRRR-EEEEEEE- (default: no memory card)")
    ap.add_argument("--mem-rom", help="the memory card's EPROM image for the emulator (bus address --mem-rom-base)")
    ap.add_argument("--mem-rom-base", default="8000")
    ap.add_argument("--from-raw", help="decode a saved raw trace (FILE.raw from --save) instead of the card")
    a = ap.parse_args()
    if a.from_raw:
        st = []
        for l in (gzip.open if a.from_raw.endswith(".gz") else open)(a.from_raw, "rt"):
            e, *h = l.split(); st.append((int(e), bits(*[int(x, 16) for x in h])))
    else:
        bd = S.BusDriver(a.port or S.find_port())
        if not any("clk-" in l for l in bd.banner): sys.exit("bus driver firmware has no CLK command: upload clk-1 or later")
        st = run_card(bd, a.cycles * 16 + 32, reset=not a.no_reset)
        if a.save:
            with open(a.save + ".raw", "w") as fh:
                for e, x in st:
                    ua = (x["d"] & 0x7F); ub = (x["a"] & 0x7F)
                    va = (x["d"] >> 7) | (x["a"] >> 7) << 1 | x["tpa"] << 2 | x["tpb"] << 3 | x["mrd"] << 4 | x["mrw"] << 5 | x["vma"] << 6
                    vb = x["q"] | x["rst"] << 1 | x["n"] << 4
                    fh.write("%d %02X %02X %02X %02X\n" % (e, ua, ub, va, vb))
    if a.raw:
        for e, s in st: print(e, " ".join("%s=%X" % kv for kv in s.items()))
    cy = cycles(st)
    lines = [fmt(c) for c in cy]
    if not a.quiet: print("\n".join(lines))
    if a.compare:
        card = card_bus_cycles(cy); emu = run_emu(len(card) * 4 + 20000, jumpers=a.jumpers, mem_rom=a.mem_rom, rom_base=int(a.mem_rom_base, 16))
        start, bad, n, skipped = compare(card, emu)
        f = lambda e: "%s %s %02X N%d" % (e[0], "%04X" % e[1] if e[1] is not None else "----", e[2], e[3])
        if skipped:
            print("COMPARE: %d dummy read(s) on the card that the emulator does not log, skipped: %s" % (len(skipped),
                  ", ".join("%04X" % card[j][1] for j in skipped[:8]) + (" ..." if len(skipped) > 8 else "")))
        if start is None: print("COMPARE: the card's first cycles are not in the emulator's first %d cycles from reset" % len(emu))
        elif bad is None: print("COMPARE: MATCH - %d bus cycles agree with the emulator (from its cycle %d after reset)" % (n, start))
        else:
            print("COMPARE: %d bus cycles agree (from emulator cycle %d), then:" % (n, start))
            print("   card     %s" % f(card[bad])); print("   emulator %s" % f(emu[start + bad - len(skipped)]))
    if a.save:
        with open(a.save, "w") as fh: fh.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
