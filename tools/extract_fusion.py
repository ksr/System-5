#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-06
"""Pull the Eagle XML out of Fusion's own .fsch / .fbrd files, into fusion-export/ under the plain design name.

A Fusion electronics document (.fsch schematic, .fbrd board) is a zip. Inside it,
  <Schematic|PCB> Document Asset[Active]/electron.BlobParts/ExtFile.<uuid>.sch|.brd
is the design as Eagle 9 XML - the same file Fusion's "Export -> Eagle" would write, except that its <layer> entries
carry Fusion's colour attributes (tools/eagle_to_kicad_all.py adds the 'color' KiCad wants).

usage: extract_fusion.py FILE.fsch|FILE.fbrd ...     e.g.  hardware/ide-cf/eagle/rev-a/ide1-a-export.f*
The output name is the revision folder's own .sch design name when there is exactly one (IO-exported.fsch ->
fusion-export/Video.sch), else the file name less '-export'. The .fsch/.fbrd files are left where they are.
"""
import os, sys, zipfile


def extract(path):
    ext = {".fsch": ".sch", ".fbrd": ".brd"}[os.path.splitext(path)[1].lower()]
    with zipfile.ZipFile(path) as z:
        inner = [n for n in z.namelist() if "/electron.BlobParts/ExtFile." in n and n.lower().endswith(ext)]
        if len(inner) != 1: sys.exit("%s: expected one embedded Eagle %s, found %d" % (path, ext, len(inner)))
        data = z.read(inner[0])
    if b"<eagle" not in data[:400]: sys.exit("%s: the embedded file is not Eagle XML" % path)
    folder = os.path.dirname(os.path.abspath(path))
    originals = [f[:-4] for f in os.listdir(folder) if f.endswith(".sch")]
    if len(originals) == 1: name = originals[0]                  # the revision's own design name (IO-exported.fsch -> Video)
    else:
        name = os.path.splitext(os.path.basename(path))[0]
        if name.endswith("-export"): name = name[:-len("-export")]
    out_dir = os.path.join(folder, "fusion-export"); os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, name + ext)
    with open(out, "wb") as f: f.write(data)
    print("%s -> %s (%d bytes)" % (path, os.path.relpath(out), len(data)))


if __name__ == "__main__":
    if len(sys.argv) < 2: sys.exit(__doc__)
    for p in sys.argv[1:]: extract(p)
