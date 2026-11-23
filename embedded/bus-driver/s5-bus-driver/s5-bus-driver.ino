/*
 * s5-bus-driver.ino - firmware for the System-5 bus driver cards: BUSDRV-B (hardware/bus-driver/kicad/rev-b, the
 * 30-pin card, built) and BUSDRV-C (hardware/bus-driver/kicad/rev-c, the 36-pin card, drawn). One sketch for both.
 * Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-06. After Ken's YACC1 bus-driver.ino.
 * BUSDRV-C added 2026-11-20 (its DESIGN.md, proposals 1-8).
 *
 * Arduino Nano + two MCP23017 (I2C 0x20 = U1, 0x21 = U2) wired straight onto the 30-pin System-5 bus. BUSDRV-C has a
 * third (0x22 = U3) for the 36-pin extension, the DEBUG cable and seven more spares, CLK OUT on the Nano's D9 and two
 * probe inputs (D8, A1). WHICH BOARD: when the bus has power the sketch looks for U3 at 0x22; found = BUSDRV-C. U1 and
 * U2 are pin for pin the same on both, so everything BUSDRV-B does is unchanged; the BUSDRV-C commands answer
 * "Error: needs BUSDRV-C" on a Rev B.
 *
 * Wire protocol (the same as the YACC1 bus driver, so tools carry over):
 *   host -> card : CMD:OPERAND#            operands are DECIMAL unless noted; no line ending needed
 *   card -> host : optional "Data: ..." lines, "Complete" or "Error: ...", then the prompt ">>"
 *   A banner line is printed before the first prompt; the host looks for "s5-bus-driver" and "blocks-".
 *     BUSDRV-B: s5-bus-driver blocks-1 io-2 clk-1 walk-1 2026-11-22 BUSDRV-B
 *     BUSDRV-C: s5-bus-driver blocks-1 io-2 clk-2 ext-1 mode-2 load-1 probe-1 walk-1 2026-11-22 BUSDRV-C
 *     with the bus off the board is not known yet: "... clk-1 walk-1 2026-11-22 (bus off: board not known yet)"; the note
 *     printed when the bus comes up names the board, and so does STATUS on a BUSDRV-C.
 *   Signal names starting with '-' are active low: "-MRD:1#" asserts -MRD (drives it low).
 *
 * Safety rules built in (see hardware/bus-driver/kicad/rev-b/README.md):
 *   - At reset the card is a MONITOR: every expander pin is an input. It drives the bus only after MASTER:1#,
 *     which is refused if TPA/TPB are seen toggling (a CPU is running) or the bus has no power.
 *     BUSDRV-B cannot tell a stopped CPU card from an empty slot: pull the CPU card before MASTER:1#.
 *     BUSDRV-C also refuses while its own clock runs, and when the DEBUG cable's CLOCK follows CLK OUT (a CPU Rev D
 *     is cabled to it: the test costs that CPU eight clock edges).
 *   - Open-collector lines (-RESET, -INT, -EF; on BUSDRV-C also -EF1, -EF2, -EF3, -PAUSE, -DMAIN) are only ever
 *     pulled low or released (pin made an input). WALK keeps to that too.
 *   - While bus +5V is off (A0 / BUS_SENSE low) the expanders are held in reset by releasing nothing that could
 *     back-feed them: XRST (D4) low, I2C stopped and its pins inputs without pull-ups.
 *   - MCP23017 GPA7/GPB7 are output-only on current silicon: they are spare outputs, never bus signals.
 *
 * Commands (case sensitive):
 *   HELP:0#                    list commands
 *   STATUS:0#                  "Data: bus=on|off mode=MONITOR|MASTER"; BUSDRV-C adds " board=C cpu=RUN|RESET|PAUSE|LOAD
 *                              clk=hz" (cpu: from -RESET and -PAUSE as they are on the bus; clk 0 = stopped)
 *   MASTER:1# / MASTER:0#      take / give up the bus (MASTER:0 makes every pin an input again)
 *   SNAP:0#                    "Data: D=hh A=hh TPA=0 TPB=0 -MRD=1 -MRW=1 -VMA=1 Q=0 N=0 -RESET=1 -INT=1 -EF=1 SP=x"
 *                              (levels as seen on the bus; active-low names show the pin level, 1 = inactive)
 *                              BUSDRV-C adds " -EF1=1 -EF2=1 -EF3=1 -PAUSE=1 -DMAIN=1 SC0=1 DBG=csx S5=hh": DBG the DEBUG
 *                              cable's CLOCK, SC0, SC1 (three digits), S5 the levels on SPARE5-9 (bits 0-4)
 *   WATCH:ms#                  print a SNAP line on every change for ms milliseconds (0 = until any key)
 *   <signal>:0|1#              one bus line: TPA TPB -MRD -MRW -VMA Q -RESET -INT -EF            (MASTER only;
 *                              the open-collector -RESET -INT -EF also in MONITOR: 1 pulls low, 0 releases)
 *   N:n#                       N2..N0 = n (0..7)                                                (MASTER only)
 *   WR-ADDRBUS:n# RD-ADDRBUS:0#   the 8 address lines as they are                                 (WR: MASTER)
 *   WR-DATABUS:n# RD-DATABUS:0# DATABUS-RD-MODE:1#                                               (WR: MASTER)
 *   RDMEM:addr#                1802 memory read cycle  -> "Data: n"                             (MASTER only)
 *   WRMEM:addr,val#            1802 memory write cycle                                          (MASTER only)
 *   RDBLK:addr,count#          count 1..64 bytes -> "Data: hh hh ..."                           (MASTER only)
 *   WRBLK:addr,count,hh..#     count 1..32 bytes, 2 hex digits each, no spaces                  (MASTER only)
 *   OUT:n,val#                 1802 OUT n: val on the data bus, -MRD low, N=n, TPA and TPB pulses (MASTER only)
 *   INP:n#                     1802 INP n: N=n, TPA pulse, TPB high, read the data bus -> "Data: n" (MASTER only)
 *   INBLK:n,count#             count 1..64 INPs from port n -> "Data: hh hh ..."               (MASTER only)
 *   OUTBLK:n,count,hh..#       count 1..32 OUTs to port n, 2 hex digits each, no spaces         (MASTER only)
 *   SPARE:mask#                the spare outputs: bits 0..3 = SPARE1..4 (J2). BUSDRV-C: bits 4..8 = SPARE5..9 (those
 *                              SPDIR has made outputs), bits 9..10 = SPARE10..11 (J3). Works in either mode
 *   XRST:0#                    pulse the expanders' reset (every pin back to input; mode becomes MONITOR)
 *   CLK:n#                     MONITOR, clock stepping. n clock edges; after each the bus is read, and a line "T e ua ub va
 *                              vb" (e decimal, the GPIO ports in hex; BUSDRV-C: "T e ua ub va vb wa wb", U3's too, with
 *                              the DEBUG cable's CLOCK bit shown as 0: it changes on every edge) is
 *                              printed when it changed, then "Data: e" (edges done). Any key stops it.
 *                              software/busdrv/cputrace.py decodes the lines.
 *                              BUSDRV-B (clk-1): each edge is a rising edge on SPARE1 (J2 pin 1), wired to CPU Rev A's
 *                              IC8 pin 3 (the 74LS74 that halves the oscillator into the 1802's CLOCK).
 *                              BUSDRV-C (clk-2): each edge is one change of CLK OUT (D9), which the DEBUG cable takes to
 *                              CPU Rev D's EXT CLK (its JP1 on EXT). A steady clock is stopped first.
 *   16 edges are one machine cycle either way.
 *   WALK:pin,level#            MONITOR, CPU card out (walk-1, 2026-11-21): ONE bus line driven alone, to find shorts
 *                              between bus lines. Every bus pin is an input with its expander pull-up on (100k: a line
 *                              the backplane does not hold then rests high); the pin is driven to level 0 or 1, the
 *                              ports are read, and the pin is an input again with the pull-ups off: about a millisecond
 *                              in all. pin = chip * 16 + port * 8 + bit of a bus line (U1 = chip 0, port A = 0; e.g. 20 =
 *                              U2 GPA4 = -MRD; software/busdrv/s5busdrv.py has the table). level 2 drives nothing: the
 *                              lines at rest. -> "Data: ua ub va vb" (the GPIO ports as read, hex; BUSDRV-C: "... wa wb").
 *                              A pin that does not reach its level (held the other way: a short to a supply, a card
 *                              driving it) is let go at once, two expander transactions after it was driven, and the
 *                              ports are read after that, so its own bit shows it did not follow. Afterwards the pin
 *                              is as it was (a line this card was holding low is low again). Level 1 is refused
 *                              on an open-collector line. Refused in MASTER mode and whenever MASTER:1# would be: TPA /
 *                              TPB toggling, or (BUSDRV-C) its clock running or a CPU card on the DEBUG cable.
 *                              software/busdrv/bringup.py's plan "shorts" walks every line and names the shorts.
 *
 * BUSDRV-C only (ext-1, mode-2, load-1, clk-2, probe-1); all work in MONITOR mode, with the CPU card in place:
 *   -EF1 -EF2 -EF3 -PAUSE -DMAIN :0|1#   the extension's open-collector lines: 1 pulls low, 0 releases. SC0 is read only.
 *   SPDIR:mask#                bits 0..4: SPARE5..9 are outputs (1) or inputs (0, as after XRST)
 *   SPIN:0#                    "Data: n": the levels on SPARE5..9 (bits 0..4)
 *   DBG:0#                     "Data: CLOCK=c SC0=s SC1=x": the DEBUG cable's three inputs (pulled up: 111 with no cable)
 *   DBG:1#                     eight clock edges, and whether the cable's CLOCK follows them: "Data: CLK OUT reaches the
 *                              1802" or an error (no cable, or the CPU card's JP1 not on EXT)
 *   MODE:n#                    the 1802's mode from -RESET and -PAUSE: 0 RUN (both released), 1 RESET (-RESET low),
 *                              2 PAUSE (-PAUSE low), 3 LOAD (both low). Both lines are low together only for LOAD (that
 *                              sets CPU Rev D's LOADED flag): every other change passes through RUN or RESET. LOAD always
 *                              goes through RESET first, so R(0) = 0000. With the clock stopped, RESET and LOAD give the
 *                              1802 32 clock edges while -RESET is low. PAUSE waits (up to 0.5 s) to see -RESET high
 *                              on the bus first: the CPU card's DS1813 holds it low 150 ms after it is let go.
 *                              4 BOOT (mode-2, 2026-11-22): a boot reset, -RESET and -DMAIN low together with -PAUSE
 *                              high: CPU Rev D clears its LOADED flag, so MODE:0# after it starts the machine in the
 *                              EPROM, as the card's own RESET/RUN switch and the front panel's RESET button do. Refused
 *                              while -PAUSE is low on the bus (it would be LOAD mode with a DMA request). STATUS shows
 *                              cpu=RESET; every other MODE lets -DMAIN go before anything else.
 *   DMA:val#                   LOAD mode: one byte into M(R(0)) by a DMA IN cycle -> "Data: aaaa" (the address, hex)
 *   LOADBLK:count,hh..#        LOAD mode: count 1..32 bytes -> "Data: count aaaa" (aaaa = the first byte's address, hex)
 *   CLKHZ:hz#                  a steady clock on CLK OUT, 1..2000000 Hz -> "Data: hz" (the rate Timer 1 can make)
 *   CLKSTOP:0#                 stop it: CLK OUT holds its level, for CLK:n and the LOAD commands
 *   PROBE:0#                   "Data: P1=x P2=y": the two probe inputs (J2) now
 *   PCOUNT:ms#                 count the edges on both probes for ms (1..10000) -> "Data: P1=n P2=m" (by interrupt:
 *                              good to some tens of kHz, not measured)
 *   PTIME:ms#                  PROBE1 by Timer 1's input capture, waiting up to ms (default 1000, at most 4000) for
 *                              rising, falling, rising -> "Data: period_ns=n high_ns=m" (62.5 ns steps; clock stopped)
 *   PDELAY:e#                  one edge on CLK OUT, and the time to PROBE1's next falling (0) or rising (1) edge ->
 *                              "Data: ns" (62.5 ns steps, up to 4 ms; clock stopped). With PROBE1 on CLK OUT itself
 *                              it gives the measurement's own delay: subtract that.
 *
 * LOAD mode by the clock (DESIGN.md, option B; CPU Rev D, DEBUG cable on, its JP1 on EXT): the Nano is the 1802's
 * clock, one edge at a time, and reads the bus between edges. For each byte: SC0 high (an idle cycle); -DMAIN low;
 * clock until SC0 falls (the 1802 has taken the request: this is the DMA cycle); -DMAIN released at once, so that one
 * DMA cycle follows and no more; -MRD seen high (the memory is off the data lines); the byte on D0-D7; clock until
 * -MRW has gone low and come back; D0-D7 released; clock until SC0 is high again (were it not, a second DMA cycle
 * has run: an error). The address of the write is read on the way (high byte while TPA is high, low byte while -MRW
 * is low). Every step checks what it expects and says what it found instead.
 *
 * 1802 bus cycle as run here (memory cards latch A8-A15 from A0-A7 while TPA is high, see memory/REVIEW.md):
 *   A0-A7 = high byte, TPA high, TPA low; A0-A7 = low byte; -VMA low;
 *   read : -MRD low, TPB high, sample D0-D7, TPB low, -MRD high
 *   write: D0-D7 = data, -MRW low, TPB high, TPB low, -MRW high, D0-D7 released
 *   -VMA high.   Each step is an I2C write (400 kHz), so a byte takes roughly 1 ms; timing is far slower than an
 *   1802 but every edge is in 1802 order, which is what the static cards need.
 *   TPB: the 6845 card's CRTC takes TPB as its E and answers only while E is high; it latches a write as E falls,
 *   so -MRW stays low until after TPB (the 1802 itself raises -MRW first: timing finding T2).
 * I/O cycles (the IDE card decodes N0-N2 and takes the direction from -MRD; its strobe window uses TPA and TPB):
 *   OUT: D0-D7 = data, -MRD low (an 1802 OUT is a memory read), N = port, TPA pulse, TPB pulse, N = 0, -MRD high
 *   INP: N = port, TPA pulse, TPB high, sample D0-D7, TPB low, N = 0
 *   -VMA stays high, so no memory card answers the -MRD of an OUT.
 *   Before 2026-10-11 memory cycles had no TPB and OUT/INP had no -MRD or TPA: the CRTC never answered and the IDE
 *   card read from the drive (into the bus driver's own data) on every OUT. Found with software/busdrv/fwsim.py,
 *   which runs these same steps against the cards' netlists. Keep fwsim.py in step with any change here.
 */
