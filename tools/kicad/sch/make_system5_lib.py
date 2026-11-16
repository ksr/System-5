#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-26
"""make_system5_lib.py - writes system5.kicad_sym, the symbols KiCad has no good one for:
  System5_Bus  the 30-pin System-5 bus connector, every pin named (docs/manual/bus.md)
  IDT7134      4K x 8 dual-port RAM, DIL48 (the 6845 card's IC1; drawn as YACC1-D's gen_v20.py draws it)
Box symbols as YACC1-D's gen_v20.py box_symbol() makes them.   python3 tools/kicad/sch/make_system5_lib.py"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sheet as S0
G = 2.54


def pin_line(num, name, etype, x, y, ang, length=2.54):
    eff = "(effects (font (size 1.27 1.27)))"
    return ('\t\t\t(pin %s line (at %s %s %d) (length %s) (name %s %s) (number %s %s))'
            % (etype, S0.f(x), S0.f(y), ang, S0.f(length), S0.q(name), eff, S0.q(num), eff))


def box_symbol(name, ref, desc, left=(), right=(), top=(), bottom=(), width=None):
    L = 2.54
    rows = max(len(left), len(right), 1)
    h = rows * G + G
    w = width or max(15.24, 2.54 * (max(len(top), len(bottom), 1) + 1))
    w = round(w / G) * G
    eff = "(effects (font (size 1.27 1.27)))"
    hid = "(effects (font (size 1.27 1.27)) (hide yes))"
    out = ['\t(symbol "%s"' % name, '\t\t(pin_names (offset 0.762))', '\t\t(exclude_from_sim no) (in_bom yes) (on_board yes)',
           '\t\t(property "Reference" "%s" (at 0 %s 0) %s)' % (ref, S0.f(h / 2 + L + 2.54), eff),
           '\t\t(property "Value" "%s" (at 0 %s 0) %s)' % (name, S0.f(-(h / 2 + L + 2.54)), eff),
           '\t\t(property "Footprint" "" (at 0 0 0) %s)' % hid, '\t\t(property "Datasheet" "" (at 0 0 0) %s)' % hid,
           '\t\t(property "Description" %s (at 0 0 0) %s)' % (S0.q(desc), hid),
           '\t\t(symbol "%s_0_1"' % name,
           '\t\t\t(rectangle (start %s %s) (end %s %s) (stroke (width 0.254) (type default)) (fill (type background)))'
           % (S0.f(-w / 2), S0.f(h / 2), S0.f(w / 2), S0.f(-h / 2)), '\t\t)', '\t\t(symbol "%s_1_1"' % name]
    y0 = h / 2 - G
    for i, (num, pn, et) in enumerate(left):
        out.append(pin_line(num, pn, et, -w / 2 - L, y0 - i * G, 0))
    for i, (num, pn, et) in enumerate(right):
        out.append(pin_line(num, pn, et, w / 2 + L, y0 - i * G, 180))
    for i, (num, pn, et) in enumerate(top):
        out.append(pin_line(num, pn, et, -w / 2 + G + i * G, h / 2 + L, 270))
    for i, (num, pn, et) in enumerate(bottom):
        out.append(pin_line(num, pn, et, -w / 2 + G + i * G, -h / 2 - L, 90))
    out += ['\t\t)', '\t\t(embedded_fonts no)', '\t)']
    return "\n".join(out)


BUS = ["+5V"] + ["D%d" % i for i in range(8)] + ["Q", "TPA", "TPB", "~{MRD}", "~{MRW}"] + ["A%d" % i for i in range(8)] + \
      ["~{INT}", "N2", "~{EF}", "~{VMA}", "~{RESET}", "N1", "N0", "GND"]


def main():
    io, inp, pas, pw = "bidirectional", "input", "passive", "power_in"
    bus = box_symbol("System5_Bus", "J", "System-5 bus: 30-pin single-row 0.1\" card-edge header (docs/manual/bus.md)",
                     right=[(str(i + 1), n, pas) for i, n in enumerate(BUS)], width=12.7)
    s7134 = box_symbol(
        "IDT7134", "IC", "IDT7134 4K x 8 dual-port static RAM, DIL48",
        left=[(str(p), "A%dL" % i, inp) for i, p in enumerate((6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 4, 3))] +
             [(str(16 + i), "I/O%dL" % i, io) for i in range(8)] + [("1", "~{CEL}", inp), ("2", "R/~{WL}", inp), ("5", "~{OEL}", inp)],
        right=[(str(p), "A%dR" % i, inp) for i, p in enumerate((42, 41, 40, 39, 38, 37, 36, 35, 34, 33, 44, 45))] +
              [(str(25 + i), "I/O%dR" % i, io) for i in range(8)] + [("47", "~{CER}", inp), ("46", "R/~{WR}", inp), ("43", "~{OER}", inp)],
        top=[("48", "VCC", pw)], bottom=[("24", "GND", pw)], width=22.86)
    ata = {1: "~{RESET}", 2: "GND", 3: "DD7", 4: "DD8", 5: "DD6", 6: "DD9", 7: "DD5", 8: "DD10", 9: "DD4", 10: "DD11",
           11: "DD3", 12: "DD12", 13: "DD2", 14: "DD13", 15: "DD1", 16: "DD14", 17: "DD0", 18: "DD15", 19: "GND",
           20: "KEY", 21: "DMARQ", 22: "GND", 23: "~{DIOW}", 24: "GND", 25: "~{DIOR}", 26: "GND", 27: "IORDY",
           28: "CSEL", 29: "~{DMACK}", 30: "GND", 31: "INTRQ", 32: "~{IOCS16}", 33: "DA1", 34: "~{PDIAG}", 35: "DA0",
           36: "DA2", 37: "~{CS0}", 38: "~{CS1}", 39: "~{DASP}", 40: "GND"}
    ide = box_symbol("IDE40", "J", "40-pin IDE (ATA) header, 2 x 20, 0.1\": the drive end's signal names",
                     left=[(str(i), ata[i], pas) for i in range(1, 41, 2)],
                     right=[(str(i), ata[i], pas) for i in range(2, 41, 2)], width=20.32)
    text = "\n".join(['(kicad_symbol_lib', '\t(version 20251024)', '\t(generator "make_system5_lib")',
                      '\t(generator_version "1.0")', bus, s7134, ide, ')', ''])
    path = os.path.join(HERE, "system5.kicad_sym")
    open(path, "w").write(text)
    S0.kicad_cli("sym", "upgrade", "--force", path)
    print("wrote", path)


if __name__ == "__main__":
    main()
