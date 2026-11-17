# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-01
"""GBASIC in the emulator (System-5 with VIDEO-G, HBIOS for VIDEO-G, ELF/OS 0.2.6 from a disk image).

    python3 software/gbasic/tests/test_gbasic.py          (about 10 minutes; -k NAME for one test)

Each test starts from a snapshot taken after the first boot (ELF/OS, then GBASIC).  Graphics are compared pixel
for pixel with Python models of the same integer algorithms; the timings are the emulated 1802's (1.76 MHz,
8 clocks a machine cycle), printed at the end.
"""
import os, sys, unittest
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import harness
from harness import GBasic, lines_of

SCREENS = os.path.join(HERE, "screens")
TIMES = []


def setUpModule():
    if harness.mkelfos.missing():       # GBASIC runs under ELF/OS 0.2.6: Mike Riley's, in the private-resources repository
        raise unittest.SkipTest("ELF/OS 0.2.6 is in the private-resources repository, not here (tools/mkelfos.py)")


def run(g, src, limit=400_000_000):
    return lines_of(g.run_prog(src, limit))


def unwrap(lines):
    """join the lines GBASIC wrapped at the 64th column (a full 64 characters, then a line not starting a new one)"""
    out = []
    for l in lines:
        if out and len(out[-1]) % 64 == 0 and not l[:1].isdigit(): out[-1] += l
        else: out.append(l)
    return out


def page_pixels(g, page=None, h=200):
    v = g.video; p = v.pages[v.cpage() if page is None else page]; out = set()
    for y in range(h):
        row = p[y * 64:y * 64 + 64]
        for b in range(64):
            if row[b]:
                for k in range(8):
                    if row[b] & (0x80 >> k): out.add((b * 8 + k, y))
    return out


# ------------------------------------------------------------------ reference models (the same integer arithmetic)
def clip(points, h=200):
    return {(x, y) for x, y in points if 0 <= x < 512 and 0 <= y < h}


def ref_line(x0, y0, x1, y1, h=200):
    pts = []
    if y0 == y1:
        pts = [(x, y0) for x in range(min(x0, x1), max(x0, x1) + 1)]
    elif x0 == x1:
        pts = [(x0, y) for y in range(min(y0, y1), max(y0, y1) + 1)]
    elif abs(x1 - x0) >= abs(y1 - y0):
        if x1 < x0: x0, y0, x1, y1 = x1, y1, x0, y0
        dx, dy, sy = x1 - x0, abs(y1 - y0), (1 if y1 > y0 else -1)
        err, x, y = dx >> 1, x0, y0
        for _ in range(dx + 1):
            pts.append((x, y)); x += 1; err -= dy
            if err < 0: err += dx; y += sy
    else:
        if y1 < y0: x0, y0, x1, y1 = x1, y1, x0, y0
        dy, dx, sx = y1 - y0, abs(x1 - x0), (1 if x1 > x0 else -1)
        err, x, y = dy >> 1, x0, y0
        for _ in range(dy + 1):
            pts.append((x, y)); y += 1; err -= dx
            if err < 0: err += dy; x += sx
    return clip(pts, h)


def ref_box(x1, y1, x2, y2, fill, h=200):
    x1, x2 = sorted((x1, x2)); y1, y2 = sorted((y1, y2))
    if fill: return clip({(x, y) for x in range(x1, x2 + 1) for y in range(y1, y2 + 1)}, h)
    pts = {(x, y) for x in range(x1, x2 + 1) for y in (y1, y2)}
    pts |= {(x, y) for x in (x1, x2) for y in range(y1 + 1, y2)}
    return clip(pts, h)


def ref_ellipse(cx, cy, rx, ry, fill, h=200):
    if rx == 0 or ry == 0: return ref_line(cx - rx, cy - ry, cx + rx, cy + ry, h)
    A, B = rx * rx + rx, ry * ry + ry
    err, Ay, Bx = A * ry - 1, 2 * A * ry - A, B
    w, wp, pts = 0, -1, set()
    for y in range(ry, -1, -1):
        if y != ry: err += Ay; Ay -= 2 * A
        while err >= Bx: err -= Bx; Bx += 2 * B; w += 1
        a = 0 if fill else min(wp + 1, w)
        spans = [(-w, w)] if a == 0 else [(-w, -a), (a, w)]
        for l, r in spans:
            for row in ({cy - y, cy + y}):
                pts |= {(cx + x, row) for x in range(l, r + 1)}
        wp = w
    return clip(pts, h)


