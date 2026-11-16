PROJECT = sec1

$(PROJECT).prg: $(PROJECT).asm
	cpp $(PROJECT).asm -o - | sed -e 's/^#.*//' > temp.asm
	rcasm -l -v -x -h -d 1802 temp >$(PROJECT).lst
	mv temp.img $(PROJECT).img
	srec_cat orig_bios/bios.img -intel $(PROJECT).img -intel -o >$(PROJECT).s1
	srec_cat $(PROJECT).s1 -fill 0xff 0xf000 0x10000 -o -Intel >$(PROJECT).hex
	-rm $(PROJECT).s1
	srec_cat $(PROJECT).hex -Intel -crop 0xf000 0x10000 -offset -0xf000 -o -RAW >$(PROJECT).rom

clean:
	-rm $(PROJECT).lst
	-rm $(PROJECT).img
	-rm $(PROJECT).hex
	-rm $(PROJECT).rom
	-rm temp.asm

	
