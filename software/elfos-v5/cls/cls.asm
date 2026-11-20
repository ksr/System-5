; cls for Elf/OS v5 on System-5: clears the screen of the 6845 card (16 lines) or of VIDEO-G (25 lines).
; Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-14; both cards 2026-11-20
;
; Mike Riley's cls types ESC [ H ESC [ 2 J, the codes that clear an ANSI terminal. HBIOS's screen is not one: it
; showed "[H[2J" and cleared nothing. This program writes spaces over the screen itself.
;
; HBIOS types on the bottom line of the screen and scrolls the rest up, so there is no "home". The cursor is left
; where it is, at the start of the bottom line, and the next text appears there.
; The screen starts at 7000, 64 characters a line. How many lines it has depends on the video card: 16 on the 6845
; card (7000-73FF), 25 on VIDEO-G (7000-763F). HBIOS keeps its cursor position, an address in that RAM, in the last
; two bytes of the video RAM (77FE high, 77FF low), and when cls runs the cursor is on the bottom line: 73C0 on the
; 6845 card, 7600 on VIDEO-G. So this program clears from 7000 to the end of the line the cursor is on, and is the
; same program for both cards (until 2026-11-20 it cleared 7000-73FF, which left VIDEO-G's lines 16-24 as they were).
; If those two bytes do not hold an address a cursor can have (below 7000, or in the last line, 77C0-77FF, where
; the two bytes themselves are), it clears the 6845 card's 16 lines. The two bytes are never touched.
;
; Build: python3 software/elfos-v5/build.py  (tools/asm1802.py; it writes cls, the Elf/OS program, and cls.lst)

screen:     equ     07000h          ; the video RAM: 64 characters a line
cursor:     equ     077feh          ; HBIOS's cursor position: the high byte, then the low byte
scrend16:   equ     07400h          ; one past the 6845 card's 16 lines

            org     2000h
            br      start
; What `ver /bin/cls` shows, laid out as in Mike Riley's programs: the month (with C0h added, as his have it), the
; day, the year, the hour, minute and second, a build number, and a text.
            db      0c0h + 11, 20
            dw      2026
            db      12, 0, 0
            dw      2
            db      'System-5 screen', 0

start:      ldi     high cursor     ; RF at HBIOS's cursor position
            phi     rf
            ldi     low cursor
            plo     rf
            lda     rf              ; RE = the last character of the cursor's line ...
            phi     re
            ldn     rf
            ori     3fh
            plo     re
            inc     re              ; ... and one past it: 7400 on the 6845 card, 7640 on VIDEO-G
            ghi     re              ; an address in 7040-77C0?
            smi     high screen
            bnf     lines16         ; below 7000: not a cursor
            smi     08h
            bnf     found           ; 70xx-77xx: clear up to there
lines16:    ldi     high scrend16   ; anything else: the 6845 card's 16 lines
            phi     re
            ldi     low scrend16
            plo     re
found:      ldi     high screen     ; RF = the first character of the screen
            phi     rf
            ldi     low screen
            plo     rf
clear:      ldi     ' '
            str     rf
            inc     rf
            glo     rf              ; until RF is at RE (the low byte is 00 or 40h only at the end of a line)
            str     r2
            glo     re
            xor
            bnz     clear
            ghi     rf
            str     r2
            ghi     re
            xor
            bnz     clear
            ldi     0               ; the program's return value: no error
            sep     r5              ; back to Elf/OS
