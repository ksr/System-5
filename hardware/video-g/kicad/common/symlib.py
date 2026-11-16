# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-01
"""symlib.py - read KiCad symbols for the VIDEO-G generators (stock KiCad 10 libraries + kicad/lib/video-g-local).

symbol(lib_id)  -> the symbol's text, flattened ("extends" resolved) and renamed to lib_id, ready to embed
pins(lib_id)    -> {number: Pin} for every pin of the symbol (all units; De Morgan alternates skipped)
units(lib_id)   -> sorted unit numbers that carry pins (unit 0 = common to all units)
"""
import os, re
from collections import namedtuple

STOCK = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols"
KICAD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))           # hardware/video-g/kicad
LOCAL_NAME = "video-g-local"
LOCAL_SYM = os.path.join(KICAD, "lib", LOCAL_NAME + ".kicad_sym")
LOCAL_FP = os.path.join(KICAD, "lib", LOCAL_NAME + ".pretty")

Pin = namedtuple("Pin", "number name etype unit x y angle length hidden")


def block(text, i):
    """the balanced (...) form starting at text[i]"""
    d = 0; j = i; ins = False
    while True:
        c = text[j]
        if ins:
            if c == "\\": j += 1
            elif c == '"': ins = False
        elif c == '"': ins = True
        elif c == "(": d += 1
        elif c == ")":
            d -= 1
            if d == 0: return text[i:j + 1]
        j += 1


_lib = {}
def _libtext(lib):
    if lib not in _lib:
        path = LOCAL_SYM if lib == LOCAL_NAME else os.path.join(STOCK, lib + ".kicad_sym")
        _lib[lib] = open(path).read()
    return _lib[lib]


def _top(t, name):
    m = re.search(r'\(symbol "%s"' % re.escape(name), t)
    if not m: raise KeyError("symbol %s not found" % name)
    return block(t, m.start())


_sym = {}
def symbol(lib_id):
    """flattened symbol text named lib_id (Lib:Name), as embedded in a schematic's lib_symbols"""
    if lib_id in _sym: return _sym[lib_id]
    lib, name = lib_id.split(":")
    t = _libtext(lib)
    b = _top(t, name)
    m = re.search(r'\(extends "([^"]+)"\)', b)
    if m:
        parent = m.group(1); pb = _top(t, parent)
        props = dict(re.findall(r'\(property "([^"]+)" ("[^"]*")', b))
        pb = pb.replace('(symbol "%s_' % parent, '(symbol "%s_' % name)
        for k, v in props.items():
            pb = re.sub(r'\(property "%s" "[^"]*"' % re.escape(k), '(property "%s" %s' % (k, v), pb, count=1)
        b = pb.replace('(symbol "%s"' % parent, '(symbol "%s"' % name, 1)
    b = b.replace('(symbol "%s"' % name, '(symbol "%s"' % lib_id, 1)
    _sym[lib_id] = b
    return b


_PIN = re.compile(r'\(pin (\w+) \w+\s*\(at ([\-\d.]+) ([\-\d.]+) (\d+)\)\s*\(length ([\d.]+)\)(\s*\(hide yes\))?'
                  r'\s*\(name "([^"]*)".*?\(number "([^"]*)"', re.S)


def pins(lib_id):
    """{number: Pin}; unit from the sub-symbol name NAME_<unit>_<style>; style 2 (De Morgan) skipped"""
    s = symbol(lib_id); name = lib_id.split(":")[1]           # sub-symbols keep the bare name: NAME_1_1
    out = {}
    for m in re.finditer(r'\(symbol "%s_(\d+)_(\d+)"' % re.escape(name), s):
        unit, style = int(m.group(1)), int(m.group(2))
        if style > 1: continue
        sub = block(s, m.start())
        for p in _PIN.finditer(sub):
            num = p.group(8)
            out[num] = Pin(num, p.group(7), p.group(1), unit, float(p.group(2)), float(p.group(3)), int(p.group(4)),
                           float(p.group(5)), bool(p.group(6)))
    return out


def units(lib_id):
    return sorted({p.unit for p in pins(lib_id).values()})
