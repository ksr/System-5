; GBASIC - definitions, macros and the memory map.  Ken Rother's System-5, by Claude (Anthropic), 2026-11-01.

; ------------------------------------------------------------------ registers
; R2 stack (X = 2), R3 PC, R4/R5 SCRT call/return, R6 link (Mike Riley's BIOS SCRT; RE.0 is used by it).
tp          equ     rb              ; text pointer: the token being interpreted
acc         equ     rd              ; expression value

; ------------------------------------------------------------------ ELF/OS kernel and BIOS
o_wrmboot   equ     0303h
o_open      equ     0306h
o_read      equ     0309h
o_write     equ     030ch
o_close     equ     0312h
o_opendir   equ     0315h
o_delete    equ     0318h
f_type      equ     0ff03h          ; BIOS: type D (HBIOS screen)

; ------------------------------------------------------------------ System-5 / VIDEO-G hardware
KBDPORT     equ     1               ; the IO card (6845 card machines): INP 1 = key, EF3 = a key waits
VGKEY       equ     7802h           ; VIDEO-G (memory-mapped, 2026-11-17): the key; reading it clears KEY-READY (EF3)
VGCSR      equ     7804h           ; VIDEO-G: status (read) / control (write)
VGY         equ     7806h           ; VIDEO-G GFX: the Y register (write) / the mouse byte (read)
SCREEN      equ     7000h           ; text RAM (64 columns)
GWIN        equ     7C00h           ; graphics window: pixel line Y, 64 bytes
CTL_TEXTOFF equ     01h
CTL_GFXON   equ     02h
CTL_XOR     equ     04h
CTL_DPAGE   equ     08h
CTL_CPAGE   equ     10h
ST_MONITOR  equ     10h             ; status: 1 = IBM 5151 (512 x 256)
ST_GFX      equ     20h             ; status: GFX board fitted
ST_VSYNC    equ     04h

; ------------------------------------------------------------------ tokens below 80h (keywords: tables.inc)
TK_EOL      equ     00h
TK_NUM      equ     01h             ; + 2 bytes, decimal literal (0-65535)
TK_HEX      equ     02h             ; + 2 bytes, &H literal
TK_VAR      equ     03h             ; + slot*2: a variable
TK_ARR      equ     04h             ; + slot*2: an array (followed by '(')

; ------------------------------------------------------------------ limits
MAXVARS     equ     96              ; variable names (scalars and arrays together)
LINEMAX     equ     127             ; characters in a typed line
STACKTOP    equ     6fffh           ; machine stack (grows down to 6F00)
STACKLOW    equ     6f30h           ; expressions stop with "Too complex" below this
MEMTOP      equ     6900h           ; program and arrays end below this (bss.asm above)
COLS        equ     64              ; screen width (both video cards)

; ------------------------------------------------------------------ error numbers (msgtab order)
E_SYNTAX    equ     1
E_MEMORY    equ     2
E_NOLINE    equ     3
E_RETURN    equ     4
E_NEXT      equ     5
E_DIVZERO   equ     6
E_SUBSCR    equ     7
E_REDIM     equ     8
E_DATA      equ     9
E_VALUE     equ     10
E_CONT      equ     11
E_COMPLEX   equ     12
E_NOGFX     equ     13
E_FILE      equ     14
E_LONG      equ     15
E_OVERFLOW  equ     16
E_VARS      equ     17
E_NOTFOUND  equ     18
E_DIRECT    equ     19
E_BREAK     equ     20              ; not an error: "Break in nnn"

; ------------------------------------------------------------------ macros
call        macro   target          ; SCRT call
            sep     r4
            dw      target
            endm
rtn         macro                   ; SCRT return
            sep     r5
            endm
ldiw        macro   reg, value      ; reg = 16-bit constant
            ldi     high value
            phi     reg
            ldi     low value
            plo     reg
            endm
mov         macro   dst, src        ; dst = src (16 bits)
            ghi     src
            phi     dst
            glo     src
            plo     dst
            endm
push        macro   reg             ; push 16 bits (X = 2)
            glo     reg
            stxd
            ghi     reg
            stxd
            endm
pop         macro   reg             ; pop 16 bits (X = 2)
            irx
            ldxa
            phi     reg
            ldx
            plo     reg
            endm
zpage       macro   reg             ; reg.1 = the page of the zero-page variables
            ldi     high zp
            phi     reg
            endm
zp_at       macro   reg, var        ; reg = address of a zero-page variable
            ldi     high zp
            phi     reg
            ldi     low var
            plo     reg
            endm
error       macro   num             ; raise error num (never returns)
            ldi     num
            lbr     raise
            endm
