; GBASIC - the statement loop and the statements (graphics and files are in gfx.asm and file.asm).

; ------------------------------------------------------------------ the statement loop
; exec_line: TP at a statement (tokbuf in direct mode, or the program).  Never returns: it ends at ready.
exec_line:
stmt:       ldn     tp
            jz      st_eol
            xri     ':'
            jnz     st_go
            inc     tp
            jmp     stmt
st_go:      bn3     st_nokey            ; a key waits: Ctrl-C / Esc?  (here CURLINE is the statement's line)
            call    brkcheck
st_nokey:   lda     tp
            plo     re                  ; the token (no SCRT call before it is used)
            smi     80h
            jnf     st_nokw
            smi     STMT_LAST - 80h + 1
            lbdf    syntax_err          ; a keyword, but not a statement
            glo     re                  ; handler = stmttab[token - 80h]
            smi     80h
            shl
            adi     low stmttab
            plo     r9
            ldi     high stmttab
            adci    0
            phi     r9
            ldiw    r8, st_disp + 1
            lda     r9
            str     r8
            inc     r8
            ldn     r9
            str     r8
st_disp:    sep     r4                  ; call the handler (its address is written here)
            dw      0
            jmp     stmt
st_nokw:    glo     re                  ; a variable: LET without the word
            xri     TK_VAR
            jz      st_let1
            glo     re
            xri     TK_ARR
            lbnz    syntax_err
st_let1:    dec     tp
            call    st_let
            jmp     stmt
; the end of a line: the next line, or the end of the program / direct command
st_eol:     zp_at   r9, curline
            lda     r9
            phi     ra
            ldn     r9
            plo     ra
            glo     ra
            jnz     st_next1
            ghi     ra
            lbz     ready               ; a direct command is done
st_next1:   ldn     ra                  ; RA += length
            str     r2
            glo     ra
            add
            plo     ra
            ghi     ra
            adci    0
            phi     ra
            ldn     ra
            jz      st_progend
            glo     ra                  ; CURLINE = RA (R9 -> curline + 1)
            str     r9
            dec     r9
            ghi     ra
            str     r9
            glo     ra                  ; TP = RA + 3
            adi     3
            plo     tp
            ghi     ra
            adci    0
            phi     tp
            jmp     stmt
st_progend: lbr     ready

syntax_err: error   E_SYNTAX

; expect: the byte after the call must be at TP (it is skipped), else Syntax error.   call expect / db ')'
expect:     lda     r6
            str     r2
            ldn     tp
            xor
            lbnz    syntax_err
            inc     tp
            rtn

; at_end: DF = 1 if TP is at the end of a statement (0, ':', ELSE or ')
at_end:     ldn     tp
            jz      ae_yes
            xri     ':'
            jz      ae_yes
            ldn     tp
            xri     TK_ELSE
            jz      ae_yes
            ldn     tp
            xri     TK_REM2
            jz      ae_yes
            adi     0
            rtn
ae_yes:     smi     0
            rtn

; ------------------------------------------------------------------ END STOP CONT RUN NEW
st_end:     call    cont_save
            lbr     ready
st_stop:    error   E_BREAK
cont_save:  zp_at   r9, curline         ; in a program: remember where (TP, CURLINE) for CONT
            lda     r9
            phi     ra
            ldn     r9
            plo     ra
            glo     ra
            jnz     cs_yes
            ghi     ra
            jz      cs_dn
cs_yes:     zp_at   r9, contok
            ldi     1
            str     r9
            inc     r9                  ; conttp, then contline follow contok
            ghi     tp
            str     r9
            inc     r9
            glo     tp
            str     r9
            inc     r9
            ghi     ra
            str     r9
            inc     r9
            glo     ra
            str     r9
cs_dn:      rtn
st_cont:    zp_at   r9, contok
            ldn     r9
            jz      ct_no
            ldi     0
            str     r9
            inc     r9
            lda     r9
            phi     tp
            lda     r9
            plo     tp
            lda     r9
            phi     ra
            ldn     r9
            plo     ra
            zp_at   r9, curline
            ghi     ra
            str     r9
            inc     r9
            glo     ra
            str     r9
            rtn
ct_no:      error   E_CONT

st_run:     call    clear_run
            ldn     tp
            xri     TK_NUM
            jnz     rn_first
            inc     tp
            lda     tp
            phi     acc
            lda     tp
            plo     acc
            lbr     jump_to
rn_first:   ldiw    ra, prog            ; continue from the dummy line: the first line is next
            lbr     jump_ra
run_program:
            call    clear_run           ; (entered by a jump, after LOAD from the command line)
            ldiw    ra, prog
            call    jump_ra
            lbr     stmt

; ------------------------------------------------------------------ GOTO GOSUB RETURN ON IF
st_goto:    call    expr
            lbr     jump_to
st_gosub:   call    expr
gosub_acc:  call    find_line           ; ACC = line; frame: TP (after the statement), CURLINE, 'G'
            lbnf    jt_none
            call    cs_room5
            ghi     tp
            str     r9
            inc     r9
            glo     tp
            str     r9
            inc     r9
            zp_at   r8, curline
            lda     r8
            str     r9
            inc     r9
            ldn     r8
            str     r9
            inc     r9
            ldi     'G'
            str     r9
            inc     r9
            call    cs_set              ; csp = R9
            lbr     jump_ra
; cs_room5 / cs_room10: R9 = csp, Too complex if the frame does not fit
cs_room5:   ldi     5
            jmp     cs_room
cs_room10:  ldi     10
cs_room:    stxd                        ; n
            zp_at   r8, csp
            lda     r8
            phi     r9
            ldn     r8
            plo     r9
            irx
            ldx
            str     r2                  ; RF = R9 + n
            glo     r9
            add
            plo     rf
            ghi     r9
            adci    0
            phi     rf
            glo     rf                  ; past cstack_end?
            smi     low (cstack_end + 1)
            ghi     rf
            smbi    high (cstack_end + 1)
            lbdf    complex_err
            rtn
complex_err: error  E_COMPLEX
; cs_set: csp = R9
cs_set:     zp_at   r8, csp
            ghi     r9
            str     r8
            inc     r8
            glo     r9
            str     r8
            rtn
; cs_get: R9 = csp
cs_get:     zp_at   r8, csp
            lda     r8
            phi     r9
            ldn     r8
            plo     r9
            rtn
; cs_empty: DF = 1 if R9 is at the bottom of the control stack
cs_empty:   glo     r9
            xri     low cstack
            jnz     ce_no
            ghi     r9
            xri     high cstack
            jnz     ce_no
            smi     0
            rtn
ce_no:      adi     0
            rtn

st_return:  call    cs_get
rt_find:    call    cs_empty
            jdf     rt_none
            dec     r9
            ldn     r9                  ; the frame type
            inc     r9
            xri     'G'
            jz      rt_found
            glo     r9                  ; a FOR frame: drop it
            smi     10
            plo     r9
            ghi     r9
            smbi    0
            phi     r9
            jmp     rt_find
rt_found:   glo     r9                  ; R9 = the frame (5 bytes)
            smi     5
            plo     r9
            ghi     r9
            smbi    0
            phi     r9
            call    cs_set
            lda     r9
            phi     tp
            lda     r9
            plo     tp
            zp_at   r8, curline
            lda     r9
            str     r8
            inc     r8
            ldn     r9
            str     r8
            rtn
rt_none:    error   E_RETURN

st_on:      call    expr                ; ACC = n
            ldn     tp
            xri     TK_GOTO
            jz      on_ok
            ldn     tp
            xri     TK_GOSUB
            lbnz    syntax_err
on_ok:      lda     tp
            stxd                        ; which (GOTO / GOSUB)
            ldiw    r7, 1               ; R7 = counter
            ldi     0
            plo     rc                  ; RC.0 = 1 when found
on_loop:    ldn     tp
            xri     TK_NUM
            lbnz    syntax_err
            inc     tp
            glo     r7                  ; counter = n?
            str     r2
            glo     acc
            xor
            jnz     on_skip
            ghi     r7
            str     r2
            ghi     acc
            xor
            jnz     on_skip
            lda     tp                  ; the target
            phi     rf
            lda     tp
            plo     rf
            ldi     1
            plo     rc
            jmp     on_next
on_skip:    inc     tp
            inc     tp
on_next:    inc     r7
            ldn     tp
            xri     ','
            jnz     on_end
            inc     tp
            jmp     on_loop
on_end:     irx                         ; which
            ldx
            plo     re
            glo     rc
            jz      on_none
            mov     acc, rf
            glo     re
            xri     TK_GOSUB
            jz      gosub_acc
            lbr     jump_to
on_none:    rtn

st_if:      call    expr
            ldn     tp
            xri     TK_THEN
            jnz     if_nothen
            inc     tp
if_nothen:  glo     acc
            jnz     if_true
            ghi     acc
            jz      if_false
if_true:    ldn     tp                  ; THEN 100
            xri     TK_NUM
            jnz     if_dn
if_goto:    inc     tp
            lda     tp
            phi     acc
            lda     tp
            plo     acc
            lbr     jump_to
if_dn:      rtn
if_false:   mov     ra, tp              ; look for ELSE on this line
if_scan:    ldn     ra
            jz      if_eol
            xri     TK_ELSE
            jz      if_else
            call    skiptok
            jmp     if_scan
if_eol:     mov     tp, ra
            rtn
if_else:    inc     ra
            mov     tp, ra
            ldn     tp
            xri     TK_NUM
            jz      if_goto
            rtn

; REM, ' and ELSE (met as a statement: the THEN part is done) skip the rest of the line; DATA skips its items
st_rem:     ldn     tp
            jz      srm_dn
            inc     tp
            jmp     st_rem
srm_dn:     rtn
st_rem_data: mov    ra, tp
srd_loop:   ldn     ra
            jz      srd_dn
            xri     ':'
            jz      srd_dn
            call    skiptok
            jmp     srd_loop
srd_dn:     mov     tp, ra
            rtn

; ------------------------------------------------------------------ LET FOR NEXT
st_let:     ldn     tp                  ; R8 -> the variable (a plain one here, an element by varref)
            xri     TK_VAR
            jnz     sl_gen
            inc     tp
            lda     tp
            plo     r8
            ldi     high varvals
            phi     r8
            jmp     sl_eq
sl_gen:     call    varref
sl_eq:      push    r8
            lda     tp
            xri     TK_EQ
            lbnz    syntax_err
            call    expr
            pop     r8
            ghi     acc
            str     r8
            inc     r8
            glo     acc
            str     r8
            rtn

; FOR v = a TO b [STEP s].  Frame: slot*2, limit, step, TP, CURLINE, 'F' (10 bytes).
st_for:     ldn     tp
            xri     TK_VAR
            lbnz    syntax_err
            inc     tp
            lda     tp
            stxd                        ; slot * 2
            call    expect
            db      TK_EQ
            call    expr
            irx                         ; v = a
            ldx
            dec     r2
            plo     r8
            ldi     high varvals
            phi     r8
            ghi     acc
            str     r8
            inc     r8
            glo     acc
            str     r8
            call    expect
            db      TK_TO
            call    expr
            push    acc                 ; limit
            ldiw    acc, 1
            ldn     tp
            xri     TK_STEP
            jnz     for_nostep
            inc     tp
            call    expr
for_nostep: pop     r7                  ; R7 = limit, ACC = step
            irx
            ldx
            plo     rc                  ; RC.0 = slot * 2
            ; a FOR frame for the same variable (not past a GOSUB) is dropped, with anything above it
            call    cs_get
for_old:    call    cs_empty
            jdf     for_push
            dec     r9
            ldn     r9
            inc     r9
            xri     'F'
            jnz     for_push            ; a GOSUB frame: stop looking
            glo     r9
            smi     10
            plo     r9
            ghi     r9
            smbi    0
            phi     r9
            ldn     r9                  ; its variable
            str     r2
            glo     rc
            xor
            jnz     for_old
            call    cs_set              ; drop it and everything above
for_push:   call    cs_room10           ; R9 = csp
            glo     rc
            str     r9
            inc     r9
            ghi     r7
            str     r9
            inc     r9
            glo     r7
            str     r9
            inc     r9
            ghi     acc
            str     r9
            inc     r9
            glo     acc
            str     r9
            inc     r9
            ghi     tp
            str     r9
            inc     r9
            glo     tp
            str     r9
            inc     r9
            zp_at   r8, curline
            lda     r8
            str     r9
            inc     r9
            ldn     r8
            str     r9
            inc     r9
            ldi     'F'
            str     r9
            inc     r9
            lbr     cs_set

; NEXT [v[,w...]]
st_next:    ldi     0ffh                ; RC.0 = slot * 2, or FF for any
            plo     rc
            ldn     tp
            xri     TK_VAR
            jnz     nx_find0
            inc     tp
            lda     tp
            plo     rc
nx_find0:   zp_at   r8, csp             ; R9 = csp
            lda     r8
            phi     r9
            ldn     r8
            plo     r9
nx_find:    glo     r9                  ; the bottom: NEXT without FOR
            xri     low cstack
            jnz     nx_some
            ghi     r9
            xri     high cstack
            jz      nx_none
nx_some:    dec     r9
            ldn     r9
            inc     r9
            xri     'F'
            jnz     nx_none             ; a GOSUB frame first
            glo     r9                  ; RA = the frame
            smi     10
            plo     ra
            ghi     r9
            smbi    0
            phi     ra
            glo     rc
            xri     0ffh
            jz      nx_found
            ldn     ra
            str     r2
            glo     rc
            xor
            jz      nx_found
            mov     r9, ra              ; an inner loop: drop it
            jmp     nx_find
nx_none:    error   E_NEXT
nx_found:   zp_at   r8, csp             ; csp = R9 (inner frames gone)
            ghi     r9
            str     r8
            inc     r8
            glo     r9
            str     r8
            lda     ra                  ; R8 -> the variable
            plo     r8
            ldi     high varvals
            phi     r8
            lda     ra                  ; R7 = limit
            phi     r7
            lda     ra
            plo     r7
            lda     ra                  ; RF = step
            phi     rf
            lda     ra
            plo     rf
            lda     r8                  ; ACC = v + step
            phi     acc
            ldn     r8
            str     r2
            glo     rf
            add
            plo     acc
            ghi     acc
            phi     re                  ; RE.1 = v.hi (for the overflow test)
            str     r2
            ghi     rf
            adc
            phi     acc
            dec     r8                  ; store it
            ghi     acc
            str     r8
            inc     r8
            glo     acc
            str     r8
            ; overflow: v and step of the same sign, and the sum of the other sign -> the loop is over
            ghi     re
            str     r2
            ghi     rf
            xor
            ani     80h
            jnz     nx_noovf
            ghi     acc
            str     r2
            ghi     rf
            xor
            ani     80h
            jnz     nx_done
nx_noovf:   ghi     rf                  ; step < 0: done when v < limit; else done when v > limit
            ani     80h
            jnz     nx_neg
            glo     acc                 ; limit - v < 0 ?  (signed: compare with the sign bits flipped)
            str     r2
            glo     r7
            sm
            ghi     acc
            xri     80h
            str     r2
            ghi     r7
            xri     80h
            smb
            jnf     nx_done
            jmp     nx_loop
nx_neg:     glo     r7                  ; v - limit < 0 ?
            str     r2
            glo     acc
            sm
            ghi     r7
            xri     80h
            str     r2
            ghi     acc
            xri     80h
            smb
            jnf     nx_done
nx_loop:    lda     ra                  ; back to the top of the loop: TP, CURLINE from the frame
            phi     tp
            lda     ra
            plo     tp
            zp_at   r8, curline
            lda     ra
            str     r8
            inc     r8
            ldn     ra
            str     r8
            rtn
nx_done:    glo     ra                  ; drop the frame
            smi     5
            plo     r9
            ghi     ra
            smbi    0
            phi     r9
            call    cs_set
            ldn     tp                  ; NEXT I,J
            xri     ','
            jnz     nx_dn
            inc     tp
            ldn     tp
            xri     TK_VAR
            lbnz    syntax_err
            jmp     st_next
nx_dn:      rtn

; ------------------------------------------------------------------ PRINT
; Items: expressions, "strings", TAB(n), SPC(n), CHR$(n); ';' joins, ',' goes to the next 16-column zone.
; A newline at the end unless it ends with ';' or ','.
st_print:   zp_at   r9, prflag
            ldi     1
            str     r9
pr_loop:    call    at_end
            jdf     pr_end
            ldn     tp
            xri     ';'
            jz      pr_semi
            ldn     tp
            xri     ','
            jz      pr_comma
            zp_at   r9, prflag
            ldi     1
            str     r9
            ldn     tp
            xri     '"'
            jz      pr_str
            ldn     tp
            xri     TK_TAB
            jz      pr_tab
            ldn     tp
            xri     TK_SPC
            jz      pr_spc
            ldn     tp
            xri     TK_CHR
            jz      pr_chr
            call    expr
            call    printnum
            jmp     pr_loop
pr_semi:    inc     tp
            zp_at   r9, prflag
            ldi     0
            str     r9
            jmp     pr_loop
pr_comma:   inc     tp
            zp_at   r9, prflag
            ldi     0
            str     r9
            zp_at   r9, column
            ldn     r9
            smi     48
            jnf     pr_zone
            call    newline
            jmp     pr_loop
pr_zone:    call    space
            zp_at   r9, column
            ldn     r9
            ani     0fh
            jnz     pr_zone
            jmp     pr_loop
pr_str:     inc     tp
            call    print_lit
            jmp     pr_loop
pr_tab:     inc     tp
            call    expr
            call    expect
            db      ')'
            ghi     acc                 ; columns 0-63 only
            jnz     pr_loop
            glo     acc
            smi     COLS
            jdf     pr_loop
pr_tab1:    zp_at   r9, column          ; spaces up to column n
            ldn     r9
            str     r2
            glo     acc
            sm
            jnf     pr_loop
            jz      pr_loop
            call    space
            jmp     pr_tab1
pr_spc:     inc     tp
            call    expr
            call    expect
            db      ')'
pr_spc1:    glo     acc
            jz      pr_loop
            ghi     acc
            ani     80h
            jnz     pr_loop
            call    space
            dec     acc
            jmp     pr_spc1
pr_chr:     inc     tp
            call    expr
            call    expect
            db      ')'
            glo     acc
            call    putc
            jmp     pr_loop
pr_end:     zp_at   r9, prflag
            ldn     r9
            lbnz    newline
            rtn
; print_lit: TP just past an opening quote: print to the closing quote (TP past it) or the end of the line
print_lit:  ldn     tp
            jz      pl_dn
            lda     tp
            xri     '"'
            jz      pl_dn
            dec     tp
            lda     tp
            call    putc
            jmp     print_lit
pl_dn:      rtn

; ------------------------------------------------------------------ INPUT ["prompt";|,] var[,var...]
st_input:   zp_at   r9, inqmark
            ldi     1
            str     r9
            ldn     tp
            xri     '"'
            jnz     in_noprm
            inc     tp
            call    print_lit
            ldn     tp
            xri     ';'
            jz      in_semi
            ldn     tp
            xri     ','
            lbnz    syntax_err
            zp_at   r9, inqmark
            ldi     0
            str     r9
in_semi:    inc     tp
in_noprm:   zp_at   r9, intp            ; for "Redo from start"
            ghi     tp
            str     r9
            inc     r9
            glo     tp
            str     r9
in_ask:     zp_at   r9, inqmark
            ldn     r9
            jz      in_read
            ldiw    rf, m_qm
            call    puts
in_read:    call    getline
            lbdf    brk_yes             ; Ctrl-C: stop
            zp_at   r9, inptr
            ldi     high linebuf
            str     r9
            inc     r9
            ldi     low linebuf
            str     r9
in_var:     call    varref              ; R8 -> the variable
            push    r8
in_num:     zp_at   r9, inptr
            lda     r9
            phi     rf
            ldn     r9
            plo     rf
            call    skipsp
            jnz     in_have
            ldiw    rf, m_qq            ; ran out: ask for more
            call    puts
            call    getline
            lbdf    brk_yes
            zp_at   r9, inptr
            ldi     high linebuf
            str     r9
            inc     r9
            ldi     low linebuf
            str     r9
            jmp     in_num
in_have:    call    in_value            ; ACC; DF = 1 if it is not a number
            jdf     in_redo
            call    skipsp              ; then ',' or the end
            jz      in_store
            xri     ','
            jnz     in_redo
            inc     rf
in_store:   zp_at   r9, inptr
            ghi     rf
            str     r9
            inc     r9
            glo     rf
            str     r9
            pop     r8
            ghi     acc
            str     r8
            inc     r8
            glo     acc
            str     r8
            ldn     tp
            xri     ','
            jnz     in_dn
            inc     tp
            jmp     in_var
in_dn:      rtn
in_redo:    irx                         ; drop the variable address
            irx
            ldiw    rf, m_redo
            call    puts
            call    newline
            zp_at   r9, intp
            lda     r9
            phi     tp
            ldn     r9
            plo     tp
            jmp     in_ask
m_qm:       db      "? ",0
m_qq:       db      "?? ",0
m_redo:     db      "?Redo from start",0

; in_value: RF at text -> ACC = a number: [+|-] digits, or &H hex.  DF = 1 if it is not one (or too big).
in_value:   ldi     0
            plo     rc                  ; RC.0 = 1 if negative
            ldn     rf
            xri     '-'
            jnz     iv_plus
            ldi     1
            plo     rc
            inc     rf
            jmp     iv_num
iv_plus:    ldn     rf
            xri     '+'
            jnz     iv_num
            inc     rf
iv_num:     ldn     rf
            xri     '&'
            jz      iv_hex
            ldn     rf
            call    isdigit
            jnf     iv_bad
            call    parse_num
            jdf     iv_bad
            jmp     iv_sign
iv_hex:     inc     rf
            ldn     rf
            ani     0dfh
            xri     'H'
            jnz     iv_bad
            inc     rf
            call    parse_hexn
            jdf     iv_bad
iv_sign:    glo     rc
            jz      iv_ok
            glo     acc
            sdi     0
            plo     acc
            ghi     acc
            sdbi    0
            phi     acc
iv_ok:      adi     0                   ; DF = 0
            rtn
iv_bad:     smi     0
            rtn

; ------------------------------------------------------------------ READ DATA RESTORE
st_read:    call    varref
            push    r8
            call    data_next           ; ACC = the next DATA item
            pop     r8
            ghi     acc
            str     r8
            inc     r8
            glo     acc
            str     r8
            ldn     tp
            xri     ','
            jnz     srd_ok
            inc     tp
            jmp     st_read
srd_ok:     rtn

; data_next: ACC = the next item of the DATA statements (in program order).  Out of DATA at the end.
data_next:  zp_at   r9, dataptr         ; RA = where we are, R9 = its line
            lda     r9
            phi     ra
            lda     r9
            plo     ra
            lda     r9
            phi     rc
            ldn     r9
            plo     rc
            mov     r9, rc
            ghi     ra
            jnz     dn_have
            ldiw    r9, prog            ; from the start: the dummy line's final 0
            ldiw    ra, prog + 3
            jmp     dn_find
dn_have:    ldn     ra                  ; after an item: ',' = another item here
            xri     ','
            jnz     dn_find
            inc     ra
            jmp     dn_eval
dn_find:    ldn     ra                  ; look for the next DATA
            jnz     dn_tok
            ldn     r9                  ; the next line
            str     r2
            glo     r9
            add
            plo     r9
            ghi     r9
            adci    0
            phi     r9
            ldn     r9
            jz      dn_out
            glo     r9
            adi     3
            plo     ra
            ghi     r9
            adci    0
            phi     ra
            jmp     dn_find
dn_tok:     xri     TK_DATA
            jz      dn_data
            call    skiptok
            jmp     dn_find
dn_data:    inc     ra
dn_eval:    push    tp                  ; evaluate the item with TP there
            mov     tp, ra
            push    r9
            call    expr
            pop     r9
            mov     ra, tp
            pop     tp
            zp_at   r8, dataptr
            ghi     ra
            str     r8
            inc     r8
            glo     ra
            str     r8
            inc     r8
            ghi     r9
            str     r8
            inc     r8
            glo     r9
            str     r8
            rtn
dn_out:     error   E_DATA

st_restore: zp_at   r9, dataptr
            ldi     0
            str     r9
            inc     r9
            str     r9
            ldn     tp                  ; RESTORE n: from line n
            xri     TK_NUM
            jnz     rs_dn
            inc     tp
            lda     tp
            phi     acc
            lda     tp
            plo     acc
            call    find_line
            lbnf    jt_none
            ldn     ra                  ; dataptr = the final 0 of the line before
            smi     1
            str     r2
            glo     ra
            add
            plo     rc
            ghi     ra
            adci    0
            phi     rc
            zp_at   r9, dataptr
            ghi     rc
            str     r9
            inc     r9
            glo     rc
            str     r9
            inc     r9
            ghi     ra
            str     r9
            inc     r9
            glo     ra
            str     r9
rs_dn:      rtn

; ------------------------------------------------------------------ POKE OUT WAIT RANDOMIZE CALL CLS LOCATE BYE
st_poke:    call    expr
            push    acc
            call    expect
            db      ','
            call    expr
            pop     r8
            glo     acc
            str     r8
            rtn

st_out:     call    port_expr           ; the port, 1-7 -> OUT opcode written in outstub
            call    expect
            db      ','
            call    expr
            glo     acc
            call    outstub
            rtn
outstub:    str     r2                  ; (RAM, rewritten: OUT n)
outop:      out     1
            dec     r2
            rtn
; port_expr: ACC = an expression 1-7; writes OUT n and INP n into the stubs
port_expr:  call    expr
            ghi     acc
            lbnz    value_err
            glo     acc
            lbz     value_err
            smi     8
            lbdf    value_err
            glo     acc
            adi     60h
            plo     re
            ldiw    r9, outop
            glo     re
            str     r9
            ldiw    r9, inpop
            glo     re
            adi     8
            str     r9
            rtn
inpstub:
inpop:      inp     1                   ; (RAM, rewritten: INP n)
            rtn
value_err:  error   E_VALUE

; WAIT n: n frames (1/60 s each; VIDEO-G's VSYNC when it is there)
st_wait:    call    expr
wt_loop:    glo     acc
            jnz     wt_one
            ghi     acc
            jz      wt_dn
            ani     80h
            jnz     wt_dn
wt_one:     call    frame_wait
            dec     acc
            jmp     wt_loop
wt_dn:      rtn
frame_wait: zp_at   r9, vgstat          ; VIDEO-G: wait for VSYNC to end and start again
            ldn     r9
            jz      fw_loop
fw_lo:      bn3     fw_lo1
            call    brkcheck
fw_lo1:     sex     r2
            inp     VGPORT
            ani     ST_VSYNC
            jnz     fw_lo
fw_hi:      bn3     fw_hi1
            call    brkcheck
fw_hi1:     sex     r2
            inp     VGPORT
            ani     ST_VSYNC
            jz      fw_hi
            rtn
fw_loop:    ldiw    rc, 611             ; no VIDEO-G: about 16.7 ms at 1.76 MHz
fw_l1:      dec     rc
            glo     rc
            jnz     fw_l1
            ghi     rc
            jnz     fw_l1
            bn3     fw_dn
            call    brkcheck
fw_dn:      rtn

st_randomize:
            call    expr
            glo     acc
            jnz     rz_ok
            ghi     acc
            jnz     rz_ok
            inc     acc
rz_ok:      zp_at   r9, rndseed
            ghi     acc
            str     r9
            inc     r9
            glo     acc
            str     r9
            rtn

; CALL a: machine code at a, called with SCRT (it returns with SEP R5); it must keep R2.  TP is saved.
st_call:    call    expr
            ldiw    r9, sc_call + 1
            ghi     acc
            str     r9
            inc     r9
            glo     acc
            str     r9
            push    tp
sc_call:    sep     r4
            dw      0
            pop     tp
            rtn

; CLS: blank the text screen (7000-77FD; HBIOS keeps its cursor in 77FE/77FF), back to column 0
st_cls:     ldiw    rf, SCREEN + 7fdh
            sex     rf
            ldi     255                 ; RC.0 counts 255 x 8 bytes, then 6 more
            plo     rc
cls_loop:   ldi     ' '
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            dec     rc
            glo     rc
            jnz     cls_loop
            stxd                        ; 2040 done; 6 to go (77FD - 2040 = 7005 .. 7000)
            stxd
            stxd
            stxd
            stxd
            stxd
            sex     r2
            zp_at   r9, locptr
            ldi     0
            str     r9
            inc     r9
            str     r9
            ldi     13
            lbr     putc

; LOCATE row, column: the next PRINT goes straight to that place on the screen (until its newline)
st_locate:  call    expr
            ghi     acc
            lbnz    value_err
            zp_at   r9, vgstat          ; rows: 25 on VIDEO-G, 16 on the 6845 card
            ldn     r9
            jz      lc_16
            ldi     25
            jmp     lc_rows
lc_16:      ldi     16
lc_rows:    str     r2
            glo     acc
            sm
            lbdf    value_err
            glo     acc                 ; R7 = row * 64
            plo     r7
            ldi     0
            phi     r7
            ldi     6
            plo     rc
lc_sh:      glo     r7
            shl
            plo     r7
            ghi     r7
            shlc
            phi     r7
            dec     rc
            glo     rc
            jnz     lc_sh
            push    r7
            call    expect
            db      ','
            call    expr
            pop     r7
            ghi     acc
            lbnz    value_err
            glo     acc
            smi     COLS
            lbdf    value_err
            glo     acc
            str     r2
            glo     r7
            add
            plo     r7
            ghi     r7
            adci    high SCREEN
            phi     r7
            zp_at   r9, locptr
            ghi     r7
            str     r9
            inc     r9
            glo     r7
            str     r9
            rtn

st_bye:     call    vg_reset            ; text on, graphics off
            lbr     o_wrmboot
