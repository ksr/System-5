#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-01
"""asm1802: a small RCA 1802 cross-assembler (Python 3.9+, standard library only).

Written for GBASIC (software/gbasic) and the VIDEO-G HBIOS build (firmware/hbios/video-g). It reads Mike Riley's
rcasm syntax as used in HBIOS (it assembles firmware/hbios/v1.0.4/sec1.asm, after cpp, to the same bytes as rcasm:
`python3 tools/asm1802.py --selftest`), plus:

  * a check on every short branch: the target must be in the page of the branch's address byte (rcasm silently
    keeps only the low byte, which is a wrong jump when the target is in another page);
  * relaxing jumps  JMP JZ JNZ JDF JNF JQ JNQ (JGE = JDF, JLT = JNF): short (2 bytes) when the target is in the
    page, long (3 bytes, LBR/LBZ/...) otherwise, chosen by iterating until the addresses settle;
  * macros (MACRO name args ... ENDM; \\@ in a macro body is a number unique to each expansion), IF/ELSE/ENDIF on
    expressions known at that point, INCLUDE "file", ALIGN n, and an expression language with
    + - * / % & | ^ << >> ~, HIGH x / LOW x and x.1 / x.0, $ = the current address, 'c' characters.

Usage:
  asm1802.py SOURCE [-o OUT.bin] [--hex OUT.hex] [--lst OUT.lst] [--sym OUT.sym]
                    [--elfos OUT --exec ADDR] [-D NAME=VALUE ...]

-o writes the bytes from the lowest to the highest address assembled (gaps = 00).  --elfos writes an ELF/OS
executable: a 6-byte header (load address, size, exec address; big-endian) and the same bytes.  The listing has
rcasm's layout ('LINE ADDR: bytes  source'), so s5emu's `sym` command reads its labels.
"""
import argparse, os, re, sys

# ------------------------------------------------------------------------------------------------ instruction set
NOARG = {"IDL": 0x00, "IRX": 0x60, "RET": 0x70, "DIS": 0x71, "LDXA": 0x72, "STXD": 0x73, "ADC": 0x74, "SDB": 0x75,
         "SHRC": 0x76, "RSHR": 0x76, "SMB": 0x77, "SAV": 0x78, "MARK": 0x79, "REQ": 0x7A, "SEQ": 0x7B, "SHLC": 0x7E,
         "RSHL": 0x7E, "NOP": 0xC4, "LSNQ": 0xC5, "LSNZ": 0xC6, "LSNF": 0xC7, "LSKP": 0xC8, "NLBR": 0xC8,
         "LSIE": 0xCC, "LSQ": 0xCD, "LSZ": 0xCE, "LSDF": 0xCF, "LDX": 0xF0, "OR": 0xF1, "AND": 0xF2, "XOR": 0xF3,
         "ADD": 0xF4, "SD": 0xF5, "SHR": 0xF6, "SM": 0xF7, "SHL": 0xFE, "SKP": 0x38, "NBR": 0x38}
REGOP = {"LDN": 0x00, "INC": 0x10, "DEC": 0x20, "LDA": 0x40, "STR": 0x50, "GLO": 0x80, "GHI": 0x90, "PLO": 0xA0,
         "PHI": 0xB0, "SEP": 0xD0, "SEX": 0xE0}
IMM = {"ADCI": 0x7C, "SDBI": 0x7D, "SMBI": 0x7F, "LDI": 0xF8, "ORI": 0xF9, "ANI": 0xFA, "XRI": 0xFB, "ADI": 0xFC,
       "SDI": 0xFD, "SMI": 0xFF}
SHORT = {"BR": 0x30, "BQ": 0x31, "BZ": 0x32, "BDF": 0x33, "BPZ": 0x33, "BGE": 0x33, "B1": 0x34, "B2": 0x35,
         "B3": 0x36, "B4": 0x37, "BNQ": 0x39, "BNZ": 0x3A, "BNF": 0x3B, "BM": 0x3B, "BL": 0x3B, "BN1": 0x3C,
         "BN2": 0x3D, "BN3": 0x3E, "BN4": 0x3F}
