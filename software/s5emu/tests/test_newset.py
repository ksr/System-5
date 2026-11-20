# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-20
"""The new card set together (Ken, 2026-11-20: "test in both instruction and hardware emulators, assume current
memory and IDE card and the new CPU, IO, video text and gfx"): CPU Rev D, the IO panel (LEDs, toggles, clock, serial
port) and VIDEO-G TEXT + GFX, beside the memory card (Rev E, the emulator's Rev D) and the IDE card of today's
machine, with the VIDEO-G HBIOS (roms/hbios-video-g.rom, on v1.0.8 since the same day) and Elf/OS 5.1.1.

Each test runs on a machine a `machine()` method makes, so the same tests run on the instruction-level machine
(`Fast...`: videog.VideoGMachine with the panel) and on the hardware machine (`HW...`: hw.HWMachine with every card from
its netlist, CPU Rev D, memory Rev D, IDE Rev A, the IO panel and VIDEO-G TEXT and GFX (hwvideog.py), where the bus
log must also stay empty: no fight, no double drive, nothing undefined).

  Rom     the VIDEO-G HBIOS's v1.0.5-v1.0.8 additions: H, Q1 / Q0, D and its -- more -- key, the panel demo, @F1E0
  Cards   a program in RAM reaches every new card: ports 4, 6 and 7, VIDEO-G's registers, window and text RAM
  Panel   a program toggled in from the IO panel runs, and CPU Rev D's LOADED flag decides what a reset boots
  System  Elf/OS 5.1.1 from the card image: B, ver, free, dir, cls on 25 rows, the clock in sysinfo and date, vgdemo

The System tests need the Elf/OS v5 card image, which is in the private-resources repository (skipped without it).
"""
import datetime, gzip, os, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from s5emu.rtc import DS12885                       # noqa: E402
from s5emu.shell import Shell                       # noqa: E402
from s5emu.videog import VideoGMachine              # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
VG_ROM = os.path.join(HERE, "..", "roms", "hbios-video-g.rom")
ROM108 = os.path.join(HERE, "..", "roms", "hbios-1.0.8.rom")
V5_GZ = os.path.join(ROOT, "..", "private-resources", "elf", "reference", "mike-riley", "elfos-v5", "system5",
                     "elfos-5.1.1-system5-16mb.img.gz")
MHZ = 2.0                                           # CPU Rev D's clock


def screen(m):
    return [l.rstrip() for l in m.video.lines()]


class Fast:
    """the instruction-level machine: VIDEO-G and the IO panel as behaviour (CPU Rev D's LOADED flag is the machine's)"""
    def machine(self, rom=VG_ROM, disk=None):
        return VideoGMachine(cpu_rom=rom, disk=disk, panel=True, mhz=MHZ)

    def bus_events(self, m):
        return {}                                   # it keeps no bus log


class HW:
    """the hardware machine: CPU Rev D, the memory card, the IDE card, the IO panel and VIDEO-G, each from its netlist"""
    def machine(self, rom=VG_ROM, disk=None):
        from s5emu.hw import HWMachine
        return HWMachine(cpu_rom=rom, disk=disk, mem_rev="D", cpu_rev="D", ide_rev="A", panel_rev="A", videog="1.0", mhz=MHZ)

    def bus_events(self, m):
        return m.log.events


class Common:
    def until(self, m, sh, prompt, cap=40_000_000):
        """run until the keys are used up and the bottom row is `prompt`"""
        for _ in range(0, cap, 100_000):
            sh.d.run(max_instructions=100_000)
            if not m.kbd.queue and screen(m)[-1] == prompt: return
        self.fail("no %r on the bottom row; the screen:\n%s" % (prompt, "\n".join(screen(m))))

    def serial_in(self, m, data):
        if hasattr(m.panel, "serial_in"): m.panel.serial_in(data)
        else: m.panel.uart.receive(data)

    def serial_out(self, m):
        return bytes(m.panel.serial_out() if hasattr(m.panel, "serial_out") else m.panel.uart.sent())


