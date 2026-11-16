#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-11
"""Bring up System-5 cards one at a time from the bus driver card, with the CPU card out of the backplane.

Plans (the procedure, jumpers and what each step proves are in BRINGUP.md beside this file):
  memory   memory Rev D: block map against the jumpers, data lines, address lines, RAM test, EPROM read, LEDs
  cf       IDE/CF Rev A with its CF adapter and a CF card: status, register path, register select, the BIOS's
           set-up (8-bit mode), IDENTIFY, sector 0, optional write test
  video    6845 Rev B: decode, video RAM data / address / full test, CRTC register path, then HBIOS's 16 x 64
           set-up and a test screen to check on the monitor
  all      the three cards together: the combined address map, no card answering in another's space, the CRTC
           and the RAM not double-mapped, the CF card undisturbed by memory traffic

Run against the real card (the Nano's USB port is found automatically):
  python3 bringup.py memory
  python3 bringup.py memory --full --rom ../../../private-resources/elf/firmware/elfos-install-rom/<image>.bin
  python3 bringup.py cf
  python3 bringup.py video --interactive
Run against the simulated backplane (the netlist models; nothing to plug in):
  python3 bringup.py --sim memory
  python3 bringup.py --sim memory --fault stuck:mem:3:0       (see what a stuck data line looks like)

Each step prints PASS, FAIL, WARN (works, but look at it), INFO or LOOK (check by eye on the card or the monitor).
The exit status is 1 if any step failed.
"""
import argparse, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import s5busdrv as S                                                         # noqa: E402

DEFAULT_JUMPERS = "RRRRRRR-EEEEEEE-"
# memory Rev C/D (from the netlists): each chip's select mux, and on Rev D its LED (LED1 = +5 V)
MEM_MUX = {"IC1": "IC2", "IC11": "IC4", "IC3": "IC15", "IC5": "IC13"}
MEM_LED = {"D": {"IC1": "LED2", "IC11": "LED3", "IC3": "LED4", "IC5": "LED5"}}
MEM_PART = {"RAM": "62256 RAM", "ROM": "27256 EPROM"}
# HBIOS v1.0.4 vtable (firmware/hbios/v1.0.4/sec1.asm): BYTE May 1979 Table 2, 16 rows x 64 characters
HBIOS_CRTC = [94, 64, 77, 8, 28, 2, 16, 22, 0, 8, 64, 8, 0, 0, 0x03, 0xC0]
IDE_STATUS_BITS = [(0x80, "BSY"), (0x40, "DRDY"), (0x20, "DF"), (0x10, "DSC"), (0x08, "DRQ"), (0x04, "CORR"), (0x02, "IDX"), (0x01, "ERR")]


def read_file(path):
    with open(path, "rb") as fh: return fh.read()


def bits_text(mask, prefix="D"):
    return " ".join("%s%d" % (prefix, i) for i in range(8) if mask >> i & 1)


def status_text(s):
    return "%02X (%s)" % (s, " ".join(n for b, n in IDE_STATUS_BITS if s & b) or "none")


class Step:
    def __init__(self, code, title):
        self.code, self.title, self.status, self.lines, self.hints = code, title, "PASS", [], []

    def fail(self, text, hint=None):
        self.status = "FAIL"; self.lines.append(text)
        if hint and hint not in self.hints: self.hints.append(hint)

    def warn(self, text, hint=None):
        if self.status == "PASS": self.status = "WARN"
        self.lines.append(text)
        if hint and hint not in self.hints: self.hints.append(hint)

    def info(self, text): self.lines.append(text)

    def skip(self, text): self.status = "SKIP"; self.lines.append(text)


