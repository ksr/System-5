# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-20
"""The 6845 video card Rev B-Clean-Keyboard (hardware/video-6845/kicad/rev-b-clean-keyboard): Rev B's video with VIDEO-G
TEXT's PS/2 keyboard section on the 36-pin bus, the key at 7802 and the status at 7804. Ken, 2026-11-20: "run a full
emulator hardware and instruction with this -keyboard version".

  Card     the card alone from its netlist (hw.NetlistVideoKbdCard), cycle by cycle through its gates: what answers at
           each address, the key and KEY-READY, the flag line JP1 picks, the text RAM where Rev B has it, the 6845
           there too but write-only (Ken, 2026-11-24). What the 6845 sees inside a cycle: test_hw_crtcbus.py. Rev B-Clean's own netlist is tried here too: on the bus it must be Rev B.

Then the whole machine with this card, on both emulators, each test on a machine a `machine()` method makes (as
tests/test_newset.py does for VIDEO-G, whose ROM, panel and helper tests are used again here):
  Fast...  the instruction-level machine (machine.Video6845KbdMachine, with the IO panel)
  HW...    the hardware machine (hw.HWMachine): CPU Rev D, the memory card, the IDE card, the IO panel and this card,
           each from its netlist; the bus log must stay empty (no fight, no double drive, nothing undefined)
with the VIDEO-G HBIOS (roms/hbios-video-g.rom: it polls 7804 and reads 7802) and Elf/OS 5.1.1:
  Rom      the monitor's commands, typed on this card's keyboard: H, Q1 / Q0, D and its -- more -- key, the panel
           demo, @F1E0
  Kbd      the card as the software sees it: the text RAM through the monitor, the status and the key, the flag on
           EF3, nothing at VIDEO-G's mouse and graphics addresses
  Panel    a program toggled in from the IO panel runs, and CPU Rev D's LOADED flag decides what a reset boots
  System   Elf/OS 5.1.1 from the card image: B, ver, free, dir, cls on 25 rows, the IO panel's clock in sysinfo and
           date; vgdemo says there is no graphics board (the status register's GFX bit is 0)
The System tests need the Elf/OS v5 card image, which is in the private-resources repository (skipped without it).
"""
import datetime, gzip, os, sys, tempfile, unittest


HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from s5emu.hw import HWMachine, NetlistVideoCard, NetlistVideoKbdCard     # noqa: E402
from s5emu.machine import FLOAT, Keyboard, Video6845, Video6845KbdMachine  # noqa: E402
from s5emu.rtc import DS12885                                            # noqa: E402
from s5emu.shell import Shell                                            # noqa: E402
from test_newset import Common, PanelTests, RomTests, screen             # noqa: E402  (mixins: not test cases themselves)

ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
VG_ROM = os.path.join(HERE, "..", "roms", "hbios-video-g.rom")
V5_GZ = os.path.join(ROOT, "..", "private-resources", "elf", "reference", "mike-riley", "elfos-v5", "system5",
                     "elfos-5.1.1-system5-16mb.img.gz")
REV = "B-Clean-Keyboard"
PROMPT = "test>"                                    # HBIOS's monitor prompt


def card(flag="-EF"):
    v = Video6845(); k = Keyboard(); k.port = None
    return NetlistVideoKbdCard(v, k, REV, kbd_flag=flag), v, k


def read(c, a, vma=0, log=True):
    """-> the byte on the bus (None: nothing drives), after checking that one part at most drives and nothing is undefined"""
    drv, faults = c.bus_read(a, vma, log)
    assert not faults, faults
    assert len(drv) <= 1, drv
    return drv[0][1] if drv else None


def write(c, a, v, vma=0):
    got, faults = c.bus_write(a, vma, v)
    assert not faults, faults
    return got


