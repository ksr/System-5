# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-06
"""1802 disassembler: disasm(read, addr) -> (length, text). Mnemonics as in RCA's manual / rcasm."""
_R = ["LDN", "INC", "DEC", None, "LDA", "STR", None, None, "GLO", "GHI", "PLO", "PHI", None, "SEP", "SEX", None]
_SB = ["BR", "BQ", "BZ", "BDF", "B1", "B2", "B3", "B4", "SKP", "BNQ", "BNZ", "BNF", "BN1", "BN2", "BN3", "BN4"]
_LB = ["LBR", "LBQ", "LBZ", "LBDF", "NOP", "LSNQ", "LSNZ", "LSNF", "LSKP", "LBNQ", "LBNZ", "LBNF", "LSIE", "LSQ", "LSZ", "LSDF"]
_7 = ["RET", "DIS", "LDXA", "STXD", "ADC", "SDB", "SHRC", "SMB", "SAV", "MARK", "REQ", "SEQ", "ADCI", "SDBI", "SHLC", "SMBI"]
_F = ["LDX", "OR", "AND", "XOR", "ADD", "SD", "SHR", "SM", "LDI", "ORI", "ANI", "XRI", "ADI", "SDI", "SHL", "SMI"]


def disasm(read, addr, symbols=None):
    sym = (lambda a: symbols.get(a, "%04X" % a)) if symbols else (lambda a: "%04X" % a)
    op = read(addr); i, n = op >> 4, op & 15
    if op == 0: return 1, "IDL"
    if op == 0xD4:                          # SCRT convention (Mike Riley's BIOS, HBIOS, ELF/OS): SEP R4 + DW target = CALL
        t = read((addr + 1) & 0xFFFF) << 8 | read((addr + 2) & 0xFFFF)
        return 3, "CALL %s" % sym(t)
    if op == 0xD5: return 1, "RETN"           # SCRT return (SEP R5)
    if _R[i]: return 1, "%s R%X" % (_R[i], n)
    if i == 3:
        if n == 8: return 1, "SKP"
        t = ((addr + 1) & 0xFF00) | read((addr + 1) & 0xFFFF)
        return 2, "%s %s" % (_SB[n], sym(t))
    if i == 6:
        if n == 0: return 1, "IRX"
        if n == 8: return 1, "DB 68H  ; 1806 prefix"
        return 1, ("OUT %d" % n) if n < 8 else ("INP %d" % (n - 8))
    if i == 7:
        if n in (12, 13, 15): return 2, "%s %02XH" % (_7[n], read((addr + 1) & 0xFFFF))
        return 1, _7[n]
    if i == 12:
        if n == 4 or n & 4 or n == 8: return 1, _LB[n]
        t = read((addr + 1) & 0xFFFF) << 8 | read((addr + 2) & 0xFFFF)
        return 3, "%s %s" % (_LB[n], sym(t))
    if i == 15 and n in (8, 9, 10, 11, 12, 13, 15): return 2, "%s %02XH" % (_F[n], read((addr + 1) & 0xFFFF))
    return 1, _F[n]


def listing(read, addr, count, symbols=None):
    out = []
    for _ in range(count):
        ln, text = disasm(read, addr, symbols)
        out.append((addr, bytes(read((addr + k) & 0xFFFF) for k in range(ln)), text)); addr = (addr + ln) & 0xFFFF
    return out
