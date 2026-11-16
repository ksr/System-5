#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-15
"""Make the public System-5 repository (github.com/ksr/System-5) from this one.

    python3 tools/public/export.py                       build the public tree in a temporary folder and scan it
    python3 tools/public/export.py --out ../System-5     ... and make ../System-5 hold exactly that tree
    python3 tools/public/export.py --out ../System-5 --commit "message"     ... and commit it there

ksr/elf stays the working repository: it keeps Claude's notes and the history of the third-party files. ksr/System-5
is a copy of its publishable files, made by this program from a commit (--ref, default HEAD, so nothing uncommitted
is ever published). The program never pushes: Ken pushes, after looking at what it made.

1. The files of the commit, minus PRIVATE below.
2. The files in tools/public/overrides/ in place of the working ones (the Codespace set-up without the private
   repository and Elf/OS v5).
3. The scan. Any finding stops it, unless ALLOW below names it with a reason: a file of the third-party folders that
   moved to private-resources on 2026-11-15; secrets (private keys, tokens, passwords); email addresses; phone
   numbers; a GPS position in a photo; reserved-rights and do-not-distribute notices; a file over 50 MB. Text inside
   zips and inside PDFs' compressed streams is scanned too; of an image, only its metadata (its pixels would match by
   chance). Paths under /Users/ are counted, not stopped (KiCad and Eagle write where their files were: harmless).
4. With --out, the folder is made to hold exactly the tree (git init on first use); with --commit, it is committed.
"""
import argparse, os, re, shutil, subprocess, sys, tarfile, tempfile, zipfile, zlib

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
OVERRIDES = os.path.join(ROOT, "tools", "public", "overrides")
MARK = "system5-public-export"            # in the output's .git/: this program made that folder and may empty it

PRIVATE = [                               # kept out of the public repository
    "CLAUDE.md",                          # the working notes for Claude sessions (Ken, 2026-11-15)
    "docs/.removed-dups.txt",             # the list of duplicates left out of the old website copy
    ".github/workflows/website.yml",      # the website is built and published from ksr/elf
    "tools/public/overrides/",            # copied over the working files, not as themselves
]
MOVED = ["reference/", "firmware/elfos-install-rom/", "firmware/system4-tiny-basic-rom/", "software/rcasm-mac-build/",
         "software/disktool/", "hardware/memory/eagle/rev-b/bringup/2026-10-30-eprom-ic5"]   # third-party: never

SECRETS = [(re.compile(p), what) for p, what in [
    (rb"-----BEGIN [A-Z ]*PRIVATE KEY-----", "a private key"),
    (rb"\bgh[pousr]_[A-Za-z0-9]{36,}", "a GitHub token"),
    (rb"\bgithub_pat_[A-Za-z0-9_]{22,}", "a GitHub token"),
    (rb"\bAKIA[0-9A-Z]{16}\b", "an AWS key"),
    (rb"\bAIza[0-9A-Za-z_-]{35}", "a Google API key"),
    (rb"\bxox[abposr]-[A-Za-z0-9-]{10,}", "a Slack token"),
    (rb"\bsk_live_[0-9A-Za-z]{16,}", "a payment key"),
    (rb"(?i)\b(password|passwd|secret|api[_-]?key|auth[_-]?token)\b\s*[:=]\s*['\"][^'\"\s]{6,}['\"]", "a password or key"),
]]
EMAIL = re.compile(rb"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
PHONE = re.compile(rb"(?<![\w.$#-])(?:\(\d{3}\) ?|\d{3}[-. ])\d{3}[-.]\d{4}(?![\w.-])")
RIGHTS = re.compile(rb"(?i)all right[s] reserved|do not distribut[e]|not for (?:re)?distributio[n]|confidentia[l]|proprietar[y]")
IMAGES = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".heic", ".webp"}
USERS = re.compile(rb"/Users/[A-Za-z0-9._-]+")
DATA = {".gbr", ".gbl", ".gtl", ".gbs", ".gts", ".gbo", ".gto", ".gko", ".gbp", ".gtp", ".gm1", ".g1", ".g2", ".drl",
        ".xln", ".kicad_pcb", ".kicad_sch", ".kicad_pro", ".kicad_prl", ".kicad_sym", ".kicad_mod", ".net", ".hex",
        ".lst", ".rpt", ".pos", ".svg", ".dsn", ".ses", ".sym", ".ps", ".eps", ".rom", ".bin", ".img", ".lbr", ".brd",
        ".sch", ".pdf", ".zip", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".step", ".wrl", ".dri", ".gpi", ".cmp",
        ".sol", ".stc", ".sts", ".plc", ".pls", ".crc", ".crs"}    # numbers in these are data, not phone numbers
