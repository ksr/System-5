#!/usr/bin/env python3
# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-12
"""Check HBIOS v1.0.5's D command (the monitor's disassembler) in the emulator, line for line against s5emu's own
disassembler: every opcode, the whole ROM page by page through the pauses, the ways to write a range, one screenful
with no end, the keys that stop it at a pause, the H list, and that ! and ? still work. About 7 minutes.

  python3 firmware/hbios/v1.0.5/check_disasm.py
"""
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "software", "s5emu"))
from s5emu.machine import Machine
from s5emu.shell import Shell
from s5emu.disasm import disasm

m = Machine(cpu_rom=os.path.join(ROOT, 'software', 's5emu', 'roms', 'hbios-1.0.5.rom')); sh = Shell(m)
run = lambda n=200_000: sh.d.run(max_instructions=n)
rows = lambda: [l.rstrip() for l in m.video.lines()]
run(2_000_000)

def expected(start, end):
    out, a = [], start
    while True:
        n, t = disasm(m.peek, a)
        t = t.split(';')[0].rstrip()                    # the emulator adds a comment to 68
        b = ' '.join('%02X' % m.peek((a + k) & 0xFFFF) for k in range(n))
        out.append('%04X  %-8s  %s' % (a, b, t))
        nxt = a + n
        if nxt > 0xFFFF or nxt > end: break
        a = nxt
    return out

def drive(cmd, keys_at_pause=' ', limit=4000):
    """type cmd; at each pause press keys_at_pause; collect the lines; return (lines, pauses, ended_with_prompt)"""
    m.kbd.press(cmd + '\n'); got, pauses = [], 0
    for _ in range(limit):
        run(150_000)
        r = rows()
        if r[-1].startswith('-- more --'):
            got.extend(r[-15:-1]); pauses += 1
            if pauses == 1:                               # the first page: drop the command line if it shows
                pass
            m.kbd.press(keys_at_pause)
            continue
        if r[-1] == 'test>' and not m.kbd.ready():
            # the last page: the lines after the last pause (or after the command), up to the prompt
            got.append(None); got.extend(r[:-1])
            return got, pauses, True
    return got, pauses, False

def tail_lines(got):
    """resolve the final page: keep its lines from the first one not already seen"""
    if None not in got: return got
    i = got.index(None); head, last = got[:i], got[i + 1:]
    k = 0
    if head:
        # the last screen still shows lines of the page before; skip up to the last line already collected
        for j in range(len(last)):
            if last[j] == head[-1]: k = j + 1
    else:
        for j in range(len(last)):
            if last[j].lstrip().upper().startswith('TEST>D'): k = j + 1
    return head + [l for l in last[k:] if l]

def check(name, cmd, start, end, keys=' '):
    got, pauses, ended = drive(cmd, keys)
    got = tail_lines(got)
    want = expected(start, end)
    bad = [(i, g, w) for i, (g, w) in enumerate(zip(got, want)) if g != w]
    ok = ended and not bad and len(got) == len(want)
    print('%-34s %s: %d lines, %d pauses%s' % (name, 'PASS' if ok else 'FAIL', len(got), pauses,
          '' if ok else '; want %d lines, first difference %r' % (len(want), bad[:1] or (got[-2:], want[-2:]))))
    return ok

results = []
# 1. every opcode, laid out as a stream with its own operands, at 0400
a = 0x400; ops = []
for op in range(256):
    m.write(a, op); m.write(a + 1, 0x12 + op % 7); m.write(a + 2, 0x34 + op % 11)
    n, _ = disasm(m.peek, a); ops.append(a); a += n
end = a - 1
results.append(check('every opcode (0400-%04X)' % end, 'D 0400:%04X' % end, 0x400, end))
# 2. the whole ROM
results.append(check('the whole ROM', 'D F000:FFFF', 0xF000, 0xFFFF))
# 3. the ways to write it
results.append(check('DF940:F960', 'DF940:F960', 0xF940, 0xF960))
results.append(check('d f940-f960 (lower case, dash)', 'd f940-f960', 0xF940, 0xF960))
results.append(check('D F940 F960 (space)', 'D F940 F960', 0xF940, 0xF960))
# 4. no end: one screenful, no pause
got, pauses, ended = drive('D F900')
got = tail_lines(got); want = expected(0xF900, 0xFFFF)[:14]
ok = ended and pauses == 0 and got == want
print('%-34s %s: %d lines, %d pauses' % ('D F900 (one screenful)', 'PASS' if ok else 'FAIL', len(got), pauses)); results.append(ok)
# 5. the stop keys at the first pause
for key, name in (('\x1b', 'Esc'), ('q', 'q'), ('\x03', 'Ctrl-C')):
    m.kbd.press('D F000:F3FF\n'); stopped = False
    for _ in range(400):
        run(150_000)
        if rows()[-1].startswith('-- more --'):
            m.kbd.press(key)
            for _ in range(40):
                run(150_000)
                if rows()[-1] == 'test>' and not m.kbd.ready(): stopped = True; break
            break
    print('%-34s %s' % ('%s at the pause stops' % name, 'PASS' if stopped else 'FAIL')); results.append(stopped)
# 6. the help lists D, and the old commands still work
m.kbd.press('H\n'); run(1_500_000)
ok = ' D start:end     disassemble, a screenful at a time' in rows() and ' D start         disassemble one screenful' in rows()
print('%-34s %s' % ('H lists D', 'PASS' if ok else 'FAIL')); results.append(ok)
m.kbd.press('!0300 AA BB\n?0300\n'); run(2_000_000)
ok = any(l.startswith('0300: AA BB') for l in rows())
print('%-34s %s' % ('! and ? still work', 'PASS' if ok else 'FAIL')); results.append(ok)
print('ALL PASS' if all(results) else 'SOME FAILED')
sys.exit(0 if all(results) else 1)
