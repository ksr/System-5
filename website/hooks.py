# Author: Claude (Anthropic) for Ken Rother, 2026
"""MkDocs hook for the System-5 website.

Links: the repository is private, so a relative link to a repository file that is not on the site (a source, a board
file, a zip) cannot go to GitHub: it becomes plain text (its link text). A link to a directory goes to that
directory's README page when the site has one; a link to the repository README goes to "The repository" page.

Menu: each card's section under Cards gets one item per KiCad revision (hardware/<card>/kicad/<rev>/README.md, staged
as notes.md, or its DESIGN.md for a design in progress), named
with what hardware/FABRICATED.md says about it (in use, made, ordered, scrap, not ordered, design only): the word
comes from the heading of the table the board is in, except that a row saying SCRAP is "scrap" and a row whose
note says "**In use" is "in use" (a 2026 board that is built and running, not just ordered).

Pictures (Ken, 2026-11-23): each card chapter, revision page and VIDEO-G page that shows no picture of its own gets
one under its title: a photo of that revision when there is one, else its KiCad render, and the caption says which.
A photo added to the revision's photos/ folder takes the render's place by itself."""
import glob, os, posixpath, re, subprocess
from urllib.parse import unquote

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the repository this folder is in
LINK = re.compile(r'(!?)\[((?:[^\[\]]|\[[^\]]*\])*)\]\((<[^>]+>|[^)\s]+)((?:\s+"[^"]*")?)\)')
stats = {"plain": 0, "readme": 0, "photo": 0, "render": 0}

# the board names in FABRICATED.md's tables -> the card folder under hardware/
BOARD = [("Bus driver", "bus-driver"), ("Bus", "bus"), ("CPU", "cpu"), ("Memory", "memory"),
         ("6845 video", "video-6845"), ("IO panel", "io-panel"), ("Front panel", "front-panel"), ("IO", "io-1861-keyboard"), ("IDE", "ide-cf")]
# FABRICATED.md's section headings -> the word the menu shows
STATUS = [("Ordered 2026", "ordered"), ("Ordered", "made"), ("probably not ordered", "not ordered"),
          ("Design only", "design only")]


def fab_status():
    """{(card folder, revision): status} from the tables in hardware/FABRICATED.md."""
    out, status = {}, None
    for line in open(os.path.join(REPO, "hardware", "FABRICATED.md"), encoding="utf-8"):
        if line.startswith("## "):
            status = next((s for key, s in STATUS if key in line), None)
            continue
        cols = [c.strip() for c in line.split("|")]
        if not status or len(cols) < 4 or cols[1] in ("Board", "") or set(cols[1]) <= set("-"): continue
        card = next((folder for name, folder in BOARD if cols[1].startswith(name)), None)
        rev = cols[2].split()[0].lower() if cols[2] else ""
        if card and rev:
            out[(card, rev)] = "scrap" if "SCRAP" in line else "in use" if "**In use" in line else status
    return out


def on_config(config):
    """Add one item per KiCad revision to each card's section under Cards (CARD_OF names each section's folder)."""
    fab = fab_status()
    for top in config["nav"]:
        if not (isinstance(top, dict) and "Cards" in top): continue
        for section in top["Cards"]:
            (title, items), = section.items()
            if not isinstance(items, list): continue
            card = CARD_OF.get(title)
            if not card: continue
            for rdir in sorted(glob.glob(os.path.join(REPO, "hardware", card, "kicad", "*", ""))):
                folder = os.path.basename(os.path.dirname(rdir))
                # a revision's page: its README (staged as notes.md), else its DESIGN.md (a design in progress)
                if os.path.exists(os.path.join(rdir, "README.md")): page_name = "notes.md"
                elif os.path.exists(os.path.join(rdir, "DESIGN.md")): page_name = "DESIGN.md"
                else: continue
                rev = folder[4:] if folder.startswith("rev-") else folder
                status = fab.get((card, rev.lower()))
                name = rev.upper() if len(rev) == 1 else "-".join(w.capitalize() for w in rev.split("-")) if re.fullmatch(r"[a-z](-[a-z]+)+", rev) else rev
                label = "Rev %s" % name + (" (%s)" % status if status else "")      # (rev-b-clean is "Rev B-Clean", rev-b-clean-keyboard "Rev B-Clean-Keyboard")
                items.append({label: "hardware/%s/kicad/%s/%s" % (card, folder, page_name)})
    return config


# the Cards sections of mkdocs.yml -> their folder under hardware/
CARD_OF = {"Backplane and bus": "bus", "CPU card": "cpu", "Memory card": "memory", "6845 video card": "video-6845",
           "IO card (1861 + keyboard)": "io-1861-keyboard", "IDE / CF card": "ide-cf", "Bus driver card": "bus-driver",
           "IO panel card": "io-panel", "Front panel": "front-panel"}


# the card chapters with no picture of their own -> the revision they describe (the card in the machine)
CHAPTER = {"docs/manual/bus.md": ("bus", "rev-2009"), "docs/manual/cpu-card.md": ("cpu", "rev-a"),
           "docs/manual/io-card.md": ("io-1861-keyboard", "rev-a"), "docs/manual/ide-cf-card.md": ("ide-cf", "rev-a"),
           "docs/manual/video-6845-card.md": ("video-6845", "rev-b"), "docs/manual/memory-card.md": ("memory", "rev-e"),
           "docs/manual/bus-driver-card.md": ("bus-driver", "rev-b")}
VIDEO_G = [("video-g", "text-1.0"), ("video-g", "gfx-1.0")]
MONTHS = "January February March April May June July August September October November December".split()


