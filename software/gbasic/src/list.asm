; GBASIC - LIST: turn a stored line back into text (also used by SAVE).

; listline: R9 -> a line record.  Prints "nnn text" and CR LF through putc.  Keeps R9.
; Spacing: a word keyword gets a space before it after a letter, digit, ')', '"' or '$', and a space after it unless
; it is a function, ends in '(' or is followed by ':' ',' ';' ')' or the end.  Names and numbers get a space
; before them after a letter or digit (so that A B does not come back as AB).  RC.1 = the last character printed.
listline:   push    r9
            inc     r9
            lda     r9
            phi     acc
            lda     r9
            plo     acc
            call    printu
            call    space
            mov     ra, r9              ; RA -> the tokens
            ldi     ' '
            phi     rc
ll_loop:    lda     ra
            jz      ll_end
            plo     rc                  ; RC.0 = the token
            smi     TK_NUM
            jz      ll_num
            smi     TK_HEX - TK_NUM
            jz      ll_hex
            smi     TK_VAR - TK_HEX
            jz      ll_var
            smi     TK_ARR - TK_VAR
            jz      ll_var
            glo     rc
            xri     '"'
            jz      ll_str
            glo     rc
            ani     80h
            jnz     ll_kw
            glo     rc                  ; any other character, as it is
            call    ll_put
            jmp     ll_loop
ll_end:     call    newline
            pop     r9
            rtn
; a number
ll_num:     call    ll_alsp
            lda     ra
            phi     acc
            lda     ra
            plo     acc
            call    printu
            ldi     '0'
            phi     rc
            jmp     ll_loop
ll_hex:     ldi     '&'
            call    ll_put
            ldi     'H'
            call    ll_put
            lda     ra
            call    ll_hex2
            lda     ra
            call    ll_hex2
            ldi     '0'
            phi     rc
            jmp     ll_loop
; a variable: its name from varnames
ll_var:     call    ll_alsp
            lda     ra                  ; slot * 2
            plo     r8
            ldi     high varnames
            phi     r8
            lda     r8
            ani     7fh
            call    ll_put
            ldn     r8
            ani     7fh
            jz      ll_loop
            call    ll_put
            jmp     ll_loop
; a string literal
ll_str:     glo     rc
            call    ll_put
ll_s1:      ldn     ra
            jz      ll_loop
            lda     ra
            call    ll_put
            xri     '"'
            jnz     ll_s1
            jmp     ll_loop
; a keyword
ll_kw:      glo     rc                  ; R8 = its name
            smi     80h
            shl
            adi     low kwaddr
            plo     r8
            ldi     high kwaddr
            adci    0
            phi     r8
            lda     r8
            plo     re
            ldn     r8
            plo     r8
            glo     re
            phi     r8
            ldn     r8                  ; a word keyword (starts with a letter)?
            ani     7fh
            smi     'A'
            jnf     ll_kwsym
            ghi     rc                  ; space before it?
            call    ll_isal
            jdf     ll_kwsp
            ghi     rc
            xri     ')'
            jz      ll_kwsp
            ghi     rc
            xri     '"'
            jz      ll_kwsp
            ghi     rc
            xri     '$'
            jnz     ll_kwsym
ll_kwsp:    call    space
ll_kwsym:   lda     r8                  ; the name (SCRT calls use RE.0: the byte goes on the stack)
            stxd
            ani     7fh
            call    ll_put
            irx
            ldx
            ani     80h
            jz      ll_kwsym
            glo     rc                  ; REM and ': the rest as it was typed
            xri     TK_REM
            jz      ll_rest
            glo     rc
            xri     TK_REM2
            jz      ll_rest
            ghi     rc                  ; ends in '(' or is a symbol: no space after
            xri     '('
            jz      ll_loop
            ghi     rc
            call    ll_isal
            jnf     ll_loop
            glo     rc                  ; a function: no space after
            smi     FN_FIRST
            jnf     ll_kwa
            smi     FN_LAST - FN_FIRST + 1
            jnf     ll_loop