#include <Wire.h>

#define BAUD 115200
#define PROMPT ">>"
#define BLOCK_MAX 64
#define WBLOCK_MAX 32

// Nano pins (gen/netlist.py of each board). D5, D8, D9 and A1 are not connected on BUSDRV-B.
#define PIN_INT_U1 2
#define PIN_INT_U2 3
#define PIN_XRST 4
#define PIN_INT_U3 5          // BUSDRV-C
#define PIN_PROBE1 8          // BUSDRV-C: PB0 = ICP1, Timer 1's input capture
#define PIN_CLK 9             // BUSDRV-C: PB1 = OC1A, CLK OUT (through R7 to J2 and the DEBUG header J4)
#define PIN_PROBE2 A1         // BUSDRV-C: PC1 = PCINT9
#define PIN_SENSE A0
#define SENSE_ON 700          // ADC counts: bus +5V through 10k/100k reads about 930; off reads near 0

// MCP23017 registers, IOCON.BANK = 0
#define IODIRA 0x00
#define GPINTENA 0x04
#define IOCON 0x0A
#define GPPUA 0x0C
#define GPIOA 0x12
#define OLATA 0x14
const uint8_t ADDR[3] = {0x20, 0x21, 0x22};

// Where each bus signal is: chip (0 = U1, 1 = U2, 2 = U3), port (0 = A, 1 = B), bit
struct Sig { const char *name; uint8_t chip, port, bit, flags; };
#define LOW_ACTIVE 1          // name starts with '-'
#define OPEN_COLL 2           // only ever pulled low or released
const Sig SIGS[] = {
  {"TPA", 1, 0, 2, 0}, {"TPB", 1, 0, 3, 0}, {"-MRD", 1, 0, 4, LOW_ACTIVE}, {"-MRW", 1, 0, 5, LOW_ACTIVE},
  {"-VMA", 1, 0, 6, LOW_ACTIVE}, {"Q", 1, 1, 0, 0}, {"-RESET", 1, 1, 1, LOW_ACTIVE | OPEN_COLL},
  {"-INT", 1, 1, 2, LOW_ACTIVE | OPEN_COLL}, {"-EF", 1, 1, 3, LOW_ACTIVE | OPEN_COLL},
  {"-EF1", 2, 0, 0, LOW_ACTIVE | OPEN_COLL}, {"-EF2", 2, 0, 1, LOW_ACTIVE | OPEN_COLL},       // BUSDRV-C: U3
  {"-EF3", 2, 0, 2, LOW_ACTIVE | OPEN_COLL}, {"-PAUSE", 2, 0, 3, LOW_ACTIVE | OPEN_COLL},
  {"-DMAIN", 2, 0, 4, LOW_ACTIVE | OPEN_COLL},
};
const uint8_t NSIGS = sizeof(SIGS) / sizeof(SIGS[0]);
// data bus: D0-D6 = U1 GPA0-6, D7 = U2 GPA0.  address bus: A0-A6 = U1 GPB0-6, A7 = U2 GPA1.  N0-N2 = U2 GPB4-6.
// spares: SPARE1 = U1 GPA7, SPARE2 = U1 GPB7, SPARE3 = U2 GPA7, SPARE4 = U2 GPB7 (output-only pins)
// BUSDRV-C, U3: GPA0-4 -EF1 -EF2 -EF3 -PAUSE -DMAIN, GPA5 SC0 (read only), GPA6 SPARE5, GPA7 SPARE10 (output only);
//               GPB0-2 the DEBUG cable's CLOCK, SC0, SC1 (inputs, pulled up), GPB3-6 SPARE6-9, GPB7 SPARE11 (output only)
#define VA_A7 0x02            // U2 port A as read
#define VA_TPA 0x04
#define VA_MRD 0x10
#define VA_MRW 0x20
#define VB_RESET 0x02         // U2 port B
#define WA_PAUSE 0x08         // U3 port A
#define WA_DMAIN 0x10
#define WA_SC0 0x20

