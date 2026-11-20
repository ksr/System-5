;
; HBIOS for VIDEO-G 1.0 (System-5) on HBIOS v1.0.8: the ROM for the new card set (CPU Rev D, the IO panel, VIDEO-G).
; Made 2026-11-01 from HBIOS v1.0.4 for the VIDEO-G TEXT board; brought up to v1.0.8 on 2026-11-20 (Ken).
;
; For VIDEO-G (hardware/video-g/DESIGN.md sections 2, 3 and 8), in place of v1.0.4's 6845-card driver:
;   - VIDEO-G is memory-mapped (2026-11-17, hardware/video-g/DESIGN.md section 3): the 6845 at 7800 (address
;     register) and 7801 (data), as on the 6845 card; the key at 7802; status / control at 7804 (KEY-READY = bit 0)
;   - the 64 x 25 NTSC table (R0-R9 = 94,64,76,8,31,6,25,28,0,7; 8 x 8 cells), cursor rows 0-7
;   - the bottom row is row 24 (7600); the cursor is kept in 77FE/77FF as before (not displayed at 25 rows)
;   - the control register (7804) = 00 at start: text on, graphics, XOR and mouse off, page 0
;   - inchar and brk poll KEY-READY in the status register instead of EF3 (any CPU card: CPU Rev D takes the bus
;     -EF on EF4), read the key at 7802 and keep every register but D
;   - a line feed scrolls only the 24 visible rows (1536 bytes, twelve to a pass of the loop) and blanks row 24:
;     about 50 ms at 1.76 MHz, against 168 ms for the v1.0.4 copy of all of 7040-77FF
;   - the cursor address sent to R14/R15 is the 6845 address (RC - 7000), not the high byte of RC AND 3F
;   - a key of 80h or more (the VIDEO-G keyboard: F1-F12 80-8B, Home Up PgUp Left 5 Right End Down PgDn Ins Del
;     90-9A, with Shift C0-DA) is returned by inchar but not echoed (outchar strips bit 7: it would print junk)
;
; From v1.0.5 to v1.0.8, as in firmware/hbios/v1.0.8/sec1.asm (2026-11-20):
;   - the monitor's added commands: H (the list), B (boot the OS), D start:end (disassemble), Q1 / Q0, and the IO
;     panel demo at @F1C0. The disassembler's key wait reads VIDEO-G's keyboard (rawkey), where v1.0.8 has EF3 / INP 1
;   - the IO panel's real-time clock behind f_gettod and f_settod: the same bytes at the same addresses as v1.0.8
;     (FC92-FCEB and F7CD-F7FF)
;   - not here: v1.0.7's key codes at @F1E0 (written for the 6845 card and the old keyboard port). @F1E0 restarts
;     HBIOS in this ROM, so that the habit does no harm
; To make room in the 4K EPROM the line feed's copy is a loop of twelve bytes a pass (it was 64, 226 bytes of code at
; F300), and the pieces sit in the free runs: brk after the driver (F0D7), the rest of the H list and rawkey after
; inchar, Q1 / Q0 at F1E3, the scroll at FC45 after the disk fix. build.py checks that no piece runs into the next.
; build.py also gives it v1.0.6's disk fix (LBA mode, FBC1 / FBDF / FC31-FC44), which Elf/OS v5 needs, v1.0.5's
; hook into Mike Riley's monitor (F941, F9EB-F9ED) and v1.0.8's clock vectors (F816-F81A, FEDC).
; The jump table at F200 and the Riley code are as in v1.0.4.
;
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

crtca:		equ	07800h		; the 6845: address register (VIDEO-G, memory-mapped)
crtcd:		equ	07801h		; the 6845: data register
kdata:		equ	07802h		; the key (reading it clears KEY-READY)
vstat:		equ	07804h		; status (read; bit 0 = KEY-READY) and control (write)
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
		ldi high vstat	; the control register (7804) = 00: text on, graphics, XOR and mouse off, page 0
		phi rf
		ldi low vstat
		plo rf
		ldi 00h
		str rf
		ldi low crtca	; RF = 7800, the 6845's address register
		plo rf
		ldi high vtable ; Register D set to vtable (CRTC register, value pairs)
		phi rd          ;
		ldi low vtable  ;
		plo rd          ;
