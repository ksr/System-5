# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-12
"""Browser emulator: the HTTP API as the page uses it - boot, type, change the clock, both kinds of state."""
import json, os, sys, threading, time, unittest, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, ".."))
from s5emu.machine import Machine
from s5emu.shell import Shell
from s5emu import web
ROM104 = os.path.join(HERE, "..", "roms", "hbios-1.0.4.rom")


class T(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = web.App(Shell(Machine(cpu_rom=ROM104)), run=True)
        cls.srv = web.make_server(cls.app, "127.0.0.1", 0)
        cls.base = "http://127.0.0.1:%d/" % cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.app.running = False; cls.srv.shutdown(); cls.srv.server_close()

    def get(self, path):
        with urllib.request.urlopen(self.base + path, timeout=10) as r:
            return r.read() if path in ("", "index.html") else json.load(r)

    def post(self, path, body):
        req = urllib.request.Request(self.base + path, json.dumps(body).encode(), {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.load(r)

    def wait_screen(self, test, timeout=30):
        t = time.time()
        while time.time() - t < timeout:
            s = self.get("api/state?light")
            if test(s["screen"]): return s
            time.sleep(0.05)
        self.fail("screen never matched; it shows:\n" + "\n".join(self.get("api/state?light")["screen"]))

    def test_1_boots_running_and_echoes_a_key(self):
        self.wait_screen(lambda sc: any(l.rstrip().endswith("test>") for l in sc))
        self.post("api/key", {"text": "X"})
        self.wait_screen(lambda sc: any(l.rstrip().endswith("test>X") for l in sc))

    def test_light_and_full_state(self):
        light = self.get("api/state?light")
        self.assertEqual(len(light["screen"]), 16)
        self.assertTrue(light["running"])
        self.assertNotIn("code", light)                         # the Machine tab's poll skips the debugger's work
        self.assertEqual(light["rom"], "hbios-1.0.4.rom")       # the page says which ROM runs
        full = self.get("api/state")
        for k in ("code", "mem", "breaks", "log", "pc"): self.assertIn(k, full)
        self.assertEqual(len(full["cpu"]["R"]), 16)

    def test_clock(self):
        self.assertIn("500 kHz", self.post("api/cmd", {"cmd": "speed 500k"})["out"])
        self.assertEqual(self.get("api/state?light")["clock"], 500000)
        self.assertIn("flat out", self.post("api/cmd", {"cmd": "speed max"})["out"])
        self.assertIsNone(self.get("api/state?light")["clock"])
        self.assertIn("speed:", self.post("api/cmd", {"cmd": "speed 99g"})["out"])   # rejected, clock unchanged
        self.assertIsNone(self.get("api/state?light")["clock"])

    def test_parse_clock(self):
        self.assertEqual(web.parse_clock("1.76m"), 1.76e6)
        self.assertEqual(web.parse_clock("500k"), 5e5)
        self.assertEqual(web.parse_clock("2000000"), 2e6)
        self.assertIsNone(web.parse_clock("max"))
        self.assertRaises(ValueError, web.parse_clock, "10")    # 10 Hz: below 1 kHz

    def test_page_and_memory_window(self):
        page = self.get("")
        self.assertIn(b'id="mscreen"', page); self.assertIn(b"window.S5_EMU", page)
        self.post("api/mem", {"addr": "F000"})
        self.assertEqual(self.get("api/state")["mem"][0]["a"], 0xF000)


class Panel(unittest.TestCase):
    """the IO panel card on the page: its state, and the panel commands the page's controls send"""
    def test_panel_state_and_commands(self):
        app = web.App(Shell(Machine(cpu_rom=ROM104, panel=True)), run=True)
        srv = web.make_server(app, "127.0.0.1", 0); base = "http://127.0.0.1:%d/" % srv.server_address[1]
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            get = lambda: json.load(urllib.request.urlopen(base + "api/state?light", timeout=10))["panel"]
            cmd = lambda c: json.load(urllib.request.urlopen(urllib.request.Request(base + "api/cmd", json.dumps({"cmd": c}).encode(),
                                                                                      {"Content-Type": "application/json"}), timeout=10))
            self.assertEqual(get(), {"latch": None, "switches": 0, "input": False, "run": True, "load": False, "mode": "run"})
            cmd("panel sw 3C"); self.assertEqual(get()["switches"], 0x3C)
            cmd("panel input on"); self.assertTrue(get()["input"]); cmd("panel input off"); self.assertFalse(get()["input"])
            cmd("panel run off"); cmd("panel load on"); self.assertEqual(get()["mode"], "load")
        finally:
            app.running = False; srv.shutdown(); srv.server_close()


if __name__ == "__main__":
    unittest.main()
