# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-06
"""System-5 machine tests: real ROM boot, keyboard, 1861 DMA, IDE, memory-card jumpers, ELF/OS boot."""
import os, sys, unittest, tempfile, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, ".."))
from s5emu.machine import Machine
from s5emu.shell import Shell
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
ROM09 = os.path.join(ROOT, "firmware/hbios/v0.9/sec1.rom")
ROM104 = os.path.join(HERE, "..", "roms", "hbios-1.0.4.rom")
ROM105 = os.path.join(HERE, "..", "roms", "hbios-1.0.5.rom")
ROM106 = os.path.join(HERE, "..", "roms", "hbios-1.0.6.rom")
ROM107 = os.path.join(HERE, "..", "roms", "hbios-1.0.7.rom")
ROM108 = os.path.join(HERE, "..", "roms", "hbios-1.0.8.rom")
# Elf/OS v5 is third-party and unlicensed: its image is kept in the private repository beside this one
V5_GZ = os.path.join(ROOT, "..", "private-resources", "elf", "reference", "mike-riley", "elfos-v5", "system5",
                     "elfos-5.1.1-system5-16mb.img.gz")
# so is ELF/OS 0.2.6 (Mike Riley's 2004-05 kernel, programs and disktool), which tools/mkelfos.py makes a disk from
sys.path.insert(0, os.path.join(HERE, "..", "tools"))
import mkelfos                                                  # noqa: E402
ELFOS026 = not mkelfos.missing()
NO_ELFOS026 = "ELF/OS 0.2.6 is in the private-resources repository, not here (tools/mkelfos.py)"


