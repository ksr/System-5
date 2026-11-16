// Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-01
/*
   video-g-ps2 (2026-11-01) - the PS/2 controller of System-5's VIDEO-G 1.0 video cards (hardware/video-g/DESIGN.md
   sections 4 and 5; embedded/video-g-ps2/README.md). ONE sketch for the ATmega328P on both boards:

     TEXT board, IC10   a PS/2 KEYBOARD, translated to ASCII. The CPU reads a key with INP 1 when the bus -EF says one
                        waits (HBIOS's inchar, unchanged: BN3 then INP 1). The firmware drives the keyboard's LEDs.
     GFX board, IC11    a PS/2 MOUSE, its 3-byte packets. The CPU reads a byte with INP 7 when TEXT's status port
                        (INP 4) bit 1 says one waits. The mouse reports only while MOUSE-ON (OUT 4 bit 5) is 1.

   The strap on PD7 tells them apart: open (TEXT) = keyboard mode; 4.7k to GND (GFX, R6) = mouse mode.

   Adapted from YACC1-D's embedded/video-ps2 (the keyboard + mouse controller of YACC1's video card V2.0, revised after
   its design reviews V2-1..V2-18 and R2-10; copied, never modified). VIDEO-G keeps V2.0's data path to the CPU and
   drops the rest: one PS/2 port per chip instead of two, no command latch (-RDCMD, BUSY), no INTREQ, no SRC.
   Changes and the reasons for them: README.md, "Changes from V2.0".

   Pins (Arduino Uno numbering = the ATmega328P's port pins; DIP-28 pin in brackets):
                            TEXT board, IC10 (keyboard mode)          GFX board, IC11 (mouse mode)
     D0   PD0 RXD   [2]     FTX: FTDI header J5 pin 4                 FTX: FTDI header J3 pin 4
     D1   PD1 TXD   [3]     FRX: J5 pin 5                             FRX: J3 pin 5      (console 38400 8N1, bootloader)
     D2   PD2 INT0  [4]     KCLK: keyboard jack J4 pin 5, R9 4.7k     MCLK: mouse jack J2 pin 5, R4 4.7k
     D4   PD4       [6]     KDAT: J4 pin 1, R10 4.7k                  MDAT: J2 pin 1, R5 4.7k
     D6   PD6       [12]    LDDATA out: clocks the key latch IC9 and  LDDATA out: clocks the mouse latch IC12 and
                            sets KEY-READY (IC24B); RN2 10k pull-up   sets MOUSE-READY (IC13B); R3 10k pull-up
     D7   PD7       [13]    not connected: keyboard mode              MSTRAP, R6 4.7k to GND: mouse mode
     A0-A5 PC0-PC5 [23-28]  MD0-MD5 out  -> IC9 D inputs (INP 1)      MD0-MD5 out  -> IC12 D inputs (INP 7)
     D8, D9 PB0 PB1 [14,15] MD6, MD7 out                              MD6, MD7 out
     D10  PB2       [16]    KREADY in (IC24B Q)                       MREADY in (IC13B Q)
     D11  PB3       [17]    not connected                             MOUSEON in: control register IC19 Q5 (OUT 4 bit 5)
     D3 D5 D12 D13 = PD3 PD5 PB4 PB5 [5 11 18 19]: not connected on either board (inputs with pull-ups here)
     RESET          [1]     MRST: R7 10k, C27 from the FTDI DTR, and  MRST: R1 10k, C21 from the FTDI DTR, and
                            the bus -RESET through IC23 (7416, o.c.)  the bus -RESET through IC15 (74LS05, o.c.)
   The PS/2 lines are open drain: a pin is either an input (the board's 4.7k pull-up makes 1) or an output driving 0.

   The load protocol (the same on both boards; READY = KEY-READY on TEXT, MOUSE-READY on GFX):
     the firmware puts a byte on MD0-MD7 and pulses LDDATA low (it idles high, V2-7); the rising edge clocks the
     74HCT374 and sets READY (a 74HCT74 half with D = 1). The CPU's INP (1 or 7) drives the latch onto D0-D7 from about
     2 T to the end of the cycle and clears READY at TPB; -RESET clears it too. READY drives the bus -EF on TEXT (jumper
     KBD-EF) and the status port's bit 0 / bit 1.
     The firmware loads the next byte only when READY is 0 AND 1 ms has passed since READY last fell (a pin-change
     interrupt timestamps the fall): READY clears at TPB but the read enable lasts to the end of that cycle, and the
     bus driver's INP:n# holds TPB high for ~0.3 ms, so loading at once could change the byte under a read still going
     on. After each load READY is read back; still 0 means an INP was clearing it, and the same byte is loaded again.
     Driver rule (as V2.0's R2-10): INP 1 / INP 7 only after READY was seen 1 (EF3, or INP 4 bit 0 / bit 1).
*/

