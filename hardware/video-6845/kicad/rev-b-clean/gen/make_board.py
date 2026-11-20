#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-20
"""make_board.py - Rev B-Clean's board: Rev B's (../rev-b/video-6845-rev-b.kicad_pcb, the copper of Ken's working card,
track for track as the 2005 Eagle board) without the DB9 (Ken, 2026-11-20: "no need for db9, composite only ... a
cleanup with minimal to no changes to circuit"), and with the 6845's light-pen input tied to ground (Ken, the same day:
"Yes tie light pen to gnd"). Run with KiCad's Python after gen/make_schematic.py and
gen/footprints.py; writes ../video-6845-rev-b-clean.kicad_pcb with Rev B's silkscreen texts still on it (gen/silk.py
redoes them).

  0. Rev B's board under its new names: the project and its libraries; the bus connector U$1 (Eagle's name) is J1, the
     RCA jack U$4 is J2; the title block (rev B-Clean)
  1. X1, the DB9, taken off, with the comment-layer area Eagle drew round it
  2. the copper that ran only to X1's four used pins (ground, video, HSYNC, VSYNC) removed: the track at each pin, then
     whatever that leaves with an end on nothing, until nothing dangles. Every other track and via is Rev B's, and is
     locked
  3. every part's drawing brought up to this folder's library (gen/footprints.py: bodies and courtyards), with
     tools/kicad/fp_update.py, which touches no pad
  4. checked: every pad still has the net Rev B gave it; then the one change to the circuit, IC3's pin 3 (LPSTB, open
     on Rev B) on ground: three track segments on the top copper, 0.254 mm as all of Rev B's, from the pin out past the
     pad row, round pin 2 (-RESET) and up to the end of the ground track that leaves pin 1; then every net of the
     schematic's netlist is one net here
  5. the nets under the schematic's names. Rev B's board kept the names Eagle gave them in 2005 (N$45, VADDR11), which
     KiCad's parity check counts as 199 differences from the schematic (/Sheet 1/VADDR11, Net-(IC14A-O)): the same nets
     under other names. Each board net takes its schematic name, and each pin the schematic leaves open on purpose its
     "unconnected-" net. Names only: no pad joins or leaves a net
"""
import os, re, sys
import pcbnew
HERE = os.path.dirname(os.path.abspath(__file__)); DEST = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(DEST, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "kicad")); import kicad_route, fp_update
OLD, NEW = "video-6845-rev-b", "video-6845-rev-b-clean"
REVB = os.path.join(DEST, "..", "rev-b", OLD + ".kicad_pcb")
PCB = os.path.join(DEST, NEW + ".kicad_pcb")
NET = os.path.join(DEST, "reports", "netlist.net")
LIB = os.path.join(DEST, NEW + "-eagle.pretty")
RENAME = {"U$1": "J1", "U$4": "J2"}
GONE = "X1"
T, MM = pcbnew.ToMM, pcbnew.FromMM


def netlist():
    """the schematic's netlist: {net: its (reference, pin) set}"""
    s = open(NET).read(); nets = {}
    for name, body in re.findall(r'\(net\s+\(code "\d+"\)\s+\(name "([^"]+)"\)(.*?)(?=\n\t\t\(net\s|\n\t\)\n\))', s, re.S):
        nets[name] = frozenset(re.findall(r'\(node\s+\(ref "([^"]+)"\)\s+\(pin "([^"]+)"\)', body))
    return nets