# ---------------------------------------------------------------------------------------------- the ROM
class RomTests(Common):
    def boot(self):
        m = self.machine(); sh = Shell(m); self.until(m, sh, "test>", 4_000_000)
        return m, sh

    def test_clock_driver_and_panel_demo_are_v108s(self):
        """the clock driver, its vectors, the panel demo and the disk fix: v1.0.8's bytes at v1.0.8's addresses"""
        with open(VG_ROM, "rb") as f: vg = f.read()
        with open(ROM108, "rb") as f: v108 = f.read()
        for lo, hi in ((0xFC92, 0xFCEB), (0xF7CD, 0xF7FF), (0xF815, 0xF81A), (0xF1C0, 0xF1D1), (0xFC31, 0xFC44),
                       (0xFEDB, 0xFEDD)):
            self.assertEqual(vg[lo - 0xF000:hi - 0xF000 + 1], v108[lo - 0xF000:hi - 0xF000 + 1], "%04X-%04X" % (lo, hi))

    def test_h_lists_the_commands(self):
        m, sh = self.boot()
        m.kbd.press("H\n"); self.until(m, sh, "test>", 4_000_000)
        s = screen(m)
        for line in (" B               boot the OS from the CF card (@FF00)", " D start         disassemble one screenful",
                     " Q1 / Q0         turn Q on / off (SEQ / REQ)", " @F1C0           panel demo: toggles to LEDs, INPUT to Q",
                     " H               this list"):
            self.assertIn(line, s)
        self.assertEqual(s.index(" H               this list") + 1, len(s) - 1)     # the list in one piece, in order

    def test_q_on_and_off(self):
        m, sh = self.boot()
        m.kbd.press("Q1\n"); self.until(m, sh, "test>", 2_000_000); self.assertEqual(m.cpu.Q, 1)
        m.kbd.press("Q0\n"); self.until(m, sh, "test>", 2_000_000); self.assertEqual(m.cpu.Q, 0)

    def test_d_disassembles_and_its_key_is_videogs(self):
        """D start:end stops at -- more -- for a key, read from VIDEO-G's keyboard (7804 / 7802) without an echo: a
        space goes on, Esc stops. Every opcode, laid out at 0400 with its operands, comes out as s5emu's disassembler
        writes it (as tests.test_machine does for v1.0.5, whose D this is)"""
        from s5emu.disasm import disasm
        m, sh = self.boot(); run = lambda n=150_000: sh.d.run(max_instructions=n)
        a = 0x400
        for op in range(256):
            m.write(a, op); m.write(a + 1, 0x12 + op % 7); m.write(a + 2, 0x34 + op % 11)
            a += disasm(m.peek, a)[0]
        want, b = [], 0x400
        while b < a:
            n, t = disasm(m.peek, b)
            want.append("%04X  %-8s  %s" % (b, " ".join("%02X" % m.peek(b + k) for k in range(n)), t.split(";")[0].rstrip()))
            b += n
        m.kbd.press("D 0400:%04X\n" % (a - 1)); got = []
        for _ in range(3000):
            run()
            if screen(m)[-1].startswith("-- more --"): got.extend(screen(m)[-15:-1]); m.kbd.press(" ")
            elif screen(m)[-1] == "test>" and not m.kbd.ready(): break
        last = screen(m)[:-1]
        got.extend(last[last.index(got[-1]) + 1:])
        self.assertEqual(got, want)
        m.kbd.press("D F000:F3FF\n"); self.until(m, sh, "-- more --", 4_000_000)
        m.kbd.press("\x1b"); self.until(m, sh, "test>", 2_000_000)               # Esc at the first pause stops

    def test_panel_demo(self):
        m, sh = self.boot()
        m.panel_set(switches=0xA6); m.kbd.press("@F1C0\n"); sh.d.run(max_instructions=300_000)
        self.assertEqual(m.panel.latch, 0xA6)
        m.panel_set(input=True); sh.d.run(max_instructions=2000); self.assertEqual(m.cpu.Q, 1)
        m.panel_set(input=False, switches=0x19); sh.d.run(max_instructions=2000)
        self.assertEqual((m.panel.latch, m.cpu.Q), (0x19, 0))

    def test_f1e0_restarts(self):
        """@F1E0 is v1.0.7's key-code display on the 6845-card ROMs; this ROM has none, and restarts instead"""
        m, sh = self.boot()
        m.kbd.press("H\n"); self.until(m, sh, "test>", 4_000_000)
        m.kbd.press("@F1E0\n"); sh.d.run(max_instructions=400_000)
        self.assertEqual([l for l in screen(m) if l], ["test>"])


