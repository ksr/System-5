#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-08
"""Turn the converted 6845 Rev B (kicad/rev-b) into the order master, the way kicad/rev-a was done:
2 copper layers, real part values in the schematic and board (IC8 = 74LS163, not the drawn 74HC160), and
silkscreen labels: each chip's part number and job, each passive's value. Run once, under KiCad's python:
  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 gen/make_master.py
"""
import os, re, pcbnew

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PCB = os.path.join(HERE, "video-6845-rev-b.kicad_pcb")
SCH = os.path.join(HERE, "video-6845-rev-b-sheet1.kicad_sch")

VALUES = {
    **{"C%d" % i: "0.1uF" for i in list(range(1, 8)) + list(range(9, 16))}, "C8": "10uF",
    "IC1": "IDT7134", "IC2": "74LS373", "IC3": "HD6845", "IC4": "74LS85", "IC5": "74LS00", "IC6": "74LS04",
    "IC7": "74LS174", "IC8": "74LS163", "IC9": "74LS175", "IC10": "74LS174", "IC11": "74LS166", "IC12": "2732",
    "IC13": "74LS86", "IC14": "7416", "LED1": "LED 5mm", "Q1": "9MHz", "R1": "470", "R2": "1K", "R3": "1K",
    "R4": "1K", "R5": "33", "R6": "270", "RN1": "10k", "SV1": "2x4 header", "U$1": "System-5 bus 30-pin",
    "U$4": "RCA jack", "X1": "DB9 female",
}
JOBS = {
    "IC1": "VIDEO RAM (2K USED)", "IC2": "A8-A15 LATCH", "IC3": "CRTC", "IC4": "BLOCK SELECT (SV1)",
    "IC5": "SEL/CHAR CLK", "IC6": "OSC / INVERT", "IC7": "CHAR BIT 6 LATCH", "IC8": "CHAR CLK /6 (163!)",
    "IC9": "CURSOR/DE DELAY", "IC10": "CHAR LATCH", "IC11": "DOT SHIFT", "IC12": "CHAR ROM 000H",
    "IC13": "VIDEO XOR", "IC14": "VIDEO / SYNC OUT",
}
PASSIVE = re.compile(r"^(C|R|RN)\d+$")


def schematic():
    t = open(SCH).read()
    for ref, val in VALUES.items():
        t, n = re.subn(r'(\(property "Reference" "%s" [^\n]*\n\s*\(property "Value" )"[^"]*"' % re.escape(ref),
                       lambda m: m.group(1) + '"%s"' % val, t)
        if not n: print("schematic: no symbol", ref)
    open(SCH, "w").write(t)


def board():
    b = pcbnew.LoadBoard(PCB)
    b.SetCopperLayerCount(2)
    for fp in b.GetFootprints():
        ref = fp.GetReference()
        if ref in VALUES: fp.SetValue(VALUES[ref])
        label = None
        if ref in JOBS:
            label, pos = "%s %s\n%s" % (ref, VALUES[ref], JOBS[ref]), fp.GetPosition()
            ang = 90 if abs(fp.GetOrientationDegrees()) == 90 else 0
        elif PASSIVE.match(ref):
            r = fp.Reference()
            label, pos, ang = "%s %s" % (ref, VALUES[ref]), r.GetPosition(), r.GetTextAngleDegrees() % 180
        if label:
            fp.Reference().SetVisible(False)
            t = pcbnew.PCB_TEXT(b); t.SetText(label); t.SetPosition(pos); t.SetLayer(pcbnew.F_SilkS)
            t.SetTextAngleDegrees(ang); s = 1.0 if ref in JOBS else 1.1557
            t.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(s), pcbnew.FromMM(s))); t.SetTextThickness(pcbnew.FromMM(0.15))
            b.Add(t)
    pcbnew.SaveBoard(PCB, b)


if __name__ == "__main__":
    schematic(); board()
    open(os.path.join(HERE, "MASTER"), "w").write(
        "Hand-maintained KiCad master since 2026-10-08: 2 copper layers (KiCad's Eagle import made it 4), real part "
        "values (IC8 = 74LS163), silkscreen labels and JLCPCB order files (gen/make_master.py, gen/make_orders.sh). "
        "tools/eagle_to_kicad_all.py must not regenerate this folder.\n")