class Language(unittest.TestCase):
    def setUp(self): self.g = GBasic()

    def p(self, expr):
        return lines_of(self.g.cmd("PRINT " + expr))

    def test_arithmetic_and_precedence(self):
        cases = {"2+3*4": 14, "(2+3)*4": 20, "-7/2": -3, "7/-2": -3, "-7 MOD 3": -1, "7 MOD -3": 1,
                 "100*400": -25536, "32767+1": -32768, "-32768/-1": -32768, "2-3-4": -5, "64/4/2": 8,
                 "-2*-3": 6, "--5": 5, "1+2=3": -1, "3<>3": 0, "1<2 AND 2<3": -1, "NOT 1=1": 0, "NOT 0": -1,
                 "5 XOR 3": 6, "12 OR 3": 15, "12 AND 10": 8, "2<3=-1": -1, "3>=3": -1, "3<=2": 0, "&HFFFF": -1,
                 "&H7FFF+1": -32768, "65535": -1, "ABS(-32767)": 32767, "SGN(-9)": -1, "SGN(0)": 0, "SGN(44)": 1}
        for e, v in cases.items():
            self.assertEqual(self.p(e), [str(v)], e)

    def test_division_by_zero(self):
        self.assertIn("?Division by zero", self.g.cmd("PRINT 1/0"))
        self.assertIn("?Division by zero", self.g.cmd("PRINT 5 MOD 0"))

    def test_variables(self):
        g = self.g
        g.cmd("A=1: B9=2: XY=3: Z=A+B9+XY")
        self.assertEqual(self.p("A;B9;XY;Z"), ["1236"])
        self.assertEqual(self.p("Q"), ["0"])              # never set
        g.cmd("FORI=1TO3:S=S+I:NEXT")                       # FOR I = 1 TO 3 without spaces
        self.assertEqual(self.p("S"), ["6"])
        self.assertIn("?Syntax error", g.cmd("ABC=1"))     # names are one or two characters

    def test_arrays(self):
        g = self.g
        out = run(g, """
            10 DIM A(10), M(3,4)
            20 FOR I=0 TO 10: A(I)=I*I: NEXT
            30 FOR I=0 TO 3: FOR J=0 TO 4: M(I,J)=I*10+J: NEXT J,I
            40 PRINT A(10); " "; M(3,4); " "; M(2,1); " "; A(3)+M(1,1)
            50 B(5)=7: PRINT B(5); B(10)
            """)
        self.assertEqual(out, ["100 34 21 20", "70"])
        self.assertIn("?Bad subscript in 20", g.cmd("20 PRINT A(11)\nRUN"))
        self.assertIn("?Already DIMed in 10", g.cmd("10 DIM A(5): DIM A(5)\nRUN"))
        self.assertIn("?Bad subscript", g.cmd("PRINT B(11)"))   # auto-DIM 10 on first use

    def test_for_next(self):
        out = run(self.g, """
            10 FOR I=1 TO 3: PRINT I;: NEXT: PRINT
            20 FOR I=10 TO 1 STEP -4: PRINT I;" ";: NEXT I: PRINT
            30 FOR I=5 TO 1: PRINT "ONCE";: NEXT: PRINT
            40 FOR I=32760 TO 32767 STEP 5: PRINT I;" ";: NEXT: PRINT
            50 FOR I=1 TO 2: FOR J=1 TO 2: PRINT I;J;" ";: NEXT J,I: PRINT
            60 FOR K=1 TO 3: FOR L=1 TO 100: IF L=2 THEN 80
            70 NEXT L
            80 NEXT K: PRINT K;L
            """)
        self.assertEqual(out, ["123", "10 6 2 ", "ONCE", "32760 32765 ", "11 12 21 22 ", "42"])
        self.assertIn("?NEXT without FOR", self.g.cmd("NEXT"))

    def test_gosub_on_if(self):
        out = run(self.g, """
            10 FOR N=1 TO 4: ON N GOSUB 100,200,300: NEXT
            20 ON 2 GOTO 30,40
            30 PRINT "NOT HERE"
            40 IF 1 THEN PRINT "T1" ELSE PRINT "E1"
            50 IF 0 THEN PRINT "T2" ELSE PRINT "E2"
            60 IF 5>3 THEN 80
            70 PRINT "SKIPPED"
            80 IF 0 THEN 70 ELSE 90
            90 GOSUB 400: PRINT "BACK": END
            100 PRINT "A";: RETURN
            200 PRINT "B";: RETURN
            300 PRINT "C": RETURN
            400 FOR I=1 TO 3: IF I=2 THEN RETURN
            410 NEXT
            """)
        self.assertEqual(out, ["ABC", "T1", "E2", "BACK"])
        self.assertIn("?RETURN without GOSUB", self.g.cmd("RETURN"))
        self.assertIn("?Undefined line in 10", self.g.cmd("NEW\n10 GOTO 99\nRUN"))

    def test_data_read_restore(self):
        out = run(self.g, """
            10 DATA 1,-2,&H10
            20 DATA 3*3: REM expressions work too
            30 FOR I=1 TO 4: READ X: PRINT X;" ";: NEXT: PRINT
            40 RESTORE 20: READ Y: PRINT Y
            50 RESTORE: READ Z: PRINT Z
            60 READ A,B,C,D
            """)
        self.assertEqual(out[:3], ["1 -2 16 9 ", "9", "1"])
        self.assertIn("?Out of DATA in 60", out[3])

    def test_print_formatting(self):
        g = self.g
        self.assertEqual(self.p('"A";1;"B"'), ["A1B"])
        out = g.cmd('PRINT 1,2,3')
        self.assertIn("1               2               3", out)
        self.assertEqual(self.p('"X";TAB(5);"Y";SPC(3);"Z";CHR$(33)'), ["X    Y   Z!"])
        self.assertIn("NO NEWLINE?", g.cmd('PRINT "NO NEWLINE";: PRINT "?"').replace("\n", ""))
        self.assertEqual(self.p('5 \' a comment'), ["5"])
        out = g.cmd('FOR I=1 TO 70: PRINT "*";: NEXT')    # GBASIC wraps at 64 columns itself
        self.assertIn("*" * 64 + "\n" + "*" * 6, out)

    def test_input(self):
        g = self.g
        g.program('10 INPUT "TWO";A,B\n20 INPUT C\n30 PRINT A+B+C')
        g.type_text("RUN\n"); g.run_until_waiting()
        g.type_text("5\n"); g.run_until_waiting()           # one value: asks for the rest
        g.type_text("&H10\n"); g.run_until_waiting()
        g.type_text("x\n"); g.run_until_waiting()           # not a number: redo
        g.type_text("-1\n"); g.run_until_waiting()
        out = g.text()
        self.assertIn("TWO? 5", out); self.assertIn("?? &H10", out); self.assertIn("?Redo from start", out)
        self.assertTrue(out.rstrip().endswith("20\nReady"), out[-60:])

    def test_edit_list_renum_delete(self):
        g = self.g
        for l in ("30 PRINT 3", "10 PRINT 1", "20 PRINT 2", "20 PRINT 22", "40 GOTO 10", "25 GOSUB 30", "35 REM x"):
            g.cmd(l)
        g.cmd("35")                                        # delete a line by its number
        self.assertEqual(lines_of(g.cmd("LIST")), ["10 PRINT 1", "20 PRINT 22", "25 GOSUB 30", "30 PRINT 3", "40 GOTO 10"])
        self.assertEqual(lines_of(g.cmd("LIST 20-30")), ["20 PRINT 22", "25 GOSUB 30", "30 PRINT 3"])
        self.assertEqual(lines_of(g.cmd("LIST -20")), ["10 PRINT 1", "20 PRINT 22"])
        g.cmd("RENUM 100,5")
        self.assertEqual(lines_of(g.cmd("LIST")), ["100 PRINT 1", "105 PRINT 22", "110 GOSUB 115", "115 PRINT 3",
                                                   "120 GOTO 100"])
        g.cmd("DELETE 105-110")
        self.assertEqual(lines_of(g.cmd("LIST")), ["100 PRINT 1", "115 PRINT 3", "120 GOTO 100"])
        g.cmd("NEW")
        self.assertEqual(lines_of(g.cmd("LIST")), [])

    def test_list_spacing_round_trip(self):
        g = self.g
        g.cmd('10 fori=1to10step2:ifi>5thenprint"big";i else printi;:next')
        g.cmd("20 x=-&h7000:poke &h6000,peek(x)and255:?abs(x)mod7")
        listing = unwrap(lines_of(g.cmd("LIST")))         # (the screen is 64 columns: long lines wrap)
        self.assertEqual(listing, ['10 FOR I=1 TO 10 STEP 2:IF I>5 THEN PRINT "big";I ELSE PRINT I;:NEXT',
                                   "20 X=-&H7000:POKE &H6000,PEEK(X) AND 255:PRINT ABS(X) MOD 7"])
        g.cmd("NEW")
        for l in listing: g.cmd(l)                         # typing the listing back gives the same listing
        self.assertEqual(unwrap(lines_of(g.cmd("LIST"))), listing)

    def test_stop_cont_break(self):
        g = self.g
        out = run(g, '10 PRINT "A": STOP\n20 PRINT "B"')
        self.assertEqual(out, ["A", "Break in 10"])
        self.assertEqual(lines_of(g.cmd("CONT")), ["B"])
        self.assertIn("?Can't continue", g.cmd("CONT"))
        g.program("10 N=N+1: GOTO 10")
        g.type_text("RUN\n"); g.run_until_waiting(300_000)
        g.type_text("\x03")                                 # Ctrl-C
        self.assertTrue(g.run_until_waiting(1_000_000))
        self.assertIn("Break in 10", g.text())
        n = int(lines_of(g.cmd("PRINT N"))[0]); self.assertGreater(n, 10)
        g.type_text("CONT\n"); g.run_until_waiting(300_000); g.type_text("\x1b")   # Esc works too
        self.assertTrue(g.run_until_waiting(1_000_000))
        self.assertGreater(int(lines_of(g.cmd("PRINT N"))[0]), n)

    def test_errors_have_line_numbers(self):
        g = self.g
        self.assertIn("?Syntax error in 20", g.cmd("NEW\n10 A=1\n20 PRINT 1+\nRUN"))
        self.assertIn("?Syntax error", g.cmd("PRINT 2+"))
        self.assertIn("?Overflow", g.cmd("PRINT 65536"))
        self.assertIn("?Illegal value", g.cmd("OUT 9,1"))

    def test_peek_poke_usr_call_rnd_fre(self):
        g = self.g
        g.cmd("POKE &H6000,123")
        self.assertEqual(self.p("PEEK(&H6000)"), ["123"])
        # USR: machine code at 6000: RF = RF * 2 (GHI/GLO shifts), SEP R5
        code = [0x8F, 0xFE, 0xAF, 0x9F, 0x7E, 0xBF, 0xD5]
        for i, b in enumerate(code): g.cmd("POKE %d,%d" % (0x6000 + i, b))
        self.assertEqual(self.p("USR(&H6000,1234)"), ["2468"])
        # CALL: machine code that pokes 42 into 6100: LDI 61 PHI RF LDI 00 PLO RF LDI 2A STR RF SEP R5
        code = [0xF8, 0x61, 0xBF, 0xF8, 0x00, 0xAF, 0xF8, 0x2A, 0x5F, 0xD5]
        for i, b in enumerate(code): g.cmd("POKE %d,%d" % (0x6050 + i, b))
        g.cmd("CALL &H6050")
        self.assertEqual(self.p("PEEK(&H6100)"), ["42"])
        out = run(g, "10 RANDOMIZE 7: FOR I=1 TO 200: R=RND(6): IF R<0 OR R>5 THEN PRINT \"BAD\"\n"
                     "20 C(R)=C(R)+1: NEXT: FOR I=0 TO 5: IF C(I)=0 THEN PRINT \"MISSING\"\n30 NEXT: PRINT \"OK\"")
        self.assertEqual(out, ["OK"])
        a = run(g, "10 RANDOMIZE 99: PRINT RND(1000);RND(1000)")
        b = run(g, "10 RANDOMIZE 99: PRINT RND(1000);RND(1000)")
        self.assertEqual(a, b)
        free = int(self.p("FRE(0)")[0]); self.assertGreater(free, 6000)

    def test_vg_registers_by_peek_and_poke(self):
        """VIDEO-G is memory-mapped (2026-11-17): the status at 7804, the Y register at 7806; INP and OUT still reach
        the ports, but VIDEO-G answers none"""
        st = int(self.p("PEEK(&H7804)")[0])
        self.assertEqual(st & 0xE0, 0xA0)                  # VIDEO-G with GFX, NTSC
        self.g.cmd("POKE &H7806,123")
        self.assertEqual(self.g.video.yreg, 123)
        self.assertEqual(int(self.p("INP(4)")[0]), 255)    # no port answers: the bus floats

    def test_locate_and_cls(self):
        g = self.g
        g.program('10 CLS: LOCATE 3,10: PRINT "HELLO";: PRINT "!": LOCATE 24,63: PRINT "Z": INPUT A')
        g.type_text("RUN\n"); g.run_until_waiting()       # waiting in INPUT: nothing has scrolled
        screen = g.video.lines()
        self.assertEqual(screen[3][10:16], "HELLO!")
        self.assertEqual(screen[24][63], "Z")
        self.assertEqual("".join(screen[:3] + screen[4:23]).strip(), "")
        g.cmd("1")

    def test_inkey_special_keys(self):
        g = self.g
        g.program("10 K=INKEY: IF K=0 THEN 10\n20 PRINT K")
        g.type_text("RUN\n"); g.run_until_waiting(200_000)
        g.m.kbd.queue.append(0x91)                          # Up
        g.run_until_waiting()
        self.assertIn("145", g.text())
        g.m.kbd.queue.extend([0x80, 0xC1])                   # F1 and Shift+Up while typing: ignored
        self.assertEqual(lines_of(g.cmd("PRINT 7")), ["7"])


