PROJECT = bios

$(PROJECT).prg: $(PROJECT).asm
	cpp $(PROJECT).asm -o - | sed -e 's/^#.*//' > temp.asm
	rcasm -l -h -v -x -d 1802 temp >bios.lst
	mv temp.img $(PROJECT).img

clean:
	-rm $(PROJECT).lst
	-rm $(PROJECT).img
	-rm temp.asm

