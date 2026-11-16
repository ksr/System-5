;
; HBIOS for VIDEO-G 1.0 (System-5), made 2026-11-01 from HBIOS v1.0.4 (firmware/hbios/v1.0.4/sec1.asm, unchanged).
; Changes, all for the VIDEO-G TEXT board (hardware/video-g/DESIGN.md sections 2, 3 and 8):
;   - the 6845 is on ports: OUT 5 = address register, OUT 6 = data (7800/7801 is now the graphics window)
;   - the 64 x 25 NTSC table (R0-R9 = 94,64,76,8,31,6,25,28,0,7; 8 x 8 cells), cursor rows 0-7
;   - the bottom row is row 24 (7600); the cursor is kept in 77FE/77FF as before (not displayed at 25 rows)
;   - OUT 4 = 00 at start: text on, graphics, XOR and mouse off, page 0
;   - a line feed scrolls only the 24 visible rows (an unrolled copy, 1536 bytes) and blanks row 24:
;     about 45 ms at 1.76 MHz, against 168 ms for the v1.0.4 copy of all of 7040-77FF
;   - the cursor address sent to R14/R15 is the 6845 address (RC - 7000), not the high byte of RC AND 3F
;   - a key of 80h or more (the VIDEO-G keyboard: F1-F12 80-8B, Home Up PgUp Left 5 Right End Down PgDn Ins Del
;     90-9A, with Shift C0-DA) is returned by inchar but not echoed (outchar strips bit 7: it would print junk)
; Everything else (the keyboard on INP 1 / EF3, break, the jump table at F200, the Riley code) is as in v1.0.4.
;
; Define BIOS to generate code for use with ELFOS BIOS
;

#define BIOS

;
; Define 6845VIDEOLOWER when video card (REV B and beyond) supports lower
; case characters and there is no need to force characters to upper case
;

#define VIDEOLOWER

;
; Define BASIC if the is for use with Tiny basic and not for ELFOS BIOS
;

;
; minimon is entry point in ELFOS BIOS to jump to once bios has booted
;

minimon:	equ     0ff54h

cur_h:		equ     14		; Cursor postion high
cur_l:		equ     15		; Cursor postion low

vmem:		equ	07000h		; Start of video memory
vmem_end:	equ     07800h		; End of video memory
vmem_ch:	equ	vmem_end-2
vmem_cl:	equ     vmem_end-1
space:		equ	020h		; Ascii Space
rows:		equ	25		; VIDEO-G NTSC: 64 x 25
line24:		equ     vmem+(64*24)	; the bottom row
vis_end:	equ	vmem+(64*25)	; end of the visible text (7640)

JUMPTBL:	equ	0ff00h
basic_start:	equ	0f700h
basic_end:	equ	0feffh
basic_dest:	equ	00100h
basmon:		equ	0f500h

		org 0f000h
boot:		ldi high boot	;Trigger Boot rom remap
		phi r0		;
		sex r0		; X = P: OUT with the byte that follows
		out 4		; VIDEO-G control register (OUT 4) = 00: text on, graphics off
		db 00h
		ldi high vtable ; Register D set to vtable (CRTC register, value pairs)
		phi rd          ;
		ldi low vtable  ;
		plo rd          ;
		sex rd		; X = RD: OUT sends M(RD) and steps RD
;
; Load Video Paramters into CRTC
;
vload:          out 5           ; register number to the 6845 address register (OUT 5)
	        out 6           ; its value to the 6845 data register (OUT 6)
	        glo rd          ; end of the table?
	        xri vtable_end.0
	        bnz  vload      ; If not load next CRTC Video paramter
		sex r0		; (X back to the program counter, as after reset)
;
; Clear Video memory (with space charachter)
;

		ldi high vmem   ; Register F set to start of Video memory
		phi rf          ;
		ldi low vmem    ;
		plo rf          ;