class ReadmeExamples(unittest.TestCase):
    """the example programs in README.md run as described"""
    def test_text_examples(self):
        g = GBasic()
        out = run(g, """
            10 REM times table
            20 FOR I=1 TO 9: FOR J=1 TO 9
            30 PRINT TAB(J*6);I*J;
            40 NEXT J: PRINT: NEXT I
            """)
        self.assertEqual(len(out), 9)
        self.assertEqual(out[8].split(), ["9", "18", "27", "36", "45", "54", "63", "72", "81"])
        self.assertEqual(out[0].index("1"), 6)
        g.program("""
            10 INPUT "HOW MANY";N: IF N<1 THEN 10
            20 S=0: FOR I=1 TO N: READ X: S=S+X: NEXT
            30 PRINT "SUM";S;" MEAN";S/N
            40 DATA 4,8,15,16,23,42
            """)
        g.type_text("RUN\n"); g.run_until_waiting(); out = g.cmd("6")
        self.assertIn("SUM108 MEAN18", out)
        g.program("""
            10 ON RND(3)+1 GOSUB 100,200,300: GOTO 10
            100 PRINT "ROCK": RETURN
            200 PRINT "PAPER": RETURN
            300 PRINT "SCISSORS": RETURN
            """)
        start = len(g.out); g.type_text("RUN\n"); g.run_until_waiting(400_000); g.type_text("\x03")
        g.run_until_waiting()
        words = set(g.text(start).split())
        self.assertTrue({"ROCK", "PAPER", "SCISSORS"} <= words, words)
        self.assertIn("Break in", g.text(start))
        out = run(g, """
            10 FOR I=0 TO 6: READ B: POKE &H6800+I,B: NEXT
            20 PRINT USR(&H6800,1234)
            30 DATA &H8F,&HFE,&HAF,&H9F,&H7E,&HBF,&HD5: REM GLO RF SHL PLO RF GHI RF SHLC PHI RF SEP R5
            """)
        self.assertEqual(out, ["2468"])

    def test_graphics_examples(self):
        g = GBasic()
        run(g, """
            10 ERASE: GRAPHICS ON
            20 FOR R=10 TO 90 STEP 10: CIRCLE 128,100,R: NEXT
            30 FOR X=256 TO 511 STEP 16: LINE 256,199,X,0: NEXT
            40 BOX 300,120,500,190,F: PEN 2: CIRCLE 400,155,30,F: PEN 1
            """)
        self.assertGreater(g.video.count_pixels(), 15000)
        g.program("""
            10 REM a ball: PEN 2 draws it, and drawing it again in the same place removes it (a key stops it)
            20 ERASE: GRAPHICS ON: PEN 2: X=20: Y=20: DX=3: DY=2
            30 CIRCLE X,Y,8,F
            40 WAIT 1: CIRCLE X,Y,8,F
            50 X=X+DX: Y=Y+DY: IF X<8 OR X>503 THEN DX=-DX
            60 IF Y<8 OR Y>191 THEN DY=-DY
            70 IF INKEY=0 THEN 30
            80 PEN 1: GRAPHICS OFF
            """)
        g.type_text("RUN\n"); g.run_until_waiting(2_000_000); g.type_text("Q"); self.assertTrue(g.run_until_waiting())
        x, y = map(int, lines_of(g.cmd('PRINT X;" ";Y'))[0].split())
        self.assertGreater(x, 20); self.assertEqual(g.video.count_pixels(), 0); self.assertFalse(g.video.gfx_on())
        run(g, """
            10 REM drawing on page 1 while page 0 shows, then showing it
            20 GRAPHICS ON: PAGE 0,1: ERASE
            30 FOR I=0 TO 199 STEP 4: LINE 0,I,511,199-I: NEXT
            40 PAGE 1
            """)
        self.assertEqual(g.video.dpage(), 1); self.assertGreater(g.video.count_pixels(page=1), 20000)