;
; Load Video Paramters into CRTC
;
vload:          lda rd          ; register number to the 6845's address register (7800)
		str rf
		inc rf
	        lda rd          ; its value to the data register (7801)
		str rf
		dec rf
	        glo rd          ; end of the table?
	        xri vtable_end.0
	        bnz  vload      ; If not load next CRTC Video paramter
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
; Update Cursor position: R14/R15 = RC - 7000, through 7800 / 7801 (RF is saved above and restored at outdn)
;
update:
		ldi high crtca	; RF = 7800, the 6845's address register
		phi rf
		ldi low crtca
		plo rf
		ldi cur_h      ; CRTC High cursor register
		str rf
		inc rf
		ghi rc         ; Get High portion of cursor postion
		ani 07h        ; the 6845 address: 64 x row + column, 0-7FF
		str rf         ; cursor position high (7801)
		dec rf
		ldi cur_l      ; CRTC low cursor register
		str rf
		inc rf
		glo rc
		str rf         ; cursor positon low
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
; (brk sits here, in the free bytes after the driver, so that the rest of the H list fits after inchar)
;
; Check for a break character: DF = 1 if a key waits and it is ESC (a key that waits is read either way, as before)
;
brk:		sex 2		; keep RF
		glo rf
		stxd
		ghi rf
		stxd
		ldi high vstat	; RF = 7804, the status register
		phi rf
		ldi low vstat
		plo rf
		ldn rf		; KEY-READY?
		shr
		bnf bno		; no key: DF = 0 (SHR left it 0)
		ldi low kdata	; RF = 7802: the key
		plo rf
		ldn rf
		xri 01bh       ; Check for ESC
                bnz bnoclr     ; Not a break character
		ldi 0ffh       ; Set DF to 1
		shl            ; Shift left D
		br brkdone
bnoclr:		ldi 00         ; Clear DF
		shl            ;
bno:
brkdone:	irx		; RF back (IRX, LDXA, PHI, LDX, PLO leave DF alone)
		ldxa
		phi rf
		ldx
		plo rf
		sep r5         ; Return
e_f0:				; (build.py: must not pass F100)
;
;
;
		org 0f100h
inchar:		sex 2		; keep RF on the stack (R2 = s on return, as on entry)
		glo rf
		stxd
		ghi rf
		stxd
		ldi high vstat	; RF = 7804, the status register
		phi rf
		ldi low vstat
		plo rf
inwait:		ldn rf		; Wait for an input character: KEY-READY (bit 0), polled, not EF3 (CPU Rev D has -EF
		shr		; on EF4)
		bnf inwait
		ldi low kdata	; RF = 7802: Read character (the read clears KEY-READY)
		plo rf
		ldn rf
		str r2		; the character, in the free byte below the saved RF
		ani 080h       ; VIDEO-G: F1-F12, arrows etc. send 80h and up: return them, but no echo
		bnz innoecho
		ldn r2         ; the character again
		dec r2         ; Decrement (R2) Save inputed character across call
		sep r4         ; Output the character
		dw out         ;
		inc r2         ; Increment (R2) restore inputed character
innoecho:	irx		; RF back
		ldxa
		phi rf
		ldx
		plo rf
		dec r2		; the character, two below R2 (nothing has written there since)
		dec r2
		ldn r2         ; Get the input Character
		inc r2
		inc r2
		sep r5         ; Return
;
; The rest of the monitor's H list (v1.0.5), typed after montext
montext2:	db ' Q1 / Q0         turn Q on / off (SEQ / REQ)',10,13
		db ' @F1C0           panel demo: toggles to LEDs, INPUT to Q',10,13
		db ' H               this list',10,13,0