class Card(unittest.TestCase):
    def test_what_answers_where(self):
        c, v, k = card()
        who = lambda a, mrd, mrw: sorted((ref, kind, op) for ref, kind, op, _ in c.decode(a, 0, mrd, mrw)[0])
        ram_r, ram_w = [("IC1", "DPRAM", "r")], [("IC1", "DPRAM", "w")]
        crtc_r, crtc_w = [], [("IC3", "CRTC", "w")]                     # write-only: its read drives nothing
        key = [("IC18", "READY", "c"), ("IC19", "KEY", "r")]; status = [("IC20", "STATUS", "r")]
        for a in (0x7000, 0x7123, 0x77FF):                              # the text RAM, all 2K of it
            self.assertEqual((who(a, 0, 1), who(a, 1, 0)), (ram_r, ram_w), "%04X" % a)
        for base in range(0x7800, 0x7C00, 8):                           # the registers, the same every 8 addresses
            self.assertEqual((who(base, 0, 1), who(base, 1, 0)), (crtc_r, crtc_w), "%04X" % base)
            self.assertEqual((who(base + 1, 0, 1), who(base + 1, 1, 0)), (crtc_r, crtc_w), "%04X" % (base + 1))
            for a in (base + 2, base + 3):
                self.assertEqual((who(a, 0, 1), who(a, 1, 0)), (key, []), "%04X" % a)       # the key: read only
            for a in (base + 4, base + 5):
                self.assertEqual((who(a, 0, 1), who(a, 1, 0)), (status, []), "%04X" % a)    # status: read only
            for a in (base + 6, base + 7):
                self.assertEqual((who(a, 0, 1), who(a, 1, 0)), ([], []), "%04X" % a)        # VIDEO-G's mouse: not here
        for a in range(0x7C00, 0x8000, 0x55):                           # A10 = 1 (VIDEO-G's graphics window): nothing
            self.assertEqual((who(a, 0, 1), who(a, 1, 0)), ([], []), "%04X" % a)
        for a in (0x6802, 0x6804, 0x8802, 0xF802, 0x0802, 0x6000, 0x8000):                   # another block: nothing
            self.assertEqual((who(a, 0, 1), who(a, 1, 0)), ([], []), "%04X" % a)
        for a in (0x7000, 0x7800, 0x7802, 0x7804):                      # -VMA high (the boot map): nothing
            self.assertEqual((c.decode(a, 1, 0, 1), c.decode(a, 1, 1, 0)), (((), ()), ((), ())), "%04X" % a)

    def test_no_cycle_is_undefined(self):
        c, v, k = card()
        for a in list(range(0x7000, 0x8000, 0x21)) + list(range(0x7800, 0x7810)) + list(range(0, 0x10000, 0x0333)):
            for vma in (0, 1):
                for mrd, mrw in ((0, 1), (1, 0)):
                    self.assertEqual(c.decode(a, vma, mrd, mrw)[1], (), "%04X vma %d" % (a, vma))

    def test_a_key(self):
        c, v, k = card()
        self.assertEqual(read(c, 0x7804), 0x80)                         # nothing waiting: bit 7 alone
        self.assertFalse(c.ef("-EF"))
        k.press("A")
        self.assertTrue(c.ef("-EF"))                                    # the ATmega loads the latch and sets KEY-READY
        self.assertEqual(read(c, 0x7804), 0x81)
        self.assertEqual(read(c, 0x7804), 0x81)                         # reading the status clears nothing
        self.assertEqual(read(c, 0x7802, log=False), 0x41)              # a look (the debugger's) clears nothing
        self.assertEqual(read(c, 0x7804), 0x81)
        self.assertEqual(read(c, 0x7802), 0x41)                         # the read takes the key and clears KEY-READY
        self.assertEqual(read(c, 0x7804), 0x80)
        self.assertFalse(c.ef("-EF"))
        self.assertEqual(read(c, 0x7802), 0x41)                         # the latch keeps its byte (no new key)

    def test_keys_one_at_a_time(self):
        c, v, k = card()
        k.press("ok\n"); got = []
        for _ in range(3):
            self.assertEqual(read(c, 0x7804) & 1, 1)
            got.append(read(c, 0x7802))
        self.assertEqual(got, [ord("o"), ord("k"), 0x0D])
        self.assertEqual(read(c, 0x7804), 0x80)

    def test_every_code_bit_reaches_its_data_line(self):
        c, v, k = card()
        for code in [1 << i for i in range(8)] + [0x55, 0xAA, 0xFF, 0x00]:
            k.queue.append(code)
            self.assertEqual(read(c, 0x7804), 0x81)
            self.assertEqual(read(c, 0x7802), code, "%02X" % code)

    def test_writes_to_the_keyboard_addresses_do_nothing(self):
        c, v, k = card()
        k.press("Z"); c.ef("-EF")
        before = (list(v.reg), v.sel, bytes(v.vram))
        for a in (0x7802, 0x7803, 0x7804, 0x7805, 0x7806, 0x7807, 0x7C00, 0x7FFF):
            self.assertEqual(write(c, a, 0x5A), [], "%04X" % a)         # (VIDEO-G's HBIOS writes 00 to 7804 at start)
        self.assertEqual((list(v.reg), v.sel, bytes(v.vram)), before)
        self.assertEqual(read(c, 0x7804), 0x81)                         # and the key still waits
        self.assertEqual(read(c, 0x7802), ord("Z"))

    def test_reset_clears_key_ready(self):
        c, v, k = card()
        k.press("Q"); self.assertTrue(c.ef("-EF"))
        c.reset()
        self.assertEqual(read(c, 0x7804), 0x80)

    def test_the_flag_line_is_the_one_jp1_picks(self):
        lines = ("-EF1", "-EF2", "-EF3", "-EF")
        for flag in lines + (None,):
            c, v, k = card(flag)
            self.assertEqual([c.ef(x) for x in lines], [False] * 4, flag)
            k.press("x")
            self.assertEqual([c.ef(x) for x in lines], [x == flag for x in lines], flag)
            self.assertEqual(read(c, 0x7804), 0x81)                     # whatever the shunt, the status has it
            self.assertEqual(read(c, 0x7802), ord("x"))
            self.assertEqual([c.ef(x) for x in lines], [False] * 4, flag)

    def test_the_6845_and_the_text_ram(self):
        c, v, k = card()
        self.assertEqual(write(c, 0x7800, 14), ["6845 IC3"])            # the address register, then the data
        self.assertEqual(write(c, 0x7801, 0x12), ["6845 IC3"])
        self.assertEqual(write(c, 0x7800, 15), ["6845 IC3"]); write(c, 0x7801, 0x34)
        self.assertEqual((v.reg[14], v.reg[15]), (0x12, 0x34))
        write(c, 0x7808, 14); write(c, 0x7809, 0x2A); self.assertEqual(v.reg[14], 0x2A)       # the pair again, 8 further on
        for a in (0x7800, 0x7801, 0x7808, 0x7BF9): self.assertIsNone(read(c, a), "%04X" % a)  # write-only: nothing drives
        self.assertEqual((v.sel, v.reg[14], v.reg[15]), (14, 0x2A, 0x34))                     # and a read changes nothing
        for a, b in ((0x7000, 0x48), (0x7001, 0x49), (0x763F, 0x21), (0x77FF, 0x7E)):
            self.assertEqual(write(c, a, b), ["6845 IC1"]); self.assertEqual(read(c, a), b)
        self.assertEqual(v.vram[0], 0x48); self.assertEqual(v.vram[0x7FF], 0x7E)

    def test_rev_b_clean_is_rev_b_on_the_bus(self):
        """Rev B-Clean's netlist (no DE-9, the light-pen input on ground) against Rev B's, the card in the machine"""
        b, bc = NetlistVideoCard(Video6845(), "B"), NetlistVideoCard(Video6845(), "B-Clean")
        strip = lambda r: (sorted((kind, op, ca) for _, kind, op, ca in r[0]), r[1])
        for a in list(range(0x6FF0, 0x7010)) + list(range(0x77F0, 0x7810)) + list(range(0x7000, 0x8000, 0x37)) + list(range(0, 0x10000, 0x0111)):
            for vma in (0, 1):
                for mrd, mrw in ((0, 1), (1, 0)):
                    self.assertEqual(strip(bc.decode(a, vma, mrd, mrw)), strip(b.decode(a, vma, mrd, mrw)), "%04X vma %d" % (a, vma))