class Bringup:
    def __init__(self, bd, a, out=print):
        self.bd, self.a, self.out, self.steps = bd, a, out, []
        self.found = {}                                        # block -> 'RAM' | 'ROM' | 'nothing' (from the block map)
        self.badbits = {}                                      # block -> data bits that did not follow a write
        self._mem = None                                       # the memory card's netlist model: what each block should hold
        self.line_fault = False                                # a data or address line failed: bad bytes are not the chip's
        self.bad_data = 0                                      # data bits M2 / V2 found stuck

    # ------------------------------------------------------------------ reporting
    def step(self, code, title, fn, *args):
        st = Step(code, title); t = time.time()
        try:
            fn(st, *args)
        except S.CardError as e:
            st.fail("the bus driver refused a command: %s" % e)
        except (TimeoutError, OSError) as e:
            st.fail("no answer from the bus driver: %s" % e, "Check the USB cable and that the bus has power (STATUS).")
        self.steps.append(st)
        self.out("[%-4s] %s %s  (%.1f s)" % (st.status, code, title, time.time() - t))
        for l in st.lines: self.out("         " + l)
        for h in st.hints: self.out("         -> " + h)
        return st

    def summary(self):
        n = {k: sum(1 for s in self.steps if s.status == k) for k in ("PASS", "WARN", "FAIL", "LOOK", "INFO", "SKIP")}
        self.out("")
        self.out("Summary: %d steps, %d pass, %d warn, %d fail, %d skipped, %d to check by eye" % (
            len(self.steps), n["PASS"], n["WARN"], n["FAIL"], n["SKIP"], n["LOOK"]))
        for s in self.steps:
            if s.status in ("FAIL", "WARN", "LOOK", "SKIP"): self.out("  %-4s %s %s" % (s.status, s.code, s.title))
        return n["FAIL"] == 0

    def report(self, path, plan):
        with open(path, "w") as fh:
            fh.write("# Bring-up report: %s\n\n%s\n\n" % (plan, time.strftime("%Y-%m-%d %H:%M")))
            for s in self.steps:
                fh.write("## %s %s: %s\n\n" % (s.code, s.title, s.status))
                for l in s.lines: fh.write("    %s\n" % l)
                for h in s.hints: fh.write("\n- %s\n" % h)
                fh.write("\n")

    def look(self, st, question, details):
        """a check by eye: ask when interactive, else list it for later"""
        for d in details: st.info(d)
        if self.a.interactive:
            ans = input("    %s [y/n] " % question).strip().lower()
            if ans.startswith("y"): st.info("seen: yes")
            else: st.fail("seen: no")
        else:
            st.status = "LOOK"; st.info("check by eye: " + question + " (run with --interactive to answer here)")

    # ------------------------------------------------------------------ bus helpers
    def rd(self, a): return self.bd.read(a, 1)[0]
    def wr(self, a, v): self.bd.write(a, bytes([v & 0xFF]))

    def charge(self, v):
        """drive the data bus to v and let go: on a backplane without pull-ups (the 2009 bus) an undriven data line keeps
        the last value put on it, so a read straight after a write would see the write even where nothing answers"""
        self.bd.cmd("WR-DATABUS", v & 0xFF); self.bd.cmd("DATABUS-RD-MODE", 0)

    def rd_after(self, a, v):
        """read a with the data bus first charged to v: what comes back was driven by the card, not left on the bus"""
        self.charge(v); return self.rd(a)

    def probe(self, a):
        """what answers at a: 'RAM' (writes stick), 'ROM' (reads something, ignores writes), 'nothing' (FF, or the
        floating bus follows whatever was last on it) or 'unstable'. Every read is made with the bus charged to the
        opposite of what is expected first (charge()), so a floating bus cannot pass for RAM (found 2026-10-30 on the
        2009 backplane). A RAM with a bad data line is still 'RAM': self.badbits[a >> 12] = the bits that did not follow."""
        r0 = self.rd_after(a, 0x00); r1 = self.rd_after(a, 0xFF)
        if r0 != r1 and (r0, r1) == (0x00, 0xFF):           # the read just follows the bus: nothing drives it
            return "nothing"
        self.wr(a, 0x55); g1 = self.rd_after(a, 0xAA); self.wr(a, 0xAA); g2 = self.rd_after(a, 0x55); self.wr(a, r1)
        bad = (g1 ^ 0x55) | (g2 ^ 0xAA)
        if bin(g1 ^ g2).count("1") >= 5:                   # most bits follow the writes: RAM, perhaps with a bad line
            if bad: self.badbits[a >> 12] = bad
            return "RAM"
        if r0 == r1 == g1 == g2:
            sample = self.bd.read(a & 0xFFF0, 16)
            return "nothing" if r1 == 0xFF and all(b == 0xFF for b in sample) else "ROM"
        return "unstable"

    # ------------------------------------------------------------------ common steps
    def s_connect(self, st):
        st.info("bus driver: %s" % " / ".join(self.bd.banner))
        if not self.bd.ioblocks:
            st.warn("this firmware is older than 2026-10-11 (no 'io-2' in the banner)",
                    "Update the bus driver firmware: the old one runs no TPB in memory cycles (the 6845 never answers) "
                    "and no -MRD/TPA in OUT/INP (the CF card reads when it should write). Flash embedded/bus-driver/s5-bus-driver.")
        s = self.bd.status(); st.info(s)
        if "bus=on" not in s:
            st.fail("the bus has no power", "Power the backplane; the bus driver runs its expanders from bus +5V.")
            return
        try:
            self.bd.master(True)
        except S.CardError as e:
            st.fail(str(e), "Pull the CPU card: the bus driver refuses the bus while TPA/TPB are toggling.")
            return
        st.info("bus driver is bus master")

    def s_idle(self, st):
        snap = self.bd.snap(); st.info(snap)
        f = dict(kv.split("=") for kv in snap.split())
        for line in ("-RESET", "-INT", "-EF"):
            if f.get(line) == "0":
                st.warn("%s reads low with nothing asking for it" % line,
                        "On a backplane without pull-ups (the 2009 bus) a released open-collector line floats and reads low "
                        "here: that is expected. On a bus with pull-ups (Rev D) it means a card holds %s low or the line is "
                        "shorted to GND: pull cards one at a time to find which." % line)
        if f.get("-RESET") == "0":
            st.info("(a low -RESET also holds the 6845 in reset: the CRTC steps would fail)")

    # ------------------------------------------------------------------ memory card
    def mem_model(self):
        """{block: (kind, chip ref, jumper pins)} for this card revision and these jumpers, from its netlist: the
        emulator's gate-level decode is asked which chip each block enables"""
        if self._mem is None:
            sys.path.insert(0, os.path.join(HERE, "..", "s5emu"))
            from s5emu.hw import NetlistMemoryCard
            m = NetlistMemoryCard(self.a.mem_rev, self.a.jumpers); pins = {}
            for net, hits in m.jumper_map().items():
                where = "/".join("%s.%s" % k for k in m.nl.nets[net] if "MA08" in m.nl.parts[k[0]].lib)
                for ref, kind, b in hits: pins[(ref, b)] = where
            self._mem = {}
            for b in range(16):
                on = sorted(m._enabled(b << 12))
                kinds = {k for _, k in on}
                kind = "nothing" if not on else "RAM+ROM" if len(kinds) > 1 else on[0][1]
                ref = "+".join(r for r, _ in on)
                self._mem[b] = (kind, ref, pins.get((on[0][0], b), "") if on else "")
            self.mem_unused = m.jumpers_unused
        return self._mem

    def mem_expect(self, b): return self.mem_model()[b][0]

    def chip_for(self, b):
        """-> (chip ref, part, jumper pins, mux, LED) for what block b should hold"""
        kind, ref, where = self.mem_model()[b]
        return (ref, MEM_PART.get(kind, kind), where or "(no jumper: wired)", MEM_MUX.get(ref, "?"),
                MEM_LED.get(self.a.mem_rev, {}).get(ref))

    def s_mem_map(self, st):
        st.info("memory Rev %s, jumpers %s (block 0 first; R = RAM, E = EPROM, - = open)" % (self.a.mem_rev, self.a.jumpers))
        model = self.mem_model()
        wired = not any(where for _, _, where in model.values())
        if wired:
            st.info("on Rev %s the jumpers do nothing: its rework wires each chip select. The expected map below is what "
                    "its netlist decodes." % self.a.mem_rev)
        elif self.mem_unused:
            st.info("jumpers asked for that this card cannot set: %s (the expected map below is what its netlist decodes)"
                    % ", ".join("%s %X000" % kb for kb in self.mem_unused))
        rows = []; blank = {}; blank_hints = []; bad_ram = []
        for b in range(16):
            want = self.mem_expect(b); got = self.probe((b << 12) | 0x0A5); self.found[b] = got
            mark = "ok"
            if want == "RAM" and got != "RAM":
                ref, part, hdr, mux, led = self.chip_for(b)
                mark = "FAIL"
                st.fail("%X000: expected RAM (%s), found %s" % (b, ref, got),
                        "RAM missing: check %s's jumper for the block (%s), %s in its socket (pin 1, bent pins), its select "
                        "mux %s (74x151), and the 74LS32 that gates its !CE." % (ref, hdr, ref, mux))
            elif want == "RAM" and b in self.badbits:
                mark = "FAIL"; bad_ram.append(b)
            elif want == "ROM" and got != "ROM":
                ref, part, hdr, mux, led = self.chip_for(b)
                if got == "nothing":
                    mark = "WARN"; blank.setdefault(ref, []).append(b)
                    if ref not in [h[0] for h in blank_hints]: blank_hints.append((ref, hdr, mux))
                else:
                    mark = "FAIL"; st.fail("%X000: expected EPROM (%s), found %s" % (b, ref, got))
            elif want == "RAM+ROM":
                mark = "FAIL"; st.fail("%X000: the jumpers enable both a RAM and an EPROM here: one jumper per column" % b)
            elif want == "nothing" and got != "nothing":
                mark = "FAIL"
                st.fail("%X000: expected nothing (jumper open), found %s" % (b, got),
                        "A chip answers where no jumper is fitted: a jumper in the wrong column, a solder bridge on the header, "
                        "or a mux (74HCT151) input shorted to GND.")
            rows.append("%X000  %-8s %-8s %s" % (b, want, got, mark))
        if bad_ram:
            bits = 0
            for b in bad_ram: bits |= self.badbits[b]
            st.fail("RAM answers in %s, but data bits %s do not follow the writes (M2 tests them one by one)" % (
                " ".join("%X000" % b for b in bad_ram), bits_text(bits)))
        for ref, hdr, mux in blank_hints:
            bs = blank[ref]
            st.warn("%X000-%XFFF: expected EPROM (%s), reads FF: not fitted, blank, or not selected" % (bs[0], bs[-1], ref),
                    "EPROM reads FF: is %s fitted and programmed?%s A blank EPROM reads FF everywhere, so an empty socket "
                    "and a blank chip look the same here." % (ref, "" if hdr.startswith("(") else " Check its jumpers and mux %s." % mux))
        st.info("block  expected found")
        for r in rows: st.info(r)

    def ram_blocks(self):
        return [b for b in range(16) if self.found.get(b, self.mem_expect(b)) == "RAM" and self.mem_expect(b) == "RAM"]

    def data_lines(self, st, a, what):
        stuck0 = stuck1 = 0; other = 0
        pats = [1 << k for k in range(8)] + [0xFF ^ (1 << k) for k in range(8)] + [0x00, 0xFF, 0x55, 0xAA]
        for p in pats:
            self.wr(a, p); g = self.rd(a); bad = g ^ p
            stuck0 |= bad & p; stuck1 |= bad & ~p & 0xFF
            if bad and bin(p).count("1") == 1: other |= bad & ~p & 0xFF
        st.info("tested at %04X with walking ones, walking zeros, 00 FF 55 AA" % a)
        self.bad_data = stuck0 | stuck1
        if stuck0 | stuck1:
            if stuck0: st.fail("bits that will not go high: %s" % bits_text(stuck0))
            if stuck1: st.fail("bits that will not go low: %s" % bits_text(stuck1))
            self.line_fault = True
            st.hints.append("A data line fault on %s: the bus connector pin and its solder joint, the chip's I/O pin, and a "
                            "short to the next line (bits that fail together are often neighbours). If every card shows "
                            "the same bit, suspect the backplane or the bus driver's own data line." % what)
        else:
            st.info("all 8 data lines go both ways")

    def s_mem_data(self, st):
        rb = self.ram_blocks()
        if not rb: st.skip("skipped: no RAM found to test with: fix the block map first"); return
        self.data_lines(st, (rb[0] << 12) | 0x010, "the memory card")

    def address_lines(self, st, base, bits, ok, what, hint):
        addrs = [(k, base ^ (1 << k)) for k in bits if ok(base ^ (1 << k))]
        good = 0xFF & ~self.bad_data                       # marker values use only the data bits that work
        marks = [v for v in range(1, 256) if not v & ~good][:len(addrs) + 1]
        if len(marks) < len(addrs) + 1:
            st.skip("skipped: too few working data lines to tell %d addresses apart (fix the data lines first)" % (len(addrs) + 1)); return
        mb, marks = marks[-1], marks[:-1]
        self.wr(base, mb)
        for i, (k, a) in enumerate(addrs): self.wr(a, marks[i])
        bad = []; gb = self.rd(base) & good
        if gb != mb:
            for i, (k, a) in enumerate(addrs):
                if gb == marks[i]: bad.append(k); break
        for i, (k, a) in enumerate(addrs):
            g = self.rd(a) & good
            if g != marks[i] and k not in bad: bad.append(k)
        st.info("base %04X; address bits tested: %s" % (base, " ".join("A%d" % k for k, _ in addrs)))
        if bad:
            st.fail("address bits that do not reach the chip (writes land on another address): %s" % " ".join("A%d" % k for k in sorted(bad)))
            st.hints.append(hint); self.line_fault = True
        else:
            st.info("every tested address bit selects a different byte")

    def s_mem_addr(self, st):
        rb = set(self.ram_blocks())
        if not rb: st.skip("skipped: no RAM found: fix the block map first"); return
        base = (min(rb) << 12) | 0x000
        self.address_lines(st, base, range(16), lambda a: (a >> 12) in rb, "memory",
                           "A0-A7 come straight from the bus through the CD4050 buffers (IC7, IC8); A8-A15 are latched from "
                           "A0-A7 while TPA is high by the CD4042s (IC6, IC9; IC9 Q0-Q2 = A12-A14 also drive the 74HCT151 "
                           "selects). A fault only in A8 and up points at the latches or TPA (bus pin).")

    def s_mem_ram(self, st):
        rb = self.ram_blocks()
        if not rb: st.skip("skipped: no RAM found: fix the block map first"); return
        runs = []
        for b in rb:
            if runs and runs[-1][1] == b - 1: runs[-1][1] = b
            else: runs.append([b, b])
        if self.a.full:
            for s, e in runs:
                lo, hi = s << 12, (e << 12) | 0xFFF
                st.info("full test %04X-%04X (about %d s on the real card)" % (lo, hi, (hi - lo + 1) * 14 * 2 // 1000))
                if not S.memtest(self.bd, lo, hi): st.fail("RAM errors in %04X-%04X (see above)" % (lo, hi))
        else:
            errors = 0
            for b in rb:
                for start in ((b << 12), (b << 12) + 0x800, (b << 12) + 0xF00):
                    n = 64; pat = bytes(((start + i) >> 8 ^ (start + i)) & 0xFF for i in range(n))
                    for p in (pat, bytes([0x55]) * n, bytes([0xAA]) * n):
                        self.bd.write(start, p); g = self.bd.read(start, n)
                        bad = [i for i in range(n) if g[i] != p[i]]
                        if bad:
                            errors += 1
                            st.fail("%04X: wrote %02X read %02X (%d bad in this 64-byte run)" % (start + bad[0], p[bad[0]], g[bad[0]], len(bad)))
            st.info("quick test: 3 x 64 bytes in each RAM block, address pattern, 55, AA (--full tests every byte)")
            if errors and self.line_fault: st.hints.append("Expected after the data or address line failure above: fix that first.")
            elif errors: st.hints.append("Isolated bad bytes with good data and address lines point at the RAM chip itself.")

    def s_mem_rom(self, st):
        eb = [b for b in range(16) if self.mem_expect(b) == "ROM"]
        if not eb: st.info("no EPROM blocks in the jumpers"); return
        image = None
        if self.a.rom:
            data = read_file(self.a.rom)
            image = {self.a.rom_base + i: v for i, v in enumerate(data)}
            st.info("comparing with %s (%d bytes at %04X)" % (self.a.rom, len(data), self.a.rom_base))
        saved = bytearray()
        for b in eb:
            n = 4096 if (self.a.full or image is not None or self.a.save_rom) else 256
            first = self.bd.read(b << 12, n); again = self.bd.read(b << 12, 256)
            saved += first; s = sum(first) & 0xFFFF
            note = "blank (all FF)" if all(x == 0xFF for x in first) else "first bytes " + first[:8].hex(" ").upper()
            st.info("%X000-%X%03X  sum %04X  %s" % (b, b, n - 1, s, note))
            if again != first[:256]:
                st.fail("%X000: two reads of the same bytes differ" % b,
                        "Unstable EPROM reads: a slow EPROM is fine at this speed, so suspect a loose socket, a floating "
                        "!OE or !CE, or two parts driving the bus.")
            if image is not None:
                diffs = [(b << 12) + i for i in range(n) if (b << 12) + i in image and image[(b << 12) + i] != first[i]]
                if diffs: st.fail("%X000: %d bytes differ from the image, first at %04X (image %02X, read %02X)" % (
                    b, len(diffs), diffs[0], image[diffs[0]], first[diffs[0] - (b << 12)]))
        if n < 4096: st.info("(the first 256 bytes of each block; --full, --rom or --save-rom read all 4K)")
        if self.a.save_rom:
            with open(self.a.save_rom, "wb") as fh: fh.write(saved)
            st.info("saved %d bytes (the EPROM blocks in order) to %s" % (len(saved), self.a.save_rom))

    def s_mem_leds(self, st):
        rb = self.ram_blocks(); eb = [b for b in range(16) if self.mem_expect(b) == "ROM"]
        details = ["LED1 = +5 V, always on."] if self.a.mem_rev in MEM_LED else []
        if self.a.mem_rev not in MEM_LED:
            st.info("(Rev %s: its LEDs are driven by a 74LS00, IC10; each should still light with its chip)" % self.a.mem_rev)
        for kind, blocks in (("R", rb), ("E", eb)):
            for half in (0, 1):
                bs = [b for b in blocks if b >> 3 == half]
                if not bs: continue
                ref, part, hdr, mux, led = self.chip_for(bs[0]); led = led or "the LED for " + ref
                details.append("%s (%s %s): reading %X000 for 3 s now - %s should glow, the other chip LEDs stay dark" % (led, ref, part, bs[0], led))
                t = time.time()
                while time.time() - t < (3 if self.a.interactive or not self.a.sim else 0.05): self.bd.read(bs[0] << 12, 64)
        self.look(st, "did each chip's LED glow while it was read, and only then?", details)

    # ------------------------------------------------------------------ IDE / CF card
    def ide_sel(self, reg): self.bd.out(self.a.ide_sel, reg)
    def ide_out(self, reg, v): self.ide_sel(reg); self.bd.out(self.a.ide_data, v)
    def ide_in(self, reg): self.ide_sel(reg); return self.bd.inp(self.a.ide_data)

    def ide_wait(self, mask, want, seconds=3.0):
        t = time.time(); s = self.ide_in(7)
        while (s & mask) != want and time.time() - t < seconds: s = self.ide_in(7)
        return s

    def s_cf_status(self, st):
        st.info("register select OUT %d, data port %d (IDE card SV1 / SV2)" % (self.a.ide_sel, self.a.ide_data))
        s = self.ide_wait(0x80, 0x00)
        st.info("status register: " + status_text(s))
        if s == 0xFF:
            st.fail("status reads FF: nothing drives the data lines",
                    "Nothing answers: is the CF card in the adapter, the adapter powered (its power lead), the 40-way ribbon "
                    "pin 1 to pin 1? Then the IDE card: SV1 on port %d, SV2 on port %d, the 74LS138 (IC4) on N0-N2." % (self.a.ide_sel, self.a.ide_data))
        elif s & 0x80:
            st.fail("BSY stays set for 3 s", "The card never finished its power-up: check its supply at the adapter (5 V), and try another CF card.")
        elif not s & 0x40:
            st.warn("DRDY is not set", "The drive is not ready: power it off and on, then run this again.")
        if s & 0x01: st.warn("ERR is set (from power-up or the last command)")
        self.cf_ok = s not in (0xFF,) and not s & 0x80

    def s_cf_regs(self, st):
        stuck0 = stuck1 = 0
        for p in [1 << k for k in range(8)] + [0xFF ^ (1 << k) for k in range(8)] + [0x00, 0xFF, 0x55, 0xAA]:
            self.ide_out(3, p); g = self.ide_in(3); bad = g ^ p
            stuck0 |= bad & p; stuck1 |= bad & ~p & 0xFF
        st.info("LBA 0-7 register (3) written and read back: walking ones and zeros, 00 FF 55 AA")
        if stuck0: st.fail("bits that will not go high: %s" % bits_text(stuck0))
        if stuck1: st.fail("bits that will not go low: %s" % bits_text(stuck1))
        if stuck0 | stuck1:
            st.hints.append("The drive's data lines DD0-DD7 go straight from the bus to the 40-pin header (no buffer): check "
                            "the ribbon, the header pins, and the adapter. D0-D3 also feed the 74LS75 register latch (IC7).")

    def s_cf_select(self, st):
        vals = {2: 0x11, 3: 0x22, 4: 0x44, 5: 0x88}
        for r, v in vals.items(): self.ide_out(r, v)
        got = {r: self.ide_in(r) for r in vals}
        st.info("wrote " + " ".join("R%d=%02X" % rv for rv in vals.items()) + ", read " + " ".join("R%d=%02X" % rv for rv in got.items()))
        bad = [r for r in vals if got[r] != vals[r]]
        if bad:
            st.fail("registers that do not keep their own value: " + " ".join("R%d" % r for r in bad),
                    "Writes land in the wrong register: a register-address line (DA0-DA2 from the 74LS75 latch IC7, fed by "
                    "D0-D2 on OUT %d) is stuck or open. Registers that read the same value share the faulty line." % self.a.ide_sel)

    def s_cf_init(self, st):
        """what Mike Riley's BIOS does at power-up (resetide): master device, control register, 8-bit mode"""
        self.ide_wait(0x80, 0); self.ide_out(6, 0xE0); self.ide_out(0x0E, 0x02)
        s = self.ide_wait(0x80, 0); st.info("device control 0E = 02, then status " + status_text(s))
        self.ide_out(1, 0x01); self.ide_out(7, 0xEF); s = self.ide_wait(0x80, 0)
        st.info("SET FEATURES 01 (8-bit transfers): status " + status_text(s))
        if s & 0x01:
            st.fail("the card refused 8-bit mode (ERR)", "Every CF card should accept 8-bit mode (feature 01); try another card.")
        if s & 0x80: st.fail("still busy after SET FEATURES")

    def read_sector_data(self):
        s = self.ide_wait(0x88, 0x08)
        if not s & 0x08: return None, s
        self.ide_sel(0); data = self.bd.inp_block(self.a.ide_data, 512)
        return data, self.ide_in(7)

    def s_cf_identify(self, st):
        self.ide_out(6, 0xE0); self.ide_out(7, 0xEC)
        data, s = self.read_sector_data()
        if data is None:
            st.fail("no data after IDENTIFY: status " + status_text(s), "The command did not reach the card, or it does not answer IDENTIFY.")
            return
        w = lambda i: data[2 * i] | data[2 * i + 1] << 8
        txt = lambda a, b: "".join(chr(data[2 * i + 1]) + chr(data[2 * i]) for i in range(a, b)).strip()
        lba = w(60) | w(61) << 16
        st.info("model    %s" % txt(27, 47)); st.info("serial   %s" % txt(10, 20)); st.info("firmware %s" % txt(23, 27))
        st.info("LBA sectors %d (%.1f MB); CHS %d/%d/%d" % (lba, lba * 512 / 1e6, w(1), w(3), w(6)))
        if not w(49) & 0x200: st.warn("the card does not report LBA support (word 49 bit 9)")
        if s & 0x08: st.warn("DRQ still set after 512 bytes: the card had more data than expected")
        if not txt(27, 47).strip(" \0"): st.warn("blank model string")

    def s_cf_read(self, st):
        n = max(1, self.a.sectors); image = read_file(self.a.image) if self.a.image else None
        for lba in range(n):
            self.ide_out(2, 1); self.ide_out(3, lba & 0xFF); self.ide_out(4, lba >> 8 & 0xFF); self.ide_out(5, lba >> 16 & 0xFF)
            self.ide_out(6, 0xE0 | (lba >> 24 & 0x0F)); self.ide_out(7, 0x20)
            data, s = self.read_sector_data()
            if data is None:
                st.fail("LBA %d: no data, status %s" % (lba, status_text(s))); return
            if lba == 0:
                st.info("LBA 0, first 64 bytes:")
                for i in range(0, 64, 16): st.info("  %03X  %s" % (i, data[i:i + 16].hex(" ").upper()))
                st.info("  ... last two bytes %02X %02X%s" % (data[510], data[511], " (a PC boot signature)" if data[510:512] == b"\x55\xaa" else ""))
            if s & 0x09: st.warn("LBA %d: status after the read %s" % (lba, status_text(s)))
            if image is not None:
                want = image[lba * 512:(lba + 1) * 512]
                if data != want:
                    i = next(k for k in range(512) if k >= len(want) or data[k] != want[k])
                    st.fail("LBA %d differs from the image at byte %d" % (lba, i))
        if image is not None and st.status == "PASS": st.info("%d sector(s) match %s" % (n, self.a.image))

    def s_cf_write(self, st):
        lba = self.a.cf_write_lba
        def rw(cmd, data=None):
            self.ide_out(2, 1); self.ide_out(3, lba & 0xFF); self.ide_out(4, lba >> 8 & 0xFF); self.ide_out(5, lba >> 16 & 0xFF)
            self.ide_out(6, 0xE0 | (lba >> 24 & 0x0F)); self.ide_out(7, cmd)
            if cmd == 0x20: return self.read_sector_data()[0]
            s = self.ide_wait(0x88, 0x08)
            if not s & 0x08: return None
            self.ide_sel(0); self.bd.out_block(self.a.ide_data, data); return self.ide_wait(0x80, 0)
        orig = rw(0x20)
        if orig is None: st.fail("could not read LBA %d first" % lba); return
        pat = bytes((i * 7 + lba) & 0xFF for i in range(512))
        if rw(0x30, pat) is None: st.fail("the card did not ask for data after WRITE SECTORS"); return
        back = rw(0x20)
        if back != pat: st.fail("LBA %d read back differs from what was written" % lba)
        rw(0x30, orig); again = rw(0x20)
        if again != orig: st.fail("LBA %d: the original contents did NOT read back after restoring" % lba)
        else: st.info("LBA %d: wrote a pattern, read it back, restored the original and checked it" % lba)

    # ------------------------------------------------------------------ 6845 card
    def s_vid_map(self, st):
        vb = self.a.video_base >> 12; rows = []
        for b in range(16):
            if b == vb: continue
            got = self.probe((b << 12) | 0x0A5)
            if got != "nothing":
                st.fail("%X000: %s answers (only the 6845 card should be in the backplane)" % (b, got),
                        "Another card is in the backplane, or the 6845 card decodes a second block: check SV1 (one jumper).")
            rows.append("%X000 %s" % (b, got))
        lo = self.probe(self.a.video_base | 0x0A5)
        st.info("%04X (video RAM): %s" % (self.a.video_base, lo))
        if lo != "RAM":
            st.fail("no video RAM at %04X" % self.a.video_base,
                    "The card does not answer in its block: SV1 jumper (1-2 = block 7), the 74LS85 compare (IC4) against "
                    "the latched A12-A15 (74LS373 IC2, latched on TPA), and -VMA: the compare only matches while -VMA is low.")
        if st.status != "FAIL": st.info("other blocks: nothing answers")

    def s_vid_data(self, st):
        self.data_lines(st, self.a.video_base + 0x10, "the 6845 card (IDT7134 right port)")

    def s_vid_addr(self, st):
        base = self.a.video_base
        self.address_lines(st, base, range(11), lambda a: True, "video RAM",
                           "A0-A10 reach the IDT7134's right port straight from the bus (A0-A7) and the 74LS373 latch (A8-A10). "
                           "A11 picks RAM (0) or CRTC (1) and is not part of this test. The CPU sees 2K: the 7134's A11R is tied low.")

    def s_vid_ram(self, st):
        base = self.a.video_base; n = 0x800
        pat = bytes(((base + i) >> 8 ^ (base + i)) & 0xFF for i in range(n))
        errors = 0
        for name, p in (("address pattern", pat), ("55", bytes([0x55]) * n), ("AA", bytes([0xAA]) * n)):
            self.bd.write(base, p); g = self.bd.read(base, n)
            bad = [i for i in range(n) if g[i] != p[i]]
            if bad:
                errors += 1; st.fail("%s: %d bad bytes, first %04X wrote %02X read %02X" % (name, len(bad), base + bad[0], p[bad[0]], g[bad[0]]))
        st.info("all 2K of video RAM (%04X-%04X): address pattern, 55, AA" % (base, base + n - 1))

    def s_vid_crtc(self, st):
        ar, dr = self.a.video_base + 0x800, self.a.video_base + 0x801
        def setreg(r, v, at=None): self.wr(at or ar, r); self.wr(dr, v)
        def getreg(r, at=None, rd=None): self.wr(at or ar, r); return self.rd(rd or dr)
        bad = []
        for v14, v15 in ((0x15, 0x2A), (0x2A, 0x15), (0x3F, 0x00), (0x00, 0xFF), (0x01, 0x80), (0x20, 0x01)):
            setreg(14, v14); setreg(15, v15)
            g14, g15 = getreg(14) & 0x3F, getreg(15)
            if (g14, g15) != (v14, v15): bad.append((v14, v15, g14, g15))
        st.info("cursor registers R14 (6 bits) and R15 written through %04X/%04X and read back, switching registers each time" % (ar, dr))
        if bad:
            v14, v15, g14, g15 = bad[0]
            if len(bad) == 6 and all((b[2], b[3]) == (0x3F, 0xFF) for b in bad):
                st.fail("the CRTC never answers: R14/R15 read FF",
                        "Nothing drives the bus on a CRTC read. The 6845's E is TPB: bus driver firmware older than 2026-10-11 "
                        "never raises TPB in a memory cycle. Then: CS from the 74LS85 decode with A11 high, R/W = -MRW, and "
                        "-RESET (a low -RESET holds the 6845 reset).")
            else:
                st.fail("wrote R14=%02X R15=%02X, read %02X %02X (%d of 6 patterns wrong)" % (v14, v15, g14, g15, len(bad)),
                        "Reads of R14 coming back as the R15 value (or ANDed with it) mean RAM also answers at %04X: another "
                        "card decodes this block (the memory card's block-%X jumper must be open). Otherwise a CRTC data line "
                        "(D0-D7 on the 6845 pins 26-33) or RS (= A0, pin 24)." % (ar, self.a.video_base >> 12))
        else:
            st.info("R14/R15 hold their values: the CRTC's E (TPB), CS, R/W and RS paths all work")
            setreg(14, 0x07, at=ar + 0x7FE)                   # the CRTC repeats through x800-xFFF: RS is A0 alone
            g = getreg(14, at=ar + 0x7FE, rd=dr + 0x400) & 0x3F
            if g == 0x07: st.info("and it repeats through %04X-%04X, as drawn (RS = A0)" % (ar, ar + 0x7FF))
            else: st.warn("no repeat at %04X/%04X (read %02X): RS or the A11 decode differs from the drawing" % (ar + 0x7FE, dr + 0x400, g))

    def s_vid_screen(self, st):
        ar, dr, base = self.a.video_base + 0x800, self.a.video_base + 0x801, self.a.video_base
        for r, v in enumerate(HBIOS_CRTC): self.wr(ar, r); self.wr(dr, v)
        st.info("CRTC R0-R15 = HBIOS v1.0.4's table: " + " ".join(str(v) for v in HBIOS_CRTC))
        screen = bytearray(b" " * 1024)
        def put(row, col, text, inverse=False):
            for i, ch in enumerate(text.encode()):
                screen[row * 64 + col + i] = ch | (0x80 if inverse else 0)
        put(0, 0, "+" + "-" * 62 + "+")
        for row in range(1, 15): put(row, 0, "|"); put(row, 63, "|")
        put(15, 0, "+" + "-" * 62 + "+")
        put(2, 17, "SYSTEM-5 6845 VIDEO BRING-UP")
        put(4, 4, "CHARACTER SET (96 PRINTABLE; ROW 7 IS LOWER CASE):")
        put(5, 4, "".join(chr(c) for c in range(0x20, 0x40))); put(6, 4, "".join(chr(c) for c in range(0x40, 0x60)))
        put(7, 4, "".join(chr(c) for c in range(0x60, 0x7F)))
        put(8, 4, "REVERSE VIDEO:"); put(9, 4, "".join(chr(c) for c in range(0x40, 0x60)), inverse=True)
        put(11, 4, "ROW 11 - 16 ROWS OF 64 - CURSOR ON THE LAST ROW")
        put(13, 4, "0123456789" * 5)
        self.bd.write(base, bytes(screen))
        back = self.bd.read(base, 1024)
        if back != bytes(screen): st.fail("the test screen did not read back from video RAM")
        self.look(st, "does the monitor show the test screen as described?", [
            "On the monitor (composite out, 64 x 16):",
            "  a border of + - | around the whole screen, all four corners visible",
            "  'SYSTEM-5 6845 VIDEO BRING-UP' centred on row 2",
            "  the printable characters on rows 5-7 (space to ?, @ to _, then ` to ~ in lower case: Rev B's goodfont),",
            "  and @ to _ in reverse video on row 9 (a Rev A card's 64-character font shows row 7 as upper case)",
            "  digits 0-9 repeated on row 13, and the cursor blinking at the start of the bottom row",
            "If the picture rolls or tears: R0-R7 assume BYTE's 9 MHz crystal and /6 character clock; check the crystal.",
            "If the characters are wrong but the layout is right: the character EPROM (2732, Rev B 'goodfont').",
        ])

    # ------------------------------------------------------------------ all cards together
    def s_all_map(self, st):
        vb = self.a.video_base >> 12
        if self.mem_expect(vb) != "nothing":
            st.fail("the memory card answers in block %X too, where the 6845 card sits (%s %s)" % (vb, self.mem_expect(vb), self.chip_for(vb)[0]),
                    "Both cards drive the bus at %X000-%XFFF. Open the memory card's block-%X jumper column (--jumpers "
                    "position %d = '-'). On the reworked Rev B the jumpers do not decide this: its RAM fills 0000-7FFF." % (vb, vb, vb, vb + 1))
        rows = []; blank = []
        for b in range(16):
            want = "RAM" if b == vb else self.mem_expect(b)
            got = self.probe((b << 12) | 0x0A5); self.found[b] = got
            if want == "ROM" and got == "nothing": blank.append(b)
            elif got != want: st.fail("%X000: expected %s, found %s" % (b, want, got))
            rows.append("%X000  %-8s %s" % (b, want, got))
        if blank: st.warn("EPROM blocks reading FF (blank or not fitted): " + " ".join("%X000" % b for b in blank))
        st.info("block  expected found (block %X = the 6845 card)" % vb)
        for r in rows: st.info(r)

    def s_all_cross(self, st):
        rb = [b for b in self.ram_blocks() if b != self.a.video_base >> 12]
        if not rb: st.fail("no memory card RAM to test with"); return
        ma, va = (rb[0] << 12) | 0x123, self.a.video_base | 0x123
        self.wr(ma, 0x5A); self.wr(va, 0xA5)
        for i in range(4): self.wr(ma, 0x30 + i); self.wr(va, 0x60 + i)
        gm, gv = self.rd(ma), self.rd(va)
        st.info("alternating writes to %04X (memory) and %04X (video): read %02X and %02X" % (ma, va, gm, gv))
        if (gm, gv) != (0x33, 0x63): st.fail("memory and video RAM disturb each other")

    def s_all_ide(self, st):
        self.ide_out(3, 0x5A); self.ide_sel(3)
        rb = [b for b in self.ram_blocks() if b != self.a.video_base >> 12]
        for i in range(32): self.wr(((rb[0] if rb else 0) << 12) + i, i)
        for i in range(16): self.wr(self.a.video_base + i, 0x40 + i)
        g = self.bd.inp(self.a.ide_data)
        st.info("CF register 3 = 5A, then 48 memory and video writes, then INP %d without reselecting: %02X" % (self.a.ide_data, g))
        if g != 0x5A:
            st.fail("memory cycles disturbed the CF card's register latch or the register",
                    "The IDE card must ignore memory cycles (N = 0): check the 74LS138 (IC4) enables and the latch strobe.")

    # ------------------------------------------------------------------ plans
    def plan(self, name):
        s = self.step
        s("B1", "bus driver, bus power, bus master", self.s_connect)
        if self.steps[-1].status == "FAIL": return
        s("B2", "control lines idle", self.s_idle)
        if name == "memory":
            s("M1", "block map against the jumpers", self.s_mem_map)
            s("M2", "data lines (RAM)", self.s_mem_data)
            s("M3", "address lines (RAM)", self.s_mem_addr)
            s("M4", "RAM test" + (" (full)" if self.a.full else " (quick)"), self.s_mem_ram)
            s("M5", "EPROM read", self.s_mem_rom)
            s("M6", "chip-select LEDs", self.s_mem_leds)
        elif name == "cf":
            s("C1", "drive status", self.s_cf_status)
            if self.steps[-1].status == "FAIL": return
            s("C2", "register data path", self.s_cf_regs)
            s("C3", "register select (DA0-DA2)", self.s_cf_select)
            s("C4", "BIOS set-up: control register, 8-bit mode", self.s_cf_init)
            s("C5", "IDENTIFY DEVICE", self.s_cf_identify)
            s("C6", "read sector%s" % ("s 0-%d" % (self.a.sectors - 1) if self.a.sectors > 1 else " 0"), self.s_cf_read)
            if self.a.cf_write_lba is not None: s("C7", "write test on LBA %d (restored)" % self.a.cf_write_lba, self.s_cf_write)
        elif name == "video":
            s("V1", "address decode (block %X only)" % (self.a.video_base >> 12), self.s_vid_map)
            s("V2", "video RAM data lines", self.s_vid_data)
            s("V3", "video RAM address lines", self.s_vid_addr)
            s("V4", "video RAM, all 2K", self.s_vid_ram)
            s("V5", "CRTC register path", self.s_vid_crtc)
            s("V6", "HBIOS set-up and test screen", self.s_vid_screen)
        elif name == "all":
            s("A1", "combined address map", self.s_all_map)
            s("A2", "memory and video RAM independent", self.s_all_cross)
            s("A3", "CRTC not double-mapped", self.s_vid_crtc)
            s("A4", "CF drive status", self.s_cf_status)
            s("A5", "CF card ignores memory traffic", self.s_all_ide)
            s("A6", "IDENTIFY DEVICE", self.s_cf_identify)
        if not self.a.keep: self.bd.master(False)


SIM_CARDS = {"memory": ("mem",), "cf": ("ide",), "video": ("video",), "all": ("mem", "video", "ide")}


def sim_driver(a):
    from backplane import Backplane
    from fwsim import FwCard
    kw = dict(cards=SIM_CARDS[a.plan], jumpers=a.jumpers, image=a.image, mem_rev=a.mem_rev)
    for f in a.fault or []:
        k, *rest = f.split(":")
        if k == "stuck": kw.setdefault("stuck", {})[rest[0]] = (int(rest[1]), int(rest[2]))
        elif k == "empty": kw.setdefault("empty", []).append(rest[0])
        elif k == "nodrive": kw["drive"] = False
        elif k == "addr": kw["addr"] = (int(rest[0]), int(rest[1]))
        elif k == "card-jumpers": kw["jumpers"] = rest[0].upper()      # the card jumpered unlike --jumpers says
        elif k == "legacy": kw["_legacy"] = True
        else: raise SystemExit("--fault: stuck:CARD:BIT:LEVEL, empty:REF, addr:BIT:LEVEL, card-jumpers:J, nodrive or legacy")
    legacy = kw.pop("_legacy", False)
    bp = Backplane(**kw)
    if a.rom: bp.load_rom(read_file(a.rom), a.rom_base)
    return S.BusDriver(transport=FwCard(bp, legacy=legacy)), bp


def hexaddr(s):
    """A bus address is hex, as the help and the reports print it: 8000, 0x8000 and $8000 are all 8000 hex."""
    s = str(s).strip().lower()
    return int(s[1:] if s.startswith("$") else s[2:] if s.startswith("0x") else s, 16)


def main(argv=None):
    ap = argparse.ArgumentParser(description="System-5 card bring-up from the bus driver card", epilog=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan", choices=("memory", "cf", "video", "all"))
    ap.add_argument("--port"); ap.add_argument("--log", action="store_true", help="show the serial traffic")
    ap.add_argument("--sim", action="store_true", help="the simulated backplane (netlist models) instead of the card")
    ap.add_argument("--fault", action="append", help="simulator only: stuck:mem:3:0, empty:IC5, addr:4:0, card-jumpers:RRR-----EEEEEEE-, nodrive, legacy (old firmware)")
    ap.add_argument("--jumpers", default=DEFAULT_JUMPERS, help="memory card blocks 0-F: R RAM, E EPROM, - open (default %(default)s)")
    ap.add_argument("--mem-rev", default="D", choices=("D", "C", "B-built"), help="memory card revision (default D)")
    ap.add_argument("--full", action="store_true", help="test every RAM byte (minutes on the real card)")
    ap.add_argument("--rom", help="compare the EPROM blocks with this binary image")
    ap.add_argument("--rom-base", type=hexaddr, default=0x8000, help="bus address of the image's first byte (default 8000)")
    ap.add_argument("--save-rom", help="save what the EPROM blocks read to this file")
    ap.add_argument("--ide-sel", type=int, default=2, help="IDE card register-select port, SV1 (default 2)")
    ap.add_argument("--ide-data", type=int, default=3, help="IDE card data port, SV2 (default 3)")
    ap.add_argument("--image", help="cf: compare the sectors read with this disk image; --sim: the CF card holds it")
    ap.add_argument("--sectors", type=int, default=1, help="cf: how many sectors to read from LBA 0 (default 1)")
    ap.add_argument("--cf-write-lba", type=int, help="cf: write test on this LBA (its contents are saved and put back)")
    ap.add_argument("--video-base", type=hexaddr, default=0x7000, help="6845 card block (SV1), default 7000")
    ap.add_argument("--interactive", action="store_true", help="ask about the checks by eye (LEDs, the monitor)")
    ap.add_argument("--keep", action="store_true", help="stay bus master at the end (the test screen stays either way)")
    ap.add_argument("--report", help="also write the results to this Markdown file")
    a = ap.parse_args(argv)
    a.jumpers = a.jumpers.upper()
    if len(a.jumpers) != 16 or set(a.jumpers) - set("RE-"): ap.error("--jumpers: 16 characters of R, E and -")
    if a.sim:
        bd, bp = sim_driver(a)
        if a.log: bd.log = sys.stderr
    else:
        bd, bp = S.BusDriver(a.port, log=sys.stderr if a.log else None), None
    print("System-5 bring-up: %s%s" % (a.plan, " (SIMULATED backplane)" if a.sim else ""))
    b = Bringup(bd, a); b.plan(a.plan); ok = b.summary()
    if bp is not None and bp.fights():
        print("simulator: %d bus fights during the run, first: %s" % (len(bp.fights()), bp.fights()[0]))
    if a.report: b.report(a.report, a.plan); print("report written to", a.report)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
