# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-20
"""The bus-driver link as BUSDRV-C (s5emu/buslink.py): the host tool software/busdrv/s5busdrv.py driving the emulated
machine with CPU Rev D in place: the modes, LOAD mode filling RAM with CPU Rev D's LOADED flag, the 36-pin lines.
And as BUSDRV-B, unchanged, on a machine without CPU Rev D."""
import os, sys, unittest
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "..", "busdrv"))
from s5emu.hw import HWMachine                                              # noqa: E402
from s5emu.buslink import BusLink, card_for, C_COMMANDS, C_LINES           # noqa: E402
from s5emu.shell import Shell                                              # noqa: E402
import s5busdrv as S                                                       # noqa: E402

ROM = os.path.join(HERE, "..", "roms", "hbios-1.0.6.rom")
# 0300-030F = 80..8F, Q on, idle
PROG = bytes([0xF8, 0x03, 0xB1, 0xF8, 0x00, 0xA1, 0xF8, 0x10, 0xA2, 0x81, 0xF9, 0x80, 0x51, 0x11, 0x22, 0x82, 0x3A, 0x09, 0x7B, 0x00])
IMAGE = PROG + bytes((100 + 7 * i) & 0xFF for i in range(300 - len(PROG)))


class Wire:
    """the link without the pseudo-terminal: what s5busdrv.BusDriver reads and writes"""
    def __init__(self, link):
        self.link = link; self.rx = ""; self.buf = bytearray(); self._emit([link.banner(), ">>"])
    def write(self, b):
        self.rx += b.decode("ascii")
        while "#" in self.rx:
            c, self.rx = self.rx.split("#", 1); self._emit(self.link.run(c) + [">>"])
    def read(self, n=1): b = bytes(self.buf[:n]); del self.buf[:n]; return b
    def reset_input_buffer(self): pass
    def _emit(self, lines): self.buf += ("\r\n".join(lines) + "\r\n").encode()


def machine(**kw):
    """-> (BusDriver, machine, link): CPU Rev D, HBIOS in its EPROM, the memory, video, IDE and IO cards"""
    m = HWMachine(cpu_rom=ROM, cpu_rev="D", **kw); link = BusLink(m, lambda: False, pty=False)
    return S.BusDriver(transport=Wire(link)), m, link


def err(test, bd, op, operand=0):
    with test.assertRaises(S.CardError) as cm: bd.cmd(op, operand)
    return str(cm.exception)


