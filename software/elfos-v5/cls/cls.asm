; cls for Elf/OS v5 on System-5: clears the 6845 card's screen.
; Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-14
;
; Mike Riley's cls types ESC [ H ESC [ 2 J, the codes that clear an ANSI terminal. HBIOS's screen is not one: it
; showed "[H[2J" and cleared nothing. This program writes spaces over the screen itself.
;
; HBIOS (1.0.4 and 1.0.5) types on the bottom line of a 64 x 16 screen and scrolls the rest up, so there is no
; "home". The cursor is left where it is, at the start of the bottom line, and the next text appears there.
; The screen is the first 1024 bytes of the 6845 card's video RAM, 7000-73FF. HBIOS keeps its cursor position in
; the last two bytes of that RAM (77FE, 77FF); they are not touched.
;
; Build: python3 software/elfos-v5/build.py  (tools/asm1802.py; it writes cls, the Elf/OS program, and cls.lst)

screen:     equ     07000h          ; the 6845 card's video RAM: 16 lines of 64 characters
scrend:     equ     07400h          ; one past the last character on the screen

            org     2000h
            br      start
; What `ver /bin/cls` shows, laid out as in Mike Riley's programs: the month (with C0h added, as his have it), the
; day, the year, the hour, minute and second, a build number, and a text.
            db      0c0h + 11, 14
            dw      2026
            db      12, 0, 0
            dw      1
            db      'System-5 6845 screen', 0

start:      ldi     high screen     ; RF = the first character of the screen
            phi     rf
            ldi     low screen
            plo     rf
clear:      ldi     ' '
            str     rf
            inc     rf
            ghi     rf              ; until RF is past the last line
            xri     high scrend
            bnz     clear
            ldi     0               ; the program's return value: no error
            sep     r5              ; back to Elf/OS
