; GBASIC - expressions: precedence climbing over 16-bit signed integers.
;
; Precedence: OR XOR (1)  AND (2)  NOT (unary, its operand at 3)  = <> < > <= >= (3)  + - (4)  * / MOD (5)
; unary - and +, then numbers, variables, array elements, functions and ( ).  True is -1, false 0.

; expr: the expression at TP -> ACC (TP past it).  Uses R7, R8, R9, RA, RC, RF.
expr:       ldi     1
exprp:      stxd                        ; this level takes operators of at least this precedence
            glo     r2                  ; enough stack left?
            smi     low STACKLOW
            ghi     r2
            smbi    high STACKLOW
            lbnf    complex_err
            ldn     tp                  ; a variable or a number: here, without a call
            xri     TK_VAR
            jnz     ex_nv
            inc     tp
            lda     tp
            plo     r8
            ldi     high varvals
            phi     r8
            lda     r8
            phi     acc
            ldn     r8
            plo     acc
            jmp     ex_loop
ex_nv:      ldn     tp
            xri     TK_NUM
            jz      ex_num
            ldn     tp
            xri     TK_HEX
            jnz     ex_un
ex_num:     inc     tp
            lda     tp
            phi     acc
            lda     tp
            plo     acc
            jmp     ex_loop
ex_un:      call    unary               ; ACC = the left operand
ex_loop:    ldn     tp
            smi     OP_FIRST
            jnf     ex_done
            smi     OP_LAST - OP_FIRST + 1
            jdf     ex_done
            ldn     tp
            smi     OP_FIRST
            plo     r7                  ; R7.0 = the operator's index
            adi     low prectab
            plo     r8
            ldi     high prectab
            adci    0
            phi     r8
            ldn     r8                  ; its precedence >= this level's?
            irx
            sm
            dec     r2
            jnf     ex_done
            inc     tp
            push    acc                 ; the left operand
            glo     r7
            stxd                        ; the operator
            ldn     r8                  ; the right operand binds one level tighter
            adi     1
            call    exprp
            irx                         ; R7.0 = operator, RF = left
            ldxa
            plo     r7
            ldxa
            phi     rf
            ldx
            plo     rf
            glo     r7                  ; + and -: here
            xri     TK_PLUS - OP_FIRST
            jnz     ex_nadd
            glo     acc
            str     r2
            glo     rf
            add
            plo     acc
            ghi     acc
            str     r2
            ghi     rf
            adc
            phi     acc
            jmp     ex_loop
ex_nadd:    glo     r7
            xri     TK_MINUS - OP_FIRST
            jnz     ex_nsub
            glo     acc
            str     r2
            glo     rf
            sm
            plo     acc
            ghi     acc
            str     r2
            ghi     rf
            smb
            phi     acc
            jmp     ex_loop
ex_nsub:    glo     r7                  ; ACC = RF op ACC: optab[op]
            shl
            adi     low optab
            plo     r8
            ldi     high optab
            adci    0
            phi     r8
            ldiw    r9, ex_call + 1
            lda     r8
            str     r9
            inc     r9
            ldn     r8
            str     r9
ex_call:    sep     r4
            dw      0
            jmp     ex_loop
ex_done:    irx                         ; drop the level
            rtn

unary:      ldn     tp
            xri     TK_MINUS
            jz      un_neg
            ldn     tp
            xri     TK_PLUS
            jz      un_plus
            ldn     tp
            xri     TK_NOT
            jz      un_not
            jmp     primary
un_neg:     inc     tp
            call    unary
neg_acc:    glo     acc
            sdi     0
            plo     acc
            ghi     acc
            sdbi    0
            phi     acc
            rtn
un_plus:    inc     tp
            jmp     unary
un_not:     inc     tp
            ldi     3
            call    exprp
            glo     acc
            xri     0ffh
            plo     acc
            ghi     acc
            xri     0ffh
            phi     acc
            rtn

primary:    lda     tp
            plo     re                  ; (no SCRT call while RE.0 holds it)
            xri     TK_NUM
            jz      pm_num
            glo     re
            xri     TK_HEX
            jz      pm_num
            glo     re
            xri     TK_VAR
            jz      pm_var
            glo     re
            xri     TK_ARR
            jz      pm_arr
            glo     re
            xri     '('
            jz      pm_paren
            glo     re
            smi     FN_FIRST
            lbnf    syntax_err
            smi     FN_LAST - FN_FIRST + 1
            lbdf    syntax_err
            glo     re                  ; fntab[token - FN_FIRST]
            smi     FN_FIRST
            shl
            adi     low fntab
            plo     r8
            ldi     high fntab
            adci    0
            phi     r8
            ldiw    r9, pm_fcall + 1
            lda     r8
            str     r9
            inc     r9
            ldn     r8
            str     r9