// ---------------------------------------------------------------- build options
#define KEYS_VT100 0        // 0: special keys as single bytes, as the old System-5 keyboard (the PAK-VI) sent them:
                            //    F1-F12 $80-$8B, Home Up PgUp Left 5 Right End Down PgDn Ins Del $90-$9A, Shift + $40
                            // 1: YACC1 V2.0's VT100 sequences (ESC [ A..D, H, F, 5~, 6~), Delete $7F, no F keys
#define DEBUG_AT_START 0    // 1: the console shows every PS/2 byte and every load from the start ('d' toggles it)

// ---------------------------------------------------------------- pins (Arduino numbers) and sizes
#define PIN_CLK 2           // PD2 INT0  PS/2 clock
#define PIN_DAT 4           // PD4       PS/2 data
#define PIN_LDDATA 6        // PD6       latch clock + READY set (idle high)
#define PIN_STRAP 7         // PD7       mode strap
#define PIN_READY 10        // PB2       KEY-READY / MOUSE-READY
#define PIN_MOUSEON 11      // PB3       MOUSE-ON (GFX)

#define QSIZE 64                     // the queue to the CPU
#define RXSIZE 64                    // the PS/2 receive ring
#define FRAME_TIMEOUT_US 2000UL      // a gap this long between clock edges restarts the frame
#define READ_GUARD_US 1000UL         // after READY falls (the CPU took a byte), wait this long before the next load
#define MOUSE_RETRY_MS 2000UL        // MOUSE-ON is 1 but no mouse started: try again this often
#define MOUSE_QUIET_US 25000UL       // a part packet followed by this much silence is dropped

#define LED_SCROLL 1                 // the keyboard's LED bits ($ED's argument)
#define LED_NUM 2
#define LED_CAPS 4

// The PS/2 pins by port bit (their PORT bits stay 0: output = drive low). SBI/CBI, so safe beside the interrupt.
#define CLK_LOW()     (DDRD |= _BV(PD2))
#define CLK_RELEASE() (DDRD &= ~_BV(PD2))
#define DAT_LOW()     (DDRD |= _BV(PD4))
#define DAT_RELEASE() (DDRD &= ~_BV(PD4))
#define DAT_IN()      (PIND & _BV(PD4))

bool mouse_mode;                     // from the strap: false = keyboard (TEXT), true = mouse (GFX)
bool debug_on = DEBUG_AT_START;

// ---------------------------------------------------------------- the PS/2 port (interrupt side)
volatile uint8_t rx_n, rx_bits, rx_ones;                 // the frame being received: bit number, data, ones counted
volatile uint8_t tx_on, tx_byte, tx_parity, tx_ack;      // host to device: sending, the byte, its parity, 1 = acked
volatile uint32_t last_edge;                             // micros() of the last clock edge
volatile uint8_t rx[RXSIZE], rx_head, rx_tail;
volatile uint16_t frame_errors, rx_overruns;

