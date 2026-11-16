crtca:		equ	0c800h
crtcd:		equ	crtca+1
vmem:		equ	0c000h
JUMPTBL:	equ	0ff00h
basic_start:	equ	0f700h
basic_end:	equ	0feffh
basic_dest:	equ	00100h
line23:		equ    vmem+(80*23)
basmon:		equ	0f500h

		org 0f000h
boot:		ldi high boot	; Load D immediate
		phi r0		; Put high register R0
top:		ldi 0ffh
		phi r1
		plo r1
l1:		dec r1
		ghi r1
		bnz l1
		seq
		ldi 0ffh
		phi r1
		plo r1
l2:		dec r1
		ghi r1
		bnz l2
		req
		br top