pm_fcall:   sep     r4
            dw      0
            rtn
pm_num:     lda     tp
            phi     acc
            lda     tp
            plo     acc
            rtn
pm_var:     lda     tp
            plo     r8
            ldi     high varvals
            phi     r8
            lda     r8
            phi     acc
            ldn     r8
            plo     acc
            rtn
pm_arr:     dec     tp
            call    varref
            lda     r8
            phi     acc
            ldn     r8
            plo     acc
            rtn
pm_paren:   call    expr
            call    expect
            db      ')'
            rtn

; paren: "( expr )" -> ACC
paren:      call    expect
            db      '('
            call    expr
            call    expect
            db      ')'
            rtn

; ------------------------------------------------------------------ variables and arrays
; varref: TP at a variable or array element -> R8 = the address of its value (TP past it).
varref:     lda     tp
            xri     TK_VAR
            jnz     vr_arr
            lda     tp
            plo     r8
            ldi     high varvals
            phi     r8
            rtn
vr_arr:     xri     TK_VAR ^ TK_ARR
            lbnz    syntax_err
            lda     tp
            stxd                        ; [slot*2]
            call    expect
            db      '('
            call    expr
            push    acc                 ; [slot*2][i]
            ldn     tp
            xri     ','
            jnz     vr_one
            inc     tp
            call    expr                ; ACC = j
            ldi     2
            jmp     vr_close
vr_one:     ldi     1
vr_close:   stxd                        ; [slot*2][i][dims]
            call    expect
            db      ')'
            irx
            ldx
            plo     rc                  ; RC.0 = dims used
            pop     r7                  ; R7 = i
            irx
            ldx
            plo     r8                  ; R8 -> the array's pointer
            ldi     high varvals
            phi     r8
            lda     r8
            phi     r9
            ldn     r8
            plo     r9
            dec     r8
            ghi     r9
            jnz     vr_have
            ; not dimensioned: DIM it (10) on first use, 1-D only
            glo     rc
            xri     1
            lbnz    subscr_err
            push    r7
            push    acc
            ldiw    r7, 10
            ldi     0
            phi     acc
            plo     acc
            call    dim_alloc           ; R9 = the block
            pop     acc
            pop     r7
            ldi     1
            plo     rc
vr_have:    lda     r9                  ; same number of subscripts?
            str     r2
            glo     rc
            xor
            lbnz    subscr_err
            lda     r9                  ; i < n1 (unsigned: negative i fails too)
            phi     rf
            lda     r9
            plo     rf
            glo     rf
            str     r2
            glo     r7
            sm
            ghi     rf
            str     r2
            ghi     r7
            smb
            lbdf    subscr_err
            glo     rc
            xri     1
            jz      vr_1d
            lda     r9                  ; 2-D: j < n2, index = i * n2 + j
            phi     rf
            lda     r9
            plo     rf
            glo     rf
            str     r2
            glo     acc
            sm
            ghi     rf
            str     r2
            ghi     acc
            smb
            lbdf    subscr_err
            push    r9
            push    acc                 ; j
            mov     acc, r7             ; i * n2
            call    mul16
            pop     rf
            call    op_add              ; + j
            pop     r9
            jmp     vr_addr
vr_1d:      inc     r9                  ; past n2
            inc     r9
            mov     acc, r7
vr_addr:    glo     acc                 ; R8 = R9 + index * 2
            shl
            plo     acc
            ghi     acc
            shlc
            phi     acc
            glo     acc
            str     r2
            glo     r9
            add
            plo     r8
            ghi     acc
            str     r2
            ghi     r9
            adc
            phi     r8
            rtn
subscr_err: error   E_SUBSCR

; DIM a(n)[, b(n,m) ...]
st_dim:     ldn     tp
            xri     TK_ARR
            lbnz    syntax_err
            inc     tp
            lda     tp
            stxd                        ; [slot*2]
            call    expect
            db      '('
            call    expr
            push    acc                 ; [slot*2][d1]
            ldn     tp
            xri     ','
            jnz     dm_one
            inc     tp
            call    expr                ; ACC = d2
            ldi     2
            jmp     dm_go
