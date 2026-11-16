; GBASIC - the program store: lines, NEW, CLEAR, DELETE, RENUM.
;
; A line is [length][number hi][number lo][tokens...][0]; length counts all of it.  The store starts with a dummy
; line 0 ([4][0][0][0]) and ends with a single 0.  A jump to a line sets CURLINE to the line before it and TP to
; that line's final 0, so the statement loop steps onto the target as it does at any line end.

; find_line: ACC = number -> R9 = the first line numbered >= ACC (or the end mark), RA = the line before it.
; DF = 1 if R9's number = ACC.  Uses R9, RA only.
find_line:  ldiw    r9, prog
fl_loop:    mov     ra, r9
            ldn     r9                  ; R9 += length
            str     r2
            glo     r9
            add
            plo     r9
            ghi     r9
            adci    0
            phi     r9
            ldn     r9
            jz      fl_end
            inc     r9
            lda     r9                  ; ACC.hi - n.hi
            str     r2
            ghi     acc
            sm
            jnz     fl_hi
            ldn     r9                  ; ACC.lo - n.lo
            str     r2
            glo     acc
            sm
            dec     r9
            dec     r9
            jz      fl_exact
            jdf     fl_loop             ; ACC > n
            rtn                         ; ACC < n (DF = 0)
fl_hi:      dec     r9
            dec     r9
            jdf     fl_loop
            rtn
fl_exact:   smi     0                   ; DF = 1
            rtn
fl_end:     adi     0                   ; DF = 0
            rtn

; jump_to: ACC = line number.  Sets up the jump (Undefined line if there is no such line).
jump_to:    call    find_line
            jnf     jt_none
jump_ra:    zp_at   r9, curline         ; CURLINE = the line before, TP = its final 0
            ghi     ra
            str     r9
            inc     r9
            glo     ra
            str     r9
            ldn     ra
            smi     1
            str     r2
            glo     ra
            add
            plo     tp
            ghi     ra
            adci    0
            phi     tp
            rtn
jt_none:    error   E_NOLINE

; edit_line: put tokbuf in the program as line lineno (tklen bytes of tokens; 0 bytes = delete the line).
edit_line:  zp_at   r9, lineno
            lda     r9
            phi     acc
            ldn     r9
            plo     acc
            zp_at   r9, loading         ; LOAD: no clearing; a line after the last one goes on the end
            ldn     r9
            jz      el_edit
            ldi     low lastnum
            plo     r9
            ldn     r9                  ; lineno > lastnum?
            str     r2
            ghi     acc
            sm
            jnz     el_cmp
            inc     r9
            ldn     r9
            dec     r9
            str     r2
            glo     acc
            sm
            jz      el_find             ; equal: replace it
el_cmp:     jnf     el_find             ; smaller: the general way
            ghi     acc                 ; lastnum = lineno
            str     r9
            inc     r9
            glo     acc
            str     r9
            zp_at   r9, progend         ; R9 = the end mark: insert there
            lda     r9
            phi     rf
            ldn     r9
            plo     rf
            mov     r9, rf
            jmp     el_noold
el_edit:    call    clear_run           ; any edit clears the variables
el_find:    call    find_line
            jnf     el_noold
            call    del_line