// WALK: the bus lines of each port [chip][port] (not the spares, not the DEBUG inputs), and which of them are open collector
const uint8_t BUSPINS[3][2] = {{0x7F, 0x7F}, {0x7F, 0x7F}, {0x3F, 0x00}};
const uint8_t OCPINS[3][2] = {{0x00, 0x00}, {0x00, 0x0E}, {0x1F, 0x00}};

uint8_t olat[3][2];           // output latch shadows [chip][port]
uint8_t iodir[3][2];          // direction shadows: 1 = input
uint8_t nchips = 2;           // 3 on BUSDRV-C
uint8_t spdir = 0;            // BUSDRV-C: SPARE5..9 outputs (bits 0..4)
bool busOn = false, master = false, i2cUp = false, revC = false;
bool loadSynced = false;      // LOAD mode: the clock is ours and the 1802 is making idle cycles
unsigned long clkHz = 0;      // the steady clock on CLK OUT; 0 = stopped (D9 a plain output)
volatile unsigned long pcnt[2];
const __FlashStringHelper *why;   // what a LOAD step found instead of what it expected
String command;

// ---------------------------------------------------------------- MCP23017 access
void wr(uint8_t chip, uint8_t reg, uint8_t v) {
  Wire.beginTransmission(ADDR[chip]); Wire.write(reg); Wire.write(v); Wire.endTransmission();
}
uint8_t rd(uint8_t chip, uint8_t reg) {
  Wire.beginTransmission(ADDR[chip]); Wire.write(reg); Wire.endTransmission(false);
  Wire.requestFrom(ADDR[chip], (uint8_t)1); return Wire.available() ? Wire.read() : 0xFF;
}
void putLat(uint8_t c, uint8_t p) { wr(c, OLATA + p, olat[c][p]); }
void putDir(uint8_t c, uint8_t p) { wr(c, IODIRA + p, iodir[c][p]); }
uint8_t gpio(uint8_t c, uint8_t p) { return rd(c, GPIOA + p); }
void gpio2(uint8_t c, uint8_t *ab) {          // GPIOA then GPIOB in one sequential read (IOCON.SEQOP = 0)
  Wire.beginTransmission(ADDR[c]); Wire.write(GPIOA); Wire.endTransmission(false);
  Wire.requestFrom(ADDR[c], (uint8_t)2); ab[0] = Wire.available() ? Wire.read() : 0xFF; ab[1] = Wire.available() ? Wire.read() : 0xFF;
}

// Every pin an input except the output-only spares (which keep their latch value) and, on BUSDRV-C, the spares
// SPDIR has made outputs. That lets go of every open-collector line too.
void allInputs() {
  for (uint8_t c = 0; c < nchips; c++)
    for (uint8_t p = 0; p < 2; p++) {
      iodir[c][p] = 0x7F;
      if (c == 2) iodir[c][p] = p ? (0x07 | ((~(spdir >> 1) & 0x0F) << 3)) : (0x3F | ((spdir & 1) ? 0 : 0x40));
      putDir(c, p);
    }
  master = false; loadSynced = false;
}

void expandersInit() {
  Wire.beginTransmission(ADDR[2]); revC = Wire.endTransmission() == 0; nchips = revC ? 3 : 2;   // U3 answers: BUSDRV-C
  spdir = 0;
  for (uint8_t c = 0; c < nchips; c++) {
    wr(c, IOCON, 0x40);                       // MIRROR: INTA covers both ports; BANK 0; INT active-low push-pull
    wr(c, GPPUA, 0); wr(c, GPPUA + 1, c == 2 ? 0x07 : 0);   // no pull-ups: the bus has its own levels. (U3: the three
    olat[c][0] = olat[c][1] = 0; putLat(c, 0); putLat(c, 1);   //  DEBUG inputs are pulled up, so no cable reads 111)
  }
  allInputs();
}

// ---------------------------------------------------------------- BUSDRV-C: the clock on D9 (Timer 1, OC1A)
inline void clkEdge() { PINB = _BV(PB1); }    // one change of CLK OUT = one edge of the 1802's clock (the pin an output)

void clkStop() {
  if (clkHz) {
    if (PINB & _BV(PB1)) PORTB |= _BV(PB1); else PORTB &= ~_BV(PB1);    // the pin keeps the level it has
    clkHz = 0;
  }
  TCCR1A = 0; TCCR1B = 0;
}

