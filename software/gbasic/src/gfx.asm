; GBASIC - VIDEO-G: detection, the display switches and the drawing commands.
;
; The graphics window 7800-783F is pixel line Y (OUT 7); bit 7 of byte 0 is x = 0.  x 0-511, y 0-199 (NTSC) or
; 0-255 (IBM 5151, MONITOR jumper).  Everything is clipped to the screen.  PEN 1 draws (OR), PEN 0 erases (AND NOT),
; PEN 2 inverts (XOR); every pixel of a shape is touched once, so drawing a shape twice with PEN 2 removes it.

; ------------------------------------------------------------------ detection, control register
; vg_detect: INP 4; VIDEO-G answers 10xxxxxx (a missing card floats: the INP opcode itself, 6C, or FF here).
; Then the control register = 00 (text on, graphics off; the ELF/OS boot loader writes sector numbers to port 4),
; and with the GFX board both graphics pages are cleared.
vg_detect:  sex     r2
            inp     VGPORT
            plo     re
            ani     0c0h
            xri     80h
            jnz     vd_none
            zp_at   r9, vgstat
            glo     re
            str     r9
            ani     ST_GFX
            jz      vd_none
            zp_at   r9, gfxok
            ldi     1
            str     r9
            zp_at   r9, gheight         ; 200 or 256 lines
            glo     re
            ani     ST_MONITOR
            jz      vd_ntsc
            ldi     1
            str     r9
            inc     r9
            ldi     0
            str     r9
            jmp     vd_none
vd_ntsc:    ldi     0
            str     r9
            inc     r9
            ldi     200
            str     r9
vd_none:    zp_at   r9, ctrl
            ldi     0
            str     r9
            str     r2
            out     VGPORT
            dec     r2
            zp_at   r9, pen
            ldi     1
            str     r9
            zp_at   r9, gfxok
            ldn     r9
            jz      vd_dn
            ldi     CTL_CPAGE           ; clear page 1, then page 0
            call    setctrl_d
            ldi     0
            call    gerase
            ldi     0
            call    setctrl_d
            ldi     0
            call    gerase
vd_dn:      rtn

vg_banner:  zp_at   r9, vgstat
            ldn     r9
            jz      vb_none
            zp_at   r9, gfxok
            ldn     r9
            jz      vb_text
            ldiw    rf, m_vggfx
            call    puts
            zp_at   r9, gheight
            lda     r9
            phi     acc
            ldn     r9
            plo     acc
            call    printu
            lbr     newline
vb_text:    ldiw    rf, m_vgtext
            jmp     vb_put
vb_none:    ldiw    rf, m_novg
vb_put:     call    puts
            lbr     newline
m_vggfx:    db      "VIDEO-G graphics 512 x ",0
m_vgtext:   db      "VIDEO-G text, no GFX board: no graphics",0
m_novg:     db      "No VIDEO-G: text only",0

; setctrl: OUT 4 = ctrl.   setctrl_d: ctrl = D, then OUT 4.
setctrl_d:  plo     re
            zp_at   r9, ctrl
            glo     re
            str     r9
setctrl:    zp_at   r9, ctrl
            ldn     r9
            str     r2
            out     VGPORT
            dec     r2
            rtn
; vg_textsafe: back in direct mode, the text must show (graphics stay as they are)
vg_textsafe: zp_at  r9, vgstat
            ldn     r9
            jz      vts_dn
            ldi     low ctrl
            plo     r9
            ldn     r9
            ani     CTL_TEXTOFF
            jz      vts_dn
            ldn     r9
            ani     0ffh - CTL_TEXTOFF
            str     r9
            jmp     setctrl
vts_dn:     rtn
; vg_reset: (BYE) text on, graphics off, page 0
vg_reset:   zp_at   r9, vgstat
            ldn     r9
            jz      vts_dn
            ldi     0
            jmp     setctrl_d
gfx_need:   zp_at   r9, gfxok
            ldn     r9
            lbz     nogfx_err
            rtn
nogfx_err:  error   E_NOGFX

; ------------------------------------------------------------------ GRAPHICS TEXT MIX PAGE PEN
; onoff: ON -> D = 1, OFF -> D = 0
onoff:      lda     tp
            xri     TK_ON
            jz      oo_on
            dec     tp
            lda     tp
            xri     TK_OFF
            lbnz    syntax_err
            ldi     0
            rtn
oo_on:      ldi     1
            rtn
st_graphics: call   gfx_need
            call    onoff
            plo     rc
            zp_at   r9, ctrl
            ldn     r9
            ani     0ffh - CTL_GFXON
            plo     re
            glo     rc
            jz      sg_set
            glo     re
            ori     CTL_GFXON
            plo     re
sg_set:     glo     re
            lbr     setctrl_d
st_text:    call    gfx_need            ; (the control register is on the GFX board)
            call    onoff
            plo     rc
            zp_at   r9, ctrl
            ldn     r9
            ori     CTL_TEXTOFF
            plo     re
            glo     rc
            jz      sg_set
            glo     re
            ani     0ffh - CTL_TEXTOFF
            plo     re
            jmp     sg_set
st_mix:     call    gfx_need            ; MIX OR / MIX XOR: how text and graphics combine
            lda     tp
            plo     rc
            zp_at   r9, ctrl
            ldn     r9
            ani     0ffh - CTL_XOR
            plo     re
            glo     rc
            xri     TK_OR
            jz      sg_set
            glo     rc
            xri     TK_XOR
            lbnz    syntax_err
            glo     re
            ori     CTL_XOR
            plo     re
            jmp     sg_set
; PAGE show [, draw]: the page displayed and the page drawn on (0 or 1); draw = show if not given
st_page:    call    gfx_need
            call    expr
            call    bit01
            stxd                        ; show
            stxd                        ; draw (= show unless given)
            ldn     tp
            xri     ','
            jnz     pg_pop
            inc     tp
            call    expr
            call    bit01
            irx
            stxd
pg_pop:     irx
            ldxa
            phi     rc                  ; RC.1 = draw
            ldx
            plo     rc                  ; RC.0 = show
pg_set:     zp_at   r9, ctrl
            ldn     r9
            ani     0ffh - CTL_DPAGE - CTL_CPAGE
            plo     re
            glo     rc
            jz      pg_1
            glo     re
            ori     CTL_DPAGE
            plo     re
pg_1:       ghi     rc
            jz      pg_2
            glo     re
            ori     CTL_CPAGE
            plo     re
pg_2:       glo     re
            lbr     setctrl_d