void ps2_isr() {                                         // every falling clock edge (INT0)
  uint8_t d = DAT_IN() ? 1 : 0;                          // the data bit first: it is valid only while the clock is low
  uint32_t now = micros();
  if (now - last_edge > FRAME_TIMEOUT_US) rx_n = 0;      // a stray or broken frame: start again
  last_edge = now;
  if (tx_on) {                                           // host to device: put the next bit while the clock is low
    if (rx_n < 8) { if ((tx_byte >> rx_n) & 1) DAT_RELEASE(); else DAT_LOW(); }
    else if (rx_n == 8) { if (tx_parity) DAT_RELEASE(); else DAT_LOW(); }
    else if (rx_n == 9) DAT_RELEASE();                   // the stop bit: released
    else { tx_ack = d ? 2 : 1; tx_on = 0; rx_n = 0; return; }   // the device's acknowledge bit (0 = acknowledged)
    rx_n++;
    return;
  }
  if (rx_n == 0) { if (d) return; rx_bits = 0; rx_ones = 0; }     // the start bit must be 0
  else if (rx_n <= 8) { rx_bits |= d << (rx_n - 1); rx_ones += d; }
  else if (rx_n == 9) rx_ones += d;                               // odd parity over data + parity
  else {                                                          // the stop bit
    if (d && (rx_ones & 1)) {
      uint8_t h = (rx_head + 1) % RXSIZE;
      if (h != rx_tail) { rx[rx_head] = rx_bits; rx_head = h; } else rx_overruns++;
    } else frame_errors++;
    rx_n = 0;
    return;
  }
  rx_n++;
}

int ps2_get() {                                          // the next received byte, or -1
  if (rx_head == rx_tail) return -1;
  uint8_t b = rx[rx_tail];
  rx_tail = (rx_tail + 1) % RXSIZE;
  return b;
}

bool ps2_send(uint8_t b) {                               // host to device; true when the device acknowledged
  uint8_t par = 1;                                       // odd parity: 1 when the byte has an even number of ones
  for (uint8_t i = 0; i < 8; i++) par ^= (b >> i) & 1;
  // Request to send: the clock low for 120 us. INT0 would fire on this edge of our own (it triggers on an output pin
  // too), so it is masked meanwhile and its flag cleared before the device's first clock: our edge can neither count
  // as the device's first clock (V2-3: the transmitter is still armed only after the 120 us) nor complete a frame the
  // device was half-way through (the device aborts that frame and sends it again later).
  EIMSK &= ~_BV(INT0);
  CLK_LOW();
  delayMicroseconds(120);
  noInterrupts();
  tx_byte = b; tx_parity = par; tx_ack = 0; rx_n = 0; tx_on = 1;
  interrupts();
  DAT_LOW();                                             // the start bit
  EIFR = _BV(INTF0);                                     // forget our own edge
  EIMSK |= _BV(INT0);
  CLK_RELEASE();                                         // a rising edge; the device now clocks the bits in
  uint32_t t0 = millis();
  while (tx_on && millis() - t0 < 20) { }
  DAT_RELEASE();
  bool ok = tx_ack == 1;
  noInterrupts(); tx_on = 0; rx_n = 0; interrupts();
  return ok;
}

uint8_t held[16], nheld;                                 // bytes that came while a command waited for its reply

int ps2_next() {                                         // the main loop's next byte: the held ones first, in order
  if (nheld) {
    uint8_t b = held[0];
    for (uint8_t i = 1; i < nheld; i++) held[i - 1] = held[i];
    nheld--;
    return b;
  }
  return ps2_get();
}

void ps2_flush() { noInterrupts(); rx_tail = rx_head; interrupts(); nheld = 0; }

static inline bool ps2_is_reply(uint8_t b) {             // what a device sends in answer to the host: acknowledge,
  return b == 0xFA || b == 0xFE || b == 0xEE || b == 0xAA || b == 0xFC || b == 0x00;   // resend, echo, BAT, ID
}

