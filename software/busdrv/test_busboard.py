# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-25
"""The bus Rev D backplane's own netlist, with cards and a program on it (busboard.py; Ken, 2026-11-25: "Yes, add the Bus
Rev D test"). The board's wiring is read from hardware/bus/kicad/rev-d/reports/netlist.net; each card's connector goes on
the socket pins it stands on; a pin-level 1802 runs bus_program.asm through the board; each machine cycle is compared
with the instruction-level machine's as it ends, and the lamps, the video RAM, the 6845, the clock, the UART and the
drive are compared with that machine's at the end.

  Slots      the program with the five cards in all eight arrangements round the bus, so that every slot holds every one
             of the five, and with the flag lines' jumpers in all four settings
  Board      the board by itself: what every position of every slot rests at (so every pull resistor); the cards with the
             CPU card out; the supply from each input to every slot; what the netlist joins, against docs/manual/bus.md
  Geometry   the sockets' and the cards' pads on the boards: where busboard.py says a pad stands
  PowerUp    the states the flip-flops and latches come up in: the program runs from all of them, and the IO panel as it
             was drawn until 2026-11-25 is noticed
  Faults     faults planted in a copy of the board's netlist, all of which must be noticed: every position of every slot
             open, every two neighbours in every slot swapped, each slot turned or one along, neighbouring lines shorted
             (all of these by the program, with the flag lines' jumpers tried in all four settings), and every pull
             resistor missing, moved or on the wrong supply; and -INT shorted to -DMAIN, which only the watch on -DMAIN in
             RUN sees (2026-11-27). The one setting Slots has in each arrangement misses 8 of the
             288 opens, one flag line in each slot (J1 -EF3, J2 -EF, J3 -EF1, J4 -EF2, J5 -EF3, J6 -EF, J7 -EF1, J8 -EF2;
             QA, 2026-11-25); the board at rest shows all 8

Every line of the 36 is used by the program; "Lines" says by what. What no test here can see: the bypass and bulk
capacitors' work (C1-C10), the power LED, the regulator, the jack and the diode as parts, a resistor's value, SW1's and
JP1's spare positions (Board.power_path follows how they are joined, no more), the mounting holes, and anything of time,
voltage, current or noise. The pull resistors on lines the CPU card pulls up itself (RN2's eight) or the 1802 always
drives (RN3's, RN4's) change nothing for the program; the idle board shows them. A fault that gives the same circuit
(two resistors of one network exchanged) is none.

The instruction level has no board: machine.py passes bytes from card to card, so it cannot see a wiring fault. Here it
gives the expected result: the same program, the same cycles.

    python3 -m unittest test_busboard          about three minutes
    python3 busboard.py survey [GROUP ...]     the faults counted by what notices them ("short, others": all 595 other pairs)
"""
import os, re, unittest

import busboard as b


def footprint(path, ref):
    """{pad: (x, y)} of one part's pads as its footprint has them (millimetres, the footprint's own axes)"""
    with open(path) as fh: text = fh.read()
    out = {}
    for m in re.finditer(r'^\t\(footprint "', text, re.M):
        end = text.index("\n\t)", m.start()); body = text[m.start():end]
        if not re.search(r'\(property "Reference" "%s"' % re.escape(ref), body): continue
        for p in re.finditer(r'\(pad "(\d+)" \w+ \w+\s*\(at (-?[\d.]+) (-?[\d.]+)', body): out[int(p.group(1))] = (float(p.group(2)), float(p.group(3)))
        return out
    raise ValueError("%s: no %s" % (path, ref))


