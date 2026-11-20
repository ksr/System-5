# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-20
"""VIDEO-G 1.0 from its two netlists (s5emu/hwvideog.py): the card against the behavioural model (s5emu/videog.py),
what its gates do sub-phase by sub-phase, and the whole machine from netlists with it (python3 -m s5emu --hw --video g).

Where the gates show something the design notes do not say, the test records it as found, with a comment: the 6845
enabled in the high-byte time of the other registers' reads, its RS moving under a high E in a read of x801, and the
second, cut-short -WE a window write can get. None of them is hidden, and none is asserted to be right."""
import contextlib, gzip, io, os, sys, tempfile, unittest
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, ".."))
from s5emu.hw import HWMachine
from s5emu.hwvideog import NetlistVideoG
from s5emu.machine import FLOAT, Keyboard
from s5emu.shell import Shell
from s5emu.videog import VideoG

VG_ROM = os.path.join(HERE, "..", "roms", "hbios-video-g.rom")
V5_GZ = os.path.join(HERE, "..", "..", "..", "..", "private-resources", "elf", "reference", "mike-riley", "elfos-v5", "system5",
                     "elfos-5.1.1-system5-16mb.img.gz")


class Bench:
    """what a VideoG needs of a machine, on the bench: a keyboard queue and the CPU's cycle count (the 6845's beam)"""
    def __init__(self):
        self.kbd = Keyboard(None); self.cpu = type("CPU", (), {"cycles": 0})()


def pair(**kw):
    """-> (the behavioural model, a second one read and written only through its netlist card, that card)"""
    jumpers = {k: kw.pop(k) for k in ("block", "kbd_flag") if k in kw}
    ref = VideoG(Bench(), **kw); v = VideoG(Bench(), **kw)
    return ref, v, NetlistVideoG(v, **jumpers)


def read(card, a, vma=0, commit=True):
    """a read cycle as the machine does it: the AND of whatever drives, FF if nothing does -> (byte, drivers, faults)"""
    drv, faults = card.bus_read(a, vma, commit); b = 0xFF
    for _, x in drv: b &= x
    return b, [n for n, _ in drv], faults