el_noold:   zp_at   r8, tklen
            ldn     r8
            lbz     eln_dn
            adi     4                   ; RC = L = tklen + 4
            plo     rc
            ldi     0
            adci    0
            phi     rc
            zp_at   r8, progend         ; R7 = progend
            lda     r8
            phi     r7
            ldn     r8
            plo     r7
            glo     rc                  ; R8 = progend + L (new end)
            str     r2
            glo     r7
            add
            plo     r8
            ghi     rc
            str     r2
            ghi     r7
            adc
            phi     r8
            mov     rf, r8              ; room? new end + 1 < memlim
            inc     rf
            zp_at   ra, memlim + 1
            ldn     ra
            str     r2
            glo     rf
            sm
            dec     ra
            ldn     ra
            str     r2
            ghi     rf
            smb
            jdf     eln_full
            push    rc                  ; L
            push    r8                  ; new end
            mov     rf, r7              ; move [R9 .. progend] up by L: from the end down
            glo     r9                  ; RC = progend - R9 + 1
            str     r2
            glo     r7
            sm
            plo     rc
            ghi     r9
            str     r2
            ghi     r7
            smb
            phi     rc
            inc     rc
            call    move_up             ; RF = source end, R8 = destination end
            pop     r8                  ; progend = new end
            zp_at   r7, progend
            ghi     r8
            str     r7
            inc     r7
            glo     r8
            str     r7
            call    set_arrend
            pop     rc                  ; write the line at R9
            glo     rc
            str     r9
            inc     r9
            zp_at   r8, lineno
            lda     r8
            str     r9
            inc     r9
            ldn     r8
            str     r9
            inc     r9
            ldiw    rf, tokbuf              ; tklen bytes (numbers may hold 00), then the 0
            zp_at   r8, tklen
            ldn     r8
            plo     rc
el_copy:    glo     rc
            jz      el_end
            lda     rf
            str     r9
            inc     r9
            dec     rc
            jmp     el_copy
el_end:     ldi     0
            str     r9
eln_dn:      rtn
eln_full:    error   E_MEMORY

; del_line: delete the line at R9 (R9 then points at what followed).  Uses RC, RF, R8.
del_line:   ldn     r9                  ; RF = R9 + L (source)
            str     r2
            glo     r9
            add
            plo     rf
            ghi     r9
            adci    0
            phi     rf
            mov     r8, r9
            ; fall into del_range: delete [R8, RF)
; del_range: delete the bytes from R8 up to RF (not included); progend moves down.  Keeps R9.
del_range:  push    r9
            zp_at   r9, progend         ; RC = progend + 1 - RF
            lda     r9
            phi     rc
            ldn     r9
            plo     rc
            inc     rc
            glo     rf
            str     r2
            glo     rc
            sm
            plo     rc
            ghi     rf
            str     r2
            ghi     rc
            smb
            phi     rc
            glo     r8                  ; R7 = RF - R8 = bytes removed
            str     r2
            glo     rf
            sm
            plo     r7
            ghi     r8
            str     r2
            ghi     rf
            smb
            phi     r7
            call    move_down
            zp_at   r9, progend         ; progend -= R7
            inc     r9
            glo     r7
            str     r2
            ldn     r9
            sm
            str     r9
            dec     r9
            ghi     r7
            str     r2
            ldn     r9
            smb
            str     r9
            pop     r9
            ; fall into set_arrend
set_arrend: zp_at   r8, progend         ; arrend = progend + 1 (no arrays)
            lda     r8
            phi     rf
            ldn     r8
            plo     rf
            inc     rf
            zp_at   r8, arrend
            ghi     rf
            str     r8
            inc     r8
            glo     rf
            str     r8
            rtn

; move_down: copy RC bytes from RF to R8, upwards (R8 below RF)
move_down:  glo     rc
            jnz     md_go
            ghi     rc
            jz      md_dn
md_go:      lda     rf
            str     r8
            inc     r8
            dec     rc
            jmp     move_down
md_dn:      rtn
; move_up: copy RC bytes from RF downwards to R8 (RF, R8 = the last bytes; R8 above RF)
move_up:    glo     rc
            jnz     mvu_go
            ghi     rc
            jz      mvu_dn
mvu_go:      ldn     rf
            dec     rf
            str     r8
            dec     r8
            dec     rc
            jmp     move_up
mvu_dn:      rtn

; do_new: no program, no variables
do_new:     ldiw    r9, prog
            ldi     4
            str     r9
            inc     r9
            ldi     0
            str     r9
            inc     r9
            str     r9
            inc     r9
            str     r9
            inc     r9
            str     r9                  ; the end mark
            zp_at   r8, progend
            ghi     r9
            str     r8
            inc     r8
            glo     r9
            str     r8
            zp_at   r8, nvars
            ldi     0
            str     r8
            ; fall into clear_run
