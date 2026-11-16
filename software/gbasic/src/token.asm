; GBASIC - the tokenizer: linebuf (text) -> tokbuf (tokens).
;
; Keywords become one byte (80h up, tables.inc); numbers become TK_NUM/TK_HEX + 2 bytes; a variable name (a letter,
; or a letter and a letter or digit) becomes TK_VAR/TK_ARR + its slot * 2; strings and the text after REM or ' stay
; as typed; spaces elsewhere are dropped (LIST puts them back).  Letters outside strings may be typed in lower case.

; tokenize: DF = 1 if the line starts with a line number (then lineno = it).  tklen = bytes of tokens (no 0).
; Uses R7, R8, R9, RA, RC, RF, ACC.
tokenize:   ldiw    rf, linebuf
            ldiw    r9, tokbuf
            zp_at   r8, numflag
            ldi     0
            str     r8
            call    skipsp
            call    isdigit
            jnf     tk_loop
            call    parse_dec           ; ACC = the line number
            glo     acc
            jnz     tk_lnok
            ghi     acc
            lbz     syntax_err          ; line 0
tk_lnok:    zp_at   r8, lineno
            ghi     acc
            str     r8
            inc     r8
            glo     acc
            str     r8
            zp_at   r8, numflag
            ldi     1
            str     r8
tk_loop:    glo     r9                  ; room left? (tokbuf is page aligned: R9.0 = length)
            smi     250
            jdf     tk_long
            ldn     rf
            jz      tk_finish
            xri     ' '
            jnz     tk_1
            inc     rf                  ; spaces vanish
            jmp     tk_loop
tk_long:    error   E_LONG
tk_1:       ldn     rf
            xri     '"'
            jz      tk_str
            ldn     rf
            xri     '?'
            jnz     tk_2
            inc     rf                  ; ? = PRINT
            ldi     TK_PRINT
            str     r9
            inc     r9
            jmp     tk_loop
tk_2:       ldn     rf
            xri     27h                 ; ' = REM
            jnz     tk_3
            inc     rf
            ldi     TK_REM2
            str     r9
            inc     r9
            jmp     tk_rest
tk_3:       ldn     rf
            call    isdigit
            jnf     tk_4
            call    parse_dec
            ldi     TK_NUM
tk_numout:     str     r9
            inc     r9
            ghi     acc
            str     r9
            inc     r9
            glo     acc
            str     r9
            inc     r9
            jmp     tk_loop
tk_4:       ldn     rf
            xri     '&'
            jnz     tk_5
            inc     rf
            ldn     rf
            ani     0dfh
            xri     'H'
            lbnz    syntax_err
            inc     rf
            call    parse_hex
            ldi     TK_HEX
            jmp     tk_numout
tk_5:       ldn     rf
            call    isalpha
            jnf     tk_op
            call    kwmatch             ; a keyword here?
            jnf     tk_name
            str     r9
            inc     r9
            xri     TK_REM
            jz      tk_rest
            jmp     tk_loop
tk_name:     call    varname             ; R8 = name; RF past it
            call    skipsp              ; an array if '(' follows
            xri     '('
            jnz     tk_scalar
            glo     r8
            ori     80h
            plo     r8
tk_scalar:  call    findvar             ; D = slot * 2 (R8 kept)
            plo     rc
            glo     r8
            ani     80h
            jz      tk_isvar
            ldi     TK_ARR
            jmp     tk_emit
tk_isvar:   ldi     TK_VAR
tk_emit:    str     r9
            inc     r9
            glo     rc
            str     r9
            inc     r9
            jmp     tk_loop
; operators: < <> <= > >= = + - * /
tk_op:      lda     rf
            plo     rc                  ; RC.0 = the character
            xri     '<'
            jnz     tk_op2
            ldn     rf
            xri     '>'
            jnz     tk_op1
            inc     rf
            ldi     TK_NE
            jmp     tk_put
tk_op1:     ldn     rf
            xri     '='
            jnz     tk_op1b
            inc     rf
            ldi     TK_LE
            jmp     tk_put
tk_op1b:    ldi     TK_LT
            jmp     tk_put
tk_op2:     glo     rc
            xri     '>'
            jnz     tk_op3
            ldn     rf
            xri     '='
            jnz     tk_op2b
            inc     rf
            ldi     TK_GE
            jmp     tk_put
tk_op2b:    ldi     TK_GT
            jmp     tk_put
tk_op3:     glo     rc
            xri     '='
            jnz     tk_op4
            ldi     TK_EQ
            jmp     tk_put
tk_op4:     glo     rc
            xri     '+'
            jnz     tk_op5
            ldi     TK_PLUS
            jmp     tk_put
tk_op5:     glo     rc
            xri     '-'
            jnz     tk_op6
            ldi     TK_MINUS
            jmp     tk_put
tk_op6:     glo     rc
            xri     '*'
            jnz     tk_op7
            ldi     TK_MUL
            jmp     tk_put
