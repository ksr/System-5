; Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-25
; The bus test's program (busboard.py): it goes in the CPU card's EPROM at F000 and uses every line of the bus. It
; checks nothing itself but a checksum it keeps in RB.0: every cycle it makes is compared with the instruction-level
; machine's. The bytes it sends to port 4 are markers (busboard.py acts on E1, E2 and ED).
;   R1 interrupt   R2 stack / X   R3 PC   R7 pointer   R8 table   R9 count   RA data   RB checksum   RC sector pointer
        ORG 0F000h
        LDI 0F0h                ; at 0000 in the boot map: the first A15 cycle ends it
        PHI R0
        LDI LOW START
        PLO R0
START:  LDI HIGH MAIN
        PHI R3
        LDI LOW MAIN
        PLO R3
        SEP R3
MAIN:   LDI HIGH INTR
        PHI R1
        LDI LOW INTR
        PLO R1
        LDI 06Fh                ; the stack, X
        PHI R2
        LDI 0F0h
        PLO R2
        SEX R2
        LDI 0
        PLO RB
        REQ
; ---- RAM: 0000 and 1, 2, 4 ... 4000, a byte of its own at each, then all read back (every address line, A0-A14)
        LDI 0A1h
        PLO RA
        LDI 0
        PHI R7
        PLO R7
        LDI 16
        PLO R9
RAMW:   GLO RA
        STR R7
        ADI 35h
        PLO RA
        GLO R7                  ; R7 = 0 -> 1, else shifted left
        LBNZ RAMS
        GHI R7
        LBNZ RAMS
        INC R7
        LBR RAMN
RAMS:   GLO R7
        SHL
        PLO R7
        GHI R7
        SHLC
        PHI R7
RAMN:   DEC R9
        GLO R9
        LBNZ RAMW
        LDI 0
        PHI R7
        PLO R7
        LDI 16
        PLO R9
RAMR:   LDN R7
        STR R2
        GLO RB
        XOR
        PLO RB
        GLO R7
        LBNZ RRS
        GHI R7
        LBNZ RRS
        INC R7
        LBR RRN
RRS:    GLO R7
        SHL
        PLO R7
        GHI R7
        SHLC
        PHI R7
RRN:    DEC R9
        GLO R9
        LBNZ RAMR
; ---- the memory card's EPROMs: 8000 and 8001, 8002, 8004 ... C000 (its bytes are the address, mixed)
        LDI 80h
        PHI R7
        LDI 0
        PLO R7
        LDN R7
        LDI 0
        PHI R8
        LDI 1
        PLO R8
        LDI 15
        PLO R9
ROMR:   GHI R8
        ORI 80h
        PHI R7
        GLO R8
        PLO R7
        LDN R7
        STR R2
        GLO RB
        ADD
        PLO RB
        GLO R8
        SHL
        PLO R8
        GHI R8
        SHLC
        PHI R8
        DEC R9
        GLO R9
        LBNZ ROMR
        LDI 0E5h                ; E5A5, and a write there that must change nothing
        PHI R7
        LDI 0A5h
        PLO R7
        LDN R7
        STR R7
        LDN R7