unsigned long clkStart(unsigned long hz) {    // -> the rate set: 16 MHz / (2 * prescaler * count)
  static const uint16_t PRE[5] = {1, 8, 64, 256, 1024};
  for (uint8_t i = 0; i < 5; i++) {
    unsigned long half = F_CPU / 2 / PRE[i], top = (half + hz / 2) / hz;
    if (top >= 1 && top <= 65536UL) {
      TCCR1A = 0; TCCR1B = 0; TCNT1 = 0; OCR1A = top - 1;
      TCCR1A = _BV(COM1A0); TCCR1B = _BV(WGM12) | (i + 1);   // CTC, OC1A toggles on each match; CS1 = the prescaler
      clkHz = (half + top / 2) / top; return clkHz;          // (to the nearest Hz)
    }
  }
  return 0;
}

bool clockOurs() {                            // the DEBUG cable's CLOCK follows eight edges of CLK OUT and holds between
  uint8_t last = gpio(2, 1) & 1;
  for (uint8_t i = 0; i < 8; i++) {
    clkEdge(); uint8_t a = gpio(2, 1) & 1, b = gpio(2, 1) & 1;
    if (a == last || b != a) return false;    // (a clock running by itself passes this once in 65,000)
    last = a;
  }
  return true;
}

ISR(PCINT0_vect) { pcnt[0]++; }               // PROBE1 (D8)
ISR(PCINT1_vect) { pcnt[1]++; }               // PROBE2 (A1)

// ---------------------------------------------------------------- power handling
void busPower() {
  bool on = analogRead(PIN_SENSE) > SENSE_ON;
  if (on == busOn) return;
  busOn = on;
  if (on) {
    pinMode(PIN_XRST, INPUT);                  // R3 pulls XRST up to bus +5V: expanders run
    delay(2);
    Wire.begin(); Wire.setClock(400000);
    digitalWrite(SDA, LOW); digitalWrite(SCL, LOW);   // AVR: drop the internal pull-ups; R1/R2 go to bus +5V
    i2cUp = true; expandersInit();
    if (revC) { digitalWrite(PIN_CLK, LOW); pinMode(PIN_CLK, OUTPUT); }
    Serial.print(F("Note: bus power on, MONITOR mode, BUSDRV-")); Serial.println(revC ? 'C' : 'B');
  } else {
    if (i2cUp) { Wire.end(); i2cUp = false; }
    pinMode(SDA, INPUT); pinMode(SCL, INPUT);  // no back-feed into the unpowered expanders
    pinMode(PIN_XRST, OUTPUT); digitalWrite(PIN_XRST, LOW);
    clkStop(); pinMode(PIN_CLK, INPUT);        // nor into an unpowered CPU card's EXT CLK
    master = false; loadSynced = false;
    Serial.println(F("Note: bus power off"));
  }
}

// ---------------------------------------------------------------- bus primitives (MASTER)
void setBit(uint8_t c, uint8_t p, uint8_t b, bool v) { if (v) olat[c][p] |= (1 << b); else olat[c][p] &= ~(1 << b); }

void sigWrite(const Sig &s, bool asserted) {
  bool level = (s.flags & LOW_ACTIVE) ? !asserted : asserted;
  if (s.flags & OPEN_COLL) {                   // pull low (output 0) or release (input); never drive high
    setBit(s.chip, s.port, s.bit, false); putLat(s.chip, s.port);
    if (level) iodir[s.chip][s.port] |= (1 << s.bit); else iodir[s.chip][s.port] &= ~(1 << s.bit);
    putDir(s.chip, s.port);
  } else {
    setBit(s.chip, s.port, s.bit, level); putLat(s.chip, s.port);
  }
}
const Sig *sigFind(const String &n) {
  for (uint8_t i = 0; i < NSIGS; i++) if (n == SIGS[i].name) return &SIGS[i];
  return 0;
}
void sig(const char *n, bool asserted) { sigWrite(*sigFind(n), asserted); }

void addrOut(uint8_t v) {                     // A0-A6 on U1 GPB0-6 (SPARE2 on bit 7 kept), A7 on U2 GPA1
  olat[0][1] = (olat[0][1] & 0x80) | (v & 0x7F); putLat(0, 1);
  setBit(1, 0, 1, v & 0x80); putLat(1, 0);
}
void dataDir(bool out) {                      // D0-D6 = U1 GPA0-6, D7 = U2 GPA0
  iodir[0][0] = out ? 0x00 : 0x7F; putDir(0, 0);
  if (out) iodir[1][0] &= ~1; else iodir[1][0] |= 1; putDir(1, 0);
}
void dataOut(uint8_t v) {
  olat[0][0] = (olat[0][0] & 0x80) | (v & 0x7F); putLat(0, 0);
  setBit(1, 0, 0, v & 0x80); putLat(1, 0);
}
uint8_t dataIn() { return (gpio(0, 0) & 0x7F) | ((gpio(1, 0) & 1) << 7); }
uint8_t addrIn() { return (gpio(0, 1) & 0x7F) | ((gpio(1, 0) & 2) << 6); }

// May this card drive bus lines? Not with a CPU on the bus. (MASTER:1# and WALK ask.)
bool busFree(String &why) {
  if (!busOn) { why = F("bus has no power"); return false; }
  // a running CPU toggles TPA/TPB: watch for 20 ms
  uint8_t first = gpio(1, 0) & 0x0C; unsigned long t = millis();
  while (millis() - t < 20) if ((gpio(1, 0) & 0x0C) != first) { why = F("TPA/TPB toggling: a CPU is running - pull the CPU card"); return false; }
  if (revC) {                                  // BUSDRV-C can see a stopped CPU Rev D too, through the DEBUG cable
    if (clkHz) { why = F("the clock is running: CLKSTOP:0# first"); return false; }
    if (clockOurs()) { why = F("a CPU card answers on the DEBUG cable - pull the CPU card"); return false; }
  }
  return true;
}

// Take the bus: idle levels first (latches), then directions, so nothing glitches active.
bool takeBus(String &why) {
  if (!busFree(why)) return false;
  olat[1][0] = (olat[1][0] & 0x80) | 0x70;     // U2 A: D7 0, A7 0, TPA 0, TPB 0, -MRD 1, -MRW 1, -VMA 1
  olat[1][1] = (olat[1][1] & 0x80);            // U2 B: Q 0, -RESET/-INT/-EF latch 0 (they stay inputs = released), N 0
  olat[0][1] &= 0x80; putLat(0, 1); putLat(1, 0); putLat(1, 1);
  iodir[0][1] = 0x00;                          // A0-A6 out
  iodir[1][0] = 0x01;                          // U2 A: D7 in, A7 TPA TPB -MRD -MRW -VMA out, SPARE3 out
  iodir[1][1] = 0x0E;                          // U2 B: Q out, -RESET -INT -EF in (released), N0-N2 out, SPARE4 out
  iodir[0][0] = 0x7F; putDir(0, 0); putDir(0, 1); putDir(1, 0); putDir(1, 1);
  master = true; loadSynced = false; return true;
}

void setN(uint8_t n) { olat[1][1] = (olat[1][1] & 0x8F) | ((n & 7) << 4); putLat(1, 1); }

void cycleAddr(uint16_t a) {                  // high byte latched on TPA, then the low byte, -VMA asserted
  addrOut(a >> 8); sig("TPA", 1); sig("TPA", 0);
  addrOut(a & 0xFF); sig("-VMA", 1);
}
uint8_t memRead(uint16_t a) {
  cycleAddr(a); dataDir(false);
  sig("-MRD", 1); sig("TPB", 1);               // TPB = the 6845's E: its bus port answers only while E is high
  uint8_t v = dataIn();
  sig("TPB", 0); sig("-MRD", 0);
  sig("-VMA", 0); return v;
}
void memWrite(uint16_t a, uint8_t v) {
  cycleAddr(a); dataOut(v); dataDir(true);
  sig("-MRW", 1); sig("TPB", 1); sig("TPB", 0); sig("-MRW", 0);   // the 6845 latches as E falls, R/W still low
  dataDir(false); sig("-VMA", 0);
}
void ioOut(uint8_t n, uint8_t b) {             // an 1802 OUT: memory-read direction, data from "memory" (us)
  dataOut(b); dataDir(true); sig("-MRD", 1);
  setN(n); sig("TPA", 1); sig("TPA", 0); sig("TPB", 1); sig("TPB", 0);
  setN(0); sig("-MRD", 0); dataDir(false);
}
uint8_t ioInp(uint8_t n) {
  dataDir(false); setN(n); sig("TPA", 1); sig("TPA", 0);
  sig("TPB", 1); uint8_t d = dataIn(); sig("TPB", 0); setN(0);
  return d;
}

