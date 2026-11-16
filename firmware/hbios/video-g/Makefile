PROJECT = sec1
# VIDEO-G HBIOS: v1.0.4's Makefile, with Mike Riley's BIOS taken from ../v1.0.4/orig_bios (unchanged).
# build.py does the same with tools/asm1802.py instead of rcasm (same bytes).
BIOSIMG = ../v1.0.4/orig_bios/bios.img

$(PROJECT).prg: $(PROJECT).asm
	cpp $(PROJECT).asm -o - | sed -e 's/^#.*//' > temp.asm
	rcasm -l -v -x -h -d 1802 temp >$(PROJECT).lst
	mv temp.img $(PROJECT).img
	srec_cat $(BIOSIMG) -intel $(PROJECT).img -intel -o >$(PROJECT).s1
	srec_cat $(PROJECT).s1 -fill 0xff 0xf000 0x10000 -o -Intel >$(PROJECT).hex
	-rm $(PROJECT).s1
	srec_cat $(PROJECT).hex -Intel -crop 0xf000 0x10000 -offset -0xf000 -o -RAW >$(PROJECT).rom

clean:
	-rm $(PROJECT).lst
	-rm $(PROJECT).img
	-rm $(PROJECT).hex
	-rm $(PROJECT).rom
	-rm temp.asm
