#!/usr/bin/env python3
"""mkpdf.py -- the System-5 documents (docs/manual) as readable PDF books. (From P32W's tools/mkpdf.py, 2026-10-26.)

The Markdown files in docs/ and the READMEs are the sources; this turns
them into a few books (BOOKS below), each one PDF with a title page, a
contents page and a chapter per document, links between documents of the
same book working inside the PDF. A small Markdown converter of its own
(headings, paragraphs, lists, tables, code blocks, the inline marks the
documents use) writes HTML, and Chrome, headless, prints it.

    python3 tools/mkpdf.py [-o DIR] [BOOK ...]      (default: every book, into docs/manual/pdf)

Needs Google Chrome (or CHROME=path). Nothing is downloaded.
"""
import os, re, sys, html, subprocess, tempfile, datetime, argparse

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

# (file name, title, subtitle, [documents]) -- a document is a path from the repository's root
BOOKS = [
    ("system5-hardware-reference", "System-5 Hardware Reference", "The system, the bus and every card: theory of operation",
     ["docs/manual/system.md", "docs/manual/bus.md", "docs/manual/cpu-card.md", "docs/manual/memory-card.md",
      "docs/manual/video-6845-card.md", "docs/manual/io-card.md", "docs/manual/ide-cf-card.md",
      "docs/manual/bus-driver-card.md", "docs/manual/other-cards.md"]),
    ("system5-programmers-guide", "System-5 Programmer's Guide", "The memory and I/O maps, the devices, HBIOS, "
     "the monitor and the BIOS calls", ["docs/manual/programmers-guide.md"]),
    ("system5-operators-guide", "System-5 Operator's Guide", "The boot monitor, the ELF/OS installer, every ELF/OS "
     "command and Rc/Basic", ["docs/manual/operators-guide.md"]),
    ("system5-system", "System-5: the System", "The cards, a bus cycle, the maps and how it starts", ["docs/manual/system.md"]),
    ("system5-bus", "The System-5 Bus", "The 30-pin bus: every pin, the 1802's cycle, -VMA, rules for a card",
     ["docs/manual/bus.md"]),
    ("system5-cpu-card", "System-5 CPU Card", "Theory of operation", ["docs/manual/cpu-card.md"]),
    ("system5-memory-card", "System-5 Memory Card", "Theory of operation", ["docs/manual/memory-card.md"]),
    ("system5-video-6845-card", "System-5 6845 Video Card", "Theory of operation", ["docs/manual/video-6845-card.md"]),
    ("system5-io-card", "System-5 IO Card (1861 and Keyboard)", "Theory of operation", ["docs/manual/io-card.md"]),
    ("system5-ide-cf-card", "System-5 IDE/CF Card", "Theory of operation", ["docs/manual/ide-cf-card.md"]),
    ("system5-bus-driver-card", "System-5 Bus Driver Card", "Theory of operation", ["docs/manual/bus-driver-card.md"]),
    ("system5-other-cards", "System-5: Other Cards and Designs", "The prototyping card, the front panel, earlier revisions",
     ["docs/manual/other-cards.md"]),
]

# ---------------------------------------------------------------- Markdown -> HTML
def slug(s):
    s = re.sub(r"<[^>]+>", "", s).lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")