LONG = {"LBR": 0xC0, "LBQ": 0xC1, "LBZ": 0xC2, "LBDF": 0xC3, "LBNQ": 0xC9, "LBNZ": 0xCA, "LBNF": 0xCB}
RELAX = {"JMP": ("BR", "LBR"), "JZ": ("BZ", "LBZ"), "JNZ": ("BNZ", "LBNZ"), "JDF": ("BDF", "LBDF"),
         "JGE": ("BDF", "LBDF"), "JNF": ("BNF", "LBNF"), "JLT": ("BNF", "LBNF"), "JQ": ("BQ", "LBQ"),
         "JNQ": ("BNQ", "LBNQ")}
SKIPS = {"SKP", "NBR", "LSKP", "NLBR", "LSNQ", "LSNZ", "LSNF", "LSIE", "LSQ", "LSZ", "LSDF"}
DIRECTIVES = {"ORG", "EQU", "DB", "BYTE", "DW", "WORD", "DS", "ALIGN", "END", "SET"}


class AsmError(Exception):
    pass


# ------------------------------------------------------------------------------------------------ expressions
TOKEN = re.compile(r"\s*(?:(?P<num>0[xX][0-9A-Fa-f]+|\$[0-9A-Fa-f]+|%[01]+|[0-9][0-9A-Fa-f]*[hH]|[01]+[bB](?![0-9A-Fa-f])|[0-9]+)"
                   r"|(?P<chr>'(?:[^'\\]|\\.)')|(?P<id>[A-Za-z_.@][\w.@]*)|(?P<op><<|>>|[-+*/%&|^~()$]))")


def parse_number(t):
    if t[:2] in ("0x", "0X"): return int(t[2:], 16)
    if t[0] == "$": return int(t[1:], 16)
    if t[0] == "%": return int(t[1:], 2)
    if t[-1] in "hH": return int(t[:-1], 16)
    if t[-1] in "bB" and set(t[:-1]) <= set("01"): return int(t[:-1], 2)
    return int(t, 10)


class Expr:
    """recursive-descent expression evaluator; names are looked up through `lookup` (raises KeyError if unknown)"""
    def __init__(self, text, lookup, here):
        self.toks = []; pos = 0; text = text.strip()
        while pos < len(text):
            m = TOKEN.match(text, pos)
            if not m or m.end() == pos: raise AsmError("bad expression: %r" % text)
            if m.group("num"): self.toks.append(("n", parse_number(m.group("num"))))
            elif m.group("chr"):
                c = m.group("chr")[1:-1]
                self.toks.append(("n", ord(c[1]) if c.startswith("\\") else ord(c)))
            elif m.group("id"): self.toks.append(("i", m.group("id")))
            else: self.toks.append(("o", m.group("op")))
            pos = m.end()
        self.i = 0; self.lookup = lookup; self.here = here

    def peek(self): return self.toks[self.i] if self.i < len(self.toks) else (None, None)
    def take(self): t = self.peek(); self.i += 1; return t

    def value(self):
        v = self.p_or()
        if self.i != len(self.toks): raise AsmError("junk in expression")
        return v

    def p_or(self):
        t = self.peek()
        if t[0] == "i" and t[1].upper() in ("HIGH", "LOW"):     # rcasm: HIGH/LOW take the whole rest (high x+64 = high(x+64))
            self.take(); v = self.p_or()
            return (v >> 8) & 0xFF if t[1].upper() == "HIGH" else v & 0xFF
        v = self.p_xor()
        while self.peek() == ("o", "|"): self.take(); v |= self.p_xor()
        return v

    def p_xor(self):
        v = self.p_and()
        while self.peek() == ("o", "^"): self.take(); v ^= self.p_and()
        return v

    def p_and(self):
        v = self.p_shift()
        while self.peek() == ("o", "&"): self.take(); v &= self.p_shift()
        return v

    def p_shift(self):
        v = self.p_add()
        while self.peek() in (("o", "<<"), ("o", ">>")):
            op = self.take()[1]; r = self.p_add(); v = v << r if op == "<<" else v >> r
        return v

    def p_add(self):
        v = self.p_mul()
        while self.peek() in (("o", "+"), ("o", "-")):
            op = self.take()[1]; r = self.p_mul(); v = v + r if op == "+" else v - r
        return v

    def p_mul(self):
        v = self.p_unary()
        while self.peek() in (("o", "*"), ("o", "/"), ("o", "%")):
            op = self.take()[1]; r = self.p_unary()
            if op == "*": v *= r
            elif r == 0: raise AsmError("division by zero")
            elif op == "/": v = int(v / r)
            else: v %= r
        return v

    def p_unary(self):
        t = self.peek()
        if t == ("o", "-"): self.take(); return -self.p_unary()
        if t == ("o", "+"): self.take(); return self.p_unary()
        if t == ("o", "~"): self.take(); return ~self.p_unary()
        if t[0] == "i" and t[1].upper() in ("HIGH", "LOW"):
            self.take(); v = self.p_or()
            return (v >> 8) & 0xFF if t[1].upper() == "HIGH" else v & 0xFF
        return self.p_atom()

    def p_atom(self):
        k, v = self.take()
        if k == "n": return v
        if k == "o" and v == "(":
            r = self.p_or()
            if self.take() != ("o", ")"): raise AsmError("missing )")
            return r
        if k == "o" and v == "$": return self.here
        if k == "i":
            name = v; suffix = None
            if name.endswith(".0") or name.endswith(".1"): name, suffix = name[:-2], name[-1]
            r = self.lookup(name)
            if suffix == "0": r &= 0xFF
            elif suffix == "1": r = (r >> 8) & 0xFF
            return r
        raise AsmError("bad expression")


