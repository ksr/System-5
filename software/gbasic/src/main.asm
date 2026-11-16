; GBASIC - entry, console, line editor, errors, the main loop.

            org     2000h
            jmp     start               ; ELF/OS runs programs at their exec address (2000)
            db      11,1                ; date for ELF/OS VER: 11/1/2026
            dw      2026
signon:     db      "GBASIC 1.0 for System-5",0

peekc       macro                       ; D = the byte on top of the stack (R2 + 1), R2 unchanged
            irx
            ldx
            dec     r2
            endm

; ------------------------------------------------------------------ cold start
; Called by the kernel (SCRT) with RA -> the command line arguments.
start:      sex     r3                  ; interrupts off: nothing may interrupt us
            dis
            db      23h                 ; X = 2, P = 3
            ghi     ra                  ; keep the argument pointer
            phi     rf
            glo     ra
            plo     rf
            ldiw    r2, STACKTOP
            ldiw    r9, zp              ; clear the zero page
            ldi     0
            plo     rc
zclr:       ldi     0
            str     r9
            inc     r9
            dec     rc
            glo     rc
            jnz     zclr
            zp_at   r9, argptr
            ghi     rf
            str     r9
            inc     r9
            glo     rf
            str     r9
            zp_at   r9, rndseed         ; a non-zero seed
            ldi     5ah
            str     r9
            inc     r9
            ldi     0a5h
            str     r9
            zp_at   r9, memlim
            ldi     high MEMTOP
            str     r9
            inc     r9
            ldi     low MEMTOP
            str     r9
            call    vg_detect           ; VIDEO-G? graphics? (control = 00: text on, graphics off)
            call    do_new              ; empty program, no variables
            call    newline
            ldiw    rf, signon
            call    puts
            call    newline
            call    vg_banner           ; "VIDEO-G graphics 512 x 200" / "No graphics"
            call    fre_value
            call    printu
            ldiw    rf, m_free
            call    puts
            call    newline
            ; a file name on the command line: LOAD it and RUN
            zp_at   r9, argptr
            lda     r9
            phi     rf
            ldn     r9
            plo     rf
argsk:      ldn     rf                  ; skip spaces
            xri     ' '
            jnz     argsk2
            inc     rf
            jmp     argsk
argsk2:     ldn     rf
            lbz     ready               ; no argument
            call    load_named          ; RF -> name (ends at a space or 0)
            lbr     run_program
m_free:     db      " bytes free",0

; ------------------------------------------------------------------ warm start: "Ready", then read lines
ready:      ldiw    r2, STACKTOP
            sex     r2
            zp_at   r9, locptr          ; a LOCATEd PRINT ending in ';' is over
            ldi     0
            str     r9
            inc     r9
            str     r9
            call    vg_textsafe         ; text back on if a program turned it off
            call    crlf_if
            ldiw    rf, m_ready
            call    puts
            call    newline
mainloop:   ldiw    r2, STACKTOP
            sex     r2
            zp_at   r9, outmode         ; output to the screen
            ldi     0
            str     r9
            zp_at   r9, curline         ; direct mode
            ldi     0
            str     r9
            inc     r9
            str     r9
            call    getline             ; linebuf
            lbdf    mainloop            ; Ctrl-C: nothing
            call    tokenize            ; tokbuf; DF = 1: it had a line number
            lbdf    numbered
            ldiw    tp, tokbuf
            ldn     tp
            lbz     mainloop            ; empty line
            lbr     exec_line           ; run it (direct mode); ends at ready
numbered:   call    edit_line           ; insert / replace / delete
            lbr     mainloop
m_ready:    db      "Ready",0

; ------------------------------------------------------------------ errors
; raise: D = error number.  Prints "?message[ in line]" and goes to ready.
raise:      plo     re                  ; (no SCRT call before it is used)
            ldiw    r2, STACKTOP
            sex     r2
            glo     re
            stxd                        ; keep the number
            zp_at   r9, outmode         ; back to the screen (an error during SAVE)
            ldi     0
            str     r9
            zp_at   r9, locptr          ; and the console (an error after LOCATE)
            ldi     0
            str     r9
            inc     r9
            str     r9
            call    file_abort          ; close a file left open by SAVE/LOAD
            call    crlf_if
            peekc
            xri     E_BREAK
            jz      raise_brk
            ldi     '?'
            call    putc
raise_brk:  peekc                       ; message number -> RF = its text
            plo     rc
            ldiw    rf, msgtab
raise_f:    dec     rc
            glo     rc
            jz      raise_p
raise_s:    lda     rf
            jnz     raise_s
            jmp     raise_f
raise_p:    call    puts
            zp_at   r9, curline         ; running? " in nnn"
            lda     r9
            phi     rf
            ldn     r9
            plo     rf
            glo     rf
            jnz     raise_ln
            ghi     rf
            jz      raise_dn