; clear_run: every variable 0, arrays gone, FOR/GOSUB stack empty, READ from the first DATA, no CONT
clear_run:  ldiw    rf, varvals
            ldi     2 * MAXVARS
            plo     rc
cr_loop:    ldi     0
            str     rf
            inc     rf
            dec     rc
            glo     rc
            jnz     cr_loop
            call    set_arrend
            zp_at   r8, csp
            ldi     high cstack
            str     r8
            inc     r8
            ldi     low cstack
            str     r8
            zp_at   r8, dataptr
            ldi     0
            str     r8
            inc     r8
            str     r8
            zp_at   r8, contok
            ldi     0
            str     r8
            rtn

st_new:     call    do_new
            lbr     ready
st_clear:   lbr     clear_run

; DELETE a-b (or DELETE a)
st_delete:  call    range               ; RA = first line >= a, R7 = b
            mov     r9, ra
dl_scan:    ldn     r9                  ; R9 = the first line past b
            jz      dl_go
            inc     r9
            lda     r9
            str     r2
            ghi     r7
            sm
            jnf     dl_past
            jnz     dl_in
            ldn     r9
            str     r2
            glo     r7
            sm
            jnf     dl_past
dl_in:      dec     r9
            dec     r9
            ldn     r9
            str     r2
            glo     r9
            add
            plo     r9
            ghi     r9
            adci    0
            phi     r9
            jmp     dl_scan
dl_past:    dec     r9
            dec     r9
dl_go:      mov     r8, ra
            mov     rf, r9
            call    del_range
            call    clear_run
            lbr     ready

; skiptok: RA -> a token; RA past it (it stays on a final 0).  Strings and REM/' text are skipped whole.
skiptok:    lda     ra
            jz      sk_eol
            plo     re
            smi     TK_NUM
            jz      sk_3
            smi     TK_HEX - TK_NUM
            jz      sk_3
            smi     TK_VAR - TK_HEX
            jz      sk_2
            smi     TK_ARR - TK_VAR
            jz      sk_2
            glo     re
            xri     '"'
            jz      sk_str
            glo     re
            xri     TK_REM
            jz      sk_rem
            glo     re
            xri     TK_REM2
            jz      sk_rem
            rtn
sk_3:       inc     ra
sk_2:       inc     ra
            rtn
sk_str:     ldn     ra
            jz      skt_dn
            lda     ra
            xri     '"'
            jnz     sk_str
skt_dn:      rtn
sk_rem:     ldn     ra
            jz      skt_dn
            inc     ra
            jmp     sk_rem
sk_eol:     dec     ra
            rtn

; RENUM [start[,step]]  (10,10 if not given).  Fixes GOTO, GOSUB, THEN, ELSE, RESTORE, RUN and ON lists.
st_renum:   ldiw    r7, 10              ; R7 = start
            ldiw    r8, 10              ; R8 = step
            ldn     tp
            xri     TK_NUM
            jnz     rn_go
            inc     tp
            lda     tp
            phi     r7
            lda     tp
            plo     r7
            ldn     tp
            xri     ','
            jnz     rn_go
            inc     tp
            ldn     tp
            xri     TK_NUM
            lbnz    syntax_err
            inc     tp
            lda     tp
            phi     r8
            lda     tp
            plo     r8
rn_go:      zp_at   r9, rn_start
            ghi     r7
            str     r9
            inc     r9
            glo     r7
            str     r9
            inc     r9
            ghi     r8                  ; rn_step follows rn_start
            str     r9
            inc     r9
            glo     r8
            str     r9
            ; do the numbers fit?  R7 runs through the new numbers
            ldiw    r9, prog
