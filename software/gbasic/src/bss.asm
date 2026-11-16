; GBASIC - RAM.  The program area starts right after the code (prog, in gbasic.asm) and ends at MEMTOP (6900);
; above it, at fixed places, the variables, buffers and stacks.  Nothing here is in the file.
;
;   6900-69BF varvals   6A00-6ABF varnames  (page aligned, 96 names)      6B10-6BFF FOR/GOSUB stack
;   6C00-6C7F LOAD's read buffer            6C80-6CFF the typed line       6D00-6DFF tokens of a line
;   6E00-6EFF the zero page of variables    6F00-6FFF the machine stack (R2 from 6FFF down)

            org     MEMTOP
varvals:    ds      2 * MAXVARS         ; page aligned: slot * 2 is the low byte
            org     MEMTOP + 0c0h
namebuf:    ds      20                  ; a file name
direntry:   ds      32                  ; FILES: one directory entry
            org     MEMTOP + 100h
varnames:   ds      2 * MAXVARS         ; letter, second character (bit 7: an array)
            org     MEMTOP + 210h
cstack:     ds      240                 ; FOR frames (10 bytes) and GOSUB frames (5 bytes)
cstack_end:
loadrb:     ds      128                 ; 6C00
linebuf:    ds      128                 ; 6C80, within one page
tokbuf:     ds      256                 ; 6D00, page aligned
zp:                                     ; 6E00: one page of variables (cleared at start)
argptr:     ds      2                   ; the command line
rndseed:    ds      2
outmode:    ds      1                   ; 0 = screen, 1 = into the buffer at outptr (SAVE)
outptr:     ds      2
locptr:     ds      2                   ; LOCATE: where the next character goes (0 = the console)
column:     ds      1                   ; the console's column
keybuf:     ds      1                   ; a key taken by the break check
curline:    ds      2                   ; the line running (0 = direct mode)
contok:     ds      1                   ; CONT allowed; conttp and contline follow
conttp:     ds      2
contline:   ds      2
numflag:    ds      1
lineno:     ds      2
tklen:      ds      1
vname:      ds      2
nvars:      ds      1
progend:    ds      2                   ; the program's end mark
arrend:     ds      2                   ; the first free byte above the arrays
memlim:     ds      2                   ; the program must end below this (MEMTOP; lower during LOAD)
loading:    ds      1
lastnum:    ds      2                   ; LOAD: the last line number put in
csp:        ds      2                   ; the FOR/GOSUB stack
dataptr:    ds      2                   ; READ: where the next item is (0 = from the start); dataline follows
dataline:   ds      2
prflag:     ds      1
inqmark:    ds      1
intp:       ds      2
inptr:      ds      2
rn_start:   ds      2                   ; RENUM; rn_step follows
rn_step:    ds      2
vgstat:     ds      1                   ; VIDEO-G status at start (0 = no VIDEO-G)
gfxok:      ds      1                   ; 1 = the GFX board is there
gheight:    ds      2                   ; 200 or 256 lines
ctrl:       ds      1                   ; what was last written to the control register
pen:        ds      1                   ; 0 erase, 1 draw, 2 invert
gfill:      ds      1
gx:         ds      2                   ; the graphics cursor; gx, gy and argv are copied together by LINE
gy:         ds      2
argv:       ds      12
lx0:        ds      2                   ; LINE's ends (lx0, ly0, lx1, ly1 together)
ly0:        ds      2
lx1:        ds      2
ly1:        ds      2
lddx:       ds      2
lddy:       ds      2
lsx:        ds      1
ew:         ds      2                   ; ELLIPSE
ewp:        ds      2
ey:         ds      2
esp:        ds      8                   ; a row's spans: left, right (and a second left, right)
erow:       ds      2
eA:         ds      4
eB:         ds      4
eT:         ds      4
eerr:       ds      4
eAy:        ds      4
eA2:        ds      4
eB2:        ds      4
eBx:        ds      4
eone:       ds      4
fileopen:   ds      1
fdptr:      ds      2
lcount:     ds      1
zp_used:
