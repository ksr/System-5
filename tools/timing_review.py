#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-07
"""System-5 static timing review: the bus paths of the built cards checked against the CDP1802A's bus timing.

usage: timing_review.py [MHz ...]     (default: 1.76, the usual 3.52 MHz crystal / 2; the actual crystal is unread)

See also: python3 -m s5emu.timing (from software/s5emu), the same checks computed from the netlists.

Every check is worst case: the 1802's maximum delays (and, where the datasheet gives no minimum, the typical value as
the fast bound - marked), each part's maximum propagation delay, and the slower of its two edges. Times are in ns from
the clock edge that starts the machine cycle ("00"); T = clock period. hardware/TIMING-REVIEW.md explains each check.

1802 timing: ../private-resources/elf/reference/datasheets/cdp1802.pdf (Intersil CDP1802A, VCC = VDD = 5 V, CL = 50 pF), pages 6-10 and the
edge positions in Figure 4. Part delays: the PARTS table; each entry names its datasheet. They were typed in from
those datasheets' published maxima, not read from copies in ../private-resources/elf/reference/, so check them when the datasheets are added.
"""
import sys

# The 1802 timing (CPU) and part delays (PARTS) are shared with the automated analysis in software/s5emu/s5emu/timing.py,
# which derives the paths from the netlists; this script keeps the hand-written paths as a cross-check.
sys.path.insert(0, __import__("os").path.join(__import__("os").path.dirname(__import__("os").path.abspath(__file__)), "..", "software", "s5emu"))
from s5emu.timing import CPU, PARTS                                     # noqa: E402


def P(name, key): return PARTS[name][key]