; ---- nothing answers: 7806, 7C00 and 7FFF read FF (the bus's pull-ups), before and after a 00 on the bus
        LDI 78h
        PHI R7
        LDI 06h
        PLO R7
        LDI 0
        STR R2
        LDN R2
        LDN R7
        LDI 7Ch
        PHI R7
        LDI 0
        PLO R7
        LDN R2
        LDN R7
        INP 1                   ; and a port nobody has
; ---- the video RAM: 7000, 7001, 7002 ... 7400, written and read; then the 6845's sixteen registers
        LDI 70h
        PHI R7
        LDI 0
        PLO R7
        LDI 0C9h
        STR R7
        LDI 1
        PLO R8
        LDI 0
        PHI R8
        LDI 11
        PLO R9
        LDI 5Ah
        PLO RA
VIDW:   GHI R8
        ORI 70h
        PHI R7
        GLO R8
        PLO R7
        GLO RA
        STR R7
        ADI 47h
        PLO RA
        LDN R7
        GLO R8
        SHL
        PLO R8
        GHI R8
        SHLC
        PHI R8
        DEC R9
        GLO R9
        LBNZ VIDW
        LDI 70h
        PHI R7
        LDI 0
        PLO R7
        LDN R7
        LDI 78h
        PHI R7
        LDI 15
        PLO R9
CRT:    LDI 0
        PLO R7
        GLO R9
        STR R7
        INC R7
        ADI 0C0h
        XRI 5Ah
        STR R7
        DEC R9
        GHI R9
        GLO R9
        LBNZ CRT
; ---- the keyboard: wait for its flag on EF3, the status, the key; twice; then the flag is off
        LBR KEYS
        ALIGN 256
KEYS:   LDI 2
        PLO R9
KEY:    BN3 KEY
        B1 EFB0                 ; none of the other three while a key waits
        B2 EFB0
        B4 EFB0
        LDI 04h
        PLO R7
        LDN R7
        LDI 02h
        PLO R7
        LDN R7
        STR R2
        GLO RB
        ADD
        PLO RB
        DEC R9
        GLO R9
        LBNZ KEY
        B3 KEYBAD
        LBR KEYOK
EFB0:
KEYBAD: LDI 0EEh
        STR R2
        OUT 4
KEYOK:  LDI 04h
        PLO R7
        LDN R7
; ---- the IO panel: bytes to its LEDs, the toggles, Q, INPUT on EF1 (the host presses it at E1, lets go at E2)
        LDI 1
        PLO RA
P4:     GLO RA
        STR R2
        OUT 4
        DEC R2
        GLO RA
        SHL
        PLO RA
        LBNZ P4
        LDI 0
        STR R2
        OUT 4
        DEC R2
        INP 4
        SEQ
        LDI 0FFh
        STR R2
        OUT 4
        DEC R2
        REQ
        LDI 55h
        STR R2
        OUT 4
        DEC R2
        B1 IN1
IN1:    LDI 0E1h
        STR R2
        OUT 4
        DEC R2
        LBR WAIT1
        ALIGN 16
WAIT1:  BN1 WAIT1
        B2 EFB                  ; INPUT is down: none of the other three
        B3 EFB
        B4 EFB
        LDI 0E2h
        STR R2
        OUT 4
        DEC R2
        LBR WAIT0
        ALIGN 16
WAIT0:  B1 WAIT0
        B2 EFB                  ; and none when nothing pulls them
        B3 EFB
        B4 EFB
        LBR EFOK
EFB:    LDI 0EFh
        STR R2
        OUT 4
        DEC R2
; ---- the clock's RAM (ports 6 and 7) and the UART on the same ports: scratch, a character out
EFOK:   SEX R3
        OUT 6
        DB 2Ah
        OUT 7
        DB 0D3h
        OUT 6
        DB 55h
        OUT 7
        DB 2Ch
        OUT 6
        DB 2Ah
        SEX R2
        INP 7
        SEX R3
        OUT 6
        DB 55h
        SEX R2
        INP 7
        SEX R3
        OUT 6
        DB 87h
        OUT 7
        DB 69h
        SEX R2
        INP 7
        SEX R3
        OUT 6
        DB 85h
        SEX R2
        INP 7
        SEX R3
        OUT 6
        DB 80h
        OUT 7
        DB 'S'
; ---- the drive (ports 2 and 3): its registers, then bytes of sector 1
        OUT 2
        DB 2
        OUT 3
        DB 1
        OUT 2
        DB 3
        OUT 3
        DB 1
        OUT 2
        DB 4
        OUT 3
        DB 0A6h
        SEX R2
        INP 3
        SEX R3
        OUT 2
        DB 5
        OUT 3
        DB 59h
        SEX R2
        INP 3
        SEX R3
        OUT 2
        DB 4
        OUT 3
        DB 0
        OUT 2
        DB 5
        OUT 3
        DB 0
        OUT 2
        DB 6
        OUT 3
        DB 0E0h
        OUT 2
        DB 7
        OUT 3
        DB 20h
        SEX R2
        INP 3
        SEX R3
        OUT 2
        DB 0
        SEX R2
        INP 3
        INP 3
        INP 3
        INP 3
        INP 3
        INP 3
        INP 3
        INP 3
; ---- an interrupt: the UART's, when a character has come in (it waits already): IER bit 0
        SEX R3
        OUT 6
        DB 81h
        OUT 7
        DB 01h                  ; -INT falls: the interrupt comes after this instruction
        NOP
        NOP
        SEX R2
        GLO RB
        STR R2
        OUT 4                   ; the checksum, on the LEDs
        DEC R2
        LDI 0EDh
        STR R2
        OUT 4
        DEC R2
DONE:   LBR DONE
; ---- the interrupt: IIR, the character (which lets -INT go), Q on
        ALIGN 16
INTRET: LDXA
        RET
INTR:   DEC R2
        SAV
        DEC R2
        STR R2
        DEC R2
        SEX R1                  ; P = 1 here
        OUT 6
        DB 82h
        SEX R2
        INP 7
        SEX R1
        OUT 6
        DB 80h
        SEX R2
        INP 7
        SEQ
        INC R2
        LBR INTRET