;
; rawkey: D = the next key, waited for and not echoed (the disassembler's -- more --). Called through SCRT.
; RF is used and not kept; every other register is left alone.
rawkey:		ldi high vstat	; RF = 7804, the status register
		phi rf
		ldi low vstat
		plo rf
rkwait:		ldn rf		; KEY-READY (bit 0)?
		shr
		bnf rkwait
		ldi low kdata	; RF = 7802: the key (the read clears KEY-READY)
		plo rf
		ldn rf
		sep r5
e_f1:				; (build.py: must not pass F1C0)
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
;
; Monitor commands added in HBIOS v1.0.5 (Ken, 2026-11-12): H lists the commands, B boots the OS from the CF card,
; D start:end disassembles (a screenful at a time, waiting for a key; D start alone shows one screenful), Q1 / Q0
; turn the 1802's Q output on / off. @F1C0 runs a small IO panel demo.
; Mike Riley's monitor (F900) goes back to its prompt when it does not know a command. build.py patches that one
; branch (F940: BNZ F913 becomes BNZ F9EB) and puts LBR monext in the BIOS's free bytes at F9EB, so an unknown
; command comes here. On entry: RC.1 = the command character, RA = the hex number typed after it, X = 2, P = 3,
; SCRT set up (R4 call, R5 return). F913 is the monitor's prompt: it types test> and reads the next line.
;
monprompt:	equ 0f913h
f_msg:		equ 0ff09h	; type the zero-terminated text at RF
f_ltrim:	equ 0ff15h	; RF past spaces
f_hexin:	equ 0ff45h	; RD = the hex number at RF; RF after it
f_hexout2:	equ 0ff48h	; two hex digits of RD.0 to RF, RF after them
f_hexout4:	equ 0ff4bh	; four hex digits of RD to RF, RF after them
monext:		ghi rc		; the command character
		ani 0dfh	; lower case to upper case (b -> B, h -> H)
		smi 'B'
		lbz monboot	; B: boot the OS
		smi 'D'-'B'
		lbz mondis	; D: disassemble
		smi 'H'-'D'
		lbz monhelp	; H: list the commands
		smi 'Q'-'H'
		lbz monq	; Q1 / Q0: Q on / off
		lbr monprompt	; anything else: back to the prompt, as before
;
monboot:	ldi high 0ff00h	; as @FF00: R0 = FF00, X = P = 0, then f_boot
		phi r0
		ldi low 0ff00h
		plo r0
		sex r0
		sep r0
;
monhelp:	ldi high montext
		phi rf
		ldi low montext
		plo rf
		sep r4		; f_msg types the text at RF
		dw 0ff09h
		ldi high montext2	; the rest of the list, after the keyboard code
		phi rf
		ldi low montext2
		plo rf
		sep r4
		dw 0ff09h
		lbr monprompt
;
montext:	db 'Monitor commands (numbers in hex):',10,13
		db ' ?addr           show 128 bytes from addr',10,13
		db ' !addr bb bb ..  store bytes at addr',10,13
		db ' =src dst count  copy count bytes from src to dst',10,13
		db ' @addr           run at addr (P = X = 0)',10,13
		db ' B               boot the OS from the CF card (@FF00)',10,13
		db ' D start:end     disassemble, a screenful at a time',10,13
		db '                 (at -- more --: any key goes on, Esc stops)',10,13
		db ' D start         disassemble one screenful',10,13
		db 0
;
; D start:end - disassemble, one instruction a line: the address, the bytes, the mnemonic, as the emulator's
; disassembler writes them (so the two can be compared line for line). Every 14 lines it waits for a key: Esc,
; Ctrl-C or Q stops, any other key goes on. D start with no end shows 14 lines. Stops at the end address or when the
; address passes FFFF. Registers: RA the address, R9 the end, R8.0 lines left before a pause, R8.1 1 = an end was
; given, RB.0 the opcode, RB.1 its length, R7 a table or the operands, RC a counter. The line is built in the
; monitor's input buffer (0003): the address at 0003, the bytes at 0009, the mnemonic at 0013.
;
dline_at:	equ 0003h
dbytes_at:	equ 0009h
dtext_at:	equ 0013h
dlines:		equ 14
mondis:		ldi high 0004h	; read the line again from after the D: f_hexin does not skip spaces
		phi rf
		ldi low 0004h
		plo rf
		sep r4
		dw f_ltrim
		sep r4
		dw f_hexin	; the start address
		ghi rd
		phi ra
		glo rd
		plo ra
		sep r4
		dw f_ltrim
		ldn rf		; ':' or '-' between the two addresses
		xri ':'
		lbz dskip
		xri ':'^'-'
		lbnz dnosep
dskip:		inc rf
		sep r4
		dw f_ltrim
dnosep:		ldn rf
		lbz dnoend	; nothing more on the line: no end address
		sep r4
		dw f_hexin	; the end address
		ghi rd
		phi r9
		glo rd
		plo r9
		ldi 1
		lskp
dnoend:		ldi 0
		phi r8		; R8.1 = 1 when an end address was given
dpage:		ldi dlines
		plo r8
;
; one line
dline:		ldi high dline_at	; the address
		phi rf
		ldi low dline_at
		plo rf
		ghi ra
		phi rd
		glo ra
		plo rd
		sep r4
		dw f_hexout4
		ldi ' '
		str rf
		inc rf
		str rf
		ldi high dtext_at	; the mnemonic and its operand (sets RB.1 = the length)
		phi rf
		ldi low dtext_at
		plo rf
		lda ra		; the opcode (RA moves on; dbytes goes back to it)
		plo rb
		dec ra
		sep r4
		dw ddecode
		ldi 10		; end of the line
		str rf
		inc rf
		ldi 13
		str rf
		inc rf
		ldi 0
		str rf
		ldi high dbytes_at	; the bytes, in a field 10 wide
		phi rf
		ldi low dbytes_at
		plo rf
		ghi rb
		plo rc		; RC.0 = bytes to show
		ldi 3
		phi rc		; RC.1 = slots
dbyte:		glo rc
		lbz dnobyte
		dec rc
		lda ra		; RA moves past the instruction here
		plo rd
		glo ra		; RA past FFFF: R8.1 bit 1, to stop after this line
		lbnz dshow
		ghi ra
		lbnz dshow
		ghi r8
		ori 2
		phi r8
dshow:		sep r4
		dw f_hexout2
		lbr dslot
dnobyte:	ldi ' '
		str rf
		inc rf
		str rf
		inc rf
dslot:		ldi ' '
		str rf
		inc rf
		ghi rc
		smi 1
		phi rc
		lbnz dbyte
		ldi ' '
		str rf
		ldi high dline_at	; type it
		phi rf
		ldi low dline_at
		plo rf
		sep r4
		dw f_msg
;
; the next one, or stop
		ghi r8		; past FFFF: stop
		ani 2
		lbnz ddone
		ghi r8
		lbz dcount	; no end address: just count the lines
		sex r2		; RA past R9: stop
		glo ra
		str r2
		glo r9
		sm
		ghi ra
		str r2
		ghi r9
		smb
		lbnf ddone
dcount:		dec r8
		glo r8
		lbnz dline
		ghi r8
		lbz ddone	; no end address: one screenful
		ldi high dmore	; wait for a key
		phi rf
		ldi low dmore
		plo rf
		sep r4
		dw f_msg
dkey:		sep r4		; the key, not echoed: VIDEO-G's, polled at 7804 and read at 7802 (X stays 2)
		dw rawkey
		plo r7		; (not RC: the screen output uses it)
		ldi high derase
		phi rf
		ldi low derase
		plo rf
		sep r4
		dw f_msg
		glo r7
		xri 1bh		; Esc
		lbz ddone
		xri 1bh^03h	; Ctrl-C
		lbz ddone
		glo r7		; Q or q
		ani 0dfh
		xri 'Q'
		lbz ddone
		lbr dpage
ddone:		lbr monprompt
dmore:		db '-- more --',0
derase:		db 13,'          ',13,0
;
; ddecode: the mnemonic and operand of the opcode in RB.0 to RF; RB.1 = the instruction's length. RA = its address.
ddecode:	ldi 1
		phi rb
		glo rb
		lbnz dnotidl
		ldi high tidl
		phi r7
		ldi low tidl
		plo r7
		lbr dname4
dnotidl:	xri 0d4h	; D4 = SEP R4 + an address: CALL, as SCRT uses it
		lbnz dnotcall
		ldi high tcall
		phi r7
		ldi low tcall
		plo r7
		sep r4
		dw dcopy4
		lbr dlong
dnotcall:	xri 0d4h^0d5h	; D5 = SEP R5: RETN
		lbnz dnotretn
		ldi high tretn
		phi r7
		ldi low tretn
		plo r7
		lbr dname4
dnotretn:	ldi high treg	; the groups with a register: LDN INC DEC LDA STR GLO GHI PLO PHI SEP SEX
		phi r7
		ldi low treg
		plo r7
		glo rb
		shr
		shr
		shr
		shr
		sep r4
		dw dindex3
		ldn r7
		xri ' '
		lbz dnotreg
		sep r4
		dw dcopy3
		ldi ' '
		str rf
		inc rf
		ldi 'R'
		str rf
		inc rf
		glo rb		; the register, one hex digit
		ani 0fh
		plo rd
		sep r4
		dw f_hexout2	; writes 0N: keep the N
		dec rf
		ldn rf
		dec rf
		str rf
		inc rf
		sep r5
dnotreg:	glo rb
		ani 0f0h
		xri 30h
		lbnz dnot3
		glo rb		; 3N: the short branches (38 is SKP, no operand)
		xri 38h
		lbnz dshort
		ldi high tskp
		phi r7
		ldi low tskp
		plo r7
		lbr dname4
dshort:		ldi high tsb
		phi r7
		ldi low tsb
		plo r7
		glo rb
		sep r4
		dw dindex3
		sep r4
		dw dcopy3
		ldi ' '
		str rf
		inc rf
		ghi ra		; the target: the operand's page, the operand
		phi r7
		glo ra
		plo r7
		inc r7
		ghi r7
		phi rd
		ldn r7
		plo rd
		sep r4
		dw f_hexout4
		ldi 2
		phi rb
		sep r5
dnot3:		glo rb
		ani 0f0h
		xri 60h
		lbnz dnot6
		glo rb		; 6N: IRX, OUT 1-7, 68, INP 1-7
		ani 0fh
		lbnz dnotirx
		ldi high tirx
		phi r7
		ldi low tirx
		plo r7
		lbr dname4
dnotirx:	xri 08h
		lbnz dio
		ldi high t68	; 68 (the 1804/1806 prefix): DB 68H
		phi r7
		ldi low t68
		plo r7
		sep r4
		dw dcopy4
		ldi ' '
		str rf
		inc rf
		ldi high t68b
		phi r7
		ldi low t68b
		plo r7
		lbr dname4
dio:		ldi high tout
		phi r7
		ldi low tout
		plo r7
		glo rb
		ani 08h
		lbz dio1
		ldi high tinp
		phi r7
		ldi low tinp
		plo r7
dio1:		sep r4
		dw dcopy4
		ldi ' '
		str rf
		inc rf
		glo rb
		ani 07h
		adi '0'
		str rf
		inc rf
		sep r5
dnot6:		glo rb
		ani 0f0h
		xri 70h
		lbnz dnot7
		ldi high t7	; 7N: ADCI SDBI SMBI (7C 7D 7F) take a byte
		phi r7
		ldi low t7
		plo r7
		glo rb
		sep r4
		dw dindex4
		sep r4
		dw dcopy4
		glo rb
		xri 7ch
		lbz dimm
		xri 7ch^7dh
		lbz dimm
		xri 7dh^7fh
		lbz dimm
		sep r5
dnot7:		glo rb
		ani 0f0h
		xri 0c0h
		lbnz dnotc
		ldi high tc	; CN: long branches take an address; C4-C8 and CC-CF are one byte
		phi r7
		ldi low tc
		plo r7
		glo rb
		sep r4
		dw dindex4
		sep r4
		dw dcopy4
		glo rb
		ani 04h
		lbz dc1
		sep r5
dc1:		glo rb
		xri 0c8h
		lbnz dlong
		sep r5
dnotc:		ldi high tf	; FN: LDI ORI ANI XRI ADI SDI SMI (F8-FD, FF) take a byte
		phi r7
		ldi low tf
		plo r7
		glo rb
		sep r4
		dw dindex3
		sep r4
		dw dcopy3
		glo rb
		ani 0fh
		smi 8
		lbnf dnoimm
		xri 6		; FE = SHL
		lbz dnoimm
		lbr dimm
dnoimm:		sep r5
;
; operands
dimm:		ldi ' '		; one byte: 2 hex digits and H
		str rf
		inc rf
		ghi ra
		phi r7
		glo ra
		plo r7
		inc r7
		ldn r7
		plo rd
		sep r4
		dw f_hexout2
		ldi 'H'
		str rf
		inc rf
		ldi 2
		phi rb
		sep r5
dlong:		ldi ' '		; two bytes: an address
		str rf
		inc rf
		ghi ra
		phi r7
		glo ra
		plo r7
		inc r7
		lda r7
		phi rd
		ldn r7
		plo rd
		sep r4
		dw f_hexout4
		ldi 3
		phi rb
		sep r5
dname4:		sep r4		; a name alone, up to 4 characters
		dw dcopy4
		sep r5
;
; R7 = the table + entry D, entries 3 or 4 wide
dindex3:	ani 0fh
		str r2
		shl
		add		; 3 x
		lbr dindex
dindex4:	ani 0fh
		shl
		shl		; 4 x
dindex:		str r2
		glo r7
		add
		plo r7
		ghi r7
		adci 0
		phi r7
		sep r5
;
; copy a name from R7 to RF: up to 3 or 4 characters, stopping at a space
dcopy3:		ldi 3
		lskp
dcopy4:		ldi 4
		plo rc
dcopy:		lda r7
		xri ' '
		lbz dcopied
		xri ' '
		str rf
		inc rf
		dec rc
		glo rc
		lbnz dcopy
dcopied:	sep r5
;
tidl:		db 'IDL '
tcall:		db 'CALL'
tretn:		db 'RETN'
tskp:		db 'SKP '
tirx:		db 'IRX '
tout:		db 'OUT '
tinp:		db 'INP '
t68:		db 'DB  '
t68b:		db '68H '
treg:		db 'LDNINCDEC   LDASTR      GLOGHIPLOPHI   SEPSEX   '
tsb:		db 'BR BQ BZ BDFB1 B2 B3 B4 SKPBNQBNZBNFBN1BN2BN3BN4'
t7:		db 'RET DIS LDXASTXDADC SDB SHRCSMB SAV MARKREQ SEQ ADCISDBISHLCSMBI'
tc:		db 'LBR LBQ LBZ LBDFNOP LSNQLSNZLSNFLSKPLBNQLBNZLBNFLSIELSQ LSZ LSDF'
tf:		db 'LDXOR ANDXORADDSD SHRSM LDIORIANIXRIADISDISHLSMI'
e_monext:			; (build.py: must not pass F7CD)
;
; The IO panel demo (Ken, 2026-11-12): @F1C0 from the monitor. Over and over: read the toggles (INP 4), show them on
; the LEDs (OUT 4), and set Q to match INPUT (EF1: pressed = Q on). Reset ends it. The monitor's @ starts it with
; P = 0 and X = 0, so R0 is its program counter; INP and OUT need X on a byte of RAM, so R1 points at 00F0 (the
; monitor's workspace: nothing else runs meanwhile).
		org 0f1c0h
pdemo:		ldi 00h		; R1 = 00F0, a byte of RAM for INP and OUT
		phi r1
		ldi 0f0h
		plo r1
		sex r1
ploop:		inp 4		; the toggles to M(R1) and D
		out 4		; M(R1) to the LEDs; R1 + 1
		dec r1
		b1 pqon		; INPUT pressed (EF1): Q on
		req
		br ploop
pqon:		seq
		br ploop
e_pdemo:			; (build.py: must not pass F1E0)
;
; @F1E0 is v1.0.7's key-code display on the 6845-card ROMs. It is not in this ROM: here it restarts HBIOS.
		org 0f1e0h
		lbr boot
;
; Q1 / Q0: the 1802's Q output on (SEQ, 7B) or off (REQ, 7A). Any number but 0 turns it on.
monq:		ldi high 0004h	; read the number again from after the Q: f_hexin does not skip spaces
		phi rf
		ldi low 0004h
		plo rf
		sep r4
		dw f_ltrim
		sep r4
		dw f_hexin
		glo rd
		lbz monq0
		seq
		lbr monprompt
monq0:		req
		lbr monprompt
e_monq:				; (build.py: must not pass F200)
;
; The IO panel card's real-time clock (Ken, 2026-11-18; v1.0.8): a DS12885 on two ports, as the card's JP4 is set: OUT 6
; latches a register number, OUT 7 writes that register, INP 7 reads it. f_gettod (F815) and f_settod (F818) jump here
; (in v1.0.4-v1.0.7 they jump to the BIOS's error return), and f_getdev's answer has bit 4 (an RTC) set. The calls are
; Mike Riley's, as his BIOS answers them for the ELF2000's DS1287 (orig_bios/bios.asm, e2k_gtod / e2k_stod): RF points
; at six bytes, month, day, year, hour, minute, second; the year is ELF/OS's (years since 1972), kept in the clock's
; year register as it is (28 years is a whole number of leap cycles, so the clock's leap years stay right). Binary,
; 24-hour mode, daylight saving off. DF = 0: done; f_gettod returns DF = 1 (D = 1) when the clock is not running in
; binary 24-hour mode: never set, or no clock at all (an INP of a port nobody drives reads FF, which is not 010 in DV).
; Called through SCRT (R4 / R5), so X = 2 and R2 is the stack: a byte goes out from M(R2) (STR R2, OUT n, DEC R2).
; Nothing but D, DF and RF changes.
;
		org 0fc92h
rtcget:		sep r4		; register A: is the oscillator running (DV = 010)?
		dw rtcrd
		db 0ah
		ani 70h
		xri 20h
		lbnz rtcbad
		sep r4		; register B: binary (DM) and 24-hour?
		dw rtcrd
		db 0bh
		ani 06h
		xri 06h
		lbnz rtcbad
rtcuip:		sep r4		; wait while an update is in progress (UIP, register A bit 7): then
		dw rtcrd	; the registers stay put for 244 us at least
		db 0ah
		ani 80h
		lbnz rtcuip
		sep r4		; month
		dw rtcrd
		db 08h
		str rf
		inc rf
		sep r4		; day
		dw rtcrd
		db 07h
		str rf
		inc rf
		sep r4		; year
		dw rtcrd
		db 09h
		str rf
		inc rf
		sep r4		; hour
		dw rtcrd
		db 04h
		str rf
		inc rf
		sep r4		; minute
		dw rtcrd
		db 02h
		str rf
		inc rf
		sep r4		; second
		dw rtcrd
		db 00h
		str rf
		inc rf
		adi 0		; DF = 0: done
		sep r5
rtcbad:		ldi 1		; DF = 1, D = 1: the clock is not set (or not there)
		smi 0
		sep r5
;
; rtcrd: D = the clock's register named by the byte after the call. rtcwr: D into it.
rtcrd:		lda r6		; the register number
		str r2
		out 6		; latch it (AS)
		dec r2
		inp 7		; read the register (DS): to M(R2) and D
		sep r5
rtcwr:		stxd		; the value, kept below the free byte
		lda r6		; the register number
		str r2
		out 6		; latch it (AS)
		dec r2
		irx		; R2 at the value
		out 7		; write it (R/W)
		dec r2		; R2 back where it was
		sep r5
e_rtc:				; (build.py: must not pass FD00)
;
; f_settod: start the oscillator (register A = 20h: DV = 010, no square wave), stop the count (SET) in binary 24-hour
; mode, write the six registers, then let it count (register B = 06h), as Mike's e2k_stod does but daylight saving off.
		org 0f7cdh
rtcset:		ldi 20h
		sep r4
		dw rtcwr
		db 0ah
		ldi 86h		; SET, binary (DM), 24-hour
		sep r4
		dw rtcwr
		db 0bh
		lda rf		; month
		sep r4
		dw rtcwr
		db 08h
		lda rf		; day
		sep r4
		dw rtcwr
		db 07h
		lda rf		; year
		sep r4
		dw rtcwr
		db 09h
		lda rf		; hour
		sep r4
		dw rtcwr
		db 04h
		lda rf		; minute
		sep r4
		dw rtcwr
		db 02h
		lda rf		; second
		sep r4
		dw rtcwr
		db 00h
		ldi 06h		; count: binary, 24-hour, SET off
		sep r4
		dw rtcwr
		db 0bh
		adi 0		; DF = 0
		sep r5
e_rtcset:			; (build.py: must not pass F800)
;
; Line feed: copy rows 1-24 to rows 0-23, twelve bytes a pass (1536 = 128 passes), then blank row 24.
; RE = destination, RF = source; RC (the cursor) does not change. The source's low byte is 40h again only after
; a whole 768 bytes (64 passes), at 7340 and at 7640, so the end test costs three instructions a pass.
; At FC45, after the disk fix's code (FC31-FC44, put there by build.py).
;
		org 0fc45h
scroll:		ldi high vmem    ; Register E = row 0
		phi re
		ldi low vmem
		plo re
		ghi re           ; Register F = row 1 (7040)
		phi rf
		ldi low vmem+64
		plo rf
sloop:
		lda rf		; twelve bytes of the row
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
		glo rf           ; source at xx40?
		xri vis_end.0
		bnz sloop
		ghi rf           ; and past row 24 (RF = 7640)?
		xri high vis_end
		bnz sloop
; Blank row 24: Register E now points to its first character
erl:		ldi space        ; Space Character
		str re
		inc re
		glo re           ; up to 7640
		xri vis_end.0
		bnz erl          ; Continue erasing line
		lbr update       ; and set the cursor (RC is unchanged)
e_scroll:			; (build.py: must not pass FC92)
#endif