// ---------------------------------------------------------------- BUSDRV-C: the 1802's mode, and LOAD mode by the clock
uint8_t cpuMode() {                            // from the bus: 0 RUN, 1 RESET, 2 PAUSE, 3 LOAD
  return ((gpio(1, 1) & VB_RESET) ? 0 : 1) | ((gpio(2, 0) & WA_PAUSE) ? 0 : 2);
}

bool setMode(uint8_t m) {
  // -RESET and -PAUSE are low together only in LOAD (the moment they are, CPU Rev D sets LOADED): every other
  // change lets one go before it pulls the other. Letting -RESET go is not the same as -RESET going high: the CPU
  // card's DS1813 holds it low for 150 ms more, and its RESET/RUN switch or the IO panel may hold it too. So PAUSE
  // waits to see -RESET high on the bus, and gives up (false) rather than make a LOAD of it.
  // BOOT (4) is -RESET and -DMAIN low with -PAUSE high: CPU Rev D clears LOADED. -DMAIN is low with -RESET for
  // nothing else, so every change lets it go first; and BOOT is refused while anything holds -PAUSE low, where the
  // two lines would be LOAD mode with a DMA request.
  loadSynced = false;
  sig("-DMAIN", 0);
  why = F("-RESET stays low (the CPU card's switch, another card): -PAUSE now would be LOAD");
  if (m == 2) {
    sig("-RESET", 0);
    unsigned long t = millis();
    while (!(gpio(1, 1) & VB_RESET)) if (millis() - t > 500) return false;
    sig("-PAUSE", 1); return true;
  }
  sig("-PAUSE", 0);                            // RUN, RESET, LOAD and BOOT all start by letting -PAUSE go
  if (m == 4 && !(gpio(2, 0) & WA_PAUSE)) {
    why = F("-PAUSE is low (the LOAD switch, another card): a boot reset needs it high"); return false;
  }
  sig("-RESET", m != 0);
  if (m && !clkHz) for (uint8_t i = 0; i < 32; i++) clkEdge();   // the clock is ours: give the 1802 its reset
  if (m == 3) sig("-PAUSE", 1);                // LOAD: through RESET, so R(0) = 0000
  if (m == 4) sig("-DMAIN", 1);                // BOOT
  return true;
}

bool loadReady() {                             // LOAD mode on the bus, the clock ours and reaching the 1802, idle cycles
  if (cpuMode() != 3) { why = F("not in LOAD mode: MODE:3# first"); loadSynced = false; return false; }
  if (loadSynced) return true;
  clkStop();
  if (!clockOurs()) { why = F("CLK OUT does not reach the 1802: DEBUG cable, or the CPU card's JP1 not on EXT"); return false; }
  uint8_t rises = 0, last = gpio(1, 0);
  for (uint8_t i = 0; i < 200 && rises < 2; i++) {       // the initialization cycle, then idle cycles: TPA twice
    clkEdge(); uint8_t va = gpio(1, 0);
    if ((va & VA_TPA) && !(last & VA_TPA)) rises++;
    last = va;
  }
  if (rises < 2) { why = F("no TPA from the 1802 in LOAD mode"); return false; }
  loadSynced = true; return true;
}

bool dmaByte(uint8_t v, uint16_t *addr) {
  uint8_t i, va = 0, hi = 0, lo = 0; bool low = false, done = false;
  // an idle cycle first: SC0 high. If it stays low, DMA cycles are running with no request of ours
  for (i = 0; i < 40 && !(gpio(2, 0) & WA_SC0); i++) clkEdge();
  if (i == 40) { why = F("SC0 stays low: DMA cycles with no request (-DMAIN held low?)"); return false; }
  // CPU Rev D (2026-11-22) passes -DMAIN to the 1802 only once it has seen the line high in LOAD mode: a line that
  // something holds low makes no DMA cycles there, and none of ours either
  if (!(gpio(2, 0) & WA_DMAIN)) { why = F("-DMAIN is low before the request: something else holds it"); return false; }
  sig("-DMAIN", 1);                            // the request
  for (i = 0; i < 40; i++) { clkEdge(); if (!(gpio(2, 0) & WA_SC0)) break; }   // until the 1802 takes it: SC0 low
  sig("-DMAIN", 0);                            // taken (or not): let go at once, so one DMA cycle follows and no more
  if (i == 40) { why = F("no DMA cycle: -DMAIN does not reach the 1802"); return false; }
  for (i = 0; i < 6 && !((va = gpio(1, 0)) & VA_MRD); i++) clkEdge();          // the memory off the data lines
  if (i == 6) { why = F("-MRD low in the DMA cycle"); return false; }
  dataOut(v); dataDir(true);                   // the byte, for this cycle only
  for (i = 0; i < 40 && !done; i++) {          // through the write: -MRW low, then high again
    if (va & VA_TPA) hi = (gpio(0, 1) & 0x7F) | ((va & VA_A7) << 6);           // the address: high byte during TPA
    if (!(va & VA_MRW)) { if (!low) lo = (gpio(0, 1) & 0x7F) | ((va & VA_A7) << 6); low = true; }   // low byte during -MRW
    else if (low) { done = true; break; }
    clkEdge(); va = gpio(1, 0);
  }
  dataDir(false);                              // off the data lines before the idle cycle reads memory
  if (!done) { why = F("no -MRW pulse in the DMA cycle"); return false; }
  for (i = 0; i < 12; i++) { clkEdge(); if (gpio(2, 0) & WA_SC0) break; }      // one DMA cycle only: idle again
  if (i == 12) { why = F("a second DMA cycle followed (-DMAIN held low?)"); loadSynced = false; return false; }
  *addr = ((uint16_t)hi << 8) | lo; return true;
}

// ---------------------------------------------------------------- WALK: one bus line driven alone
void walkPulls(bool on) {                      // the expanders' own pull-ups (100k) on every bus line, or off again
  for (uint8_t c = 0; c < nchips; c++) {       // (U3's three DEBUG inputs keep theirs either way)
    wr(c, GPPUA, on ? BUSPINS[c][0] : 0); wr(c, GPPUA + 1, (on ? BUSPINS[c][1] : 0) | (c == 2 ? 0x07 : 0));
  }
}