# ------------------------------------------------------------------------------------------------ source reading
def split_operands(s):
    """split on commas outside quotes and parentheses"""
    out = []; cur = ""; q = None; depth = 0
    for ch in s:
        if q:
            cur += ch
            if ch == q: q = None
        elif ch in "'\"": q = ch; cur += ch
        elif ch == "(": depth += 1; cur += ch
        elif ch == ")": depth -= 1; cur += ch
        elif ch == "," and depth == 0: out.append(cur.strip()); cur = ""
        else: cur += ch
    if cur.strip() or out: out.append(cur.strip())
    return out


def strip_comment(line):
    q = None
    for i, ch in enumerate(line):
        if q:
            if ch == q: q = None
        elif ch in "'\"":
            # a quote starts a string/char only where an operand can start (not inside a name like don't)
            q = ch
        elif ch == ";": return line[:i]
    return line


LABEL = re.compile(r"^([A-Za-z_.@][\w.@]*):")
NAMEEQU = re.compile(r"^([A-Za-z_.@][\w.@]*)\s+(equ|set|macro)\b\s*(.*)$", re.I)


class Line:
    __slots__ = ("file", "num", "text", "label", "op", "args", "addr", "size", "long", "bytes", "macro_depth")

    def __init__(self, file, num, text, label, op, args, depth=0):
        self.file, self.num, self.text, self.label, self.op, self.args = file, num, text, label, op, args
        self.addr = 0; self.size = 0; self.long = False; self.bytes = b""; self.macro_depth = depth


