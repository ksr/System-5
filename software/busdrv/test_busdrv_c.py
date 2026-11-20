#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-20
"""Tests for BUSDRV-C: the firmware's Rev C commands (fwsim.py, the sketch in Python) on the simulated 36-pin
backplane (backplane.Backplane36: the bus Rev D, a memory card from its netlist, CPU Rev D's gates from its netlist
and the 1802 as cpupins.Pins1802, one clock edge at a time), the host tool and the two Rev C bring-up plans.

  Pins     the 1802 pin model against the real 1802: the clock-stepped trace of CPU Rev A of 2026-10-31
  Commands every new command against the simulator
  Load     LOAD mode by the clock: bytes into RAM once each with no fight on D0-D7, then RUN executing them
  Faults   what the firmware says, and never does, when the cable is off, JP1 is wrong or -DMAIN is stuck; and the
           simulator catching a firmware that does a LOAD step wrongly
  RevB     BUSDRV-B: every Rev C command refused, everything else as before
  Plans    bringup.py bus36 and load, healthy and with each fault

Run: python3 test_busdrv_c.py   (under a minute)"""
import argparse, contextlib, glob, gzip, io, os, sys, tempfile, unittest
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import s5busdrv as S, bringup as B, cputrace                                   # noqa: E402
from backplane import Backplane, Backplane36                                   # noqa: E402
from fwsim import FwCard, C_COMMANDS                                           # noqa: E402
from cpupins import Pins1802                                                   # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
JUMPERS = "RR------E-------"                    # two RAM blocks and an EPROM block: enough, and quick to build

# a program for LOAD mode: 0300-030F = 80..8F, Q on, idle
PROG = bytes([0xF8, 0x03, 0xB1, 0xF8, 0x00, 0xA1, 0xF8, 0x10, 0xA2,      # R1 = 0300; R2.0 = 16
              0x81, 0xF9, 0x80, 0x51, 0x11, 0x22, 0x82, 0x3A, 0x09,      # GLO 1; ORI 80; STR 1; INC 1; DEC 2; GLO 2; BNZ
              0x7B, 0x00])                                               # SEQ; IDL
IMAGE = PROG + bytes((100 + 7 * i) & 0xFF for i in range(300 - len(PROG)))     # 300 bytes: the program, then a pattern


def card(rev="C", fw=None, **kw):
    """-> (BusDriver, Backplane36, FwCard)"""
    kw.setdefault("jumpers", JUMPERS)
    bp = Backplane36(cards=("mem",), **kw); fc = FwCard(bp, rev=rev, **(fw or {}))
    return S.BusDriver(transport=fc), bp, fc


def err(test, bd, op, operand=0):
    """the card's error text for a command it must refuse"""
    with test.assertRaises(S.CardError) as cm: bd.cmd(op, operand)
    return str(cm.exception)