class Card(unittest.TestCase):
    def same(self, ref, v):
        self.assertEqual(bytes(ref.vram), bytes(v.vram)); self.assertEqual((ref.reg, ref.sel), (v.reg, v.sel))
        self.assertEqual((ref.ctrl, ref.yreg), (v.ctrl, v.yreg)); self.assertEqual([bytes(p) for p in ref.pages], [bytes(p) for p in v.pages])

    def test_every_address_in_the_block(self):
        """each of 7000-7FFF written and then read, through the gates and in the behavioural model: the same bytes land
        in the same places, the same byte comes back, one part drives and no cycle has a fault. The registers and the
        window are written in an order that moves the Y register and the pages about, so the multiplexer wiring found
        from the netlist is compared with the model's line y at y * 64 across both pages."""
        ref, v, card = pair(); lines = set()
        for a in list(range(0x7000, 0x7800)) + list(range(0x7C00, 0x8000)) + list(range(0x7800, 0x7C00)):
            b = (a * 73 + (a >> 5) * 19 + 7) & 0xFF
            got, faults = card.bus_write(a, 0, b); ref.write(a, b)
            self.assertEqual(faults, [], "%04X" % a); self.assertLessEqual(len(got), 1, "%04X lands in %s" % (a, got))
            if a & 0xC07 == 0x807:                                   # after each set of eight register addresses, fill
                lines.add((v.ctrl & 0x10, v.yreg))                   # the window at the line and page they now name
                for x in range(64):
                    card.bus_write(0x7C00 + x, 0, (x * 5 + v.yreg) & 0xFF); ref.write(0x7C00 + x, (x * 5 + ref.yreg) & 0xFF)
        self.same(ref, v); self.assertGreater(len(lines), 50)        # (lines all over both pages)
        for m in (ref.m, v.m): m.kbd.queue[:] = [(k * 7 + 1) & 0xFF for k in range(600)]
        ref.mouse.extend((k * 11 + 3) & 0xFF for k in range(600)); v.mouse.extend(ref.mouse)
        for a in range(0x7000, 0x8000):
            b, drv, faults = read(card, a)
            self.assertEqual(faults, [], "%04X" % a); self.assertEqual(len(drv), 1, "%04X: %s" % (a, drv))
            self.assertEqual(b, ref.read(a), "%04X" % a)
        self.assertEqual(ref.m.kbd.queue, v.m.kbd.queue); self.assertEqual(list(ref.mouse), list(v.mouse))
        self.assertIsNone(card.slot_fault)                           # (the window's slot ran through the gates on the way)

    def test_who_answers_where(self):
        """the map as DESIGN.md section 3 has it, by the part that drives or takes the byte; the register pairs repeat
        through 7BFF and the window through 7FFF"""
        ref, v, card = pair(); v.m.kbd.queue[:] = [0x41] * 40; v.mouse.extend([1] * 40)
        want_r = {0: "video-g IC4", 1: "video-g IC9", 2: "video-g IC8", 3: "video-g GFX IC12"}
        want_w = {0: ["video-g IC4"], 1: [], 2: ["video-g GFX IC19"], 3: ["video-g GFX IC10"]}
        for a in (0x7000, 0x7001, 0x73FF, 0x77FF):
            self.assertEqual(read(card, a)[1], ["video-g IC3"]); self.assertEqual(card.bus_write(a, 0, 0x20)[0], ["video-g IC3"])
        for a in list(range(0x7800, 0x7810)) + [0x7900, 0x79F4, 0x7A02, 0x7BFE, 0x7BFF]:
            self.assertEqual(read(card, a)[1], [want_r[(a >> 1) & 3]], "%04X" % a)
            self.assertEqual(card.bus_write(a, 0, 0)[0], want_w[(a >> 1) & 3], "%04X" % a)
        for a in (0x7C00, 0x7C3F, 0x7C40, 0x7D15, 0x7FFF):
            self.assertEqual(read(card, a)[1], ["video-g GFX IC6"]); self.assertEqual(card.bus_write(a, 0, 0)[0], ["video-g GFX IC1"])
        v.yreg = 9; card.bus_write(0x7C05, 0, 0xA5)                  # the window repeats every 64 bytes
        self.assertEqual([read(card, a)[0] for a in (0x7C05, 0x7C45, 0x7FC5)], [0xA5] * 3)
        self.assertEqual(v.pages[0][9 * 64 + 5], 0xA5)

    def test_nothing_outside_the_block(self):
        """every page outside 7000-7FFF is idle whatever its low byte, read or written (one cycle through the gates
        with the low byte unknown proves a page); and the block itself is idle while the CPU card holds -VMA high"""
        ref, v, card = pair()
        for hi in range(256):
            for write in (False, True):
                r = card.page(hi, 0, write)
                self.assertEqual(r == "idle", hi >> 4 != 7, "%02X" % hi)
                self.assertEqual(card.page(hi, 1, write), "idle")
        before = (bytes(v.vram), list(v.reg), v.ctrl, v.yreg)
        for a in (0x0000, 0x6FFF, 0x8000, 0x8804, 0xF800, 0xFFFF):
            self.assertEqual(card.bus_read(a, 0), ([], [])); self.assertEqual(card.bus_write(a, 0, 0x55), ([], []))
        for a in (0x7000, 0x7801, 0x7804, 0x7C00):                   # -VMA high: the boot map, the CPU EPROM's cycle
            self.assertEqual(card.bus_read(a, 1), ([], [])); self.assertEqual(card.bus_write(a, 1, 0x55), ([], []))
        self.assertEqual(before, (bytes(v.vram), list(v.reg), v.ctrl, v.yreg))

    def test_block_jumper(self):
        """SV1: a shunt is a 0 bit; the card answers in the block it names and nowhere else"""
        for block in range(16):
            ref, v, card = pair(block=block)
            answers = {hi >> 4 for b in range(16) for hi in (b << 4, (b << 4) | 0x8, (b << 4) | 0xF) if card.page(hi, 0, False) != "idle"}
            self.assertEqual(answers, {block})
            base = block << 12
            self.assertEqual(read(card, base + 0x123)[1], ["video-g IC3"]); self.assertEqual(read(card, base + 0x804)[1], ["video-g IC8"])
            self.assertEqual(card.bus_write(base + 0xC00, 0, 1)[0], ["video-g GFX IC1"])

    def test_text_alone(self):
        """TEXT without GFX (the ribbon unplugged): the text RAM, the 6845, the key and the status work; GFX-PRESENT
        and MOUSE-READY read 0 (TEXT's pull-downs); the window and the mouse float; writes to 7804, 7806 and the window
        land nowhere"""
        ref, v, card = pair(gfx=False)
        self.assertFalse(card.gfx)
        self.assertEqual(card.bus_write(0x7005, 0, 0x41), (["video-g IC3"], [])); self.assertEqual(read(card, 0x7005)[:2], (0x41, ["video-g IC3"]))
        self.assertEqual(read(card, 0x7804)[0] & 0x22, 0)
        self.assertEqual(read(card, 0x7804)[0], ref.status())
        for a in (0x7806, 0x7C00, 0x7FFF):
            self.assertEqual(read(card, a), (FLOAT, [], []), "%04X" % a)
        for a in (0x7804, 0x7806, 0x7C00):
            self.assertEqual(card.bus_write(a, 0, 0x3F), ([], [])); self.assertEqual((v.ctrl, v.yreg), (0, 0))
        v.m.kbd.press("k"); self.assertEqual(read(card, 0x7802)[:2], (ord("k"), ["video-g IC9"]))

    def test_status(self):
        """7804: 0 KEY-READY, 1 MOUSE-READY, 2 VSYNC, 3 DE, 4 MONITOR, 5 GFX-PRESENT, 7..6 = 10: each bit from the net on
        the 74LS244's input, the 6845's two from the behavioural beam"""
        ref, v, card = pair()
        self.assertEqual(read(card, 0x7804)[0] & 0xF3, 0xA0)         # the ID, GFX fitted, NTSC, nothing waiting
        v.m.kbd.press("x"); self.assertEqual(read(card, 0x7804)[0] & 0x03, 0x01)
        v.mouse.append(5); self.assertEqual(read(card, 0x7804)[0] & 0x03, 0x03)
        read(card, 0x7802); self.assertEqual(read(card, 0x7804)[0] & 0x03, 0x02)
        read(card, 0x7806); self.assertEqual(read(card, 0x7804)[0] & 0x03, 0x00)
        seen = set()
        for cyc in range(0, 40000, 7):                               # the beam through a frame: both bits move, as the model's
            v.m.cpu.cycles = ref.m.cpu.cycles = cyc
            b = read(card, 0x7804)[0]; self.assertEqual(b, ref.status()); seen.add(b & 0x0C)
        self.assertEqual(seen, {0x00, 0x04, 0x08})
        ref, v, card = pair(monitor="mda")
        self.assertEqual(read(card, 0x7804)[0] & 0xF3, 0xB0)         # JP1 2-3: MONITOR high

    def test_key_ready(self):
        """a key: the ATmega loads the latch and sets KEY-READY; the bus flag line goes low; a read of 7802 (or 7803)
        gives the key and clears KEY-READY at TPB; the next key follows. A look (no commit) clears nothing, and nor does
        the key latch's enable in the high-byte time of a read at 7Axx"""
        ref, v, card = pair()
        self.assertFalse(card.ef("-EF")); self.assertEqual(read(card, 0x7804)[0] & 1, 0)
        v.m.kbd.press("AB")
        self.assertTrue(card.ef("-EF")); self.assertFalse(card.ef("-EF1")); self.assertTrue(card.kready)
        self.assertEqual(read(card, 0x7802, commit=False)[0], 0x41); self.assertEqual(v.m.kbd.queue, [0x41, 0x42])
        self.assertEqual(card.early(0x7A00), [("mrd", "IC9"), ("hold", "IC9")])
        read(card, 0x7A00); self.assertEqual(v.m.kbd.queue, [0x41, 0x42])     # (the 6845 answers 7A00; the key stays)
        self.assertEqual(read(card, 0x7802)[0], 0x41); self.assertEqual(v.m.kbd.queue, [0x42]); self.assertTrue(card.ef("-EF"))
        self.assertEqual(read(card, 0x7803)[0], 0x42); self.assertEqual(v.m.kbd.queue, []); self.assertFalse(card.ef("-EF"))
        self.assertEqual(read(card, 0x7802)[0], 0x42)                # no key waiting: the latch still holds the last one
        clears = [(ph, cl) for ph, rd, wr, cl, ck in card.trace(0x7802) if cl]
        self.assertEqual(clears, [("tpb", ["KEY-READY"])])           # the clear is TPB's, as DESIGN.md says

    def test_kbd_flag_jumper(self):
        """JP3 KBD FLAG: one shunt puts KEY-READY on -EF1, -EF2, -EF3 or -EF; none leaves all four alone"""
        for line in ("-EF1", "-EF2", "-EF3", "-EF", None):
            ref, v, card = pair(kbd_flag=line); v.m.kbd.press("k")
            self.assertEqual([n for n in ("-EF1", "-EF2", "-EF3", "-EF") if card.ef(n)], [line] if line else [])
            self.assertTrue(card.kready)

    def test_mouse(self):
        """the mouse latch at 7806 and MOUSE-READY, as the key; turning MOUSE-ON off leaves one byte in the latch"""
        ref, v, card = pair()
        card.bus_write(0x7804, 0, 0x20); self.assertTrue(v.mouse_packet(3, -2, 1))
        self.assertEqual(read(card, 0x7804)[0] & 2, 2)
        self.assertEqual([read(card, 0x7806)[0] for _ in range(3)], [0x29, 0x03, 0xFE]); self.assertEqual(read(card, 0x7804)[0] & 2, 0)
        v.mouse_packet(1, 1); card.bus_write(0x7804, 0, 0x00)
        self.assertEqual(len(v.mouse), 1); self.assertEqual(read(card, 0x7804)[0] & 2, 2)
        clears = [(ph, cl) for ph, rd, wr, cl, ck in card.trace(0x7806) if cl]
        self.assertEqual(clears, [("tpb", ["MOUSE-READY"])])

    def test_reset(self):
        """-RESET through the gates: the control register's -MR, KCLR and MCLR all follow it"""
        ref, v, card = pair()
        card.bus_write(0x7804, 0, 0x3F); card.bus_write(0x7806, 0, 0x77); v.m.kbd.press("k"); v.mouse.append(1)
        self.assertTrue(card.ef("-EF")); self.assertTrue(card.mready)
        v.m.kbd.queue.clear(); v.mouse.clear()                       # (nothing for the ATmegas to load again)
        card.bus_reset()
        self.assertEqual(v.ctrl, 0); self.assertEqual(v.yreg, 0x77)  # the Y register has no reset
        self.assertFalse(card.kready); self.assertFalse(card.mready); self.assertFalse(card.ef("-EF"))
        card.reset_line(0); v.m.kbd.press("k")                       # held low (the IO panel's RUN off): nothing is set,
        self.assertEqual(card.held, {"KEY-READY", "MOUSE-READY", "control"})
        card.bus_write(0x7804, 0, 0x3F); card.bus_write(0x7806, 0, 0x11)     # and the control register stays clear
        self.assertEqual((v.ctrl, v.yreg), (0, 0x11)); self.assertFalse(card.ef("-EF")); self.assertEqual(read(card, 0x7804)[0] & 1, 0)
        card.reset_line(1); self.assertTrue(card.ef("-EF")); self.assertEqual(card.held, set())    # let go: the key is loaded

    def test_strobes_sub_phase_by_sub_phase(self):
        """the cycle as the gates time it: read enables from -MRD's fall to the end of the cycle; the 6845's E only at
        TPB in a write (TPB within -MRW); a register's clock low at TPB and rising when -MRW rises; the text RAM written
        while -MRW is low"""
        ref, v, card = pair()
        on = lambda a, w=False: {ph: (rd, wr) for ph, rd, wr, cl, ck in card.trace(a, 0, w)}
        t = on(0x7000); self.assertEqual([ph for ph in t if t[ph][0] == ["IC3"]], ["mrd", "hold", "low", "tpb", "end"])
        t = on(0x7801); self.assertEqual([ph for ph in t if t[ph][0] == ["IC4"]], ["mrd", "hold", "low", "tpb", "end"])
        t = on(0x7801, True); self.assertEqual([ph for ph in t if t[ph][1] == ["IC4"]], ["tpb"])
        self.assertTrue(all(not t[ph][0] for ph in t))               # nothing drives in a write cycle
        t = on(0x7000, True); self.assertEqual([ph for ph in t if t[ph][1] == ["IC3"]], ["mrw", "tpb"])
        for a, reg in ((0x7804, "control"), (0x7806, "Y")):
            clk = [ck[reg] for ph, rd, wr, cl, ck in card.trace(a, 0, True)]
            self.assertEqual(clk, [1, 1, 1, 1, 1, 0, 1, 1])          # idle tpa hold low mrw TPB mrwend end
            self.assertEqual(card.plan(a, 0, True).regs, [reg])
        self.assertIsNone(card.plan(0x7802, 0, True))                # 7802 takes no write: the cycle does nothing here

    def test_as_found_the_6845_in_the_high_byte_time(self):
        """AS FOUND, not in DESIGN.md. The 1802 takes -MRD low at 1.5 T, while A0-A7 still carry the HIGH address byte
        (the low byte comes at 2.5 T). The register decoders IC5 and IC6 take A1 and A2 from those lines, so for that
        clock a read at 78xx or 79xx looks like a read of 7800/7801 (A9 = A10 = 0 there): -RDCRTC is low, E is high and
        the 6845 is on the bus, whatever register the low byte then names; at 7Axx / 7Bxx (A9 = 1) it is the key latch.
        Nobody else drives then and the 1802 does not look, and KEY-READY is not cleared (that waits for TPB). The
        hand-over to the status buffer or the key latch at 2.5 T is a matter of nanoseconds this model does not see."""
        ref, v, card = pair()
        for a in (0x7802, 0x7804, 0x7806, 0x79F4):
            self.assertEqual(card.early(a), [("mrd", "IC4"), ("hold", "IC4")], "%04X" % a)
        for a in (0x7A00, 0x7A04, 0x7B06):
            self.assertEqual(card.early(a), [("mrd", "IC9"), ("hold", "IC9")], "%04X" % a)
        for a in (0x7000, 0x77FF, 0x7800, 0x7801, 0x7A02, 0x7C00, 0x7FFF):
            self.assertEqual(card.early(a), [], "%04X" % a)          # the part the low byte names is the one already on

    def test_as_found_rs_moves_under_e_in_a_read_of_7801(self):
        """AS FOUND, not in DESIGN.md. In a read the 6845's E is the whole -MRD time, so it rises at 1.5 T with A8 on RS
        (A0's line still carries the high byte); A0 itself arrives at 2.5 T. A read of 7801 therefore moves RS from 0
        to 1 with E already high: the 6845's address set-up to E (tAS) is not met. Writes are not touched (their E is
        TPB's), and no System-5 program reads 7801 today (the VIDEO-G HBIOS and GBASIC only write it). The text RAM's
        address pins move the same way under its enables, which an asynchronous RAM does not mind."""
        ref, v, card = pair()
        self.assertEqual(card.shifts(0x7801), [("low", "IC4")])
        self.assertEqual(card.shifts(0x7800), []); self.assertEqual(card.shifts(0x7901), []); self.assertEqual(card.shifts(0x7900), [("low", "IC4")])
        self.assertEqual(card.shifts(0x7123), [("low", "IC3")])
        v.sel = 14; v.reg[14] = 0x12
        self.assertEqual(read(card, 0x7801)[0], 0x12)                # (played as if the 6845 follows the late RS)

    def test_multiplexer_wiring(self):
        """the graphics RAM's address as the four 74HCT157s make it, found from the netlist input by input:
        DESIGN.md section 5's table, both sides"""
        ref, v, card = pair()
        cpu = [("A", i) for i in range(6)] + [("Y", i) for i in (3, 4, 5, 6, 7, 0, 1, 2)] + [("C", 4)]
        disp = [("MA", i) for i in range(11)] + [("RA", i) for i in range(3)] + [("C", 3)]
        self.assertEqual(card.cpu_map, cpu); self.assertEqual(card.disp_map, disp)
        self.assertEqual(card.cell(0x2A, 0x10, 0xA5), (0x6D2A, 1, 0xA5 * 64 + 0x2A))
        self.assertEqual((card.wr_bit, card.rd_bit), (list(range(8)), list(range(8))))

    def test_the_slot_through_the_gates(self):
        """a window access with the character counter stepped (WRQ, -WE at counts 9 and 10, the write buffer, the RAM's
        -OE, the read latch on QC): from every counter phase a write lands in the cell the wiring names and a read
        brings it back; with -MRW low for 11 dot clocks (917 ns) or more every phase gets a whole -WE, with 10 it does
        not (DESIGN.md section 5: the limit is about a 2.1 MHz 1802)"""
        ref, v, card = pair()
        self.assertIsNone(card.slot_check(12)); self.assertIsNone(card.slot_check(11))
        self.assertIn("no whole -WE", card.slot_check(10)); card.slot_check()
        for lo, y, ctrl, byte in ((0x00, 0, 0, 0x81), (0x3F, 199, 0x10, 0x7E), (0x15, 0x5A, 0x08, 0x33)):
            ga = card.cell(lo, ctrl, y)[0]
            for start in (8, 11, 12, 15):
                cells = {}; r = card.slot(lo, byte, start=start, counts=12, cells=cells, ctrl=ctrl, y=y)
                self.assertEqual(r["faults"], []); self.assertEqual(cells, {ga: byte})
                r = card.slot(lo, None, start=start, cells=cells, ctrl=ctrl, y=y)
                self.assertEqual((r["latch"], r["drives"], r["writes"], r["faults"]), (byte, True, [], []))

    def test_as_found_a_second_cut_short_we(self):
        """AS FOUND. A write that starts just before a character boundary gets its whole -WE in the first slot and
        still has -MRW low when the next slot's count 9 comes: -WE falls again and -MRW's rise cuts it short (GWR is in
        the -WE gate). The same byte goes to the same cell with the address and data still held, so nothing is lost;
        it is a second, shorter write pulse the notes do not mention."""
        ref, v, card = pair()
        r = card.slot(0x10, 0x55, start=14, counts=12)
        self.assertEqual([(n, k) for n, k, adr, d in r["writes"]], [(3, 9), (4, 10), (11, 9)])     # whole, then one count
        self.assertEqual({(adr, d) for n, k, adr, d in r["writes"]}, {(card.cell(0x10, 0, 0)[0], 0x55)})
        self.assertEqual(r["faults"], [])