int ps2_wait(uint16_t wait_ms) {                         // the next REPLY byte within wait_ms, or -1 (R2-10): a scan
  uint32_t t0 = millis();                                // code or mouse byte that comes meanwhile is held for the loop
  do {
    int b;
    while ((b = ps2_get()) >= 0) {
      if (ps2_is_reply(b)) return b;
      if (nheld < sizeof held) held[nheld++] = b;
    }
  } while (millis() - t0 < wait_ms);
  return -1;
}

bool ps2_command(uint8_t b) {                            // send and expect $FA (acknowledge), one retry on $FE (resend);
  for (uint8_t i = 0; i < 2; i++) {                      // another reply byte (a stray $AA / $00) is skipped, for 50 ms
    if (!ps2_send(b)) continue;
    uint32_t t0 = millis();
    int r;
    do r = ps2_wait(50); while (r >= 0 && r != 0xFA && r != 0xFE && millis() - t0 < 50);
    if (r == 0xFA) return true;
    if (r != 0xFE) return false;
  }
  return false;
}

// ---------------------------------------------------------------- the queue to the CPU and the latch
uint8_t qbyte[QSIZE], qh, qt;
volatile uint32_t taken_us;                              // micros() when READY last fell: an INP took the byte
uint16_t load_retries;

uint8_t qfree() { return (qt + QSIZE - qh - 1) % QSIZE; }
void qput(uint8_t b) { if (qfree()) { qbyte[qh] = b; qh = (qh + 1) % QSIZE; } }

ISR(PCINT0_vect) { if (!(PINB & _BV(PB2))) taken_us = micros(); }   // PCINT2 = PB2 = READY: only its fall matters

static inline bool ready() { return PINB & _BV(PB2); }

void md_write(uint8_t b) {                               // MD0-MD5 = PC0-PC5, MD6 = PB0, MD7 = PB1; outputs all the time
  PORTC = (PORTC & 0xC0) | (b & 0x3F);                   // (nothing but the latch listens: no V2-9 release needed)
  PORTB = (PORTB & 0xFC) | (b >> 6);
}

void print_hex2(uint8_t b) { if (b < 0x10) Serial.print('0'); Serial.print(b, HEX); }

void feed_cpu() {                                        // the next queued byte into the latch once the CPU took the last
  if (qh == qt || ready()) return;
  noInterrupts(); uint32_t t = taken_us; interrupts();
  if (micros() - t < READ_GUARD_US) return;              // the INP that took the last byte may still be reading the latch
  md_write(qbyte[qt]);
  delayMicroseconds(1);
  PORTD &= ~_BV(PD6);                                    // LDDATA idles high (V2-7): a low pulse,
  delayMicroseconds(1);
  PORTD |= _BV(PD6);                                     // the latch and READY take its rising edge
  delayMicroseconds(1);
  if (ready()) {
    if (debug_on) { Serial.print(F("-> ")); print_hex2(qbyte[qt]); Serial.println(); }
    qt = (qt + 1) % QSIZE;
  } else {                                               // READY held clear: an INP is still going on (or READY is
    load_retries++;                                      // stuck): the same byte again after another guard time
    noInterrupts(); taken_us = micros(); interrupts();
  }
}

