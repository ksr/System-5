# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-06
"""KiCad netlist reader for the hardware-faithful mode.

Reads the `reports/netlist.net` that tools/eagle_to_kicad_all.py (or KiCad) writes for each card, and gives:
  parts   {ref: Part(ref, value, lib)}                     lib = the KiCad lib part name, e.g. 74x151_N_pwrhidden
  pins    {(ref, pin): (net, function)}                    function = the pin name without the '_<pin>' suffix
  nets    {net: [(ref, pin), ...]}

Board reworks are edits on the netlist, so they stay data a photo can correct:
  lift(ref, pin)                  the pin is bent out of its socket: it leaves its net (it floats)
  wire(ref, pin, to_ref, to_pin)  a wire from the lifted pin to another pin: it joins that pin's net
  short(net_a, net_b)             a jumper: the two nets become one
  refit(ref, value, {pin: fn})    another chip in the socket whose pins do other jobs (a 28C256 in a 27C256 socket)
Two boards that work as one (VIDEO-G's TEXT and GFX, joined by a ribbon):
  join(other, prefix)             the other board's parts and nets come in under a prefix; the supplies are shared.
                                  A jumper() per conductor then makes each cable wire one net
"""
import os, re
from collections import namedtuple

Part = namedtuple("Part", "ref value lib")


def _sexp(text):
    toks = re.findall(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+', text); stack = [[]]
    for t in toks:
        if t == "(": stack.append([])
        elif t == ")": x = stack.pop(); stack[-1].append(x)
        else: stack[-1].append(t[1:-1].replace('\\"', '"') if t[0] == '"' else t)
    return stack[0][0]


def _get(node, key):
    return next((x for x in node if isinstance(x, list) and x and x[0] == key), None)


class Netlist:
    def __init__(self, path):
        self.path = path
        with open(path) as f: tree = _sexp(f.read())
        self.parts = {}
        for c in _get(tree, "components")[1:]:
            lib = _get(c, "libsource")
            ref = _get(c, "ref")[1]
            self.parts[ref] = Part(ref, _get(c, "value")[1], _get(lib, "part")[1] if lib else "")
        self.pins = {}; self.pintype = {}
        for n in _get(tree, "nets")[1:]:
            name = _get(n, "name")[1]
            for node in n:
                if isinstance(node, list) and node[0] == "node":
                    ref, pin = _get(node, "ref")[1], _get(node, "pin")[1]
                    fn = (_get(node, "pinfunction") or [None, ""])[1]
                    self.pins[(ref, pin)] = (name, re.sub(r"_[^_]*$", "", fn) if fn else pin)
                    self.pintype[(ref, pin)] = (_get(node, "pintype") or [None, ""])[1]
        self.edits = []

    # ------------------------------------------------------------------ queries
    @property
    def nets(self):
        out = {}
        for key, (net, _) in self.pins.items(): out.setdefault(net, []).append(key)
        return out

    def net(self, ref, pin): return self.pins[(ref, str(pin))][0]
    def function(self, ref, pin): return self.pins[(ref, str(pin))][1]

    def part_pins(self, ref):
        """{function: net} for one part (functions that repeat, like the GND pins of a header, keep the last)"""
        return {fn: net for (r, _), (net, fn) in self.pins.items() if r == ref}

    def pin_by_function(self, ref, function):
        for (r, p), (_, fn) in self.pins.items():
            if r == ref and fn == function: return p
        raise KeyError("%s has no pin %s" % (ref, function))

    # ------------------------------------------------------------------ a second board
    SUPPLIES = ("VCC", "+5V", "GND")

    def join(self, other, prefix):
        """take in another board's netlist: each of its parts and nets under `prefix` (IC1 -> GFX.IC1), the supply nets
        under their own names, so both boards share them. Nothing else is connected yet: a cable is a jumper() per
        conductor"""
        for ref, part in other.parts.items():
            if prefix + ref in self.parts: raise ValueError("join: %s is already a part" % (prefix + ref))
            self.parts[prefix + ref] = Part(prefix + ref, part.value, part.lib)
        for (ref, pin), (net, fn) in other.pins.items():
            self.pins[(prefix + ref, pin)] = (net if net in self.SUPPLIES else prefix + net, fn)
            self.pintype[(prefix + ref, pin)] = other.pintype.get((ref, pin), "")
        self.edits.append("joined with %s (its parts and nets as %s...)" % (os.path.basename(os.path.dirname(os.path.dirname(other.path))), prefix))

    # ------------------------------------------------------------------ reworks
    def lift(self, ref, pin):
        pin = str(pin); net, fn = self.pins[(ref, pin)]
        self.pins[(ref, pin)] = ("lifted:%s.%s" % (ref, pin), fn); self.edits.append("lift %s.%s (was on %s)" % (ref, pin, net))

    def wire(self, ref, pin, to_ref, to_pin):
        pin = str(pin); to = self.net(to_ref, to_pin); fn = self.pins[(ref, pin)][1]
        self.pins[(ref, pin)] = (to, fn); self.edits.append("wire %s.%s to %s.%s (%s)" % (ref, pin, to_ref, to_pin, to))

    def jumper(self, ref_a, pin_a, ref_b, pin_b):
        """a jumper fitted across two header pins: their nets become one (a power net keeps its name)"""
        a, b = self.net(ref_a, pin_a), self.net(ref_b, pin_b)
        if b in ("VCC", "GND", "+5V"): a, b = b, a
        self.short(a, b); self.edits[-1] = "jumper %s.%s-%s.%s (%s)" % (ref_a, pin_a, ref_b, pin_b, self.edits[-1])

    def retype(self, ref, lib, value):
        """a different chip in the socket (same pinout): e.g. the CPU card's 74LS374 where the schematic has a 373"""
        old = self.parts[ref]; self.parts[ref] = Part(ref, value, lib)
        self.edits.append("%s fitted as %s (schematic: %s)" % (ref, value, old.value))

    def refit(self, ref, value, functions):
        """another chip in the socket, same footprint, some pins with other jobs: e.g. a 28C256 EEPROM where the board
        has a 27C256, pin 1 A14 (the 27C256's VPP) and pin 27 ~{WE} (its A14). functions: {pin: the new chip's name}"""
        old = self.parts[ref]; self.parts[ref] = Part(ref, value, old.lib)
        for pin, fn in functions.items():
            net, _ = self.pins[(ref, str(pin))]; self.pins[(ref, str(pin))] = (net, fn)
        self.edits.append("%s fitted as %s (schematic: %s): %s" % (
            ref, value, old.value, ", ".join("pin %s %s" % (p, fn) for p, fn in functions.items())))

    def short(self, net_a, net_b):
        if net_a == net_b: return
        for k, (net, fn) in self.pins.items():
            if net == net_b: self.pins[k] = (net_a, fn)
        self.edits.append("short %s to %s" % (net_b, net_a))
