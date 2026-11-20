#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-18
"""make_board.py - Rev F's board: Rev E's (../rev-e/memory-rev-e.kicad_pcb) with the EEPROM sockets (Ken, 2026-11-18:
"yes put in Rev F"; gen/make_schematic.py has the circuit), every Rev E track that still serves kept and locked, so
Freerouting adds only the new connections (gen/route.py). Run with KiCad's Python; writes ../memory-rev-f.kicad_pcb with
Rev E's silkscreen texts still on it (gen/silk.py redoes them after routing).

  0. Rev E's board, the bus connector U$1 (Eagle's name) renamed J1
  1. IC3 and IC5 pins 1 and 27 on their new nets (P1_LO, P27_LO, P1_HI, P27_HI); the sockets' value 27C256/28C256
  2. the A14 (BUFFADDR14) copper that ran through IC5's and IC3's pin 27 removed, and whatever it leaves dangling, so the
     net's other pins stay joined and Freerouting rejoins the rest through the jumpers (pin 1 met VCC through its plane
     only: nothing to remove)
  3. JP1 (IC5, EPROM HI) and JP2 (IC3, EPROM LO), 2 x 3 headers, along the top edge beyond the card guide (the board
     layout rules: jumper blocks at an edge), each turned so its two shunt positions lie along the card when it stands
     in the bus; R6 / R7 (47k, P27_x to VCC) beside them, standing upright; their nets and symbol links from the
     schematic's netlist
  4. every remaining track and via locked
"""
import os, sys, re
import pcbnew
HERE = os.path.dirname(os.path.abspath(__file__)); DEST = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(DEST, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "kicad")); import kicad_route
REVE = os.path.join(DEST, "..", "rev-e", "memory-rev-e.kicad_pcb")
PCB = os.path.join(DEST, "memory-rev-f.kicad_pcb")
NET = os.path.join(DEST, "reports", "netlist.net")
FPLIB = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"
LOCAL = os.path.join(DEST, "memory-rev-d-eagle.pretty")
MM, T = pcbnew.FromMM, pcbnew.ToMM
V = lambda x, y: pcbnew.VECTOR2I(MM(x), MM(y))
SHEET = "/Sheet 1/"
CHANGED = {("IC3", "1"): "P1_LO", ("IC3", "27"): "P27_LO", ("IC5", "1"): "P1_HI", ("IC5", "27"): "P27_HI"}
NEW = {   # ref: (library, footprint, value, (x, y, rotation))
    "JP2": (FPLIB + "/Connector_PinHeader_2.54mm.pretty", "PinHeader_2x03_P2.54mm_Vertical", "EPROM LO PART", (124.0, 16.8, 90)),
    "JP1": (FPLIB + "/Connector_PinHeader_2.54mm.pretty", "PinHeader_2x03_P2.54mm_Vertical", "EPROM HI PART", (139.0, 16.8, 90)),
    # the pull-ups stand upright (2.54 mm pitch): a lying 0207 left R6 no room for its label between JP1 and R5
    "R7": (FPLIB + "/Resistor_THT.pretty", "R_Axial_DIN0207_L6.3mm_D2.5mm_P2.54mm_Vertical", "47k", (126.5, 20.9, 0)),
    "R6": (FPLIB + "/Resistor_THT.pretty", "R_Axial_DIN0207_L6.3mm_D2.5mm_P2.54mm_Vertical", "47k", (141.5, 20.9, 0)),
}
LIBNAME = {"PinHeader": "Connector_PinHeader_2.54mm:", "R_Axial": "Resistor_THT:"}


def netlist():
    s = open(NET).read(); padnet, paths = {}, {}
    for name, body in re.findall(r'\(net\s+\(code "\d+"\)\s+\(name "([^"]+)"\)(.*?)(?=\n\t\t\(net\s|\n\t\)\n\))', s, re.S):
        for ref, pad in re.findall(r'\(node\s+\(ref "([^"]+)"\)\s+\(pin "([^"]+)"\)', body):
            padnet[(ref, pad)] = name
    for block in re.split(r'\n\t\t\(comp\s', s)[1:]:
        ref = re.search(r'\(ref "([^"]+)"\)', block); sp = re.search(r'\(sheetpath\s+\(names "[^"]*"\)\s+\(tstamps "([^"]+)"\)', block)
        ts = re.search(r'\n\t\t\t\(tstamps "([^"]+)"', block)
        if ref and sp and ts:
            paths[ref.group(1)] = sp.group(1).rstrip("/") + "/" + ts.group(1)
    return padnet, paths