class Assembler:
    def __init__(self, defines=None):
        self.symbols = {}
        for i in range(16):
            self.symbols["R%X" % i] = i; self.symbols["R%d" % i] = i
        self.predefined = set(self.symbols)
        for k, v in (defines or {}).items(): self.symbols[k.upper()] = v
        self.macros = {}; self.lines = []; self.uniq = 0; self.errors = []; self.warnings = []
        self.exec_addr = None

    # ---------------------------------------------------------------- pass 0: read, expand macros, conditionals
    def read(self, path, depth=0):
        if depth > 8: raise AsmError("include nesting too deep")
        base = os.path.dirname(os.path.abspath(path))
        src = open(path, encoding="latin-1").read().splitlines()
        self._expand(src, path, base, depth)

    def _parse(self, raw):
        """-> (label, op, argtext).  'label: op args', 'name equ v' / 'name macro p,..' (no colon), '  op args'"""
        s = strip_comment(raw).strip()
        if not s: return None, None, ""
        label = None
        m = LABEL.match(s)
        if m:
            label = m.group(1); s = s[m.end():].strip()
            if not s: return label, None, ""
        else:
            m2 = NAMEEQU.match(s)
            if m2: return m2.group(1), m2.group(2).upper(), m2.group(3)
        parts = s.split(None, 1)
        return label, parts[0].upper(), (parts[1] if len(parts) > 1 else "")

    def _expand(self, src, path, base, depth, mdepth=0):
        i = 0; cond = []          # stack of (active, seen_true)
        while i < len(src):
            raw = src[i]; num = i + 1; i += 1
            label, op, args = self._parse(raw)
            active = all(c[0] for c in cond)
            if op in ("IF", "IFDEF", "IFNDEF"):
                if not active: cond.append((False, True)); continue
                if op == "IF": t = bool(self._eval_now(args, path, num))
                else:
                    t = args.strip().upper() in self.symbols
                    if op == "IFNDEF": t = not t
                cond.append((t, t)); continue
            if op == "ELSE":
                a, seen = cond.pop(); cond.append((not seen, True)); continue
            if op in ("ENDIF", "ENDI"):
                cond.pop(); continue
            if not active: continue
            if op == "MACRO":
                name = (label or "").upper()
                if not name:   # "MACRO name args" form
                    parts = args.split(None, 1); name = parts[0].upper(); args = parts[1] if len(parts) > 1 else ""
                params = [p.strip().upper() for p in split_operands(args)] if args.strip() else []
                body = []
                while i < len(src):
                    l2, o2, a2 = self._parse(src[i]); i += 1
                    if o2 == "ENDM": break
                    body.append(src[i - 1])
                self.macros[name] = (params, body); continue
            if op == "INCLUDE":
                f = args.strip().strip('"').strip("'")
                p = f if os.path.isabs(f) else os.path.join(base, f)
                if label: self.lines.append(Line(path, num, raw, label, None, ""))
                self.read(p, depth + 1); continue
            if op and op in self.macros:
                params, body = self.macros[op]
                vals = split_operands(args) if args.strip() else []
                if len(vals) > len(params): self.errors.append("%s:%d: too many macro arguments" % (path, num))
                vals += [""] * (len(params) - len(vals))
                self.uniq += 1
                self.lines.append(Line(path, num, raw, label, None, "", mdepth))  # the label, and the call's listing line
                exp = []
                for b in body:
                    t = b.replace("\\@", "_%d" % self.uniq)
                    for p, v in sorted(zip(params, vals), key=lambda pv: -len(pv[0])):
                        t = re.sub(r"(?<![\w.@])%s(?![\w@])" % re.escape(p), lambda _m, v=v: v, t, flags=re.I)
                    exp.append(t)
                if mdepth > 20: raise AsmError("macro nesting too deep")
                self._expand_macro(exp, path, num, base, depth, mdepth + 1)
                continue
            if op == "END":
                if args.strip(): self.lines.append(Line(path, num, raw, label, "END", args, mdepth))
                break
            self.lines.append(Line(path, num, raw, label, op, args, mdepth))
            if op in ("EQU", "SET") and label:            # make equates usable by later IFs
                try: self.symbols[label.upper()] = self._eval_now(args, path, num)
                except AsmError: pass

    def _expand_macro(self, exp, path, num, base, depth, mdepth):
        start = len(self.lines)
        self._expand(exp, path, base, depth, mdepth)
        for l in self.lines[start:]:
            l.num = num; l.macro_depth = max(l.macro_depth, mdepth)

    def _eval_now(self, text, path, num):
        def look(n):
            n = n.upper()
            if n not in self.symbols: raise AsmError("%s:%d: %s not defined before this IF/EQU" % (path, num, n))
            return self.symbols[n]
        return Expr(text, look, 0).value()

    # ---------------------------------------------------------------- passes
    def lookup_factory(self, final):
        def look(name):
            n = name.upper()
            if n in self.symbols: return self.symbols[n]
            if final: raise AsmError("undefined symbol %s" % name)
            return 0
        return look

    def evaluate(self, text, here, final):
        return Expr(text, self.lookup_factory(final), here).value()

    def size_of(self, l, here, final):
        op = l.op
        if op is None: return 0
        if op in NOARG or op in REGOP or op in ("OUT", "INP"): return 1
        if op in IMM or op in SHORT: return 2
        if op in LONG: return 3
        if op in RELAX: return 3 if l.long else 2
        if op in ("DB", "BYTE"): return sum(len(self._dbitem(a, here, False)) for a in split_operands(l.args))
        if op in ("DW", "WORD"): return 2 * len(split_operands(l.args))
        if op == "DS": return self.evaluate(l.args, here, final)
        if op == "ALIGN":
            n = self.evaluate(l.args, here, final); return (-here) % n if n else 0
        if op in ("ORG", "EQU", "SET", "END"): return 0
        raise AsmError("unknown instruction %s" % op)

    def _dbitem(self, a, here, final):
        a = a.strip()
        if len(a) >= 2 and a[0] == '"' and a[-1] == '"':
            return a[1:-1].replace('\\"', '"').encode("latin-1")
        if len(a) >= 3 and a[0] == "'" and a[-1] == "'" and len(a) != 3 and not (len(a) == 4 and a[1] == "\\"):
            return a[1:-1].encode("latin-1")          # rcasm: 'text' in DB is a string
        v = self.evaluate(a, here, final)
        if not -256 < v < 256: raise AsmError("byte value out of range: %s = %d" % (a, v))
        return bytes([v & 0xFF])

    def layout(self, final):
        """assign addresses; returns True if any symbol changed"""
        here = 0; changed = False; seen = {}
        for l in self.lines:
            if l.label and l.op != "SET":
                k = l.label.upper()
                if k in seen and seen[k] is not l:
                    raise AsmError("%s:%d: %s is defined twice (also %s:%d; names are not case sensitive)"
                                   % (l.file, l.num, l.label, seen[k].file, seen[k].num))
                seen[k] = l
                if k in self.predefined:
                    raise AsmError("%s:%d: %s is a register name" % (l.file, l.num, l.label))
            if l.op == "ORG":
                here = self.evaluate(l.args, here, final) & 0xFFFF
            if l.label and l.op not in ("EQU", "SET"):
                k = l.label.upper()
                if k.startswith("."):
                    raise AsmError("local labels are not supported")
                if self.symbols.get(k) != here: changed = True
                self.symbols[k] = here
            if l.op in ("EQU", "SET"):
                if not l.label: raise AsmError("EQU without a name")
                v = self.evaluate(l.args, here, final)
                k = l.label.upper()
                if self.symbols.get(k) != v: changed = True
                self.symbols[k] = v
            l.addr = here
            l.size = self.size_of(l, here, final)
            here = (here + l.size) & 0xFFFF if l.op != "ORG" else here
        return changed

    def assemble(self):
        if self.errors: return
        try:
            for _ in range(50):
                ch = self.layout(False)
                grew = False
                for l in self.lines:
                    if l.op in RELAX and not l.long:
                        try: t = self.evaluate(l.args, l.addr, False)
                        except AsmError: continue
                        if (t >> 8) != ((l.addr + 1) >> 8) & 0xFF:
                            l.long = True; grew = True
                if not ch and not grew: break
            self.layout(True)
        except AsmError as e:
            self.errors.append(str(e)); return
        prev = None
        for l in self.lines:
            if l.op in RELAX and l.long and prev is not None and prev.op in SKIPS:
                self.errors.append("%s:%d: %s became a long jump right after %s, which skips a fixed size\n    %s"
                                   % (l.file, l.num, l.op, prev.op, l.text.strip()))
            if l.op is not None: prev = l
            try:
                l.bytes = self.encode(l)
                if len(l.bytes) != l.size and l.op not in ("DS", "ALIGN"):
                    raise AsmError("internal: size %d != %d" % (len(l.bytes), l.size))
            except AsmError as e:
                self.errors.append("%s:%d: %s\n    %s" % (l.file, l.num, e, l.text.strip()))
            except (KeyError, IndexError, ValueError) as e:
                self.errors.append("%s:%d: %s\n    %s" % (l.file, l.num, e, l.text.strip()))

    def reg(self, text, here):
        v = self.evaluate(text, here, True)
        if not 0 <= v <= 15: raise AsmError("register out of range: %s" % text)
        return v

    def encode(self, l):
        op = l.op; a = l.args; here = l.addr
        if op is None or op in ("ORG", "EQU", "SET"): return b""
        if op == "END":
            self.exec_addr = self.evaluate(a, here, True) if a.strip() else None; return b""
        if op in NOARG:
            if a.strip(): raise AsmError("%s takes no operand" % op)
            return bytes([NOARG[op]])
        if op in REGOP:
            r = self.reg(a, here)
            if op == "LDN" and r == 0: raise AsmError("LDN R0 is IDL")
            return bytes([REGOP[op] | r])
        if op in ("OUT", "INP"):
            p = self.evaluate(a, here, True)
            if not 1 <= p <= 7: raise AsmError("port must be 1-7")
            return bytes([(0x60 if op == "OUT" else 0x68) + p])
        if op in IMM:
            v = self.evaluate(a, here, True)
            if not -256 < v < 256: raise AsmError("immediate out of range: %s = %d" % (a, v))
            return bytes([IMM[op], v & 0xFF])
        if op in SHORT or (op in RELAX and not l.long):
            code = SHORT[op] if op in SHORT else SHORT[RELAX[op][0]]
            t = self.evaluate(a, here, True) & 0xFFFF
            if (t >> 8) != ((here + 1) >> 8) & 0xFF:
                raise AsmError("short branch to %04X out of page (branch at %04X)" % (t, here))
            return bytes([code, t & 0xFF])
        if op in LONG or op in RELAX:
            code = LONG[op] if op in LONG else LONG[RELAX[op][1]]
            t = self.evaluate(a, here, True) & 0xFFFF
            return bytes([code, t >> 8, t & 0xFF])
        if op in ("DB", "BYTE"):
            return b"".join(self._dbitem(x, here, True) for x in split_operands(a))
        if op in ("DW", "WORD"):
            out = b""
            for x in split_operands(a):
                v = self.evaluate(x, here, True) & 0xFFFF; out += bytes([v >> 8, v & 0xFF])
            return out
        if op in ("DS", "ALIGN"): return b""
        raise AsmError("unknown instruction %s" % op)

    # ---------------------------------------------------------------- output
    def image(self):
        mem = {}
        for l in self.lines:
            for i, b in enumerate(l.bytes): mem[(l.addr + i) & 0xFFFF] = b
        return mem

    def listing(self):
        out = []
        for l in self.lines:
            bs = l.bytes
            first = " ".join("%02x" % b for b in bs[:4])
            if l.op in ("EQU", "SET"):
                out.append("%5d %04x:             %s" % (l.num, self.symbols.get(l.label.upper(), 0) & 0xFFFF, l.text.rstrip()))
                continue
            text = l.text.rstrip() if l.macro_depth == 0 or l.op is None else "        +" + (("%s:" % l.label + " ") if l.label else "") + ("%s %s" % (l.op or "", l.args)).rstrip()
            if l.macro_depth and l.op is None and not l.label: continue
            out.append("%5d %04x: %-12s %s" % (l.num, l.addr, first, text))
            for k in range(4, len(bs), 4):
                out.append("      %04x: %-12s" % (l.addr + k, " ".join("%02x" % b for b in bs[k:k + 4])))
        out.append("")
        for k in sorted(self.symbols):
            if re.fullmatch(r"R[0-9A-F]|R1[0-5]|R[0-9]", k): continue
            out.append("%04x: %s" % (self.symbols[k] & 0xFFFF, k))
        return "\n".join(out) + "\n"