// ---------------------------------------------------------------- keyboard mode: set-2 scan codes -> ASCII
const uint8_t PROGMEM kmap[][3] = {           // {set-2 code, unshifted, shifted}: V2.0's US layout
  {0x0D, 9, 9}, {0x0E, '`', '~'}, {0x15, 'q', 'Q'}, {0x16, '1', '!'}, {0x1A, 'z', 'Z'},
  {0x1B, 's', 'S'}, {0x1C, 'a', 'A'}, {0x1D, 'w', 'W'}, {0x1E, '2', '@'}, {0x21, 'c', 'C'},
  {0x22, 'x', 'X'}, {0x23, 'd', 'D'}, {0x24, 'e', 'E'}, {0x25, '4', '$'}, {0x26, '3', '#'},
  {0x29, ' ', ' '}, {0x2A, 'v', 'V'}, {0x2B, 'f', 'F'}, {0x2C, 't', 'T'}, {0x2D, 'r', 'R'},
  {0x2E, '5', '%'}, {0x31, 'n', 'N'}, {0x32, 'b', 'B'}, {0x33, 'h', 'H'}, {0x34, 'g', 'G'},
  {0x35, 'y', 'Y'}, {0x36, '6', '^'}, {0x3A, 'm', 'M'}, {0x3B, 'j', 'J'}, {0x3C, 'u', 'U'},
  {0x3D, '7', '&'}, {0x3E, '8', '*'}, {0x41, ',', '<'}, {0x42, 'k', 'K'}, {0x43, 'i', 'I'},
  {0x44, 'o', 'O'}, {0x45, '0', ')'}, {0x46, '9', '('}, {0x49, '.', '>'}, {0x4A, '/', '?'},
  {0x4B, 'l', 'L'}, {0x4C, ';', ':'}, {0x4D, 'p', 'P'}, {0x4E, '-', '_'}, {0x52, '\'', '"'},
  {0x54, '[', '{'}, {0x55, '=', '+'}, {0x5A, 13, 13}, {0x5B, ']', '}'},
  {0x5D, '\\', '|'}, {0x66, 8, 8}, {0x76, 27, 27}, {0x7C, '*', '*'}, {0x7B, '-', '-'},
  {0x79, '+', '+'},
};
// The keypad's digit keys, and the grey editing keys (the same codes after E0): {code, character with Num Lock on,
// the PAK-VI's code for the editing function}. The PAK-VI numbered them by keypad position, $90 + (7 8 9 4 5 6 1 2 3 0 .)
const uint8_t PROGMEM kpad[][3] = {
  {0x6C, '7', 0x90}, {0x75, '8', 0x91}, {0x7D, '9', 0x92}, {0x6B, '4', 0x93}, {0x73, '5', 0x94}, {0x74, '6', 0x95},
  {0x69, '1', 0x96}, {0x72, '2', 0x97}, {0x7A, '3', 0x98}, {0x70, '0', 0x99}, {0x71, '.', 0x9A},
};
const uint8_t PROGMEM fkeys[12] = {0x05, 0x06, 0x04, 0x0C, 0x03, 0x0B, 0x83, 0x0A, 0x01, 0x09, 0x78, 0x07};  // F1..F12

bool lshift, rshift, lctrl, rctrl, brk, ext;
uint8_t leds;                                     // the lock states, as $ED's argument (LED_CAPS | LED_NUM | LED_SCROLL)
uint8_t locks_down;                               // lock keys held down now: their repeats do not toggle again
uint8_t skip;                                     // bytes of a Pause sequence (E1 ...) still to swallow

void send_leds() { if (ps2_command(0xED)) ps2_command(leds); }

int8_t kpad_find(uint8_t c) {
  for (uint8_t i = 0; i < sizeof kpad / sizeof kpad[0]; i++) if (pgm_read_byte(&kpad[i][0]) == c) return i;
  return -1;
}

// An editing or function key. k: $80-$8B F1-F12; $90-$9A Home Up PgUp Left 5 Right End Down PgDn Ins Del
void key_special(uint8_t k, bool shift) {
#if KEYS_VT100
  (void)shift;
  const char *s;
  switch (k) {
    case 0x91: s = "\x1b[A"; break;   case 0x97: s = "\x1b[B"; break;   case 0x95: s = "\x1b[C"; break;
    case 0x93: s = "\x1b[D"; break;   case 0x90: s = "\x1b[H"; break;   case 0x96: s = "\x1b[F"; break;
    case 0x92: s = "\x1b[5~"; break;  case 0x98: s = "\x1b[6~"; break;
    case 0x9A: qput(0x7F); return;                // Delete = DEL
    default: return;                              // F keys, Insert, keypad 5: nothing (as V2.0)
  }
  if (qfree() < 4) return;                        // a sequence goes in whole or not at all
  while (*s) qput(*s++);
#else
  qput(shift ? k + 0x40 : k);                     // one byte, as the PAK-VI sent it; Shift adds $40
#endif
}