class T(unittest.TestCase):
    def test_hbios_monitor_boots(self):
        m = Machine(cpu_rom=ROM09); sh = Shell(m)
        sh.d.run(max_instructions=1_000_000)
        self.assertEqual(m.video.lines()[-1].rstrip(), "TEST>")
        self.assertFalse(m.cpurom.remap)                       # the jump to F000 turned the reset remap off

    def test_keyboard_echo(self):
        m = Machine(cpu_rom=ROM09); sh = Shell(m); sh.d.run(max_instructions=1_000_000)
        m.kbd.press("X"); sh.d.run(max_instructions=200_000)
        self.assertTrue(m.video.lines()[-1].startswith("TEST>X"))

    def test_memory_jumpers(self):
        m = Machine(jumpers=["RAM"] * 7 + [None] + ["ROM"] * 8)
        m.cpurom.remap = False
        m.write(0x1000, 0x42); self.assertEqual(m.read(0x1000), 0x42)
        m.memory.rom[0x9000] = 0x77; m.write(0x9000, 0); self.assertEqual(m.read(0x9000), 0x77)   # ROM ignores writes
        self.assertEqual(m.read(0x7900), 0xFF)                # open block above the video RAM floats

    def test_video_crtc(self):
        m = Machine(); m.cpurom.remap = False
        m.write(0x7000, ord("H")); m.write(0x7001, ord("i")); self.assertTrue(m.video.lines()[0].startswith("Hi"))
        m.write(0x7800, 14); m.write(0x7801, 0); m.write(0x7800, 15); m.write(0x7801, 65)
        self.assertEqual(m.video.cursor(), (1, 1))

    def test_1861_dma(self):
        # interrupt routine at 0030/0032 points R0 at a 1K picture at 0200; main loop: INP 4 (display on), BR
        prog = [0xF8, 0x00, 0xB1, 0xB2, 0xB3, 0xF8, 0x32, 0xA1, 0xF8, 0xFF, 0xA2, 0xF8, 0x10, 0xA3, 0xE2, 0xD3,
                0x6C, 0x30, 0x11]
        isr = [0x72, 0x70, 0x22, 0x78, 0x22, 0x52, 0xF8, 0x02, 0xB0, 0xF8, 0x00, 0xA0, 0x30, 0x30]
        m = Machine(); m.cpurom.remap = False
        for i, b in enumerate(prog): m.write(i, b)
        for i, b in enumerate(isr): m.write(0x30 + i, b)
        pic = bytes((0xAA if (r // 4) % 2 else 0x55) for r in range(128) for _ in range(8))
        for i, b in enumerate(pic): m.write(0x200 + i, b)
        for _ in range(60_000): m.step()
        self.assertTrue(m.pixie.on); self.assertGreater(m.pixie.frames, 2)
        self.assertEqual(bytes(m.pixie.frame), pic)

    def test_ide_read_write(self):
        from s5emu.machine import IDE
        ide = IDE(sectors=64)
        def regs(lba, cmd):
            for r, v in ((2, 1), (3, lba & 0xFF), (4, 0), (5, 0), (6, 0xE0)): ide.out(2, r); ide.out(3, v)
            ide.out(2, 7); ide.out(3, cmd)
        regs(5, 0x30); ide.out(2, 0)
        for i in range(512): ide.out(3, i & 0xFF)
        regs(5, 0x20); ide.out(2, 7); self.assertTrue(ide.inp(3) & ide.DRQ); ide.out(2, 0)
        self.assertEqual(bytes(ide.inp(3) for _ in range(512)), bytes(i & 0xFF for i in range(512)))

    def test_ide_chs_and_end_of_card(self):
        """register 6 bit 6 picks LBA or CHS, as on the real card, and an address not on the card is ERR with ID not
        found (10h) and no DRQ, for a write as for a read (2026-11-15: Elf/OS v5's 00 in register 6 hung the machine)"""
        from s5emu.machine import IDE
        ide = IDE(sectors=16 * 63 * 3)                 # three cylinders of 16 heads x 63 sectors
        for l in (0, 1, 2, 1008): ide.disk[l * 512:(l + 1) * 512] = bytes([l & 0xFF]) * 512
        def cmd(c, r3, r4, r6, r5=0):
            for r, v in ((2, 1), (3, r3), (4, r4), (5, r5), (6, r6)): ide.out(2, r); ide.out(3, v)
            ide.out(2, 7); ide.out(3, c); st = ide.inp(3); ide.out(2, 1); return st, ide.inp(3)
        def read(*a):
            st, err = cmd(0x20, *a)
            if not st & ide.DRQ: return st & ide.ERR, err, None
            ide.out(2, 0); return st & ide.ERR, err, bytes(ide.inp(3) for _ in range(512))[:1]
        self.assertEqual(read(1, 0, 0xE0), (0, 0, b"\x01"))                 # LBA mode, as HBIOS sends: LBA 1
        self.assertEqual(read(1, 0, 0x00), (0, 0, b"\x00"))                 # CHS: sector 1 is the first, LBA 0
        self.assertEqual(read(2, 0, 0x00), (0, 0, b"\x01"))                 # (cylinder 0, head 0, sector 2): LBA 1
        self.assertEqual(read(1, 1, 0x00), (0, 0, bytes([1008 & 0xFF])))   # (cylinder 1, head 0, sector 1): LBA 1008
        for bad in ((0, 0, 0x00), (1, 3, 0x00), (64, 0, 0x00), (0xD0, 0x0B, 0xE0)):   # sector 0, cylinder 3, sector 64,
            self.assertEqual(read(*bad), (ide.ERR, ide.IDNF, None), bad)              # LBA 3024: none is on the card
        before = bytes(ide.disk)                                            # a write past the end: refused, and the
        self.assertEqual(cmd(0x30, 0xD0, 0x0B, 0xE0), (ide.DRDY | ide.ERR, ide.IDNF))   # data sent after it lands
        ide.out(2, 0)                                                       # nowhere
        for _ in range(512): ide.out(3, 0x55)
        self.assertEqual(bytes(ide.disk), before)
        self.assertEqual(read(2, 0, 0xE0), (0, 0, b"\x02"))                # the next good command works again

    @unittest.skipUnless(os.path.exists(ROM106), "build firmware/hbios/v1.0.6 first")
    def test_hbios_106_reads_in_lba_mode(self):
        """HBIOS 1.0.6 sends E0h in register 6 whatever R8.1 holds: a boot loader reading sector 0 with R8 = 0000, as
        Elf/OS v5 reads, gets ERR (ID not found) on 1.0.4 and 1.0.5, and the sector on 1.0.6 (2026-11-15) and on
        1.0.7, which keeps 1.0.6's LBA code"""
        loader = bytes([0x90, 0xB3, 0xF8, 0x06, 0xA3, 0xD3,      # 0100 R3 = 0106, SEP R3, as v5's boot loader starts
                        0xF8, 0x00, 0xA7, 0xB7, 0xA8, 0xB8,      # 0106 R7 = 0000, R8 = 0000: R8.1 = 00, as v5 passes
                        0xF8, 0x03, 0xBF, 0xF8, 0x00, 0xAF,      # 010C RF = 0300, the buffer
                        0xD4, 0xFF, 0x3C,                        # 0112 CALL f_ideread (DF = error)
                        0xF8, 0x02, 0xBF, 0xF8, 0x00, 0xAF,      # 0115 RF = 0200
                        0x3B, 0x21, 0xF8, 0x45, 0x30, 0x23,      # 011B BNF 0121; LDI 'E'; BR 0123
                        0xF8, 0x4F, 0x5F, 0x30, 0x24])           # 0121 LDI 'O'; 0123 STR RF; 0124 BR 0124
        img = tempfile.mktemp(suffix=".img")
        with open(img, "wb") as f: f.write(loader.ljust(512, b"\0") + bytes(512 * (16 * 63 * 2 - 1)))
        try:
            for rom, ok in ((ROM104, False), (ROM105, False), (ROM106, True), (ROM107, True)):
                m = Machine(cpu_rom=rom, disk=img); sh = Shell(m)
                sh.d.run(max_instructions=2_000_000); m.kbd.press("@FF00\n"); sh.d.run(max_instructions=2_000_000)
                self.assertEqual(chr(m.peek(0x0200)), "O" if ok else "E", os.path.basename(rom))
                if ok: self.assertEqual(bytes(m.peek(0x0300 + i) for i in range(len(loader))), loader)
                else: self.assertEqual(m.ide.error, m.ide.IDNF)
        finally:
            os.remove(img)

    @unittest.skipUnless(os.path.exists(ROM108), "build firmware/hbios/v1.0.8 first")
    def test_hbios_108_clock_on_the_io_panel(self):
        """v1.0.8 (2026-11-18): f_gettod / f_settod through the IO panel's DS12885 on ports 6 and 7, as Mike's BIOS
        answers them for the ELF2000 (RF at month, day, year since 1972, hour, minute, second); f_getdev's bit 4. A new
        chip (oscillator off) or no clock at all: f_gettod returns DF = 1. The ROM is v1.0.7 but for the driver."""
        import datetime
        from s5emu.rtc import DS12885
        with open(ROM107, "rb") as f: r107 = f.read()
        with open(ROM108, "rb") as f: r108 = f.read()
        diff = [0xF000 + i for i in range(4096) if r107[i] != r108[i]]
        self.assertTrue(diff and all(0xFC92 <= a <= 0xFCFF or 0xF7CD <= a <= 0xF7FF or a in (0xF816, 0xF817, 0xF819, 0xF81A, 0xFEDC)
                                     for a in diff))
        call = lambda at, fn, rf: bytes([0x90, 0xB3, 0xF8, (at + 6) & 0xFF, 0xA3, 0xD3,   # R3 = at + 6, SEP R3 (@ starts P = 0)
                                         0xE2,                                     # SEX R2: SCRT wants X = 2
                                         0xF8, rf >> 8, 0xBF, 0xF8, rf & 0xFF, 0xAF,  # RF
                                         0xD4, fn >> 8, fn & 0xFF,                 # CALL fn
                                         0xF8, 0x02, 0xBA, 0xF8, (at >> 4 & 0xF0) | 0x00, 0xAA,  # RA = 02x0: the result
                                         0x3B, (at + 0x1C) & 0xFF,                 # BNF ok
                                         0xF8, 0x45, 0x30, (at + 0x1E) & 0xFF,     # 'E' (DF = 1)
                                         0xF8, 0x4F,                               # ok: 'O'
                                         0x5A, 0x1A, 0x8F, 0x5A, 0x1A, 0x9F, 0x5A, # STR RA; RF after it, low then high
                                         0x30, (at + 0x25) & 0xFF])                # and stop: BR to itself
        clock = [datetime.datetime(2026, 11, 18, 1, 30, 0)]
        rtc = DS12885(now=lambda: clock[0])                                    # a new chip: the oscillator off

        def run_call(fn, rf, data=b"", panel=True):
            m = Machine(cpu_rom=ROM108, panel=panel); sh = Shell(m)
            if panel: m.panel.rtc = rtc
            sh.d.run(max_instructions=2_000_000)
            for i, b in enumerate(call(0x0100, fn, rf)): m.write(0x0100 + i, b)
            for i, b in enumerate(data): m.write(rf + i, b)
            m.kbd.press("@0100\n"); sh.d.run(max_instructions=1_000_000)
            return m, chr(m.peek(0x0210))
        m, r = run_call(0xF815, 0x0300); self.assertEqual(r, "E")             # not set yet
        m, r = run_call(0xF818, 0x0300, bytes([11, 18, 54, 1, 30, 0]))         # 2026-11-18 01:30:00 (54 = 2026 - 1972)
        self.assertEqual(r, "O"); self.assertTrue(rtc.running())
        self.assertEqual((rtc.ram[0x0A], rtc.ram[0x0B]), (0x20, 0x06))         # oscillator on; binary, 24-hour, counting
        self.assertEqual(rtc.time(), datetime.datetime(2054, 11, 18, 1, 30, 0))
        clock[0] += datetime.timedelta(seconds=61)
        m, r = run_call(0xF815, 0x0300); self.assertEqual(r, "O")
        self.assertEqual([m.peek(0x0300 + i) for i in range(6)], [11, 18, 54, 1, 31, 1])
        self.assertEqual(m.peek(0x0211) | m.peek(0x0212) << 8, 0x0306)         # RF after the six bytes
        m, r = run_call(0xFF81, 0x0000); self.assertEqual(m.peek(0x0211) | m.peek(0x0212) << 8, 0x0015)   # f_getdev
        m, r = run_call(0xF815, 0x0300, panel=False); self.assertEqual(r, "E")  # no IO panel: no clock

    @unittest.skipUnless(os.path.exists(ROM107), "build firmware/hbios/v1.0.7 first")
    def test_hbios_107_key_codes_on_screen(self):
        """v1.0.7's @F1E0 (Ken, 2026-11-17), self-contained: it waits for the keyboard's flag (EF3), reads the key
        (INP 1) and writes its code as text, "0x31" for the key 1, straight into the video RAM at the start of the
        bottom line, over the one before; it calls nothing in the BIOS, so nothing else on the screen changes. The ROM
        is v1.0.6 with only that added (a jump at F1E0-F1E2, the routine at FC50-FC91), so H's list is v1.0.6's"""
        with open(ROM106, "rb") as f: r106 = f.read()
        with open(ROM107, "rb") as f: r107 = f.read()
        diff = [0xF000 + i for i in range(4096) if r106[i] != r107[i]]
        self.assertEqual(diff[:3], [0xF1E0, 0xF1E1, 0xF1E2])
        self.assertTrue(diff[3:] and all(0xFC50 <= a <= 0xFC91 for a in diff[3:]))
        m = Machine(cpu_rom=ROM107); sh = Shell(m); run = lambda n=1_500_000: sh.d.run(max_instructions=n)
        lines = lambda: [l.rstrip() for l in m.video.lines()]
        run(2_000_000)
        m.kbd.press("H\n"); run()
        self.assertEqual([l for l in lines() if l][-2:], [" H               this list", "test>"])
        m.kbd.press("@F1E0\n"); run()
        above = lines()[:-1]
        for key, shown in (("1", "0x31"), ('"', "0x22"), ("'", "0x27"), ("a", "0x61"), ("A", "0x41"),
                           ("\x1b", "0x1B"), ("\r", "0x0D"), ("~", "0x7E"), ("\x7f", "0x7F")):
            m.kbd.press(key); run(300_000)
            self.assertEqual(lines()[-1], shown, repr(key))
            self.assertEqual(lines()[:-1], above, repr(key))        # only the bottom line changes: nothing is typed
            self.assertEqual(m.video.cursor(), (15, 4), repr(key))  # the cursor just after the text
        n = m.cpu.instructions; run(200_000)                       # no key: it goes on waiting, the text stays
        self.assertGreater(m.cpu.instructions, n); self.assertEqual(lines()[-1], "0x7F")
        self.assertEqual((m.cpu.P, m.cpu.R[0]), (0, 0xFC64))       # in its wait for the keyboard's flag

    @unittest.skipUnless(os.path.exists(ROM104), "run tools/mkrom.py first")
    @unittest.skipUnless(ELFOS026, NO_ELFOS026)
    def test_elfos_boots_from_disk(self):
        img = tempfile.mktemp(suffix=".img")
        subprocess.run([sys.executable, os.path.join(HERE, "..", "tools", "mkelfos.py"), img, "--mb", "4"], check=True, capture_output=True)
        m = Machine(cpu_rom=ROM104, disk=img); sh = Shell(m); run = lambda n=3_000_000: sh.d.run(max_instructions=n)
        run(); m.kbd.press("@FF00\n"); run(); m.kbd.press("\n"); run()
        m.kbd.press("FREE\n"); run(20_000_000)
        screen = "\n".join(m.video.lines())
        self.assertIn("Elf/OS Ready", screen); self.assertIn("Total AUs", screen)
        os.remove(img)

    @unittest.skipUnless(os.path.exists(V5_GZ) and os.path.exists(ROM108), "needs the Elf/OS v5 image and HBIOS v1.0.8")
    def test_elfos_v5_reads_and_sets_the_io_panels_clock(self):
        """Elf/OS v5 on HBIOS v1.0.8 with the IO panel's DS12885 (2026-11-18): sysinfo finds the clock and shows its time
        (ELF/OS's year is years since 1972: the clock holds 54 for 2026); `date` sets it through f_settod and reads it
        back, across the turn of the year"""
        import datetime, gzip
        from s5emu.rtc import DS12885
        img = tempfile.mktemp(suffix=".img")
        with gzip.open(V5_GZ) as f, open(img, "wb") as g: g.write(f.read())
        try:
            m = Machine(cpu_rom=ROM108, disk=img, panel=True); sh = Shell(m)
            clock = [datetime.datetime(2054, 11, 18, 2, 30, 0)]
            m.panel.rtc = DS12885(now=lambda: clock[0], start=clock[0])
            def until(prompt, cap=10_000_000):
                for _ in range(0, cap, 250_000):
                    sh.d.run(max_instructions=250_000)
                    if not m.kbd.queue and m.video.lines()[-1].rstrip() == prompt: return
                self.fail("no %r prompt; the screen:\n%s" % (prompt, "\n".join(m.video.lines())))
            def run(cmd):
                m.kbd.press("cls\n"); until(":"); m.kbd.press(cmd + "\n"); until(":")
                return [l.rstrip() for l in m.video.lines()]
            until("test>"); m.kbd.press("B\n"); until(":")
            self.assertIn("  RTC       : Yes (11/18/2026 02:30:00)", run("sysinfo"))
            self.assertIn("11/18/2026 2:30:0", run("date"))
            run("date 12/31/2026 23:59:50")
            self.assertEqual((m.panel.rtc.time(), m.panel.rtc.ram[0x0A], m.panel.rtc.ram[0x0B]),
                             (datetime.datetime(2054, 12, 31, 23, 59, 50), 0x20, 0x06))
            clock[0] += datetime.timedelta(seconds=15)
            screen = run("date"); self.assertTrue(any(l.startswith("1/1/2027 0:0:5") for l in screen), "\n".join(screen))
        finally:
            os.remove(img)

    @unittest.skipUnless(os.path.exists(V5_GZ), "the Elf/OS v5 image is in the private-resources repository, not here")
    def test_elfos_v5_boots_from_disk(self):
        """Mike Riley's Elf/OS v5: the System-5 image (kernel 5.1.1 build 229, patched to keep its stack below the video
        RAM) boots on HBIOS 1.0.6 with the IO panel fitted, as a Codespace runs it. On 1.0.5 and 1.0.4 it hangs before
        its first message, as the real machine did (2026-11-15): v5 reads with 00 in register 6, a CHS address the card
        refuses, and 1.0.6 is the HBIOS that sets E0h itself"""
        import gzip
        for rom, boot in ((ROM106, "B\n"), (ROM105, "B\n"), (ROM104, "@FF00\n")):
            img = tempfile.mktemp(suffix=".img")
            with gzip.open(V5_GZ) as f, open(img, "wb") as g: g.write(f.read())
            m = Machine(cpu_rom=rom, disk=img, panel=True); sh = Shell(m)
            def until(prompt, cap=8_000_000):               # run until the keys are used up and the prompt is back
                for _ in range(0, cap, 250_000):
                    sh.d.run(max_instructions=250_000)
                    if not m.kbd.queue and m.video.lines()[-1].rstrip() == prompt: return
                self.fail("no %r prompt; the screen:\n%s" % (prompt, "\n".join(m.video.lines())))
            until("test>"); m.kbd.press(boot)
            if rom != ROM106:                               # the kernel's first read is refused: nothing more appears
                sh.d.run(max_instructions=4_000_000)
                self.assertFalse(any("Ready" in l or "Starting" in l for l in m.video.lines()), os.path.basename(rom))
                self.assertEqual((m.ide.status & m.ide.ERR, m.ide.error), (m.ide.ERR, m.ide.IDNF))
                os.remove(img); continue
            until(":")
            self.assertEqual([l.rstrip() for l in m.video.lines()][-4:], ["V5.1.1", "", "Ready", ":"])
            m.kbd.press("ver\n"); until(":"); m.kbd.press("free\n"); until(":")
            screen = "\n".join(m.video.lines())
            self.assertIn("5.1.1 Build 229", screen); self.assertIn("Total AUs: 3906", screen)
            # cls: Mike Riley's types the ANSI codes ESC[H ESC[2J, which HBIOS's screen showed as "[H[2J"; the image has
            # the System-5 one (software/elfos-v5/cls), which writes spaces over the screen
            m.kbd.press("cls\n"); until(":")
            self.assertEqual([l.rstrip() for l in m.video.lines() if l.strip()], ["Ready", ":"])
            if rom == ROM106:       # sysinfo tells the CPU by opcode 68 (68 B7: RNX R7 on an 1805), which an 1802 runs as
                m.kbd.press("sysinfo\n"); until(":")    # an INP of no port; the emulator once stopped there
                screen = "\n".join(l.rstrip() for l in m.video.lines())
                self.assertIn("  IDE       : Yes", screen); self.assertFalse(m.pixie.on)   # and no card saw an input
                m.kbd.press("cls\n"); until(":"); m.kbd.press("sysinfo\n")
                for _ in range(40):                    # the first lines scroll off: catch the CPU line as it goes by
                    sh.d.run(max_instructions=100_000)
                    if any(l.rstrip() == "CPU         : 1802" for l in m.video.lines()): break
                else: self.fail("sysinfo never showed CPU : 1802")
                # the card's fsck: Mike Riley's FSCK/5 v0.1 listed false orphans without end on a small card (it held
                # the 3906 lumps as 999,936); the image has it patched, and it says so (0.1p). private-resources:
                # elf/reference/mike-riley/elfos-v5/fsck/
                until(":"); m.kbd.press("fsck\n"); until(":")
                screen = [l.rstrip() for l in m.video.lines()]
                self.assertIn("FSCK/5 0.1p", screen); self.assertIn("Scanning LAT:", screen)
                self.assertFalse(any("Orphaned" in l for l in screen), "\n".join(screen))
            os.remove(img)

    @unittest.skipUnless(os.path.exists(V5_GZ), "the Elf/OS v5 image is in the private-resources repository, not here")
    def test_elfos_v5_cls_is_the_system5_one(self):
        """software/elfos-v5: cls is what its source assembles to, and the v5 card image holds exactly that program"""
        import importlib.util
        v5 = os.path.join(ROOT, "software", "elfos-v5")
        def load(name):                               # by path: other folders have a build.py of their own
            spec = importlib.util.spec_from_file_location("elfos_v5_" + name, os.path.join(v5, name + ".py"))
            mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
        build, v5card = load("build"), load("v5card")
        prog, _ = build.assemble("cls")
        with open(os.path.join(v5, "cls", "cls"), "rb") as f: self.assertEqual(f.read(), prog)
        img = v5card.read_image(V5_GZ)
        self.assertEqual(v5card.contents(img, *v5card.lookup(img, "/bin/cls")[1:3]), prog)
        self.assertNotIn(b"\x1b[", prog)                       # no ANSI codes (ESC [ ...; a lone 1Bh is no code:
        #                                                         build 2 has one, the low byte of its first branch)
        self.assertIn(("/bin/cls", len(prog), [0x26]), v5card.ls(img, "/bin"))
        # put refuses what it cannot do in place: a file that is not there, and one that needs more lumps
        for path, data in (("/bin/nosuch", prog), ("/bin/cls", bytes(5000))):
            with self.assertRaises(SystemExit): v5card.put(bytearray(img), path, data)

    def test_hbios_105_monitor_h_and_b(self):
        """v1.0.5's monitor: H lists the commands, Q1 / Q0 set and reset Q, B boots ELF/OS (lower case too); !, = and ?
        still work; a command it does not know still just gives the prompt again"""
        img = None                                      # B needs an ELF/OS disk: tried only where there is one
        if ELFOS026:
            img = os.path.join(tempfile.mkdtemp(), "elfos.img")
            subprocess.run([sys.executable, os.path.join(HERE, "..", "tools", "mkelfos.py"), img, "--mb", "4"], check=True, capture_output=True)
        m = Machine(cpu_rom=ROM105, disk=img); sh = Shell(m); run = lambda n=1_500_000: sh.d.run(max_instructions=n)
        lines = lambda: [l.rstrip() for l in m.video.lines() if l.strip()]
        run(2_000_000)
        m.kbd.press("H\n"); run()
        self.assertIn(" B               boot the OS from the CF card (@FF00)", lines())
        self.assertIn(" Q1 / Q0         turn Q on / off (SEQ / REQ)", lines())
        self.assertEqual(lines()[-2:], [" H               this list", "test>"])
        for cmd, q in (("Q1", 1), ("Q0", 0), ("q 1", 1), ("?F000", 1), ("q0", 0)):   # Q stays set through other commands
            m.kbd.press(cmd + "\n"); run()
            self.assertEqual(m.cpu.Q, q, cmd)
        m.kbd.press("!0400 41 42 43\n=0400 0410 3\nQ\n\n"); run(4_000_000)
        self.assertEqual([m.peek(0x410 + i) for i in range(3)], [0x41, 0x42, 0x43])
        self.assertEqual(lines()[-3:], ["test>Q", "test>", "test>"])
        m.kbd.press("?0410\n"); run()
        self.assertIn("0410: 41 42 43", "\n".join(lines()))
        if img:
            m.kbd.press("b\n"); run(4_000_000)
            self.assertIn("Elf/OS Ready", lines())
            os.remove(img)

    def test_io_panel_serial_port(self):
        """the IO panel's 16C550 (2026-11-20) in the fast machine: it shares the clock's ports
        6 and 7; a byte with bit 7 set written to port 6 picks the UART's register, one with bit 7 clear the clock's"""
        m = Machine(cpu_rom=ROM104, panel=True); u = m.panel.uart
        def wr(reg, v): m.out(6, 0x80 | reg); m.out(7, v)
        def rd(reg): m.out(6, 0x80 | reg); return m.inp(7)
        wr(3, 0x80); wr(0, 3); wr(1, 0); wr(3, 0x03); self.assertEqual(u.baud(), 38400)
        for c in b"ELF": wr(0, c)
        self.assertEqual(u.sent(), b"ELF"); self.assertEqual(rd(5), 0x60)
        u.receive("os"); self.assertEqual((rd(5), rd(0), rd(0), rd(5)), (0x61, ord("o"), ord("s"), 0x60))
        wr(4, 0x10); wr(0, 0x55); self.assertEqual((rd(0), u.sent()), (0x55, b""))     # loop mode: it comes back in
        wr(4, 0x1F); self.assertEqual(rd(6), 0xF0); wr(4, 0x00); self.assertEqual(rd(6), 0x00)
        wr(7, 0xC3); m.out(6, 0x40); m.out(7, 0x3C)                                    # the UART's scratch byte, the clock's RAM
        self.assertEqual(m.inp(7), 0x3C); self.assertEqual(rd(7), 0xC3)
        wr(1, 0x01); u.receive("x"); self.assertTrue(u.intr()); m.reset(); self.assertFalse(u.intr())   # -RESET: MR
        self.assertEqual(rd(1), 0x00)

    def test_io_panel_reset_button(self):
        """the IO panel card's own RESET button (2026-11-23), in the fast machine: a boot reset. It holds the 1802 in
        reset while it is down and clears the LOADED flag, so the ROM boots when it is let go; nothing while LOAD is on"""
        m = Machine(cpu_rom=ROM104, panel=True); d = Shell(m).d
        m.panel_set(run=False); m.panel_set(load=True)
        for b in (0x7B, 0x30, 0x01): m.panel_set(switches=b); m.panel_set(input=True); m.panel_set(input=False)   # SEQ; BR 01
        m.panel_set(load=False); m.panel_set(run=True); d.run(max_instructions=300)
        self.assertTrue(m.loaded); self.assertEqual(m.cpu.Q, 1)            # the loaded program runs
        m.panel_set(reset=True); self.assertTrue(m.held); self.assertFalse(m.loaded); self.assertEqual(m.cpu.Q, 0)
        m.panel_set(reset=False); self.assertFalse(m.held); self.assertTrue(m.cpurom.remap)    # the boot map: the ROM
        d.run(max_instructions=300); self.assertGreaterEqual(m.cpu.R[m.cpu.P], 0xF000)
        m.panel_set(run=False); m.panel_set(load=True); self.assertTrue(m.loaded)
        m.panel_set(reset=True); self.assertTrue(m.loaded); self.assertEqual(m.cpu.R[0], 0)    # LOAD on: nothing
        m.panel_set(reset=False, load=False, run=True)

    def test_io_panel_toggle_in_and_run(self):
        """the IO panel card in the fast machine (--panel A): a program toggled in through LOAD mode runs and copies the
        toggles to the LEDs; RUN + LOAD pauses; INPUT is EF1 while held; the Reset button boots the ROM again"""
        m = Machine(cpu_rom=ROM104, panel=True); d = Shell(m).d
        self.assertEqual(m.pixie.port, 0)                                 # the 1861 off port 4
        prog = [0xE1, 0xF8, 0x20, 0xA1, 0x6C, 0x64, 0x21, 0x30, 0x04]    # SEX 1; LDI 20; PLO 1; INP 4; OUT 4; DEC 1; BR 04
        m.panel_set(run=False); m.panel_set(load=True)                    # LOAD mode
        for b in prog: m.panel_set(switches=b); m.panel_set(input=True); m.panel_set(input=False)
        self.assertEqual([m.read(a) for a in range(9)], prog)
        m.panel_set(load=False); self.assertEqual(m.cpu.R[0], 0)          # reset
        m.panel_set(switches=0x5A, run=True); d.run(max_instructions=2000)
        self.assertEqual(m.panel.latch, 0x5A)
        m.panel_set(switches=0xC3); d.run(max_instructions=2000); self.assertEqual(m.panel.latch, 0xC3)
        m.panel_set(load=True); n = m.cpu.instructions; d.run(max_instructions=500)
        self.assertEqual(m.cpu.instructions, n); m.panel_set(load=False)  # RUN + LOAD: paused
        self.assertFalse(m.ef(1)); m.panel_set(input=True); self.assertTrue(m.ef(1)); m.panel_set(input=False)
        m.reset(); d.run(max_instructions=2_000_000)
        self.assertEqual(m.video.lines()[-1].rstrip(), "test>")

    def test_hbios_105_panel_demo(self):
        """@F1C0 in v1.0.5: the IO panel demo copies the toggles to the LEDs and sets Q while INPUT is held; Reset ends it"""
        m = Machine(cpu_rom=ROM105, panel=True); sh = Shell(m); run = lambda n=200_000: sh.d.run(max_instructions=n)
        run(2_000_000); m.kbd.press("@F1C0\n"); run(400_000)
        for sw in (0x5A, 0xC3):
            m.panel_set(switches=sw); run(); self.assertEqual(m.panel.latch, sw)
        self.assertEqual(m.cpu.Q, 0)
        m.panel_set(input=True); run(); self.assertEqual(m.cpu.Q, 1)
        m.panel_set(input=False); run(); self.assertEqual(m.cpu.Q, 0)
        m.reset(); run(2_000_000); self.assertEqual(m.video.lines()[-1].rstrip(), "test>")

    def test_hbios_105_disassembler(self):
        """D: every opcode, laid out at 0400 with its operands, comes out as s5emu's disassembler writes it, through
        the -- more -- pauses; Esc at a pause stops; D with no end shows one screenful and no pause.
        (firmware/hbios/v1.0.5/check_disasm.py does the whole ROM too.)"""
        from s5emu.disasm import disasm
        m = Machine(cpu_rom=ROM105); sh = Shell(m); run = lambda n=150_000: sh.d.run(max_instructions=n)
        rows = lambda: [l.rstrip() for l in m.video.lines()]
        run(2_000_000)
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
            if rows()[-1].startswith("-- more --"): got.extend(rows()[-15:-1]); m.kbd.press(" ")
            elif rows()[-1] == "test>" and not m.kbd.ready(): break
        last = rows()[:-1]
        got.extend(last[last.index(got[-1]) + 1:])
        self.assertEqual(got, want)
        m.kbd.press("D F000:F3FF\n")                           # Esc at the first pause
        for _ in range(400):
            run()
            if rows()[-1].startswith("-- more --"): break
        m.kbd.press("\x1b"); run(1_000_000)
        self.assertEqual(rows()[-1], "test>")
        m.kbd.press("D F900\n"); run(3_000_000)                # no end: one screenful, no pause
        self.assertEqual(rows()[-16:-1], ["test>D F900"] + [w for w in self._listing(m, 0xF900, 14)])
        self.assertEqual(rows()[-1], "test>")

    @staticmethod
    def _listing(m, a, count):
        from s5emu.disasm import disasm
        out = []
        for _ in range(count):
            n, t = disasm(m.peek, a)
            out.append("%04X  %-8s  %s" % (a, " ".join("%02X" % m.peek(a + k) for k in range(n)), t.split(";")[0].rstrip()))
            a += n
        return out

    def test_hbios_105_differs_from_104_only_in_the_new_code(self):
        """the 1.0.5 ROM is the burned 1.0.4 except the new code, which only fills bytes 1.0.4 leaves empty (FF) at
        F11C-F1FF and F20C-F7FF, and the four hook bytes in the monitor"""
        with open(ROM104, "rb") as f: a = f.read()
        with open(ROM105, "rb") as f: b = f.read()
        changed = [0xF000 + i for i in range(4096) if a[i] != b[i]]
        new = [x for x in changed if 0xF11C <= x < 0xF200 or 0xF20C <= x < 0xF800]
        self.assertTrue(new)
        self.assertEqual([x for x in new if a[x - 0xF000] != 0xFF], [])          # nothing of 1.0.4 overwritten
        self.assertEqual([x for x in changed if x not in new], [0xF941, 0xF9EB, 0xF9EC, 0xF9ED])
        self.assertEqual(b[0xF9EB - 0xF000:0xF9EE - 0xF000], bytes([0xC0, 0xF2, 0x0C]))   # LBR monext


if __name__ == "__main__":
    unittest.main(verbosity=1)