tk_op7:     glo     rc
            xri     '/'
            jnz     tk_op8
            ldi     TK_DIV
            jmp     tk_put
tk_op8:     glo     rc                  ; anything else as typed: ( ) , ; : # etc.
tk_put:     str     r9
            inc     r9
            jmp     tk_loop
; a string: copy up to the closing quote (one is added if missing)
tk_str:     lda     rf
            str     r9
            inc     r9
tk_s1:      glo     r9
            smi     252
            jdf     tk_long
            ldn     rf
            jz      tk_s2
            lda     rf
            str     r9
            inc     r9
            xri     '"'
            jnz     tk_s1
            jmp     tk_loop
tk_s2:      ldi     '"'
            str     r9
            inc     r9
            jmp     tk_finish
; after REM or ': the rest of the line as typed
tk_rest:    glo     r9
            smi     253
            jdf     tk_long
            lda     rf
            str     r9
            inc     r9
            jnz     tk_rest
            dec     r9
tk_finish:     ldi     0
            str     r9
            glo     r9                  ; tklen
            plo     re
            zp_at   r8, tklen
            glo     re
            str     r8
            zp_at   r8, numflag         ; DF = had a line number
            ldn     r8
            shr
            zp_at   r8, lineno          ; ACC = the line number
            lda     r8
            phi     acc
            ldn     r8
            plo     acc
            rtn

; varname: RF at a letter -> R8.1 = the letter (upper case), R8.0 = the second character or 0.  A second letter is
; taken only if no keyword starts there (FORI=ATOB is FOR I = A TO B).  A third letter or digit is an error, unless
; a keyword starts there (IFAB THEN... and IFABTHEN both work; SCORE would read as SC OR E, as in Microsoft BASIC).
varname:    lda     rf
            ani     0dfh
            plo     re
            zp_at   r8, vname
            glo     re
            str     r8
            inc     r8
            ldi     0
            str     r8
            ldn     rf
            call    isdigit
            jdf     vn_take
            call    isalpha
            jnf     vn_dn
            call    kwmatch
            jdf     vn_kw
            ldn     rf
            ani     0dfh
vn_take:    plo     re
            zp_at   r8, vname + 1
            glo     re
            str     r8
            inc     rf
            ldn     rf                  ; a third character
            call    isdigit
            jdf     vn_long
            call    isalpha
            jnf     vn_dn
            call    kwmatch             ; a keyword may follow straight on
            jnf     vn_long
vn_kw:      mov     rf, rc              ; leave the keyword for the tokenizer
vn_dn:      zp_at   r8, vname
            lda     r8
            plo     re
            ldn     r8
            plo     r8
            glo     re
            phi     r8
            rtn
vn_long:    lbr     syntax_err

; findvar: R8 = name (letter; second character | 80h for an array) -> D = slot * 2.  New names are added.
findvar:    ldiw    ra, varnames
            zp_at   rc, nvars
            ldn     rc
            plo     rc                  ; RC.0 = names left to check
fv_loop:    glo     rc
            jz      fv_new
            lda     ra
            str     r2
            ghi     r8
            xor
            jnz     fv_skip
            ldn     ra
            str     r2
            glo     r8
            xor
            jz      fv_found
fv_skip:    inc     ra
            dec     rc
            jmp     fv_loop
fv_found:   dec     ra
            glo     ra                  ; varnames is page aligned: the offset is slot * 2
            rtn
fv_new:     zp_at   rc, nvars
            ldn     rc
            smi     MAXVARS
            jdf     fv_full
            ldn     rc
            adi     1
            str     rc
            ghi     r8
            str     ra
            inc     ra
            glo     r8
            str     ra
            dec     ra
            glo     ra                  ; and its value 0
            plo     rc
            ldi     high varvals
            phi     rc
            ldi     0
            str     rc
            inc     rc
            str     rc
            glo     ra
            rtn
fv_full:    error   E_VARS

; kwmatch: RF at a letter.  If a keyword starts there: DF = 1, D = its token, RF past it, RC = where it started.
; Else DF = 0 and RF unchanged.  Uses R7, R8, RA, RC, RE.
kwmatch:    ldn     rf
            ani     0dfh
            smi     'A'
            adi     low kwfirst
            plo     r8
            ldi     high kwfirst
            adci    0
            phi     r8                  ; R8 = &kwfirst[letter]
            lda     r8
            phi     r7                  ; R7.1 = i
            ldn     r8
            plo     r7                  ; R7.0 = end
km_next:    ghi     r7
            str     r2
            glo     r7
            sm                          ; end - i
            jz      km_fail
            ghi     r7                  ; token = kwlist[i]
            adi     low kwlist
            plo     r8
            ldi     high kwlist
            adci    0
            phi     r8
            ldn     r8
            plo     rc                  ; RC.0 = the token
            smi     80h                 ; R8 = kwaddr[token - 80h]
            shl
            adi     low kwaddr
            plo     r8
            ldi     high kwaddr
            adci    0
            phi     r8
            lda     r8
            phi     ra
            ldn     r8
            plo     r8
            ghi     ra
            phi     r8                  ; R8 = the name
            mov     ra, rf              ; RA = the input