class Doc:
    """One document: its HTML, its headings; links to other documents of the
    book become links inside the PDF."""
    def __init__(self, path, prefix, docmap):
        self.path, self.prefix, self.docmap = path, prefix, docmap
        self.heads = []                                 # (level, text, id)
        self.ids = set()

    # ---- inline
    def inline(self, s):
        codes = []
        def keep(m):
            codes.append("<code>%s</code>" % html.escape(m.group(2)))
            return "\x00%d\x00" % (len(codes) - 1)
        s = re.sub(r"(`+)(.+?)\1", keep, s)
        s = re.sub(r"\\([\\`*_{}\[\]()#+\-.!|<>~])", lambda m: "\x01%d\x01" % ord(m.group(1)), s)
        s = html.escape(s, quote=False)
        def link(m):
            text, url = m.group(1), html.unescape(m.group(2))
            return '<a href="%s">%s</a>' % (html.escape(self.href(url)), text)
        s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", link, s)
        s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", s)
        s = re.sub(r"(?<![\w])_(?!\s)([^_]+?)(?<!\s)_(?![\w])", r"<em>\1</em>", s)
        s = re.sub(r"~~(.+?)~~", r"<del>\1</del>", s)
        s = re.sub(r"(?<![\"'=])(https?://[^\s<)]+)", r'<a href="\1">\1</a>', s)
        s = re.sub(r"\x01(\d+)\x01", lambda m: html.escape(chr(int(m.group(1)))), s)
        return re.sub(r"\x00(\d+)\x00", lambda m: codes[int(m.group(1))], s)

    def href(self, url):
        if re.match(r"^[a-z]+:", url):
            return url
        target, _, frag = url.partition("#")
        if not target:
            return "#%s-%s" % (self.prefix, frag)
        full = os.path.normpath(os.path.join(os.path.dirname(self.path), target))
        if full in self.docmap:
            return "#%s%s" % (self.docmap[full], "-" + frag if frag else "")
        return "https://github.com/ksr/elf/blob/main/%s" % full     # (another book's, or a source file)

    # ---- blocks
    def convert(self, text):
        self.lines = text.split("\n")
        self.i = 0
        return self.blocks(self.lines)

    def blocks(self, lines):
        out = []
        i = 0
        n = len(lines)
        while i < n:
            l = lines[i]
            if not l.strip():
                i += 1
                continue
            m = re.match(r"^(```+|~~~+)\s*(\S*)", l)
            if m:
                fence = m.group(1)
                j = i + 1
                body = []
                while j < n and not lines[j].startswith(fence):
                    body.append(lines[j])
                    j += 1
                out.append(self.code(body))
                i = j + 1
                continue
            m = re.match(r"^(#{1,6})\s+(.*?)\s*#*$", l)
            if m:
                out.append(self.heading(len(m.group(1)), m.group(2)))
                i += 1
                continue
            if re.match(r"^\s*([-*_])(\s*\1){2,}\s*$", l):
                out.append("<hr>")
                i += 1
                continue
            if l.lstrip().startswith("|") and i + 1 < n and re.match(r"^\s*\|?\s*:?-{2,}", lines[i + 1]):
                j = i + 2
                while j < n and lines[j].lstrip().startswith("|"):
                    j += 1
                out.append(self.table(lines[i], lines[i + 1], lines[i + 2:j]))
                i = j
                continue
            if l.startswith(">"):
                j = i
                body = []
                while j < n and lines[j].startswith(">"):
                    body.append(re.sub(r"^>\s?", "", lines[j]))
                    j += 1
                out.append("<blockquote>%s</blockquote>" % self.blocks(body))
                i = j
                continue
            if LIST.match(l):
                j = i + 1
                while j < n:
                    if not lines[j].strip():
                        k = j + 1
                        while k < n and not lines[k].strip():
                            k += 1
                        if k < n and (lines[k].startswith(" ") or LIST.match(lines[k])) and not lines[k].startswith("```"):
                            j = k
                            continue
                        break
                    if not lines[j].startswith(" ") and not LIST.match(lines[j]) and \
                            (lines[j].startswith("#") or lines[j].startswith("|") or lines[j].startswith("```")):
                        break
                    j += 1
                out.append(self.lst(lines[i:j]))
                i = j
                continue
            j = i
            para = []
            while j < n and lines[j].strip() and not re.match(r"^(#{1,6}\s|```|~~~|>|\s*\|)", lines[j]) \
                    and not (j > i and LIST.match(lines[j])):
                para.append(lines[j].strip())
                j += 1
            out.append("<p>%s</p>" % self.inline(" ".join(para)))
            i = j
        return "\n".join(out)

    def heading(self, level, text):
        base = slug(text) or "s"
        hid, k = "%s-%s" % (self.prefix, base), 2
        while hid in self.ids:
            hid, k = "%s-%s-%d" % (self.prefix, base, k), k + 1
        self.ids.add(hid)
        self.heads.append((level, self.inline(text), hid))
        if level == 1:
            hid = self.prefix                           # (the chapter's own anchor)
        return '<h%d id="%s">%s</h%d>' % (level, hid, self.inline(text), level)

    def code(self, body):
        width = max([len(x) for x in body] or [0])
        size = min(8.0, 6.9 * 72 / (0.6 * max(width, 1)))
        return '<pre style="font-size:%.2fpt">%s</pre>' % (max(size, 5.0), html.escape("\n".join(body)))

    def table(self, head, sep, rows):
        cells = lambda r: [c.strip() for c in re.split(r"(?<!\\)\|", re.sub(r"^\s*\||(?<!\\)\|\s*$", "", r))]
        aligns = []
        for c in cells(sep):
            aligns.append("center" if c.startswith(":") and c.endswith(":") else "right" if c.endswith(":") else "left")
        def row(r, tag):
            cs = cells(r)
            return "<tr>%s</tr>" % "".join('<%s style="text-align:%s%s">%s</%s>' % (
                tag, aligns[k] if k < len(aligns) else "left", "; white-space: nowrap" if len(c) <= 12 else "",
                self.inline(c), tag) for k, c in enumerate(cs))
        ncols = len(cells(head))
        cls = ' class="wide"' if ncols >= 5 or max(len(r) for r in [head] + rows) > 160 else ""
        return "<table%s><thead>%s</thead><tbody>%s</tbody></table>" % (
            cls, row(head, "th"), "".join(row(r, "td") for r in rows))

    def lst(self, lines):
        """A list and its nested lists, by indentation."""
        first = LIST.match(lines[0])
        ordered = first.group(2)[0].isdigit()
        base = len(first.group(1))
        items, cur = [], None
        for l in lines:
            m = LIST.match(l)
            if m and len(m.group(1)) <= base + 1 and (m.group(2)[0].isdigit()) == ordered:
                cur = [l[m.end():]]
                items.append(cur)
            elif cur is not None:
                cur.append(l)
        out = []
        for it in items:
            # an item's continuation lines, dedented to its content's column
            body = [it[0]]
            for l in it[1:]:
                body.append(re.sub(r"^ {1,%d}" % (base + 4), "", l) if l.strip() else "")
            inner = self.blocks(body)
            if inner.count("<p>") == 1 and inner.startswith("<p>") and "\n" not in inner:
                inner = inner[3:-4]                     # (a one-paragraph item: no paragraph spacing)
            elif inner.startswith("<p>") and not re.search(r"\n\s*\n", "\n".join(body)):
                inner = re.sub(r"^<p>(.*?)</p>", r"\1", inner, count=1, flags=re.S)
            out.append("<li>%s</li>" % inner)
        tag = "ol" if ordered else "ul"
        start = ' start="%s"' % first.group(2)[:-1] if ordered and first.group(2)[:-1] != "1" else ""
        return "<%s%s>%s</%s>" % (tag, start, "".join(out), tag)

