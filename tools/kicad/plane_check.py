#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-19
"""Check the power planes of a board (zones on inner copper layers), on a refilled copy:
each plane is one continuous piece, every pad of its net reaches the fill, no pad of another net sits in it, and no
track runs on a plane layer. Run with KiCad's Python: plane_check.py <board.kicad_pcb>   exit 1 on a failure."""
import sys, os, shutil, tempfile
import pcbnew
src = sys.argv[1]; tmp = os.path.join(tempfile.mkdtemp(), "b.kicad_pcb"); shutil.copy(src, tmp)
b = pcbnew.LoadBoard(tmp); pcbnew.ZONE_FILLER(b).Fill(b.Zones()); ok = True
inner = [z for z in b.Zones() if not z.GetIsRuleArea() and b.GetLayerName(z.GetFirstLayer()).startswith("In")]
if not inner: print("no planes (no zones on inner layers)"); sys.stdout.flush(); os._exit(0)
for z in inner:
    lid = z.GetFirstLayer(); L = b.GetLayerName(lid); net = z.GetNetname(); poly = z.GetFilledPolysList(lid)
    pads = [(fp.GetReference(), p) for fp in b.GetFootprints() for p in fp.Pads()]
    miss = [r + "." + p.GetNumber() for r, p in pads if p.GetNetname() == net
            and not poly.Collide(p.GetPosition(), int(p.GetSize(pcbnew.F_Cu).x / 2) + pcbnew.FromMM(0.45))]
    short = [r + "." + p.GetNumber() for r, p in pads if p.GetNetname() not in (net, "") and poly.Contains(p.GetPosition())]
    trk = sum(1 for t in b.GetTracks() if t.GetLayer() == lid and t.Type() == pcbnew.PCB_TRACE_T)
    good = poly.OutlineCount() == 1 and not miss and not short and not trk; ok &= good
    print("%s %s plane %s: %d piece(s), %d %s pads all reach it: %s, other-net pads inside: %s, tracks on the layer: %d"
          % ("PASS" if good else "FAIL", L, net, poly.OutlineCount(), sum(1 for r, p in pads if p.GetNetname() == net), net,
             "yes" if not miss else "NO %s" % miss[:8], short[:8] or "none", trk))
sys.stdout.flush(); os._exit(0 if ok else 1)