class Pins(unittest.TestCase):
    def test_against_the_real_1802(self):
        """the model, given the data bus the real 1802 had, makes the same TPA, TPB, -MRD, -MRW, N, Q and address bytes
        on every clock edge of the first 6,000 machine cycles of the 2026-10-31 trace (HBIOS from power-on, CPU Rev A).
        A register the program has not loaded yet holds what the real chip powered up with: its bytes are taken from
        the trace the first time they show on the address lines in a cycle with no strobe."""
        raw = glob.glob(os.path.join(ROOT, "hardware", "cpu", "eagle", "rev-a", "bringup", "*.raw.gz"))[0]
        st = []
        with gzip.open(raw, "rt") as fh:
            for l in fh:
                e, *h = l.split(); st.append((int(e), cputrace.bits(*[int(x, 16) for x in h])))
                if int(e) > 17 + 6000 * 16: break
        per = {}; k = 0; cur = None
        for e in range(st[0][0], st[-1][0]):
            while k < len(st) and st[k][0] == e: cur = st[k][1]; k += 1
            per[e] = cur
        p = Pins1802(); p.set_mode(1, 1); p.init = 0; p.D = None           # RUN, the initialization cycle over
        seeded = set(); kinds = set(); bad = []
        for i in range(6000 * 16):
            e = 17 + i                                                     # the fetch at 0000 starts at trace edge 17
            p.edge(dma_in=1, dbus=per[e - 1]["d"]); o = p.outputs(); r = per[e]; kind = p.cyc["kind"]; ee = i % 16
            kinds.add(kind)
            if kind == "none" and o["A"] != r["a"] and ee in (0, 5):
                n = p.opcode & 15; half = ee == 0
                if (n, half) not in seeded:
                    seeded.add((n, half)); reg = p.core.R[n]
                    reg = (reg & 0x00FF) | (r["a"] << 8) if half else (reg & 0xFF00) | r["a"]
                    p.core.R[n] = reg; p.snap["R"][n] = reg; p.done = None; p._work_out()
                    p.cyc["addr"] = reg; p.A = r["a"]; o = p.outputs()
            got = (o["TPA"], o["TPB"], o["MRD"], o["MRW"], o["A"], o["N"], o["Q"])
            if got != (r["tpa"], r["tpb"], r["mrd"], r["mrw"], r["a"], r["n"], r["q"]): bad.append((e, ee, kind, got, r))
        self.assertEqual(bad[:3], [])
        self.assertEqual(kinds, {"fetch", "read", "write", "none"})
        self.assertLess(len(seeded), 24)

    def test_the_cycle_edge_by_edge(self):
        """a fetch, a write and a DMA IN cycle: which edge moves which pin (the table in cpupins.py)"""
        p = Pins1802(); p.set_mode(1, 1)
        seen = []
        for i in range(18 + 16 * 3):                                     # the initialization cycle, then 5F: STR RF
            p.edge(dma_in=1, dbus=0x5F); o = p.outputs()
            seen.append((o["TPA"], o["TPB"], o["MRD"], o["MRW"], o["SC1"], o["SC0"], o["D"]))
        init = seen[2:18]; fetch = seen[18:34]; write = seen[34:50]
        self.assertEqual([i for i, s in enumerate(init) if s[0]], [2, 3])              # TPA in the initialization cycle too
        self.assertTrue(all(s[2] == 1 and s[3] == 1 for s in init))                    # and no strobe
        self.assertEqual([i for i, s in enumerate(fetch) if s[0]], [2, 3])             # TPA: 1.0 T to 2.0 T
        self.assertEqual([i for i, s in enumerate(fetch) if s[1]], [13, 14])           # TPB: 6.5 T to 7.5 T
        self.assertEqual([i for i, s in enumerate(fetch) if not s[2]], list(range(3, 16)))   # -MRD low from 1.5 T
        self.assertEqual({(s[4], s[5]) for s in fetch}, {(0, 0)})                      # S0
        self.assertEqual([i for i, s in enumerate(write) if not s[3]], [10, 11, 12, 13])     # -MRW: 5.0 T to 7.0 T
        self.assertTrue(all(s[2] == 1 for s in write))                                 # -MRD high in a write
        self.assertEqual([i for i, s in enumerate(write) if s[6] is not None], list(range(4, 16)))   # its data from 2.0 T
        # LOAD mode: idle cycles (S1, a read of M(R(0))); a request makes the next cycle S2 with -MRW and no -MRD
        p = Pins1802(); p.set_mode(0, 0); kinds = []
        for i in range(18 + 16 * 4):
            p.edge(dma_in=0 if 18 + 16 <= i < 18 + 32 else 1, dbus=0xEE)
        self.assertEqual([c[0] for c in p.cycles], ["init", "idle", "idle", "dma", "idle"])
        self.assertEqual(p.core.R[0], 1)                                               # one byte, R(0) + 1

    def test_pause_and_reset(self):
        p = Pins1802(); p.set_mode(1, 1)
        for i in range(40): p.edge(dbus=0xC4)                                          # NOPs
        before = p.outputs(); p.set_mode(1, 0)                                         # PAUSE: every pin holds
        for i in range(64): p.edge(dbus=0xC4)
        self.assertEqual(p.outputs(), before)
        n = len(p.cycles); p.set_mode(1, 1)
        for i in range(16): p.edge(dbus=0xC4)
        self.assertEqual(len(p.cycles), n + 1)                                         # RUN again: it goes on where it stood
        p.set_mode(0, 1); o = p.outputs()                                              # RESET: no TPA / TPB, 00 on the bus
        self.assertEqual((o["TPA"], o["TPB"], o["MRD"], o["MRW"], o["D"], o["SC1"], o["SC0"]), (0, 0, 1, 1, 0, 0, 1))
        for i in range(64): p.edge(dbus=0xC4)
        self.assertEqual(p.outputs(), o)