raise_ln:   inc     rf                  ; the line's number
            lda     rf
            phi     acc
            ldn     rf
            plo     acc
            ldiw    rf, m_in
            call    puts
            call    printu
            peekc                       ; a break or STOP can be continued
            xri     E_BREAK
            jnz     raise_dn
            call    cont_save
raise_dn:   call    newline
            irx
            ldx
            xri     E_BREAK
            lbz     ready
            zp_at   r9, contok          ; an error cannot be continued
            ldi     0
            str     r9
            lbr     ready
m_in:       db      " in ",0
msgtab:     db      "Syntax error",0
            db      "Out of memory",0
            db      "Undefined line",0
            db      "RETURN without GOSUB",0
            db      "NEXT without FOR",0
            db      "Division by zero",0
            db      "Bad subscript",0
            db      "Already DIMed",0
            db      "Out of DATA",0
            db      "Illegal value",0
            db      "Can't continue",0
            db      "Too complex",0
            db      "No graphics",0
            db      "File error",0
            db      "Line too long",0
            db      "Overflow",0
            db      "Too many variables",0
            db      "File not found",0
            db      "Not in a program",0
            db      "Break",0

; ------------------------------------------------------------------ console output
; putc: D = character.  Keeps the column, wraps at 64 (HBIOS does not), sends a LOCATEd PRINT straight to the
; screen, or into a buffer for SAVE.  Keeps every register but RE.0; returns the character in D.
putc:       plo     re
            glo     r9
            stxd
            ghi     r9
            stxd
            glo     re
            stxd                        ; [r9.lo][r9.hi][char], R2 below
            zpage   r9
            ldi     low outmode         ; into a buffer (LIST for SAVE)?
            plo     r9
            ldn     r9
            jz      putc_scr
            ldi     low outptr          ; *outptr++ = c
            plo     r9
            lda     r9
            phi     re
            ldn     r9
            plo     re                  ; RE = pointer (no SCRT calls while it is used)
            peekc
            str     re
            inc     re
            glo     re
            str     r9
            dec     r9
            ghi     re
            str     r9
            jmp     putc_ret
putc_scr:   ldi     low locptr          ; LOCATE: write into the text RAM
            plo     r9
            lda     r9
            jz      putc_con
            phi     re
            ldn     r9
            plo     re
            peekc
            xri     8                   ; backspace: one place back, blanked (not before 7000)
            jnz     putc_lnb
            glo     re
            jnz     putc_lbs
            ghi     re
            xri     high SCREEN
            jz      putc_ret
putc_lbs:   dec     re
            ldi     ' '
            str     re
            jmp     putc_lst
putc_lnb:   peekc
            smi     ' '                 ; another control character ends LOCATE mode
            jnf     putc_lend
            peekc
            str     re
            inc     re
putc_lst:   glo     re
            str     r9
            dec     r9
            ghi     re
            str     r9
            jmp     putc_ret
putc_lend:  ldi     0
            str     r9
            dec     r9
            str     r9
putc_con:   peekc                       ; the console: column bookkeeping
            smi     ' '
            jdf     putc_prn
            peekc
            xri     13
            jnz     putc_nocr
            ldi     low column          ; CR: column 0
            plo     r9
            ldi     0
            str     r9
            jmp     putc_send
putc_nocr:  peekc
            xri     8
            jnz     putc_send
            ldi     low column          ; backspace: column - 1
            plo     r9
            ldn     r9
            jz      putc_send
            smi     1
            str     r9
            jmp     putc_send
putc_prn:   ldi     low column
            plo     r9
            ldn     r9
            smi     COLS
            jnf     putc_col            ; column < 64
            ldi     0                   ; wrap: CR LF first
            str     r9
            ldi     13
            call    f_type
            ldi     10
            call    f_type
putc_col:   zp_at   r9, column
            ldn     r9
            adi     1
            str     r9
putc_send:  peekc
            call    f_type
putc_ret:   irx                         ; restore R9, return the character in D
            ldxa
            plo     re
            ldxa
            phi     r9
            ldx
            plo     r9
            glo     re
            rtn

newline:    zp_at   r9, locptr          ; after a LOCATEd PRINT: back to the console, nothing printed
            ldn     r9
            jz      nl_con
            ldi     0
            str     r9
            inc     r9
            str     r9
            rtn
nl_con:     ldi     13
            call    putc
            ldi     10
            lbr     putc
crlf_if:    zp_at   r9, column          ; newline unless at column 0
            ldn     r9
            lbnz    newline
            rtn
space:      ldi     ' '
            lbr     putc

; puts: print the zero-terminated string at RF (RF ends past the 0)
puts:       lda     rf
            lbz     puts_dn
            call    putc
            jmp     puts
puts_dn:    rtn

