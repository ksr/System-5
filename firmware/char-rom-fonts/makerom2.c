/* produce proper ASCII character generator rom from 2513_combined */
#include <stdio.h>
#define CHARACTERS 96
#define ROWS 8

main()
{
	int c;
	int col;
	int char_counter;
	int row_counter;
	int bit_count;
	int mask;
	unsigned char font [CHARACTERS][ROWS]; 

	for(char_counter=0; char_counter < CHARACTERS; char_counter++)
	{
		for(row_counter=0; row_counter < ROWS; row_counter++)
		{
			c=getchar();
			font[char_counter][row_counter]= (c <<3)  & 0xf8;
		}
	}

/* 0x00 - 0x1f */
	for(char_counter=0; char_counter <= 0x1f ; char_counter++)
		for(row_counter=0; row_counter < ROWS; row_counter++)
			putchar(0);
/* 0x20 - 0x7f */
	for(char_counter=0x20; char_counter <= 0x7f ; char_counter++)
	{
		putchar(0);
		for(row_counter=0; row_counter < ROWS-1; row_counter++)
			putchar(font[char_counter-0x20][row_counter]);
	}
}