bit01:      ghi     acc                 ; ACC must be 0 or 1 -> D
            lbnz    value_err
            glo     acc
            smi     2
            lbdf    value_err
            glo     acc
            rtn
; PEN 0 erase, 1 draw, 2 invert
st_pen:     call    expr
            ghi     acc
            lbnz    value_err
            glo     acc
            smi     3
            lbdf    value_err
            zp_at   r9, pen
            glo     acc
            str     r9
            rtn

; ------------------------------------------------------------------ argument helpers
; args_n: D = n: n expressions separated by commas -> argv[0..n-1]
args_n:     plo     rc
            ldi     low argv
            phi     rc                  ; RC.1 = where the next one goes
an_loop:    glo     rc
            stxd
            ghi     rc
            stxd
            call    expr
            irx
            ldxa
            phi     rc
            ldx
            plo     rc
            ghi     rc
            plo     r9
            ldi     high zp
            phi     r9
            ghi     acc
            str     r9
            inc     r9
            glo     acc
            str     r9
            ghi     rc
            adi     2
            phi     rc
            dec     rc
            glo     rc
            jz      an_dn
            glo     rc
            stxd
            call    expect
            db      ','
            irx
            ldx
            plo     rc
            jmp     an_loop
an_dn:      rtn
; opt_fill: [, F] or [, expr]: fill = 1 if F (the bare letter) or the expression is not 0
opt_fill:   zp_at   r9, gfill
            ldi     0
            str     r9
            ldn     tp
            xri     ','
            jnz     of_dn
            inc     tp
            ldn     tp                  ; the variable F on its own?
            xri     TK_VAR
            jnz     of_expr
            inc     tp
            ldn     tp
            plo     r8
            dec     tp
            ldi     high varnames
            phi     r8
            lda     r8
            xri     'F'
            jnz     of_expr
            ldn     r8
            jnz     of_expr
            inc     tp
            inc     tp
            call    at_end
            jdf     of_yes
            dec     tp                  ; F was the start of an expression after all
            dec     tp
of_expr:    call    expr
            glo     acc
            jnz     of_yes
            ghi     acc
            jz      of_dn
of_yes:     zp_at   r9, gfill
            ldi     1
            str     r9
of_dn:      rtn
; ld_r7, ld_r8, ld_acc: load a zero-page word (D = its offset); st_r7 stores R7.  They use R9.
ld_r7:      plo     r9                  ; R7 = zp word at offset D
            ldi     high zp
            phi     r9
            lda     r9
            phi     r7
            ldn     r9
            plo     r7
            rtn
ld_r8:      plo     r9
            ldi     high zp
            phi     r9
            lda     r9
            phi     r8
            ldn     r9
            plo     r8
            rtn
ld_acc:     plo     r9
            ldi     high zp
            phi     r9
            lda     r9
            phi     acc
            ldn     r9
            plo     acc
            rtn
st_r7:      plo     r9                  ; zp word at offset D = R7
            ldi     high zp
            phi     r9
            ghi     r7
            str     r9
            inc     r9
            glo     r7
            str     r9
            rtn

; ------------------------------------------------------------------ PSET/DOT, POINT, ERASE
st_pset:    call    gfx_need
            ldi     2
            call    args_n
            ldi     low argv
            call    ld_r7
            ldi     low argv + 2
            call    ld_r8
            call    set_gxy             ; the graphics cursor = (R7, R8)
            lbr     plot

fn_point:   call    gfx_need
            call    expect
            db      '('
            ldi     2
            call    args_n
            call    expect
            db      ')'
            ldi     low argv
            call    ld_r7
            ldi     low argv + 2
            call    ld_r8
            ldi     0
            phi     acc
            plo     acc
            call    clip_xy             ; DF = 1 off the screen
            jdf     pt_dn
            glo     r8
            str     r2
            out     YPORT
            dec     r2
            call    pixaddr             ; RF, D = mask
            str     r2
            ldn     rf
            and
            jz      pt_dn
            inc     acc
pt_dn:      rtn

; ERASE [v]: fill the page being drawn on with the byte v (default 0 = clear)
st_erase:   call    gfx_need
            ldi     0
            phi     acc
            plo     acc
            call    at_end
            jdf     er_go
            call    expr
er_go:      glo     acc
            lbr     gerase

; gerase: D = byte: every line of the drawing page (64 STXD a line)
gerase:     phi     rc                  ; RC.1 = the byte
            zp_at   r9, gheight + 1     ; R7.0 = the line count (200, or 0 = 256)
            ldn     r9
            plo     r7
            ldi     0
            plo     rc                  ; RC.0 = y
ge_line:    glo     rc
            str     r2
            out     YPORT
            dec     r2
            ldiw    r9, GWIN + 63       ; 64 STXD, in line: no call for each line
            sex     r9
            ghi     rc
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            sex     r2
            inc     rc
            glo     rc
            str     r2
            glo     r7
            xor
            jnz     ge_line
            rtn

; ------------------------------------------------------------------ pixels and spans
; clip_xy: DF = 1 if (R7, R8) is off the screen
clip_xy:    ghi     r7
            ani     0feh
            jnz     cx_off
            ghi     r8
            jnz     cx_off
            zp_at   r9, gheight         ; 256 lines: any y.lo
            ldn     r9
            jnz     cx_on
            glo     r8
            smi     200
            jdf     cx_off
cx_on:      adi     0
            rtn
cx_off:     smi     0
            rtn
; pixaddr: R7 = x (0-511) -> RF = its byte in the window, D = its bit mask
pixaddr:    ghi     r7
            shr
            glo     r7
            shrc
            shr
            shr
            plo     rf
            ldi     high GWIN
            phi     rf
            glo     r7
            ani     7
            adi     low bitmask
            plo     r9
            ldi     high bitmask
            adci    0
            phi     r9
            ldn     r9
            rtn
bitmask:    db      80h,40h,20h,10h,08h,04h,02h,01h
lmasks:     db      0ffh,07fh,03fh,01fh,0fh,07h,03h,01h     ; from bit x&7 to the right end of the byte
rmasks:     db      80h,0c0h,0e0h,0f0h,0f8h,0fch,0feh,0ffh  ; from the left end of the byte to bit x&7

; pen_apply: D = mask, RF -> the byte: the pen on those bits
pen_apply:  plo     re
            zp_at   r9, pen
            ldn     r9
            jz      pa_erase
            xri     2
            jz      pa_inv
            glo     re
            str     r2
            ldn     rf
            or
            str     rf
            rtn
pa_erase:   glo     re
            xri     0ffh
            str     r2
            ldn     rf
            and
            str     rf
            rtn
