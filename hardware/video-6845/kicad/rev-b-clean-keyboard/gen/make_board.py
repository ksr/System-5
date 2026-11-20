#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-20
"""make_board.py - Rev B-Clean-Keyboard's board, before routing: Rev B-Clean's (../rev-b-clean: Rev B's copper, the
card in Ken's machine, less the DB9) made larger, with the 36-pin connector and the keyboard section's parts placed
(gen/keyboard.py). Run with KiCad's Python after gen/make_schematic.py and gen/footprints.py; gen/route.py then has
Freerouting add the new connections, with every Rev B track locked.

  0. Rev B-Clean's board under this card's names; the title block
  1. the outline: 190.5 x 106.565 mm, 49.5 mm more at the front edge and 10.325 mm more at the +5V end of the bus edge
  2. J1: the 36-pin connector C36 where the 30-pin C30 was, pads 1-30 on the same holes
  2b. the RCA jack J2 to the front edge, under the PS/2 jack (keyboard.MOVE)
  3. the 6845's -CS (IC3 pin 25) cut from Rev B's select at IC5 pin 3, which drove it and now drives -UPPER: the
     first two pieces of the track go, the rest stays on the 6845's pin as -CRTCCS, for the new decoder to drive
  3b. Rev B's A2 track, which ran through where the new pin 31 is, turned in between pins 31 and 32
  4. the new parts, each where keyboard.PLACE puts it, linked to its schematic symbol
  5. every pad on the net the schematic gives it; the old nets whose names changed there take the new names. Checked:
     no pad of Rev B-Clean's changes net but the 6845's pin 25, every net of the schematic is one net here, and no
     new pad sits on Rev B's copper
"""
import os, re, sys
import pcbnew
HERE = os.path.dirname(os.path.abspath(__file__)); DEST = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(DEST, "..", "..", "..", ".."))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(ROOT, "tools", "kicad"))
import keyboard as K
import kicad_route
BASE = os.path.join(DEST, "..", "rev-b-clean", K.OLD + ".kicad_pcb")
PCB = os.path.join(DEST, K.NEW + ".kicad_pcb")
NET = os.path.join(DEST, "reports", "netlist.net")
LIB = os.path.join(DEST, K.LIB + ".pretty")
STOCK = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"
T, MM = pcbnew.ToMM, pcbnew.FromMM
V = lambda x, y: pcbnew.VECTOR2I(MM(x), MM(y))


def netlist():
    """-> ({(ref, pin): net}, {ref: its symbol's path for the footprint's link})"""
    s = open(NET).read(); sch, paths = {}, {}
    for name, body in re.findall(r'\(net\s+\(code "\d+"\)\s+\(name "([^"]+)"\)(.*?)(?=\n\t\t\(net\s|\n\t\)\n\))', s, re.S):
        for ref, pad in re.findall(r'\(node\s+\(ref "([^"]+)"\)\s+\(pin "([^"]+)"\)', body):
            sch[(ref, pad)] = name
    for blk in re.split(r'\n\t\t\(comp\s', s)[1:]:
        ref = re.search(r'\(ref "([^"]+)"\)', blk); sp = re.search(r'\(sheetpath\s+\(names "[^"]*"\)\s+\(tstamps "([^"]+)"\)', blk)
        ts = re.search(r'\n\t\t\t\(tstamps "([^"]+)"', blk)
        if ref and sp and ts:
            paths[ref.group(1)] = sp.group(1).rstrip("/") + "/" + ts.group(1).split()[0]
    return sch, paths