class Geometry(unittest.TestCase):
    """busboard.CARDS says which position each connector pad stands on. Pad for pad, 2.54 mm apart in one row, from the
    GND end; which end that is, the pads' own nets say (position 1 GND, position 30 +5V on the board and on every card)"""
    def row(self, pads, where):
        at = {where(n): xy for n, xy in pads.items()}
        x1, y1 = at[min(at)]; dx, dy = at[min(at) + 1][0] - x1, at[min(at) + 1][1] - y1
        self.assertAlmostEqual((dx * dx + dy * dy) ** 0.5, 2.54, 2)
        for k, pos in enumerate(sorted(at)):
            self.assertAlmostEqual(at[pos][0], x1 + k * dx, 2); self.assertAlmostEqual(at[pos][1], y1 + k * dy, 2)
        return sorted(at)

    def test_the_sockets(self):
        board = os.path.join(b.ROOT, "hardware/bus/kicad/rev-d/s5bus-d.kicad_pcb"); bus = b.bus_netlist()
        for j in b.SLOTS:
            self.assertEqual(self.row(footprint(board, j), lambda n: n), list(range(1, 37)))
            self.assertEqual((bus.net(j, 1), bus.net(j, 30)), ("GND", "+5V"))

    def test_the_cards(self):
        for name, (folder, ref, where) in b.CARDS.items():
            d = os.path.join(b.ROOT, folder); boards = [f for f in os.listdir(d) if f.endswith(".kicad_pcb")]
            self.assertEqual(len(boards), 1, d)
            pos = self.row(footprint(os.path.join(d, boards[0]), ref), where)
            self.assertIn(len(pos), (30, 36)); self.assertEqual(pos, list(range(1, len(pos) + 1)), name)
            nl = b.card_netlist(name); at = {where(int(p)): nl.net(r, p) for r, p in nl.pins if r == ref}
            self.assertEqual((at[1], at[30] in ("VCC", "+5V")), ("GND", True), name)


class Board(unittest.TestCase):
    def test_the_board_at_rest(self): b.idle(b.bus_netlist())

    def test_the_cards_at_rest_with_the_cpu_card_out(self):
        for k in range(8):
            a = b.arrangement(k); del a["cpu"]; b.idle_cards(b.bus_netlist(), a)

    def test_the_supply(self):
        self.assertEqual(b.power_path(b.bus_netlist(), "REG"), ["/VIN", "/VIN_D", "/5V_REG", "/5V_SEL", "+5V"])
        self.assertEqual(b.power_path(b.bus_netlist(), "EXT"), ["/5V_EXT", "/5V_SEL", "+5V"])

    def test_what_is_joined(self):
        """every position is one net through all eight slots, no two positions are one, and every net of the board is
        accounted for: a slot's line or a step of the supply; nothing else hangs on a slot's line"""
        bus = b.bus_netlist(); nets = bus.nets; lines = {}
        for pos, line in enumerate(b.LINES, 1):
            got = {bus.net(j, pos) for j in b.SLOTS}; self.assertEqual(len(got), 1, line)
            lines[got.pop()] = line
        self.assertEqual(sorted(lines.values()), sorted(b.LINES))
        for net, line in lines.items(): self.assertEqual(net.split("/")[-1], line)
        others = {n for n in nets if n not in lines and not n.startswith("unconnected")}
        self.assertEqual(others, {"/VIN", "/VIN_D", "/5V_REG", "/5V_SEL", "/5V_EXT", "/LED_PWR"})
        self.assertEqual([k for n in nets if n.startswith("unconnected") for k in nets[n]], [("SW1", "1")])
        for net, line in lines.items():
            if line in ("+5V", "GND"): continue
            on = sorted(r for r, _ in nets[net] if r not in b.SLOTS)
            self.assertEqual(len(on), 0 if line in b.NO_IDLE else 1, (line, on))          # its one pull resistor
            self.assertTrue(all(r.startswith("RN") for r in on))