; printnum: print ACC (signed).  printu: unsigned.  Uses RC, RF; keeps ACC.
printnum:   ghi     acc
            ani     80h
            lbz     printu
            ldi     '-'
            call    putc
            push    acc
            glo     acc                 ; ACC = -ACC
            sdi     0
            plo     acc
            ghi     acc
            sdbi    0
            phi     acc
            call    printu
            pop     acc
            rtn
printu:     push    acc
            push    r7
            ldiw    rf, pow10
            ldi     0                   ; RC.0 = 1 once a digit has been printed
            plo     rc
pu_pow:     lda     rf                  ; R7 = power of ten
            phi     r7
            lda     rf
            plo     r7
            ghi     r7
            jnz     pu_dig
            glo     r7
            xri     1
            jz      pu_last
pu_dig:     ldi     '0'
            phi     rc
pu_sub:     glo     r7                  ; ACC - R7
            str     r2
            glo     acc
            sm
            plo     re
            ghi     r7
            str     r2
            ghi     acc
            smb
            jnf     pu_out              ; went negative: digit done
            phi     acc
            glo     re
            plo     acc
            ghi     rc
            adi     1
            phi     rc
            jmp     pu_sub
pu_out:     ghi     rc
            xri     '0'
            jnz     pu_put
            glo     rc                  ; leading zero?
            jz      pu_pow
pu_put:     ghi     rc
            call    putc
            ldi     1
            plo     rc
            jmp     pu_pow
pu_last:    glo     acc                 ; the units digit, always
            adi     '0'
            call    putc
            pop     r7
            pop     acc
            rtn
pow10:      dw      10000,1000,100,10,1

; ------------------------------------------------------------------ keyboard
; getkey: wait for a key -> D.  A key saved by the break check comes first.  The wait stirs the RND seed.
getkey:     zp_at   r9, keybuf
            ldn     r9
            jz      gk_wait
            plo     re
            ldi     0
            str     r9
            glo     re
            rtn
gk_wait:    ldi     low rndseed
            plo     r9
kwait:      ldn     r9                  ; (kwait: the test harness knows GBASIC waits for a key here)
            adi     1
            str     r9
            b3      gk_key
            jmp     kwait
gk_key:     sex     r2
            inp     KBDPORT
            rtn

; keyhit: a key waiting? DF = 1 and D = the key (taken), else DF = 0.  For INKEY and LIST's pause.
keyhit:     zp_at   r9, keybuf
            ldn     r9
            jz      kh_port
            plo     re
            ldi     0
            str     r9
            glo     re
            smi     0                   ; DF = 1
            glo     re
            rtn
kh_port:    b3      kh_get
            adi     0                   ; DF = 0
            rtn
kh_get:     sex     r2
            inp     KBDPORT
            plo     re
            smi     0
            glo     re
            rtn

; brkcheck: between statements, when EF3 says a key waits.  Ctrl-C or Esc stops the program; any other key is
; kept for INPUT/INKEY.
brkcheck:   sex     r2
            inp     KBDPORT
            xri     3
            jz      brk_yes
            xri     3 ^ 1bh
            jz      brk_yes
            ldx                         ; keep it (INP left it at M(R2))
            plo     re
            zp_at   r9, keybuf
            glo     re
            str     r9
            rtn
brk_yes:    error   E_BREAK

; ------------------------------------------------------------------ line editor
; getline: read a line into linebuf (0-terminated).  Backspace/Delete edit, Ctrl-C or Esc cancels (DF = 1).
getline:    ldiw    r7, linebuf
            ldi     0
            plo     r8                  ; R8.0 = count
gl_key:     call    getkey
            plo     re
            xri     13
            jz      gl_cr
            glo     re
            xri     8
            jz      gl_bs
            glo     re
            xri     7fh
            jz      gl_bs
            glo     re
            xri     3
            jz      gl_cancel
            glo     re
            xri     1bh
            jz      gl_cancel
            glo     re
            smi     ' '
            jnf     gl_key              ; other control characters: ignore
            glo     re
            ani     80h                 ; VIDEO-G's F1-F12, arrows etc. (80h up): ignore (INKEY reads them)
            jnz     gl_key
            glo     r8
            smi     LINEMAX
            jdf     gl_key              ; full
            glo     re
            str     r7
            inc     r7
            inc     r8
            call    putc
            jmp     gl_key
gl_bs:      glo     r8
            jz      gl_key
            dec     r7
            dec     r8
            ldi     8
            call    putc
            jmp     gl_key
gl_cr:      ldi     0
            str     r7
            call    newline
            adi     0                   ; DF = 0
            rtn
gl_cancel:  ldiw    rf, m_ctlc
            call    puts
            call    newline
            ldi     0
            str     r7
            smi     0                   ; DF = 1
            rtn
m_ctlc:     db      "^C",0