class Files(unittest.TestCase):
    def test_save_load_round_trip_and_type(self):
        g = GBasic()
        prog = ['10 REM saved by GBASIC', '20 FOR I=1 TO 3:PRINT "LINE";I:NEXT', '30 DIM A(5):A(2)=&H7000:PRINT A(2)',
                '40 IF 1 THEN PRINT "X" ELSE PRINT "Y"']
        g.cmd("NEW")
        for l in prog: g.cmd(l)
        self.assertEqual(lines_of(g.cmd('SAVE "RT.BAS"')), [])
        self.assertIn("RT.BAS", g.cmd("FILES"))
        g.cmd("NEW")
        self.assertEqual(lines_of(g.cmd('LOAD "RT.BAS"')), [])
        self.assertEqual(lines_of(g.cmd("LIST")), prog)
        self.assertEqual(lines_of(g.cmd("RUN")), ["LINE1", "LINE2", "LINE3", "28672", "X"])
        self.assertIn("?File not found", g.cmd('LOAD "NOPE"'))
        self.assertEqual(lines_of(g.cmd("LIST")), prog)     # a failed LOAD keeps the program
        # back in ELF/OS, the file is plain text
        g.type_text("BYE\n"); g.run_until_text("$ ", 5_000_000)
        start = len(g.out)
        g.type_text("TYPE RT.BAS\n"); g.run_until_text("Ready\n$ ", 30_000_000, start)
        typed = g.text(start)
        for l in prog: self.assertIn(l, typed)
        # and GBASIC RT.BAS loads and runs it
        start = len(g.out)
        g.type_text("GBASIC RT.BAS\n")
        self.assertTrue(g.run_until_waiting(80_000_000))
        self.assertIn("LINE3\n28672\nX", g.text(start))

    def test_kill(self):
        g = GBasic()
        g.cmd('10 PRINT 1\nSAVE "GONE"')
        self.assertIn("GONE", g.cmd("FILES"))
        g.cmd('KILL "GONE"')
        self.assertNotIn("GONE", g.cmd("FILES"))
        self.assertIn("?File not found", g.cmd('KILL "GONE"'))