km_cmp:     lda     ra                  ; input character, upper case if a letter
            plo     re
            smi     'a'
            jnf     km_c1
            smi     26
            jdf     km_c1
            glo     re
            smi     20h
            plo     re
km_c1:      lda     r8                  ; name character (the last has bit 7)
            phi     re
            ani     7fh
            str     r2
            glo     re
            xor
            jnz     km_miss
            ghi     re
            ani     80h
            jz      km_cmp
            glo     rc                  ; matched: RC = start, RF = past the keyword
            plo     re
            mov     rc, rf
            mov     rf, ra
            glo     re
            smi     0                   ; DF = 1, D = the token
            glo     re
            rtn
km_miss:    ghi     r7
            adi     1
            phi     r7
            jmp     km_next
km_fail:    adi     0                   ; DF = 0
            rtn

; skipsp: RF past spaces; D = the character there
skipsp:     ldn     rf
            xri     ' '
            jnz     sk_dn
            inc     rf
            jmp     skipsp
sk_dn:      ldn     rf
            rtn

; isdigit: DF = 1 if D is 0-9 (D unchanged)
isdigit:    plo     re
            smi     '0'
            jnf     isd_no
            smi     10
            jdf     isd_no
            glo     re
            smi     0
            glo     re
            rtn
isd_no:     glo     re
            adi     0
            glo     re
            rtn

; isalpha: DF = 1 if D is a letter, then D = it in upper case; else DF = 0, D unchanged
isalpha:    plo     re
            ani     0dfh
            smi     'A'
            jnf     isd_no
            smi     26
            jdf     isd_no
            glo     re
            ani     0dfh
            smi     0
            glo     re
            ani     0dfh
            rtn

; ishex: DF = 1 and D = 0-15 if D is a hex digit (either case); else DF = 0
ishex:      call    isdigit
            jnf     ish_a
            smi     '0'
            smi     0                   ; DF = 1 (D unchanged)
            rtn
ish_a:      call    isalpha
            jnf     ish_no
            smi     'A'
            smi     6
            jdf     ish_no
            adi     6 + 10              ; A-F -> 10-15 (adi sets DF = 0 here: no carry)
            plo     re
            smi     0
            glo     re
            rtn
ish_no:     adi     0
            rtn

; parse_dec: RF at a digit -> ACC = the number (0-65535; Overflow error if bigger), RF past it.  Uses R7.
; parse_num: the same, but DF = 1 instead of the error (for INPUT).
parse_dec:  call    parse_num
            lbdf    pd_ovf
            rtn
parse_num:  ldi     0
            phi     acc
            plo     acc
pd_loop:    ldn     rf
            call    isdigit
            jnf     pd_dn
            ; ACC = ACC * 10 + digit
            glo     acc                 ; R7 = ACC * 2
            shl
            plo     r7
            ghi     acc
            shlc
            phi     r7
            jdf     pd_bad
            glo     r7                  ; ACC = R7 * 4
            shl
            plo     acc
            ghi     r7
            shlc
            phi     acc
            jdf     pd_bad
            glo     acc
            shl
            plo     acc
            ghi     acc
            shlc
            phi     acc
            jdf     pd_bad
            glo     r7                  ; + R7 = ACC * 10
            str     r2
            glo     acc
            add
            plo     acc
            ghi     r7
            str     r2
            ghi     acc
            adc
            phi     acc
            jdf     pd_bad
            lda     rf                  ; + digit
            smi     '0'
            str     r2
            glo     acc
            add
            plo     acc
            ghi     acc
            adci    0
            phi     acc
            jdf     pd_bad
            jmp     pd_loop
pd_dn:      adi     0                   ; DF = 0
            rtn
pd_bad:     smi     0                   ; DF = 1
            rtn
pd_ovf:     error   E_OVERFLOW

; parse_hex: RF at hex digits -> ACC (1-4 digits), RF past them; errors if none or too many.
; parse_hexn: the same, DF = 1 instead of an error.
parse_hex:  call    parse_hexn
            lbdf    pd_ovf
            rtn
parse_hexn: ldi     0
            phi     acc
            plo     acc
            plo     r7                  ; digits seen
ph_loop:    ldn     rf
            call    ishex
            jnf     ph_dn
            plo     re                  ; the digit (no SCRT calls until it is used)
            ghi     acc                 ; a fifth digit: overflow
            ani     0f0h
            jnz     pd_bad
            ldi     4
            plo     rc
ph_sh:      glo     acc
            shl
            plo     acc
            ghi     acc
            shlc
            phi     acc
            dec     rc
            glo     rc
            jnz     ph_sh
            glo     re
            str     r2
            glo     acc
            or
            plo     acc
            inc     rf
            inc     r7
            jmp     ph_loop
ph_dn:      glo     r7
            jz      pd_bad              ; &H with no digits
            adi     0
            rtn
