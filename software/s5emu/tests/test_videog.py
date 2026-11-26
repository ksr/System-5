# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-01
"""VIDEO-G model (s5emu/videog.py) and the VIDEO-G HBIOS (firmware/hbios/video-g): the memory-mapped registers, window, pages, status,
the boot screen, the 24-row scroll and its speed, the PNG writer."""
import os, struct, sys, unittest, zlib
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, ".."))
from s5emu.videog import VideoGMachine
from s5emu.machine import FLOAT, Machine
VG_ROM = os.path.join(HERE, "..", "roms", "hbios-video-g.rom")


def bare(**kw):
    m = VideoGMachine(**kw); m.cpurom.remap = False
    return m


class Card(unittest.TestCase):
    """the card as memory-mapped since 2026-11-17: 7800/7801 6845, 7802 key, 7804 status / control, 7806 mouse / Y,
    7C00-7C3F the window (7800-7807 repeat through 7BFF); no I/O port"""
    STAT, KEY, CTRL, Y, MOUSE, WIN = 0x7804, 0x7802, 0x7804, 0x7806, 0x7806, 0x7C00

    def test_status_ntsc_gfx(self):
        m = bare(); s = m.read(self.STAT)
        self.assertEqual(s & 0xC0, 0x80)          # card ID 10
        self.assertEqual(s & 0x30, 0x20)          # GFX fitted, MONITOR = NTSC
        m.kbd.press("A"); self.assertTrue(m.read(self.STAT) & 1)         # KEY-READY
        self.assertTrue(m.ef(3))                  # and the bus -EF (EF3 on CPU Rev A; JP3 KBD FLAG as set)
        self.assertEqual(m.read(self.KEY), ord("A")); self.assertFalse(m.read(self.STAT) & 1)

    def test_no_ports(self):
        m = bare(); m.kbd.press("A")
        self.assertEqual([m.inp(n) for n in (1, 4, 5, 6, 7)], [0xFF] * 5)   # nothing answers an INP
        m.out(4, 0x0F); m.out(7, 9)
        self.assertEqual((m.video.ctrl, m.video.yreg), (0, 0))           # nor an OUT
        self.assertTrue(m.read(self.STAT) & 1)    # and the key still waits (INP 1 did not take it)

    def test_registers_repeat(self):
        m = bare(); m.kbd.press("Q")
        self.assertEqual(m.read(0x7A02), ord("Q"))                       # 7800-7807 repeat through 7BFF
        m.write(0x7B86, 12); self.assertEqual(m.video.yreg, 12)
        m.write(0x7805, 0x02); self.assertTrue(m.video.gfx_on())        # A0 is not decoded there: 7805 = 7804

    def test_io_panel_on_port_4_beside_video_g(self):
        m = bare(panel=True)
        m.out(4, 0x5A); self.assertEqual(m.panel.latch, 0x5A); self.assertEqual(m.video.ctrl, 0)
        m.panel.switches = 0x3C; self.assertEqual(m.inp(4), 0x3C)

    def test_status_mda_and_no_gfx(self):
        self.assertTrue(bare(monitor="mda").read(self.STAT) & 0x10)
        m = bare(gfx=False)
        self.assertEqual(m.read(self.STAT) & 0x20, 0)
        m.write(self.Y, 5); m.write(self.WIN, 0x55)
        self.assertEqual(m.read(self.WIN), 0xFF)  # nothing answers: the bus floats
        self.assertEqual(m.read(self.MOUSE), 0xFF)

    def test_window_lines_and_pages(self):
        m = bare()
        m.write(self.Y, 10); m.write(self.WIN + 3, 0xA5)
        self.assertEqual(m.video.pages[0][10 * 64 + 3], 0xA5)
        self.assertEqual(m.read(self.WIN + 3), 0xA5)
        self.assertEqual(m.read(0x7FC3), 0xA5)    # the 64-byte window repeats through 7FFF
        m.write(self.Y, 11); self.assertEqual(m.read(self.WIN + 3), m.video.pages[0][11 * 64 + 3])
        m.write(self.CTRL, 0x10); m.write(self.Y, 10); m.write(self.WIN + 3, 0x3C)       # CPAGE = 1
        self.assertEqual(m.video.pages[1][10 * 64 + 3], 0x3C)
        self.assertEqual(m.video.pages[0][10 * 64 + 3], 0xA5)
        self.assertEqual([m.video.pixel(x, 10, page=1) for x in range(24, 32)], [0, 0, 1, 1, 1, 1, 0, 0])  # 3C

    def test_text_ram_and_crtc(self):
        m = bare()
        m.write(0x7000, ord("H")); m.write(0x7000 + 64 * 24, ord("Z"))
        self.assertTrue(m.video.lines()[0].startswith("H"))
        self.assertTrue(m.video.lines()[24].startswith("Z"))
        self.assertEqual(len(m.video.lines()), 25)
        m.write(0x7800, 14); m.write(0x7801, 6); m.write(0x7800, 15); m.write(0x7801, 3)   # as on the 6845 card
        self.assertEqual(m.video.cursor(), (24, 3))
        self.assertEqual((m.video.reg[14], m.video.reg[15]), (6, 3))

    def test_the_6845_is_write_only(self):
        """7800 / 7801 read as FF whatever was written, in every pair that repeats, and a read changes nothing"""
        m = bare(); m.write(0x7800, 14); m.write(0x7801, 0x2A); before = (list(m.video.reg), m.video.sel)
        for a in (0x7800, 0x7801, 0x7808, 0x7BF9): self.assertEqual(m.read(a), FLOAT, "%04X" % a)
        self.assertEqual((list(m.video.reg), m.video.sel, m.video.reg[14]), before + (0x2A,))

    def test_no_gfx_no_control_register(self):
        m = bare(gfx=False); m.write(self.CTRL, 0x0F)
        self.assertEqual(m.video.ctrl, 0)        # on the GFX board since 2026-11-02
        self.assertTrue(m.video.text_on())

    def test_mouse_latch(self):
        m = bare(); v = m.video
        self.assertFalse(v.mouse_packet(1, 2))   # MOUSE-ON off: the mouse sends nothing
        m.write(self.CTRL, 0x20)
        self.assertTrue(v.mouse_packet(5, -3, 1))
        self.assertTrue(m.read(self.STAT) & 2)
        self.assertEqual(m.read(self.MOUSE) & 0x0F, 0x09)  # buttons 1, the always-1 bit
        m.write(self.CTRL, 0x00)                 # off with two bytes unread: one stays in the latch
        self.assertTrue(m.read(self.STAT) & 2)
        self.assertEqual(m.read(self.MOUSE), 5)
        self.assertFalse(m.read(self.STAT) & 2)

    def test_special_keys(self):
        from s5emu.videog import KEYS
        self.assertEqual((KEYS["F1"], KEYS["F12"], KEYS["UP"], KEYS["DEL"]), (0x80, 0x8B, 0x91, 0x9A))
        m = bare(); m.kbd.queue.append(KEYS["LEFT"] + 0x40)
        self.assertEqual(m.read(self.KEY), 0xD3)

    def test_control_and_reset(self):
        m = bare(); m.write(self.CTRL, 0x0F)
        v = m.video
        self.assertFalse(v.text_on()); self.assertTrue(v.gfx_on()); self.assertTrue(v.xor_mode()); self.assertEqual(v.dpage(), 1)
        m.reset(); self.assertEqual(v.ctrl, 0)

    def test_vsync_follows_the_clock(self):
        m = bare(); seen = set()
        for c in range(0, 4000, 25):
            m.cpu.cycles = c; seen.add(bool(m.read(self.STAT) & 4))
        self.assertEqual(seen, {True, False})

    def test_png(self):
        m = bare(); m.write(self.Y, 0); m.write(self.WIN, 0xFF); m.write(self.CTRL, 0x02)
        path = os.path.join(HERE, "_vg_test.png")
        m.video.save_png(path, "gfx", 1)
        with open(path, "rb") as f: data = f.read()
        os.remove(path)
        self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
        w, h = struct.unpack(">II", data[16:24]); self.assertEqual((w, h), (512, 200))
        self.assertEqual(sum(sum(r) for r in m.video.picture("gfx")), m.video.count_pixels(page=0))

    def test_default_machine_unchanged(self):
        m = Machine(); m.cpurom.remap = False
        m.write(0x7800, 14)                       # the 6845 card: CRTC address register in memory
        self.assertEqual(m.video.sel, 14)