class Slots(unittest.TestCase):
    def test_every_card_in_every_slot(self):
        seen = set()
        for k in range(8):
            a = b.arrangement(k); flags = "ABCD"[k % 4]
            with self.subTest(slots=a, flags=flags):
                r = b.Run(b.bus_netlist(), a, flags).all()
                self.assertGreater(r.cycles, 2000); seen |= set(a.items())
        self.assertEqual(len(seen), 5 * 8)

    def test_the_program_uses_every_line(self):
        """the five cards' connectors together take all 36 positions, the CPU card and the IO panel each of them"""
        self.assertEqual(b.used("cpu"), list(range(1, 37))); self.assertEqual(b.used("panel"), list(range(1, 37)))

    def test_the_expected_cycles_are_what_they_should_be(self):
        """the instruction-level machine's result is not empty: each kind of cycle, each port, the interrupt, the loads"""
        r = b.expected(); run = r["run"]; kinds = {c[0] for c in run}
        self.assertEqual(kinds, {"fetch", "read", "write", "inp"})
        self.assertEqual({c[3] for c in run if c[0] == "read"} - {0}, {2, 3, 4, 6, 7}); self.assertEqual({c[3] for c in run if c[0] == "inp"}, {1, 3, 4, 7})
        self.assertEqual(r["load"], [("dma", i, v, 0) for i, v in enumerate(b.RAM_PROGRAM)])
        self.assertNotIn(0xEE, [c[2] for c in run if c[3] == 4]); self.assertNotIn(0xEF, [c[2] for c in run if c[3] == 4])
        self.assertEqual([c[2] for c in run if c[0] == "inp" and c[1] == 0x6FF0][1:2], [b.TOGGLES])
        self.assertTrue(any(c[0] == "inp" and c[2] == b.UART_IN[0] for c in run))
        self.assertEqual(r["tx"], b"S"); self.assertEqual(r["boot"][0][:2], ("fetch", 0)); self.assertEqual(r["boot"][3][1], 0xF003)


class PowerUp(unittest.TestCase):
    """the states flip-flops and latches come up in (2026-11-25: the IO panel as drawn until then could not start from
    every one; Ken: "fix both power-up faults in one new route"). Nothing is pressed before the program"""
    REQ, ACK, DRIVE = ("panel.U10", 0), ("panel.U10", 1), ("panel.U11", 0)
    STATES = {"every one 0": 0, "every one 1": 1, "REQ alone 1": {REQ: 1, DRIVE: 0, ACK: 0}, "DRIVE alone 1": {REQ: 0, DRIVE: 1, ACK: 0},
              "REQ and DRIVE 1": {REQ: 1, DRIVE: 1, ACK: 0}, "unknown": None}

    def setUp(self): b._NL.clear(); b._MEMO.clear(); self.addCleanup(self._restore)
    def _restore(self): b.REWORK.clear(); b._NL.clear(); b._MEMO.clear()

    def test_the_program_runs_from_every_state(self):
        for what, state in self.STATES.items():
            with self.subTest(what): self.assertGreater(b.Run().all(state).cycles, 2000)

    def test_the_panel_as_drawn_does_not(self):
        """the same on the card as it was drawn: each of the states that must fail does, the others run"""
        b.REWORK.update(b.AS_DRAWN); said = {}
        for what, state in self.STATES.items():
            try: b.Run().all(state); said[what] = None
            except b.Noticed as e: said[what] = str(e)
        self.assertIsNone(said["every one 0"])
        for what in ("every one 1", "REQ alone 1", "DRIVE alone 1", "REQ and DRIVE 1"): self.assertIn("disagree on bus./D", said[what] or "", what)

    def load(self, r, s, byte):
        """one INPUT press in LOAD mode -> the DMA cycles it made"""
        n = len(s.pins.cycles); s.toggles(byte); s.settle(); s.press("SW10", "SW11", "SW9"); r.spin(64); s.press("SW10", "SW11"); r.spin(32)
        return [c for c in s.pins.cycles[n:] if c[0] == "dma"]

    def test_power_up_with_load_on(self):
        """what the manual says: power up with LOAD off. With LOAD on, INPUT loads nothing or the toggles' byte is
        written by itself if REQ came up as 1 (CPU Rev D's DMA_ARMED: ("cpu.U8", its half)); LOAD off and on mends it"""
        seen = set()
        for req in (0, 1):
            for drive in (0, 1):
                for armed in (0, 1):
                    r = b.Run(); s = r.s; s._put_pins(); s.press("SW10", "SW11")
                    m8 = next(m for m in s.models if m.ref == "cpu.U8"); half = next(i for i, f in enumerate(m8.ff) if f[3].endswith("ARM_L"))
                    for _ in range(2):
                        for m in s.models:
                            if m.ref == "panel.U10": m.state = {0: req, 1: 0}
                            elif m.ref == "panel.U11": m.state[0] = drive
                            elif m is m8: m.state[half] = armed
                            else: continue
                            s.kick(m)
                        s.settle()
                    n = len(s.pins.cycles); r.spin(16 * 20); itself = [c for c in s.pins.cycles[n:] if c[0] == "dma"]
                    seen.add((req, armed, bool(itself), len(self.load(r, s, 0x3C)) == 1 and not itself))
                    s.press("SW10"); r.spin(8); s.press("SW10", "SW11"); r.spin(40)
                    self.assertEqual([c[2] for c in self.load(r, s, 0x5B)], [0x5B], (req, drive, armed))
        self.assertEqual({(q, a, i) for q, a, i, _ in seen}, {(0, 0, False), (0, 1, False), (1, 0, False), (1, 1, True)})
        self.assertEqual({(q, a) for q, a, _, ok in seen if not ok}, {(1, 0), (1, 1)})

    def test_a_request_pending_as_load_goes_off(self):
        r = b.Run(); s = r.s; s.power_on(0); r.play("run"); s.press("SW10"); s.press("SW10", "SW11"); r.spin(40)
        net = lambda n: next(v for k, v in s.val.items() if k.split("/")[-1] == n)
        s.press("SW10", "SW11", "SW9"); self.assertEqual((net("REQ"), net("-DMAIN")), (1, 0))      # the clock stopped here
        s.press("SW10", "SW11"); self.assertEqual(net("REQ"), 1)
        s.press("SW10"); self.assertEqual((net("REQ"), net("-DMAIN")), (0, 1))                     # LOAD off