def main():
    sch, paths = netlist()
    text = open(BASE).read().replace(K.OLD, K.NEW)
    open(PCB, "w").write(text)
    # what is read off Rev B-Clean's board before anything is taken out of it: where J1 is and what its pads are on
    b0 = pcbnew.LoadBoard(PCB)
    old = b0.FindFootprintByReference("J1")
    assert old.GetFPIDAsString().endswith(":C30"), old.GetFPIDAsString()
    j1_at, j1_rot, j1_path = (old.GetPosition().x, old.GetPosition().y), old.GetOrientationDegrees(), old.GetPath().AsString()
    holes = {p.GetNumber(): (p.GetPosition().x, p.GetPosition().y) for p in old.Pads()}
    # the old outline and the old J1 go on the file's text (pcbnew loses its place when items are removed from a board)
    forms = kicad_route.top_forms(text)
    moved0 = {r: b0.FindFootprintByReference(r) for r in K.MOVE}
    moved0 = {r: (f.GetFPIDAsString(), f.GetValue(), f.GetPath().AsString()) for r, f in moved0.items()}
    offb = ["J1"] + sorted(K.MOVE)                      # (the parts that move come off too and are put back in step 2b)
    keep = [f for f in forms if not (f.startswith("(gr_") and '(layer "Edge.Cuts")' in f)
            and not (f.startswith("(footprint") and any(re.search(r'\(property "Reference" "%s"' % r, f) for r in offb))]
    assert len(forms) - len(keep) >= 1 + len(offb), len(forms) - len(keep)
    open(PCB, "w").write("(kicad_pcb\n\t" + "\n\t".join(keep) + "\n)\n")
    b = pcbnew.LoadBoard(PCB)
    tb = b.GetTitleBlock(); tb.SetTitle("System-5 6845 video Rev B-Clean-Keyboard"); tb.SetRevision(K.REV); tb.SetDate(K.DATE)
    tb.SetComment(0, "Rev B-Clean with VIDEO-G's keyboard section on the 36-pin bus; see README.md")
    before = {(f.GetReference(), p.GetNumber()): p.GetNetname() for f in b0.GetFootprints() for p in f.Pads()}

    def net(name):
        ni = b.FindNet(name)
        if ni is None:
            ni = pcbnew.NETINFO_ITEM(b, name); b.Add(ni)
        return ni

    # 1. the outline
    l, t, r, bt = K.EDGE
    s = pcbnew.PCB_SHAPE(b); s.SetShape(pcbnew.SHAPE_T_RECT); s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(MM(0.1))
    s.SetStart(V(l, t)); s.SetEnd(V(r, bt)); b.Add(s)

    # 2. J1: C36 for C30, on the same holes
    j1 = pcbnew.FootprintLoad(LIB, "C36"); j1.SetFPIDAsString(K.LIB + ":C36")
    j1.SetReference("J1"); j1.SetValue("System-5 bus 36-pin"); j1.SetPosition(pcbnew.VECTOR2I(*j1_at)); j1.SetOrientationDegrees(j1_rot)
    j1.SetPath(pcbnew.KIID_PATH(j1_path)); j1.Reference().SetVisible(False); j1.Value().SetVisible(False)
    b.Add(j1)
    for p in j1.Pads():
        n = p.GetNumber()
        if n in holes:
            assert abs(p.GetPosition().x - holes[n][0]) < 1000 and abs(p.GetPosition().y - holes[n][1]) < 1000, "J1 pad %s moved" % n
            if before[("J1", n)]:                       # (a net no other pad or track is on went with the old J1)
                p.SetNet(net(before[("J1", n)]))
    top = min(T(p.GetPosition().y) for p in j1.Pads())
    print("J1: C36, pads 1-30 on Rev B's holes; pad 36 at y %.2f (top edge %.2f)" % (top, t))

    # 2b. Rev B-Clean's parts that move (K.MOVE: the RCA jack, to the front edge): the same footprint, schematic link and
    #     nets at the new place. The tracks that ran to the old pads stay for now: the routers join the nearest of them
    #     and gen/route_leftovers.py takes off what is then left hanging
    for r_, (x, y, rot) in K.MOVE.items():
        fpid, value, path = moved0[r_]; lib, name = fpid.split(":")
        fp = pcbnew.FootprintLoad(LIB, name); assert fp is not None and lib == K.LIB, fpid
        fp.SetFPIDAsString(fpid); fp.SetReference(r_); fp.SetValue(value); fp.SetPosition(V(x, y)); fp.SetOrientationDegrees(rot)
        fp.SetPath(pcbnew.KIID_PATH(path)); fp.Reference().SetVisible(False); fp.Value().SetVisible(False)
        b.Add(fp)
        for p in fp.Pads():
            if before[(r_, p.GetNumber())]: p.SetNet(net(before[(r_, p.GetNumber())]))
        bb = fp.GetBoundingBox(False)
        print("%s moved to (%.2f, %.2f) at %g: x %.2f-%.2f, y %.2f-%.2f (front edge %.2f)" % (r_, x, y, rot, T(bb.GetLeft()), T(bb.GetRight()), T(bb.GetTop()), T(bb.GetBottom()), r))

    # 3. the 6845's -CS. Rev B's track runs from IC5 pin 3 (the NAND that makes the select) to IC3 pin 25. It is cut
    #    at IC5: its first K.CUT_SEGMENTS pieces, from the pin, go. The rest stays, still on the 6845's pin, and is now
    #    -CRTCCS, which the new decoder drives; IC5 pin 3 keeps the old net, alone on it, and step 5 names it -UPPER
    def at(a, c): return abs(T(a.x) - T(c.x)) < 0.01 and abs(T(a.y) - T(c.y)) < 0.01
    cp = lambda v: pcbnew.VECTOR2I(int(v.x), int(v.y))        # (copies: a track's own point changes with the track)
    pad5 = b.FindFootprintByReference(K.CUT_AT[0]).FindPadByNumber(K.CUT_AT[1]); cs = pad5.GetNetname()
    pad3 = b.FindFootprintByReference(K.CUT[0]).FindPadByNumber(K.CUT[1])
    assert pad3.GetNetname() == cs and sch[K.CUT] != sch[K.CUT_AT], "Rev B's -CS is not IC5 pin 3 to IC3 pin 25"
    gone = set(); pos = cp(pad5.GetPosition())
    for _ in range(K.CUT_SEGMENTS):
        nxt = [tr for tr in b.GetTracks() if tr.GetNetname() == cs and tr.Type() != pcbnew.PCB_VIA_T
               and tr.m_Uuid.AsString() not in gone and (at(tr.GetStart(), pos) or at(tr.GetEnd(), pos))]
        assert len(nxt) == 1, "Rev B's -CS track at IC5 pin 3 is not one run: %d pieces" % len(nxt)
        gone.add(nxt[0].m_Uuid.AsString()); pos = cp(nxt[0].GetEnd() if at(nxt[0].GetStart(), pos) else nxt[0].GetStart())
    kept = [tr for tr in b.GetTracks() if tr.GetNetname() == cs and tr.m_Uuid.AsString() not in gone]
    crtc = net(sch[K.CUT])
    for tr in kept:
        tr.SetNet(crtc)
    pad3.SetNet(crtc)
    print("the 6845's -CS cut from Rev B's select at IC5 pin 3: %d pieces removed, %d tracks and vias kept on IC3 pin 25, "
          "their free end at (%.2f, %.2f)" % (len(gone), len(kept), T(pos.x), T(pos.y)))

    # 3b. Rev B's A2 track runs up the card-edge side of J1's pad row and turns in past the +5V end, through where
    #     pin 31 (-EF1) now is. Its turn is moved to pass between pins 31 and 32: the upright run 1.91 mm longer, a new
    #     level piece through the gap (0.38 mm to each pad), and the slanted piece shortened to meet it.
    pads = {p.GetNumber(): p.GetPosition() for p in j1.Pads()}
    a2 = pads["17"]; ymid = (pads["31"].y + pads["32"].y) // 2
    bend = [tr for tr in b.GetTracks() if tr.Type() != pcbnew.PCB_VIA_T and tr.GetLayer() == pcbnew.F_Cu
            and tr.GetNetCode() == j1.FindPadByNumber("17").GetNetCode()
            and min(tr.GetStart().y, tr.GetEnd().y) < pads["1"].y and min(tr.GetStart().x, tr.GetEnd().x) < a2.x]
    up = [tr for tr in bend if tr.GetStart().x == tr.GetEnd().x]; slant = [tr for tr in bend if tr.GetStart().x != tr.GetEnd().x]
    assert len(up) == 1 and len(slant) == 1, "Rev B's A2 track past J1's +5V end is not as it was: %d + %d" % (len(up), len(slant))
    up, slant = up[0], slant[0]
    corner = cp(up.GetStart() if up.GetStart().y < up.GetEnd().y else up.GetEnd())
    assert at(slant.GetStart(), corner) or at(slant.GetEnd(), corner)
    far = cp(slant.GetEnd() if at(slant.GetStart(), corner) else slant.GetStart())
    assert abs(abs(far.x - corner.x) - abs(far.y - corner.y)) < 1000 and far.y < ymid < corner.y, "A2's slanted piece"
    c2 = pcbnew.VECTOR2I(corner.x, ymid); c3 = pcbnew.VECTOR2I(far.x - (ymid - far.y), ymid)
    (up.SetStart if at(up.GetStart(), corner) else up.SetEnd)(c2)
    slant.SetStart(c3); slant.SetEnd(far)
    lev = pcbnew.PCB_TRACK(b); lev.SetStart(c2); lev.SetEnd(c3); lev.SetLayer(pcbnew.F_Cu); lev.SetWidth(up.GetWidth())
    lev.SetNet(up.GetNet()); b.Add(lev)
    print("Rev B's A2 track turned in between J1's pins 31 and 32: the corner from y %.2f to %.2f, one segment added" % (T(corner.y), T(ymid)))

    # 4. the new parts
    for r_, (value, lib_id, fpid, note) in K.PARTS.items():
        lib, name = fpid.split(":")
        fp = pcbnew.FootprintLoad(LIB if lib == K.LIB else os.path.join(STOCK, lib + ".pretty"), name)
        assert fp is not None, fpid
        fp.SetFPIDAsString(fpid); fp.SetReference(r_); fp.SetValue(value)
        x, y, rot = K.PLACE[r_]; fp.SetPosition(V(x, y)); fp.SetOrientationDegrees(rot)
        fp.SetPath(pcbnew.KIID_PATH(paths[r_])); fp.Reference().SetVisible(False); fp.Value().SetVisible(False)
        b.Add(fp)

    # 5. the nets: the old ones under the schematic's names of today, then every pad on its net
    names = {}
    for f in b.GetFootprints():
        for p in f.Pads():
            key = (f.GetReference(), p.GetNumber())
            if p.GetNetname() and key in sch:
                names.setdefault(p.GetNetname(), set()).add(sch[key])
    for old_name, new_names in names.items():
        assert len(new_names) == 1, "the board's net %s is %s in the schematic" % (old_name, sorted(new_names))
        (new_name,) = new_names
        if new_name != old_name:
            assert b.FindNet(new_name) is None, new_name
            b.FindNet(old_name).SetNetname(new_name)
    moved = []
    for f in b.GetFootprints():
        for p in f.Pads():
            key = (f.GetReference(), p.GetNumber()); want = sch.get(key, "")
            if p.GetNetname() != want:
                if key in before and before[key] and not before[key].startswith("unconnected-"):
                    moved.append(key)                     # (a pin that was open may join a net: J1's -EF)
                p.SetNet(net(want) if want else b.FindNet(""))
    assert not moved, "pads of Rev B-Clean's that would change net: %s" % moved[:8]
    after = {(f.GetReference(), p.GetNumber()): p.GetNetname() for f in b.GetFootprints() for p in f.Pads() if p.GetNetname()}
    assert after == sch, "the board's pads are not on the schematic's nets"
    for tr in b.GetTracks():
        if tr.m_Uuid.AsString() not in gone:
            tr.SetLocked(True)
    pcbnew.SaveBoard(PCB, b)
    forms = kicad_route.top_forms(open(PCB).read())
    keep = [f for f in forms if not (f.startswith(("(segment", "(via", "(arc")) and any(u in f for u in gone))]
    assert len(forms) - len(keep) == len(gone)
    open(PCB, "w").write("(kicad_pcb\n\t" + "\n\t".join(keep) + "\n)\n")

    b = pcbnew.LoadBoard(PCB)
    b.BuildConnectivity()
    cy = [(f.GetReference(), f.GetCourtyard(pcbnew.F_CrtYd).BBox()) for f in b.GetFootprints() if f.GetCourtyard(pcbnew.F_CrtYd).OutlineCount()]
    new = set(K.PARTS) | {"J1"} | set(K.MOVE)
    clash = [(a, c) for i, (a, ba) in enumerate(cy) for c, bc in cy[i + 1:] if ba.Intersects(bc) and (a in new or c in new)]
    eb = b.GetBoardEdgesBoundingBox()
    out = [f.GetReference() for f in b.GetFootprints() if f.GetReference() in new and f.GetReference() not in ("J3", "J2") and not eb.Contains(f.GetBoundingBox(False))]
    print("new parts' courtyards overlapping others:", clash or "none", "| parts over the edge:", out or "none")
    # no new pad on Rev B's copper (a courtyard does not show it: the old tracks run on under the new parts)
    def gap(p, tr):
        c = p.GetPosition(); a, e = tr.GetStart(), tr.GetEnd()
        dx, dy = e.x - a.x, e.y - a.y; L = dx * dx + dy * dy
        u = 0 if L == 0 else max(0.0, min(1.0, ((c.x - a.x) * dx + (c.y - a.y) * dy) / L))
        d = ((c.x - a.x - u * dx) ** 2 + (c.y - a.y - u * dy) ** 2) ** 0.5
        return T(d - max(p.GetSize(pcbnew.F_Cu).x, p.GetSize(pcbnew.F_Cu).y) / 2 - tr.GetWidth() / 2)
    hits = ["%s.%s on %s (%.2f mm)" % (f.GetReference(), p.GetNumber(), tr.GetNetname().split("/")[-1], gap(p, tr))
            for f in b.GetFootprints() if f.GetReference() in new for p in f.Pads() for tr in b.GetTracks()
            if tr.GetNetCode() != p.GetNetCode() and gap(p, tr) < 0.2]
    if hits:
        sys.stdout.flush(); print("STOP: new pads on Rev B's copper:", hits); os._exit(1)
    print("wrote %s: %.1f x %.1f mm, %d footprints, %d tracks and vias (Rev B's, locked), %d connections to route"
          % (os.path.basename(PCB), T(eb.GetWidth()), T(eb.GetHeight()), len(list(b.GetFootprints())), len(list(b.GetTracks())),
             b.GetConnectivity().GetUnconnectedCount(False)))
    sys.stdout.flush(); os._exit(0)


if __name__ == "__main__":
    main()