class Commands(unittest.TestCase):
    def test_banner_status_snap(self):
        bd, bp, fc = card()
        self.assertEqual(bd.rev, "C"); self.assertTrue(bd.ioblocks)
        for word in ("clk-2", "ext-1", "mode-1", "load-1", "probe-1", "BUSDRV-C"): self.assertIn(word, bd.banner[0])
        self.assertEqual(bd.status(), "bus=on mode=MONITOR board=C cpu=RUN clk=0")
        f = bd.fields(bd.snap())
        self.assertEqual([f[k] for k in ("-EF1", "-EF2", "-EF3", "-PAUSE", "-DMAIN", "SC0")], ["1"] * 6)

    def test_extension_lines(self):
        """each open-collector line of the extension: pulled low and let go; the 1802's EF pins follow the jumpers"""
        bd, bp, fc = card()
        for name in ("-EF1", "-EF2", "-EF3", "-PAUSE", "-DMAIN"):
            bd.line(name, True); f = bd.fields(bd.snap())
            self.assertEqual({k: f[k] for k in ("-EF1", "-EF2", "-EF3", "-PAUSE", "-DMAIN")},
                             {k: "0" if k == name else "1" for k in ("-EF1", "-EF2", "-EF3", "-PAUSE", "-DMAIN")})
            if name == "-EF1": self.assertTrue(bp.cpu.pins.ef(1)); self.assertFalse(bp.cpu.pins.ef(2))   # JP2: -EF1 on EF1
            bd.line(name, False)
        self.assertFalse(bp.cpu.pins.ef(1))
        err(self, bd, "SC0", 0)                                                        # SC0 is read only: no such command

    def test_modes_never_both_low_but_for_load(self):
        """RUN, RESET, PAUSE in every order: -RESET and -PAUSE are never low together, so LOADED stays clear; LOAD sets it"""
        bd, bp, fc = card(); pairs = []
        seen = bp.set_pins
        def spy(pins, d): pairs.append((pins.get("RESET"), pins.get("PAUSE"))); seen(pins, d)
        bp.set_pins = spy
        for a in ("run", "reset", "pause"):
            for b in ("run", "reset", "pause"):
                bd.mode(a); bd.mode(b); self.assertEqual(bd.cpu_mode(), b.upper())
        self.assertNotIn((0, 0), pairs); self.assertFalse(bp.cpu.loaded())
        bd.mode("load"); self.assertEqual(bd.cpu_mode(), "LOAD"); self.assertTrue(bp.cpu.loaded())
        i = pairs.index((0, 0)); self.assertEqual(pairs[i - 1], (0, None))             # through RESET, so R(0) = 0000
        bd.mode("run"); self.assertEqual(bd.cpu_mode(), "RUN"); self.assertTrue(bp.cpu.loaded())   # a bus reset keeps it
        self.assertIn("MODE 0 RUN", err(self, bd, "MODE", 4))

    def test_pause_waits_for_reset_to_be_high(self):
        """the CPU card's DS1813 holds -RESET low after the bus driver lets it go. -PAUSE pulled then makes LOAD mode
        and sets LOADED: by hand it does. MODE waits to see -RESET high on the bus first, and gives up if it never is"""
        bd, bp, fc = card(reset_stretch=40)
        bd.line("-RESET", True); bd.line("-RESET", False); self.assertEqual(bp.pins["RESET"], 0)   # let go, still low
        bd.line("-PAUSE", True); self.assertTrue(bp.cpu.loaded())                      # by hand: that was LOAD
        bd, bp, fc = card(reset_stretch=40); both = []
        seen = bp._resolve
        def spy(): seen(); both.append((bp.pins["RESET"], bp.pins["PAUSE"]))
        bp._resolve = spy
        bd.mode("reset"); bd.mode("pause")
        self.assertIn((0, 1), both); self.assertNotIn((0, 0), both); self.assertFalse(bp.cpu.loaded())
        self.assertEqual(bd.cpu_mode(), "PAUSE")
        bd, bp, fc = card(stuck_lines={"RESET": 0})                                    # the CPU card's switch on RESET
        self.assertIn("-RESET stays low", err(self, bd, "MODE", 2)); self.assertFalse(bp.cpu.loaded())
        self.assertEqual(bp.pins["PAUSE"], 1)

    def test_master_refused_with_a_cpu_card(self):
        bd, bp, fc = card()
        self.assertIn("a CPU card answers on the DEBUG cable", err(self, bd, "MASTER", 1))
        self.assertEqual(bp.fights(), [])
        bd, bp, fc = card(cpu=False)                                                   # the CPU card out: as BUSDRV-B
        bd.master(True); bd.write(0x0100, b"\x12\x34\x56"); self.assertEqual(bd.read(0x0100, 3), b"\x12\x34\x56")
        self.assertIn("MODE is for a CPU card in place", err(self, bd, "MODE", 3))
        self.assertIn("LOAD mode is for a CPU card in place", err(self, bd, "LOADBLK", "1,00"))
        bd.master(False); bd.cmd("CLKHZ", 1000)
        self.assertIn("the clock is running", err(self, bd, "MASTER", 1))

    def test_dbg(self):
        bd, bp, fc = card()
        self.assertEqual(set(bd.dbg()), {"CLOCK", "SC0", "SC1"}); self.assertEqual(bd.clock_test(), "CLK OUT reaches the 1802")
        bd, bp, fc = card(cable=False)
        self.assertEqual(bd.dbg(), {"CLOCK": "1", "SC0": "1", "SC1": "1"})             # pulled up: no cable reads 111
        self.assertIn("CLK OUT does not reach the 1802", err(self, bd, "DBG", 1))

    def test_clk_steps_and_traces(self):
        """CLK:n on BUSDRV-C: every edge a change of CLK OUT; the trace decodes to machine cycles with the state code"""
        bd, bp, fc = card(cpu_rom=bytes([0x7B, 0x30, 0x01]) + bytes([0xFF] * 4093))    # SEQ; BR 01
        bd.mode("reset"); bd.mode("run")
        n0 = bp.cpu.edges; st = bd.clk(18 + 16 * 6); self.assertEqual(bp.cpu.edges - n0, 18 + 16 * 6)
        self.assertTrue(all(len(h) == 6 for e, h in st))
        cy = cputrace.cycles([(e, cputrace.bits(*h)) for e, h in st])
        self.assertEqual([cputrace.fmt(c) for c in cy][1:6],                           # (the first is the initialization cycle)
                         ["0000 R 7B N0 Q0 S0", "0000 - FF N0 Q0 S1", "0001 R 30 N0 Q1 S0", "0002 R 01 N0 Q1 S1", "0001 R 30 N0 Q1 S0"])
        #                  (SEQ's execute cycle uses no memory: R(B) = 0000 on the address lines, nothing on the data lines)
        self.assertIn("MONITOR mode", err(self, card(cpu=False)[0], "RDMEM", 0))

    def test_clock_rate(self):
        bd, bp, fc = card()
        self.assertEqual([bd.clk_hz(h) for h in (2000000, 1000000, 1, 3, 440)], [2000000, 1000000, 1, 3, 440])
        self.assertEqual(bd.clk_hz(1500000), 1600000)                                  # 8 MHz / 5: the nearest Timer 1 has
        self.assertEqual(bd.fields(bd.status())["clk"], "1600000")
        self.assertIn("CLKHZ 1..2000000", err(self, bd, "CLKHZ", 3000000))
        n = bp.cpu.edges; bd.status(); self.assertGreater(bp.cpu.edges, n)             # it runs between commands
        bd.clk_stop(); n = bp.cpu.edges; bd.status(); self.assertEqual(bp.cpu.edges, n)
        self.assertEqual(bd.fields(bd.status())["clk"], "0")

    def test_spares(self):
        bd, bp, fc = card()
        bd.cmd("SPARE", 0b11000001111); self.assertEqual([fc.fw.olat[c][p] >> 7 for c in range(3) for p in range(2)], [1] * 6)
        self.assertEqual(int(bd.cmd("SPIN")[0]), 0x1F)                                 # inputs, nothing on them
        bd.cmd("SPDIR", 0x1F); bd.cmd("SPARE", 0b00101010000); self.assertEqual(int(bd.cmd("SPIN")[0]), 0b10101)
        bd.cmd("XRST"); self.assertEqual(int(bd.cmd("SPIN")[0]), 0x1F)

    def test_probes(self):
        bd, bp, fc = card(); bp.probe[1] = "CLK_OUT"; bp.probe[2] = "TPA"
        self.assertEqual(bd.probe(), {"P1": 0, "P2": 0})
        bd.mode("reset"); bd.mode("run"); bd.cmd("CLKHZ", 100000)
        c = bd.pcount(10); self.assertGreater(c["P1"], 100); self.assertEqual(c["P1"] // c["P2"], 8)   # 16 clock edges to 2 of TPA
        self.assertIn("Timer 1 is making the clock", err(self, bd, "PTIME", 100))
        self.assertIn("Timer 1 is making the clock", err(self, bd, "PDELAY", 1))
        bd.clk_stop(); level = bp.clk_out
        self.assertEqual(bd.pdelay(not level), 0)                                      # PROBE1 on CLK OUT: the edge itself
        self.assertIn("no such edge", err(self, bd, "PDELAY", 1 if bp.clk_out else 0))
        self.assertIn("PCOUNT 1..10000", err(self, bd, "PCOUNT", 0))

    def test_dma_one_byte(self):
        bd, bp, fc = card()
        self.assertIn("not in LOAD mode", err(self, bd, "DMA", 0x5A))
        bd.mode("load")
        self.assertEqual([bd.dma(0x5A), bd.dma(0xC3), bd.dma(0x00)], [0, 1, 2])
        self.assertEqual([bp.peek(a) for a in range(3)], [0x5A, 0xC3, 0x00])
        self.assertIn("value 0..255", err(self, bd, "DMA", 256))
        self.assertIn("LOADBLK:count,hh..", err(self, bd, "LOADBLK", "33," + "00" * 33))
        self.assertIn("LOADBLK:count,hh..", err(self, bd, "LOADBLK", "4,0011"))
        self.assertIn("bad hex", err(self, bd, "LOADBLK", "2,00ZZ"))
        self.assertEqual(bp.fights(), [])


class Load(unittest.TestCase):
    def load_and_run(self, **kw):
        bd, bp, fc = card(**kw); drove = []
        seen = bp.set_pins
        def spy(pins, d):
            if d is not None: drove.append((bp.pins["MRD"], bp.pins["SC0"]))           # the bus when D0-D7 are driven
            seen(pins, d)
        bp.set_pins = spy
        bd.mode("load"); first = bd.dma_load(IMAGE)
        self.assertEqual(first, 0)
        self.assertEqual(bytes(bp.peek(a) for a in range(len(IMAGE))), IMAGE)          # byte for byte
        self.assertEqual({bp.writes_at(a) for a in range(len(IMAGE))}, {1})            # each written once
        self.assertEqual(sum(bp.writes.values()), len(IMAGE))                          # and nothing else written
        self.assertEqual(bp.fights(), [])                                              # no fight on D0-D7
        self.assertEqual(set(drove), {(1, 0)})                 # the data lines driven only with -MRD high, in the DMA cycle
        self.assertTrue(bp.cpu.loaded())
        bd.mode("run"); st = bd.clk(18 + 16 * 2 * (6 + 16 * 7 + 2 + 2))                 # RUN: the program fills 0300-030F
        self.assertEqual(bytes(bp.peek(0x300 + i) for i in range(16)), bytes(range(0x80, 0x90)))
        self.assertEqual(bd.fields(bd.snap())["Q"], "1"); self.assertTrue(bp.cpu.pins.core.idle)
        self.assertEqual(bp.fights(), [])
        return bd, bp, fc

    def test_300_bytes_then_run(self): self.load_and_run()

    def test_dma_sampled_at_tpb_rising(self):
        """the same with the 1802 taking its DMA request at TPB's leading edge, the other end of the data sheet's window"""
        self.load_and_run(dma_sample=13)

    def test_a_bus_reset_keeps_the_program_and_sw1_boots_the_eprom(self):
        rom = bytes([0x7B, 0x00]) + bytes([0xFF] * 4094)                               # the "HBIOS": SEQ; IDL
        bd, bp, fc = card(cpu_rom=rom)
        bd.mode("load"); bd.dma_load(bytes([0xC4, 0xC4, 0xC4, 0x00]))                  # three NOPs, IDL: Q stays off
        bd.mode("reset"); bd.mode("run"); bd.clk(18 + 16 * 12)
        cy = [c for c in bp.cpu.pins.cycles if c[0] == "fetch"][-4:]
        self.assertEqual([(c[1], c[2]) for c in cy], [(0, 0xC4), (1, 0xC4), (2, 0xC4), (3, 0x00)])   # RAM, not the EPROM
        self.assertEqual(bp.pins["Q"], 0)
        bp.press_sw1(True); self.assertFalse(bp.cpu.loaded()); bp.press_sw1(False)     # the CPU card's RESET/RUN switch
        bd.clk(18 + 16 * 4); self.assertEqual(bp.pins["Q"], 1)                         # the EPROM at 0000: the boot map

    def test_the_host_tool(self):
        """load_image: a file that starts above 0000 gets a jump at 0000; main() runs dmaload against the simulator"""
        img = S.load_image([(0x0100, bytes([0x7B, 0x00]))])
        self.assertEqual((img[:3], len(img), img[0x100:]), (bytes([0xC0, 0x01, 0x00]), 0x102, bytes([0x7B, 0x00])))
        with self.assertRaises(SystemExit): S.load_image([(2, b"\x00")])
        bd, bp, fc = card()
        bd.mode("load"); bd.dma_load(img); bd.mode("run"); bd.clk(18 + 16 * 8)
        self.assertEqual(bp.pins["Q"], 1)                                              # LBR 0100; SEQ
        p = tempfile.mktemp(suffix=".bin")
        with open(p, "wb") as fh: fh.write(PROG)
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            S.main(["--sim", "--rev", "C", "loadrun", p, "0", "0"])
        os.remove(p)
        self.assertIn("0000-0013 20 bytes by DMA IN", out.getvalue()); self.assertIn("cpu=RUN", out.getvalue())


class Faults(unittest.TestCase):
    def refuses(self, text, **kw):
        """LOAD mode asked for, a block sent: the card says `text`, and never drives D0-D7"""
        bd, bp, fc = card(**kw); drove = []
        seen = bp.set_pins
        def spy(pins, d):
            if d is not None: drove.append(d)
            seen(pins, d)
        bp.set_pins = spy
        bd.mode("load")
        with self.assertRaises(S.CardError) as cm: bd.dma_load(IMAGE[:40])
        self.assertIn(text, str(cm.exception)); self.assertEqual(drove, [])
        return bd, bp, fc

    def test_no_debug_cable(self):
        bd, bp, fc = self.refuses("CLK OUT does not reach the 1802", cable=False)
        self.assertEqual(bp.writes, {})

    def test_jp1_on_the_cards_own_clock(self):
        bd, bp, fc = self.refuses("CLK OUT does not reach the 1802", jp1="INT")
        self.assertEqual(bp.writes, {})

    def test_dmain_stuck_low(self):
        """-DMAIN held low by something else: the 1802 makes DMA cycles by itself (the simulator shows them); the card
        sees SC0 low before it has asked, and puts no byte on the bus"""
        bd, bp, fc = self.refuses("SC0 stays low: DMA cycles with no request", stuck_lines={"DMAIN": 0})
        self.assertIn("dma", [c[0] for c in bp.cpu.pins.cycles])

    def test_dmain_not_reaching_the_cpu(self):
        bd, bp, fc = self.refuses("no DMA cycle: -DMAIN does not reach the 1802", stuck_lines={"DMAIN": 1})
        self.assertEqual(bp.writes, {})

    def test_not_in_load_mode(self):
        bd, bp, fc = card()
        for m in ("run", "reset", "pause"):
            bd.mode(m); self.assertIn("not in LOAD mode", err(self, bd, "LOADBLK", "1,AA"))
        self.assertEqual(bp.writes, {})

    def test_the_simulator_catches_dmain_held_too_long(self):
        """a firmware that lets -DMAIN go only after the DMA cycle (the first hazard in DESIGN.md): a second DMA cycle
        writes the next address too. The simulator's memory shows it, and the sketch's own check reports it."""
        bd, bp, fc = card(fw=dict(load_fault="hold-dmain")); bd.mode("load")
        self.assertIn("a second DMA cycle followed", err(self, bd, "LOADBLK", "1,5A"))
        self.assertEqual((bp.peek(0), bp.writes_at(0)), (0x5A, 1))
        fc.fw.run_clock(16)                                                            # the second cycle to its end
        self.assertEqual(bp.writes_at(1), 1); self.assertEqual(bp.peek(1), 0xFF)       # whatever was on the bus: nothing

    def test_the_simulator_catches_data_driven_too_early(self):
        """a firmware that puts the byte on D0-D7 with the request (the second hazard): it fights the memory card's
        idle-cycle read, and the simulator logs each fight"""
        bd, bp, fc = card(fw=dict(load_fault="early-data")); bd.mode("load"); bd.dma_load(IMAGE[:8])
        self.assertTrue(bp.fights()); self.assertIn("bus driver=", bp.fights()[0][2]); self.assertIn("mem IC1=", bp.fights()[0][2])


class RevB(unittest.TestCase):
    def test_rev_b_refuses_every_rev_c_command(self):
        from fwsim import SIGS
        bp = Backplane(cards=("mem",), jumpers=JUMPERS); bd = S.BusDriver(transport=FwCard(bp))
        self.assertEqual(bd.rev, "B"); self.assertIn("clk-1", bd.banner[0]); self.assertNotIn("ext-1", bd.banner[0])
        self.assertEqual(bd.status(), "bus=on mode=MONITOR")                           # as before: no board field
        for op in C_COMMANDS + tuple(n for n, s in SIGS.items() if s[0] == 2):
            self.assertIn("needs BUSDRV-C", err(self, bd, op, 1), op)
        self.assertEqual(bd.cmd("CLK", 16), ["16"])                                    # clk-1: SPARE1, as it was
        bd.master(True); bd.write(0x0040, b"\xA5\x5A"); self.assertEqual(bd.read(0x0040, 2), b"\xA5\x5A")
        self.assertEqual(len(bd.fields(bd.snap())), 13)                                # SNAP: the thirteen fields of BUSDRV-B
        self.assertEqual(bp.fights(), [])

    def test_an_open_collector_line_is_let_go_in_monitor_mode(self):
        """-RESET pulled and released without ever being master: the release reaches the bus (it did not before
        2026-11-20: with every pin an input again the simulated card skipped the write)"""
        bp = Backplane(cards=("mem",), jumpers=JUMPERS); bd = S.BusDriver(transport=FwCard(bp))
        bd.cmd("-RESET", 1); self.assertEqual(bp.pins["RESET"], 0)
        bd.cmd("-RESET", 0); self.assertIsNone(bp.pins["RESET"])


def plan(name, *faults, busdrv="B"):
    a = argparse.Namespace(plan=name, port=None, log=False, sim=True, fault=list(faults) or None, jumpers=JUMPERS, full=False,
                           rom=None, rom_base=0x8000, save_rom=None, ide_sel=2, ide_data=3, image=None, sectors=1,
                           cf_write_lba=None, video_base=0x7000, interactive=False, keep=False, report=None, mem_rev="D",
                           busdrv=busdrv)
    bd, bp = B.sim_driver(a); out = io.StringIO()
    b = B.Bringup(bd, a, out=lambda s: out.write(s + "\n")); b.plan(name); b.summary()
    return b, bp, out.getvalue()


def status(b): return {s.code: s.status for s in b.steps}
def text(b, code): s = next(s for s in b.steps if s.code == code); return "\n".join(s.lines + s.hints)


class Plans(unittest.TestCase):
    def test_bus36_healthy(self):
        b, bp, out = plan("bus36")
        self.assertEqual(status(b), {"C1": "PASS", "X1": "PASS", "X2": "PASS", "X3": "PASS", "X4": "PASS"}, out)

    def test_bus36_missing_pulls(self):
        b, bp, out = plan("bus36", "nopull:PAUSE")
        self.assertEqual(status(b)["X2"], "FAIL"); self.assertIn("-PAUSE stays low after it is let go", text(b, "X2"))
        self.assertNotIn("also takes", text(b, "X2"))
        b, bp, out = plan("bus36", "nopull:TPB")
        self.assertEqual(status(b)["X3"], "FAIL"); self.assertIn("TPB stays 1 after it is let go: no pull-down", text(b, "X3"))
        b, bp, out = plan("bus36", "nopull:MRW")
        self.assertEqual(status(b)["X3"], "FAIL"); self.assertIn("-MRW stays 0 after it is let go: no pull-up", text(b, "X3"))
        b, bp, out = plan("bus36", "nopull:D")
        self.assertEqual(status(b)["X3"], "FAIL"); self.assertIn("D0-D7 read 00 after 00 is let go", text(b, "X3"))
        b, bp, out = plan("bus36", "stuck-line:EF2:0")
        self.assertEqual(status(b)["X1"], "FAIL"); self.assertIn("-EF2 reads low with nothing pulling it", text(b, "X1"))

    def test_load_healthy(self):
        b, bp, out = plan("load")
        self.assertEqual(set(status(b).values()), {"PASS"}, out); self.assertEqual(len(b.steps), 7)
        self.assertIn("read all 48 bytes back as loaded", text(b, "L4")); self.assertEqual(bp.fights(), [])
        self.assertEqual(bd_mode(b), "RUN")

    def test_load_faults(self):
        b, bp, out = plan("load", "nocable")
        self.assertEqual(status(b)["L1"], "FAIL"); self.assertIn("6-way ribbon", text(b, "L1")); self.assertNotIn("L3", status(b))
        b, bp, out = plan("load", "jp1int")
        self.assertEqual(status(b)["L1"], "FAIL"); self.assertIn("JP1 on EXT", text(b, "L1"))
        b, bp, out = plan("load", "stuck-line:DMAIN:0")
        self.assertEqual(status(b)["L3"], "FAIL"); self.assertIn("slot position 34", text(b, "L3")); self.assertNotIn("L4", status(b))
        b, bp, out = plan("load", "stuck-line:PAUSE:1")                                 # -PAUSE never reaches the bus
        self.assertEqual(status(b)["L2"], "FAIL"); self.assertIn("MODE LOAD: the bus shows cpu=RESET", text(b, "L2"))

    def test_an_older_plan_on_busdrv_c(self):
        """the memory plan as BUSDRV-B runs it, on BUSDRV-C in a bus Rev D with the CPU card out: the same results"""
        b, bp, out = plan("memory", busdrv="C")
        self.assertIn("BUSDRV-C", text(b, "B1"))
        self.assertEqual([status(b)[c] for c in ("B1", "B2", "M1", "M2", "M3", "M4")], ["PASS", "PASS", "WARN", "PASS", "PASS", "PASS"], out)
        self.assertEqual(bp.fights(), [])


def bd_mode(b): return b.bd.cpu_mode()


if __name__ == "__main__":
    with contextlib.redirect_stdout(io.StringIO()): r = unittest.main(exit=False, verbosity=0).result
    print("%d tests, %d failures, %d errors" % (r.testsRun, len(r.failures), len(r.errors)))
    for f in r.failures + r.errors: print(f[1])
    sys.exit(0 if r.wasSuccessful() else 1)