rn_chk:     call    nextline            ; this line gets R7
            jz      rn_pass1
            call    nextline_peek       ; another after it: it gets R7 + step, which must be <= 65535
            jz      rn_pass1
            glo     r8
            str     r2
            glo     r7
            add
            plo     r7
            ghi     r8
            str     r2
            ghi     r7
            adc
            phi     r7
            jdf     rn_big
            jmp     rn_chk
rn_big:     error   E_OVERFLOW
; pass 1: every line number after GOTO/GOSUB/THEN/ELSE/RESTORE/RUN (and ON lists, which follow GOTO/GOSUB)
rn_pass1:   ldiw    r9, prog
rn_p1line:  call    nextline
            jz      rn_pass2
            mov     ra, r9
            inc     ra
            inc     ra
            inc     ra
rn_p1tok:   ldn     ra
            jz      rn_p1line
            xri     TK_GOTO
            jz      rn_ref
            ldn     ra
            xri     TK_GOSUB
            jz      rn_ref
            ldn     ra
            xri     TK_THEN
            jz      rn_ref
            ldn     ra
            xri     TK_ELSE
            jz      rn_ref
            ldn     ra
            xri     TK_RESTORE
            jz      rn_ref
            ldn     ra
            xri     TK_RUN
            jz      rn_ref
            call    skiptok
            jmp     rn_p1tok
rn_ref:     inc     ra
rn_ref1:    ldn     ra
            xri     TK_NUM
            jnz     rn_p1tok
            inc     ra                  ; ACC = the old number
            lda     ra
            phi     acc
            ldn     ra
            plo     acc
            dec     ra
            push    r9
            call    rn_lookup           ; ACC = its new number (or the same if no such line)
            pop     r9
            ghi     acc
            str     ra
            inc     ra
            glo     acc
            str     ra
            inc     ra
            ldn     ra                  ; a list: , number , number ...
            xri     ','
            jnz     rn_p1tok
            inc     ra
            jmp     rn_ref1
; pass 2: the lines themselves
rn_pass2:   zp_at   r9, rn_start
            lda     r9
            phi     r7
            lda     r9
            plo     r7
            lda     r9
            phi     r8
            ldn     r9
            plo     r8
            ldiw    r9, prog
rn_p2:      call    nextline
            jz      rn_dn
            inc     r9
            ghi     r7
            str     r9
            inc     r9
            glo     r7
            str     r9
            dec     r9
            dec     r9
            glo     r8
            str     r2
            glo     r7
            add
            plo     r7
            ghi     r8
            str     r2
            ghi     r7
            adc
            phi     r7
            jmp     rn_p2
rn_dn:      call    clear_run
            lbr     ready
; rn_lookup: ACC = old number -> ACC = new number.  Uses R7, R8, R9, RF.
rn_lookup:  zp_at   r9, rn_start
            lda     r9
            phi     r7
            lda     r9
            plo     r7
            lda     r9
            phi     r8
            ldn     r9
            plo     r8
            ldiw    r9, prog
rl_loop:    call    nextline
            jz      rl_none
            inc     r9
            lda     r9
            str     r2
            ghi     acc
            xor
            jnz     rl_no
            ldn     r9
            str     r2
            glo     acc
            xor
            jnz     rl_no
            mov     acc, r7
            rtn
rl_no:      dec     r9
            dec     r9
            glo     r8
            str     r2
            glo     r7
            add
            plo     r7
            ghi     r8
            str     r2
            ghi     r7
            adc
            phi     r7
            jmp     rl_loop
rl_none:    rtn

; nextline: R9 -> a line (or the dummy) -> R9 = the next line; D = its length (0 = the end mark).
nextline:   ldn     r9
            str     r2
            glo     r9
            add
            plo     r9
            ghi     r9
            adci    0
            phi     r9
            ldn     r9
            rtn
; nextline_peek: D = length of the line after R9 (R9 unchanged)
nextline_peek:
            push    r9
            call    nextline
            plo     re
            pop     r9
            glo     re
            rtn
