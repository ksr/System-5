# Author: Claude (Anthropic) for Ken Rother, 2026
"""MkDocs hook for the System-5 website.

Links: the repository is private, so a relative link to a repository file that is not on the site (a source, a board
file, a zip) cannot go to GitHub: it becomes plain text (its link text). A link to a directory goes to that
directory's README page when the site has one; a link to the repository README goes to "The repository" page.

Menu: each card's section under Cards gets one item per KiCad revision (hardware/<card>/kicad/<rev>/README.md, staged
as notes.md, or its DESIGN.md for a design in progress), named
with what hardware/FABRICATED.md says about it (in use, made, ordered, scrap, not ordered, design only): the word
comes from the heading of the table the board is in, except that a row saying SCRAP is "scrap" and a row whose
note says "**In use" is "in use" (a 2026 board that is built and running, not just ordered)."""
import glob, os, posixpath, re
from urllib.parse import unquote

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the repository this folder is in
LINK = re.compile(r'(!?)\[((?:[^\[\]]|\[[^\]]*\])*)\]\((<[^>]+>|[^)\s]+)((?:\s+"[^"]*")?)\)')
stats = {"plain": 0, "readme": 0}

# the board names in FABRICATED.md's tables -> the card folder under hardware/
BOARD = [("Bus driver", "bus-driver"), ("Bus", "bus"), ("CPU", "cpu"), ("Memory", "memory"),
         ("6845 video", "video-6845"), ("IO panel", "io-panel"), ("IO", "io-1861-keyboard"), ("IDE", "ide-cf")]
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
                label = "Rev %s" % (rev.upper() if len(rev) == 1 else rev) + (" (%s)" % status if status else "")
                items.append({label: "hardware/%s/kicad/%s/%s" % (card, folder, page_name)})
    return config


# the Cards sections of mkdocs.yml -> their folder under hardware/
CARD_OF = {"Backplane and bus": "bus", "CPU card": "cpu", "Memory card": "memory", "6845 video card": "video-6845",
           "IO card (1861 + keyboard)": "io-1861-keyboard", "IDE / CF card": "ide-cf", "Bus driver card": "bus-driver",
           "IO panel card": "io-panel"}


def on_page_markdown(markdown, page, config, files):
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