# ---------------------------------------------------------------------------------------------- the two machines
class Fast:
    """the instruction-level machine: the card and the IO panel as behaviour"""
    def machine(self, rom=VG_ROM, disk=None):
        return Video6845KbdMachine(cpu_rom=rom, disk=disk, panel=True)

    def bus_events(self, m):
        return {}                                   # it keeps no bus log


class HW:
    """the hardware machine: CPU Rev D, the memory card, the IDE card, the IO panel and this card, each from its netlist"""
    def machine(self, rom=VG_ROM, disk=None, flag="-EF"):
        return HWMachine(cpu_rom=rom, disk=disk, mem_rev="D", cpu_rev="D", ide_rev="A", panel_rev="A", video_rev=REV,
                         kbd_flag=flag, mhz=2.0)

    def bus_events(self, m):
        return m.log.events


class KbdTests(Common):
    def boot(self):
        m = self.machine(); sh = Shell(m); self.until(m, sh, PROMPT, 4_000_000)
        return m, sh

    def test_25_rows_and_the_text_ram(self):
        m, sh = self.boot()
        self.assertEqual((len(screen(m)), m.video.reg[1], m.video.reg[6]), (25, 64, 25))     # the VIDEO-G HBIOS's table
        m.kbd.press("!7000 53 35 2D 4B\n"); self.until(m, sh, PROMPT, 4_000_000)             # the monitor writes the RAM
        self.assertEqual(bytes(m.video.vram[0:4]), b"S5-K")
        self.assertEqual([m.peek(0x7000 + k) for k in range(4)], [0x53, 0x35, 0x2D, 0x4B])
        self.assertEqual(self.bus_events(m), {})

    def test_the_status_the_key_and_the_flag(self):
        m, sh = self.boot()
        self.assertEqual((m.peek(0x7804), m.ef(3)), (0x80, False))      # nothing waiting; EF3 is the bus -EF on CPU Rev D
        m.kbd.queue.append(0x51)
        self.assertEqual((m.peek(0x7804), m.ef(3)), (0x81, True))       # KEY-READY: in the status and on the flag line
        self.assertEqual(m.peek(0x7804), 0x81)                          # a look takes nothing
        sh.d.run(max_instructions=20_000)                               # the monitor reads the key at 7802 and echoes it
        self.assertEqual((m.peek(0x7804), m.ef(3)), (0x80, False))
        self.assertEqual(screen(m)[-1], PROMPT + "Q")
        self.assertEqual(self.bus_events(m), {})

    def test_nothing_at_videogs_other_addresses(self):
        m, sh = self.boot()
        before = (bytes(m.video.vram), list(m.video.reg), m.video.sel)
        for a in (0x7806, 0x7807, 0x7C00, 0x7C3F, 0x7FFF):              # VIDEO-G's mouse / Y register and its window
            self.assertEqual(m.peek(a), FLOAT, "%04X" % a)
            m.write(a, 0x5A)
        for a in (0x7802, 0x7804):                                      # the key and the status take no write
            m.write(a, 0x00)                                            # (the VIDEO-G HBIOS writes 00 to 7804 at start)
        self.assertEqual((bytes(m.video.vram), list(m.video.reg), m.video.sel), before)
        self.assertEqual(self.bus_events(m), {})

    def test_the_6845_at_7800_and_every_8_addresses(self):
        m, sh = self.boot()
        m.write(0x7800, 14); m.write(0x7801, 0x02); m.write(0x7808, 15); m.write(0x7809, 0x7F)
        self.assertEqual((m.video.reg[14], m.video.reg[15]), (0x02, 0x7F))
        m.write(0x7BF8, 14); m.write(0x7BF9, 0x01); self.assertEqual(m.video.reg[14], 0x01)
        self.assertEqual(self.bus_events(m), {})

    def test_the_6845_is_write_only(self):
        """nothing drives a read of 7800 / 7801: the bus's pull-ups read (FF on the bus Rev D), and the registers stay"""
        m, sh = self.boot(); before = (list(m.video.reg), m.video.sel)
        for a in (0x7800, 0x7801, 0x7808, 0x7BF9):
            self.assertEqual((m.peek(a), m.read(a)), (FLOAT, FLOAT), "%04X" % a)
        self.assertEqual((list(m.video.reg), m.video.sel), before)
        self.assertEqual(self.bus_events(m), {})

    def test_a_ram_probe_stops_at_the_6845(self):
        """the ways HBIOS and the Elf/OS kernel look for the top of RAM (write over a byte, read it back): no RAM at 7800"""
        m, sh = self.boot(); sel = m.video.sel
        b = m.read(0x7800); m.write(0x7800, b ^ 0xFF); self.assertNotEqual(m.read(0x7800), b ^ 0xFF)       # HBIOS (FE87)
        m.write(0x7800, b)
        m.write(0x7800, 0x00); self.assertNotEqual(m.read(0x7800), 0x00)                                    # the kernel (23CE)
        m.write(0x7800, sel); self.assertEqual(self.bus_events(m), {})