dm_one:     ldi     0
            phi     acc
            plo     acc
            ldi     1
dm_go:      stxd                        ; [slot*2][d1][dims]
            call    expect
            db      ')'
            irx
            ldx
            plo     rc
            pop     r7
            irx
            ldx
            plo     r8
            ldi     high varvals
            phi     r8
            ldn     r8                  ; already has one?
            lbnz    redim_err
            call    dim_alloc
            ldn     tp
            xri     ','
            jnz     dm_dn
            inc     tp
            jmp     st_dim
dm_dn:      rtn
redim_err:  error   E_REDIM

; dim_alloc: R8 -> an array's pointer, R7 = d1, ACC = d2, RC.0 = dims.  Makes the block at arrend:
; [dims][d1+1][d2+1][elements, all 0] and points the variable at it.  -> R9 = the block.
dim_alloc:  ghi     r7                  ; 0-32767 only
            ani     80h
            lbnz    value_err
            ghi     acc
            ani     80h
            lbnz    value_err
            inc     r7
            inc     acc
            push    r8                  ; [ptr]
            glo     rc
            stxd                        ; [ptr][dims]
            push    r7                  ; [ptr][dims][n1]
            push    acc                 ; [ptr][dims][n1][n2]
            mov     rf, r7
            call    umul32              ; RA:RC = n1 * n2
            ghi     ra
            lbnz    mem_err
            glo     ra
            lbnz    mem_err
            ghi     rc
            ani     0c0h
            lbnz    mem_err
            glo     rc                  ; RC = 2 * n1 * n2 + 5
            shl
            plo     rc
            ghi     rc
            shlc
            phi     rc
            glo     rc
            adi     5
            plo     rc
            ghi     rc
            adci    0
            phi     rc
            zp_at   r8, arrend          ; R9 = the block, RF = its end
            lda     r8
            phi     r9
            ldn     r8
            plo     r9
            glo     rc
            str     r2
            glo     r9
            add
            plo     rf
            ghi     rc
            str     r2
            ghi     r9
            adc
            phi     rf
            lbdf    mem_err
            glo     rf                  ; RF <= MEMTOP?
            smi     low (MEMTOP + 1)
            ghi     rf
            smbi    high (MEMTOP + 1)
            lbdf    mem_err
            ghi     rf                  ; arrend = RF
            str     r8
            dec     r8
            ghi     rf
            str     r8
            inc     r8
            glo     rf
            str     r8
            push    r9                  ; zero the block
da_zero:    glo     rc
            jnz     da_z1
            ghi     rc
            jz      da_z2
da_z1:      ldi     0
            str     r9
            inc     r9
            dec     rc
            jmp     da_zero
da_z2:      pop     r9
            pop     acc                 ; n2
            pop     r7                  ; n1
            irx
            ldx                         ; dims
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
            dec     r9                  ; back to the block
            dec     r9
            dec     r9
            dec     r9
            pop     r8                  ; the pointer
            ghi     r9
            str     r8
            inc     r8
            glo     r9
            str     r8
            rtn
mem_err:    error   E_MEMORY

; fre_value: ACC = free bytes (MEMTOP - arrend)
fre_value:  zp_at   r8, arrend
            lda     r8
            phi     rf
            ldn     r8
            plo     rf
            glo     rf
            sdi     low MEMTOP
            plo     acc
            ghi     rf
            sdbi    high MEMTOP
            phi     acc
            rtn

; ------------------------------------------------------------------ functions (TP after the name)
fn_abs:     call    paren
            ghi     acc
            ani     80h
            lbnz    neg_acc
            rtn
fn_sgn:     call    paren
            ghi     acc
            ani     80h
            jnz     sg_neg
            glo     acc
            jnz     sg_pos
            ghi     acc
            jz      sg_dn
sg_pos:     ldiw    acc, 1
sg_dn:      rtn
sg_neg:     ldiw    acc, 0ffffh
            rtn
; RND(n): 0 .. n-1 for n > 0; RND(0): 0 .. 32767; RND(-n): new seed n (returns 0)
fn_rnd:     call    paren
            ghi     acc
            ani     80h
            jz      rnd_pos
            zp_at   r9, rndseed
            ghi     acc
            str     r9
            inc     r9
            glo     acc
            str     r9
            ldi     0
            phi     acc
            plo     acc
            rtn