BIG = 50 * 1024 * 1024
ALLOW = [  # (rule, path pattern, matched-text pattern, why): findings checked by hand and left in
    ("email", r"^hardware/libraries/eagle/library/74xx-eu\.lbr$", r"^librarian@cadsoft\.de$",
     "CadSoft's library contact address, inside their own Eagle library (2026-11-15)"),
]


def tree(ref, stage):
    """the commit's files into stage, minus PRIVATE, plus the overrides; the list of findings so far"""
    p = subprocess.Popen(["git", "-C", ROOT, "archive", "--format=tar", ref], stdout=subprocess.PIPE)
    with tarfile.open(fileobj=p.stdout, mode="r|") as t:
        t.extractall(stage, **({"filter": "data"} if hasattr(tarfile, "data_filter") else {}))
    if p.wait(): sys.exit("git archive %s failed" % ref)
    found = []
    for rel in files(stage):
        if any(rel == m or rel.startswith(m) for m in MOVED):
            found.append(("third-party", rel, rel))
    for rel in PRIVATE:
        p = os.path.join(stage, rel)
        if os.path.isdir(p): shutil.rmtree(p)
        elif os.path.lexists(p): os.remove(p)
    for rel in files(OVERRIDES) if os.path.isdir(OVERRIDES) else []:
        dst = os.path.join(stage, rel)
        if not os.path.exists(dst):
            sys.exit("tools/public/overrides/%s replaces nothing: %s is not in %s" % (rel, rel, ref))
        shutil.copy2(os.path.join(OVERRIDES, rel), dst)
    return found


def files(top):
    for d, dirs, fs in os.walk(top):
        dirs[:] = [x for x in dirs if x != ".git"]
        for f in fs:
            yield os.path.relpath(os.path.join(d, f), top)


def pdf_text(b):
    """the PDF's own bytes and every Flate stream it holds, inflated"""
    out = [b]
    for m in re.finditer(rb"stream\r?\n", b):
        try: out.append(zlib.decompressobj().decompress(b[m.end():m.end() + 4_000_000]))
        except zlib.error: pass
    return b"\n".join(out)


def scan_bytes(rel, b, found, users):
    ext = os.path.splitext(rel)[1].lower()
    if ext == ".pdf": b = pdf_text(b)
    for rx, what in SECRETS:
        for m in rx.finditer(b): found.append(("secret: " + what, rel, m.group(0)))
    for m in EMAIL.finditer(b): found.append(("email", rel, m.group(0)))
    if ext not in DATA and b"\0" not in b[:8192]:
        for m in PHONE.finditer(b): found.append(("phone", rel, m.group(0)))
    for m in RIGHTS.finditer(b): found.append(("rights", rel, m.group(0)))
    users[rel] = users.get(rel, 0) + len(USERS.findall(b))


def image(rel, path, found, users):
    """an image's metadata: a GPS position, and the text it carries (EXIF strings, PNG text) scanned like a file's"""
    try:
        from PIL import Image
        with Image.open(path) as im:
            exif = im.getexif(); g = exif.get_ifd(0x8825)
            text = [v for v in list(exif.values()) + list(im.info.values()) if isinstance(v, (str, bytes))]
        if g and (2 in g or 4 in g): found.append(("GPS position", rel, str(g.get(2)) + " " + str(g.get(4))))
        scan_bytes(rel + " (metadata)", b"\n".join(v.encode("utf-8", "replace") if isinstance(v, str) else v
                                                   for v in text), found, users)
    except Exception as e:                                  # an image PIL cannot read is looked at by hand
        found.append(("unreadable image", rel, str(e)[:80]))