// ---------------------------------------------------------------- reporting
void snapLine() {
  uint8_t ua = gpio(0, 0), ub = gpio(0, 1), va = gpio(1, 0), vb = gpio(1, 1);
  char buf[96];
  uint8_t d = (ua & 0x7F) | ((va & 1) << 7), a = (ub & 0x7F) | ((va & 2) << 6);
  snprintf(buf, sizeof buf, "D=%02X A=%02X TPA=%d TPB=%d -MRD=%d -MRW=%d -VMA=%d Q=%d N=%d -RESET=%d -INT=%d -EF=%d SP=%X",
           d, a, (va >> 2) & 1, (va >> 3) & 1, (va >> 4) & 1, (va >> 5) & 1, (va >> 6) & 1, vb & 1, (vb >> 4) & 7,
           (vb >> 1) & 1, (vb >> 2) & 1, (vb >> 3) & 1,
           ((olat[0][0] >> 7) & 1) | ((olat[0][1] >> 7) & 1) << 1 | ((olat[1][0] >> 7) & 1) << 2 | ((olat[1][1] >> 7) & 1) << 3);
  Serial.print(F("Data: ")); Serial.print(buf);
  if (revC) {
    uint8_t wa = gpio(2, 0), wb = gpio(2, 1);
    snprintf(buf, sizeof buf, " -EF1=%d -EF2=%d -EF3=%d -PAUSE=%d -DMAIN=%d SC0=%d DBG=%d%d%d S5=%02X",
             wa & 1, (wa >> 1) & 1, (wa >> 2) & 1, (wa >> 3) & 1, (wa >> 4) & 1, (wa >> 5) & 1, wb & 1, (wb >> 1) & 1, (wb >> 2) & 1,
             ((wa >> 6) & 1) | ((wb >> 2) & 0x1E));
    Serial.print(buf);
  }
  Serial.println();
}

int hexv(char c) { if (c >= '0' && c <= '9') return c - '0'; if (c >= 'A' && c <= 'F') return c - 'A' + 10; if (c >= 'a' && c <= 'f') return c - 'a' + 10; return -1; }
void err(const __FlashStringHelper *m) { Serial.print(F("Error: ")); Serial.println(m); }
void errS(const String &m) { Serial.print(F("Error: ")); Serial.println(m); }
void hex4(uint16_t a) { char b[6]; snprintf(b, sizeof b, "%04X", a); Serial.print(b); }
void ns(unsigned long ticks) { Serial.print((ticks >> 1) * 125UL + ((ticks & 1) ? 62 : 0)); }   // Timer 1 counts of 62.5 ns

// ---------------------------------------------------------------- BUSDRV-C's commands; false = not one of them
bool runC(const String &op, const String &arg, long v) {
  if (!(op == "MODE" || op == "DMA" || op == "LOADBLK" || op == "CLKHZ" || op == "CLKSTOP" || op == "PROBE" || op == "PCOUNT" ||
        op == "PTIME" || op == "PDELAY" || op == "DBG" || op == "SPDIR" || op == "SPIN")) return false;
  if (!revC) { err(F("needs BUSDRV-C (no U3 at 0x22)")); return true; }
  if (op == "MODE") {
    if (v < 0 || v > 4) { err(F("MODE 0 RUN, 1 RESET, 2 PAUSE, 3 LOAD, 4 BOOT")); return true; }
    if (master) { err(F("MODE is for a CPU card in place: MASTER:0# first")); return true; }
    if (!setMode(v)) { err(why); return true; }
  } else if (op == "DMA" || op == "LOADBLK") {
    int c1 = arg.indexOf(','); long count = op == "DMA" ? 1 : v; uint16_t a = 0, first = 0;
    if (master) { err(F("LOAD mode is for a CPU card in place: MASTER:0# first")); return true; }
    if (op == "DMA") { if (v < 0 || v > 255) { err(F("value 0..255")); return true; } }
    else if (count < 1 || count > WBLOCK_MAX || c1 < 0 || (long)arg.length() < c1 + 1 + 2 * count) { err(F("LOADBLK:count,hh.. count 1..32, 2 hex digits per byte")); return true; }
    if (!loadReady()) { err(why); return true; }
    for (long i = 0; i < count; i++) {
      int b = v;
      if (op != "DMA") {
        int hi = hexv(arg[c1 + 1 + 2 * i]), lo = hexv(arg[c1 + 2 + 2 * i]);
        if (hi < 0 || lo < 0) { err(F("bad hex in LOADBLK")); return true; }
        b = hi * 16 + lo;
      }
      if (!dmaByte(b, &a)) { Serial.print(F("Error: byte ")); Serial.print(i); Serial.print(F(": ")); Serial.println(why); return true; }
      if (i == 0) first = a;
      else if (a != (uint16_t)(first + i)) { Serial.print(F("Error: byte ")); Serial.print(i); Serial.print(F(" went to ")); hex4(a); Serial.println(F(", not the next address")); return true; }
    }
    Serial.print(F("Data: ")); if (op != "DMA") { Serial.print(count); Serial.print(' '); } hex4(first); Serial.println();
  } else if (op == "CLKHZ") {
    if (v < 1 || v > 2000000L) { err(F("CLKHZ 1..2000000 (the cards are timed for 2 MHz)")); return true; }
    loadSynced = false; Serial.print(F("Data: ")); Serial.println(clkStart(v));
  } else if (op == "CLKSTOP") { clkStop();
  } else if (op == "PROBE") {
    Serial.print(F("Data: P1=")); Serial.print(digitalRead(PIN_PROBE1)); Serial.print(F(" P2=")); Serial.println(digitalRead(PIN_PROBE2));
  } else if (op == "PCOUNT") {
    if (v < 1 || v > 10000) { err(F("PCOUNT 1..10000 ms")); return true; }
    pcnt[0] = pcnt[1] = 0; PCMSK0 = _BV(PCINT0); PCMSK1 = _BV(PCINT9); PCIFR = _BV(PCIF0) | _BV(PCIF1);
    PCICR |= _BV(PCIE0) | _BV(PCIE1); delay(v); PCICR &= ~(_BV(PCIE0) | _BV(PCIE1));
    Serial.print(F("Data: P1=")); Serial.print(pcnt[0]); Serial.print(F(" P2=")); Serial.println(pcnt[1]);
  } else if (op == "PTIME" || op == "PDELAY") {
    if (clkHz) { err(F("Timer 1 is making the clock: CLKSTOP:0# first")); return true; }
    if (op == "PTIME") {                       // rising, falling, rising on PROBE1: Timer 1 free at 16 MHz, 62.5 ns a count
      unsigned long ms = (v < 1 || v > 4000) ? 1000 : v, t[3], t0 = millis(); uint16_t ovf = 0; uint8_t k = 0;
      TCCR1A = 0; TCCR1B = _BV(ICES1) | _BV(CS10); TIFR1 = _BV(ICF1) | _BV(TOV1);
      while (k < 3 && millis() - t0 < ms) {
        uint8_t f = TIFR1;
        if (f & _BV(ICF1)) {
          uint16_t c = ICR1, o = ovf;
          if ((f & _BV(TOV1)) && c < 0x8000) o++;          // the timer wrapped before this edge, not yet counted
          t[k++] = ((unsigned long)o << 16) | c;
          TCCR1B ^= _BV(ICES1); TIFR1 = _BV(ICF1);         // the other edge next
        }
        if (f & _BV(TOV1)) { ovf++; TIFR1 = _BV(TOV1); }
      }
      TCCR1B = 0;
      if (k < 3) { err(F("no rising-falling-rising on PROBE1 in that time")); return true; }
      Serial.print(F("Data: period_ns=")); ns(t[2] - t[0]); Serial.print(F(" high_ns=")); ns(t[1] - t[0]); Serial.println();
    } else {                                   // one clock edge, and PROBE1's next edge of the kind asked for
      TCCR1A = 0; TCCR1B = (v ? _BV(ICES1) : 0) | _BV(CS10); TIFR1 = _BV(ICF1);
      noInterrupts(); uint16_t t0 = TCNT1; clkEdge(); interrupts();
      unsigned long u = micros(); loadSynced = false;
      while (!(TIFR1 & _BV(ICF1)) && micros() - u < 4000) {}
      bool got = TIFR1 & _BV(ICF1); uint16_t c = ICR1; TCCR1B = 0;
      if (!got) { err(F("no such edge on PROBE1 within 4 ms of the clock edge")); return true; }
      Serial.print(F("Data: ")); ns((uint16_t)(c - t0)); Serial.println();
    }
  } else if (op == "DBG") {
    if (v) {
      if (clkHz) { err(F("the clock is running: CLKSTOP:0# first")); return true; }
      loadSynced = false;
      if (!clockOurs()) { err(F("CLK OUT does not reach the 1802: DEBUG cable, or the CPU card's JP1 not on EXT")); return true; }
      Serial.println(F("Data: CLK OUT reaches the 1802"));
    } else {
      uint8_t wb = gpio(2, 1); char b[32];
      snprintf(b, sizeof b, "CLOCK=%d SC0=%d SC1=%d", wb & 1, (wb >> 1) & 1, (wb >> 2) & 1);
      Serial.print(F("Data: ")); Serial.println(b);
    }
  } else if (op == "SPDIR") {
    spdir = v & 0x1F;
    iodir[2][0] = (iodir[2][0] & 0xBF) | ((spdir & 1) ? 0 : 0x40); iodir[2][1] = (iodir[2][1] & 0x87) | ((~(spdir >> 1) & 0x0F) << 3);
    putDir(2, 0); putDir(2, 1);
  } else {                                     // SPIN
    Serial.print(F("Data: ")); Serial.println(((gpio(2, 0) >> 6) & 1) | ((gpio(2, 1) >> 2) & 0x1E));
  }
  Serial.println(F("Complete"));
  return true;
}