def main():
    # 0. Rev B's board, renamed
    src = open(REVB).read().replace(OLD, NEW)
    for old, new in RENAME.items():
        assert src.count('"%s"' % old) >= 1, old
        src = src.replace('"%s"' % old, '"%s"' % new)
    open(PCB, "w").write(src)
    b = pcbnew.LoadBoard(PCB)
    tb = b.GetTitleBlock(); tb.SetTitle("System-5 6845 video Rev B-Clean"); tb.SetRevision("B-Clean"); tb.SetDate("2026-11-20")
    tb.SetComment(0, "Rev B (Ken's working card, 2005) without the DB9; see README.md")
    before = {(f.GetReference(), p.GetNumber()): p.GetNetname() for f in b.GetFootprints() for p in f.Pads()}
    b.FindFootprintByReference("SV1").SetValue("ADDRESS BLOCK 2x4")   # as the schematic (gen/make_schematic.py)
    # 1 and 2. the DB9's copper: found here, removed below on the file's text (pcbnew loses its place when items are
    #    removed while walking a list), by each item's uuid
    x1 = b.FindFootprintByReference(GONE)
    old = {p.GetNumber(): (p.GetNetname(), p.GetPosition()) for p in x1.Pads() if p.GetNetname()}
    gone = set()
    def at(pt, q): return abs(T(pt.x) - T(q.x)) < 0.01 and abs(T(pt.y) - T(q.y)) < 0.01
    for pin, (net, pos) in old.items():
        for t in b.GetTracks():
            if t.GetNetname() == net and t.Type() != pcbnew.PCB_VIA_T and (at(t.GetStart(), pos) or at(t.GetEnd(), pos)):
                gone.add(t.m_Uuid.AsString())
    assert len(gone) == len(old) == 4, (len(gone), sorted(old))
    first = set(gone)
    nets = {n for n, _ in old.values()}
    pads = {}
    for f in b.GetFootprints():
        if f.GetReference() != GONE:
            for p in f.Pads():
                pads.setdefault(p.GetNetname(), []).append(p)
    while True:                                          # dangling: an end that meets no pad, via or other track of its net
        live = [t for t in b.GetTracks() if t.m_Uuid.AsString() not in gone and t.GetNetname() in nets]
        more = set()
        for t in live:
            if t.Type() == pcbnew.PCB_VIA_T:             # a via that live tracks of its net reach on one layer only
                on = {o.GetLayer() for o in live if o is not t and o.Type() != pcbnew.PCB_VIA_T and
                      (at(o.GetStart(), t.GetPosition()) or at(o.GetEnd(), t.GetPosition()) or o.HitTest(t.GetPosition()))}
                if len(on) < 2 and not any(p.HitTest(t.GetPosition()) for p in pads.get(t.GetNetname(), [])):
                    more.add(t.m_Uuid.AsString())        # (or none): it joins nothing to anything now
                continue
            for end in (t.GetStart(), t.GetEnd()):
                hit = any(p.HitTest(end) for p in pads.get(t.GetNetname(), []))
                hit = hit or any(o is not t and o.GetNetname() == t.GetNetname() and (
                    (o.Type() == pcbnew.PCB_VIA_T and o.HitTest(end)) or
                    (o.Type() != pcbnew.PCB_VIA_T and o.GetLayer() == t.GetLayer() and (at(o.GetStart(), end) or at(o.GetEnd(), end) or o.HitTest(end))))
                    for o in live)
                if not hit:
                    more.add(t.m_Uuid.AsString()); break
        if not more:
            break
        gone |= more
    kinds = [("via" if t.Type() == pcbnew.PCB_VIA_T else "track", t.GetNetname()) for t in b.GetTracks() if t.m_Uuid.AsString() in gone]
    print("copper removed with the DB9: %d tracks and %d vias (%s)" % (
        sum(k == "track" for k, _ in kinds), sum(k == "via" for k, _ in kinds),
        ", ".join("%s %d" % (n, sum(1 for _, m in kinds if m == n)) for n in sorted(nets))))
    xbox = x1.GetBoundingBox(False)
    zone = [z.m_Uuid.AsString() for z in b.Zones() if not z.GetNetname() and z.GetBoundingBox().Intersects(xbox)
            and z.GetBoundingBox().GetLeft() < x1.GetPosition().x < z.GetBoundingBox().GetRight()]
    assert len(zone) == 1, zone
    for t in b.GetTracks():
        if t.m_Uuid.AsString() not in gone:
            t.SetLocked(True)
    pcbnew.SaveBoard(PCB, b)
    forms = kicad_route.top_forms(open(PCB).read())
    def drop(f):
        if f.startswith(("(segment", "(via", "(arc")) and any(u in f for u in gone): return True
        if f.startswith("(zone") and zone[0] in f: return True
        if f.startswith("(footprint") and re.search(r'\(property "Reference" "%s"' % GONE, f): return True
        return False
    keep = [f for f in forms if not drop(f)]
    assert len(forms) - len(keep) == len(gone) + 2, (len(forms), len(keep), len(gone))
    text = "(kicad_pcb\n\t" + "\n\t".join(keep) + "\n)\n"
    # 3. the parts' drawings from this folder's library
    mods = {ref: open(os.path.join(LIB, fpid.split(":")[1] + ".kicad_mod")).read() for ref, fpid in fp_update.refs(text).items()}
    text, n = fp_update.update_all(text, mods)
    open(PCB, "w").write(text)
    # 4. the checks
    b = pcbnew.LoadBoard(PCB)
    after = {(f.GetReference(), p.GetNumber()): p.GetNetname() for f in b.GetFootprints() for p in f.Pads()}
    want = {(RENAME.get(r, r), p): n for (r, p), n in before.items() if r not in (GONE,) and RENAME.get(r, r) != GONE}
    assert after == {k: v for k, v in want.items()}, "a pad's net changed"
    # the 6845's light-pen input (pin 3) to ground: out to the right of the pad row, round pin 2, to the ground track's
    # end 2.54 mm right of and 1.27 mm above pin 1 (as drawn), which this board has from Rev B
    ic3 = b.FindFootprintByReference("IC3"); p1, p3 = ic3.FindPadByNumber("1"), ic3.FindPadByNumber("3")
    assert p1.GetNetname() == "GND" and not p3.GetNetname(), (p1.GetNetname(), p3.GetNetname())
    a = p3.GetPosition(); aim = pcbnew.VECTOR2I(p1.GetPosition().x + MM(2.54), p1.GetPosition().y - MM(1.27))
    ends = [e for t in b.GetTracks() if t.Type() != pcbnew.PCB_VIA_T and t.GetNetname() == "GND" and t.GetLayer() == pcbnew.F_Cu
            for e in (t.GetStart(), t.GetEnd()) if abs(e.x - aim.x) < MM(0.02) and abs(e.y - aim.y) < MM(0.02)]
    assert ends, "no ground track ends where the tie is to join"
    d = ends[0]
    pts = [a, pcbnew.VECTOR2I(d.x - MM(1.27), a.y), pcbnew.VECTOR2I(d.x, a.y - MM(1.27)), d]
    assert abs((d.x - MM(1.27)) - a.x - MM(1.27)) < MM(0.02), "pin 3 is not where the tie expects it"
    gnd = b.FindNet("GND"); p3.SetNet(gnd)
    for q0, q1 in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(b); t.SetStart(q0); t.SetEnd(q1); t.SetLayer(pcbnew.F_Cu); t.SetWidth(MM(0.254)); t.SetNet(gnd)
        t.SetLocked(True); b.Add(t)
    print("IC3 pin 3 (LPSTB) tied to ground: 3 segments on F.Cu, %s" % " - ".join("(%.2f, %.2f)" % (T(q.x), T(q.y)) for q in pts))
    after = {(f.GetReference(), p.GetNumber()): p.GetNetname() for f in b.GetFootprints() for p in f.Pads()}
    group = {}
    for (ref, pin), net in after.items():
        if net: group.setdefault(net, set()).add((ref, pin))
    board_groups = {frozenset(v) for v in group.values()}
    sch_groups = {v for v in netlist().values()}
    multi = lambda gs: {g for g in gs if len(g) > 1}
    assert multi(board_groups) == multi(sch_groups), "the board's nets are not the schematic's"
    # 5. the schematic's names
    sch = {node: name for name, nodes in netlist().items() for node in nodes}
    names = {}
    for node, net in after.items():
        if net: names.setdefault(net, set()).add(sch[node])
    assert all(len(v) == 1 for v in names.values()), "a board net spans two schematic nets"
    renamed = 0
    for net, (new,) in ((k, tuple(v)) for k, v in names.items()):
        if net != new:
            assert b.FindNet(new) is None, new
            b.FindNet(net).SetNetname(new); renamed += 1
    opened = 0
    for f in b.GetFootprints():
        for p in f.Pads():
            want = sch.get((f.GetReference(), p.GetNumber()))
            if want and not p.GetNetname():               # a pin the schematic leaves open on purpose
                ni = pcbnew.NETINFO_ITEM(b, want); b.Add(ni); p.SetNet(ni); opened += 1
    assert {(f.GetReference(), p.GetNumber()): p.GetNetname() for f in b.GetFootprints() for p in f.Pads() if p.GetNetname()} == \
        {k: v for k, v in sch.items()}, "a pad's net is not the schematic's"
    print("nets under the schematic's names: %d renamed, %d open pins named" % (renamed, opened))
    pcbnew.SaveBoard(PCB, b)
    print("drawings from the library: %d parts; %d nets of two pins or more, the schematic's exactly" % (len(mods), len(multi(board_groups))))
    print("wrote", PCB, "-", len(list(b.GetFootprints())), "footprints,", len(list(b.GetTracks())), "tracks and vias: Rev B's and the tie, all locked")
    sys.stdout.flush(); os._exit(0)


if __name__ == "__main__":
    main()