class RevC(unittest.TestCase):
    def test_the_card_follows_the_cpu_card(self):
        bd, m, link = machine()
        self.assertEqual((card_for(m), link.rev, bd.rev), ("C", "C", "C"))
        for word in ("clk-2", "ext-1", "mode-2", "load-1", "BUSDRV-C"): self.assertIn(word, bd.banner[0])
        self.assertEqual(bd.status(), "bus=on mode=MONITOR board=C cpu=RUN clk=0")
        self.assertIn("a CPU card answers on the DEBUG cable", err(self, bd, "MASTER", 1))
        self.assertIn("MONITOR mode", err(self, bd, "RDMEM", 0))
        self.assertEqual(bd.clock_test(), "CLK OUT reaches the 1802")
        with self.assertRaises(ValueError): BusLink(HWMachine(cpu_rom=ROM), lambda: False, rev="C", pty=False)

    def test_modes_hold_the_machine(self):
        bd, m, link = machine(); d = Shell(m).d
        d.run(max_instructions=1000); self.assertGreater(m.cpu.instructions, 0)       # RUN: HBIOS boots
        bd.mode("pause"); n = m.cpu.instructions; d.run(max_instructions=500)
        self.assertEqual((bd.cpu_mode(), m.cpu.instructions), ("PAUSE", n)); self.assertFalse(m.ccard.loaded())
        bd.mode("run"); d.run(max_instructions=500); self.assertEqual(m.cpu.instructions, n + 500)
        bd.mode("reset"); self.assertEqual((bd.cpu_mode(), m.cpu.R[m.cpu.P], m.cpu.instructions), ("RESET", 0, 0))
        d.run(max_instructions=500); self.assertEqual(m.cpu.instructions, 0); self.assertFalse(m.ccard.loaded())
        f = bd.fields(bd.snap()); self.assertEqual((f["-RESET"], f["-PAUSE"]), ("0", "1"))
        bd.mode("run"); d.run(max_instructions=500); self.assertEqual(m.cpu.instructions, 500)

    def test_load_mode_fills_ram_and_run_runs_it(self):
        """LOAD: the bytes land in RAM (the boot EPROM is off: LOADED), each one a write through the machine's bus with
        no bus event; RUN executes them; a bus reset keeps the program; the CPU card's own reset boots HBIOS"""
        bd, m, link = machine(); d = Shell(m).d
        bd.mode("load"); self.assertTrue(m.ccard.loaded()); self.assertEqual(bd.cpu_mode(), "LOAD")
        self.assertEqual(bd.dma_load(IMAGE), 0)
        self.assertEqual(bytes(m.peek(a) for a in range(len(IMAGE))), IMAGE)
        self.assertEqual(m.cpu.R[0], len(IMAGE)); self.assertEqual(m.log.events, {})
        d.run(max_instructions=200); self.assertEqual(m.cpu.instructions, 0)           # LOAD holds the 1802
        bd.mode("run"); d.run(max_instructions=200)
        self.assertEqual(bytes(m.peek(0x300 + i) for i in range(16)), bytes(range(0x80, 0x90)))
        self.assertEqual((m.cpu.Q, m.cpu.idle), (1, True)); self.assertEqual(bd.fields(bd.snap())["Q"], "1")
        bd.mode("reset"); bd.mode("run"); d.run(max_instructions=3)                   # a reset from the bus: LOADED stays
        self.assertEqual(m.cpu.R[1] >> 8, 0x03); self.assertTrue(m.ccard.loaded())
        m.reset(); d.run(max_instructions=3)                                           # the RESET/RUN switch: HBIOS again
        self.assertFalse(m.ccard.loaded()); self.assertGreaterEqual(m.cpu.R[m.cpu.P], 0xF000)
        self.assertEqual(m.log.events, {})

    def test_load_needs_load_mode(self):
        bd, m, link = machine()
        for mode in ("run", "reset", "pause"):
            bd.mode(mode); self.assertIn("not in LOAD mode", err(self, bd, "LOADBLK", "1,AA"))
        self.assertIn("LOADBLK:count,hh..", err(self, bd, "LOADBLK", "40," + "00" * 40))

    def test_ef_lines_reach_the_1802(self):
        """CPU Rev D's EF blocks as the emulator sets them: EF1 on -EF1, EF2 on -EF2, EF3 on the bus -EF"""
        bd, m, link = machine()
        for name, n in (("-EF1", 1), ("-EF2", 2), ("-EF", 3)):
            self.assertFalse(m.ef(n)); bd.line(name, True); self.assertTrue(m.ef(n))
            self.assertEqual(bd.fields(bd.snap())[name], "0")
            bd.line(name, False); self.assertFalse(m.ef(n))
        bd.line("-EF3", True); self.assertEqual([m.ef(n) for n in (1, 2, 3, 4)], [False] * 4)   # -EF3 is on no input
        bd.line("-EF1", True); bd.cmd("XRST"); self.assertFalse(m.ef(1))                # XRST lets every line go

    def test_with_the_io_panel(self):
        """the IO panel fitted too (its RUN and LOAD toggles pull the same lines): the link loads and runs as before"""
        bd, m, link = machine(panel_rev="A"); d = Shell(m).d
        bd.mode("load"); bd.dma_load(PROG); bd.mode("run"); d.run(max_instructions=200)
        self.assertEqual(bytes(m.peek(0x300 + i) for i in range(16)), bytes(range(0x80, 0x90)))
        m.panel_set(run=False); self.assertEqual(bd.cpu_mode(), "RESET")               # the panel's RUN toggle off
        m.panel_set(run=True); self.assertEqual(bd.cpu_mode(), "RUN")

    def test_clock_commands_are_stand_ins(self):
        bd, m, link = machine()
        self.assertEqual(bd.clk_hz(2000000), 2000000); self.assertEqual(bd.fields(bd.status())["clk"], "2000000")
        bd.clk_stop(); n = m.cpu.cycles; self.assertEqual(bd.clk(320), []); self.assertGreaterEqual(m.cpu.cycles - n, 20)
        self.assertEqual(bd.probe(), {"P1": 0, "P2": 0}); self.assertIn("no clock edges", err(self, bd, "PTIME", 10))

    def test_over_the_pseudo_terminal(self):
        """the whole path as `python3 -m s5emu --hw --cpu-rev D --buslink` and `s5busdrv.py --port <pty>` use it"""
        try: import serial                                                  # noqa: F401
        except ImportError: self.skipTest("pyserial is not installed")
        m = HWMachine(cpu_rom=ROM, cpu_rev="D"); link = BusLink(m, lambda: False)
        bd = S.BusDriver(port=link.path)
        self.assertEqual(bd.rev, "C"); bd.mode("load"); self.assertEqual(bd.dma_load(PROG), 0); bd.mode("run")
        self.assertEqual(bytes(m.peek(a) for a in range(len(PROG))), PROG); self.assertEqual(bd.cpu_mode(), "RUN")
        bd.ser.close()


class RevB(unittest.TestCase):
    def test_busdrv_b_as_before_and_no_rev_c_commands(self):
        m = HWMachine(cpu_rom=ROM); link = BusLink(m, lambda: False, pty=False); bd = S.BusDriver(transport=Wire(link))
        self.assertEqual((card_for(m), link.rev), ("B", "B")); self.assertEqual(link.banner(), "s5-bus-driver blocks-1 2026-10-06 (EMULATED)")
        self.assertEqual(bd.status(), "bus=on mode=MONITOR")
        for op in C_COMMANDS + C_LINES: self.assertIn("needs BUSDRV-C", err(self, bd, op, 1), op)
        self.assertIn("MONITOR mode", err(self, bd, "RDMEM", 0))
        bd.master(True); bd.read(0x8000, 1)                 # (an access with A15 high ends CPU Rev A's boot map)
        bd.write(0x0100, b"\x12\x34"); self.assertEqual(bd.read(0x0100, 2), b"\x12\x34")
        self.assertEqual(bd.snap(), "D=FF A=00 TPA=0 TPB=0 -MRD=1 -MRW=1 -VMA=1 Q=0 N=0 -RESET=1 -INT=1 -EF=1 SP=0")
        bd.master(False); self.assertEqual(m.step.__self__, m)                         # the machine is left as it was


if __name__ == "__main__":
    unittest.main(verbosity=1)