# ---------------------------------------------------------------------------------------------- the cards, one by one
PROG = bytes([
    0xF8, 0x00, 0xB1, 0xF8, 0x80, 0xA1,             # 0000 R1 = 0080, where the results go
    0xE0, 0x64, 0xA5,                               # 0006 OUT 4 = A5          the panel's LEDs and TIL311s
    0xE1, 0x6C, 0x11,                               # 0009 INP 4 -> M(0080)    the toggles
    0xE0, 0x66, 0x0D, 0xE1, 0x6F, 0x11,             # 000C clock register 0D -> M(0081)   bit 7 = battery good
    0xE0, 0x66, 0x20, 0x67, 0x5A, 0x66, 0x20,       # 0012 clock RAM 20 = 5A, select it again
    0xE1, 0x6F, 0x11,                               # 0019 -> M(0082)
    0xE0, 0x66, 0x87, 0x67, 0xC3, 0x66, 0x87,       # 001C UART scratch register (87) = C3, select it again
    0xE1, 0x6F, 0x11,                               # 0023 -> M(0083)
    0xE0, 0x66, 0x83, 0x67, 0x03, 0x66, 0x80, 0x67, 0x53,   # 0026 UART: 8 bits no parity; send 'S'
    0xE0, 0x66, 0x85, 0xE1, 0x6F, 0x11,             # 002F UART line status -> M(0084)   bit 0 = a character is waiting
    0xE0, 0x66, 0x80, 0xE1, 0x6F, 0x11,             # 0035 UART received character -> M(0085)
    0xF8, 0x78, 0xB2, 0xF8, 0x04, 0xA2, 0xF8, 0x02, 0x52,   # 003B VIDEO-G control (7804) = 02: graphics on
    0xF8, 0x06, 0xA2, 0xF8, 0x05, 0x52,             # 0044 Y register (7806) = 05
    0xF8, 0x7C, 0xB2, 0xF8, 0x00, 0xA2, 0xF8, 0xFF, 0x52,   # 004A graphics window 7C00 = FF
    0x02, 0x51, 0x11,                               # 0053 read it back -> M(0086)
    0xF8, 0x78, 0xB2, 0xF8, 0x04, 0xA2, 0x02, 0x51, 0x11,   # 0056 VIDEO-G status (7804) -> M(0087)
    0xF8, 0x70, 0xB2, 0xF8, 0x00, 0xA2, 0xF8, 0x4F, 0x52, 0x12, 0xF8, 0x4B, 0x52,   # 005F text RAM 7000 = "OK"
    0x7B, 0x00,                                     # 006C Q on, idle
])


class CardTests(Common):
    def test_a_program_in_ram_reaches_every_new_card(self):
        """no EPROM fitted, so the 1802 starts at 0000 in RAM. (A new machine is at reset already; on CPU Rev D another
        reset with no EPROM in the socket would put the boot map back on, and the 1802 would fetch from the empty
        socket: right for the real card)"""
        m = self.machine(rom=None)
        for a, b in enumerate(PROG): m.write(a, b)
        m.panel_set(switches=0x3C); self.serial_in(m, b"R")
        for _ in range(400): m.step()
        r = [m.peek(0x80 + k) for k in range(8)]; v = m.video
        self.assertEqual(m.panel.latch, 0xA5)                    # OUT 4: the LEDs
        self.assertEqual(r[0], 0x3C)                             # INP 4: the toggles
        self.assertTrue(r[1] & 0x80)                             # the clock's register 0D on ports 6 / 7
        self.assertEqual(r[2], 0x5A)                             # the clock's RAM
        self.assertEqual(r[3], 0xC3)                             # the UART, picked by bit 7 of the address port
        self.assertEqual(self.serial_out(m), b"S")
        self.assertEqual((r[4] & 1, r[5]), (1, ord("R")))
        self.assertEqual((v.ctrl, v.yreg), (0x02, 0x05))         # VIDEO-G GFX: the control and Y registers
        self.assertEqual((v.pages[0][5 * 64], r[6]), (0xFF, 0xFF))   # the graphics window, written and read back
        self.assertTrue(r[7] & 0x20)                             # status: GFX fitted
        self.assertEqual(bytes(v.vram[:2]), b"OK")               # VIDEO-G TEXT: the text RAM
        self.assertEqual(m.cpu.Q, 1)
        self.assertEqual(self.bus_events(m), {})


class PanelTests(Common):
    def test_toggle_a_program_in_and_run_it(self):
        """with the EPROM fitted: LOAD mode stores the toggles at 0000 on; RUN runs them, not HBIOS (CPU Rev D's LOADED
        flag); the panel's RESET is a reset from the bus and keeps LOADED; the CPU card's own RESET / RUN switch (or
        power-on) clears it, and HBIOS boots again"""
        m = self.machine(); sh = Shell(m)
        prog = [0xE0, 0x64, 0x99, 0x7B, 0x00]                    # SEX 0; OUT 4 = 99; SEQ; IDL
        m.panel_set(run=False); m.panel_set(load=True)
        for b in prog: m.panel_set(switches=b); m.panel_set(input=True); m.panel_set(input=False)
        m.panel_set(load=False)
        self.assertEqual([m.peek(a) for a in range(len(prog))], prog)
        m.panel_set(run=True); sh.d.run(max_instructions=2000)
        self.assertEqual((m.panel.latch, m.cpu.Q), (0x99, 1))
        m.panel_set(run=False); self.assertEqual(m.cpu.Q, 0)
        m.panel_set(run=True); sh.d.run(max_instructions=2000)
        self.assertEqual((m.cpu.Q, screen(m)[-1]), (1, ""))      # RAM again: nothing typed, Q on
        m.reset(); self.until(m, sh, "test>", 4_000_000)
        self.assertEqual(self.bus_events(m), {})