ll_kwa:     ldn     ra                  ; followed by : , ; ) or the end: no space
            jz      ll_loop
            xri     ':'
            jz      ll_loop
            ldn     ra
            xri     ','
            jz      ll_loop
            ldn     ra
            xri     ';'
            jz      ll_loop
            ldn     ra
            xri     ')'
            jz      ll_loop
            call    space
            ldi     ' '
            phi     rc
            jmp     ll_loop
ll_rest:    lda     ra
            jz      ll_end
            call    ll_put
            jmp     ll_rest

; ll_put: print D and remember it in RC.1
ll_put:     phi     rc
            lbr     putc
; ll_alsp: a space if the last character was a letter or a digit
ll_alsp:    ghi     rc
            call    ll_isal
            lbdf    space
            rtn
; ll_isal: DF = 1 if D is a letter or a digit (D kept)
ll_isal:    plo     re
            smi     '0'
            jnf     lia_no
            smi     10
            jnf     lia_yes
            glo     re
            ani     0dfh
            smi     'A'
            jnf     lia_no
            smi     26
            jnf     lia_yes
lia_no:     glo     re
            adi     0
            glo     re
            rtn
lia_yes:    glo     re
            smi     0
            glo     re
            rtn
; ll_hex2: print D as 2 hex digits
ll_hex2:    plo     re
            stxd
            shr
            shr
            shr
            shr
            call    ll_hex1
            irx
            ldx
ll_hex1:    ani     0fh
            smi     10
            jnf     llh_dig
            adi     7                   ; 10-15 -> 'A'-'F' after the add below
llh_dig:    adi     '0' + 10
            lbr     putc

; ------------------------------------------------------------------ LIST [from][-[to]]
; Any key pauses (another key goes on); Ctrl-C or Esc stops.
st_list:    call    range               ; RA = first line to show, R7 = last line number
            mov     r9, ra
sl_loop:    ldn     r9
            jz      sl_dn
            inc     r9                  ; past the last number?
            lda     r9
            str     r2
            ghi     r7
            sm
            jnf     sl_dn0
            jnz     sl_ok
            ldn     r9
            str     r2
            glo     r7
            sm
            jnf     sl_dn0
sl_ok:      dec     r9
            dec     r9
            push    r7
            call    listline
            push    r9
            call    keyhit              ; a key: pause, or stop
            jnf     sl_nokey
            xri     3
            jz      sl_stop
            xri     3 ^ 1bh
            jz      sl_stop
            call    getkey
            xri     3
            jz      sl_stop
            xri     3 ^ 1bh
            jz      sl_stop
sl_nokey:   pop     r9
            pop     r7
sl_next:    ldn     r9                  ; next line
            str     r2
            glo     r9
            add
            plo     r9
            ghi     r9
            adci    0
            phi     r9
            jmp     sl_loop
sl_stop:    pop     r9
            pop     r7
sl_dn0:
sl_dn:      rtn

; range: parse [a][-[b]] at TP -> RA = the first line with number >= a, R7 = b (65535 if not given).
; Also used by DELETE.
range:      ldi     0
            phi     acc
            plo     acc
            plo     r8                  ; R8.0 = 1 if a was given
            ldn     tp
            xri     TK_NUM
            jnz     rg_nofirst
            inc     tp
            lda     tp
            phi     acc
            lda     tp
            plo     acc
            ldi     1
            plo     r8
rg_nofirst: mov     r7, acc             ; b = a
            ldn     tp
            xri     TK_MINUS
            jz      rg_dash
            glo     r8                  ; "a" alone: just that line
            jnz     rg_find
rg_all:     ldi     0ffh
            phi     r7
            plo     r7
            jmp     rg_find
rg_dash:    inc     tp
            ldn     tp
            xri     TK_NUM
            jnz     rg_all
            inc     tp
            lda     tp
            phi     r7
            lda     tp
            plo     r7
rg_find:    push    r7
            call    find_line           ; RA = previous, R9 = first >= a
            pop     r7
            mov     ra, r9
            rtn