pa_inv:     glo     re
            str     r2
            ldn     rf
            xor
            str     rf
            rtn

; plot: one pixel at (R7, R8), clipped
plot:       call    clip_xy
            jdf     plt_dn
            glo     r8
            str     r2
            out     YPORT
            dec     r2
            call    pixaddr
            lbr     pen_apply
plt_dn:     rtn

; hspan: the pixels R7 .. R9 (either order) of line R8, clipped; whole bytes at a time.  Uses R7-R9, RA, RC, RF.
hspan:      glo     r9                  ; order: R7 <= R9 (signed)
            str     r2
            glo     r7
            sm
            ghi     r9
            xri     80h
            str     r2
            ghi     r7
            xri     80h
            smb
            jnf     hspan_ord
            mov     rf, r7
            mov     r7, r9
            mov     r9, rf
hspan_ord:  ghi     r8                  ; (R7 <= R9 already) y on the screen?
            jnz     hs_dn
            zp_at   rf, gheight
            ldn     rf
            jnz     hs_ord
            glo     r8
            smi     200
            jdf     hs_dn
hs_ord:     ghi     r9                  ; R9 < 0: nothing
            ani     80h
            jnz     hs_dn
            ghi     r7                  ; R7 < 0: from 0
            ani     80h
            jz      hs_l1
            ldi     0
            phi     r7
            plo     r7
hs_l1:      ghi     r7                  ; R7 > 511: nothing
            ani     0feh
            jnz     hs_dn
            ghi     r9                  ; R9 > 511: to 511
            ani     0feh
            jz      hs_r1
            ldi     1
            phi     r9
            ldi     0ffh
            plo     r9
hs_r1:      glo     r8                  ; the line
            str     r2
            out     YPORT
            dec     r2
            glo     r7                  ; RA.0 = the left byte's mask, RA.1 = the right byte's
            ani     7
            adi     low lmasks
            plo     rf
            ldi     high lmasks
            adci    0
            phi     rf
            ldn     rf
            plo     ra
            glo     r9
            ani     7
            adi     low rmasks
            plo     rf
            ldi     high rmasks
            adci    0
            phi     rf
            ldn     rf
            phi     ra
            ghi     r9                  ; R9 = the right byte
            shr
            glo     r9
            shrc
            shr
            shr
            plo     r9
            ldi     high GWIN
            phi     r9
            ghi     r7                  ; RF = the left byte
            shr
            glo     r7
            shrc
            shr
            shr
            plo     rf
            ldi     high GWIN
            phi     rf
            glo     rf                  ; RC.0 = right - left (bytes)
            str     r2
            glo     r9
            sm
            plo     rc
            zp_at   r8, pen
            ldn     r8
            jz      hs_er
            xri     2
            jz      hs_inv
            ; PEN 1: OR
            glo     rc
            jnz     hs_d2
            ghi     ra                  ; one byte: both masks
            str     r2
            glo     ra
            and
            str     r2
            ldn     rf
            or
            str     rf
            rtn
hs_d2:      glo     ra                  ; the left byte, the right byte, then FF between
            str     r2
            ldn     rf
            or
            str     rf
            ghi     ra
            str     r2
            ldn     r9
            or
            str     r9
            dec     r9
            dec     rc
            glo     rc
            jz      hs_dn
            ldi     0ffh
            jmp     hs_full
            ; PEN 0: AND NOT
hs_er:      glo     rc
            jnz     hs_e2
            ghi     ra
            str     r2
            glo     ra
            and
            xri     0ffh
            str     r2
            ldn     rf
            and
            str     rf
            rtn
hs_e2:      glo     ra
            xri     0ffh
            str     r2
            ldn     rf
            and
            str     rf
            ghi     ra
            xri     0ffh
            str     r2
            ldn     r9
            and
            str     r9
            dec     r9
            dec     rc
            glo     rc
            jz      hs_dn
            ldi     0
            ; whole bytes: RC.0 of them (1-62) ending at R9, all = D: jump into the STXD block
hs_full:    plo     ra
            glo     rc                  ; entry = stxblock + 65 - n
            sdi     65
            adi     low stxblock
            plo     re
            ldi     high stxblock
            adci    0
            phi     re
            ldiw    rf, hs_jmp + 1
            ghi     re
            str     rf
            inc     rf
            glo     re
            str     rf
            glo     ra
            sex     r9
hs_jmp:     lbr     0                   ; (written above) the block ends with SEX 2 / RTN
            ; PEN 2: XOR
hs_inv:     glo     rc
            jnz     hs_i2
            ghi     ra
            str     r2
            glo     ra
            and
            str     r2
            ldn     rf
            xor
            str     rf
            rtn
hs_i2:      glo     ra
            str     r2
            ldn     rf
            xor
            str     rf
            ghi     ra
            str     r2
            ldn     r9
            xor
            str     r9
            dec     rc
hs_il:      glo     rc
            jz      hs_dn
            inc     rf
            ldn     rf
            xri     0ffh
            str     rf
            dec     rc
            jmp     hs_il
hs_dn:      rtn

; stxblock: SEX R9 and 64 STXD: stores D in the 64 bytes ending at R9 (entered at +1 + 64 - n for n bytes, with
; X = R9 already).  Then SEX 2 and return.
stxblock:   sex     r9
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            stxd
            sex     r2
            rtn

; vline: the pixels of column R7 from line R8 to line R9 (either order), clipped
vline:      ghi     r7
            ani     0feh
            jnz     vl_dn
            glo     r9                  ; order R8 <= R9 (signed)
            str     r2
            glo     r8
            sm
            ghi     r9
            xri     80h
            str     r2
            ghi     r8
            xri     80h
            smb
            jnf     vl_ord
            mov     rf, r8
            mov     r8, r9
            mov     r9, rf
vl_ord:     ghi     r9                  ; R9 < 0: nothing
            ani     80h
            jnz     vl_dn
            ghi     r8                  ; R8 < 0: from 0
            ani     80h
            jz      vl_t1
            ldi     0
            phi     r8
            plo     r8
vl_t1:      ghi     r8                  ; R8 below the screen: nothing
            jnz     vl_dn
            zp_at   rf, gheight
            ldn     rf
            jnz     vl_t2
            glo     r8
            smi     200
            jdf     vl_dn
vl_t2:      ghi     r9                  ; R9 below the screen: to the last line
            jnz     vl_clip
            zp_at   rf, gheight
            ldn     rf
            jnz     vl_go
            glo     r9
            smi     200
            jnf     vl_go