class Graphics(unittest.TestCase):
    def setUp(self):
        self.g = GBasic()
        self.g.cmd("GRAPHICS ON")

    def check(self, cmd, want, label=None):
        g = self.g
        g.cmd("ERASE")
        self.assertEqual(page_pixels(g), set())
        g.cmd(cmd)
        got = page_pixels(g)
        if got != want:
            self.fail("%s: %d pixels, model %d; extra %s, missing %s" % (cmd, len(got), len(want), sorted(got - want)[:8],
                                                                       sorted(want - got)[:8]))

    def test_start_state(self):
        v = self.g.video
        self.assertEqual(page_pixels(self.g, 0), set())     # GBASIC clears both pages when it starts
        self.assertEqual(page_pixels(self.g, 1), set())
        self.assertTrue(v.gfx_on() and v.text_on())

    def test_pset_point(self):
        g = self.g
        g.cmd("ERASE: PSET 0,0: PSET 511,199: DOT 100,50: PSET -1,5: PSET 512,5: PSET 5,200")
        self.assertEqual(page_pixels(g), {(0, 0), (511, 199), (100, 50)})
        self.assertEqual(lines_of(g.cmd("PRINT POINT(100,50);POINT(101,50);POINT(-5,0)")), ["100"])

    def test_lines(self):
        for c in ((0, 10, 511, 10), (20, 20, 20, 120), (0, 0, 511, 199), (511, 0, 0, 199), (10, 190, 300, 5),
                  (300, 5, 10, 190), (5, 5, 6, 195), (400, 100, 30, 101), (-50, -20, 600, 260), (250, 100, 250, 100),
                  (100, -30, 100, 30), (-10, 50, 30, 50)):
            self.check("LINE %d,%d,%d,%d" % c, ref_line(*c))
        g = self.g; g.cmd("ERASE: LINE 10,10,20,10: LINE 20,20: LINE 10,20")   # from the graphics cursor
        self.assertEqual(page_pixels(g), ref_line(10, 10, 20, 10) | ref_line(20, 10, 20, 20) | ref_line(20, 20, 10, 20))

    def test_boxes(self):
        for c, f in (((100, 50, 200, 150), 0), ((300, 50, 400, 150), 1), ((400, 150, 300, 50), 0), ((5, 5, 5, 5), 0),
                     ((10, 10, 60, 10), 0), ((10, 10, 10, 60), 0), ((-20, -20, 40, 40), 0), ((500, 190, 530, 230), 1),
                     ((7, 3, 200, 4), 1)):
            self.check("BOX %d,%d,%d,%d%s" % (c + (",F" if f else "",)), ref_box(*c, fill=f))
        self.check("BOX 1,1,40,40,1", ref_box(1, 1, 40, 40, 1))      # a non-zero expression fills too

    def test_circles_and_ellipses(self):
        for c, f in (((256, 100, 90), 0), ((256, 100, 100), 1), ((450, 150, 40), 1), ((10, 10, 30), 0), ((100, 100, 0), 0),
                     ((100, 100, 1), 0), ((100, 100, 2), 1), ((256, 100, 300), 0), ((-100, -100, 150), 1)):
            self.check("CIRCLE %d,%d,%d%s" % (c + (",F" if f else "",)), ref_ellipse(c[0], c[1], c[2], c[2], f))
        for c, f in (((150, 170, 100, 25), 0), ((400, 30, 60, 20), 1), ((256, 100, 200, 3), 0), ((256, 100, 3, 90), 1),
                     ((256, 100, 0, 40), 0), ((256, 100, 40, 0), 1), ((256, 100, 1000, 1000), 0)):
            self.check("ELLIPSE %d,%d,%d,%d%s" % (c + (",F" if f else "",)), ref_ellipse(*c, fill=f))
        self.assertIn("?Illegal value", self.g.cmd("CIRCLE 1,1,1001"))

    def test_filled_circle_area(self):
        self.g.cmd("ERASE: CIRCLE 256,100,100,F")
        n = self.g.video.count_pixels()
        self.assertAlmostEqual(n / (3.14159265 * 100.5 ** 2), 1.0, delta=0.005)

    def test_pens(self):
        g = self.g
        g.cmd("ERASE 255")
        self.assertEqual(g.video.count_pixels(), 512 * 200)
        g.cmd("PEN 0: CIRCLE 256,100,50,F: BOX 0,0,100,100: LINE 0,199,511,0: PSET 300,10")
        holes = ref_ellipse(256, 100, 50, 50, 1) | ref_box(0, 0, 100, 100, 0) | ref_line(0, 199, 511, 0) | {(300, 10)}
        self.assertEqual(g.video.count_pixels(), 512 * 200 - len(holes))
        g.cmd("PEN 2: ERASE")
        for shape in ("CIRCLE 200,100,80", "CIRCLE 300,100,60,F", "ELLIPSE 256,100,200,90", "BOX 10,10,500,190",
                      "BOX 50,50,450,150,F", "LINE 0,0,511,199", "LINE 511,0,0,199", "LINE 5,5,500,6", "PSET 3,3"):
            g.cmd(shape)
        self.assertGreater(g.video.count_pixels(), 1000)
        for shape in ("CIRCLE 200,100,80", "CIRCLE 300,100,60,F", "ELLIPSE 256,100,200,90", "BOX 10,10,500,190",
                      "BOX 50,50,450,150,F", "LINE 0,0,511,199", "LINE 511,0,0,199", "LINE 5,5,500,6", "PSET 3,3"):
            g.cmd(shape)                                    # every pixel once: drawing again with PEN 2 removes it
        self.assertEqual(g.video.count_pixels(), 0)
        self.assertIn("?Illegal value", g.cmd("PEN 3"))

    def test_erase_fill_and_pages(self):
        g = self.g; v = g.video
        g.cmd("PAGE 0,1: ERASE 170")                        # show page 0, draw on page 1
        self.assertEqual(v.dpage(), 0); self.assertEqual(v.cpage(), 1)
        self.assertEqual(bytes(v.pages[1][:12800]), bytes([170]) * 12800)
        self.assertEqual(v.count_pixels(page=0), 0)
        g.cmd("PAGE 1"); self.assertEqual((v.dpage(), v.cpage()), (1, 1))
        g.cmd("ERASE"); self.assertEqual(v.count_pixels(page=1), 0)
        self.assertIn("?Illegal value", g.cmd("PAGE 2"))

    def test_display_switches(self):
        g = self.g; v = g.video
        g.cmd("GRAPHICS OFF"); self.assertFalse(v.gfx_on())
        g.cmd("GRAPHICS ON: MIX XOR"); self.assertTrue(v.xor_mode())
        g.cmd("MIX OR"); self.assertFalse(v.xor_mode())
        g.program("10 TEXT OFF: INPUT A")
        g.type_text("RUN\n"); g.run_until_waiting()
        self.assertFalse(v.text_on())                       # waiting in INPUT, text off
        g.cmd("1")
        self.assertTrue(v.text_on())                        # back in direct mode the text is on again

    def test_mda_height(self):
        g = GBasic(monitor="mda")
        self.assertIn("512 x 256", g.text())
        g.cmd("GRAPHICS ON: LINE 0,0,0,300: PSET 5,255: PSET 5,256")
        pix = page_pixels(g, h=256)
        self.assertEqual(len(pix), 256 + 1)
        self.assertIn((5, 255), pix)

    def test_no_gfx_board(self):
        g = GBasic(gfx=False)
        self.assertIn("no GFX board", g.text())
        for c in ("GRAPHICS ON", "PSET 1,1", "CIRCLE 1,1,1", "TEXT OFF", "PRINT POINT(1,1)"):
            self.assertIn("?No graphics", g.cmd(c), c)
        self.assertEqual(lines_of(g.cmd("PRINT 6*7")), ["42"])

    def test_screens_for_ken(self):
        """demonstration programs, pictured while they wait in INPUT (before Ready scrolls the text); tests/screens"""
        g = self.g
        os.makedirs(SCREENS, exist_ok=True)
        def shot(src, *pictures):
            g.program(src); g.type_text("RUN\n"); self.assertTrue(g.run_until_waiting())
            for name, mode, scale in pictures: g.video.save_png(os.path.join(SCREENS, name), mode, scale)
            g.cmd("0")
        shot("""
            10 ERASE: GRAPHICS ON: CLS: MIX OR
            20 FOR R=10 TO 90 STEP 10: CIRCLE 128,100,R: NEXT
            30 FOR X=256 TO 511 STEP 16: LINE 256,199,X,0: NEXT
            40 BOX 300,120,500,190,F: PEN 2: CIRCLE 400,155,30,F: PEN 1
            50 ELLIPSE 128,100,120,40
            60 LOCATE 1,2: PRINT "GBASIC 1.0 on VIDEO-G"
            70 LOCATE 2,2: PRINT "512 x 200, text OR graphics"
            80 INPUT A
            """, ("demo-screen.png", "screen", 2), ("demo-graphics.png", "gfx", 1))
        shot("""
            10 MIX XOR: LOCATE 1,2: PRINT "MIX XOR: text dots invert the graphics"
            20 LOCATE 22,40: PRINT "(over the filled box)"
            30 INPUT A
            """, ("demo-xor.png", "screen", 2))
        shot("""
            10 ERASE: CLS: MIX OR: RANDOMIZE 5
            20 FOR X=0 TO 511: D=(X-256)/2: Y=100-D*D/175: PSET X,Y: NEXT
            30 LINE 0,100,511,100: LINE 256,0,256,199
            40 FOR I=0 TO 20: PSET RND(512),RND(200): NEXT
            50 LOCATE 0,0: PRINT "Y = 100 - ((X-256)/2)^2/175  (16-bit integers)"
            60 INPUT A
            """, ("parabola.png", "screen", 2))
        self.assertTrue(os.path.exists(os.path.join(SCREENS, "demo-screen.png")))


