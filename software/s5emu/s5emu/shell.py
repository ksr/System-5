# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-06
"""The debugger command language, shared by the terminal and browser front ends (and scripts).

  s [n]            step n instructions (default 1)          n            step over a call (SEP Rn / SCRT CALL)
  c                continue (front ends run it in the background; 'stop' / Ctrl-C pauses)
  until ADDR       run to ADDR                              reset        CPU reset (remap on, display off)
  b ADDR | bd ADDR | bl        set / delete / list breakpoints (ADDR: hex, $hex, 0x.., NNNNh, a symbol, R3, pc)
  w r|w|i|o ADDR | wd ... | wl watch a memory read/write or an I/O port in/out
  r                registers                               set R3=F000 | set D=12 | set P=3 ...
  m ADDR [LEN]     memory dump                              poke ADDR BYTE [BYTE...]
  d [ADDR] [N]     disassemble (default: at PC)            stack        SCRT call stack (R6, then the R2 stack)
  trace [N]        last N executed instructions            screen       the 6845 screen as text
  key TEXT         type on the keyboard (\\n = Enter, \\e = Esc)
  load FILE [ADDR] load Intel hex / binary into RAM        rom FILE     load the CPU card ROM;  romhi FILE  memory-card EPROM
  sym FILE         load symbols from an rcasm/A18 listing  disk FILE    attach a disk image;   save   write the disk image back
  bus [clear|map|card|stop KIND,...|stop off]   --hw only: bus contention log, who answers each 4K block, the memory card
  pixie            1861 status                              link         bus-driver link pty path
  op68 [stop|run]  opcode 68, which is not an 1802 instruction: run it as the 1802 does (the default: the floating
                   bus to M(R(X)) and D) or stop there, to catch a program that has run off into data
  panel [sw HEX | input [on|off] | run on|off | load on|off]   --panel only: the IO panel card: show it (LEDs,
                   TIL311s, Q, toggles, RUN, LOAD), set the eight toggles, press INPUT (a tap; on / off holds it down and
                   lets it go; in LOAD mode a press is one DMA IN to M(R0)), the RUN/RESET and LOAD toggles (RUN off + LOAD
                   on = LOAD mode; LOAD off = reset; RUN on = run)
  png FILE [screen|gfx|text] [SCALE]   --video g: write the picture (text and graphics as shown) as a PNG
  vg               --video g: control register, Y register, monitor, pages
  help
"""
import os
from .debugger import Debugger


