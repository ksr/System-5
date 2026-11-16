; GBASIC - files on the ELF/OS disk: SAVE, LOAD, FILES (DIR), KILL.
;
; Programs are saved as plain text, exactly as LIST shows them, each line ending in CR LF, so a saved program can
; be TYPEd, copied or edited; LOAD reads any such text (CR, LF or CR LF line ends; lines without a number are
; skipped) and tokenizes it line by line, as if typed.

FDSIZE      equ     19                  ; an ELF/OS file descriptor: offset 4, dta 2, eof 2, flags 1, dir 4+2, sector 4
LOADBUF     equ     MEMTOP - FDSIZE - 512   ; LOAD's descriptor and sector buffer, at the top of the program area
LOADDTA     equ     LOADBUF + FDSIZE
SAVENEED    equ     FDSIZE + 512 + 300  ; SAVE's buffers, above the arrays

; get_name: TP at "name" -> namebuf (0-terminated, 1-19 characters)
get_name:   call    expect
            db      '"'
            ldiw    r9, namebuf
            ldi     0
            plo     rc
gn_loop:    ldn     tp
            jz      gn_end
            lda     tp
            xri     '"'
            jz      gn_end
            glo     rc
            smi     19
            lbdf    value_err
            dec     tp
            lda     tp
            str     r9
            inc     r9
            inc     rc
            jmp     gn_loop
gn_end:     ldi     0
            str     r9
            glo     rc
            lbz     value_err
            rtn

; fd_init: RD = descriptor, RF = its 512-byte sector buffer: an unused descriptor
fd_init:    push    rd
            ldi     FDSIZE
            plo     rc
fi_z:       ldi     0
            str     rd
            inc     rd
            dec     rc
            glo     rc
            jnz     fi_z
            pop     rd
            inc     rd                  ; the dta
            inc     rd
            inc     rd
            inc     rd
            ghi     rf
            str     rd
            inc     rd
            glo     rf
            str     rd
            glo     rd                  ; the current sector = FFFFFFFF (none loaded)
            adi     FDSIZE - 4 - 5
            plo     rd
            ghi     rd
            adci    0
            phi     rd
            ldi     0ffh
            str     rd
            inc     rd
            str     rd
            inc     rd
            str     rd
            inc     rd
            str     rd
            glo     rd                  ; back to the start
            smi     FDSIZE - 1
            plo     rd
            ghi     rd
            smbi    0
            phi     rd
            rtn

; file_abort: close a file left open (an error during SAVE or LOAD)
file_abort: zp_at   r9, fileopen
            ldn     r9
            jz      fa_dn
            ldi     0
            str     r9
            zp_at   r9, memlim          ; and LOAD's memory limit back
            ldi     high MEMTOP
            str     r9
            inc     r9
            ldi     low MEMTOP
            str     r9
            zp_at   r9, loading
            ldi     0
            str     r9
            zp_at   r9, fdptr
            lda     r9
            phi     rd
            ldn     r9
            plo     rd
            call    o_close
fa_dn:      rtn
; file_err: close the file, then "File error"
file_err:   error   E_FILE

; ------------------------------------------------------------------ SAVE "name"
st_save:    call    get_name
            call    fre_value           ; room for the buffers above the arrays?
            glo     acc
            smi     low SAVENEED
            ghi     acc
            smbi    high SAVENEED
            lbnf    mem_err
            push    tp
            zp_at   r9, arrend          ; RD = descriptor at arrend, RF = its buffer
            lda     r9
            phi     rd
            ldn     r9
            plo     rd
            glo     rd
            adi     FDSIZE
            plo     rf
            ghi     rd
            adci    0
            phi     rf
            call    fd_init
            ldiw    rf, namebuf
            ldi     3                   ; create, truncate
            plo     r7
            call    o_open
            lbdf    file_err
            call    file_opened         ; fdptr = RD, fileopen = 1
            ldiw    r9, prog