def pictured(uri):
    """The (card, revision folder) pairs a page shows, or []."""
    if uri in CHAPTER: return [CHAPTER[uri]]
    if uri in ("hardware/video-g/DESIGN.md", "hardware/video-g/kicad/notes.md"): return VIDEO_G
    m = re.fullmatch(r"hardware/([^/]+)/kicad/([^/]+)/(?:notes|DESIGN|BOM)\.md", uri)
    return [m.groups()] if m else []


def photo_of(card, rev):
    """The photo that shows a revision's component side (a built board before a blank one), or None."""
    found = [os.path.relpath(p, REPO) for tool in ("kicad", "eagle")
             for p in sorted(glob.glob(os.path.join(REPO, "hardware", card, tool, rev, "photos", "*.jpg")))]
    for word in ("front", "built-component", "component", "silkscreen"):
        for p in found:
            if word in os.path.basename(p): return p
    return None


def render_of(card, rev):
    found = sorted(glob.glob(os.path.join(REPO, "hardware", card, "kicad", rev, "*-render-top.png")))
    return os.path.relpath(found[0], REPO) if found else None


def photo_date(path):
    m = re.match(r"(\d{4})-(\d\d)(?:-(\d\d))?", os.path.basename(path))
    if not m: return ""
    y, mo, d = m.groups()
    return ", " + " ".join(([str(int(d))] if d else []) + [MONTHS[int(mo) - 1], y])


def picture(card, rev, markdown, here):
    """The picture of one revision with its caption, as Markdown, or ""."""
    name = rev
    if card == "video-g": name = rev.split("-")[0].upper()
    elif rev.startswith("rev-"): name = "Rev " + "-".join(w.capitalize() for w in rev[4:].split("-"))
    src = photo_of(card, rev)
    if src:
        caption = "Photo: %s%s" % (name, photo_date(src))
        stats["photo"] += 1
    else:
        src = render_of(card, rev)
        if not src: return ""
        status = fab_status().get((card, rev[4:] if rev.startswith("rev-") else rev))
        if not status and re.search(r"\bnot (ordered|built)\b", markdown[:3000], re.I): status = "design only"
        caption = "KiCad render: %s" % name + {
            "design only": ", not built", "not ordered": ", not built", "ordered": ", ordered, no photo yet",
            "made": ", made, no photo", "in use": ", built, no photo yet",
            "scrap": ", as designed (the boards made were scrap)"}.get(status, "") + (
            ". A part with no 3D model shows as its outline or bare pads.")
        stats["render"] += 1
    return '![%s](<%s>){ width="420" }\n\n*%s*\n' % (caption.split(". ")[0], posixpath.relpath(src, here or "."), caption)


def add_pictures(markdown, uri):
    boards = pictured(uri)
    if not boards or re.search(r"!\[|<img", markdown): return markdown           # it has a picture of its own
    shown = "\n".join(filter(None, (picture(c, r, markdown, posixpath.dirname(uri)) for c, r in boards)))
    if not shown: return markdown
    return re.sub(r"(?m)^# .*$", lambda m: m.group(0) + "\n\n" + shown, markdown, count=1)


def on_page_markdown(markdown, page, config, files):
    markdown = add_pictures(markdown, page.file.src_uri)
    site = {f.src_uri for f in files}
    here = posixpath.dirname(page.file.src_uri)

    def fix(m):
        bang, text, target, title = m.groups()
        t = target[1:-1] if target.startswith("<") else target
        if re.match(r"^[a-z][a-z0-9+.-]*:", t, re.I) or t.startswith("#") or t.startswith("/"): return m.group(0)
        path, _, frag = t.partition("#")
        if not path: return m.group(0)
        resolved = posixpath.normpath(posixpath.join(here, unquote(path)))
        if resolved in site or resolved.startswith(".."): return m.group(0)
        if resolved == ".": resolved = ""
        stand_in = "repository.md" if resolved in ("", "README.md") else None
        if not stand_in and os.path.isdir(os.path.join(REPO, resolved)):
            stand_in = posixpath.join(resolved, "README.md")
        if stand_in and stand_in not in site and posixpath.join(posixpath.dirname(stand_in), "notes.md") in site:
            stand_in = posixpath.join(posixpath.dirname(stand_in), "notes.md")     # a KiCad revision's README
        if not stand_in and re.fullmatch(r"hardware/[^/]+/kicad/(?:[^/]+/)?README\.md", resolved):  # a revision's or a card's
            stand_in = posixpath.join(posixpath.dirname(resolved), "notes.md")
        if stand_in and stand_in in site and not bang:
            stats["readme"] += 1
            return "[%s](<%s>%s)" % (text, posixpath.relpath(stand_in, here or ".") + ("#" + frag if frag else ""), title)
        if not os.path.exists(os.path.join(REPO, resolved)): return m.group(0)       # leave MkDocs to report it
        stats["plain"] += 1
        return text if not bang else "*%s*" % text if text else ""

    return LINK.sub(fix, markdown)


def on_post_build(config):
    print("hooks: %d links to files not on the site made plain text (the repository is private); %d links to "
          "directories or the README go to their site page" % (stats["plain"], stats["readme"]))
    print("hooks: %d photos and %d KiCad renders added under page titles" % (stats["photo"], stats["render"]))
    for p in sorted(glob.glob(os.path.join(REPO, "hardware", "*", "kicad", "*", "*-render-top.png"))):
        boards = glob.glob(os.path.join(os.path.dirname(p), "*.kicad_pcb"))
        if boards and 0 < committed(p) < committed(boards[0]):
            print("hooks: %s is older than its board: render it again" % os.path.relpath(p, REPO))


def committed(path):
    """When a file was last committed (seconds), 0 when it never was."""
    r = subprocess.run(["git", "-C", REPO, "log", "-1", "--format=%ct", "--", path], capture_output=True, text=True)
    return int(r.stdout.strip() or 0)