class OtherMachines(unittest.TestCase):
    def test_6845_card_text_only(self):
        """the System-5 of today (6845 card, HBIOS 1.0.4): GBASIC runs, graphics say No graphics"""
        g = GBasic(video="6845")
        self.assertIn("No VIDEO-G", g.text())
        self.assertEqual(lines_of(g.run_prog("10 FOR I=1 TO 3: PRINT I*I;: NEXT")), ["149"])
        self.assertIn("?No graphics", g.cmd("CIRCLE 10,10,5"))


class Speed(unittest.TestCase):
    """the emulated 1802's time for single statements (1.76 MHz), from RUN to Ready minus an empty program's"""
    def stmt_ms(self, g, stmt):
        g.program("10 REM"); c0 = g.cycles(); g.cmd("RUN"); base = g.cycles() - c0
        g.program("10 " + stmt); c0 = g.cycles(); g.cmd("RUN", 400_000_000); t = g.cycles() - c0
        return (t - base) * 8 / 1760.0

    def test_speed(self):
        g = GBasic(); g.cmd("GRAPHICS ON")
        for stmt in ("ERASE", "LINE 0,0,511,199", "LINE 0,100,511,100", "LINE 100,0,100,199", "BOX 100,50,400,150",
                     "BOX 100,50,400,150,F", "CIRCLE 256,100,100", "CIRCLE 256,100,100,F", "ELLIPSE 256,100,200,80",
                     "ELLIPSE 256,100,200,80,F", "PSET 100,100", "FOR I=1 TO 100: NEXT", "FOR I=1 TO 100: A=A+I*2: NEXT"):
            ms = self.stmt_ms(g, stmt)
            TIMES.append((stmt, ms))
            g.cmd("ERASE")
        g.program("10 I=1\n20 I=I+1\n30 IF I<100 THEN GOTO 20")
        c0 = g.cycles(); g.cmd("RUN"); TIMES.append(("IF/GOTO loop, 100 passes (RUN)", (g.cycles() - c0) * 8 / 1760.0))
        self.assertLess(dict(TIMES)["ERASE"], 250)


def tearDownModule():
    if TIMES:
        print("\nStatement times on the emulated 1802 at 1.76 MHz:")
        for s, ms in TIMES: print("  %-32s %8.1f ms" % (s, ms))


if __name__ == "__main__":
    unittest.main(verbosity=2)