vl_clip:    zp_at   rf, gheight + 1
            ldn     rf
            smi     1
            plo     r9
            ldi     0
            phi     r9
vl_go:      mov     rc, r9              ; RC.0 = the last line
            call    pixaddr             ; RF = the byte, D = the mask
            plo     ra
            zp_at   r9, pen             ; RA.1 = the ALU operation for the pen, RA.0 = the mask (inverted to erase)
            ldn     r9
            jz      vl_er
            xri     2
            jz      vl_iv
            ldi     0f1h                ; OR
            jmp     vl_op
vl_er:      glo     ra
            xri     0ffh
            plo     ra
            ldi     0f2h                ; AND
            jmp     vl_op
vl_iv:      ldi     0f3h                ; XOR
vl_op:      plo     re
            ldiw    r9, vl_alu
            glo     re
            str     r9
vl_loop:    glo     r8
            str     r2
            out     YPORT
            dec     r2
            glo     ra
            str     r2
            ldn     rf
vl_alu:     or                          ; (written above: OR / AND / XOR)
            str     rf
            glo     r8
            str     r2
            glo     rc
            xor
            jz      vl_dn
            inc     r8
            jmp     vl_loop
vl_dn:      rtn

; set_gxy: the graphics cursor (where LINE x,y starts) = (R7, R8)
set_gxy:    zp_at   r9, gx
            ghi     r7
            str     r9
            inc     r9
            glo     r7
            str     r9
            inc     r9
            ghi     r8
            str     r9
            inc     r9
            glo     r8
            str     r9
            rtn

; ------------------------------------------------------------------ LINE
; LINE x1,y1,x2,y2  or  LINE x,y (from the graphics cursor)
st_line:    call    gfx_need
            ldi     2
            call    args_n
            ldn     tp
            xri     ','
            jnz     ln_two
            inc     tp
            ldi     low argv            ; x1,y1 given: move them to gx,gy
            call    ld_r7
            ldi     low argv + 2
            call    ld_r8
            call    set_gxy
            ldi     2
            call    args_n
ln_two:     zp_at   r9, gx              ; lx0..ly1 = gx, gy, argv0, argv1
            ldiw    rf, lx0
            ldi     8
            plo     rc
ln_cp:      lda     r9                  ; gx,gy,argv are laid out one after the other
            str     rf
            inc     rf
            dec     rc
            glo     rc
            jnz     ln_cp
            ldi     low argv            ; the cursor moves to the end
            call    ld_r7
            ldi     low argv + 2
            call    ld_r8
            call    set_gxy
            ; fall into line
; line: from (lx0, ly0) to (lx1, ly1)
line:       ldi     low ly0             ; horizontal: a span
            call    ld_r8
            ldi     low ly1
            call    ld_acc
            glo     r8
            str     r2
            glo     acc
            xor
            jnz     li_nh
            ghi     r8
            str     r2
            ghi     acc
            xor
            jnz     li_nh
            ldi     low lx0
            call    ld_r7
            ldi     low lx1
            call    ld_acc
            mov     r9, acc
            lbr     hspan
li_nh:      ldi     low lx0             ; vertical: vline
            call    ld_r7
            ldi     low lx1
            call    ld_acc
            glo     r7
            str     r2
            glo     acc
            xor
            jnz     li_diag
            ghi     r7
            str     r2
            ghi     acc
            xor
            jnz     li_diag
            ldi     low ly1
            call    ld_acc
            mov     r9, acc
            lbr     vline
li_diag:    push    tp                  ; TP is a work register in here
            ; dx = |x1 - x0|, dy = |y1 - y0|; R7 = x0 ... keep the endpoints in the zero page
            ldi     low lx1             ; RF = x1 - x0
            call    ld_acc
            mov     rf, acc
            ldi     low lx0
            call    ld_acc
            call    op_sub              ; ACC = x1 - x0
            mov     r7, acc
            ldi     low lddx
            call    st_r7
            ldi     low ly1
            call    ld_acc
            mov     rf, acc
            ldi     low ly0
            call    ld_acc
            call    op_sub              ; ACC = y1 - y0
            mov     r7, acc
            ldi     low lddy
            call    st_r7
            ; |dx| >= |dy| ?
            ldi     low lddx
            call    ld_r7
            call    abs_r7
            mov     rf, r7              ; RF = |dx|
            ldi     low lddy
            call    ld_r7
            call    abs_r7              ; R7 = |dy|
            glo     r7
            str     r2
            glo     rf
            sm
            ghi     r7
            str     r2
            ghi     rf
            smb
            lbnf    li_ymaj
            ; ---------------- x-major: go left to right (swap the ends if x1 < x0)
            ldi     low lddx
            call    ld_acc
            ghi     acc
            ani     80h
            jz      lx_noswap
            call    li_swap
lx_noswap:  ldi     low lddx             ; ACC = dx = |x1 - x0| (the major delta)
            call    ld_r7
            call    abs_r7
            mov     acc, r7
            ldi     low lddy             ; TP = |dy| (the minor delta); y step +1 or -1
            call    ld_r7
            ghi     r7
            ani     80h
            plo     rc                  ; RC.0 = 80h if y goes up (decreasing)
            call    abs_r7
            mov     tp, r7
            ldiw    r9, lx_ystep        ; patch INC R8 / DEC R8
            glo     rc
            jz      lx_down
            ldi     28h                 ; DEC R8
            jmp     lx_pst
lx_down:    ldi     18h                 ; INC R8
lx_pst:     str     r9
            call    line_pen            ; patch the pixel operation
            mov     rc, acc             ; RC = dx + 1 pixels
            inc     rc
            ghi     acc                 ; RA = err = dx / 2
            shr
            phi     ra
            glo     acc
            shrc
            plo     ra
            ldi     low lx0
            call    ld_r7               ; R7 = x
            ldi     low ly0
            call    ld_r8               ; R8 = y
            call    line_y              ; OUT 7 and RE.1 = y valid (0 = on the screen)
            ghi     r7                  ; RF, RE.0 = the byte and mask for x (if x < 0 they are set when x reaches 0)
            ani     80h
            jnz     lx_neg
            call    pixaddr
            plo     re
            jmp     lx_loop
lx_neg:     ldi     80h                 ; x < 0: x = 0's byte and mask, used from there
            plo     re
            ldiw    rf, GWIN
lx_loop:    ghi     r7                  ; x off the screen: only x moves
            ani     0feh
            jnz     lx_xoff
            ghi     re                  ; y off the screen: no pixel, but the byte and mask move with x
            jnz     lx_nopix
            glo     re