@unittest.skipUnless(os.path.exists(VG_ROM), "build firmware/hbios/video-g/build.py first")
class HBIOS(unittest.TestCase):
    def boot(self):
        m = VideoGMachine(cpu_rom=VG_ROM)
        for _ in range(300_000): m.step()
        return m

    def test_special_keys_not_echoed(self):
        m = self.boot()
        before = m.video.lines()[24].rstrip()
        for k in (0x80, 0x88, 0x8A, 0x91, 0xC1, 0xDA): m.kbd.queue.append(k)
        for _ in range(100_000): m.step()
        self.assertEqual(m.video.lines()[24].rstrip(), before)   # F9 = 88 is not a backspace, F11 = 8A no line feed
        m.kbd.press("A")
        for _ in range(50_000): m.step()
        self.assertTrue(m.video.lines()[24].rstrip().endswith("A"))

    def test_boots_to_the_bottom_row(self):
        m = self.boot()
        self.assertEqual(m.video.lines()[24].rstrip(), "test>")
        self.assertEqual(m.video.cursor(), (24, 5))
        self.assertEqual(m.video.reg[6], 25)      # 64 x 25
        self.assertEqual(m.video.reg[9], 7)       # 8 scan lines
        self.assertEqual(m.video.ctrl, 0)         # the control register (7804) = 00

    def test_lba_fix_as_v106(self):
        """the VIDEO-G ROM carries v1.0.6's disk fix (Elf/OS v5 needs it on the real card), byte for byte"""
        with open(VG_ROM, "rb") as f: vg = f.read()
        with open(os.path.join(HERE, "..", "roms", "hbios-1.0.6.rom"), "rb") as f: v106 = f.read()
        for a in list(range(0xFBC1, 0xFBC4)) + list(range(0xFBDF, 0xFBE2)) + list(range(0xFC31, 0xFC45)):
            self.assertEqual(vg[a - 0xF000], v106[a - 0xF000], "%04X" % a)

    def test_line_feed(self):
        """HBIOS's type routine (F203) with a line feed, on a bare 1802: rows 1-24 move up, row 24 is blanked,
        row 25 (not on the screen) is left alone; about 45 ms at 1.76 MHz (8 clocks a machine cycle)"""
        from s5emu.cpu import CPU1802
        with open(VG_ROM, "rb") as f: rom = f.read()
        class Bus:
            def __init__(s): s.m = bytearray(65536); s.m[0xF000:] = rom
            def read(s, a): return s.m[a]
            def write(s, a, v):
                if a < 0xF000: s.m[a] = v
            def out(s, n, v): pass
            def inp(s, n): return 0
            def ef(s, n): return False
        b = Bus()
        for r in range(25): b.m[0x7000 + 64 * r:0x7000 + 64 * r + 64] = bytes([ord("A") + r]) * 64
        b.m[0x7000 + 64 * 25] = ord("!")
        b.m[0x77FE], b.m[0x77FF] = 0x76, 0x00     # the cursor: row 24
        c = CPU1802(b); c.P = 3; c.X = 2; c.R[2] = 0x6FF0; c.R[3] = 0xF203; c.D = 10
        n = 0
        while b.m[c.R[3]] != 0xD5 and n < 100000: c.step(); n += 1         # up to its SEP R5
        for r in range(24): self.assertEqual(b.m[0x7000 + 64 * r], ord("A") + r + 1)
        self.assertEqual(bytes(b.m[0x7600:0x7640]), b" " * 64)
        self.assertEqual(b.m[0x7000 + 64 * 25], ord("!"))
        self.assertEqual((b.m[0x77FE], b.m[0x77FF]), (0x76, 0x00))
        ms = c.cycles * 8 / 1.76e3
        self.assertLess(ms, 50.0); self.assertGreater(ms, 35.0)


if __name__ == "__main__":
    unittest.main(verbosity=1)
