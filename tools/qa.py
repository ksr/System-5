#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-20
"""qa.py -- the System-5 QA entry points behind `make qa-quick`, `make qa` and `make qa-fresh`
(the same three targets as in YACC1-D, p8x and P32W; chosen 2026-11-20).

    python3 tools/qa.py quick    # ~4 min: before every commit; pcb-check's tests = for the boards
    python3 tools/qa.py full     # ~50 min: the whole suite, before an order or a release
    python3 tools/qa.py fresh    # ~5 s: every committed firmware/software build against a fresh one

Three rules hold for all three:
  - nothing tracked changes: the working tree's tracked files are compared before and after
    (git status), and a run that changed one fails, naming it. New untracked files that are
    not ignored are listed too (a test leaving scratch behind);
  - a skip is not a pass: a step that prints a SKIP line, or a unittest run that skipped a
    test, is reported as skipped, and the run does not end in OK;
  - every step runs, even after one fails, and the summary gives each step's result and time.

`fresh` never builds in the repository: it copies the tracked files, as they are on disk now,
into a temporary git repository (with ../private-resources beside it, as here), runs the
builders there, and asks that copy's git what changed.

Some tests read ../private-resources/elf/ (the Elf/OS v5 card image, Riley's BIOS): without it
beside this repository they fail or skip, and the run says so.
"""
import os, re, shutil, subprocess, sys, tempfile, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

S5 = "software/s5emu"
QUICK = [
    ("s5emu: CPU", S5, "python3 -m unittest tests.test_cpu"),
    ("s5emu: timing", S5, "python3 -m unittest tests.test_timing"),
    ("s5emu: VIDEO-G", S5, "python3 -m unittest tests.test_videog"),
    ("s5emu: web", S5, "python3 -m unittest tests.test_web"),
    ("busdrv: host tool", "software/busdrv", "python3 -m unittest test_s5busdrv"),
    ("busdrv: BUSDRV-C", "software/busdrv", "python3 -m unittest test_busdrv_c"),
    ("busdrv: bring-up", "software/busdrv", "python3 -m unittest test_bringup"),
    ("busdrv: short finder", "software/busdrv", "python3 -m unittest test_shorts"),
    ("s5emu: bus link, BUSDRV-C", S5, "python3 -m unittest tests.test_buslink_c"),
    ("preorder pad drawing", ".", "python3 -m unittest tools.test_preorder_draw"),
    ("Elf/OS v5 programs as built", ".", "python3 software/elfos-v5/build.py --check"),
    ("VIDEO-G PS/2 firmware co-sim", ".", "sh embedded/video-g-ps2/sim/run.sh"),
    ("VIDEO-G TEXT netlist proof", ".", "python3 hardware/video-g/kicad/common/checknet.py hardware/video-g/kicad/text-1.0"),
    ("VIDEO-G GFX netlist proof", ".", "python3 hardware/video-g/kicad/common/checknet.py hardware/video-g/kicad/gfx-1.0"),
]
FULL = QUICK + [
    ("s5emu: machine", S5, "python3 -m unittest tests.test_machine"),
    ("s5emu: gate-level hardware", S5, "python3 -m unittest tests.test_hw"),
    ("s5emu: VIDEO-G hardware", S5, "python3 -m unittest tests.test_hw_videog"),
    ("s5emu: VIDEO-G keyboard hardware", S5, "python3 -m unittest tests.test_hw_videokbd"),
    ("s5emu: the new card set", S5, "python3 -m unittest tests.test_newset"),
    ("GBASIC", "software/gbasic/tests", "python3 test_gbasic.py"),
    ("HBIOS v1.0.5 disassembly", ".", "python3 firmware/hbios/v1.0.5/check_disasm.py"),
]
NOT_IN_FULL = [  # said at the end of every full run, so their absence is never mistaken for a pass
    "the boards' own gen/build.sh flows and pcb-check (run pcb-check on a board before its order)",
    "the website build (website/build.sh installs from PyPI)",
]

# (what, folder in the copy, command): each writes its outputs in place, as in the repository
GENERATORS = [
    ("HBIOS v1.0.5", ".", "python3 firmware/hbios/v1.0.5/build.py"),
    ("HBIOS v1.0.6", ".", "python3 firmware/hbios/v1.0.6/build.py"),
    ("HBIOS v1.0.7", ".", "python3 firmware/hbios/v1.0.7/build.py"),
    ("HBIOS v1.0.8", ".", "python3 firmware/hbios/v1.0.8/build.py"),
    ("HBIOS VIDEO-G (and s5emu/roms)", ".", "python3 firmware/hbios/video-g/build.py"),
    ("VIDEO-G character generator", ".", "python3 firmware/video-g-chargen/build.py"),
    ("GBASIC (gen_tables + assemble)", ".", "python3 software/gbasic/build.py"),
    ("Elf/OS v5 programs", ".", "python3 software/elfos-v5/build.py"),
]
FRESH_NOT_CHECKED = [
    "the KiCad boards and their PDFs (gen/build.sh routes with Freerouting; pcb-check checks a board before its order)",
    "the schematic book (tools/kicad/sch/build_all.sh)",
]
SKIP = re.compile(r"(^|:\s*)SKIP\b|\(skipped=\d+\)")   # a SKIP line, or unittest's "OK (skipped=2)"
PDF_VOLATILE = re.compile(rb"(/(?:CreationDate|ModDate)\s*\()[^)]*(\))|(/ID\s*\[)[^\]]*(\])"
                          rb"|(<xmp:(?:CreateDate|ModifyDate|MetadataDate)>)[^<]*")