lx_xri:     xri     0                   ; patched: 00 (draw, invert) or FF (erase)
            str     r2
            ldn     rf
lx_op:      or                          ; patched: OR / AND / XOR
            str     rf
lx_nopix:   glo     re                  ; x + 1: the next bit, the next byte after bit 0
            shr
            plo     re
            jnz     lx_x1
            ldi     80h
            plo     re
            inc     rf
lx_x1:      inc     r7
            jmp     lx_err
lx_xoff:    inc     r7                  ; (x < 0 walks towards 0, where RF/RE.0 are ready)
lx_err:     glo     tp                  ; err -= dy
            str     r2
            glo     ra
            sm
            plo     ra
            ghi     tp
            str     r2
            ghi     ra
            smb
            phi     ra
            ani     80h
            jz      lx_next
            glo     acc                 ; err < 0: err += dx, y steps
            str     r2
            glo     ra
            add
            plo     ra
            ghi     acc
            str     r2
            ghi     ra
            adc
            phi     ra
lx_ystep:   inc     r8                  ; patched: INC R8 / DEC R8
            ghi     r8                  ; (inline: a SCRT call would destroy the mask in RE.0)
            jnz     lx_yoff
            zp_at   r9, gheight
            ldn     r9
            jnz     lx_yon
            glo     r8
            smi     200
            jdf     lx_yoff
lx_yon:     glo     r8                  ; y on the screen: the Y register
            str     r2
            out     YPORT
            dec     r2
            ldi     0
            phi     re
            jmp     lx_next
lx_yoff:    ldi     1
            phi     re
lx_next:    dec     rc
            glo     rc
            lbnz    lx_loop
            ghi     rc
            lbnz    lx_loop
            pop     tp
            rtn
            ; ---------------- y-major: go top to bottom (swap the ends if y1 < y0)
li_ymaj:    ldi     low lddy
            call    ld_acc
            ghi     acc
            ani     80h
            jz      ly_noswap
            call    li_swap
ly_noswap:  ldi     low lddy             ; ACC = |dy| (major)
            call    ld_r7
            call    abs_r7
            mov     acc, r7
            ldi     low lddx             ; TP = |dx| (minor); RC.1... x direction kept in the zero page
            call    ld_r7
            ghi     r7
            ani     80h
            plo     rc
            zp_at   r9, lsx
            glo     rc
            str     r9
            call    abs_r7
            mov     tp, r7
            call    line_pen
            ldiw    r9, ly_xri          ; the same patches for this loop
            ldiw    rf, lx_xri
            inc     rf
            inc     r9
            ldn     rf
            str     r9
            ldiw    r9, ly_op
            ldiw    rf, lx_op
            ldn     rf
            str     r9
            mov     rc, acc
            inc     rc
            ghi     acc
            shr
            phi     ra
            glo     acc
            shrc
            plo     ra
            ldi     low lx0
            call    ld_r7
            ldi     low ly0
            call    ld_r8
            call    line_x              ; RF, D = mask, RE.1 = x valid
            plo     re
ly_loop:    ghi     r8                  ; y on the screen?
            jnz     ly_skip
            zp_at   r9, gheight
            ldn     r9
            jnz     ly_yok
            glo     r8
            smi     200
            jdf     ly_skip
ly_yok:     ghi     re
            jnz     ly_skip
            glo     r8
            str     r2
            out     YPORT
            dec     r2
            glo     re
ly_xri:     xri     0
            str     r2
            ldn     rf
ly_op:      or
            str     rf
ly_skip:    inc     r8                  ; y + 1
            glo     tp                  ; err -= dx
            str     r2
            glo     ra
            sm
            plo     ra
            ghi     tp
            str     r2
            ghi     ra
            smb
            phi     ra
            ani     80h
            jz      ly_next
            glo     acc
            str     r2
            glo     ra
            add
            plo     ra
            ghi     acc
            str     r2
            ghi     ra
            adc
            phi     ra
            zp_at   r9, lsx             ; x steps left or right
            ldn     r9
            jnz     ly_left
            inc     r7
            jmp     ly_xnew
ly_left:    dec     r7
ly_xnew:    call    line_x
            plo     re
ly_next:    dec     rc
            glo     rc
            lbnz    ly_loop
            ghi     rc
            lbnz    ly_loop
            pop     tp
            rtn

; li_swap: exchange the ends (lx0,ly0) <-> (lx1,ly1) and negate ldx, ldy
li_swap:    ldiw    r9, lx0
            ldiw    rf, lx1
            ldi     4
            plo     rc
lsw_1:      ldn     r9
            plo     re
            ldn     rf
            str     r9
            glo     re
            str     rf
            inc     r9
            inc     rf
            dec     rc
            glo     rc
            jnz     lsw_1
            ldi     low lddx
            call    ld_r7
            call    neg_r7
            ldi     low lddx
            call    st_r7
            ldi     low lddy
            call    ld_r7
            call    neg_r7
            ldi     low lddy
            lbr     st_r7
neg_r7:     glo     r7
            sdi     0
            plo     r7
            ghi     r7
            sdbi    0
            phi     r7
            rtn
abs_r7:     ghi     r7
            ani     80h
            jnz     neg_r7
            rtn
; line_pen: patch lx_xri/lx_op for the pen (OR with mask / AND with ~mask / XOR with mask)
line_pen:   zp_at   r9, pen
            ldn     r9
            plo     re
            ldiw    r9, lx_xri + 1
            ldiw    rf, lx_op
            glo     re
            jz      lp_er
            xri     2
            jz      lp_inv
            ldi     0
            str     r9
            ldi     0f1h                ; OR
            str     rf
            rtn
lp_er:      ldi     0ffh
            str     r9
            ldi     0f2h                ; AND
            str     rf
            rtn
lp_inv:     ldi     0
            str     r9
            ldi     0f3h                ; XOR
            str     rf
            rtn
; line_y: OUT 7 = y and RE.1 = 0 if y (R8) is on the screen, else 1.  Keeps RE.0.
line_y:     ghi     r8
            jnz     lyy_off
            zp_at   r9, gheight
            ldn     r9
            jnz     lyy_on
            glo     r8
            smi     200
            jdf     lyy_off
lyy_on:     glo     r8
            str     r2
            out     YPORT
            dec     r2
            ldi     0
            phi     re
            rtn
lyy_off:    ldi     1
            phi     re
            rtn