LIST = re.compile(r"^(\s*)([-*+]|\d+\.)\s+")

# ---------------------------------------------------------------- a book
CSS = """
@page { size: letter; margin: 0.75in 0.7in 0.8in 0.7in;
        @bottom-center { content: counter(page); font: 9pt "Helvetica Neue", Helvetica, sans-serif; color: #666; }
}
@page :first { @bottom-center { content: none; } }
html { font: 10.5pt/1.42 Charter, "Iowan Old Style", Georgia, serif; color: #1a1a1a; }
body { margin: 0; }
h1, h2, h3, h4, h5 { font-family: "Helvetica Neue", Helvetica, Arial, sans-serif; line-height: 1.2;
                     break-after: avoid; color: #111; }
h1 { font-size: 22pt; margin: 0 0 14pt; padding-bottom: 6pt; border-bottom: 2px solid #1d4e89;
     break-before: page; }
h2 { font-size: 14pt; margin: 18pt 0 6pt; color: #1d4e89; }
h3 { font-size: 11.5pt; margin: 14pt 0 4pt; }
h4, h5 { font-size: 10.5pt; margin: 10pt 0 3pt; }
p { margin: 0 0 7pt; orphans: 3; widows: 3; text-align: left; }
ul, ol { margin: 0 0 7pt; padding-left: 18pt; }
li { margin: 0 0 2.5pt; }
li > ul, li > ol { margin: 2.5pt 0 0; }
code { font: 0.86em Menlo, "SF Mono", Monaco, monospace; background: #f1f3f6; padding: 0 2px; border-radius: 2px; }
pre { font-family: Menlo, "SF Mono", Monaco, monospace; line-height: 1.25; background: #f6f8fa;
      border: 1px solid #dde2e8; border-radius: 3px; padding: 6pt 8pt; margin: 0 0 9pt;
      white-space: pre; overflow: hidden; break-inside: avoid; }
pre code { background: none; padding: 0; font-size: 1em; }
table { border-collapse: collapse; margin: 2pt 0 10pt; font-size: 9pt; line-height: 1.3; width: auto; max-width: 100%; }
table.wide { font-size: 8pt; width: 100%; }
th, td { border: 1px solid #c9d0d8; padding: 2.5pt 4pt; vertical-align: top; }
th { background: #e8eef5; font-family: "Helvetica Neue", Helvetica, sans-serif; font-weight: 600; }
tr { break-inside: avoid; }
thead { display: table-header-group; }
blockquote { margin: 0 0 8pt; padding: 2pt 10pt; border-left: 3px solid #9fb3c8; color: #333; }
hr { border: 0; border-top: 1px solid #ccc; margin: 12pt 0; }
a { color: #1d4e89; text-decoration: none; }
strong { font-weight: 700; }
.title { height: 9in; display: flex; flex-direction: column; justify-content: center; }
.title .name { font: 700 34pt "Helvetica Neue", Helvetica, sans-serif; color: #1d4e89; margin-bottom: 10pt; }
.title .sub { font: 15pt "Helvetica Neue", Helvetica, sans-serif; color: #444; margin-bottom: 36pt; max-width: 5.5in; }
.title .meta { font: 10pt "Helvetica Neue", Helvetica, sans-serif; color: #666; line-height: 1.6; }
.toc { break-before: page; }
.toc h1.toch { break-before: avoid; }
.toc ul { list-style: none; padding-left: 0; }
.toc li.c { font: 600 11.5pt "Helvetica Neue", Helvetica, sans-serif; margin: 9pt 0 2pt; }
.toc li.s { margin-left: 16pt; font-size: 9.5pt; margin-bottom: 1pt; }
.toc .src { font: 8pt Menlo, monospace; color: #888; font-weight: normal; margin-left: 6pt; }
.srcnote { font: 8pt "Helvetica Neue", Helvetica, sans-serif; color: #888; margin: -8pt 0 12pt; }
"""