# ---------------------------------------------------------------------------------------------- the whole machine
@unittest.skipUnless(os.path.exists(V5_GZ), "the Elf/OS v5 image is in the private-resources repository, not here")
class SystemTests(Common):
    def test_elfos_v5_on_the_new_cards(self):
        img = tempfile.mktemp(suffix=".img")
        with gzip.open(V5_GZ) as f, open(img, "wb") as g: g.write(f.read())
        try:
            m = self.machine(disk=img); sh = Shell(m); v = m.video
            clock = [datetime.datetime(2054, 11, 20, 9, 30, 0)]                    # 2026 in ELF/OS's years
            m.panel.rtc = DS12885(now=lambda: clock[0], start=clock[0])
            self.until(m, sh, "test>", 4_000_000)
            self.assertEqual(v.reg[6], 25)                                         # 25 rows, typing on row 24
            m.kbd.press("!6000 12 34 56\n"); self.until(m, sh, "test>", 4_000_000)  # VIDEO-G's keyboard -> the monitor -> RAM
            self.assertEqual([m.peek(0x6000 + k) for k in range(3)], [0x12, 0x34, 0x56])
            m.kbd.press("B\n"); self.until(m, sh, ":", 80_000_000)                 # B: the monitor's boot command
            self.assertEqual(screen(m)[-4:], ["V5.1.1", "", "Ready", ":"])
            m.kbd.press("ver\n"); self.until(m, sh, ":"); self.assertIn("5.1.1 Build 229", "\n".join(screen(m)))
            m.kbd.press("free\n"); self.until(m, sh, ":"); self.assertIn("Total AUs: 3906", "\n".join(screen(m)))
            m.kbd.press("dir\n"); self.until(m, sh, ":"); self.assertIn("bin/", "\n".join(screen(m)).lower())
            # cls: one program for both video cards since 2026-11-20; on VIDEO-G it clears all 25 rows
            m.kbd.press("cls\n"); self.until(m, sh, ":")
            self.assertEqual([l for l in screen(m) if l], ["Ready", ":"])
            # the IO panel's clock through HBIOS's driver (f_gettod / f_settod), as Elf/OS's programs see it
            m.kbd.press("sysinfo\n"); self.until(m, sh, ":", 80_000_000)
            self.assertIn("  RTC       : Yes (11/20/2026 09:30:00)", screen(m))
            self.assertIn("  IDE       : Yes", screen(m))
            m.kbd.press("date 1/2/2027 3:4:5\n"); self.until(m, sh, ":")
            self.assertEqual(m.panel.rtc.time(), datetime.datetime(2055, 1, 2, 3, 4, 5))
            # vgdemo (software/elfos-v5/vgdemo): words into the text RAM, a box and its diagonal into the graphics
            m.kbd.press("cls\n"); self.until(m, sh, ":")
            m.kbd.press("vgdemo\n"); sh.d.run(max_instructions=450_000)
            s = screen(m)
            self.assertEqual(s[2], "    TEXT: these words are characters in the text RAM (7000).")
            self.assertEqual(s[12], " " * 23 + "TEXT OVER GRAPHICS")
            self.assertTrue(s[21].startswith("    GRAPHICS: the box and the line are dots."))
            self.assertTrue(v.gfx_on() and v.text_on())
            self.assertEqual(v.count_pixels(), 2 * 256 + 126 * 4)                  # the box's two lines, and four dots a line
            self.assertEqual([v.pixel(x, y) for x, y in ((128, 36), (383, 36), (128, 163), (383, 163), (128, 100), (383, 100))], [1] * 6)
            self.assertEqual([v.pixel(x, y) for x, y in ((130, 37), (131, 37), (256, 100), (257, 100), (380, 162), (381, 162))], [1] * 6)
            self.assertEqual([v.pixel(x, y) for x, y in ((100, 100), (129, 100), (256, 20), (300, 100), (256, 180))], [0] * 5)
            m.kbd.press(" "); self.until(m, sh, ":")                               # a key ends it: graphics off again
            self.assertEqual(v.ctrl, 0)
            self.assertEqual(self.bus_events(m), {})
        finally:
            os.remove(img)


class FastRom(Fast, RomTests, unittest.TestCase): pass
class FastCards(Fast, CardTests, unittest.TestCase): pass
class FastPanel(Fast, PanelTests, unittest.TestCase): pass
class FastSystem(Fast, SystemTests, unittest.TestCase): pass
class HWRom(HW, RomTests, unittest.TestCase): pass
class HWCards(HW, CardTests, unittest.TestCase): pass
class HWPanel(HW, PanelTests, unittest.TestCase): pass
class HWSystem(HW, SystemTests, unittest.TestCase): pass          # (about four minutes)


if __name__ == "__main__":
    unittest.main(verbosity=1)
