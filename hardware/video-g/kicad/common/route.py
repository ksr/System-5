#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-01
"""route.py dsn|import BOARD_DIR - Freerouting in and out for a VIDEO-G board (run with KiCad's Python).

  dsn     BOARD_DIR/<PROJ>.dsn from the unrouted board: In1.Cu (GND) and In2.Cu (+5V) become power layers and GND/+5V
          leave the network, so Freerouting routes the signals on F.Cu/B.Cu only and every GND/+5V pin (a through-hole
          pad) lands in its plane - memory Rev E's method (hardware/memory/kicad/rev-e/gen/make_planes.py).
          The DSN is then put in a fixed order (2026-11-17). KiCad writes its components, images and pins in an order
          that changes every time make_board.py makes the board (each build gives the footprints new UUIDs), and
          Freerouting's result depends on that order: before this, two builds of the same placement could route quite
          differently, one completely and one leaving a net open. Now the same board always routes the same way.
          ROUTE_SEED in gen/place.py (or the ROUTE_SEED environment variable, which wins) shuffles the component order
          reproducibly: another seed is another try when one order leaves a net unrouted. 0 or none = the sorted order.
          The parts' drawn outlines (silkscreen, fab and courtyard lines, which KiCad writes into each image) are left
          out: Freerouting routes around pads and keepouts, not outlines, yet they changed its result - adding
          courtyards to two footprints turned a complete route into one that stalled - so a silkscreen tidy-up must
          not reroute a board.
  import  BOARD_DIR/<PROJ>.ses back into the board (tools/kicad/kicad_route.py import_ses: stitch, edge heal, zone fill)
Freerouting runs between them, from BOARD_DIR: java -jar ~/freerouting/freerouting.jar -de P.dsn -do P.ses -mt 1
"""
import os, sys, re, random, importlib.util
import pcbnew
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "kicad")); import kicad_route

PLANES = (("In1.Cu", "GND"), ("In2.Cu", "+5V"))


def load(board_dir, name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(board_dir, "gen", name + ".py"))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


# ---- the DSN as a tree, to put it in a fixed order --------------------------------------------------------------------
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


def canonical(tree, seed=0):
    """sort what KiCad lists in no fixed order: the board's keepouts, the images (their pins and keepouts; images left
    the same once their outlines are gone become one; which of two same-named images is NAME::1), the components and
    their place lines, the padstacks, the nets and their pins, the nets of each class; then, with a seed, shuffle the
    components and their place lines"""
    def is_(x, *heads): return isinstance(x, list) and x and x[0] in heads
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
        elif sec[0] == "network":
            nets = kids(sec, "net")
            for n in nets:
                for p in kids(n, "pins"): p[1:] = sorted(p[1:], key=natural)
            nets.sort(key=lambda n: natural(n[1]))
            classes = kids(sec, "class")
            for c in classes:
                names = [x for x in c[2:] if not isinstance(x, list)]
                c[:] = c[:2] + sorted(names, key=natural) + [x for x in c[2:] if isinstance(x, list)]
            other = [x for x in sec[1:] if not is_(x, "net", "class")]
            sec[:] = [sec[0]] + other + nets + classes
    return tree


def main():
    cmd, board_dir = sys.argv[1], os.path.abspath(sys.argv[2])
    N = load(board_dir, "netlist")
    PCB = os.path.join(board_dir, N.PROJ + ".kicad_pcb")
    if cmd == "dsn":
        kicad_route.export_dsn(PCB)
        dsn = PCB[:-len(".kicad_pcb")] + ".dsn"; t = open(dsn).read()
        for lname, _ in PLANES:
            t = re.sub(r'(\(layer %s\s*\(type )signal' % re.escape(lname), r'\1power', t)
        for _, net in PLANES:
            t = re.sub(r'\n\s*\(net "?%s"?\s*\(pins[^)]*\)\s*\)' % re.escape(net), '', t)    # ("+5V" may be quoted)
            t = re.sub(r'(\(class [^\n]*?) "?%s"?(?=[ )\n])' % re.escape(net), r'\1', t)
        seed = os.environ.get("ROUTE_SEED")
        seed = int(seed) if seed not in (None, "") else int(getattr(load(board_dir, "place"), "ROUTE_SEED", 0))
        t = write(canonical(parse(t), seed)).replace(QUOTE, '"') + "\n"
        open(dsn, "w").write(t)
        print("dsn: layers", re.findall(r'\(layer (\S+)\s*\(type (\w+)', t), "| GND/+5V still routed:",
              bool(re.search(r'\(net "?(GND|\+5V)"?\s*\(pins', t)), "| fixed order, route seed", seed)
    elif cmd == "import":
        kicad_route.import_ses(PCB, PCB[:-len(".kicad_pcb")] + ".ses")
    else:
        sys.exit(__doc__)
    sys.stdout.flush(); os._exit(0)


if __name__ == "__main__":
    main()