@unittest.skipUnless(os.path.exists(V5_GZ), "the Elf/OS v5 image is in the private-resources repository, not here")
class SystemTests(Common):
    def test_elfos_v5_on_this_card(self):
        img = tempfile.mktemp(suffix=".img")
        with gzip.open(V5_GZ) as f, open(img, "wb") as g: g.write(f.read())
        try:
            m = self.machine(disk=img); sh = Shell(m); v = m.video
            probes = []; real = m.read                                             # every program's read of the 6845
            def read(a):
                b = real(a)
                if a & 0xFC06 == 0x7800: probes.append((a, b))
                return b
            m.read = read
            clock = [datetime.datetime(2054, 11, 20, 9, 30, 0)]                    # 2026 in ELF/OS's years
            m.panel.rtc = DS12885(now=lambda: clock[0], start=clock[0])
            self.until(m, sh, PROMPT, 4_000_000)
            self.assertEqual(v.reg[6], 25)                                         # 25 rows, typing on row 24
            m.kbd.press("!6000 12 34 56\n"); self.until(m, sh, PROMPT, 4_000_000)  # this card's keyboard -> the monitor -> RAM
            self.assertEqual([m.peek(0x6000 + k) for k in range(3)], [0x12, 0x34, 0x56])
            m.kbd.press("B\n"); self.until(m, sh, ":", 80_000_000)                 # B: the monitor's boot command
            self.assertEqual(screen(m)[-4:], ["V5.1.1", "", "Ready", ":"])
            m.kbd.press("ver\n"); self.until(m, sh, ":"); self.assertIn("5.1.1 Build 229", "\n".join(screen(m)))
            m.kbd.press("free\n"); self.until(m, sh, ":"); self.assertIn("Total AUs: 3906", "\n".join(screen(m)))
            m.kbd.press("dir\n"); self.until(m, sh, ":"); self.assertIn("bin/", "\n".join(screen(m)).lower())
            m.kbd.press("cls\n"); self.until(m, sh, ":")                           # cls clears all 25 rows
            self.assertEqual([l for l in screen(m) if l], ["Ready", ":"])
            # the IO panel's clock through HBIOS's driver (f_gettod / f_settod), as Elf/OS's programs see it
            m.kbd.press("sysinfo\n"); self.until(m, sh, ":", 80_000_000)
            self.assertIn("  RTC       : Yes (11/20/2026 09:30:00)", screen(m))
            self.assertIn("  IDE       : Yes", screen(m))
            m.kbd.press("date 1/2/2027 3:4:5\n"); self.until(m, sh, ":")
            self.assertEqual(m.panel.rtc.time(), datetime.datetime(2055, 1, 2, 3, 4, 5))
            # vgdemo looks for VIDEO-G's graphics board in the status register (bits 7-5 = 101): not on this card
            m.kbd.press("vgdemo\n"); self.until(m, sh, ":")
            self.assertIn("vgdemo needs the VIDEO-G card with its GFX board", screen(m))
            self.assertEqual(self.bus_events(m), {})
            self.assertTrue(probes); self.assertEqual(set(probes), {(0x7800, FLOAT)})  # only the RAM probes, and nothing drove
        finally:
            os.remove(img)


