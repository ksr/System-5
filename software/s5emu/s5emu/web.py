# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-06
"""Browser emulator: a local web server (standard library only) around the same Shell as the terminal UI.

  GET  /                 the page (s5emu/web/index.html): a Machine tab (screen and keyboard) and a Debugger tab
  GET  /api/state        screen, cursor, registers, code at PC, memory window, 1861 frame, breakpoints, stop reason
  GET  /api/state?light  only what the Machine tab draws (screen, cursor, Q, run state, 1861 frame): cheaper to poll
  POST /api/cmd          {"cmd": "..."} -> {"out": "..."}   (the debugger command language; 'c' runs, 'stop' pauses,
                                                            'speed max|500k|1.76m|2m|HZ' sets the emulated clock)
  POST /api/key          {"text": "..."}                   typed on the System-5 keyboard
  POST /api/mem          {"addr": "..."}                   move the memory window
The emulator runs in a background thread; a lock keeps commands and execution apart. Everything the page does goes
through App's methods, so a page that runs the emulator itself (in the browser, with Pyodide) can call them directly
instead of over HTTP.
"""
import json, os, threading, time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlsplit
from .machine import PANEL_MODES

HERE = os.path.dirname(os.path.abspath(__file__))
CYCLE_CLOCKS = 8                                 # an 1802 machine cycle is 8 clock periods


def parse_clock(text):
    """'max' / '0' -> None (flat out); '500k', '1.76m', '2m', '4000000' -> the clock in Hz."""
    t = text.strip().lower().replace("hz", "")
    if t in ("max", "fast", "0", ""): return None
    mult = 1
    if t.endswith("k"): mult, t = 1e3, t[:-1]
    elif t.endswith("m"): mult, t = 1e6, t[:-1]
    hz = float(t) * mult
    if not 1e3 <= hz <= 50e6: raise ValueError("a clock between 1 kHz and 50 MHz, or max")
    return hz


class App:
    def __init__(self, shell, speed=None, running_flag=None, run=False):
        """speed: machine cycles a second (None = flat out), as the command line's --speed."""
        self.sh = shell; self.m = shell.m; self.d = shell.d; self.lock = threading.RLock()
        self.running = bool(run); self.speed = speed; self.mem_addr = 0; self.log = ["System-5 emulator: 'help' for commands"]
        self.flag = running_flag if running_flag is not None else [False]
        self.flag[0] = self.running
        threading.Thread(target=self._loop, daemon=True).start()

    SLICE = 2000                                 # instructions per lock hold (a few ms)

    def _loop(self):
        while True:
            if not self.running: time.sleep(0.02); continue
            t0 = time.time()
            with self.lock:
                reason = self.d.run(max_instructions=self.SLICE)
            if not reason.startswith("ran "):
                self.running = False; self.flag[0] = False; self.log.append(reason)
            if self.speed:
                want = self.SLICE * 2 / self.speed; dt = time.time() - t0
                time.sleep(max(want - dt, 0.001))
            else:
                # a real pause, not sleep(0): a thread waiting in lock.acquire() only gets the lock if this loop is not
                # already back in acquire() - without it page requests waited seconds (2026-10-06)
                time.sleep(0.001)

    def clock(self):
        """the emulated clock in Hz, or None when running flat out"""
        return self.speed * CYCLE_CLOCKS if self.speed else None

    def cmd(self, line):
        line = line.strip()
        if line == "c": self.running = True; self.flag[0] = True; self.d._hit = None; return "running"
        if line in ("stop", "pause"): self.running = False; self.flag[0] = False; self.d.reason = "paused"; return "paused"
        if line.split()[:1] == ["speed"]:
            arg = line[5:].strip()
            if arg:
                try: hz = parse_clock(arg)
                except ValueError as e: return "speed: %s" % e
                self.speed = hz / CYCLE_CLOCKS if hz else None
            hz = self.clock()
            return "speed: " + ("flat out" if hz is None else "%g kHz clock (%d machine cycles a second)" % (hz / 1e3, self.speed))
        if line.startswith("m ") and len(line.split()) == 2:
            try: self.mem_addr = self.d.addr(line.split()[1]); return "memory at %04X" % self.mem_addr
            except Exception: pass
        with self.lock:
            return self.sh.exec(line)

    def command(self, line):
        """cmd() plus the console log: what the page's command line and buttons call"""
        out = self.cmd(line)
        self.log.append("> " + line); self.log.extend(str(out).splitlines())
        return out

    def key(self, text):
        with self.lock: self.m.kbd.press(text)

    def set_mem(self, addr):
        self.mem_addr = self.d.addr(addr)

    def state(self, light=False):
        with self.lock:
            m, d, c = self.m, self.d, self.m.cpu
            px = m.pixie
            s = {"screen": m.video.lines(), "cursor": m.video.cursor(), "running": self.running, "reason": d.reason,
                 "cpu": {"Q": c.Q, "cycles": c.cycles, "instructions": c.instructions},
                 "pixie": {"on": px.on, "port": px.port, "frame": px.frame.hex() if px.on else ""},
                 "kbd": len(m.kbd.queue), "clock": self.clock(),
                 "disk": os.path.basename(m.ide.path) if getattr(m.ide, "path", None) else None,
                 "rom": getattr(m, "rom_name", None)}
            p = getattr(m, "panel", None)
            if p is not None:                           # the IO panel card: what its LEDs show, how its controls are set
                s["panel"] = {"latch": p.latch, "switches": p.switches, "input": p.pressed, "run": p.run_on,
                              "load": p.load_on, "mode": PANEL_MODES[(p.run_on, p.load_on)]}
            if light: return s
            pc = d.pc()
            s["cpu"] = {"R": c.R, "D": c.D, "DF": c.DF, "X": c.X, "P": c.P, "T": c.T, "IE": c.IE, "Q": c.Q, "idle": c.idle,
                        "cycles": c.cycles, "instructions": c.instructions}
            s["pc"] = pc
            s["code"] = [{"a": a, "b": bs.hex(" "), "t": t, "s": d.sym(a) or "", "bp": a in d.breaks} for a, bs, t in d.dis(pc, 24)]
            s["mem"] = [{"a": (self.mem_addr + i) & 0xFFFF, "b": [m.peek((self.mem_addr + i + k) & 0xFFFF) for k in range(16)]}
                        for i in range(0, 256, 16)]
            s["breaks"] = sorted(d.breaks)
            s["link"] = self.sh.link.path if self.sh.link else None
            s["log"] = self.log[-200:]
            return s