class Faults(unittest.TestCase):
    """each group's count is asserted, so a fault that could not be planted does not pass as noticed"""
    def program(self, group, n):
        fs = b.all_faults()[group]; self.assertEqual(len(fs), n); quiet = []
        for f in fs:
            if "program" not in {w for w, _ in b.notice(f)}: quiet.append(f)
        self.assertEqual(quiet, [])

    def test_every_position_of_every_slot_open(self): self.program("open", 288)
    def test_neighbours_in_a_slot_swapped(self): self.program("swap", 280)
    def test_a_slot_turned_or_one_along(self): self.program("slot", 16)
    def test_neighbouring_lines_shorted(self): self.program("short", 35)

    def test_a_short_no_card_feels(self):
        """-INT to -DMAIN, the one pair of the 595 other shorts nothing noticed until 2026-11-27 (busboard.py survey): -DMAIN
        is low only in a boot reset and in LOAD mode, when the 1802 takes no interrupt, and CPU Rev D takes -DMAIN only when
        paused, so the UART's interrupt in RUN pulled -DMAIN low with no card to feel it. The program now watches -DMAIN in
        RUN, as a logic probe or the bus driver would, and the interrupt shows it"""
        w = dict(b.notice(("short", "/-INT", "/-DMAIN")))
        self.assertIn("-DMAIN is 0 in RUN (-INT 0)", w.get("program", ""))

    def test_the_pull_resistors(self):
        for group, n in (("resistor open", 28), ("resistor moved", 24), ("resistor common", 4)):
            fs = b.all_faults()[group]; self.assertEqual(len(fs), n); quiet = []
            for f in fs:
                try: b.idle(b.fault(*f)); quiet.append(f)
                except b.Noticed: pass
            self.assertEqual(quiet, [], group)

    def test_a_copper_fault_under_one_card_only(self):
        """an open position is noticed with any card in the slot that uses it, not the CPU card alone. The memory card's
        twenty-two here; the other three cards' (81) were run once, on 2026-11-25, all noticed (three and a half minutes)"""
        self.assertEqual(len(b.used("mem")), 22)
        for pos in b.used("mem"): self.assertTrue(b.open_under("mem", pos), b.LINES[pos - 1])

    def test_the_supply_broken(self):
        for f in (("open", "D2", "1"), ("open", "U1", "3"), ("open", "JP1", "2"), ("open", "SW1", "3"), ("swap", "D2", "1", "2"),
                  ("swap", "JP1", "1", "2"), ("swap", "J10", "1", "2"), ("swap", "U1", "1", "3"), ("open", "J9", "2"), ("open", "C4", "2"),
                  ("short", "/5V_REG", "/5V_EXT"), ("short", "+5V", "/5V_SEL"), ("short", "+5V", "GND")):
            with self.assertRaises(b.Noticed, msg=str(f)):
                for src in ("REG", "EXT"): b.power_path(b.fault(*f), src)


if __name__ == "__main__":
    unittest.main()
