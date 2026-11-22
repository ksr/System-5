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
Either card (firmware of 2026-11-21 or later: "walk-1" in its banner), the CPU card out:
  shorts   a short finder: every bus line the card reaches (28 on BUSDRV-B, 34 on BUSDRV-C) pulled low alone, and the
           pulled-down ones driven high alone, every other line watched: two lines that move together are shorted.
           For a bare backplane (a new bus Rev D after its sockets are soldered) and for one new card at a time.
           It finds a short between two lines, to ground or to +5V; not an open joint, nor a short behind a card's buffers
BUSDRV-C only (the 36-pin card):
  bus36    the bus Rev D with no CPU card: every pulled line at rest, each open-collector line (-RESET -INT -EF -EF1
           -EF2 -EF3 -PAUSE -DMAIN) low alone and back up, the pull-downs and pull-ups of the driven lines
  load     CPU Rev D and a memory card in place, the DEBUG ribbon on and the CPU card's JP1 on EXT, and the bus driver
           never bus master: the cable, RESET and LOAD, a program into RAM by DMA IN with the clock stepped, RUN (the
           program reads itself back, and the bus driver checks every byte on the bus), -PAUSE, a bus reset

Run against the real card (the Nano's USB port is found automatically):
  python3 bringup.py memory
  python3 bringup.py memory --full --rom ../../../private-resources/elf/firmware/elfos-install-rom/<image>.bin
  python3 bringup.py cf
  python3 bringup.py video --interactive
Run against the simulated backplane (the netlist models; nothing to plug in):
  python3 bringup.py --sim memory
  python3 bringup.py --sim memory --fault stuck:mem:3:0       (see what a stuck data line looks like)
  python3 bringup.py --sim load                               (BUSDRV-C: CPU Rev D in place, a program loaded and run)
  python3 bringup.py --sim load --fault nocable               (the DEBUG ribbon left off)
  python3 bringup.py --sim shorts --busdrv C --fault short:N1:RESET     (a solder bridge between two slot pins)

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
    # ------------------------------------------------------------------ BUSDRV-C: the 36-pin bus, and the CPU card in place
    OC_LINES = ("-RESET", "-INT", "-EF", "-EF1", "-EF2", "-EF3", "-PAUSE", "-DMAIN")
    PULLED = (("TPA", 0), ("TPB", 0), ("-MRD", 1), ("-MRW", 1), ("-VMA", 1))        # the bus Rev D's RN3 / RN4
    RN = "the bus Rev D's resistor networks RN1-RN4 hold these lines (hardware/bus/kicad/rev-d)"

    def snap(self):
        """the SNAP line as {name: text}"""
        return self.bd.fields(self.bd.snap())

    def s_c_connect(self, st):
        st.info("bus driver: %s" % " / ".join(self.bd.banner))
        s = self.bd.status(); st.info(s)
        if "bus=on" not in s:
            st.fail("the bus has no power", "Power the backplane; the bus driver runs its expanders from bus +5V.")
            return
        if self.bd.board() != "C":
            st.fail("this plan needs BUSDRV-C: the card has no third expander (U3 at 0x22)",
                    "BUSDRV-B reaches the 30-pin bus only. Check U3 and its 0.1 uF if this is a BUSDRV-C.")

    def s_x_idle(self, st):
        f = self.snap(); st.info(self.bd.lines[0] if self.bd.lines else "")
        for name in self.OC_LINES + ("-MRD", "-MRW", "-VMA"):
            if f.get(name) != "1": st.fail("%s reads low with nothing pulling it" % name, "A card in the backplane holds it, or it is shorted to ground.")
        for name in ("TPA", "TPB"):
            if f.get(name) != "0": st.fail("%s reads high with nothing driving it" % name, "No pull-down on it, or a card drives it: this plan is for an empty backplane.")
        if f.get("N") != "0": st.fail("N0-N2 read %s with nothing driving them" % f.get("N"), "A pull-down missing on N0-N2 (RN3).")
        if f.get("D") != "FF": st.fail("D0-D7 read %s with nothing driving them" % f.get("D"), "A pull-up missing on a data line (RN1), or a card drives the bus.")
        if st.status == "PASS": st.info("every pulled line rests where its resistor holds it; A0-A7, Q and SC0 have none")

    def s_x_lines(self, st):
        down = set()                                           # lines found without a pull-up: they stay where they were put
        for name in self.OC_LINES:
            self.bd.line(name, True); f = self.snap()
            if f.get(name) != "0": st.fail("%s does not go low when the bus driver pulls it" % name, "U2 / U3 of the bus driver, or its solder joint to the bus pin.")
            also = [n for n in self.OC_LINES if n != name and n not in down and f.get(n) != "1"]
            if also: st.fail("pulling %s low also takes %s low" % (name, " ".join(also)), "A short between two bus lines: look between neighbouring pins of the slots and of U2 / U3.")
            self.bd.line(name, False); f = self.snap()
            if f.get(name) != "1":
                down.add(name)
                st.fail("%s stays low after it is let go: no pull-up on it" % name, "Check the resistor network on that line: " + self.RN + ".")
        if st.status == "PASS": st.info("each of %s goes low alone and comes back up" % " ".join(self.OC_LINES))

    def s_x_bus(self, st):
        def let_go():
            self.bd.master(False); return self.snap()
        for name, rest in self.PULLED:
            self.bd.master(True); self.bd.cmd(name, 1); f = let_go()        # driven to its active level, then released
            if f.get(name) != str(rest):
                st.fail("%s stays %s after it is let go: no %s on it" % (name, f.get(name), "pull-down" if rest == 0 else "pull-up"),
                        "Check the resistor network on that line: " + self.RN + ".")
        self.bd.master(True); self.bd.cmd("N", 7); f = let_go()
        if f.get("N") != "0": st.fail("N0-N2 read %s after N = 7 is let go: a pull-down missing" % f.get("N"), "RN3 of the bus Rev D.")
        self.bd.master(True); got = self.rd_after_release(0x00); self.bd.master(False)
        if got != 0xFF:
            st.fail("D0-D7 read %02X after 00 is let go: no pull-up on %s" % (got, bits_text(~got & 0xFF)), "RN1 of the bus Rev D.")
        if st.status == "PASS": st.info("TPA, TPB and N0-N2 fall back low, -MRD, -MRW, -VMA and D0-D7 come back high")

    def rd_after_release(self, v):
        self.charge(v); return self.bd.value("RD-DATABUS")

    def s_x_debug(self, st):
        d = self.bd.dbg(); f = self.snap()
        st.info("DEBUG header (J4) inputs: CLOCK=%s SC0=%s SC1=%s; bus SC0=%s" % (d.get("CLOCK"), d.get("SC0"), d.get("SC1"), f.get("SC0")))
        if (d.get("CLOCK"), d.get("SC0"), d.get("SC1")) != ("1", "1", "1"):
            st.warn("the DEBUG inputs do not all read 1 with no cable on J4 (the expander pulls them up)",
                    "A cable is on J4, or a short at U3's GPB0-2.")
        try:
            self.bd.clock_test(); st.warn("CLK OUT is followed on the DEBUG cable: a CPU card is connected", "This plan is for the backplane without the CPU card.")
        except S.CardError:
            st.info("no CPU card answers on the DEBUG cable, as expected")

    def load_image(self, n=48):
        """a program that reads its own n bytes one after the other, then sets Q and idles: every byte of the load
        comes back on the bus, where the bus driver can see it with the CPU card in place"""
        prog = bytes([0xF8, 0x00, 0xB1, 0xA1, 0xF8, n, 0xA2, 0x41, 0x22, 0x82, 0x3A, 0x07, 0x7B, 0x00])
        return prog + bytes((0xA5 ^ (i * 29)) & 0xFF for i in range(n - len(prog)))

    def s_l_cable(self, st):
        try: st.info(self.bd.clock_test())
        except S.CardError as e:
            st.fail(str(e).split("Error: ")[-1], "Fit the 6-way ribbon from the bus driver's J4 to the CPU card's J2 (DEBUG), and put the CPU card's "
                    "JP1 on EXT: LOAD mode by the clock needs the bus driver to be the 1802's clock.")
            return
        d = self.bd.dbg(); st.info("DEBUG inputs: CLOCK=%s SC0=%s SC1=%s" % (d.get("CLOCK"), d.get("SC0"), d.get("SC1")))

    def s_l_modes(self, st):
        want = {"reset": ("0", "1"), "load": ("0", "0")}
        for m in ("reset", "load"):
            self.bd.mode(m); got = self.bd.cpu_mode(); f = self.snap()
            if got != m.upper() or (f.get("-RESET"), f.get("-PAUSE")) != want[m]:
                st.fail("MODE %s: the bus shows cpu=%s -RESET=%s -PAUSE=%s" % (m.upper(), got, f.get("-RESET"), f.get("-PAUSE")),
                        "-RESET is on U2 and -PAUSE on U3 of the bus driver; another card (the IO panel's RUN and LOAD toggles) can hold them too.")
        if st.status == "PASS": st.info("RESET (-RESET low) and LOAD (-RESET and -PAUSE low) are on the bus; the 1802 is in LOAD mode")

    def s_l_load(self, st):
        img = self.load_image(); self.image = img
        try:
            first = self.bd.dma_load(img)
        except S.CardError as e:
            msg = str(e).split("Error: ")[-1]; hint = "See what the card found; the LOAD steps are in the sketch's header."
            if "-DMAIN" in msg: hint = "-DMAIN (slot position 34, U3 GPA4): something else holds it, or it does not reach the CPU card's U7."
            elif "CLK OUT" in msg or "TPA" in msg: hint = "The DEBUG ribbon (J4 to the CPU card's J2) and the CPU card's JP1 on EXT."
            elif "-MRW" in msg or "-MRD" in msg: hint = "The 1802 made a DMA cycle (SC0 low) with the wrong strobes: check -MRD and -MRW at the CPU card."
            st.fail(msg, hint); return
        if first != 0: st.fail("the first byte went to %04X, not 0000" % first, "LOAD mode did not start from RESET: R(0) was not cleared.")
        else: st.info("%d bytes by DMA IN to 0000-%04X, each address read off the bus as it was written" % (len(img), len(img) - 1))

    def trace(self, edges):
        import cputrace
        return cputrace.cycles([(e, cputrace.bits(*h)) for e, h in self.bd.clk(edges)])

    def s_l_run(self, st):
        img = getattr(self, "image", None)
        if img is None: st.skip("nothing was loaded"); return
        self.bd.mode("run"); cy = self.trace((len(img) * 4 + 12) * 32)
        k = next((i for i, c in enumerate(cy) if c["rd"] or c["wr"]), None)      # past the initialization cycle
        if k is None: st.fail("the 1802 made no memory cycle in RUN", "The clock: the DEBUG ribbon and JP1 on EXT."); return
        cy = cy[k:]; first = cy[0]; a0 = (first["hi"] << 8) | (first["lo"] or 0)
        if a0 != 0 or first["d"] != img[0] or not first["vma"]:
            st.fail("the first fetch after RUN is %04X = %02X%s, not 0000 = %02X from RAM" % (a0, first["d"], "" if first["vma"] else " (-VMA high: the EPROM)", img[0]),
                    "LOAD mode did not set the CPU card's LOADED flag (U8A), so the boot map put the EPROM at 0000.")
            return
        seen = {}
        for c in cy:
            if c["rd"] and not c["wr"]: seen[(c["hi"] << 8) | (c["lo"] or 0)] = c["d"]
        missing = [a for a in range(len(img)) if a not in seen]; wrong = [a for a in range(len(img)) if a in seen and seen[a] != img[a]]
        if wrong:
            st.fail("%d byte(s) read back wrong, first %04X: loaded %02X, read %02X" % (len(wrong), wrong[0], img[wrong[0]], seen[wrong[0]]),
                    "The byte was not on the data lines through the DMA write, or the memory card took a second write.")
        elif missing: st.fail("the program did not get to %04X (and %d more): it did not run as loaded" % (missing[0], len(missing) - 1))
        elif not any(c["q"] for c in cy): st.fail("the program read every byte but Q never rose")
        else: st.info("the program ran from 0000 in RAM and read all %d bytes back as loaded; Q is high" % len(img))

    def s_l_pause(self, st):
        self.bd.mode("pause"); held = self.bd.clk(64); self.bd.mode("run"); free = self.bd.clk(64)
        if len(held) > 1: st.fail("the bus changed %d times in 64 clock edges with -PAUSE low" % (len(held) - 1), "-PAUSE does not reach the 1802's WAIT (the CPU card's U7).")
        elif len(free) < 4: st.fail("the bus stayed still after -PAUSE was let go")
        else: st.info("-PAUSE low holds every bus line through 64 clock edges; let go, the cycles go on")

    def s_l_reset(self, st):
        img = getattr(self, "image", None)
        if img is None: st.skip("nothing was loaded"); return
        self.bd.mode("reset"); self.bd.mode("run"); cy = [c for c in self.trace(160) if c["rd"]]    # (past the initialization cycle)
        if not cy: st.fail("no fetch after RESET then RUN"); return
        c = cy[0]; a0 = (c["hi"] << 8) | (c["lo"] or 0)
        if a0 == 0 and c["d"] == img[0] and c["vma"]: st.info("a reset from the bus keeps LOADED: RUN starts the loaded program again (the CPU card's own RESET/RUN switch, or power-on, brings HBIOS back)")
        else: st.fail("after RESET then RUN the first fetch is %04X = %02X%s" % (a0, c["d"], "" if c["vma"] else " from the EPROM"),
                      "A reset from the bus should leave the CPU card's LOADED flag set.")

    # ------------------------------------------------------------------ shorts: every bus line driven alone (WALK)
    # The bus Rev D's resistors (hardware/bus/kicad/rev-d, RN1-RN4, 10k): pull-downs on these five; pull-ups on D0-D7,
    # the eight open-collector lines and -MRD, -MRW, -VMA; none on A0-A7, Q and SC0. The 2009 backplane has none at
    # all. In this test the expanders' own 100k pull-ups are on, so a line the backplane does not hold rests high.
    PULLED_DOWN = ("TPA", "TPB", "N0", "N1", "N2")
    NO_RESISTOR = tuple("A%d" % i for i in range(8)) + ("Q", "SC0")
    # the slot by position, 1 (GND) to 30 (+5V) and on to 36 (docs/manual/bus.md, "The 36-pin extension")
    SLOT = ("GND", "N0", "N1", "-RESET", "-VMA", "-EF", "N2", "-INT") + tuple("A%d" % i for i in range(7, -1, -1)) + \
           ("-MRW", "-MRD", "TPB", "TPA", "Q") + tuple("D%d" % i for i in range(7, -1, -1)) + \
           ("+5V", "-EF1", "-EF2", "-EF3", "-DMAIN", "SC0", "-PAUSE")

    def where(self, x, y):
        """where two lines (or a line and a supply) lie side by side: in the slots, on the bus driver's expanders"""
        out = []; pos = {n: i + 1 for i, n in enumerate(self.SLOT)}
        if x in pos and y in pos and abs(pos[x] - pos[y]) == 1:
            out.append("neighbours in every slot (positions %d and %d from the GND end)" % tuple(sorted((pos[x], pos[y]))))
        px, py = S.WALK_PINS.get(x), S.WALK_PINS.get(y)
        if px is not None and py is not None and px >> 3 == py >> 3 and abs(px - py) == 1:
            pin = lambda p: (21 if not p >> 3 & 1 else 1) + (p & 7)             # MCP23017: GPA0-7 = pins 21-28, GPB0-7 = 1-8
            out.append("neighbours on the bus driver's U%d (pins %d and %d)" % ((px >> 4) + 1, pin(px), pin(py)))
        return " and ".join(out) if out else "not neighbours in the slots or on the bus driver: look at the card in the bus"

    def s_s_connect(self, st):
        st.info("bus driver: %s" % " / ".join(self.bd.banner))
        s = self.bd.status(); st.info(s)
        if "bus=on" not in s:
            st.fail("the bus has no power", "Power the backplane; the bus driver runs its expanders from bus +5V."); return
        if not self.bd.walkable:
            st.fail("this firmware has no WALK command (no walk-1 in its banner)", "Load the current sketch: embedded/bus-driver/s5-bus-driver."); return
        if "mode=MASTER" in s: self.bd.master(False)
        try: self.rest = [self.bd.walk() for _ in range(3)]
        except S.CardError as e:
            st.fail("the bus driver will not drive a line: %s" % str(e).split("Error:")[-1].strip(),
                    "This test is for a backplane with the CPU card out.")

    def s_s_rest(self, st):
        lines = self.lines = self.bd.walk_lines(); r = self.rest
        kind = self.kind = {n: "H" if all(x[n] for x in r) else "L" if not any(x[n] for x in r) else "U" for n in lines}
        bus = getattr(self.a, "bus", "auto")
        rev_d = bus == "d" or (bus == "auto" and (self.bd.board() == "C" or sum(kind[n] != "H" for n in self.PULLED_DOWN) >= 3))
        self.expected = {n: "L" if rev_d and n in self.PULLED_DOWN else "H" for n in lines}
        st.info("%d lines, each read three times with nothing driven and the expanders' 100k pull-ups on" % len(lines))
        st.info("backplane: " + ("the bus Rev D (its 10k resistors hold TPA, TPB and N0-N2 low, the other pulled lines high)" if rev_d else
                                 "no pull-downs seen: the 2009 backplane (no resistors: the 100k pull-ups hold every line high)"))
        self.cpu_there = kind.get("Q") == "L"
        if self.cpu_there:
            also = [n for n in lines if n[0] == "A" and kind[n] == "L"]
            st.fail("Q rests low%s" % (" and so do " + " ".join(also) if also else ""),
                    "Only a CPU card drives Q, and the address lines have nothing but the 100k pull-ups on them: a CPU card is in the "
                    "bus. Take it out and run this again. If it is out, Q itself is shorted to ground: it is position 21 in the slots, "
                    "between TPA and D7, and pin 1 of the bus driver's U2.")
            return
        for n in lines:
            if kind[n] == "U":
                st.warn("%s has no clear level at rest (read %s)" % (n, " ".join(str(x[n]) for x in r)),
                        "Between a pull-up and a pull-down: a short to a line pulled the other way (the last step names it), or a card's input loading a line that has no resistor.")
            elif kind[n] == "L" and self.expected[n] == "H":
                st.fail("%s rests low" % n, "Shorted to ground%s, or a card in the bus holds it low. It is not driven in the next steps." %
                        (" (N0 is GND's neighbour in the slots)" if n == "N0" else ""))
            elif kind[n] == "H" and self.expected[n] == "L":
                st.fail("%s rests high" % n, "Its pull-down is missing (RN3 of the bus Rev D), or it is shorted to +5V or to a line that is pulled up: the next steps say which.")
        if st.status == "PASS": st.info("every line rests where it should")

    def _walk_step(self, st, level, todo, base):
        """drive each line of `todo` alone to `level`; -> ({line: every line's reading}, {line: the lines of `base` that
        went with it, seen twice}, [the lines that would not go])"""
        seen, follow, held = {}, {}, []
        for x in todo:
            a = self.bd.walk(x, level)
            if a[x] != level: held.append(x); continue
            seen[x] = a; f = [y for y in base if y != x and a[y] == level]
            if f: b = self.bd.walk(x, level); f = [y for y in f if b[y] == level]         # twice, before it counts
            if f: follow[x] = f
        return seen, follow, held

    def s_s_low(self, st):
        k, e = self.kind, self.expected
        todo = [n for n in self.lines if not (k[n] == "L" and e[n] == "H")]          # a line held low has nothing more to tell
        self.low, self.follow_low, held = self._walk_step(st, 0, todo, [n for n in self.lines if k[n] == "H"])
        for x in held:
            st.fail("%s will not go low" % x, "Something holds it high against the bus driver, which let go at once: a short to +5V, or a card driving it. " +
                    ("%s and +5V are %s." % (x, self.where(x, "+5V")) if x in ("D0", "-EF1") else "(+5V's neighbours in the slots are D0 and -EF1.)"))
        st.info("%d lines pulled low, one at a time%s" % (len(todo) - len(held), "" if self.follow_low else ": no other line went low with any of them"))
        for x, ys in self.follow_low.items(): st.info("%s low: %s low too" % (x, " ".join(ys)))

    def s_s_high(self, st):
        k, e = self.kind, self.expected
        todo = [n for n in self.lines if e[n] == "L" and k[n] != "H" and n not in S.OPEN_COLLECTOR]
        if not todo:
            self.high, self.follow_high = {}, {}
            st.info("no line rests low on this backplane: none to drive high"); return
        self.high, self.follow_high, held = self._walk_step(st, 1, todo, [n for n in self.lines if k[n] == "L"])
        for x in held:
            st.fail("%s will not go high" % x, "Shorted to ground%s, or a card holds it low; the bus driver let go at once." %
                    (" (N0 is GND's neighbour in the slots)" if x == "N0" else ""))
        st.info("%d pulled-down lines driven high, one at a time%s" % (len(todo) - len(held), "" if self.follow_high else ": no other line went high with any of them"))
        for x, ys in self.follow_high.items(): st.info("%s high: %s high too" % (x, " ".join(ys)))

    def s_s_found(self, st):
        k, e = self.kind, self.expected; edges, oneway = set(), []
        for x, ys in self.follow_low.items():                   # two lines that rest high: each must take the other low
            for y in ys:
                if x in self.follow_low.get(y, ()): edges.add(frozenset((x, y)))
                else: oneway.append("%s low takes %s low, but not the other way round" % (x, y))
        for x, ys in self.follow_high.items():
            for y in ys:
                if e[y] == "H": edges.add(frozenset((x, y)))    # y should rest high, rests low, and rises with x: joined to x's pull-down
                elif x in self.follow_high.get(y, ()): edges.add(frozenset((x, y)))
                else: oneway.append("%s high takes %s high, but not the other way round" % (x, y))
        for x in self.high:                                     # a line with no clear level: does it follow a pulled-down line both ways?
            for y in self.lines:
                if k[y] == "U" and y != x and x in self.low and self.low[x][y] == 0 and self.high[x][y] == 1:
                    if all(self.bd.walk(x, 0)[y] == 0 and self.bd.walk(x, 1)[y] == 1 for _ in range(4)): edges.add(frozenset((x, y)))
        parent = {}
        def find(n):
            parent.setdefault(n, n)
            while parent[n] != n: parent[n] = parent[parent[n]]; n = parent[n]
            return n
        for ed in edges:
            a, b = tuple(ed); parent[find(a)] = find(b)
        groups = {}
        for n in parent: groups.setdefault(find(n), []).append(n)
        self.shorts_found = [sorted(g, key=self.lines.index) for g in groups.values()]
        for g in sorted(self.shorts_found, key=lambda g: self.lines.index(g[0])):
            pairs = [(a, b) for i, a in enumerate(g) for b in g[i + 1:]]
            near = [self.where(a, b) for a, b in pairs if "not neighbours" not in self.where(a, b)]
            st.fail("%s are shorted together" % (" and ".join(g) if len(g) == 2 else ", ".join(g[:-1]) + " and " + g[-1]),
                    "%s: %s." % (" / ".join(g), near[0] if near else self.where(*pairs[0])))
        for o in oneway: st.warn(o, "Not a plain short: a card in the bus joins them through its logic. Run the test on the bare backplane, then with one card at a time.")
        left = [n for n in self.lines if k[n] == "U" and not any(n in g for g in self.shorts_found)]
        for n in left: st.warn("%s has no clear level at rest and follows no other line" % n, "A card's input on a line with no resistor, or a weak short: measure it.")
        if st.status == "PASS": st.info("no two bus lines move together: no short between any of the %d lines" % len(self.lines))
        st.info("not seen by this test: an open joint (bus36 finds a missing pull resistor), a short behind a card's buffers")

    def plan_shorts(self):
        s = self.step
        self.cpu_there = False; self.low, self.high, self.follow_low, self.follow_high, self.shorts_found = {}, {}, {}, {}, []
        s("S1", "bus driver, bus power, nothing else driving the bus", self.s_s_connect)
        if self.steps[-1].status == "FAIL": return
        s("S2", "every line at rest", self.s_s_rest)
        if self.cpu_there: return
        s("S3", "each line pulled low alone", self.s_s_low)
        s("S4", "each pulled-down line driven high alone", self.s_s_high)
        s("S5", "lines that move together", self.s_s_found)

    def plan36(self, name):
        s = self.step
        s("C1", "bus driver, bus power, BUSDRV-C", self.s_c_connect)
        if self.steps[-1].status == "FAIL": return
        if name == "bus36":
            s("X1", "every pulled line at rest", self.s_x_idle)
            s("X2", "open-collector lines: low alone, and back up", self.s_x_lines)
            s("X3", "pull-downs and pull-ups of the driven lines", self.s_x_bus)
            s("X4", "DEBUG header with no cable", self.s_x_debug)
        else:
            s("L1", "DEBUG cable: CLK OUT reaches the 1802", self.s_l_cable)
            if self.steps[-1].status == "FAIL": return
            s("L2", "RESET and LOAD on the bus", self.s_l_modes)
            s("L3", "a program into RAM by DMA IN", self.s_l_load)
            if self.steps[-1].status == "FAIL": self.bd.mode("run"); return
            s("L4", "RUN: the program reads itself back", self.s_l_run)
            s("L5", "-PAUSE holds the 1802", self.s_l_pause)
            s("L6", "a bus reset keeps the loaded program", self.s_l_reset)
            self.bd.mode("run")

    def plan(self, name):
        if name == "shorts": return self.plan_shorts()
        if name in ("bus36", "load"): return self.plan36(name)
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


SIM_CARDS = {"memory": ("mem",), "cf": ("ide",), "video": ("video",), "all": ("mem", "video", "ide"),
             "bus36": (), "load": ("mem",), "shorts": ()}
FAULTS = ("--fault: stuck:CARD:BIT:LEVEL, empty:REF, addr:BIT:LEVEL, card-jumpers:J, short:LINE:LINE (or :GND, :+5V), between:0|1, "
          "oneway:LINE:LINE, nodrive or legacy; with BUSDRV-C also nocable, jp1int, cpu-in, stuck-line:NAME:LEVEL, nopull:NAME, hold-dmain or early-data")


def sim_driver(a):
    """the simulated card and backplane. The older plans run on BUSDRV-B and the 30-pin backplane, or (--busdrv C) on
    BUSDRV-C in a bus Rev D with no CPU card; bus36 and load are BUSDRV-C's own: the bus Rev D empty, and with a memory
    card and CPU Rev D, its DEBUG header cabled to the bus driver's and its JP1 on EXT."""
    from backplane import Backplane, Backplane36
    from fwsim import FwCard
    rev_c = a.plan in ("bus36", "load") or getattr(a, "busdrv", "B") == "C"
    cards = tuple(c for c in (getattr(a, "cards", None) or "").split(",") if c) or SIM_CARDS[a.plan]
    kw = dict(cards=cards, jumpers=a.jumpers, image=a.image, mem_rev=a.mem_rev); fw = {}
    if rev_c: kw["cpu"] = a.plan == "load"
    for f in a.fault or []:
        k, *rest = f.split(":")
        if k == "stuck": kw.setdefault("stuck", {})[rest[0]] = (int(rest[1]), int(rest[2]))
        elif k == "short": kw.setdefault("shorts", []).append(tuple(n if n in ("GND", "+5V") else n.lstrip("-").upper() for n in rest[:2]))
        elif k == "between": kw["between"] = int(rest[0])            # a line between the input thresholds reads this every time
        elif k == "oneway": kw.setdefault("diodes", []).append(tuple(n.lstrip("-").upper() for n in rest[:2]))   # the first low takes the second low
        elif k == "empty": kw.setdefault("empty", []).append(rest[0])
        elif k == "nodrive": kw["drive"] = False
        elif k == "addr": kw["addr"] = (int(rest[0]), int(rest[1]))
        elif k == "card-jumpers": kw["jumpers"] = rest[0].upper()      # the card jumpered unlike --jumpers says
        elif k == "legacy": fw["legacy"] = True
        elif not rev_c: raise SystemExit(FAULTS)
        elif k == "nocable": kw["cable"] = False                       # the DEBUG ribbon left off
        elif k == "jp1int": kw["jp1"] = "INT"                          # the CPU card's clock jumper on its own oscillator
        elif k == "cpu-in": kw["cpu"] = True; kw["cable"] = False      # a CPU card left in the bus, its DEBUG ribbon off
        elif k == "stuck-line": kw.setdefault("stuck_lines", {})[rest[0].lstrip("-")] = int(rest[1])   # e.g. stuck-line:DMAIN:0
        elif k == "nopull": kw.setdefault("nopull", []).append(rest[0].lstrip("-"))                    # e.g. nopull:PAUSE, nopull:D
        elif k in ("hold-dmain", "early-data"): fw["load_fault"] = k     # the firmware doing a LOAD step wrongly
        else: raise SystemExit(FAULTS)
    bp = (Backplane36 if rev_c else Backplane)(**kw)
    if a.rom: bp.load_rom(read_file(a.rom), a.rom_base)
    return S.BusDriver(transport=FwCard(bp, rev="C" if rev_c else "B", **fw)), bp


def hexaddr(s):
    """A bus address is hex, as the help and the reports print it: 8000, 0x8000 and $8000 are all 8000 hex."""
    s = str(s).strip().lower()
    return int(s[1:] if s.startswith("$") else s[2:] if s.startswith("0x") else s, 16)


def main(argv=None):
    ap = argparse.ArgumentParser(description="System-5 card bring-up from the bus driver card", epilog=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan", choices=("memory", "cf", "video", "all", "bus36", "load", "shorts"))
    ap.add_argument("--port"); ap.add_argument("--log", action="store_true", help="show the serial traffic")
    ap.add_argument("--sim", action="store_true", help="the simulated backplane (netlist models) instead of the card")
    ap.add_argument("--busdrv", choices=("B", "C"), default="B", help="--sim: the card that runs memory, cf, video and all "
                    "(C: BUSDRV-C in a bus Rev D with no CPU card); bus36 and load are always BUSDRV-C")
    ap.add_argument("--fault", action="append", help="simulator only: stuck:mem:3:0, empty:IC5, addr:4:0, card-jumpers:RRR-----EEEEEEE-, nodrive, "
                    "short:D0:D1 (or short:N0:GND, short:D0:+5V), between:0 or between:1 (how a line between the input thresholds reads; "
                    "default: either, anew each time), oneway:A3:A4 (A3 low takes A4 low, not the other way round), legacy (old firmware); BUSDRV-C: nocable, jp1int, cpu-in, "
                    "stuck-line:DMAIN:0, nopull:PAUSE, hold-dmain, early-data")
    ap.add_argument("--cards", help="--sim: the cards in the simulated backplane, e.g. mem,video,ide (default: the plan's own; shorts: none)")
    ap.add_argument("--bus", choices=("auto", "d", "2009"), default="auto", help="shorts: the backplane. d = the bus Rev D (pull "
                    "resistors), 2009 = the 2009 board (none); auto tells them apart by the pull-downs on TPA, TPB and N0-N2")
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