def main():
    padnet, paths = netlist()
    # 0. Rev E's board, renamed
    src = open(REVE).read().replace('"U$1"', '"J1"').replace("(U$1-", "(J1-").replace("memory-rev-e", "memory-rev-f")
    open(PCB, "w").write(src)
    b = pcbnew.LoadBoard(PCB)
    nets = {}
    def netitem(n):
        ni = b.FindNet(n)
        if ni is None:
            ni = pcbnew.NETINFO_ITEM(b, n); b.Add(ni)
        return ni
    # 1. the sockets' pins 1 and 27, and their value
    old = {}
    for (ref, pin), net in CHANGED.items():
        p = b.FindFootprintByReference(ref).FindPadByNumber(pin)
        old[(ref, pin)] = (p.GetNetname(), p.GetPosition())
        assert padnet[(ref, pin)] == SHEET + net, (ref, pin, padnet.get((ref, pin)))
        p.SetNet(netitem(SHEET + net))
    for ref in ("IC3", "IC5"):
        b.FindFootprintByReference(ref).SetValue("27C256/28C256")
    # 2. the copper that joined the old nets at those pins, then whatever that leaves dangling (pcbnew loses its place
    #    when items are removed while walking a list, so the removal is done on the file's text, by each item's uuid)
    gone = set()
    def at(pt, q): return abs(T(pt.x) - T(q.x)) < 0.01 and abs(T(pt.y) - T(q.y)) < 0.01
    for (ref, pin), (net, pos) in old.items():
        for t in b.GetTracks():
            if t.GetNetname() == net and (at(t.GetStart(), pos) or at(t.GetEnd(), pos)):
                gone.add(t.m_Uuid.AsString())
    while True:                                          # dangling: an end that meets no pad, via or other track of its net
        anchors = {}
        for fp in b.GetFootprints():
            for p in fp.Pads():
                anchors.setdefault(p.GetNetname(), []).append(("pad", p))
        more = set()
        live = [t for t in b.GetTracks() if t.m_Uuid.AsString() not in gone]
        for t in live:
            if t.Type() == pcbnew.PCB_VIA_T or t.GetNetname() not in {n for n, _ in old.values()}:
                continue
            for end in (t.GetStart(), t.GetEnd()):
                hit = any(p.HitTest(end) for _, p in anchors.get(t.GetNetname(), []))
                hit = hit or any(o is not t and o.GetNetname() == t.GetNetname() and (
                    (o.Type() == pcbnew.PCB_VIA_T and o.HitTest(end)) or
                    (o.Type() != pcbnew.PCB_VIA_T and o.GetLayer() == t.GetLayer() and (at(o.GetStart(), end) or at(o.GetEnd(), end) or o.HitTest(end))))
                    for o in live)
                if not hit:
                    more.add(t.m_Uuid.AsString()); break
        if not more:
            break
        gone |= more
    print("copper removed: %d tracks (A14 through IC3 / IC5 pin 27, and what that left dangling)" % len(gone))
    # 3. the jumper blocks and pull-ups
    for ref, (lib, name, value, (x, y, rot)) in NEW.items():
        fp = pcbnew.FootprintLoad(lib, name)
        fp.SetFPIDAsString(next(v for k, v in LIBNAME.items() if name.startswith(k)) + name)
        fp.SetReference(ref); fp.SetValue(value); fp.SetPosition(V(x, y)); fp.SetOrientationDegrees(rot)
        b.Add(fp)
        for p in fp.Pads():
            p.SetNet(netitem(padnet[(ref, p.GetNumber())]))
        fp.SetPath(pcbnew.KIID_PATH(paths[ref]))
    # 4. lock what Rev E routed
    for t in b.GetTracks():
        if t.m_Uuid.AsString() not in gone:
            t.SetLocked(True)
    pcbnew.SaveBoard(PCB, b)
    forms = kicad_route.top_forms(open(PCB).read())
    keep = [f for f in forms if not (f.startswith(("(segment", "(via", "(arc")) and any(u in f for u in gone))]
    open(PCB, "w").write("(kicad_pcb\n\t" + "\n\t".join(keep) + "\n)\n")
    b = pcbnew.LoadBoard(PCB)
    cy = [(f.GetReference(), f.GetCourtyard(pcbnew.F_CrtYd).BBox()) for f in b.GetFootprints() if f.GetCourtyard(pcbnew.F_CrtYd).OutlineCount()]
    clash = [(a, c) for i, (a, ba) in enumerate(cy) for c, bc in cy[i + 1:] if ba.Intersects(bc) and (a in NEW or c in NEW)]
    print("new parts' courtyards overlapping others:", clash or "none")
    print("wrote", PCB, "-", len(list(b.GetFootprints())), "footprints,", len(list(b.GetTracks())), "tracks and vias (locked: Rev E's)")
    sys.stdout.flush(); os._exit(0)


if __name__ == "__main__":
    main()