def git(*a, cwd=ROOT):
    return subprocess.run(["git"] + list(a), cwd=cwd, capture_output=True, text=True).stdout

def tree_state():
    """(tracked files changed or deleted, with their contents' hashes) and the untracked files
    git does not ignore"""
    changed = {}
    for line in git("status", "--porcelain", "--untracked-files=no").splitlines():
        path = line[3:]
        full = os.path.join(ROOT, path)
        changed[path] = git("hash-object", full).strip() if os.path.isfile(full) else "gone"
    untracked = set(git("ls-files", "--others", "--exclude-standard").splitlines())
    return changed, untracked

def stream(cmd, cwd):
    """run a shell command, echoing its output; return (exit status, the SKIP lines)"""
    p = subprocess.Popen(cmd, shell=True, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True, errors="replace")
    skips = []
    for line in p.stdout:
        sys.stdout.write("    " + line); sys.stdout.flush()
        if SKIP.search(line):
            skips.append(line.strip())
    return p.wait(), skips

def run(tier):
    steps = QUICK if tier == "quick" else FULL
    before, untracked0 = tree_state()
    results, t0 = [], time.time()
    for what, folder, cmd in steps:
        print("\n== %s  (%s: %s)" % (what, folder, cmd), flush=True)
        t = time.time()
        rc, skips = stream(cmd, os.path.join(ROOT, folder))
        status = "FAIL" if rc else ("SKIP" if skips else "PASS")
        results.append((status, what, time.time() - t, skips))
    after, untracked1 = tree_state()
    touched = sorted(p for p in set(before) | set(after) if before.get(p) != after.get(p))
    leftovers = sorted(untracked1 - untracked0)
    print("\n" + "=" * 72 + "\nqa %s: %d steps in %.0f min" % (tier, len(steps), (time.time() - t0) / 60))
    for status, what, secs, skips in results:
        print("  %-4s  %-44s %6.0f s" % (status, what, secs))
        for s in skips:
            print("          skipped: " + s[:100])
    if touched:
        print("  FAIL  tracked files changed by the run (they must not be):")
        for p in touched: print("          " + p)
    if leftovers:
        print("  WARN  new untracked files left behind (not ignored):")
        for p in leftovers[:20]: print("          " + p)
    if tier == "full":
        print("  not in qa: " + "; ".join(NOT_IN_FULL))
    bad = [r for r in results if r[0] != "PASS"]
    if bad or touched:
        print("qa %s: NOT OK (%d failed, %d skipped%s)" % (tier, sum(r[0] == "FAIL" for r in results),
              sum(r[0] == "SKIP" for r in results), ", tracked files changed" if touched else ""))
        return 1
    print("qa %s: OK" % tier)
    return 0

def pdf_same(a, b):
    with open(a, "rb") as fa, open(b, "rb") as fb:
        sub = lambda m: b"".join(g for g in m.groups() if g)
        return PDF_VOLATILE.sub(sub, fa.read()) == PDF_VOLATILE.sub(sub, fb.read())

def fresh():
    tmp = tempfile.mkdtemp(prefix="elf-qa-fresh-")
    copy = os.path.join(tmp, "elf")
    # the builds read ../private-resources/elf/ (Riley's BIOS, the Elf/OS v5 image), as in ~/Developer
    pr = os.path.join(os.path.dirname(ROOT), "private-resources")
    if os.path.isdir(pr):
        os.symlink(pr, os.path.join(tmp, "private-resources"))
    probs, notes = [], []
    try:
        for rel in git("ls-files", "-z").split("\0"):
            src = os.path.join(ROOT, rel)
            if rel and os.path.isfile(src):
                os.makedirs(os.path.dirname(os.path.join(copy, rel)), exist_ok=True)
                shutil.copy2(src, os.path.join(copy, rel))
        git("init", "-q", cwd=copy); git("add", "-A", cwd=copy)
        git("-c", "user.name=qa", "-c", "user.email=qa@localhost", "commit", "-qm", "the tree as it is", cwd=copy)
        for what, folder, cmd in GENERATORS:
            r = subprocess.run(cmd, shell=True, cwd=os.path.join(copy, folder), capture_output=True, text=True)
            print("  %-4s  %s" % ("ran" if r.returncode == 0 else "FAIL", what), flush=True)
            if r.returncode:
                probs.append("%s failed: %s" % (what, (r.stdout + r.stderr).strip().splitlines()[-1:]))
        stale = []
        for line in git("status", "--porcelain", cwd=copy).splitlines():
            path = line[3:].strip('"')
            if line.startswith("??"):
                notes.append("made by a generator, not committed: " + path)
            elif path.endswith(".pdf") and os.path.exists(os.path.join(copy, path)):
                orig = os.path.join(tmp, "orig.pdf")
                with open(orig, "wb") as fh:
                    fh.write(subprocess.run(["git", "show", "HEAD:" + path], cwd=copy, capture_output=True).stdout)
                if not pdf_same(orig, os.path.join(copy, path)):
                    stale.append(path)
            else:
                stale.append(path)
        for p in stale:
            probs.append("stale: %s (its generator makes it differently)" % p)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n" + "=" * 72)
    for n in notes: print("  NOTE  " + n)
    for n in FRESH_NOT_CHECKED: print("  not checked: " + n)
    for p in probs: print("  NOT OK  " + p)
    print("qa fresh: %s" % ("OK" if not probs else "NOT OK (%d)" % len(probs)))
    return 1 if probs else 0

if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else ""
    if what in ("quick", "full"): sys.exit(run(what))
    if what == "fresh": sys.exit(fresh())
    sys.exit("usage: tools/qa.py quick|full|fresh")
