#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-11
"""Tests for bringup.py and the firmware's bus cycles, on the simulated backplane (backplane.py + fwsim.py: the
cards' netlists driven pin by pin as the firmware drives them). Each fault is one a real board can have; the test
checks the plan names it. Run: python3 test_bringup.py   (about two minutes)"""
import argparse, io, os, sys, tempfile, unittest, contextlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bringup as B

JUMPERS = "RR------E-------"                   # two RAM blocks and one EPROM block: the same paths, a quicker run


def run(plan, *extra, jumpers=JUMPERS):
    """-> (Bringup, Backplane, text)"""
    ap_args = [plan, "--sim", "--jumpers", jumpers] + list(extra)
    a = argparse.Namespace(plan=plan, port=None, log=False, sim=True, fault=None, jumpers=jumpers, full=False, rom=None,
                           rom_base=0x8000, save_rom=None, ide_sel=2, ide_data=3, image=None, sectors=1, cf_write_lba=None,
                           video_base=0x7000, interactive=False, keep=False, report=None, mem_rev="D", video_rev="B")
    i = 0
    while i < len(extra):
        k = extra[i].lstrip("-").replace("-", "_")
        if k == "fault": a.fault = (a.fault or []) + [extra[i + 1]]; i += 2
        elif k in ("image", "rom", "mem_rev", "video_rev"): setattr(a, k, extra[i + 1]); i += 2
        elif k in ("cf_write_lba", "sectors"): setattr(a, k, int(extra[i + 1])); i += 2
        else: setattr(a, k, True); i += 1
    bd, bp = B.sim_driver(a); out = io.StringIO()
    b = B.Bringup(bd, a, out=lambda s: out.write(s + "\n")); b.plan(plan); b.summary()
    return b, bp, out.getvalue()


def status(b, code): return next(s for s in b.steps if s.code == code).status
def text(b, code): s = next(s for s in b.steps if s.code == code); return "\n".join(s.lines + s.hints)


class Memory(unittest.TestCase):
    def test_healthy(self):
        b, bp, out = run("memory")
        self.assertEqual([status(b, c) for c in ("B1", "M2", "M3", "M4")], ["PASS"] * 4)
        self.assertEqual(status(b, "M1"), "WARN")                      # the simulated EPROM is blank
        self.assertIn("8000-8FFF: expected EPROM (IC5), reads FF", text(b, "M1"))
        self.assertEqual(bp.fights(), [])

    def test_rom_compare(self):
        img = bytes((i * 13 + 5) & 0xFF for i in range(4096)); p = tempfile.mktemp(suffix=".bin")
        with open(p, "wb") as fh: fh.write(img)
        b, bp, out = run("memory", "--rom", p)
        self.assertEqual(status(b, "M1"), "PASS"); self.assertEqual(status(b, "M5"), "PASS")
        bp.mem.program(0x8123, 0x00)                                    # one byte wrong in the chip
        b.bd.master(True); b2 = B.Bringup(b.bd, b.a, out=lambda s: None); b2.step("M5", "EPROM", b2.s_mem_rom)
        self.assertEqual(b2.steps[0].status, "FAIL"); self.assertIn("first at 8123", text(b2, "M5"))

    def test_stuck_data_line(self):
        b, bp, out = run("memory", "--fault", "stuck:mem:3:0")
        self.assertEqual(status(b, "M2"), "FAIL"); self.assertIn("will not go high: D3", text(b, "M2"))
        self.assertEqual(status(b, "M3"), "PASS")                      # the address test works round the bad bit

    def test_stuck_address_line(self):
        b, bp, out = run("memory", "--fault", "addr:4:0")
        self.assertEqual(status(b, "M2"), "PASS"); self.assertEqual(status(b, "M3"), "FAIL")
        self.assertIn("A4 A12", text(b, "M3"))                        # A12 is latched from the same bus pin

    def test_missing_ram(self):
        b, bp, out = run("memory", "--fault", "empty:IC1")
        self.assertEqual(status(b, "M1"), "FAIL"); self.assertIn("IC1 in its socket", text(b, "M1"))
        self.assertEqual(status(b, "M2"), "SKIP")

    def test_wrong_jumper(self):
        b, bp, out = run("memory", "--fault", "card-jumpers:RRR-----E-------")   # one jumper more than the plan expects
        self.assertEqual(status(b, "M1"), "FAIL"); self.assertIn("2000: expected nothing (jumper open), found RAM", text(b, "M1"))


    def test_reworked_rev_b(self):
        """Ken's present memory card: the jumpers do not decide its map, its netlist does (RAM 0000-7FFF, EPROM 8000-FFFF)"""
        b, bp, out = run("memory", "--mem-rev", "B-built")
        self.assertIn(status(b, "M1"), ("PASS", "WARN"), out); self.assertIn("the jumpers do nothing", text(b, "M1"))
        self.assertEqual(b.mem_expect(7), "RAM")
        self.assertEqual([status(b, c) for c in ("M2", "M3")], ["PASS", "PASS"])


