# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-06
"""1802 instruction tests (RCA CDP1802 user manual semantics)."""
import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from s5emu.cpu import CPU1802, IllegalOp


class Bus:
    def __init__(self, prog, at=0):
        self.m = bytearray(65536); self.m[at:at + len(prog)] = bytes(prog); self.outs = []; self.efs = set(); self.inval = 0x5A
    def read(self, a): return self.m[a]
    def write(self, a, v): self.m[a] = v
    def out(self, n, v): self.outs.append((n, v))
    def inp(self, n): return self.inval
    def ef(self, n): return n in self.efs


def run(prog, steps=None, setup=None, at=0):
    b = Bus(prog, at); c = CPU1802(b); c.R[0] = at
    if setup: setup(c, b)
    for _ in range(steps or 999):
        if c.idle: break
        c.step()
    return c, b


class T(unittest.TestCase):
    def test_ldi_plo_phi_glo(self):
        c, _ = run([0xF8, 0x12, 0xB5, 0xF8, 0x34, 0xA5, 0x00])
        self.assertEqual(c.R[5], 0x1234)

    def test_add_carry(self):
        c, _ = run([0xF8, 0xF0, 0xFC, 0x20, 0x00]); self.assertEqual((c.D, c.DF), (0x10, 1))

    def test_sd_sm_borrow(self):
        c, _ = run([0xF8, 0x05, 0xFD, 0x03, 0x00]); self.assertEqual((c.D, c.DF), (0xFE, 0))   # SDI: 03 - 05
        c, _ = run([0xF8, 0x05, 0xFF, 0x03, 0x00]); self.assertEqual((c.D, c.DF), (0x02, 1))   # SMI: 05 - 03
        c, _ = run([0xF8, 0x03, 0xFF, 0x05, 0x00]); self.assertEqual((c.D, c.DF), (0xFE, 0))   # SMI: 03 - 05

    def test_smb_uses_borrow(self):
        # DF=0 (borrow) -> 05 - 03 - 1 = 01
        c, _ = run([0xF8, 0x00, 0xFE, 0xF8, 0x05, 0x7F, 0x03, 0x00]); self.assertEqual((c.D, c.DF), (0x01, 1))

    def test_shifts(self):
        c, _ = run([0xF8, 0x81, 0xF6, 0x00]); self.assertEqual((c.D, c.DF), (0x40, 1))          # SHR
        c, _ = run([0xF8, 0x81, 0xFE, 0x00]); self.assertEqual((c.D, c.DF), (0x02, 1))          # SHL
        c, _ = run([0xF8, 0x01, 0xF6, 0xF8, 0x02, 0x76, 0x00]); self.assertEqual((c.D, c.DF), (0x81, 0))  # SHRC with DF=1

    def test_short_branch_same_page(self):
        c, _ = run([0x30, 0x05, 0x00, 0x00, 0x00, 0x7B, 0x00]); self.assertEqual(c.Q, 1)

    def test_short_branch_operand_on_next_page(self):
        # BR at 00FF: its operand is at 0100, so the target is on page 01
        prog = bytearray(0x200); prog[0xFF] = 0x30; prog[0x100] = 0x10; prog[0x110] = 0x7B; prog[0x111] = 0x00
        c, _ = run(prog, at=0, setup=lambda c, b: c.R.__setitem__(0, 0xFF)); self.assertEqual(c.Q, 1)

    def test_long_branch_and_skips(self):
        c, _ = run([0xC0, 0x00, 0x05, 0x00, 0x00, 0x7B, 0x00]); self.assertEqual(c.Q, 1)       # LBR
        c, _ = run([0xF8, 0x00, 0xCE, 0x7B, 0x7B, 0x00]); self.assertEqual(c.Q, 0)             # LSZ skips both SEQs
        c, _ = run([0xF8, 0x01, 0xCE, 0x00, 0x00, 0x7B, 0x00]); self.assertEqual(c.Q, 0)       # LSZ not taken -> IDL

    def test_mark_ret(self):
        # P=0 X=2: MARK pushes T=(X,P)=(2,0) at R2 and sets X=P=0; then SEX 2, IRX, RET restores X=2 P=0 IE=1
        def s(c, b): c.R[2] = 0x80; c.X = 2
        c, b = run([0x79, 0xE2, 0x60, 0x70, 0x00], setup=s)
        self.assertEqual(b.m[0x80], 0x20); self.assertEqual((c.X, c.P, c.IE), (2, 0, 1))

    def test_out_inp(self):
        def s(c, b): c.R[3] = 0x40; c.X = 3; b.m[0x40] = 0x99
        c, b = run([0x64, 0x6D, 0x00], setup=s)     # OUT 4 (M(R3) then R3+1), INP 5 -> M(R3), D
        self.assertEqual(b.outs, [(4, 0x99)]); self.assertEqual((c.D, b.m[0x41], c.R[3]), (0x5A, 0x5A, 0x41))

    def test_ef_branch(self):
        c, _ = run([0x36, 0x04, 0x00, 0x00, 0x7B, 0x00], setup=lambda c, b: b.efs.add(3)); self.assertEqual(c.Q, 1)
        c, _ = run([0x36, 0x04, 0x00, 0x00, 0x7B, 0x00]); self.assertEqual(c.Q, 0)

    def test_interrupt(self):
        def s(c, b): c.R[1] = 0x20; c.int_line = True; c.X = 5
        b = Bus([0xC4, 0x00]); b.m[0x20] = 0x7B; b.m[0x21] = 0x00; c = CPU1802(b); s(c, b)
        c.step(); self.assertEqual((c.P, c.X, c.IE, c.T), (1, 2, 0, 0x50)); c.int_line = False; c.step(); self.assertEqual(c.Q, 1)

    def test_illegal_68(self):
        """68 is not an 1802 instruction, but the 1802 runs it: an INP with no port, the bus to M(R(X)) and D, in two
        machine cycles; stop_on_68 makes it stop there instead, with PC still on it"""
        def s(c, b): c.X = 3; c.R[3] = 0x40; b.m[0x40] = 0x11; c.D = 0x22; b.inp = None    # no port is read: FF floats
        c, b = run([0x68, 0x00], setup=s)
        self.assertEqual((c.D, b.m[0x40], c.R[3], c.R[0], c.cycles), (0xFF, 0xFF, 0x40, 2, 4))   # 68, then IDL
        def t(c, b): c.stop_on_68 = True
        b = Bus([0x68]); c = CPU1802(b); t(c, b)
        with self.assertRaises(IllegalOp): c.step()
        self.assertEqual((c.R[0], c.instructions, c.cycles), (0, 0, 0))

    def test_cycles(self):
        c, _ = run([0xF8, 0x01, 0xC4, 0x00]); self.assertEqual(c.cycles, 2 + 3 + 2)


if __name__ == "__main__":
    unittest.main(verbosity=1)
