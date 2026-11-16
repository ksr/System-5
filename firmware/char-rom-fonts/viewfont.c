/*
	Binary font viewer
*/

#include <stdio.h>
#define CHARACTERS 128
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
			font[char_counter][row_counter]=c;
		}
	}
	
	for(char_counter=0; char_counter < CHARACTERS; char_counter++)
	{
		printf("\n\nChar = %x\n",char_counter);
		for(row_counter=0; row_counter < ROWS; row_counter++)
		{
			mask=128;
			for(col=0;col<8;col++)
			{
				if(font[char_counter][row_counter] & mask)
					printf("X");
				else
					printf("-");
				mask = mask/2;
			}
			printf("\n");
		}
	}
}


