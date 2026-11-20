#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-18
"""fp_update.py BOARD.kicad_pcb REF FOOTPRINT.kicad_mod | fp_update.py BOARD.kicad_pcb --lib LIBRARY.pretty - bring one
footprint of a routed board, or every one from a library folder, up to its library file, where only the part's drawing changed: its body (F.Fab), its courtyard (F.CrtYd), its 3D models and its description.
Pads, nets, position, texts and every track stay as they are, so the board needs no new route.

Written for the cards' bus connector (2026-11-18): the C30 / C36 footprints had pads and a courtyard round them, but
not the part. The part is a single-row right-angle header, and its plastic body lies on the board between the pads and
the card edge (Ken's photos of MEM3-E and BUSDRV-B show it). With no body drawn, the silkscreen placer and pcb-check
both took that strip for free board, and "J1 BUS" was printed under the header on every new card.

    text, n = fp_update.update(board_text, "J1", open("lib.pretty/C36.kicad_mod").read())   # the board's text, updated
    text, n = fp_update.update_all(board_text, {"J1": c36_text, "J2": rca_text, ...})         # several parts, one pass
    fp_update.refs(board_text)                                                               # {reference: "lib:footprint"}
    fp_update.py BOARD.kicad_pcb J1 lib.pretty/C36.kicad_mod                                 # one part, on a file
    fp_update.py BOARD.kicad_pcb --lib lib.pretty                                            # every part from that library

Works on the file's text (a footprint's drawing is stored in the footprint's own coordinates, not turned or moved, so
the library's forms go in as they are); KiCad writes it out in its own layout the next time the board is saved. Plain
Python.
"""
import re, sys

SHAPES = ("(fp_rect", "(fp_line", "(fp_circle", "(fp_arc", "(fp_poly")
LAYERS = ('(layer "F.Fab")', '(layer "F.CrtYd")')


def forms(text):
    """the forms directly inside the outermost one (tools/kicad/kicad_route.py's top_forms, without pcbnew)"""
    out, d, ins, start, j = [], 0, False, None, text.index("(") + 1
    while j < len(text):
        c = text[j]
        if ins:
            if c == "\\": j += 1
            elif c == '"': ins = False
        elif c == '"': ins = True
        elif c == "(":
            if d == 0: start = j
            d += 1
        elif c == ")":
            if d == 0: break
            d -= 1
            if d == 0: out.append(text[start:j + 1])
        j += 1
    return out


def drawing(form):
    """is this form of a footprint part of its drawing: a shape on F.Fab or F.CrtYd, a 3D model, the description"""
    return (form.startswith(SHAPES) and any(l in form for l in LAYERS)) or form.startswith(("(model", "(descr"))


def refs(board):
    """{reference: "library:footprint"} for every footprint on the board (its text)"""
    out = {}
    for f in forms(board):
        if f.startswith("(footprint"):
            m = re.search(r'\(property\s+"Reference"\s+"([^"]*)"', f)
            if m: out[m.group(1)] = re.match(r'\(footprint\s+"([^"]*)"', f).group(1)
    return out


def update_all(board, mods):
    """the board's text with the drawing of each footprint in mods {reference: its library file's text} replaced by
    that file's -> (text, n): n forms taken out in all, the libraries' put in. The shapes go in without the library's
    uuids (KiCad gives each a new one when it loads the board: several parts may share a footprint, and a board's
    uuids must differ)"""
    new = {ref: [re.sub(r'\s*\(uuid\s+"[^"]*"\)', "", f) for f in forms(mod) if drawing(f)] for ref, mod in mods.items()}
    out, done, seen = [], 0, set()
    for f in forms(board):
        m = re.search(r'\(property\s+"Reference"\s+"([^"]*)"', f) if f.startswith("(footprint") else None
        if m and m.group(1) in new:
            ref = m.group(1); seen.add(ref)
            head = re.match(r'\(footprint\s+"[^"]*"', f).group(0)
            kids = forms(f); keep = [k for k in kids if not drawing(k)]
            at = next((i for i, k in enumerate(keep) if k.startswith("(pad")), len(keep))    # shapes before the pads,
            shapes = [k for k in new[ref] if k.startswith(SHAPES + ("(descr",))]               # models at the end
            f = head + "\n\t\t" + "\n\t\t".join(keep[:at] + shapes + keep[at:] + [k for k in new[ref] if k.startswith("(model")]) + "\n\t)"
            done += len(kids) - len(keep)
        out.append(f)
    if set(new) - seen:
        raise SystemExit("fp_update: no footprint %s on the board" % ", ".join(sorted(set(new) - seen)))
    return "(kicad_pcb\n\t" + "\n\t".join(out) + "\n)\n", done


def update(board, ref, mod):
    """the board's text with footprint REF's drawing replaced by the library file's (mod, its text) -> (text, n)"""
    return update_all(board, {ref: mod})


if __name__ == "__main__":
    import os
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    pcb, ref, modfile = sys.argv[1:]
    board = open(pcb).read()
    if ref == "--lib":                                    # every part whose footprint is "<folder's name>:<a file in it>"
        lib = os.path.basename(os.path.normpath(modfile)); lib = lib[:-len(".pretty")] if lib.endswith(".pretty") else lib
        mods = {}
        for r, fpid in refs(board).items():
            f = os.path.join(modfile, fpid.split(":")[-1] + ".kicad_mod")
            if fpid.split(":")[0] == lib and os.path.exists(f):
                mods[r] = open(f).read()
        if not mods:
            sys.exit("fp_update: no part on the board has a footprint from %s" % modfile)
        text, n = update_all(board, mods)
        what = "%d parts (%s)" % (len(mods), " ".join(sorted(mods)[:12]) + (" ..." if len(mods) > 12 else ""))
    else:
        text, n = update(board, ref, open(modfile).read()); what = ref
    open(pcb, "w").write(text)
    print("fp_update: %s on %s: %d form(s) of their drawing replaced from %s" % (what, pcb, n, modfile))
