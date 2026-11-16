/* flip characters in 2513l obtained in the net with character positions inverted see readme */

#include <stdio.h>
#define CHARACTERS 64
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
			font[char_counter][row_counter]= c ;
		}
	}
	
	for(char_counter=CHARACTERS-1; char_counter >= 0; char_counter--)
	{
		for(row_counter=0; row_counter < ROWS; row_counter++)
		{
			putchar(font[char_counter][row_counter]); 
		}
	}
}


