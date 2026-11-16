#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-14
"""Look inside an Elf/OS v5 card image, replace a file on it, or add one.

  python3 v5card.py ls  IMAGE [/dir]         list the card, or one directory
  python3 v5card.py get IMAGE /path OUT      copy a file off the card
  python3 v5card.py put IMAGE /path FILE     replace the contents of a file that is already on the card
  python3 v5card.py add IMAGE /path FILE     add a new file (2026-11-15); -x marks it executable, for a program

IMAGE is .img or .img.gz; put and add write it back in place.

put only replaces. The file must be on the card already, and the new contents must need as many lumps as the file
has now (a lump is 4096 bytes; most programs in /bin are one lump). Two things then change on the card: the
contents of those lumps, and the length in the file's directory entry. No lump is allocated or freed, so the
allocation table is not written to.

add does what v5 does when it makes a file: the lowest free lumps, chained in the allocation table, and the first
free entry of the directory (which must exist and have one free). Mike Riley's Disktool5 can add files too.

LAT-16 cards only, as every System-5 card is. The format, as far as this needs it (worked out from the System-5
image, 2026-11-13): sectors of 512 bytes; a lump (allocation unit) is 8 sectors, and lump n is sectors 8n to 8n+7.
Sector 0 has the file-system type at 104h (1 = LAT-16) and the master directory's first lump at 12Ch (4 bytes).
The allocation table (LAT) starts at sector 17, two bytes a lump, high byte first: the next lump of the file,
FEFE for its last lump, 0 for a free lump. A directory is a file of 32-byte entries: first lump (4 bytes, 0 = no
entry), bytes used in the file's last lump (2), flags (1; bit 0 = a directory), date, time and one more byte (5),
name (20, zero-filled).
"""
import gzip, os, sys, time

SEC = 512; LUMP = 8 * SEC; LAT = 17 * SEC; LAST = 0xFEFE


def read_image(path):
    with (gzip.open(path, "rb") if path.endswith(".gz") else open(path, "rb")) as f: img = bytearray(f.read())
    if len(img) < 64 * SEC or img[0x104] != 1:
        raise SystemExit("%s: not a LAT-16 Elf/OS v5 card image (type %d at 104h)" % (path, img[0x104] if len(img) > 0x104 else -1))
    return img


