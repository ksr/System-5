; GBASIC 1.0 - an integer BASIC for Ken Rother's System-5 under ELF/OS, with VIDEO-G graphics.
; Written for System-5 by Claude (Anthropic), 2026-11-01.  Build: python3 software/gbasic/build.py
;
; An ELF/OS program: it loads at 2000h and needs RAM to 6FFFh (the text screen is at 7000h).

            include "defs.inc"
            include "main.asm"
            include "token.asm"
            include "list.asm"
            include "edit.asm"
            include "exec.asm"
            include "expr.asm"
            include "gfx.asm"
            include "file.asm"
            include "tables.inc"
prog:                                   ; the program: a dummy line 0, the lines, a 0; then the arrays
            include "bss.asm"
