; vgdemo for Elf/OS v5 on System-5 with VIDEO-G: a small demo of the two ways a program puts something on VIDEO-G's
; screen: writing characters to the text RAM (the TEXT board) and writing dots to the graphics RAM (the GFX board).
; Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-20 (Ken: "a small demo showing writing to
; text and writing to graphics")
;
; What it does, in this order:
;   1. TEXT. It stores spaces over rows 0-21 of the text RAM (the rows above the prompt's), then copies three lines
;      of words into it. A character stored at 7000 + 64 x row + column is on the screen at once: there is nothing
;      else to do.
;   2. GRAPHICS ON. It writes 02 to the control register (7804): bit 1 is GFX-ON, and bit 0 (TEXT-OFF) stays 0, so
;      the monitor shows the text and the graphics together. The graphics RAM holds whatever it powered up with,
;      so the first thing seen is a screen of stray dots.
;   3. GRAPHICS. For each of the 200 lines: it writes the line's number to the Y register (7806), and the 64 bytes
;      at 7C00-7C3F are then that line's 512 dots, bit 7 of each byte the leftmost. It clears the line, and inside
;      the box draws the box's top or bottom (bytes of FF), or its two edges (one dot each) and two dots of the
;      diagonal. The diagonal's dots are ORed into the byte: read 7C00 + x/8, OR the mask, write it back.
;   4. It waits for a key (status register 7804, bit 0 = KEY-READY; the key is read at 7802), turns the graphics
;      off again (control = 00) and goes back to Elf/OS. The graphics RAM keeps the picture.
; The words in the middle of the box are text, the box and the line across them are graphics: where they cross,
; the two are ORed by the card (the control register's XOR bit would make them cancel instead).
;
; It asks the card what it is first (status bits 7-6 = 10 on VIDEO-G, bit 5 = GFX fitted) and does nothing on any
; other video card: on the 6845 card these addresses are the 6845's own registers.
;
; Build: python3 software/elfos-v5/build.py  (tools/asm1802.py; it writes vgdemo, the Elf/OS program, and vgdemo.lst)

textram:    equ     07000h          ; the text RAM: 64 characters a row, 25 rows
key:        equ     07802h          ; the key (reading it clears KEY-READY)
ctrl:       equ     07804h          ; control (write) and status (read)
yreg:       equ     07806h          ; the Y register (write): the line the window shows
window:     equ     07c00h          ; the graphics window: the 64 bytes of line Y

lines:      equ     200             ; 512 x 200 on an NTSC monitor
top:        equ     36              ; the box: lines 36-163 ...
height:     equ     128
left:       equ     16              ; ... and bytes 16-47 of each line (dots 128-383)
right:      equ     47

text1:      equ     textram+(64*2)+4    ; row 2, column 4
text2:      equ     textram+(64*12)+23  ; row 12, column 23: inside the box
text3:      equ     textram+(64*21)+4   ; row 21, column 4: under the box, above the prompt's rows
textend:    equ     textram+(64*22)     ; one past row 21

f_msg:      equ     0ff09h          ; BIOS: type the text at RF

            org     2000h
            br      start
; What `ver /bin/vgdemo` shows (laid out as in Mike Riley's programs, as cls has it)
            db      0c0h + 11, 20
            dw      2026
            db      12, 0, 0
            dw      1
            db      'System-5 VIDEO-G demo', 0
dots:       db      0c0h, 030h, 00ch, 003h  ; two dots of the diagonal, for line mod 4 = 0, 1, 2, 3

start:      ldi     high ctrl       ; R8 at the status register (7804)
            phi     r8
            ldi     low ctrl
            plo     r8
            ldn     r8              ; is this VIDEO-G (bits 7-6 = 10) with its GFX board (bit 5)?
            ani     0e0h
            xri     0a0h
            bz      text
            ldi     high nocard     ; no: say so, and leave the card alone
            phi     rf
            ldi     low nocard
            plo     rf
            sep     r4
            dw      f_msg
            ldi     0
            sep     r5
;
; 1. TEXT: spaces over rows 0-21, then three lines of words, all stored in the text RAM
;
text:       ldi     high textram    ; RD at the first character of the screen
            phi     rd
            ldi     low textram
            plo     rd
tclear:     ldi     ' '
            str     rd
            inc     rd
            glo     rd              ; up to the end of row 21 (7580)
            xri     low textend
            bnz     tclear
            ghi     rd
            xri     high textend
            bnz     tclear
            ldi     high words      ; RF at the words, RD at the place in the text RAM
            phi     rf
            ldi     low words
            plo     rf
            ldi     high text1
            phi     rd
            ldi     low text1
            plo     rd
            sep     r4
            dw      tcopy
            ldi     high text2
            phi     rd
            ldi     low text2
            plo     rd
            sep     r4
            dw      tcopy
            ldi     high text3
            phi     rd
            ldi     low text3
            plo     rd
            sep     r4
            dw      tcopy
;
; 2. GRAPHICS ON: control register bit 1 (text stays on)
;
            ldi     02h
            str     r8
;
; 3. GRAPHICS: line by line. R7.0 = the line, R8 at the Y register, R9 at a byte of the window
;
            ldi     low yreg
            plo     r8
            ldi     0
            plo     r7
gline:      glo     r7              ; the Y register = this line: the window is now this line's 64 bytes
            str     r8
            ldi     high window
            phi     r9
            ldi     low window
            plo     r9
gclear:     ldi     0               ; clear the line
            str     r9
            inc     r9
            glo     r9
            xri     40h
            bnz     gclear
            glo     r7              ; RA.0 = the line counted from the box's top
            smi     top
            bnf     gnext           ; above the box
            plo     ra
            smi     height
            bdf     gnext           ; below it
            glo     ra
            bz      gfull           ; the box's top line
            xri     height-1
            bz      gfull           ; and its bottom line
            ldi     left            ; a line inside: the left edge, the leftmost dot of byte 16
            plo     r9
            ldi     80h
            str     r9
            ldi     right           ; the right edge, the rightmost dot of byte 47
            plo     r9
            ldi     01h
            str     r9
            glo     ra              ; the diagonal, two dots a line: the byte is 16 + line / 4 ...
            shr
            shr
            adi     left
            plo     r9
            glo     ra              ; ... and the dots are dots[line mod 4]
            ani     03h
            adi     low dots
            plo     rf
            ldi     high dots
            phi     rf
            ldn     rf
            str     r2              ; OR them into the byte: read it, OR, write it back
            ldn     r9
            or
            str     r9
            br      gnext
gfull:      ldi     left            ; the top or the bottom: bytes 16-47 all dots
            plo     r9
gfill:      ldi     0ffh
            str     r9
            inc     r9
            glo     r9
            xri     right+1
            bnz     gfill
gnext:      inc     r7
            glo     r7
            xri     lines
            bnz     gline
;
; 4. Wait for a key, turn the graphics off, back to Elf/OS
;
            ldi     low ctrl
            plo     r8
kwait:      ldn     r8              ; KEY-READY (status bit 0)?
            shr
            bnf     kwait
            ldi     low key         ; read the key: that clears KEY-READY
            plo     r8
            ldn     r8
            ldi     low ctrl
            plo     r8
            ldi     00h             ; control = 00: text on, graphics off
            str     r8
            ldi     0               ; the program's return value: no error
            sep     r5
;
; tcopy: the text at RF, up to its 00, into the text RAM at RD. RF is left after the 00, at the next text.
; (RD, not RE: a call through SCRT uses RE.0.)
tcopy:      lda     rf
            bz      tdone
            str     rd
            inc     rd
            br      tcopy
tdone:      sep     r5

words:      db      'TEXT: these words are characters in the text RAM (7000).', 0
            db      'TEXT OVER GRAPHICS', 0
            db      'GRAPHICS: the box and the line are dots. Any key ends.', 0
nocard:     db      'vgdemo needs the VIDEO-G card with its GFX board', 13, 10, 0