void keyboard_plugged() {                         // $AA outside a command: a keyboard was plugged in or reset itself
  lshift = rshift = lctrl = rctrl = brk = ext = false; skip = 0; locks_down = 0;
  if (debug_on) Serial.println(F("keyboard: self-test passed (plugged in?)"));
  send_leds();                                    // it starts with its LEDs dark: show the lock states again
}

void keyboard_byte(uint8_t c) {
  if (skip) { skip--; return; }
  if (c == 0xE1) { skip = 7; return; }            // Pause/Break: E1 14 77 E1 F0 14 F0 77
  if (c == 0xE0) { ext = true; return; }
  if (c == 0xF0) { brk = true; return; }
  if (c == 0xAA) { keyboard_plugged(); return; }
  if (c == 0x00 || c == 0xEE || c == 0xFA || c >= 0xFC) { brk = ext = false; return; }   // overrun, echo, acks, errors
  bool up = brk, e = ext;
  brk = ext = false;
  if (c == 0x12 && e) return;                     // the fake shifts around the grey keys and Print Screen
  if (c == 0x12) { lshift = !up; return; }
  if (c == 0x59 && !e) { rshift = !up; return; }  // (E0 59 is a fake shift too)
  if (c == 0x14) { if (e) rctrl = !up; else lctrl = !up; return; }
  if (c == 0x11) return;                          // Alt, AltGr: no meaning here
  uint8_t lock = e ? 0 : c == 0x58 ? LED_CAPS : c == 0x77 ? LED_NUM : c == 0x7E ? LED_SCROLL : 0;  // E0 7E: Ctrl-Break
  if (lock) {                                     // a held key repeats its make code: only the first make toggles
    if (up) locks_down &= ~lock;
    else if (!(locks_down & lock)) { locks_down |= lock; leds ^= lock; send_leds(); }
    return;
  }
  if (up) return;                                 // other releases: nothing
  bool shift = lshift || rshift;
  int8_t k = kpad_find(c);
  if (e) {                                        // E0 xx: the grey keys
    if (c == 0x4A) qput('/');                     // keypad /
    else if (c == 0x5A) qput(13);                 // keypad Enter
    else if (k >= 0) key_special(pgm_read_byte(&kpad[k][2]), shift);
    return;                                       // GUI, Menu, Print Screen, multimedia keys: nothing
  }
  if (k >= 0) {                                   // the keypad: digits with Num Lock on, the editing keys with it off
    if (leds & LED_NUM) qput(pgm_read_byte(&kpad[k][1])); else key_special(pgm_read_byte(&kpad[k][2]), shift);
    return;
  }
  for (uint8_t i = 0; i < sizeof fkeys; i++)
    if (pgm_read_byte(&fkeys[i]) == c) { key_special(0x80 + i, shift); return; }
  uint8_t ch = 0;
  for (uint8_t i = 0; i < sizeof kmap / sizeof kmap[0]; i++)
    if (pgm_read_byte(&kmap[i][0]) == c) { ch = pgm_read_byte(&kmap[i][shift ? 2 : 1]); break; }
  if (!ch) return;
  bool caps = leds & LED_CAPS;
  if (caps && ch >= 'a' && ch <= 'z') ch -= 32;
  else if (caps && shift && ch >= 'A' && ch <= 'Z') ch += 32;
  if ((lctrl || rctrl) && ch >= '@' && ch <= '~') ch &= 0x1F;   // Ctrl-A..Z = $01-$1A, Ctrl-[ = ESC ...
  qput(ch);
}

void keyboard_reset() {
  lshift = rshift = lctrl = rctrl = brk = ext = false; skip = 0; leds = 0; locks_down = 0;
  if (ps2_command(0xFF)) ps2_wait(1000);          // the self-test answer ($AA), 0.3-0.75 s later
  send_leds();
}