def git_rev():
    try:
        return subprocess.run(["git", "-C", ROOT, "log", "-1", "--format=%h %cs"], capture_output=True,
                              text=True, check=True).stdout.strip()
    except Exception:
        return ""

def book_html(fname, title, sub, docs):
    docmap = {d: "ch%d" % k for k, d in enumerate(docs, 1)}
    chapters, toc = [], []
    for d in docs:
        doc = Doc(d, docmap[d], docmap)
        body = doc.convert(open(os.path.join(ROOT, d), encoding="utf-8").read())
        if not doc.heads or doc.heads[0][0] != 1:      # (a document without its own title)
            body = '<h1 id="%s">%s</h1>' % (doc.prefix, html.escape(d)) + body
            doc.heads.insert(0, (1, html.escape(d), doc.prefix))
        body = body.replace("</h1>", '</h1><div class="srcnote">%s</div>' % html.escape(d), 1)
        chapters.append(body)
        h1 = doc.heads[0]
        toc.append('<li class="c"><a href="#%s">%s</a><span class="src">%s</span></li>' % (doc.prefix, h1[1], html.escape(d)))
        for lv, text, hid in doc.heads[1:]:
            if lv == 2:
                toc.append('<li class="s"><a href="#%s">%s</a></li>' % (hid, text))
    stamp = "%s<br>Generated %s from the repository%s" % (
        "System-5 — an RCA 1802 computer (2004–05, documented 2026)", datetime.date.today().isoformat(),
        (" at " + git_rev()) if git_rev() else "")
    return """<!doctype html><html><head><meta charset="utf-8"><title>%s</title><style>%s</style></head><body>
<section class="title"><div class="name">%s</div><div class="sub">%s</div><div class="meta">%s</div></section>
<section class="toc"><h1 class="toch">Contents</h1><ul>%s</ul></section>
%s
</body></html>""" % (html.escape(title), CSS, html.escape(title), html.escape(sub), stamp, "\n".join(toc), "\n".join(chapters))

def chrome():
    for c in (os.environ.get("CHROME"), "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
              "/usr/bin/google-chrome", "/usr/bin/chromium"):
        if c and os.path.exists(c):
            return c
    sys.exit("mkpdf: no Chrome found (set CHROME=path)")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", dest="out", default=os.path.join(ROOT, "docs", "manual", "pdf"))
    ap.add_argument("--html", action="store_true", help="keep the HTML beside each PDF")
    ap.add_argument("books", nargs="*")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    exe = chrome()
    for fname, title, sub, docs in BOOKS:
        if a.books and fname not in a.books:
            continue
        page = book_html(fname, title, sub, docs)
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(a.out if a.html else tmp, fname + ".html")
            open(src, "w", encoding="utf-8").write(page)
            pdf = os.path.join(a.out, fname + ".pdf")
            r = subprocess.run([exe, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                                "--user-data-dir=" + os.path.join(tmp, "profile"),
                                "--print-to-pdf=" + pdf, "file://" + src], capture_output=True, text=True)
            if r.returncode or not os.path.exists(pdf):
                sys.exit("mkpdf: Chrome failed on %s: %s" % (fname, r.stderr[-500:]))
        print("%-28s %4d KB  %s" % (fname + ".pdf", os.path.getsize(pdf) // 1024, title))

if __name__ == "__main__":
    main()