class HWFlag(HW, Common, unittest.TestCase):
    def test_the_flag_follows_jp1(self):
        """CPU Rev D's EF3 block is on the bus -EF (its jumpers as the emulator fits them): a waiting key shows there with
        JP1 on -EF, and not with JP1 on -EF1 or with no shunt, while the status register has it either way"""
        for flag, want in (("-EF", True), ("-EF1", False), (None, False)):
            m = self.machine(flag=flag); sh = Shell(m); self.until(m, sh, PROMPT, 4_000_000)
            self.assertFalse(m.ef(3))
            m.kbd.queue.append(0x41)
            self.assertEqual((m.ef(3), m.peek(0x7804)), (want, 0x81), flag)

    def test_what_the_machine_says_it_is(self):
        m = self.machine(); text = m.describe()
        self.assertIn("6845 card B-Clean-Keyboard", text); self.assertIn("the 6845 card has the keyboard", text)
        sh = Shell(m); self.until(m, sh, PROMPT, 4_000_000)
        rows = {l.split()[0]: l for l in m.bus_map().splitlines()}
        self.assertIn("6845 IC1", rows["7000"]); self.assertIn("nothing", rows["7800"])      # (write-only)


class FastRom(Fast, RomTests, unittest.TestCase): pass
class FastKbd(Fast, KbdTests, unittest.TestCase): pass
class FastPanel(Fast, PanelTests, unittest.TestCase): pass
class FastSystem(Fast, SystemTests, unittest.TestCase): pass
class HWRom(HW, RomTests, unittest.TestCase): pass
class HWKbd(HW, KbdTests, unittest.TestCase): pass
class HWPanel(HW, PanelTests, unittest.TestCase): pass
class HWSystem(HW, SystemTests, unittest.TestCase): pass          # (about four minutes)


if __name__ == "__main__":
    unittest.main()