// ---------------------------------------------------------------- mouse mode: MOUSE-ON, reset + enable, whole packets
uint8_t mpkt[3], mn;
bool mouse_running;                               // reset and reporting: MOUSE-ON is 1 and the start sequence worked
bool mouse_on_was;                                // MOUSE-ON at the last look
uint32_t mouse_try_ms;                            // millis() of the last start attempt

bool mouse_start() {
  ps2_flush(); mn = 0;                            // nothing from before the reset counts
  if (!ps2_command(0xFF)) return false;           // reset: $FA, then $AA and the device ID $00
  if (ps2_wait(1000) != 0xAA) return false;
  ps2_wait(100);
  if (!ps2_command(0xF4)) return false;           // enable data reporting
  nheld = 0;                                      // bytes held before its $FA were from before the reset
  return true;
}

void mouse_go() {                                 // MOUSE-ON rose (or a retry, or the mouse was plugged in again)
  mouse_running = mouse_start();
  mouse_try_ms = millis();
  if (debug_on) Serial.println(mouse_running ? F("mouse: reporting") : F("mouse: no answer"));
}

void mouse_stop() {                               // MOUSE-ON fell: quiet the mouse, drop what the CPU has not got
  mouse_running = false;
  ps2_command(0xF5);                              // disable data reporting
  ps2_flush(); mn = 0; qt = qh;                   // (a byte already in the latch stays there: README)
  if (debug_on) Serial.println(F("mouse: off"));
}

void mouse_byte(uint8_t b) {
  if (!mouse_running) return;
  if (mn == 0 && !(b & 0x08)) return;             // byte 1 always has bit 3 set: resynchronise
  mpkt[mn++] = b;
  if (mn == 3) {
    mn = 0;
    if (qfree() >= 3) { qput(mpkt[0]); qput(mpkt[1]); qput(mpkt[2]); }   // whole packets only
  }
}

void mouse_watch() {                              // every loop in mouse mode, after the received bytes are handled
  bool on = PINB & _BV(PB3);
  if (on != mouse_on_was) {
    mouse_on_was = on;
    if (on) mouse_go(); else mouse_stop();
  } else if (on && !mouse_running) {
    if (millis() - mouse_try_ms >= MOUSE_RETRY_MS) mouse_go();          // no mouse yet: try again now and then
  } else if (mn) {                                // a part packet: the rest comes within ~2 ms, or never
    noInterrupts(); uint32_t t = last_edge; interrupts();
    if (micros() - t > MOUSE_QUIET_US) {
      bool plugged = mn == 2 && mpkt[0] == 0xAA && mpkt[1] == 0x00;    // self-test passed + ID, then silence:
      mn = 0;                                                           // a mouse was plugged in or reset itself
      if (plugged && on) mouse_go();
    }
  }
}

// ---------------------------------------------------------------- start, the console, the main loop
// The mode strap. Read with the internal pull-up (20-50k), as the design says: open reads 1; against R6 (4.7k since
// 2026-11-02; it was 10k, which left the pin at 0.8-1.7 V) the pin sits at 0.4-0.95 V, inside the AVR's guaranteed 0
// (below 0.3 VCC = 1.5 V). A second test that does not depend on that ratio stays as belt and braces: charge the pin
// through the pull-up, turn the pull-up off and read it 2-3 us later: R6 empties it at once (4.7k x ~10 pF = 0.05 us);
// an open pin keeps its charge (leakage 1 uA at most). Either test seeing 0 means mouse mode.
uint8_t strap_pullup, strap_release;

bool strap_mouse() {
  pinMode(PIN_STRAP, INPUT_PULLUP);
  delay(2);
  strap_pullup = digitalRead(PIN_STRAP);
  noInterrupts();
  PORTD &= ~_BV(PD7);                             // pull-up off (the pin stays an input)
  delayMicroseconds(3);
  strap_release = (PIND & _BV(PD7)) ? 1 : 0;
  PORTD |= _BV(PD7);                              // pull-up on again
  interrupts();
  return !strap_pullup || !strap_release;
}