def scan(stage):
    found, users = [], {}
    for rel in sorted(files(stage)):
        path = os.path.join(stage, rel)
        if os.path.islink(path): continue
        if os.path.getsize(path) > BIG: found.append(("over 50 MB", rel, str(os.path.getsize(path))))
        if os.path.splitext(rel)[1].lower() in IMAGES:
            image(rel, path, found, users); continue
        b = open(path, "rb").read()
        scan_bytes(rel, b, found, users)
        if rel.lower().endswith(".zip"):
            try:
                with zipfile.ZipFile(path) as z:
                    for n in z.namelist():
                        inner = rel + "!" + n
                        if any(m in n for m in MOVED): found.append(("third-party", inner, n))
                        if not n.endswith("/") and os.path.splitext(n)[1].lower() not in IMAGES:
                            scan_bytes(inner, z.read(n), found, users)
            except zipfile.BadZipFile:
                found.append(("unreadable zip", rel, ""))
    allowed = [f for f in found if any(r == f[0] and re.search(p, f[1]) and re.search(t, f[2].decode("latin-1")
               if isinstance(f[2], bytes) else f[2]) for r, p, t, _ in ALLOW)]
    return [f for f in found if f not in allowed], allowed, {k: v for k, v in users.items() if v}


def sync(stage, out):
    """make out hold exactly the files in stage (its .git kept)"""
    out = os.path.abspath(out)
    if out == ROOT or ROOT.startswith(out + os.sep) or out.startswith(ROOT + os.sep):
        sys.exit("--out %s is this repository or around it: refused" % out)
    if not os.path.isdir(os.path.join(out, ".git")):
        if os.path.exists(out) and os.listdir(out): sys.exit("--out %s is a folder this program did not make: refused" % out)
        os.makedirs(out, exist_ok=True)
        subprocess.run(["git", "init", "-q", "-b", "main", out], check=True)
        open(os.path.join(out, ".git", MARK), "w").write("made by elf's tools/public/export.py\n")
    elif not os.path.exists(os.path.join(out, ".git", MARK)):
        sys.exit("--out %s is a git repository this program did not make (no .git/%s): refused" % (out, MARK))
    for name in os.listdir(out):
        if name == ".git": continue
        p = os.path.join(out, name)
        shutil.rmtree(p) if os.path.isdir(p) and not os.path.islink(p) else os.remove(p)
    for name in os.listdir(stage):
        s, d = os.path.join(stage, name), os.path.join(out, name)
        shutil.copytree(s, d, symlinks=True) if os.path.isdir(s) and not os.path.islink(s) else shutil.copy2(s, d, follow_symlinks=False)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--ref", default="HEAD"); ap.add_argument("--out"); ap.add_argument("--commit", metavar="MESSAGE")
    a = ap.parse_args()
    sha = subprocess.run(["git", "-C", ROOT, "rev-parse", "--short", a.ref], capture_output=True, text=True, check=True).stdout.strip()
    with tempfile.TemporaryDirectory() as tmp:
        stage = os.path.join(tmp, "System-5")
        found = tree(a.ref, stage)
        n = sum(1 for _ in files(stage))
        size = sum(os.path.getsize(os.path.join(stage, f)) for f in files(stage))
        more, allowed, users = scan(stage)
        found += more
        print("elf %s -> %d files, %.1f MB" % (sha, n, size / 1e6))
        print("allowed (checked by hand, ALLOW): %d" % len(allowed))
        print("paths under /Users/ (harmless): %d in %d files" % (sum(users.values()), len(users)))
        if found:
            print("FINDINGS: %d" % len(found))
            for rule, rel, text in found[:200]:
                print("  %-26s %s: %s" % (rule, rel, (text.decode("latin-1") if isinstance(text, bytes) else text)[:100]))
            sys.exit(1)
        print("scan: clean")
        if a.out:
            out = sync(stage, a.out)
            subprocess.run(["git", "-C", out, "add", "-A"], check=True)
            st = subprocess.run(["git", "-C", out, "status", "--short"], capture_output=True, text=True).stdout
            print("%s: %d changes staged" % (out, len(st.splitlines())))
            if a.commit and st:
                subprocess.run(["git", "-C", out, "commit", "-q", "-m", a.commit], check=True)
                print(subprocess.run(["git", "-C", out, "log", "--oneline", "-1"], capture_output=True, text=True).stdout.strip())


if __name__ == "__main__":
    main()
