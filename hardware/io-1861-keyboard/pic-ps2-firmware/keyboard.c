#include <16f84a.h>
#fuses HS,NOWDT,NOPROTECT
#use delay(clock=4000000)
#use rs232(baud=9600, rcv=PIN_A0,PARITY=N,BITS=8)
#include <input.c>


#use FAST_IO (B)
outachar(char c){
	output_b(c);
	output_high(PIN_A2);
	delay_ms(1);
	output_low(PIN_A2);
}


main()
{
	int i;
	byte c;


	set_tris_b(0);
	set_tris_a(0);

	for(i=0;i<2;i++){
		output_high(PIN_A1);
		delay_ms(100);
		output_low(PIN_A1);
		delay_ms(100);
	}
//	outachar(0x41);
//	delay_ms(1000);

//	outachar(0x42);
//	delay_ms(1000);

	while(1){
		c=getc();
		outachar(c);
	}
}
