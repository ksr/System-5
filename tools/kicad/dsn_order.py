#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-17 (from hardware/video-g/kicad/common/route.py)
"""dsn_order.py - put a Specctra DSN (KiCad's export, Freerouting's input) in a fixed order, so a board routes the same
way every time.

KiCad writes the components, images and pins of a DSN in an order that changes every time a generator makes the board
(each build gives the footprints new UUIDs), and Freerouting's result depends on that order: two builds of the same
placement can route quite differently, one completely and one leaving a net open (VIDEO-G TEXT, 2026-11-17). The
parts' drawn outlines (silkscreen, fab and courtyard lines, which KiCad writes into each image) changed the result too,
although Freerouting routes around pads and keepouts, not outlines; so they are left out, and a silkscreen tidy-up
does not reroute a board. A board's pre-routed tracks (the wiring: the bus Rev D's locked rows and supply feeds, the IO
panel's crystal and +5V runs) came in KiCad's order too, until 2026-11-18: they are sorted as well.

    t = dsn_order.fixed(open(dsn).read(), seed)      # the DSN text in a fixed order
    t = dsn_order.fixed(text, seed, {"DE9VS": "DB9VS"})   # ... a renamed net keeping the place its old name had
A seed (0 or none = the sorted order) shuffles the components and their place lines reproducibly: another seed is
another try when one order leaves a net unrouted. Used by hardware/video-g/kicad/common/route.py and
hardware/cpu/kicad/rev-d/gen/route.py. Plain Python, no KiCad needed.
"""
import random, re

QUOTE = "\x00QUOTE\x00"                                     # (string_quote ") holds a lone " that is not a string


def parse(text):
    text = text.replace('(string_quote ")', "(string_quote %s)" % QUOTE)
    stack, cur = [], []
    for tok in re.findall(r'\(|\)|"[^"]*"|[^\s()"]+', text):
        if tok == "(": stack.append(cur); cur = []
        elif tok == ")": done = cur; cur = stack.pop(); cur.append(done)
        else: cur.append(tok)
    assert not stack and len(cur) == 1, "DSN: unbalanced parentheses"
    return cur[0]


def write(node, ind=0):
    """one line for a list without sublists, else its atoms on the first line and each sublist on its own line"""
    atoms = []
    for x in node:
        if isinstance(x, list): break
        atoms.append(x)
    rest = node[len(atoms):]
    if not rest:
        return " " * ind + "(" + " ".join(atoms) + ")"
    lines = [" " * ind + "(" + " ".join(atoms)]
    for x in rest:
        lines.append(write(x, ind + 2) if isinstance(x, list) else " " * (ind + 2) + x)
    return "\n".join(lines) + ")"


def natural(s):
    s = s.strip('"')
    return [(0, int(p), "") if p.isdigit() else (1, 0, p) for p in re.split(r"(\d+)", s)]


def kids(node, head):
    return [x for x in node if isinstance(x, list) and x and x[0] == head]