clear:          ldi space        ; Load D  space character
		str rf          ; Sstore in Video memory
		inc rf          ; Increment Register F to next video memory location
		ghi rf          ; Check if past end of video memory
		xri high vmem_end ; Logical XOR D with value
		bnz clear       ; Short branch on D!=0
;
; Store cursor position in memory
;
		ldi high vmem_ch
		phi rf
		ldi low vmem_ch
		plo rf
		ldi high line24
		str rf
		inc rf
		ldi low line24
		str rf
;
; Initialization complete jump to real start
;
		lbr  cold_entry      ; Long branch
;
; Video Paramters: (register, value) pairs, 64 x 25 NTSC (hardware/video-g/DESIGN.md section 2)
;
vtable:		 db 0,94  ; R0 total number of horiz chars
		 db 1,64  ; R1 number of horiz chars displayed
		 db 2,76  ; R2 Horiz sync position (chars)
		 db 3,8   ; R3 VSYNC/HSYNC Widths
		 db 4,31  ; R4 Vert Total (chars)
		 db 5,6   ; R5 Vert total Adjust (scan lines)
		 db 6,25  ; R6 Vert displayed (chars)
		 db 7,28  ; R7 Vert Sync position (chars)
		 db 8,0   ; R8 mode contro;
		 db 9,7   ; R9 scan lines/char (8)
		 db 10,64 ; R10 cursor start (scan line/char) + blink rate
		 db 11,7  ; R11 cursor end (scan line/char)
		 db 12,0  ; R12 display addr start high
		 db 13,0  ; R13 display addr start low
		 db 14,6  ; R14 Cursor position high (row 24)
		 db 15,0  ; R15 Cursor positon low
vtable_end:
;
; Input/Output routines
;
; output a character
; Character to output in D
;
outchar: 	ani 07fh         ; Strip off high bit
		plo re           ; Store Character to output in Register e.0
		xri 07fh         ; Check if character is is 07Fh (??? Why)
		bz  outnochar    ; If yes done
		glo re

#ifndef VIDEOLOWER
;
; convert to upper
;
		ani 040h
		bz  cont1	; less then 0x40
		glo re
		ani 05fh
		plo re
#endif

;save registers
cont1:        	sex 2
		glo rf
		stxd
		ghi rf
		stxd
		glo re
		stxd
		ghi re
		stxd
		glo rc
		stxd
		ghi rc
		stxd
;
; Get character position in RC
;
		ldi high vmem_ch ; Register F points to CRTC Address register
		phi rf         ;
		ldi low vmem_ch ;
		plo rf         ;
		ldn rf	       ; Get cursor position high
		phi rc         ; Store in RC.1
		inc rf
		ldn rf	       ; Get cursor position low
		plo rc	       ; Store in RC.0


	        glo re           ; Check for a control Character below 020h
                ani 0e0h         ;
		bnz  normal      ; Normal character
		glo re           ; Check for carriage return 0dh
		xri 0dh          ;
		bz  cr           ; Process carriage return
		glo re           ; Check for line feed 0ah
		xri 0ah          ;
		bz  lf           ; Process line feed
		glo re           ; Check for backspace
		xri 08h          ;
		bz  bs           ; process backspace
		br  outdn
;
; Process a carriage return
;
cr:		ldi high line24  ; Set Register C to start of the bottom row
		phi rc         	 ;
		ldi low line24   ;
		plo rc           ;
		br  update       ; Update cursor position
;
; Process a line feed: scroll the visible rows (at F300)
;
lf:		lbr scroll
;
; Process Back Space
;
bs:             dec rc         ; Register C is character pointer
		ldi space       ; Clear postion with a space character
		str rc         ;
	        br  update     ; Update Cursor postion
;
; Process Normal Character
;
normal:         glo re         ; Register F.1 contains character
		str rc         ; Store at register C, Character pointer
                inc rc         ;
