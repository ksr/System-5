#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-28
"""Bind every System-5 card's redrawn schematic (gen_schematic.py's PDF) into one book: a cover, a contents page and
each card's sheets, with a bookmark per card and per sheet.

    python3 tools/kicad/sch/make_book.py            -> docs/manual/pdf/system5-schematics.pdf

build_all.sh runs it after redrawing the cards, so the book always matches the boards' netlists.
"""
import datetime
import io
import logging
import os
import re
import sys

from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
logging.getLogger("pypdf").setLevel(logging.ERROR)   # KiCad's sheet-to-sheet links: pypdf warns on each page
OUT = os.path.join(ROOT, "docs", "manual", "pdf", "system5-schematics.pdf")

# (folder under hardware/, card, what it is)
CARDS = [
    ("bus/kicad/rev-d", "Bus backplane Rev D (S5BUS-D)", "the new backplane: 8 slots, power switch, fuse, reverse protection, pull-ups"),
    ("cpu/kicad/rev-d", "CPU card Rev D (new, not built)", "the 36-pin CPU card: CDP1802 at 2 MHz, RESET/RUN, LOAD/PAUSE from the bus, EXT CLK, SC0, 2732 at F000"),
    ("io-panel/kicad/rev-a", "IO panel card Rev A (new, not built)", "the front panel: port 4 LEDs, TIL311s and switches; INPUT on -EF1; ELF-style RUN and LOAD with DMA loading"),
    ("cpu/kicad/rev-a", "CPU card Rev A", "CDP1802, clock, reset and run control, boot EPROM, -VMA, EF routing (as drawn)"),
    ("memory/kicad/rev-e", "Memory card Rev E", "2 x 62256 RAM, 2 x 27256 EPROM, each placed by jumpers in 4K blocks; chip-enable LEDs"),
    ("io-1861-keyboard/kicad/rev-a", "IO card Rev A", "CDP1861 video, PS/2 keyboard through a PAK-VI and a PIC16F84, CDP1852 port"),
    ("video-6845/kicad/rev-b", "6845 video card Rev B", "HD6845 CRTC, IDT7134 dual-port video RAM, character generator (after BYTE, May 1979)"),
    ("video-g/kicad/text-1.0", "VIDEO-G 1.0 TEXT (designed, not built)", "6845 + IDT7134 64-column text, status port, PS/2 keyboard; the GFX board on a ribbon"),
    ("video-g/kicad/gfx-1.0", "VIDEO-G 1.0 GFX (designed, not built)", "512 x 200 / 512 x 256 graphics in two pages, Y and control registers, PS/2 mouse"),
    ("ide-cf/kicad/rev-a", "IDE / CF card Rev A", "Mike Riley's 8-bit IDE interface with port-select jumpers"),
    ("bus-driver/kicad/rev-b", "Bus driver card Rev B (BUSDRV-B)", "Arduino Nano and 2 x MCP23017: drives the bus with the CPU card out"),
    ("bus/kicad/rev-2009", "Bus backplane 2009 (as built)", "the built six-slot backplane, from Eagle's 2009 backups"),
]


def card_pdf(folder):
    d = os.path.join(ROOT, "hardware", folder, "schematic")
    pdfs = [f for f in os.listdir(d) if f.endswith("-schematic.pdf")]
    if len(pdfs) != 1:
        raise SystemExit("%s: expected one *-schematic.pdf, found %s" % (d, pdfs))
    return os.path.join(d, pdfs[0])


def sheets(r):
    """(name, page index in this PDF) of each sheet: KiCad's top bookmarks: the root, then each sheet ("<name> (Page n)")"""
    out = []
    for k, item in enumerate(r.outline):
        if isinstance(item, list):
            for sub in item:
                if not isinstance(sub, list):
                    out.append((re.sub(r" \(Page \d+\)$", "", sub.title), r.get_destination_page_number(sub)))
        elif k == 0:
            out.append(("Overview (block diagram)", r.get_destination_page_number(item)))
    return out


def front_pages(entries):
    """the cover and the contents page (A4 landscape), as a PDF in memory"""
    buf = io.BytesIO()
    W, H = landscape(A4)
    c = canvas.Canvas(buf, pagesize=(W, H))
    c.setTitle("System-5 schematics"); c.setAuthor("Ken Rother")
    c.setFont("Helvetica-Bold", 34); c.drawString(60, H - 150, "System-5")
    c.setFont("Helvetica", 22); c.drawString(60, H - 185, "Schematics of every card")
    c.setFont("Helvetica", 12)
    y = H - 240
    for line in ("Ken Rother's RCA 1802 computer: the 30-pin bus and its cards, designed 2004-05, revised 2026.",
                 "Each card is redrawn from its board's netlist and proven pin for pin against it (MATCH), so these",
                 "sheets show the copper as it is. Theory of operation: the System-5 manual (docs/manual).",
                 "Most 2005 drawings carry no values for resistors and capacitors: those show as R and C."):
        c.drawString(60, y, line); y -= 18
    c.setFont("Helvetica", 11)
    c.drawString(60, 60, "cottageworker.com")
    c.drawRightString(W - 60, 60, "Built %s by tools/kicad/sch/make_book.py" % datetime.date.today().isoformat())
    c.showPage()
    c.setFont("Helvetica-Bold", 20); c.drawString(60, H - 70, "Contents")
    y = H - 110
    for title, what, page, nsheets in entries:
        c.setFont("Helvetica-Bold", 12); c.drawString(60, y, title)
        c.drawRightString(W - 60, y, "page %d" % page)
        c.setFont("Helvetica", 10); c.drawString(60, y - 14, "%s  (%d sheets)" % (what, nsheets))
        y -= 46
    c.setFont("Helvetica", 9)
    c.drawString(60, 40, "Each card begins with its root sheet: one block per functional sheet, its pins the nets the sheets share.")
    c.showPage(); c.save()
    return PdfReader(io.BytesIO(buf.getvalue()))


def main():
    readers, entries, page = [], [], 3
    for folder, title, what in CARDS:
        r = PdfReader(card_pdf(folder))
        readers.append((title, r))
        entries.append((title, what, page, len(r.pages)))
        page += len(r.pages)
    w = PdfWriter()
    w.append(front_pages(entries), import_outline=False)
    w.add_outline_item("Cover and contents", 0)
    at = 2
    for title, r in readers:
        w.append(r, import_outline=False)            # KiCad bookmarks every label and symbol: only its sheets are kept
        card = w.add_outline_item(title, at)
        for name, pg in sheets(r):
            w.add_outline_item(name, at + pg, parent=card)
        at += len(r.pages)
    w.add_metadata({"/Title": "System-5 schematics", "/Author": "Ken Rother", "/Subject": "cottageworker.com"})
    w.page_mode = "/UseOutlines"
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "wb") as f:
        w.write(f)
    print("book: %s, %d pages, %d cards" % (os.path.relpath(OUT, ROOT), page - 1, len(CARDS)))


if __name__ == "__main__":
    sys.exit(main())
