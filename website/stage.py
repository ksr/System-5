# Author: Claude (Anthropic) for Ken Rother, 2026
"""Copy the System-5 documents the website uses into stage/, keeping each file's repository path, so the links between
them keep working. The source is this repository's working tree, read only: nothing here writes to it.

The repository is private, so a visitor cannot follow a link to GitHub: what the site needs is copied here (the manual
and its PDFs, the board notes, the schematic PDFs, the photos and renders, resized), and hooks.py turns a link to any
other repository file into plain text.

Never on the site: third-party code and documents (in the private repository private-resources since 2026-11-15; the
reference/ in SKIP is for an old checkout), docs/website-2005 and docs/website-older (the old 1802
site, kept as it is), Claude's notes (CLAUDE.md), Eagle's backups, node_modules."""
import glob, os, re, shutil
from PIL import Image, ImageOps

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the repository this folder is in
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "stage")
GLOBS = ["BACKLOG.md", "docs/manual/*.md", "docs/manual/pdf/*.pdf", "hardware/*.md", "hardware/*/*.md",
         "hardware/*/kicad/README.md", "hardware/*/kicad/*/README.md", "hardware/*/kicad/*/DESIGN.md", "hardware/*/kicad/*/BOM.md", "hardware/*/kicad/*/schematic/*.pdf", "hardware/*/kicad/*/*.png",
         "hardware/*/kicad/*/reports/*.png", "hardware/*/eagle/*/photos/*", "hardware/*/kicad/*/photos/*", "hardware/board-notes/*.txt",
         "software/**/*.md", "embedded/**/*.md", "tools/kicad/sch/README.md",
         "software/elfos-v5/*/*.png"]            # the pictures a program's notes show (vgdemo's, 2026-11-20)
SKIP = re.compile(r"(^|/)(reference|website-2005|website-older|node_modules|eagle-backups|website-copy)(/|$)"
                  r"|(^|/)CLAUDE\.md$")
PHOTO_PX = 1400            # photos and renders are resized to fit this box
# every card is shown with its bus connector at the bottom (Ken, 2026-10-27): the photos taken another way round,
# with the turn (degrees anticlockwise) that brings the connector down
TURN = {"hardware/cpu/eagle/rev-a/photos/2026-10-07-front-1.jpg": 180,
        "hardware/io-1861-keyboard/eagle/rev-a/photos/2026-10-07-front-1.jpg": 180,
        "hardware/ide-cf/eagle/rev-a/photos/2005-03-front-1.jpg": 270,
        "hardware/memory/eagle/rev-b/photos/2026-10-07-front-1.jpg": 90,
        "hardware/video-6845/eagle/rev-b/photos/2026-10-07-front-1.jpg": 90}

# the KiCad renders: every card is drawn with its bus connector on the left (on the right seen from the bottom side),
# so a top view is turned 90 and a bottom view 270; the boards that do not plug into the bus (the
# backplane, hardware/bus, and the front panel, drawn the way it is read) are not turned
NOT_CARDS = ("bus", "front-panel")
RENDER = re.compile(r"^hardware/([^/]+)/kicad/[^/]+/[^/]+-render-(top|bottom)\.png$")


def render(src, dst, card, side):
    """A render: the empty space around the board cut off, the connector turned down, then resized."""
    im = Image.open(src).convert("RGBA")
    solid = im.getchannel("A").point(lambda a: 255 if a > 128 else 0).getbbox()     # without the faint shadow
    if solid: im = im.crop(solid)
    if card not in NOT_CARDS: im = im.rotate(90 if side == "top" else 270, expand=True)
    im.thumbnail((PHOTO_PX, PHOTO_PX))
    im.save(dst, optimize=True)


def copy(rel):
    src, dst = os.path.join(REPO, rel), os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    ext = os.path.splitext(rel)[1].lower()
    if ext in (".jpg", ".jpeg"):
        im = ImageOps.exif_transpose(Image.open(src))          # the camera's own rotation tag first
        if rel in TURN: im = im.rotate(TURN[rel], expand=True)
        im.thumbnail((PHOTO_PX, PHOTO_PX))
        im.convert("RGB").save(dst, quality=85, optimize=True)
    elif RENDER.match(rel):
        render(src, dst, *RENDER.match(rel).groups())
    elif ext == ".png":
        im = Image.open(src)
        if max(im.size) > PHOTO_PX:
            im.thumbnail((PHOTO_PX, PHOTO_PX))
            im.save(dst, optimize=True)
        else:
            shutil.copy2(src, dst)
    else:
        shutil.copy2(src, dst)


shutil.rmtree(OUT, ignore_errors=True)
paths = set()
for g in GLOBS:
    paths |= {os.path.relpath(p, REPO) for p in glob.glob(os.path.join(REPO, g), recursive=True)}
n = 0
for rel in sorted(paths):
    if SKIP.search(rel) or not os.path.isfile(os.path.join(REPO, rel)): continue
    copy(rel); n += 1
# each KiCad revision's README is staged as notes.md, and so is a card's own kicad/README.md (VIDEO-G's, for its two
# boards, 2026-11-17); hooks.py points links to the README at notes.md. This was for Material's navigation.indexes,
# which took a README.md as the card section's own page and dropped it from the list under it; that feature is off
# since 2026-11-17 (mkdocs.yml), and notes.md stays so that the pages keep their addresses
for readme in (glob.glob(os.path.join(OUT, "hardware", "*", "kicad", "*", "README.md")) +
               glob.glob(os.path.join(OUT, "hardware", "*", "kicad", "README.md"))):
    os.rename(readme, os.path.join(os.path.dirname(readme), "notes.md"))
# the visitor home page (home.md here) is the site's index; the repository README becomes "The repository" page
# (links to README.md from other documents are pointed at it by hooks.py)
shutil.copy2(os.path.join(HERE, "home.md"), os.path.join(OUT, "index.md")); n += 1
shutil.copy2(os.path.join(REPO, "README.md"), os.path.join(OUT, "repository.md")); n += 1
print("staged %d files" % n)