def canonical(tree, seed=0, order_as=None):
    """sort what KiCad lists in no fixed order: the board's keepouts, the images (their pins and keepouts; images left
    the same once their outlines are gone become one; which of two same-named images is NAME::1), the components and
    their place lines, the padstacks, the nets and their pins, the nets of each class; then, with a seed, shuffle the
    components and their place lines. order_as: {a net's name (its last part, after any "/"): the name it is sorted
    as}. A net that is renamed would otherwise move in the order, and the board would route another way: with its old
    name given here it keeps its place (2026-11-22: VIDEO-G TEXT's DB9VS became DE9VS, which sorts after DE, DE2, DE3)"""
    def is_(x, *heads): return isinstance(x, list) and x and x[0] in heads
    def net_key(name):
        s = name.strip('"'); leaf = s.split("/")[-1]
        if order_as and leaf in order_as: s = s[:len(s) - len(leaf)] + order_as[leaf]
        return natural(s)
    rename = {}
    for sec in tree:                                        # the library first: the placement uses its image names
        if is_(sec, "library"):
            for img in kids(sec, "image"):                  # the drawn outlines out: see the docstring at the top
                img[:] = [x for x in img if not is_(x, "outline")]
                body = sorted([x for x in img[2:] if isinstance(x, list)], key=lambda x: (x[0], natural(write(x))))
                img[:] = img[:2] + [x for x in img[2:] if not isinstance(x, list)] + body
            groups = {}
            for img in kids(sec, "image"):
                groups.setdefault(img[1].strip('"').split("::")[0], []).append(img)
            keep = []
            for base, imgs in groups.items():
                same = {}                                   # identical images (outlines aside) become one
                for img in imgs: same.setdefault(write(img[2:]), []).append(img)
                for k, body in enumerate(sorted(same)):
                    new = base if k == 0 else "%s::%d" % (base, k)
                    new = '"%s"' % new if same[body][0][1].startswith('"') or re.search(r'[\s()]', new) else new
                    for img in same[body]: rename[img[1]] = new
                    same[body][0][1] = new; keep.append(same[body][0])
            sec[:] = [x for x in sec if not is_(x, "image")] + keep
    for sec in tree:
        if not isinstance(sec, list) or not sec: continue
        if sec[0] == "structure":                           # the keepouts in a fixed order, where the first one was
            kos = sorted([x for x in sec if is_(x, "keepout")], key=lambda x: natural(write(x)))
            if kos:
                i = next(k for k, x in enumerate(sec) if is_(x, "keepout"))
                rest = [x for x in sec if not is_(x, "keepout")]
                sec[:] = rest[:i] + kos + rest[i:]
        elif sec[0] == "placement":
            places = {}                                     # image name -> its place lines (merged images: one list)
            for c in kids(sec, "component"):
                places.setdefault(rename.get(c[1], c[1]), []).extend(kids(c, "place"))
            comps = [["component", name] + sorted(ps, key=lambda p: natural(p[1])) for name, ps in places.items()]
            comps.sort(key=lambda c: natural(c[1]))
            if seed:
                rnd = random.Random(seed); rnd.shuffle(comps)
                for c in comps:
                    ps = c[2:]; rnd.shuffle(ps); c[2:] = ps
            sec[:] = [x for x in sec if not is_(x, "component")] + comps
        elif sec[0] == "library":
            imgs = sorted(kids(sec, "image"), key=lambda i: natural(i[1]))
            pads = sorted(kids(sec, "padstack"), key=lambda p: natural(p[1]))
            other = [x for x in sec[1:] if not is_(x, "image", "padstack")]
            sec[:] = [sec[0]] + other + imgs + pads
        elif sec[0] == "wiring":                            # pre-routed (locked) tracks, in KiCad's UUID order too, and
            wires = []                                      # joined into paths in that order: one wire per segment,
            for x in sec[1:]:                               # its ends in a fixed order, sorted
                path = next((c for c in x[1:] if is_(c, "path")), None) if is_(x, "wire") else None
                if path is None:
                    if is_(x, "wire", "via"): wires.append(x)
                    continue
                pts, rest = path[3:], [c for c in x[1:] if c is not path]
                for k in range(0, len(pts) - 2, 2):
                    a, b = pts[k:k + 2], pts[k + 2:k + 4]
                    if [float(v) for v in a] > [float(v) for v in b]: a, b = b, a
                    wires.append(["wire", ["path", path[1], path[2]] + a + b] + rest)
            wires.sort(key=lambda x: natural(write(x)))
            sec[:] = [sec[0]] + [x for x in sec[1:] if not is_(x, "wire", "via")] + wires
        elif sec[0] == "network":
            nets = kids(sec, "net")
            for n in nets:
                for p in kids(n, "pins"): p[1:] = sorted(p[1:], key=natural)
            nets.sort(key=lambda n: net_key(n[1]))
            classes = kids(sec, "class")
            for c in classes:
                names = [x for x in c[2:] if not isinstance(x, list)]
                c[:] = c[:2] + sorted(names, key=net_key) + [x for x in c[2:] if isinstance(x, list)]
            other = [x for x in sec[1:] if not is_(x, "net", "class")]
            sec[:] = [sec[0]] + other + nets + classes
    return tree


def fixed(text, seed=0, order_as=None):
    """the DSN text in the fixed order (see the docstring at the top; order_as: canonical())"""
    return write(canonical(parse(text), seed, order_as)).replace(QUOTE, '"') + "\n"
