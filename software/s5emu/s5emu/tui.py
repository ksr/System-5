# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-06
"""Terminal debugger (curses).

  +-- System-5 screen (64x16) -------+  +-- registers ---------+
  |                                   |  | D DF X P T IE Q      |
  |                                   |  | R0..RF               |
  +-----------------------------------+  +-- code at PC --------+
  +-- memory -------------------------+  |  disassembly          |
  +-- output -------------------------+  +----------------------+
  > command line  (help for commands)

Commands as in shell.py, plus 'view text|pixie|auto' for the screen pane (auto = 1861 graphics while the 1861 is on).
Keys: F5 or 'c' continue, F6/Esc pause, F10 or 's' step, F11 or 'n' step over.
While running, typed keys go to the System-5 keyboard (Enter = CR); Esc pauses. While paused the command line is active.
"""
import curses, time


class TUI:
    def __init__(self, shell, speed=None):
        self.sh = shell; self.m = shell.m; self.d = shell.d; self.out = ["System-5 emulator - 'help' for commands, 'c' to run"]
        self.cmd = ""; self.running = False; self.mem_addr = 0x0000; self.speed = speed; self.history = []
        self.view = "auto"                            # 'text' (6845), 'pixie' (1861) or 'auto' (1861 while it is on)

    def log(self, text):
        for l in str(text).splitlines() or [""]: self.out.append(l)
        self.out = self.out[-400:]

    # ------------------------------------------------------------------ drawing
    def box(self, win, title):
        win.erase(); win.box(); win.addstr(0, 2, " %s " % title)

    def draw(self, scr):
        H, W = scr.getmaxyx()
        if H < 34 or W < 110:
            scr.erase(); scr.addstr(0, 0, "Make the terminal at least 110 x 34 (now %d x %d)" % (W, H)); scr.refresh(); return
        vw, vh = 66, 18
        s = curses.newwin(vh, vw, 0, 0); self.box(s, "System-5 screen %s%s" % ("RUNNING" if self.running else "paused", "  Q" if self.m.cpu.Q else ""))
        cur = self.m.video.cursor()
        pix = self.view == "pixie" or (self.view == "auto" and self.m.pixie.on)
        if pix:                                       # 1861: 128 lines -> every 4th (the usual 64x32) -> half blocks
            bm = self.m.pixie.bitmap(); rows = [bm[r] for r in range(0, 128, 4)]
            for r in range(16):
                top, bot = rows[2 * r], rows[2 * r + 1]
                s.addstr(1 + r, 1, "".join("\u2588" if t and b else "\u2580" if t else "\u2584" if b else " " for t, b in zip(top, bot)))
            cur = None
        else:
            for r, line in enumerate(self.m.video.lines()[:16]):      # VIDEO-G (25 rows): the top 16 here; 'screen' shows all
                s.addstr(1 + r, 1, line[:64])
        if cur and cur[0] < 16 and cur[1] < 64:
            try: s.chgat(1 + cur[0], 1 + cur[1], 1, curses.A_REVERSE)
            except curses.error: pass
        s.noutrefresh()
        rw = W - vw
        r = curses.newwin(9, rw, 0, vw); self.box(r, "registers")
        c = self.m.cpu
        r.addstr(1, 2, "D=%02X  DF=%d  X=%X  P=%X  T=%02X  IE=%d  Q=%d %s" % (c.D, c.DF, c.X, c.P, c.T, c.IE, c.Q, "IDLE" if c.idle else ""))
        for i in range(16):
            r.addstr(2 + i // 4 * 1, 2 + (i % 4) * 11, "R%X %04X" % (i, c.R[i]))
        r.addstr(7, 2, "cycles %d  instr %d  1861 %s" % (c.cycles, c.instructions, "ON" if self.m.pixie.on else "off"))
        r.noutrefresh()
        ch = H - 9 - 2
        d = curses.newwin(ch, rw, 9, vw); self.box(d, "code")
        pc = self.d.pc()
        for i, (a, bs, t) in enumerate(self.d.dis(pc, ch - 2)):
            sym = self.d.sym(a); mark = ">" if a == pc else ("*" if a in self.d.breaks else " ")
            line = "%s%04X %-9s %-18s %s" % (mark, a, bs.hex(" "), t, sym or "")
            d.addstr(1 + i, 1, line[:rw - 2], curses.A_REVERSE if a == pc else 0)
        d.noutrefresh()
        mh = 8
        mm = curses.newwin(mh, vw, vh, 0); self.box(mm, "memory %04X  (m ADDR to move)" % self.mem_addr)
        for i, l in enumerate(self.sh.dump(self.mem_addr, 16 * (mh - 2)).splitlines()): mm.addstr(1 + i, 1, l[:vw - 2])
        mm.noutrefresh()
        oh = H - vh - mh - 2
        o = curses.newwin(oh, vw, vh + mh, 0); self.box(o, "output")
        for i, l in enumerate(self.out[-(oh - 2):]): o.addstr(1 + i, 1, l[:vw - 2])
        o.noutrefresh()
        prompt = ("[running: keys go to System-5, Esc pauses] " if self.running else "> ") + ("" if self.running else self.cmd)
        scr.move(H - 2, 0); scr.clrtobot(); scr.addstr(H - 2, 0, prompt[:W - 1]); scr.addstr(H - 1, 0, ("last stop: " + self.d.reason)[:W - 1], curses.A_DIM)
        scr.noutrefresh(); curses.doupdate()

    # ------------------------------------------------------------------ loop
    def run_command(self, line):
        line = line.strip(); self.history.append(line)
        if line in ("q", "quit", "exit"): return False
        if line == "c": self.running = True; self.d._hit = None; self.log("continue"); return True
        if line.startswith("view"):
            v = (line.split() + ["auto"])[1]
            if v in ("text", "pixie", "auto"): self.view = v; self.log("screen pane: " + v); return True
        if line.startswith("m ") and len(line.split()) == 2:
            try: self.mem_addr = self.d.addr(line.split()[1]); return True
            except Exception: pass
        self.log("> " + line); self.log(self.sh.exec(line)); return True

    def main(self, scr):
        curses.curs_set(0); scr.nodelay(True); scr.keypad(True); curses.raw()
        last = 0; slice_ = 4000
        while True:
            if self.running:
                t0 = time.time()
                reason = self.d.run(max_instructions=slice_)
                if not reason.startswith("ran "):
                    self.running = False; self.log(reason)
                if self.speed:                         # throttle to real 1802 speed (machine cycles per second)
                    want = slice_ * 2 / self.speed; dt = time.time() - t0
                    if dt < want: time.sleep(want - dt)
            now = time.time()
            if now - last > 0.05 or not self.running:
                self.draw(scr); last = now
            k = scr.getch()
            if k == -1:
                if not self.running: time.sleep(0.02)
                continue
            if self.running:
                while k != -1:                          # take every key typed since the last slice, not one per slice
                    if k == 27 or k == curses.KEY_F6:
                        self.running = False; self.log("paused"); self.d.reason = "paused"; break
                    elif k in (10, 13, curses.KEY_ENTER): self.m.kbd.press("\n")
                    elif k in (8, 127, curses.KEY_BACKSPACE): self.m.kbd.queue.append(8)
                    elif 0 < k < 128: self.m.kbd.queue.append(k)
                    k = scr.getch()
                continue
            if k == curses.KEY_F5: self.run_command("c")
            elif k == curses.KEY_F10: self.log(self.sh.exec("s"))
            elif k == curses.KEY_F11: self.log(self.sh.exec("n"))
            elif k in (10, 13, curses.KEY_ENTER):
                if self.cmd.strip() and not self.run_command(self.cmd): return
                self.cmd = ""
            elif k in (8, 127, curses.KEY_BACKSPACE): self.cmd = self.cmd[:-1]
            elif k == 3: return                         # Ctrl-C
            elif 32 <= k < 127: self.cmd += chr(k)


def run(shell, speed=None):
    curses.wrapper(TUI(shell, speed).main)