sv_line:    call    nextline            ; R9 = the next line (0 = the end)
            jz      sv_end
            zp_at   r8, outmode         ; LIST it into the buffer above the sector buffer
            ldi     1
            str     r8
            call    sv_bufaddr          ; RF = the text buffer
            zp_at   r8, outptr
            ghi     rf
            str     r8
            inc     r8
            glo     rf
            str     r8
            call    listline
            zp_at   r8, outmode
            ldi     0
            str     r8
            call    sv_bufaddr          ; RC = outptr - buffer
            zp_at   r8, outptr + 1
            ldn     r8
            str     r2
            glo     rf
            sd
            plo     rc
            dec     r8
            ldn     r8
            str     r2
            ghi     rf
            sdb
            phi     rc
            push    r9
            zp_at   r9, fdptr
            lda     r9
            phi     rd
            ldn     r9
            plo     rd
            call    o_write
            pop     r9
            lbdf    file_err
            jmp     sv_line
sv_end:     zp_at   r9, fdptr
            lda     r9
            phi     rd
            ldn     r9
            plo     rd
            call    o_close
            zp_at   r9, fileopen
            ldi     0
            str     r9
            pop     tp
            rtn
; sv_bufaddr: RF = arrend + FDSIZE + 512 (SAVE's line text)
sv_bufaddr: zp_at   r8, arrend
            lda     r8
            phi     rf
            ldn     r8
            adi     low (FDSIZE + 512)
            plo     rf
            ghi     rf
            adci    high (FDSIZE + 512)
            phi     rf
            rtn
; file_opened: fdptr = RD, fileopen = 1
file_opened: zp_at  r9, fdptr
            ghi     rd
            str     r9
            inc     r9
            glo     rd
            str     r9
            zp_at   r9, fileopen
            ldi     1
            str     r9
            rtn

; ------------------------------------------------------------------ LOAD "name"
st_load:    call    get_name
            call    do_load
            lbr     ready
; load_named: RF -> a name ending in a space or 0 (the command line) -> namebuf, then do_load
load_named: ldiw    r9, namebuf
            ldi     0
            plo     rc
lnm_loop:   ldn     rf
            jz      lnm_end
            xri     ' '
            jz      lnm_end
            glo     rc
            smi     19
            jdf     lnm_end
            lda     rf
            str     r9
            inc     r9
            inc     rc
            jmp     lnm_loop
lnm_end:    ldi     0
            str     r9
            ; fall into do_load
; do_load: namebuf -> the program (the old one is replaced; if the file is not there, it is kept)
do_load:    ldiw    rd, LOADBUF
            ldiw    rf, LOADDTA
            call    fd_init
            ldiw    rf, namebuf
            ldi     0
            plo     r7
            call    o_open
            jnf     ld_ok
            error   E_NOTFOUND
ld_ok:      call    file_opened
            call    do_new
            zp_at   r9, memlim          ; the program must stay below the buffers
            ldi     high LOADBUF
            str     r9
            inc     r9
            ldi     low LOADBUF
            str     r9
            zp_at   r9, loading
            ldi     1
            str     r9
            zp_at   r9, lastnum
            ldi     0
            str     r9
            inc     r9
            str     r9
            zp_at   r9, lcount
            ldi     0
            str     r9
ld_read:    ldiw    rd, LOADBUF         ; 128 bytes at a time
            ldiw    rf, LOADRB
            ldiw    rc, 128
            call    o_read
            lbdf    file_err
            glo     rc
            jz      ld_eof
            ldiw    ra, LOADRB
ld_byte:    lda     ra
            plo     re
            xri     13
            jz      ld_eol
            glo     re
            xri     10
            jz      ld_eol
            glo     re
            xri     9                   ; tab: a space
            jnz     ld_nt
            ldi     ' '
            plo     re
ld_nt:      glo     re
            smi     ' '
            jnf     ld_next             ; other control characters: dropped
            glo     re
            ani     80h                 ; and bytes 80h up
            jnz     ld_next
            zp_at   r9, lcount
            ldn     r9
            smi     LINEMAX
            jdf     ld_next             ; too long: the rest is dropped
            ldn     r9
            adi     1
            str     r9
            adi     low linebuf - 1     ; linebuf + count (linebuf does not cross a page)
            plo     r9
            ldi     high linebuf
            phi     r9
            glo     re
            str     r9
            jmp     ld_next
ld_eol:     push    ra
            push    rc
            call    ld_line
            pop     rc
            pop     ra
ld_next:    dec     rc
            glo     rc
            jnz     ld_byte
            jmp     ld_read
ld_eof:     call    ld_line             ; a last line without an end
            ldiw    rd, LOADBUF
            call    o_close
            zp_at   r9, fileopen
            ldi     0
            str     r9
            zp_at   r9, loading
            ldi     0
            str     r9
            zp_at   r9, memlim
            ldi     high MEMTOP
            str     r9
            inc     r9
            ldi     low MEMTOP
            str     r9
            lbr     clear_run
; ld_line: the collected line (if any) -> tokenized and put in the program
ld_line:    zp_at   r9, lcount
            ldn     r9
            jz      ldl_dn
            plo     re
            ldi     0
            str     r9
            glo     re
            adi     low linebuf
            plo     r9
            ldi     high linebuf
            phi     r9
            ldi     0
            str     r9
            call    tokenize
            jnf     ldl_dn              ; no line number: skipped
            call    edit_line
ldl_dn:     rtn

; ------------------------------------------------------------------ FILES (or DIR) ["path"]
st_files:   ldiw    r9, namebuf
            ldi     0
            str     r9
            ldn     tp
            xri     '"'
            jnz     fl_open
            call    get_name
fl_open:    push    tp
            ldiw    rf, namebuf
            call    o_opendir           ; RD = the directory
            lbdf    file_err
            ldi     0
            plo     r8
            stxd                        ; names on this line
fl_ent:     zp_at   r9, fdptr           ; (keep RD)
            ghi     rd
            str     r9
            inc     r9
            glo     rd
            str     r9
            ldiw    rf, direntry
            ldiw    rc, 32
            call    o_read
            lbdf    fl_dn
            glo     rc
            smi     32
            jnf     fl_dn
            ldiw    r9, direntry        ; a free entry: the first lump is 0
            lda     r9
            str     r2
            lda     r9
            or
            str     r2
            lda     r9
            or
            str     r2
            ldn     r9
            or
            jz      fl_next
            ldiw    rf, direntry + 12   ; the name
            ldi     0
            plo     rc
fl_name:    lda     rf
            jz      fl_nend
            call    putc
            inc     rc
            jmp     fl_name
fl_nend:    ldiw    r9, direntry + 6    ; a directory: "/"
            ldn     r9
            ani     1
            jz      fl_pad
            ldi     '/'
            call    putc
            inc     rc
fl_pad:     glo     rc                  ; to 16 columns
            smi     16
            jdf     fl_cnt
            call    space
            inc     rc
            jmp     fl_pad
fl_cnt:     irx                         ; four names a line
            ldx
            adi     1
            stxd
            smi     4
            jnf     fl_next
            irx
            ldi     0
            stxd
            call    newline
fl_next:    zp_at   r9, fdptr
            lda     r9
            phi     rd
            ldn     r9
            plo     rd
            jmp     fl_ent
fl_dn:      irx
            ldx
            jz      fl_dn2
            call    newline
fl_dn2:     pop     tp
            rtn

; ------------------------------------------------------------------ KILL "name"
st_kill:    call    get_name
            push    tp
            ldiw    rf, namebuf
            call    o_delete
            pop     tp
            lbdf    kill_nf
            rtn
kill_nf:    error   E_NOTFOUND