def write_image(path, img):
    if path.endswith(".gz"):              # no file name and no time in the gzip header: the same card gives the same file
        with open(path, "wb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=9, mtime=0) as f: f.write(img)
    else:
        with open(path, "wb") as f: f.write(img)


def lat(img, lump): return int.from_bytes(img[LAT + 2 * lump:LAT + 2 * lump + 2], "big")


def chain(img, lump):
    """-> the lumps of the file that starts at lump"""
    out = [lump]
    while lat(img, out[-1]) != LAST:
        nxt = lat(img, out[-1])
        if not 0 < nxt < len(img) // LUMP or nxt in out or len(out) > 8192: raise SystemExit("a broken lump chain from %04X" % lump)
        out.append(nxt)
    return out


def entries(img, dir_lump):
    """-> (offset of the entry in the image, first lump, bytes in the last lump, is a directory, name), for a directory"""
    for lump in chain(img, dir_lump):
        for at in range(lump * LUMP, (lump + 1) * LUMP, 32):
            e = img[at:at + 32]
            if any(e[0:4]):
                yield at, int.from_bytes(e[0:4], "big"), int.from_bytes(e[4:6], "big"), bool(e[6] & 1), e[12:].split(b"\0")[0].decode("latin-1")


def lookup(img, path):
    """-> (offset of the entry, first lump, bytes in the last lump, is a directory) for /a/b; the master directory for /"""
    here = (None, int.from_bytes(img[0x12C:0x130], "big"), 0, True)
    for part in [p for p in path.split("/") if p]:
        if not here[3]: raise SystemExit("%s: not a directory on the way" % path)
        for at, first, eof, isdir, name in entries(img, here[1]):
            if name == part: here = (at, first, eof, isdir); break
        else: raise SystemExit("%s: no %s on the card" % (path, part))
    return here


def contents(img, first, eof):
    c = chain(img, first)
    return b"".join(bytes(img[x * LUMP:(x + 1) * LUMP]) for x in c)[:(len(c) - 1) * LUMP + eof]


def ls(img, path="/", out=None, deep=True):
    """-> [(path, size or None for a directory, lumps)], sorted by name, directories followed by what they hold"""
    out = [] if out is None else out
    at, first, eof, isdir = lookup(img, path)
    if not isdir: raise SystemExit("%s: not a directory" % path)
    for _, f, e, d, name in sorted(entries(img, first), key=lambda x: x[4]):
        full = path.rstrip("/") + "/" + name
        out.append((full + ("/" if d else ""), None if d else (len(chain(img, f)) - 1) * LUMP + e, chain(img, f)))
        if d and deep: ls(img, full, out)
    return out


def put(img, path, data):
    """Replace the contents of the file at path. -> (old size, lumps)"""
    at, first, eof, isdir = lookup(img, path)
    if at is None or isdir: raise SystemExit("%s: not a file" % path)
    c = chain(img, first); old = (len(c) - 1) * LUMP + eof
    if not data or len(data) % LUMP == 0: raise SystemExit("%d bytes: an empty file or a whole number of lumps is not handled" % len(data))
    if (len(data) + LUMP - 1) // LUMP != len(c):
        raise SystemExit("%s has %d lump(s) on the card and %d bytes need %d: this only replaces in the same lumps"
                         % (path, len(c), len(data), (len(data) + LUMP - 1) // LUMP))
    padded = data + bytes(len(c) * LUMP - len(data))
    for i, lump in enumerate(c): img[lump * LUMP:(lump + 1) * LUMP] = padded[i * LUMP:(i + 1) * LUMP]
    img[at + 4:at + 6] = (len(data) - (len(c) - 1) * LUMP).to_bytes(2, "big")
    assert contents(img, *lookup(img, path)[1:3]) == data
    return old, c


def add(img, path, data, executable=False, when=None):
    """Add a new file at path (its directory must exist and have a free entry). -> the lumps it got.
    As v5 itself does when it makes a file (seen in s5emu, 2026-11-15, `copy /bin/ver /bin/vertest`): it takes the
    lowest free lumps, chains them in the LAT (the last one FEFE), and fills the first free 32-byte entry of the
    directory; nothing else on the card changes. Flags 10h as v5 sets for a new file, plus 02h (executable) with -x
    (the programs lbr unpacks into /bin carry 12h). Date and time are packed as v5 stores them: date =
    (year - 1972) << 9 | month << 5 | day, time = hour << 11 | minute << 5 | second / 2."""
    folder, _, name = path.rstrip("/").rpartition("/")
    if not name or len(name.encode("latin-1")) > 19: raise SystemExit("%s: a name of 1 to 19 characters" % path)
    at, dir_first, _, isdir = lookup(img, folder or "/")
    if not isdir: raise SystemExit("%s: not a directory" % (folder or "/"))
    if any(n == name for *_, n in entries(img, dir_first)): raise SystemExit("%s is already on the card (use put)" % path)
    if not data or len(data) % LUMP == 0: raise SystemExit("%d bytes: an empty file or a whole number of lumps is not handled" % len(data))
    slot = next((a for lump in chain(img, dir_first) for a in range(lump * LUMP, (lump + 1) * LUMP, 32)
                 if not any(img[a:a + 4])), None)
    if slot is None: raise SystemExit("%s: the directory is full (growing it is not handled)" % (folder or "/"))
    lumps_on_card = int.from_bytes(img[0x100:0x104], "big") // 8
    need = (len(data) + LUMP - 1) // LUMP
    free = [n for n in range(1, min(lumps_on_card, (len(img) - LAT) // 2)) if lat(img, n) == 0][:need]
    if len(free) < need: raise SystemExit("not enough free lumps: %d needed, %d free" % (need, len(free)))
    padded = data + bytes(need * LUMP - len(data))
    for i, lump in enumerate(free):
        img[lump * LUMP:(lump + 1) * LUMP] = padded[i * LUMP:(i + 1) * LUMP]
        img[LAT + 2 * lump:LAT + 2 * lump + 2] = (free[i + 1] if i + 1 < need else LAST).to_bytes(2, "big")
    t = when or time.localtime()
    entry = bytearray(32)
    entry[0:4] = free[0].to_bytes(4, "big")
    entry[4:6] = (len(data) - (need - 1) * LUMP).to_bytes(2, "big")
    entry[6] = 0x10 | (0x02 if executable else 0)
    entry[7:9] = ((t.tm_year - 1972) << 9 | t.tm_mon << 5 | t.tm_mday).to_bytes(2, "big")
    entry[9:11] = (t.tm_hour << 11 | t.tm_min << 5 | t.tm_sec // 2).to_bytes(2, "big")
    entry[12:12 + len(name)] = name.encode("latin-1")
    img[slot:slot + 32] = entry
    assert contents(img, *lookup(img, path)[1:3]) == data
    return free


def main(argv):
    if argv[:1] == ["add"] and "-x" in argv: argv = [a for a in argv if a != "-x"]; executable = True
    else: executable = False
    if len(argv) < 2 or argv[0] not in ("ls", "get", "put", "add"): raise SystemExit(__doc__)
    cmd, path = argv[0], argv[1]; img = read_image(path)
    if cmd == "ls":
        for name, size, lumps in ls(img, argv[2] if len(argv) > 2 else "/"):
            print("%-28s %s" % (name, "" if size is None else "%6d bytes, lump%s %s" % (size, "s" if len(lumps) > 1 else "", " ".join("%04X" % x for x in lumps))))
    elif cmd == "get" and len(argv) == 4:
        at, first, eof, isdir = lookup(img, argv[2])
        if at is None or isdir: raise SystemExit("%s: not a file" % argv[2])
        data = contents(img, first, eof)
        with open(argv[3], "wb") as f: f.write(data)
        print("%s: %d bytes -> %s" % (argv[2], len(data), argv[3]))
    elif cmd == "put" and len(argv) == 4:
        with open(argv[3], "rb") as f: data = f.read()
        old, lumps = put(img, argv[2], data); write_image(path, img)
        print("%s: %s is now %d bytes (it was %d), in lump%s %s" % (os.path.basename(path), argv[2], len(data), old,
              "s" if len(lumps) > 1 else "", " ".join("%04X" % x for x in lumps)))
    elif cmd == "add" and len(argv) == 4:
        with open(argv[3], "rb") as f: data = f.read()
        lumps = add(img, argv[2], data, executable); write_image(path, img)
        print("%s: %s added, %d bytes%s, in lump%s %s" % (os.path.basename(path), argv[2], len(data),
              " (executable)" if executable else "", "s" if len(lumps) > 1 else "", " ".join("%04X" % x for x in lumps)))
    else: raise SystemExit(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