void start_all() {                                // as after a reset (also the console's 'r')
  qh = qt = 0;
  if (mouse_mode) {                               // the next mouse_watch() starts or quiets the mouse as MOUSE-ON says
    mouse_running = false; mn = 0;
    mouse_on_was = !(PINB & _BV(PB3));
  } else keyboard_reset();
}

void status() {
  Serial.print(mouse_mode ? F("mouse mode: MOUSE-ON ") : F("keyboard mode: LEDs "));
  if (mouse_mode) {
    Serial.print((PINB & _BV(PB3)) ? 1 : 0);
    Serial.print(mouse_running ? F(", reporting") : F(", stopped"));
  }
  else print_hex2(leds);
  Serial.print(F(", queue ")); Serial.print((qh + QSIZE - qt) % QSIZE);
  Serial.print(F(", READY ")); Serial.print(ready() ? 1 : 0);
  noInterrupts(); uint16_t fe = frame_errors, ov = rx_overruns; interrupts();
  Serial.print(F(", frame errors ")); Serial.print(fe);
  Serial.print(F(", overruns ")); Serial.print(ov);
  Serial.print(F(", load retries ")); Serial.println(load_retries);
}

void console() {                                  // one-letter commands on the FTDI console
  if (!Serial.available()) return;
  int c = Serial.read();
  if (c == 'd') { debug_on = !debug_on; Serial.println(debug_on ? F("debug on") : F("debug off")); }
  else if (c == '?') status();
  else if (c == 'r') { Serial.println(F("restart")); start_all(); }
}

void setup() {
  PORTD |= _BV(PD6); DDRD |= _BV(PD6);            // LDDATA: high, as the pull-up held it through the reset, then out
  md_write(0); DDRC |= 0x3F; DDRB |= 0x03;        // MD0-MD7 out
  PORTD &= ~(_BV(PD2) | _BV(PD4));                // the PS/2 lines released: inputs, no internal pull-ups (4.7k on
  DDRD &= ~(_BV(PD2) | _BV(PD4));                 // the board)
  pinMode(PIN_READY, INPUT);
  pinMode(3, INPUT_PULLUP); pinMode(5, INPUT_PULLUP); pinMode(12, INPUT_PULLUP); pinMode(13, INPUT_PULLUP);
  Serial.begin(38400);
  PORTD |= _BV(PD0);                              // RXD pull-up: no FTDI cable, no stray console bytes
  mouse_mode = strap_mouse();
  if (mouse_mode) { pinMode(PIN_STRAP, INPUT); pinMode(PIN_MOUSEON, INPUT); }   // R6 holds PD7; IC19 drives MOUSE-ON
  else pinMode(PIN_MOUSEON, INPUT_PULLUP);                                       // PB3 is open on TEXT
  PCMSK0 = _BV(PCINT2); PCIFR = _BV(PCIF0); PCICR |= _BV(PCIE0);                // READY's fall: an INP took the byte
  attachInterrupt(digitalPinToInterrupt(PIN_CLK), ps2_isr, FALLING);
  Serial.print(F("video-g-ps2 2026-11-01: "));
  Serial.print(mouse_mode ? F("mouse mode (GFX)") : F("keyboard mode (TEXT)"));
  Serial.print(F(", strap PD7 pull-up ")); Serial.print(strap_pullup);
  Serial.print(F(" release ")); Serial.println(strap_release);
  start_all();
  if (!mouse_mode) Serial.println(F("keyboard ready"));
}

void show_byte(const __FlashStringHelper *tag, uint8_t b) { Serial.print(tag); print_hex2(b); Serial.println(); }

void loop() {
  int b;
  console();
  if (mouse_mode) {
    while ((b = ps2_next()) >= 0) { if (debug_on) show_byte(F("ms "), b); mouse_byte(b); }
    mouse_watch();
  } else {
    while ((b = ps2_next()) >= 0) { if (debug_on) show_byte(F("kb "), b); keyboard_byte(b); }
  }
  feed_cpu();
}