; line_x: RF = byte and D = mask of x (R7), RE.1 = 0 if x is on the screen.  (Not RE.0: SCRT's return uses it.)
line_x:     ghi     r7
            ani     0feh
            jnz     lxx_off
            call    pixaddr
            str     r2
            ldi     0
            phi     re
            ldn     r2
            rtn
lxx_off:    ldi     1
            phi     re
            rtn

; ------------------------------------------------------------------ BOX
; BOX x1,y1,x2,y2[,F]
st_box:     call    gfx_need
            ldi     4
            call    args_n
            call    opt_fill
            ldi     low argv            ; x1 <= x2, y1 <= y2
            call    bx_ord
            ldi     low argv + 2
            call    bx_ord
            zp_at   r9, gfill
            ldn     r9
            jz      bx_line
            ; filled: a span for each line y1..y2, the lines limited to the screen
            ldi     low argv + 6        ; y2 < 0: nothing
            call    ld_r8
            ghi     r8
            ani     80h
            jnz     bx_dn
            call    clip_y2             ; y2 below the screen: the last line
            mov     r7, r8
            ldi     low argv + 6
            call    st_r7
            ldi     low argv + 2        ; y1 < 0: from 0
            call    ld_r8
            ghi     r8
            ani     80h
            jz      bx_y1
            ldi     0
            phi     r8
            plo     r8
bx_y1:      ldi     0                   ; y1 below the screen: nothing
            phi     r7
            plo     r7
            call    clip_xy
            jdf     bx_dn
bx_fl:      push    r8
            call    bx_h
            pop     r8
            ldi     low argv + 6        ; done at y2
            call    ld_acc
            call    eq_r8acc
            jdf     bx_dn
            inc     r8
            jmp     bx_fl
bx_line:    ldi     low argv + 2        ; top
            call    ld_r8
            call    bx_h
            ldi     low argv + 2        ; one line high: done
            call    ld_r8
            ldi     low argv + 6
            call    ld_acc
            call    eq_r8acc
            jdf     bx_dn
            ldi     low argv + 6        ; bottom
            call    ld_r8
            call    bx_h
            ldi     low argv + 2        ; two lines high: no sides
            call    ld_r8
            inc     r8
            ldi     low argv + 6
            call    ld_acc
            call    eq_r8acc
            jdf     bx_dn
            ldi     low argv            ; left side
            call    ld_r7
            call    bx_v
            ldi     low argv            ; one pixel wide: done
            call    ld_r8
            ldi     low argv + 4
            call    ld_acc
            call    eq_r8acc
            jdf     bx_dn
            ldi     low argv + 4        ; right side
            call    ld_r7
            lbr     bx_v
bx_dn:      rtn
; bx_h: hspan(x1, x2, R8)
bx_h:       ldi     low argv
            call    ld_r7
            ldi     low argv + 4
            call    ld_acc
            mov     r9, acc
            lbr     hspan
; bx_v: vline(R7, y1 + 1, y2 - 1)
bx_v:       ldi     low argv + 2
            call    ld_r8
            inc     r8
            ldi     low argv + 6
            call    ld_acc
            mov     r9, acc
            dec     r9
            lbr     vline
; bx_ord: the zero-page words at D and D+4 in order (signed)
bx_ord:     plo     rc
            call    ld_r7
            glo     rc
            adi     4
            call    ld_r8
            call    order78
            glo     rc
            call    st_r7
            mov     r7, r8
            glo     rc
            adi     4
            lbr     st_r7
; clip_y2: R8 (>= 0) = min(R8, the last line)
clip_y2:    ghi     r8
            jnz     cy2_cl
            zp_at   r9, gheight
            ldn     r9
            jnz     cy2_dn
            glo     r8
            smi     200
            jnf     cy2_dn
cy2_cl:     zp_at   r9, gheight + 1
            ldn     r9
            smi     1
            plo     r8
            ldi     0
            phi     r8
cy2_dn:     rtn
; order78: R7 <= R8 (signed), swapping them if needed
order78:    glo     r8
            str     r2
            glo     r7
            sm
            ghi     r8
            xri     80h
            str     r2
            ghi     r7
            xri     80h
            smb
            jnf     o78_dn
            mov     rf, r7
            mov     r7, r8
            mov     r8, rf
o78_dn:     rtn
; eq_r8acc: DF = 1 if R8 = ACC
eq_r8acc:   glo     r8
            str     r2
            glo     acc
            xor
            jnz     eq_no
            ghi     r8
            str     r2
            ghi     acc
            xor
            jnz     eq_no
            smi     0
            rtn
eq_no:      adi     0
            rtn

; ------------------------------------------------------------------ CIRCLE, ELLIPSE
; CIRCLE x,y,r[,F]    ELLIPSE x,y,rx,ry[,F]    (radii 0-1000)
st_circle:  call    gfx_need
            ldi     3
            call    args_n
            call    opt_fill
            ldi     low argv + 4        ; ry = rx = r
            call    ld_r7
            ldi     low argv + 6
            call    st_r7
            jmp     ellipse
st_ellipse: call    gfx_need
            ldi     4
            call    args_n
            call    opt_fill
            ; fall into ellipse
; ellipse: centre argv0, argv1; radii argv2 (x), argv3 (y); gfill.
; Row by row from the top (y = ry) to the middle (y = 0), each row's half width w is the largest x with
;   x^2 (ry^2 + ry) + y^2 (rx^2 + rx) < (rx^2 + rx)(ry^2 + ry)       (the ellipse of radii rx + 1/2, ry + 1/2)
; kept as err = A*B - 1 - x^2 B - y^2 A (A = rx^2 + rx, B = ry^2 + ry) in 32 bits with A(2y+1), B(2x+1) stepped by
; additions.  Filled: the span -w..w on rows cy-y and cy+y.  Outline: only the new pixels of each row (from the
; previous row's w + 1), so every pixel is touched once.
ellipse:    ldi     low argv + 4        ; radii 0-1000
            call    ld_r7
            call    rad_ok
            ldi     low argv + 6
            call    ld_r7
            call    rad_ok
            ldi     low argv + 4        ; a zero radius: a line
            call    ld_r7
            glo     r7
            jnz     el_rx
            ghi     r7
            jz      el_flat
el_rx:      ldi     low argv + 6
            call    ld_r7
            glo     r7
            jnz     el_go
            ghi     r7
            jnz     el_go
el_flat:    ldi     low argv            ; a line: (cx - rx, cy - ry) - (cx + rx, cy + ry)
            call    ld_r7
            ldi     low argv + 4
            call    ld_acc
            ldi     low lx0
            call    el_pm
            ldi     low argv + 2
            call    ld_r7
            ldi     low argv + 6
            call    ld_acc
            ldi     low ly0
            call    el_pm
            lbr     line
; el_pm: zero-page words at D = R7 - ACC and at D + 4 = R7 + ACC
el_pm:      plo     rc
            push    acc
            mov     rf, r7
            call    op_sub
            mov     r7, acc
            glo     rc
            call    st_r7
            pop     acc
            call    op_add
            mov     r7, acc
            glo     rc
            adi     4
            lbr     st_r7
el_go:      zp_at   r9, eone + 3        ; the constant 1
            ldi     1
            str     r9
            ; A = rx (rx + 1) -> eA;  B = ry (ry + 1) -> eB
            ldi     low argv + 4
            call    ld_r7
            mov     rf, r7
            mov     acc, r7
            inc     acc
            call    umul32
            ldi     low eA
            call    st32
            ldi     low argv + 6
            call    ld_r7
            mov     rf, r7
            mov     acc, r7
            inc     acc
            call    umul32
            ldi     low eB
            call    st32
            ; P = A * ry -> eerr (shift and add over ry's bits; eT = A shifted)
            ldiw    r9, eerr
            call    zero32
            ldiw    r9, eT
            ldiw    rf, eA
            call    copy32
            ldi     low argv + 6
            call    ld_acc
ep_loop:    glo     acc
            jnz     ep_go
            ghi     acc
            jz      ep_dn
ep_go:      ghi     acc
            shr
            phi     acc
            glo     acc
            shrc
            plo     acc
            jnf     ep_sh
            ldiw    r9, eerr + 3
            ldiw    rf, eT + 3
            call    add32
ep_sh:      ldiw    r9, eT + 3
            call    shl32
            jmp     ep_loop
ep_dn:      ldiw    r9, eAy        ; Ay = 2P - A (the step for the row y = ry - 1)
            ldiw    rf, eerr
            call    copy32
            ldiw    r9, eAy + 3
            call    shl32
            ldiw    r9, eAy + 3
            ldiw    rf, eA + 3
            call    sub32
            ldiw    r9, eerr + 3   ; err = P - 1
            ldiw    rf, eone + 3
            call    sub32
            ldiw    r9, eA2        ; A2 = 2A, B2 = 2B, Bx = B
            ldiw    rf, eA
            call    copy32
            ldiw    r9, eA2 + 3
            call    shl32
            ldiw    r9, eB2
            ldiw    rf, eB
            call    copy32
            ldiw    r9, eB2 + 3
            call    shl32
            ldiw    r9, eBx
            ldiw    rf, eB
            call    copy32
            ldi     0                   ; w = 0, wprev = -1, y = ry
            phi     r7
            plo     r7
            ldi     low ew
            call    st_r7
            ldi     0ffh
            phi     r7
            plo     r7
            ldi     low ewp
            call    st_r7
            ldi     low argv + 6
            call    ld_r7
            ldi     low ey
            call    st_r7
            jmp     el_ext              ; the first row needs no row step
el_row:     ldi     high zp             ; err += Ay; Ay -= A2 (32 bits, in line)
            phi     rf
            phi     r9
            ldi     low eerr + 3
            plo     r9
            ldi     low eAy + 3
            plo     rf
            sex     rf
            ldn     r9
            add
            str     r9
            dec     r9
            dec     rf
            ldn     r9
            adc
            str     r9
            dec     r9
            dec     rf
            ldn     r9
            adc
            str     r9
            dec     r9
            dec     rf
            ldn     r9
            adc
            str     r9
            ldi     low eAy + 3
            plo     r9
            ldi     low eA2 + 3
            plo     rf
            ldn     r9
            sm
            str     r9
            dec     r9
            dec     rf
            ldn     r9
            smb
            str     r9
            dec     r9
            dec     rf
            ldn     r9
            smb
            str     r9
            dec     r9
            dec     rf
            ldn     r9
            smb
            str     r9
            sex     r2
            ; widen: while err >= Bx: err -= Bx, Bx += B2, w + 1
el_ext:     ldi     high zp
            phi     rf
            phi     r9
            ldi     low ew
            plo     r9
            lda     r9
            phi     r7
            ldn     r9
            plo     r7
el_xl:      ldi     low eerr + 3        ; t = err - Bx (RA.0 RC.1 RC.0 and D)
            plo     rf
            ldi     low eBx + 3
            plo     r9
            sex     r9
            ldn     rf
            sm
            plo     rc
            dec     rf
            dec     r9
            ldn     rf
            smb
            phi     rc
            dec     rf
            dec     r9
            ldn     rf
            smb
            plo     ra
            dec     rf
            dec     r9
            ldn     rf
            smb
            sex     r2
            jnf     el_xdn              ; err < Bx
            str     rf                  ; err = t
            inc     rf
            glo     ra
            str     rf
            inc     rf
            ghi     rc
            str     rf
            inc     rf
            glo     rc
            str     rf
            ldi     low eBx + 3         ; Bx += B2
            plo     r9
            ldi     low eB2 + 3
            plo     rf
            sex     rf
            ldn     r9
            add
            str     r9
            dec     r9
            dec     rf
            ldn     r9
            adc
            str     r9
            dec     r9
            dec     rf
            ldn     r9
            adc
            str     r9
            dec     r9
            dec     rf
            ldn     r9
            adc
            str     r9
            sex     r2
            inc     r7
            jmp     el_xl
el_xdn:     ldi     low ew              ; w = R7 (R9.1 is the zero page)
            plo     r9
            ghi     r7
            str     r9
            inc     r9
            glo     r7
            str     r9
            ; the spans: esp = cx - w .. cx + w (fill, or a = 0); else cx - w .. cx - a and cx + a .. cx + w
            ldi     low argv            ; RF = cx
            plo     r9
            lda     r9
            phi     rf
            ldn     r9
            plo     rf
            ldi     low esp             ; esp+0 = cx - w
            plo     r9
            glo     r7
            str     r2
            glo     rf
            sm
            plo     re
            ghi     r7
            str     r2
            ghi     rf
            smb
            str     r9
            inc     r9
            glo     re
            str     r9
            ldi     low esp + 6         ; esp+6 = cx + w
            plo     r9
            glo     r7
            str     r2
            glo     rf
            add
            plo     re
            ghi     r7
            str     r2
            ghi     rf
            adc
            str     r9
            inc     r9
            glo     re
            str     r9
            ldi     0                   ; ACC = a (0 = one span)
            phi     acc
            plo     acc
            ldi     low gfill
            plo     r9
            ldn     r9
            jnz     el_a
            ldi     low ewp             ; a = min(wprev + 1, w)
            plo     r9
            lda     r9
            phi     acc
            ldn     r9
            plo     acc
            inc     acc
            glo     acc
            str     r2
            glo     r7
            sm
            ghi     acc
            xri     80h
            str     r2
            ghi     r7
            xri     80h
            smb
            jdf     el_a
            mov     acc, r7
el_a:       ldi     low esp + 2         ; one span: esp+2 = esp+6 (cx + w)
            plo     r9
            glo     acc
            jnz     el_two
            ghi     acc
            jnz     el_two
            ldi     low esp + 6
            plo     re
            ldi     2                   ; RC.0 = spans
            plo     rc
            jmp     el_cp
el_two:     glo     acc                 ; esp+2 = cx - a, esp+4 = cx + a
            str     r2
            glo     rf
            sm
            plo     re
            ghi     acc
            str     r2
            ghi     rf
            smb
            str     r9
            inc     r9
            glo     re
            str     r9
            inc     r9
            glo     acc
            str     r2
            glo     rf
            add
            plo     re
            ghi     acc
            str     r2
            ghi     rf
            adc
            str     r9
            inc     r9
            glo     re
            str     r9
            ldi     4
            plo     rc
            jmp     el_rowsd
el_cp:      ldi     low esp + 7         ; (one span) esp+2..3 = esp+6..7
            plo     r9
            ldn     r9
            plo     re
            dec     r9
            ldn     r9
            phi     re
            ldi     low esp + 2
            plo     r9
            ghi     re
            str     r9
            inc     r9
            glo     re
            str     r9
el_rowsd:   glo     rc                  ; spans: 2 = one (esp+0..3), 4 = two (esp+0..7)
            stxd
            ldi     low ey + 1          ; erow = cy - y
            plo     r9
            ldn     r9
            str     r2
            ldi     low argv + 3
            plo     r9
            ldn     r9
            sm
            plo     re
            ldi     low ey
            plo     r9
            ldn     r9
            str     r2
            ldi     low argv + 2
            plo     r9
            ldn     r9
            smb
            plo     rf
            ldi     low erow
            plo     r9
            glo     rf
            str     r9
            inc     r9
            glo     re
            str     r9
            ldi     low esp
            call    el_hsp
            peekc
            xri     2
            jz      el_r2
            ldi     low esp + 4
            call    el_hsp
el_r2:      ldi     high zp             ; y = 0: one row only
            phi     r9
            ldi     low ey
            plo     r9
            lda     r9
            str     r2
            ldn     r9
            or
            jz      el_rdn
            ldn     r9                  ; erow = cy + y
            str     r2
            ldi     low argv + 3
            plo     r9
            ldn     r9
            add
            plo     re
            ldi     low ey
            plo     r9
            ldn     r9
            str     r2
            ldi     low argv + 2
            plo     r9
            ldn     r9
            adc
            plo     rf
            ldi     low erow
            plo     r9
            glo     rf
            str     r9
            inc     r9
            glo     re
            str     r9
            ldi     low esp
            call    el_hsp
            peekc
            xri     2
            jz      el_rdn
            ldi     low esp + 4
            call    el_hsp
el_rdn:     irx                         ; drop the span count
el_nextrow: ldi     high zp             ; wprev = w; y - 1, done after y = 0
            phi     r9
            ldi     low ew
            plo     r9
            lda     r9
            plo     re
            ldn     r9
            plo     rf
            ldi     low ewp
            plo     r9
            glo     re
            str     r9
            inc     r9
            glo     rf
            str     r9
            ldi     low ey + 1
            plo     r9
            ldn     r9
            jnz     el_ydn
            dec     r9
            ldn     r9
            inc     r9
            jz      el_dn
el_ydn:     ldn     r9                  ; y.lo - 1
            smi     1
            str     r9
            dec     r9
            ldn     r9
            smbi    0
            str     r9
            jmp     el_row
el_dn:      rtn
; el_hsp: D = the zero-page offset of a span (x left, x right): hspan_ord on row erow
el_hsp:     plo     rf
            ldi     high zp
            phi     rf
            lda     rf
            phi     r7
            lda     rf
            plo     r7
            lda     rf
            phi     r9
            ldn     rf
            plo     r9
            ldi     low erow
            plo     rf
            lda     rf
            phi     r8
            ldn     rf
            plo     r8
            lbr     hspan_ord
rad_ok:     ghi     r7                  ; R7 must be 0-1000
            ani     80h
            lbnz    value_err
            glo     r7
            smi     low 1001
            ghi     r7
            smbi    high 1001
            lbdf    value_err
            rtn

; ------------------------------------------------------------------ 32-bit helpers (big-endian in the zero page)
; st32: zero-page dword at offset D = RA:RC
st32:       plo     r9
            ldi     high zp
            phi     r9
            ghi     ra
            str     r9
            inc     r9
            glo     ra
            str     r9
            inc     r9
            ghi     rc
            str     r9
            inc     r9
            glo     rc
            str     r9
            rtn
zero32:     ldi     0                   ; [R9] = 0 (R9 -> the first byte)
            str     r9
            inc     r9
            str     r9
            inc     r9
            str     r9
            inc     r9
            str     r9
            rtn
copy32:     lda     rf                  ; [R9] = [RF] (both -> the first byte)
            str     r9
            inc     r9
            lda     rf
            str     r9
            inc     r9
            lda     rf
            str     r9
            inc     r9
            ldn     rf
            str     r9
            rtn
add32:      sex     rf                  ; [R9] += [RF] (both -> the last byte)
            ldn     r9
            add
            str     r9
            dec     r9
            dec     rf
            ldn     r9
            adc
            str     r9
            dec     r9
            dec     rf
            ldn     r9
            adc
            str     r9
            dec     r9
            dec     rf
            ldn     r9
            adc
            str     r9
            sex     r2
            rtn
sub32:      sex     rf                  ; [R9] -= [RF] (both -> the last byte)
            ldn     r9
            sm
            str     r9
            dec     r9
            dec     rf
            ldn     r9
            smb
            str     r9
            dec     r9
            dec     rf
            ldn     r9
            smb
            str     r9
            dec     r9
            dec     rf
            ldn     r9
            smb
            str     r9
            sex     r2
            rtn
shl32:      ldn     r9                  ; [R9] <<= 1 (R9 -> the last byte)
            shl
            str     r9
            dec     r9
            ldn     r9
            shlc
            str     r9
            dec     r9
            ldn     r9
            shlc
            str     r9
            dec     r9
            ldn     r9
            shlc
            str     r9
            rtn