;
; Update Cursor position: R14/R15 = RC - 7000 through OUT 5 / OUT 6 (X = 2)
;
update:
		ldi cur_h      ; CRTC High cursor register
		str r2         ; (the free byte below the stack)
		out 5          ; set CRTC Address register (R2 + 1)
		dec r2
		ghi rc         ; Get High portion of cursor postion
		ani 07h        ; the 6845 address: 64 x row + column, 0-7FF
		str r2
		out 6          ; cursor position high
		dec r2
		ldi cur_l      ; CRTC low cursor register
		str r2
		out 5          ; set CRTC Address register
		dec r2
		glo rc
		str r2
		out 6          ; cursor positon low
		dec r2
;
; Store cursor position in memory
;
		ldi high vmem_ch
		phi rf
		ldi low vmem_ch
		plo rf
		ghi rc
		str rf
		inc rf
		glo rc
		str rf
;
;restore registers
;
outdn:
		irx
		ldxa
		phi rc
		ldxa
		plo rc
		ldxa
		phi re
		ldxa
		plo re
		ldxa
		phi rf
		ldx
		plo rf
;
outnochar:		sep r5         ; Return
;
;
;
		org 0f100h
inchar:         bn3  inchar    ; Wait for an input character
        	sex 2
		inp 1          ; Read character
		ani 080h       ; VIDEO-G: F1-F12, arrows etc. send 80h and up: return them, but no echo
		bnz innoecho
		ldn r2         ; the character again
		dec r2         ; Decrement (R2) Save inputed character across call
		sep r4         ; Output the character
		dw out         ;
		inc r2         ; Increment (R2) restore inputed character
innoecho:	ldn r2         ; Get the input Character
		sep r5         ; Return
;
; Check for a break character
;
brk:		b3  brkchk     ; Character is available
bno:		ldi 00         ; Clear DF
		shl            ;
	        br brkdone       ; Return
;
;
;
brkchk:
        	sex 2
		inp 1          ; Input to (R(X)) and D, N=001
		xri 01bh       ; Check for ESC
                bnz bno        ; Not a break character
		ldi 0ffh       ; Set DF to 1
		shl            ; Shift left D
brkdone:	sep r5         ; Return
#ifdef BASIC
;
; Copy Basic into RAM
;
cbasic:         ldi high basic_start ; Set register E to start of BASIC Rom image location
		phi re
		ldi low basic_start
		plo re
		ldi high basic_dest ; Set register F to start of BASIC destination in RAM
		phi rf
		ldi low basic_dest
		plo rf
;
; Copy loop
;
bloop:          lda re         ;
		str rf         ;
		inc rf         ;
		ghi re         ;
		xri high basic_end+1 ; past end of Rom image
		bnz  bloop     ;
;
;    Jump to start of Basic
;
     lbr basic_dest       ; Long branch

		org 0ff00h
in:		lbr inchar
out:		lbr outchar
break:		lbr brk
cold_entry:	lbr cbasic
;warm_entry:	lbr wbasic
#endif

#ifdef BIOS
		org 0f200h
in:		lbr inchar
out:		lbr outchar
break:		lbr brk
cold_entry:	lbr minimon
#endif
;
; Line feed: copy rows 1-24 to rows 0-23, one row (64 bytes, unrolled) a pass, then blank row 24.
; RE = destination, RF = source; RC (the cursor) does not change.
;
		org 0f300h
scroll:		ldi high vmem    ; Register E = row 0
		phi re
		ldi low vmem
		plo re
		ldi high vmem+64 ; Register F = row 1
		phi rf
		ldi low vmem+64
		plo rf
sloop:
		lda rf		; byte 0 of the row
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		lda rf
		str re
		inc re
		ghi rf           ; source past row 24 (RF = 7640)?
		xri high vis_end
		bnz sloop
		glo rf
		xri vis_end.0
		bnz sloop
; Blank row 24: Register E now points to its first character
erl:		ldi space        ; Space Character
	        str re
       		inc re
		glo re           ; up to 7640
		xri vis_end.0
        	bnz erl          ; Continue erasing line
		lbr update       ; and set the cursor (RC is unchanged)