// ---------------------------------------------------------------- commands
void run(String c) {
  int colon = c.indexOf(':');
  if (colon < 0) { err(F("format is CMD:OPERAND#")); return; }
  String op = c.substring(0, colon), arg = c.substring(colon + 1);
  long v = arg.toInt();
  bool needMaster = !(op == "HELP" || op == "STATUS" || op == "MASTER" || op == "SNAP" || op == "WATCH" || op == "SPARE" ||
                      op == "XRST" || op == "RD-ADDRBUS" || op == "RD-DATABUS" || op == "DATABUS-RD-MODE" || op == "WALK");
  if (!busOn && op != "HELP" && op != "STATUS") { err(F("bus has no power")); return; }
  if (runC(op, arg, v)) return;
  const Sig *sg = sigFind(op);
  if (sg && sg->chip >= nchips) { err(F("needs BUSDRV-C (no U3 at 0x22)")); return; }
  if (sg && (sg->flags & OPEN_COLL)) needMaster = false;      // pulling an open-collector line low is safe with a CPU
  if (op == "CLK") needMaster = false;
  if (needMaster && !master) { err(F("MONITOR mode: send MASTER:1# first (CPU card out)")); return; }

  if (op == "HELP") {
    Serial.println(F("STATUS MASTER SNAP WATCH TPA TPB -MRD -MRW -VMA Q -RESET -INT -EF N WR-ADDRBUS RD-ADDRBUS"));
    Serial.println(F("WR-DATABUS RD-DATABUS DATABUS-RD-MODE RDMEM WRMEM RDBLK WRBLK OUT INP INBLK OUTBLK SPARE XRST CLK WALK"));
    if (revC) Serial.println(F("BUSDRV-C: -EF1 -EF2 -EF3 -PAUSE -DMAIN MODE DMA LOADBLK CLKHZ CLKSTOP DBG PROBE PCOUNT PTIME PDELAY SPDIR SPIN"));
  } else if (op == "STATUS") {
    Serial.print(F("Data: bus=")); Serial.print(busOn ? F("on") : F("off"));
    Serial.print(F(" mode=")); Serial.print(master ? F("MASTER") : F("MONITOR"));
    if (busOn && revC) {
      static const char M[] PROGMEM = "RUN\0\0\0RESET\0PAUSE\0LOAD";
      Serial.print(F(" board=C cpu=")); Serial.print((const __FlashStringHelper *)(M + 6 * cpuMode()));
      Serial.print(F(" clk=")); Serial.print(clkHz);
    }
    Serial.println();
  } else if (op == "MASTER") {
    if (v) { String why; if (!takeBus(why)) { errS(why); return; } }
    else allInputs();
  } else if (op == "SNAP") { snapLine();
  } else if (op == "WATCH") {
    uint8_t last[6], now[6]; bool first = true; unsigned long t = millis();
    while ((v == 0 || millis() - t < (unsigned long)v) && !Serial.available()) {
      for (uint8_t k = 0; k < nchips; k++) gpio2(k, now + 2 * k);
      if (revC) now[5] &= 0xFE;                // (not the DEBUG cable's CLOCK: with a clock running it never rests)
      if (first || memcmp(now, last, 2 * nchips)) { snapLine(); memcpy(last, now, 6); first = false; }
    }
    while (Serial.available()) Serial.read();
  } else if (sg) {
    sigWrite(*sg, v != 0);
    if (sg->chip == 2 || sg->bit == 1) loadSynced = false;      // -RESET, -PAUSE or -DMAIN by hand
  } else if (op == "N") { setN(v);
  } else if (op == "WR-ADDRBUS") { addrOut(v);
  } else if (op == "RD-ADDRBUS") { Serial.print(F("Data: ")); Serial.println(addrIn());
  } else if (op == "WR-DATABUS") { dataOut(v); dataDir(true);
  } else if (op == "RD-DATABUS") { Serial.print(F("Data: ")); Serial.println(dataIn());
  } else if (op == "DATABUS-RD-MODE") { if (master) dataDir(false);
  } else if (op == "RDMEM") {
    if (v < 0 || v > 65535) { err(F("addr 0..65535")); return; }
    Serial.print(F("Data: ")); Serial.println(memRead(v));
  } else if (op == "WRMEM" || op == "OUT") {
    int comma = arg.indexOf(','); if (comma < 0) { err(F("needs a,b")); return; }
    long a = arg.toInt(), b = arg.substring(comma + 1).toInt();
    if (b < 0 || b > 255) { err(F("value 0..255")); return; }
    if (op == "WRMEM") { if (a < 0 || a > 65535) { err(F("addr 0..65535")); return; } memWrite(a, b); }
    else {
      if (a < 1 || a > 7) { err(F("port 1..7")); return; }
      ioOut(a, b);
    }
  } else if (op == "INP") {
    if (v < 1 || v > 7) { err(F("port 1..7")); return; }
    Serial.print(F("Data: ")); Serial.println(ioInp(v));
  } else if (op == "INBLK" || op == "OUTBLK") {
    int c1 = arg.indexOf(','); if (c1 < 0) { err(F("needs port,count")); return; }
    int c2 = arg.indexOf(',', c1 + 1);
    long n = arg.toInt(), count = arg.substring(c1 + 1).toInt();
    if (n < 1 || n > 7) { err(F("port 1..7")); return; }
    if (count < 1 || count > (op == "INBLK" ? BLOCK_MAX : WBLOCK_MAX)) { err(F("INBLK count 1..64, OUTBLK 1..32")); return; }
    if (op == "OUTBLK") {
      if (c2 < 0 || (long)arg.length() < c2 + 1 + 2 * count) { err(F("OUTBLK needs 2 hex digits per byte")); return; }
      for (long i = 0; i < count; i++) {
        int hi = hexv(arg[c2 + 1 + 2 * i]), lo = hexv(arg[c2 + 2 + 2 * i]);
        if (hi < 0 || lo < 0) { err(F("bad hex in OUTBLK")); return; }
        ioOut(n, hi * 16 + lo);
      }
      Serial.print(F("Data: ")); Serial.println(count);
    } else {
      Serial.print(F("Data:"));
      for (long i = 0; i < count; i++) { uint8_t b = ioInp(n); Serial.print(' '); if (b < 16) Serial.print('0'); Serial.print(b, HEX); }
      Serial.println();
    }
  } else if (op == "RDBLK" || op == "WRBLK") {
    int c1 = arg.indexOf(','); if (c1 < 0) { err(F("block needs addr,count")); return; }
    int c2 = arg.indexOf(',', c1 + 1);
    long addr = arg.toInt(), count = arg.substring(c1 + 1).toInt();
    if (addr < 0 || addr > 65535 || count < 1 || count > BLOCK_MAX || addr + count > 65536) { err(F("block addr 0..65535, count 1..64")); return; }
    if (op == "WRBLK") {
      if (count > WBLOCK_MAX) { err(F("WRBLK count 1..32")); return; }
      if (c2 < 0 || (long)arg.length() < c2 + 1 + 2 * count) { err(F("WRBLK needs 2 hex digits per byte")); return; }
      for (long i = 0; i < count; i++) {
        int hi = hexv(arg[c2 + 1 + 2 * i]), lo = hexv(arg[c2 + 2 + 2 * i]);
        if (hi < 0 || lo < 0) { err(F("bad hex in WRBLK")); return; }
        memWrite(addr + i, hi * 16 + lo);
      }
      Serial.print(F("Data: ")); Serial.println(count);
    } else {
      Serial.print(F("Data:"));
      for (long i = 0; i < count; i++) { uint8_t b = memRead(addr + i); Serial.print(' '); if (b < 16) Serial.print('0'); Serial.print(b, HEX); }
      Serial.println();
    }
  } else if (op == "SPARE") {
    setBit(0, 0, 7, v & 1); setBit(0, 1, 7, v & 2); setBit(1, 0, 7, v & 4); setBit(1, 1, 7, v & 8);
    putLat(0, 0); putLat(0, 1); putLat(1, 0); putLat(1, 1);
    if (revC) {                                // SPARE5 = U3 GPA6, SPARE6-9 = GPB3-6, SPARE10 = GPA7, SPARE11 = GPB7
      olat[2][0] = ((v >> 4) & 1) << 6 | ((v >> 9) & 1) << 7; olat[2][1] = ((v >> 5) & 0x0F) << 3 | ((v >> 10) & 1) << 7;
      putLat(2, 0); putLat(2, 1);
    }
  } else if (op == "CLK") {
    if (master) { err(F("CLK is for MONITOR mode (the CPU card drives the bus)")); return; }
    long n = v; if (n < 1) { err(F("CLK:n, n >= 1")); return; }
    uint8_t last[6] = {0, 0, 0, 0, 0, 0}, now[6]; bool first = true; long e = 0;
    char buf[40];
    if (revC) { clkStop(); loadSynced = false; }
    for (e = 1; e <= n && !Serial.available(); e++) {
      if (revC) clkEdge();                     // BUSDRV-C: one change of CLK OUT
      else { setBit(0, 0, 7, true); putLat(0, 0); }             // BUSDRV-B: a rising edge on SPARE1
      for (uint8_t k = 0; k < nchips; k++) gpio2(k, now + 2 * k);
      if (revC) now[5] &= 0xFE;                // (the DEBUG cable's CLOCK changes on every edge: left out, shown as 0)
      else { setBit(0, 0, 7, false); putLat(0, 0); }
      if (first || memcmp(now, last, 2 * nchips)) {
        if (revC) snprintf(buf, sizeof buf, "T %ld %02X %02X %02X %02X %02X %02X", e, now[0], now[1], now[2], now[3], now[4], now[5]);
        else snprintf(buf, sizeof buf, "T %ld %02X %02X %02X %02X", e, now[0], now[1], now[2], now[3]);
        Serial.println(buf); memcpy(last, now, 6); first = false;
      }
    }
    while (Serial.available()) Serial.read();
    Serial.print(F("Data: ")); Serial.println(e - 1);
  } else if (op == "XRST") {
    pinMode(PIN_XRST, OUTPUT); digitalWrite(PIN_XRST, LOW); delay(1); pinMode(PIN_XRST, INPUT); delay(1);
    expandersInit();
  } else if (op == "WALK") {
    int comma = arg.indexOf(','); long lv = comma < 0 ? 2 : arg.substring(comma + 1).toInt();
    uint8_t c = (v >> 4) & 0x0F, p = (v >> 3) & 1, b = v & 7;
    if (v < 0 || v > 47 || c >= nchips || !((BUSPINS[c][p] >> b) & 1) || lv < 0 || lv > 2) {
      err(F("WALK:pin,level  pin = chip*16 + port*8 + bit of a bus line; level 0, 1, or 2 (drive nothing)")); return;
    }
    if (lv == 1 && ((OCPINS[c][p] >> b) & 1)) { err(F("an open-collector line is only ever pulled low: WALK level 0 or 2")); return; }
    if (master) { err(F("WALK is for MONITOR mode: MASTER:0# first")); return; }
    walkPulls(true);                           // on before the look for a CPU: on a bare backplane with no resistors TPA
    String why;                                //  and TPB would be floating inputs while they are watched
    if (!busFree(why)) { walkPulls(false); errS(why); return; }
    uint8_t now[6], dir0 = iodir[c][p], lat0 = olat[c][p]; bool held = lv < 2;
    if (held) {
      setBit(c, p, b, lv); putLat(c, p); iodir[c][p] &= ~(1 << b); putDir(c, p);     // the level first, then the direction
      if (((gpio(c, p) >> b) & 1) != lv) {     // it does not follow: something holds it the other way. Let go at once
        iodir[c][p] |= (1 << b); putDir(c, p); held = false;
      } else delayMicroseconds(300);           // (a line with only a 100k pull-up on it, and a card's inputs, to settle)
    }
    for (uint8_t k = 0; k < nchips; k++) gpio2(k, now + 2 * k);
    if (lv < 2) {                              // the pin as it was before. An input (as every bus pin is, but for an open-
      if (dir0 & (1 << b)) { iodir[c][p] |= (1 << b); putDir(c, p); }   // collector line this card is holding low: that
      olat[c][p] = lat0; putLat(c, p);         //  one stays low all through, and is not let go for a moment here)
      if (iodir[c][p] != dir0) { iodir[c][p] = dir0; putDir(c, p); }
    }
    walkPulls(false);
    char buf[24];
    if (revC) snprintf(buf, sizeof buf, "%02X %02X %02X %02X %02X %02X", now[0], now[1], now[2], now[3], now[4], now[5]);
    else snprintf(buf, sizeof buf, "%02X %02X %02X %02X", now[0], now[1], now[2], now[3]);
    Serial.print(F("Data: ")); Serial.println(buf);
  } else { err(F("Bad opcode")); return; }
  Serial.println(F("Complete"));
}