class System(unittest.TestCase):
    """the whole machine from netlists: CPU Rev D, memory Rev D (MEM3-E's circuit), IDE Rev A, the IO panel and VIDEO-G"""
    def machine(self, booted=False, **kw):
        """booted: past CPU Rev D's boot map (as after HBIOS's first jump to F0xx), so -VMA is low below F000"""
        m = HWMachine(cpu_rom=VG_ROM, mem_rev="D", cpu_rev="D", ide_rev="A", panel_rev="A", videog="1.0", mhz=2.0, **kw)
        if booted: m.ccard.set_booted(True)
        return m

    def until(self, m, sh, prompt, cap):
        for _ in range(0, cap, 250_000):
            sh.d.run(max_instructions=250_000)
            if not m.kbd.queue and m.video.lines()[-1].rstrip() == prompt: return
        self.fail("no %r prompt; the screen:\n%s" % (prompt, "\n".join(m.video.lines())))

    def test_hbios_and_the_monitor(self):
        """HBIOS's VIDEO-G build reaches test> on the bottom row; a monitor command typed on VIDEO-G's keyboard reaches
        RAM; the bus log stays empty"""
        m = self.machine(); sh = Shell(m)
        self.until(m, sh, "test>", 4_000_000)
        self.assertEqual(m.video.reg[6], 25)
        m.kbd.press("!6000 12 34 56\n"); self.until(m, sh, "test>", 2_000_000)
        self.assertEqual([m.peek(0x6000 + k) for k in range(3)], [0x12, 0x34, 0x56])
        self.assertEqual(m.log.events, {})
        d = m.describe(); self.assertIn("VIDEO-G 1.0", d); self.assertIn("GFX on the ribbon", d); self.assertNotIn("6845 card", d)
        bm = m.bus_map()
        for line in ("7000  -VMA=0  video-g IC3", "7800  -VMA=0  video-g IC4", "7804  -VMA=0  video-g IC8", "7C00  -VMA=0  video-g GFX IC6",
                     "6000  -VMA=0  mem IC1", "F000  -VMA=1  CPU EPROM"):
            self.assertIn(line, bm)
        self.assertNotIn("6845", bm)

    def test_key_ready_reaches_the_1802(self):
        """KEY-READY on the bus -EF (JP3 as set), which CPU Rev D's jumpers here put on EF3; with JP3 on -EF2, on EF2"""
        m = self.machine(booted=True)
        self.assertFalse(m.ef(3)); m.kbd.press("k"); self.assertTrue(m.ef(3)); self.assertFalse(m.ef(2))
        self.assertEqual(m.read(0x7802), ord("k")); self.assertFalse(m.ef(3))
        m = self.machine(kbd_flag="-EF2"); m.kbd.press("k"); self.assertTrue(m.ef(2)); self.assertFalse(m.ef(3))

    def test_the_boot_map_keeps_the_card_off(self):
        """until CPU Rev D's boot map ends, -VMA is high at every address: the card answers nothing, and the EPROM
        alone is on the bus at 7xxx (no double drive in HBIOS's first instructions)"""
        m = self.machine(); m.kbd.press("k")
        self.assertEqual(m.bus_map().count("video-g"), 0)
        m.write(0x7804, 0x16); self.assertEqual(m.video.ctrl, 0)
        m.read(0x7802); self.assertEqual(m.kbd.queue, [ord("k")]); self.assertEqual(m.log.events, {})

    def test_resets(self):
        """the CPU card's reset and the IO panel's RUN off both put -RESET on the bus: the control register clears"""
        m = self.machine(booted=True)
        m.write(0x7804, 0x16); self.assertEqual(m.video.ctrl, 0x16); m.reset(); self.assertEqual(m.video.ctrl, 0)
        m.ccard.set_booted(True)
        m.write(0x7804, 0x16); m.panel_set(run=False); self.assertEqual(m.video.ctrl, 0); self.assertTrue(m.vg.reset_low)
        m.panel_set(load=True); self.assertTrue(m.vg.reset_low)       # LOAD mode: -RESET still low
        m.panel_set(load=False); m.panel_set(run=True); self.assertFalse(m.vg.reset_low)

    def test_graphics_from_a_program(self):
        """a few 1802 instructions in RAM (no EPROM fitted) set a pixel as DESIGN.md section 3 says: y to 7806, the
        mask into 7C00 + x / 8; and the panel's LEDs, on port 4 beside VIDEO-G, show a byte"""
        m = HWMachine(cpu_rom=None, mem_rev="D", cpu_rev="D", ide_rev="A", panel_rev="A", videog="1.0", mhz=2.0)
        prog = [0xF8, 0x78, 0xB2, 0xF8, 0x04, 0xA2, 0xF8, 0x02, 0x52,       # 7804 = 02: graphics on
                0xF8, 0x06, 0xA2, 0xF8, 100, 0x52,                         # 7806 = 100: line 100
                0xF8, 0x7C, 0xB2, 0xF8, 0x20, 0xA2, 0xF8, 0x80, 0x52,       # 7C20 = 80: x = 256
                0xE0, 0x64, 0xA5, 0x00]                                    # OUT 4 = A5; idle
        for a, b in enumerate(prog): m.write(a, b)
        for _ in range(60): m.step()
        self.assertEqual((m.video.ctrl, m.video.yreg), (0x02, 100))
        self.assertEqual(m.video.pixel(256, 100), 1); self.assertEqual(m.video.pages[0][100 * 64 + 0x20], 0x80)
        self.assertEqual(m.panel.latch, 0xA5); self.assertEqual(m.log.events, {})

    def test_the_behavioural_model_on_the_modelled_bus(self):
        """videog='none': VIDEO-G's behavioural model beside the netlist cards; HBIOS still reaches test>"""
        m = HWMachine(cpu_rom=VG_ROM, mem_rev="D", cpu_rev="D", ide_rev="A", panel_rev="A", videog="none"); sh = Shell(m)
        self.assertIsNone(m.vg); self.until(m, sh, "test>", 4_000_000)
        self.assertEqual(m.log.events, {}); self.assertIn("VIDEO-G: behavioural", m.describe())
        self.assertIn("7000  -VMA=0  video-g", m.bus_map())

    def test_command_line(self):
        """python3 -m s5emu --hw --video g, with the IO panel on port 4 beside it; and the instruction-level machine
        takes --panel with --video g too (it was refused while VIDEO-G still had ports)"""
        from s5emu.__main__ import main
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()) as out:
            main(["--hw", "--video", "g", "--cpu-rev", "D", "--panel", "A", "--ui", "none", "-c", "bus"])
        self.assertIn("VIDEO-G 1.0", err.getvalue()); self.assertIn("IO panel A", err.getvalue()); self.assertIn("no bus events", out.getvalue())
        with contextlib.redirect_stderr(io.StringIO()) as err, contextlib.redirect_stdout(io.StringIO()):
            main(["--hw", "--video", "g", "--no-gfx", "--videog-rev", "none", "--monitor", "mda", "--ui", "none"])
            main(["--hw", "--video", "g", "--no-gfx", "--kbd-flag", "ef2", "--ui", "none"])
        self.assertIn("TEXT alone", err.getvalue()); self.assertIn("KEY-READY on -EF2", err.getvalue())
        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()) as out:
            main(["--video", "g", "--panel", "A", "--ui", "none", "-c", "panel"])
        self.assertIn("LEDs", out.getvalue())

    @unittest.skipUnless(os.path.exists(V5_GZ), "the Elf/OS v5 image is in the private-resources repository, not here")
    def test_elfos_v5(self):
        """Elf/OS 5.1.1 boots from the card image on the all-netlist machine with VIDEO-G (about a minute) and runs
        ver; no fight, no double drive, no undefined cycle on the way"""
        img = tempfile.mktemp(suffix=".img")
        with gzip.open(V5_GZ) as f, open(img, "wb") as g: g.write(f.read())
        try:
            m = self.machine(disk=img); sh = Shell(m)
            self.until(m, sh, "test>", 4_000_000)
            m.kbd.press("@FF00\n"); self.until(m, sh, ":", 60_000_000)
            self.assertIn("Ready", [l.rstrip() for l in m.video.lines()])
            m.kbd.press("ver\n"); self.until(m, sh, ":", 20_000_000)
            self.assertTrue(any("5.1.1 Build 229" in l for l in m.video.lines()))
            self.assertEqual(m.log.events, {})
        finally:
            os.remove(img)


if __name__ == "__main__":
    unittest.main(verbosity=1)