class CF(unittest.TestCase):
    def test_healthy_and_image(self):
        img = bytearray(512 * 4); img[0:6] = b"ELF/OS"; img[510:512] = b"\x55\xaa"; img[512 + 7] = 0x42
        p = tempfile.mktemp(suffix=".img")
        with open(p, "wb") as fh: fh.write(img)
        b, bp, out = run("cf", "--image", p, "--sectors", "2", "--cf-write-lba", "3")
        for c in ("C1", "C2", "C3", "C4", "C5", "C6", "C7"): self.assertEqual(status(b, c), "PASS", c + "\n" + out)
        self.assertIn("2 sector(s) match", text(b, "C6")); self.assertIn("a PC boot signature", text(b, "C6"))
        self.assertEqual(bytes(bp.drive.disk[3 * 512:4 * 512]), bytes(512))   # the write test put LBA 3 back
        self.assertEqual(bp.fights(), [])

    def test_no_drive(self):
        b, bp, out = run("cf", "--fault", "nodrive")
        self.assertEqual(status(b, "C1"), "FAIL"); self.assertIn("status reads FF", text(b, "C1"))

    def test_bad_drive_data_line(self):
        b, bp, out = run("cf", "--fault", "stuck:ide:5:1")
        self.assertEqual(status(b, "C2"), "FAIL"); self.assertIn("will not go low: D5", text(b, "C2"))

    def test_old_firmware(self):
        """the bus cycles before 2026-10-11: OUT without -MRD makes the IDE card read the drive while we drive the bus"""
        b, bp, out = run("cf", "--fault", "legacy")
        self.assertEqual(status(b, "B1"), "WARN"); self.assertEqual(status(b, "C1"), "FAIL")
        b, bp, out = run("cf", "--fault", "legacy")
        bp.fights()                                                     # (C1 stops the plan before an OUT with data)
        bd = b.bd; bd.master(True); bd.out(2, 3); bd.out(3, 0x5A)
        self.assertTrue(bp.fights(), "an OUT should fight the drive with the old cycles")


class Video(unittest.TestCase):
    def test_healthy(self):
        b, bp, out = run("video")
        for c in ("V1", "V2", "V3", "V4", "V5"): self.assertEqual(status(b, c), "PASS", c + "\n" + out)
        self.assertEqual(status(b, "V6"), "LOOK")
        self.assertEqual(bp.screen.reg[:16], B.HBIOS_CRTC)
        self.assertIn("SYSTEM-5 6845 VIDEO BRING-UP", "\n".join(bp.screen.lines()))
        self.assertEqual(bp.fights(), [])

    def test_write_only_6845(self):
        """Rev B-Clean-Keyboard: V5 reads no register back; the writes land (the screen comes up), and no bus fight"""
        b, bp, out = run("video", "--video-rev", "B-Clean-Keyboard")
        for c in ("V1", "V2", "V3", "V4", "V5"): self.assertEqual(status(b, c), "PASS", c + "\n" + out)
        self.assertEqual(bp.screen.reg[:16], B.HBIOS_CRTC); self.assertEqual(bp.fights(), [])
        self.assertIn("nothing drives a read of them", text(b, "V5")); self.assertNotIn("R14", text(b, "V5"))

    def test_write_only_6845_needs_no_tpb(self):
        """E = NOT -MRW: the bus driver's firmware from before 2026-10-11, with no TPB in memory cycles, writes it too"""
        b, bp, out = run("video", "--video-rev", "B-Clean-Keyboard", "--fault", "legacy")
        self.assertEqual(status(b, "V5"), "PASS"); self.assertEqual(bp.screen.reg[:16], B.HBIOS_CRTC)

    def test_write_only_6845_under_ram(self):
        b, bp, out = run("all", "--video-rev", "B-Clean-Keyboard", "--mem-rev", "B-built")
        self.assertEqual(status(b, "A3"), "FAIL"); self.assertIn("RAM also answers at", text(b, "A3"))

    def test_old_firmware_crtc_silent(self):
        b, bp, out = run("video", "--fault", "legacy")
        self.assertEqual(status(b, "V4"), "PASS")                      # the video RAM does not need TPB
        self.assertEqual(status(b, "V5"), "FAIL"); self.assertIn("never answers", text(b, "V5"))

    def test_bad_vram_data_line(self):
        b, bp, out = run("video", "--fault", "stuck:video:0:0")
        self.assertEqual(status(b, "V2"), "FAIL"); self.assertIn("will not go high: D0", text(b, "V2"))


class All(unittest.TestCase):
    def test_reworked_rev_b_with_video(self):
        """open question: with the reworked Rev B, RAM and the 6845 card both answer at 7000-7FFF"""
        b, bp, out = run("all", "--mem-rev", "B-built")
        self.assertEqual(status(b, "A1"), "FAIL"); self.assertIn("answers in block 7 too", text(b, "A1"))

    def test_healthy(self):
        b, bp, out = run("all")
        for c in ("A2", "A3", "A4", "A5", "A6"): self.assertEqual(status(b, c), "PASS", c + "\n" + out)
        self.assertEqual(bp.fights(), [])

    def test_memory_also_in_block_7(self):
        b, bp, out = run("all", jumpers="RR-----RE-------")
        self.assertEqual(status(b, "A1"), "FAIL"); self.assertIn("block 7", text(b, "A1"))
        self.assertEqual(status(b, "A3"), "FAIL")                      # RAM and the CRTC both answer at 7801
        self.assertTrue(bp.fights())                                    # (the simulator sees the fight itself)


if __name__ == "__main__":
    with contextlib.redirect_stdout(io.StringIO()): r = unittest.main(exit=False, verbosity=0).result
    print("%d tests, %d failures, %d errors" % (r.testsRun, len(r.failures), len(r.errors)))
    for f in r.failures + r.errors: print(f[1])
    sys.exit(0 if r.wasSuccessful() else 1)
