



                org 0f000h
boot: req
                ldi 0f0h
                phi R1
loop1: dec 1
                ghi R1
                bnz loop1
                seq
                ldi 0f0h
                phi R1
loop2: dec 1
                ghi R1
                bnz loop2
                br boot