def make_server(app, host="127.0.0.1", port=8802):
    """the HTTP server around an App (port 0 = any free port); serve_forever() runs it"""

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a): pass

        def _json(self, obj, code=200):
            b = json.dumps(obj).encode(); self.send_response(code)
            self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(b)))
            self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(b)

        def do_GET(self):
            u = urlsplit(self.path)
            if u.path in ("/", "/index.html"):
                with open(os.path.join(HERE, "web", "index.html"), "rb") as f: b = f.read()
                self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(b))); self.send_header("Cache-Control", "no-store")
                self.end_headers(); self.wfile.write(b)
            elif u.path == "/api/state": self._json(app.state(light="light" in u.query))
            else: self._json({"error": "not found"}, 404)

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            path = urlsplit(self.path).path
            if path == "/api/cmd":
                self._json({"out": app.command(body.get("cmd", ""))})
            elif path == "/api/key":
                app.key(body.get("text", "")); self._json({"ok": True})
            elif path == "/api/mem":
                try: app.set_mem(body.get("addr", "0"))
                except Exception as e: return self._json({"error": str(e)}, 400)
                self._json({"ok": True})
            else: self._json({"error": "not found"}, 404)

    class Server(ThreadingHTTPServer):
        daemon_threads = True

        def handle_error(self, request, client_address):
            import sys
            if isinstance(sys.exc_info()[1], (BrokenPipeError, ConnectionResetError)): return   # the page dropped a poll
            super().handle_error(request, client_address)

    try:
        return Server((host, port), H)
    except OSError as e:
        raise SystemExit("port %d is busy (%s): is the emulator already running? Use --web-port N for another" % (port, e.strerror))


def serve(shell, port=8802, speed=None, running_flag=None, host="127.0.0.1", run=False):
    app = App(shell, speed, running_flag, run=run)
    srv = make_server(app, host, port)
    shown = "127.0.0.1" if host in ("", "0.0.0.0") else host
    print("System-5 emulator: open http://%s:%d/  (Ctrl-C to quit)" % (shown, srv.server_address[1]), flush=True)
    try: srv.serve_forever()
    except KeyboardInterrupt: pass