def checks(f_mhz):
    """-> [(card, check, budget ns, needed ns, note)]: margin = budget - needed"""
    T = 1000.0 / f_mhz; c = CPU; out = []
    tpa_rise_max, tpa_rise_fast = 1.0 * T + c["tpa_max"], 1.0 * T + c["tpa_typ"]
    tpa_fall_max, tpa_fall_fast = 2.0 * T + c["tpa_max"], 2.0 * T + c["tpa_typ"]
    tpb_rise_fast = 6.5 * T + c["tpa_typ"]
    tpb_fall_fast, tpb_fall_max = 7.5 * T + c["tpa_typ"], 7.5 * T + c["tpa_max"]
    lo = 2.5 * T + c["lo_addr_max"]
    latch_in = 7.5 * T - c["din_setup"]                          # data must be on the bus by here
    mwr_rise_max = 7.0 * T + c["mwr_max"]

    # ---- CPU card
    setup = tpa_rise_fast - c["hi_addr_max"]
    out.append(("CPU", "74LS374 latches the high address on TPA's RISING edge: setup", setup, P("74LS374", "setup"),
                "datasheet guarantees setup only to TPA's falling edge (2T-550 = %.0f ns); typical 1802: %.0f ns"
                % (2 * T - 550, tpa_rise_fast - c["hi_addr_typ"])))
    out.append(("CPU", "the same, if the 374 were clocked on TPA's falling edge (inverted TPA)",
                tpa_fall_fast - c["hi_addr_max"] - P("74LS04", "tpd"), P("74LS374", "setup"), "a spare 74LS04/00 gate"))
    vma = tpa_rise_max + P("74LS374", "clk_q") + P("74LS138", "sel") + P("74LS00", "tpd")
    out.append(("CPU", "-VMA settled (374 -> 138 -> 7400) before the low address (memory card)", lo, vma,
                "-VMA is valid early in every cycle"))
    eprom = max(vma + P("74LS05", "tpd_hl"), lo) + P("2732A-30", "taa")
    out.append(("CPU", "boot EPROM read: data on the bus before the 1802 latches it", latch_in, eprom, "2732A-30"))

    # ---- memory Rev D (card of record)
    out.append(("memory D", "CD4042B latches the high address on TPA's falling edge: setup (through a CD4050B)",
                (2 * T - 550) - P("CD4050B", "tpd"), P("CD4042B", "setup"), "datasheet setup 2T-550 less the buffer"))
    out.append(("memory D", "CD4042B hold after TPA falls", (T / 2 - 25) + P("CD4050B", "tpd_min"), P("CD4042B", "hold"),
                "datasheet hold T/2-25 plus the buffer's minimum delay"))
    hi_q = max(c["hi_addr_max"] + P("CD4050B", "tpd") + P("CD4042B", "d_q"), tpa_rise_max + P("CD4042B", "clk_q"))
    ce = max(hi_q + P("74LS151", "sel"), vma + P("74LS32", "tpd")) + P("74LS32", "tpd")
    for chip in ("62256-70", "27C256-20"):
        data = max(lo + P("CD4050B", "tpd") + P(chip, "taa"), ce + P(chip, "tace"),
                   1.5 * T + c["mrd_max"] + P("CD4050B", "tpd") + P(chip, "toe"))
        out.append(("memory D", "%s read: data on the bus before the 1802 latches it" % chip, latch_in, data, ""))
    out.append(("memory D", "62256 write: data set up before WE rises (WE = -MWR through a CD4050B)",
                mwr_rise_max + P("CD4050B", "tpd_min"), 2.0 * T + c["data_out_max"] + P("62256-70", "tdw"), ""))
    out.append(("memory D", "62256 write: low address held after WE rises",
                mwr_rise_max + (T - 30) + P("CD4050B", "tpd_min"), mwr_rise_max + P("CD4050B", "tpd"),
                "datasheet low-address hold T-30 after MWR"))

    # ---- 6845 card
    out.append(("6845 A", "74LS373 latches the high address on TPA's falling edge: setup", 2 * T - 550,
                P("74LS373", "setup"), ""))
    cs = max(c["hi_addr_max"] + P("74LS373", "d_q"), tpa_rise_max + P("74LS373", "le_q")) + P("74LS85", "tpd") + P("74LS00", "tpd")
    out.append(("6845 A", "6845 CS and RS set up before E (= TPB) rises", tpb_rise_fast - max(cs, lo), P("MC6845", "tas"), ""))
    out.append(("6845 A", "6845 E high time (= TPB width, worst skew)", T - (c["tpa_max"] - c["tpa_typ"]), P("MC6845", "e_high"), ""))
    out.append(("6845 A", "6845 register write: R/W (= -MWR) held low until E (= TPB) falls",
                (7.0 * T + c["tpa_typ"]) - (tpb_fall_max + P("MC6845", "tah")), 0,
                "MWR ends at 7.0 T, TPB at 7.5 T: R/W goes high while E is still high (see the review)"))
    out.append(("6845 A", "6845 register read: data set up before the 1802 latches it",
                latch_in - (6.5 * T + c["tpa_max"] + P("MC6845", "tddr")), 0, "E rises at 6.5 T (+ up to 300 ns)"))
    out.append(("6845 A", "6845 register read: data held after the 1802 latches it (E = TPB gates it; the 7134 is not)",
                c["tpa_typ"] + P("MC6845", "tdhr"), c["din_hold"],
                "TPB's fall delay has no guaranteed minimum; typical %d ns used" % c["tpa_typ"]))

    # ---- IO and IDE cards (I/O cycles)
    n_dec = c["n_max"] + P("74LS138", "sel")
    out.append(("IO A", "keyboard CDP1852 data on the bus before the 1802 latches it (INP 1)",
                latch_in, n_dec + P("74LS04", "tpd") + P("CDP1852", "cs_data"), "CS1 from the N-line decode"))
    dior_on = tpa_fall_max + 3 * P("74LS00", "tpd") + P("74LS32", "tpd")
    out.append(("IDE A", "DIOR pulse width (ATA PIO 0 needs 165 ns)", tpb_fall_fast - dior_on, P("ATA-PIO0", "dior_min"), ""))
    out.append(("IDE A", "drive data on the bus before the 1802 latches it (INP 3)", latch_in,
                dior_on + P("ATA-PIO0", "dior_data"), ""))
    out.append(("IDE A", "INP 3 into RAM: drive data still there when the RAM's WE rises",
                tpb_fall_fast + 2 * P("74LS00", "tpd") + P("ATA-PIO0", "dior_hold"), mwr_rise_max + P("CD4050B", "tpd"),
                "DIOR ends at TPB's fall; WE = MWR through a CD4050B; bus capacitance helps"))
    return out


def main(argv):
    for f in [float(a) for a in argv] or [1.76]:
        print("\n=== clock %.3f MHz (T = %.0f ns, machine cycle %.2f us)" % (f, 1000 / f, 8000 / f / 1000))
        print("%-9s %-86s %8s %8s %8s  %s" % ("card", "check", "budget", "needs", "margin", "verdict"))
        for card, what, budget, need, note in checks(f):
            m = budget - need
            v = "OK" if m >= 50 else "MARGINAL" if m >= 0 else "FAILS (worst case)"
            print("%-9s %-86s %8.0f %8.0f %8.0f  %s%s" % (card, what[:86], budget, need, m, v, ("  - " + note) if note else ""))


if __name__ == "__main__":
    main(sys.argv[1:])