rnd_pos:    push    acc
            call    rnd_next            ; RF = 15 random bits
            pop     acc
            glo     acc
            jnz     rnd_mod
            ghi     acc
            jnz     rnd_mod
            mov     acc, rf
            rtn
rnd_mod:    call    udiv                ; RF mod ACC -> R8
            mov     acc, r8
            rtn
; rnd_next: xorshift16 (7, 9, 8) on rndseed -> RF = the new value AND 7FFF
rnd_next:   zp_at   r9, rndseed
            lda     r9
            phi     r7
            ldn     r9
            plo     r7
            ghi     r7                  ; x ^= x << 7
            shr
            glo     r7
            shrc
            str     r2
            ghi     r7
            xor
            phi     r7
            ldi     0
            shrc
            str     r2
            glo     r7
            xor
            plo     r7
            ghi     r7                  ; x ^= x >> 9
            shr
            str     r2
            glo     r7
            xor
            plo     r7
            glo     r7                  ; x ^= x << 8
            str     r2
            ghi     r7
            xor
            phi     r7
            glo     r7
            str     r9
            dec     r9
            ghi     r7
            str     r9
            ani     7fh
            phi     rf
            glo     r7
            plo     rf
            rtn
fn_peek:    call    paren
            ldn     acc
            plo     acc
            ldi     0
            phi     acc
            rtn
fn_inp:     call    expect
            db      '('
            call    port_expr
            call    expect
            db      ')'
            call    inpstub
            plo     acc
            ldi     0
            phi     acc
            rtn
; USR(a[,v]): machine code at a, called with SCRT, RF = v; returns RF (TP is kept for it)
fn_usr:     call    expect
            db      '('
            call    expr
            push    acc
            ldi     0
            phi     acc
            plo     acc
            ldn     tp
            xri     ','
            jnz     usr_1
            inc     tp
            call    expr
usr_1:      call    expect
            db      ')'
            pop     r8
            ldiw    r9, usr_call + 1
            ghi     r8
            str     r9
            inc     r9
            glo     r8
            str     r9
            mov     rf, acc
            push    tp
usr_call:   sep     r4
            dw      0
            pop     tp
            mov     acc, rf
            rtn
fn_fre:     ldn     tp                  ; FRE or FRE(x)
            xri     '('
            jnz     fre_1
            call    paren
fre_1:      lbr     fre_value
fn_inkey:   call    keyhit
            plo     acc
            ldi     0
            phi     acc
            lbdf    ik_dn
            plo     acc
ik_dn:      rtn

; ------------------------------------------------------------------ operators: ACC = RF op ACC
op_add:     glo     acc
            str     r2
            glo     rf
            add
            plo     acc
            ghi     acc
            str     r2
            ghi     rf
            adc
            phi     acc
            rtn
op_sub:     glo     acc
            str     r2
            glo     rf
            sm
            plo     acc
            ghi     acc
            str     r2
            ghi     rf
            smb
            phi     acc
            rtn
op_and:     glo     acc
            str     r2
            glo     rf
            and
            plo     acc
            ghi     acc
            str     r2
            ghi     rf
            and
            phi     acc
            rtn
op_or:      glo     acc
            str     r2
            glo     rf
            or
            plo     acc
            ghi     acc
            str     r2
            ghi     rf
            or
            phi     acc
            rtn
op_xor:     glo     acc
            str     r2
            glo     rf
            xor
            plo     acc
            ghi     acc
            str     r2
            ghi     rf
            xor
            phi     acc
            rtn
op_mul:     lbr     mul16
op_div:     call    sdiv
            mov     acc, r7
            rtn
op_mod:     call    sdiv
            mov     acc, r8
            rtn
op_eq:      call    cmp_s
            jz      op_true
            jmp     op_false
op_ne:      call    cmp_s
            jnz     op_true
            jmp     op_false
op_lt:      call    cmp_s
            jnf     op_true
            jmp     op_false
op_ge:      call    cmp_s
            jdf     op_true
            jmp     op_false
op_gt:      call    cmp_s
            jz      op_false
            jdf     op_true
            jmp     op_false
op_le:      call    cmp_s
            jz      op_true
            jnf     op_true
op_false:   ldi     0
            phi     acc
            plo     acc
            rtn
op_true:    ldi     0ffh
            phi     acc
            plo     acc
            rtn