class Shell:
    def __init__(self, machine, debugger=None):
        self.m = machine; self.d = debugger or Debugger(machine); self.link = None

    def exec(self, line):
        """run one command; returns the text to show. 'c' only arms continue: the caller runs self.d.run()."""
        line = line.strip()
        if not line: return ""
        cmd, _, rest = line.partition(" "); a = rest.split(); d = self.d; m = self.m; cpu = m.cpu
        try:
            if cmd in ("help", "?", "h"): return __doc__.split("\n", 2)[2]
            if cmd == "s":
                n = int(a[0], 0) if a else 1
                for _ in range(n): d.step()
                return self._here()
            if cmd == "n": r = d.step_over(); return r + "\n" + self._here()
            if cmd == "until": return d.run(until=d.addr(a[0]), max_instructions=50_000_000) + "\n" + self._here()
            if cmd == "reset": m.reset(); return "reset\n" + self._here()
            if cmd == "b":
                x = d.addr(a[0]); d.breaks.add(x); return "breakpoint %04X%s" % (x, self._s(x))
            if cmd == "bd":
                if a and a[0] == "all": d.breaks.clear(); return "breakpoints cleared"
                d.breaks.discard(d.addr(a[0])); return "deleted"
            if cmd == "bl": return "\n".join("%04X%s" % (x, self._s(x)) for x in sorted(d.breaks)) or "no breakpoints"
            if cmd == "w":
                kind = a[0]; x = d.addr(a[1]) if kind in "rw" else int(a[1], 0); d.watches[(kind, x)] = kind
                return "watch %s %04X" % (kind, x)
            if cmd == "wd":
                if a and a[0] == "all": d.watches.clear(); return "watches cleared"
                kind = a[0]; x = d.addr(a[1]) if kind in "rw" else int(a[1], 0); d.watches.pop((kind, x), None); return "deleted"
            if cmd == "wl": return "\n".join("%s %04X" % k for k in sorted(d.watches)) or "no watches"
            if cmd == "r": return "\n".join(d.regs_text())
            if cmd == "set":
                k, v = rest.replace(" ", "").split("="); v = int(v, 16); k = k.upper()
                if k.startswith("R"): cpu.R[int(k[1:], 16)] = v & 0xFFFF
                elif k in ("D", "DF", "X", "P", "T", "IE", "Q"): setattr(cpu, k, v)
                else: return "unknown register " + k
                return "\n".join(d.regs_text())
            if cmd == "m":
                x = d.addr(a[0]) if a else d.pc(); n = int(a[1], 0) if len(a) > 1 else 128
                return self.dump(x, n)
            if cmd == "poke":
                x = d.addr(a[0])
                for i, b in enumerate(a[1:]): m.write((x + i) & 0xFFFF, int(b, 16))
                return self.dump(x, max(16, len(a) - 1))
            if cmd == "d":
                x = d.addr(a[0]) if a else d.pc(); n = int(a[1], 0) if len(a) > 1 else 16
                return "\n".join(self._line(ad, bs, t) for ad, bs, t in d.dis(x, n))
            if cmd == "stack": return "\n".join("%04X%s" % (x, self._s(x)) for x in d.call_stack())
            if cmd == "trace":
                n = int(a[0]) if a else 20
                return "\n".join("%04X%-14s P=%X D=%02X DF=%d  %s" % (pc, self._s(pc), p, dd, df, t) for pc, p, dd, df, t in list(d.trace)[-n:])
            if cmd == "screen": return "\n".join(m.video.lines())
            if cmd == "key":
                m.kbd.press(rest.replace("\\n", "\n").replace("\\e", "\x1b")); return "typed %d" % len(rest)
            if cmd == "load":
                img = m.load_ram(a[0], d.addr(a[1]) if len(a) > 1 else None)
                return "loaded %d bytes %04X-%04X" % (len(img), min(img), max(img))
            if cmd == "rom": return "CPU card ROM: %d bytes" % m.load_cpu_rom(a[0])
            if cmd == "romhi": return "memory-card EPROM: %d bytes" % m.load_rom(a[0])
            if cmd == "sym": return "%d symbols" % d.load_symbols(a[0])
            if cmd == "disk":
                from .machine import IDE
                m.ide = IDE(a[0]); return "disk %s, %d sectors" % (a[0], len(m.ide.disk) // 512)
            if cmd == "save": m.ide.save(); return "disk saved"
            if cmd == "op68":
                if a and a[0] not in ("stop", "run"): return "op68 stop | op68 run"
                if a: cpu.stop_on_68 = a[0] == "stop"
                return "opcode 68: " + ("stops the emulator" if cpu.stop_on_68 else "runs as on an 1802 (the bus to M(R(X)) and D)")
            if cmd == "pixie":
                p = m.pixie; return "1861 port %d %s, frame %d line %d" % (p.port, "ON" if p.on else "off", p.frames, p.line)
            if cmd == "bus":
                if not hasattr(m, "log"): return "bus model is off (start with --hw)"
                if not a: return m.log.text()
                if a[0] == "clear": m.log.clear(); return "bus log cleared"
                if a[0] == "map": return m.bus_map()
                if a[0] == "card": return m.describe()
                if a[0] == "stop":
                    m.stop_on = set() if len(a) < 2 or a[1] == "off" else set(a[1].split(","))
                    return "stop on: " + (", ".join(sorted(m.stop_on)) or "nothing")
                return "bus: clear, map, card, stop KIND,... / stop off"
            if cmd == "panel":
                if not getattr(m, "panel", None): return "no IO panel (start with --panel A)"
                sub = a[0].lower() if a else ""
                if sub == "sw": m.panel_set(switches=int(a[1], 16))
                elif sub == "input" and len(a) > 1: m.panel_set(input=a[1].lower() in ("on", "1", "down"))   # held
                elif sub == "input": m.panel_set(input=True); m.panel_set(input=False)                      # a tap
                elif sub in ("run", "load"): m.panel_set(**{sub: a[1].lower() in ("on", "1")})
                elif sub == "reset" and len(a) > 1: m.panel_set(reset=a[1].lower() in ("on", "1", "down"))  # held
                elif sub == "reset": m.panel_set(reset=True); m.panel_set(reset=False)     # a tap: the card's RESET button
                elif sub: return "panel [sw HEX | input [on|off] | reset [on|off] | run on|off | load on|off]"
                return m.panel_text()
            if cmd == "front":                              # the front panel, on the IO panel card's ribbon (--hw --front A)
                if not getattr(m, "front", None): return "no front panel (start with --hw --cpu-rev D --panel A --front A)"
                sub = a[0].lower() if a else ""; on = len(a) > 1 and a[1].lower() in ("on", "1", "down")
                if sub == "sw": m.front_set(switches=int(a[1], 16))
                elif sub in ("input", "reset") and len(a) > 1: m.front_set(**{sub: on})                    # held
                elif sub in ("input", "reset"): m.front_set(**{sub: True}); m.front_set(**{sub: False})    # a tap
                elif sub in ("run", "load"): m.front_set(**{sub: on})
                elif sub: return "front [sw HEX | input [on|off] | reset [on|off] | run on|off | load on|off]"
                return m.front_text()
            if cmd == "png":
                if not hasattr(m.video, "save_png"): return "png needs --video g"
                mode = a[1] if len(a) > 1 else "screen"; sc = int(a[2]) if len(a) > 2 else 1
                return "wrote " + m.video.save_png(a[0], mode, sc)
            if cmd == "vg":
                v = m.video
                if not hasattr(v, "ctrl"): return "vg needs --video g"
                return ("VIDEO-G %s%s  control %02X (text %s, graphics %s, %s, show page %d, draw page %d, mouse %s)  Y %d  status %02X"
                        % (v.monitor.upper(), "" if v.gfx else " (no GFX board)", v.ctrl, "on" if v.text_on() else "off",
                           "on" if v.gfx_on() else "off", "XOR" if v.xor_mode() else "OR", v.dpage(), v.cpage(),
                           "on" if v.ctrl & 0x20 else "off", v.yreg, v.status()))
            if cmd == "link": return self.link.path if self.link else "bus-driver link not started (--buslink)"
            return "unknown command '%s' (help)" % cmd
        except Exception as e:
            return "error: %s" % e

    # ------------------------------------------------------------------ formatting
    def _s(self, x):
        s = self.d.sym(x); return " <%s>" % s if s else ""

    def _line(self, a, bs, t):
        return "%04X  %-9s %s%s" % (a, bs.hex(" "), t, "   <%s>" % self.d.sym(a) if self.d.sym(a) else "")

    def _here(self):
        a, bs, t = self.d.dis(None, 1)[0]
        return "%s\n%s" % (self._line(a, bs, t), self.d.regs_text()[0])

    def dump(self, x, n):
        out = []
        for i in range(0, n, 16):
            row = bytes(self.m.peek((x + i + k) & 0xFFFF) for k in range(min(16, n - i)))
            out.append("%04X  %-48s %s" % ((x + i) & 0xFFFF, row.hex(" "), "".join(chr(b) if 32 <= b < 127 else "." for b in row)))
        return "\n".join(out)