void setup() {
  Serial.begin(BAUD);
  pinMode(PIN_INT_U1, INPUT); pinMode(PIN_INT_U2, INPUT); pinMode(PIN_INT_U3, INPUT);
  pinMode(PIN_PROBE1, INPUT); pinMode(PIN_PROBE2, INPUT); pinMode(PIN_CLK, INPUT);
  pinMode(PIN_XRST, OUTPUT); digitalWrite(PIN_XRST, LOW);   // expanders held in reset until the bus has power
  pinMode(SDA, INPUT); pinMode(SCL, INPUT);
  busPower();
  Serial.print(F("s5-bus-driver blocks-1 io-2 "));
  Serial.print(revC ? F("clk-2 ext-1 mode-2 load-1 probe-1") : F("clk-1"));
  Serial.print(F(" walk-1 2026-11-22 "));
  if (busOn) { Serial.print(F("BUSDRV-")); Serial.println(revC ? 'C' : 'B'); }
  else Serial.println(F("(bus off: board not known yet)"));
  Serial.println(F(PROMPT));
}

void loop() {
  busPower();
  while (Serial.available()) {
    char ch = Serial.read();
    if (ch == '#') { run(command); command = ""; Serial.println(F(PROMPT)); }
    else if (ch != '\r' && ch != '\n' && command.length() < 2 * WBLOCK_MAX + 24) command += ch;
  }
}