; cmp_s: compare RF with ACC, signed: D = 0 if equal, DF = 1 if RF >= ACC
cmp_s:      glo     acc
            str     r2
            glo     rf
            sm
            plo     re
            ghi     acc
            xri     80h
            str     r2
            ghi     rf
            xri     80h
            smb
            str     r2
            glo     re
            or
            rtn

; mul16: ACC = RF * ACC (the low 16 bits; the same for signed numbers).  Uses R7.
mul16:      ghi     rf                  ; loop over the operand with the smaller high byte
            str     r2
            ghi     acc
            sm
            jnf     mu_go0
            jz      mu_go0
            mov     r7, rf              ; swap
            mov     rf, acc
            mov     acc, r7
mu_go0:     ldi     0
            phi     r7
            plo     r7
mu_loop:    glo     acc
            jnz     mu_go
            ghi     acc
            jz      mu_dn
mu_go:      ghi     acc
            shr
            phi     acc
            glo     acc
            shrc
            plo     acc
            jnf     mu_noadd
            glo     rf
            str     r2
            glo     r7
            add
            plo     r7
            ghi     rf
            str     r2
            ghi     r7
            adc
            phi     r7
mu_noadd:   glo     rf
            shl
            plo     rf
            ghi     rf
            shlc
            phi     rf
            jmp     mu_loop
mu_dn:      mov     acc, r7
            rtn

; umul32: RA:RC = RF * ACC (unsigned, 32 bits).  Uses R7; RF and ACC are destroyed.
umul32:     ldi     0
            phi     ra
            plo     ra
            phi     rc
            plo     rc
            phi     r7
            plo     r7
um_loop:    glo     acc
            jnz     um_go
            ghi     acc
            jz      um_dn
um_go:      ghi     acc
            shr
            phi     acc
            glo     acc
            shrc
            plo     acc
            jnf     um_noadd
            glo     rf                  ; RA:RC += R7:RF
            str     r2
            glo     rc
            add
            plo     rc
            ghi     rf
            str     r2
            ghi     rc
            adc
            phi     rc
            glo     r7
            str     r2
            glo     ra
            adc
            plo     ra
            ghi     r7
            str     r2
            ghi     ra
            adc
            phi     ra
um_noadd:   glo     rf                  ; R7:RF <<= 1
            shl
            plo     rf
            ghi     rf
            shlc
            phi     rf
            glo     r7
            shlc
            plo     r7
            ghi     r7
            shlc
            phi     r7
            jmp     um_loop
um_dn:      rtn

; sdiv: RF / ACC, signed (truncated toward 0) -> R7 = quotient, R8 = remainder (the sign of RF).
sdiv:       glo     acc
            jnz     sd_ok
            ghi     acc
            jnz     sd_ok
            error   E_DIVZERO
sd_ok:      ghi     rf                  ; the signs: [remainder's][quotient's]
            stxd
            str     r2
            ghi     acc
            xor
            stxd
            ghi     acc                 ; |ACC|
            ani     80h
            jz      sd_a
            call    neg_acc
sd_a:       ghi     rf                  ; |RF|
            ani     80h
            jz      sd_b
            glo     rf
            sdi     0
            plo     rf
            ghi     rf
            sdbi    0
            phi     rf
sd_b:       call    udiv                ; RF = quotient, R8 = remainder
            mov     r7, rf
            irx                         ; the quotient's sign
            ldxa
            ani     80h
            jz      sd_c
            glo     r7
            sdi     0
            plo     r7
            ghi     r7
            sdbi    0
            phi     r7
sd_c:       ldx                         ; the remainder's sign
            ani     80h
            jz      sd_d
            glo     r8
            sdi     0
            plo     r8
            ghi     r8
            sdbi    0
            phi     r8
sd_d:       rtn

; udiv: RF / ACC unsigned (ACC <> 0, both <= 8000h) -> RF = quotient, R8 = remainder.  Uses RC.
udiv:       ldi     0
            phi     r8
            plo     r8
            ldi     16
            plo     rc
ud_loop:    glo     rf
            shl
            plo     rf
            ghi     rf
            shlc
            phi     rf
            glo     r8
            shlc
            plo     r8
            ghi     r8
            shlc
            phi     r8
            glo     acc
            str     r2
            glo     r8
            sm
            plo     re
            ghi     acc
            str     r2
            ghi     r8
            smb
            jnf     ud_no
            phi     r8
            glo     re
            plo     r8
            glo     rf
            ori     1
            plo     rf
ud_no:      dec     rc
            glo     rc
            jnz     ud_loop
            rtn