def to_intel_hex(mem):
    lines = []
    addrs = sorted(mem)
    i = 0
    while i < len(addrs):
        start = addrs[i]; chunk = [mem[start]]; i += 1
        while i < len(addrs) and addrs[i] == start + len(chunk) and len(chunk) < 16:
            chunk.append(mem[addrs[i]]); i += 1
        rec = bytes([len(chunk), start >> 8, start & 0xFF, 0]) + bytes(chunk)
        lines.append(":%s%02X" % (rec.hex().upper(), (-sum(rec)) & 0xFF))
    lines.append(":00000001FF")
    return "\n".join(lines) + "\n"


def assemble_file(path, defines=None):
    a = Assembler(defines)
    try:
        a.read(path)
    except (AsmError, OSError) as e:
        a.errors.append(str(e))
    a.assemble()
    return a


def selftest():
    """assemble HBIOS (firmware/hbios/v1.0.4/sec1.asm after cpp) and compare with the rcasm build in v0.9/sec1.img"""
    import subprocess, tempfile
    root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    src = os.path.join(root, "firmware/hbios/v1.0.4/sec1.asm")
    ref = os.path.join(root, "firmware/hbios/v0.9/sec1.img")
    pre = subprocess.run(["cpp", "-P", src], capture_output=True, text=True).stdout
    tmp = tempfile.mktemp(suffix=".asm"); open(tmp, "w").write(pre)
    a = assemble_file(tmp); os.remove(tmp)
    if a.errors: print("\n".join(a.errors)); return 1
    mem = a.image(); want = {}
    for line in open(ref):
        line = line.strip()
        if not line.startswith(":"): continue
        raw = bytes.fromhex(line[1:]); n, ad = raw[0], raw[1] << 8 | raw[2]
        if raw[3] == 0:
            for k in range(n): want[ad + k] = raw[4 + k]
    ok = mem == want
    print("sec1.asm: %d bytes, %s rcasm's sec1.img" % (len(mem), "IDENTICAL to" if ok else "DIFFERENT from"))
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", nargs="?")
    ap.add_argument("-o", "--out"); ap.add_argument("--hex"); ap.add_argument("--lst"); ap.add_argument("--sym")
    ap.add_argument("--elfos", help="write an ELF/OS executable (6-byte header)")
    ap.add_argument("--exec", help="ELF/OS exec address (default: END's operand, else the load address)")
    ap.add_argument("-D", action="append", default=[], help="NAME=VALUE")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest: return selftest()
    if not a.source: ap.error("no source file")
    defs = {}
    for d in a.D:
        k, _, v = d.partition("="); defs[k] = int(v, 0) if v else 1
    asm = assemble_file(a.source, defs)
    for w in asm.warnings: print("warning:", w, file=sys.stderr)
    if asm.errors:
        for e in asm.errors[:50]: print("error:", e, file=sys.stderr)
        print("%d error(s)" % len(asm.errors), file=sys.stderr)
        return 1
    mem = asm.image()
    lo, hi = (min(mem), max(mem)) if mem else (0, -1)
    data = bytes(mem.get(x, 0) for x in range(lo, hi + 1))
    if a.out: open(a.out, "wb").write(data)
    if a.hex: open(a.hex, "w").write(to_intel_hex(mem))
    if a.lst: open(a.lst, "w").write(asm.listing())
    if a.sym:
        with open(a.sym, "w") as f:
            for k in sorted(asm.symbols, key=lambda k: asm.symbols[k]):
                if not re.fullmatch(r"R[0-9A-F]|R1[0-5]|R[0-9]", k): f.write("%04X %s\n" % (asm.symbols[k] & 0xFFFF, k))
    if a.elfos:
        ex = int(a.exec, 16) if a.exec else (asm.exec_addr if asm.exec_addr is not None else lo)
        hdr = bytes([lo >> 8, lo & 0xFF, len(data) >> 8, len(data) & 0xFF, ex >> 8, ex & 0xFF])
        open(a.elfos, "wb").write(hdr + data)
    nlong = sum(1 for l in asm.lines if l.op in RELAX and l.long)
    nrel = sum(1 for l in asm.lines if l.op in RELAX)
    print("%04X-%04X, %d bytes; %d of %d relaxing jumps long" % (lo, hi, len(data), nlong, nrel))
    return 0


if __name__ == "__main__":
    sys.exit(main())
