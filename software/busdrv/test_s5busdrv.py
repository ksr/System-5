#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-06
"""Tests for s5busdrv.py against the simulated card (simcard.py). Run: python3 test_s5busdrv.py"""
import os, sys, unittest, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s5busdrv as S, simcard


class T(unittest.TestCase):
    def card(self, **kw): return S.BusDriver(transport=simcard.SimCard(**kw))

    def test_banner_and_status(self):
        bd = self.card(); self.assertTrue(bd.blocks); self.assertEqual(bd.status(), "bus=on mode=MONITOR")

    def test_monitor_refuses_memory(self):
        with self.assertRaises(S.CardError): self.card().read(0, 1)

    def test_master_refused_while_cpu_runs(self):
        with self.assertRaises(S.CardError): self.card(cpu_running=True).master(True)

    def test_no_bus_power(self):
        bd = self.card(bus_on=False); self.assertEqual(bd.status(), "bus=off mode=MONITOR")
        with self.assertRaises(S.CardError): bd.master(True)

    def test_ram_rom_hole(self):
        bd = self.card(); bd.master(True)
        data = bytes(range(256)) * 3                       # 768 bytes: several blocks each way
        bd.write(0x1000, data); self.assertEqual(bd.read(0x1000, len(data)), data)
        self.assertEqual(bd.read(0x7000, 4), b"\xff" * 4)  # video hole floats
        rom = bd.read(0x8000, 4); bd.write(0x8000, b"\0\0\0\0"); self.assertEqual(bd.read(0x8000, 4), rom)

    def test_io(self):
        bd = self.card(); bd.master(True); bd.out(4, 0x5A); self.assertEqual(bd.inp(4), 0x5A)

    def test_memtest(self):
        bd = self.card(); bd.master(True)
        self.assertTrue(S.memtest(bd, 0x0000, 0x01FF)); self.assertFalse(S.memtest(bd, 0x8000, 0x800F))

    def test_intel_hex(self):
        p = tempfile.mktemp(suffix=".hex")
        with open(p, "w") as fh: fh.write(":0400100001020304E2\n:020020000A0BC9\n:00000001FF\n")   # second record: 2 bytes at 0020
        runs = S.read_intel_hex(p); self.assertEqual(runs, [(0x10, b"\x01\x02\x03\x04"), (0x20, b"\x0a\x0b")])

    def test_numbers(self):
        self.assertEqual([S.num("0x7000"), S.num("$7000"), S.num("28672")], [0x7000] * 3)


if __name__ == "__main__":
    import io, contextlib
    with contextlib.redirect_stdout(io.StringIO()): r = unittest.main(exit=False, verbosity=0).result
    print("%d tests, %d failures, %d errors" % (r.testsRun, len(r.failures), len(r.errors)))
    for f in r.failures + r.errors: print(f[1])
    sys.exit(0 if r.wasSuccessful() else 1)
