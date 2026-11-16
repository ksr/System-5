/*
 * s5-bus-driver.ino - firmware for the System-5 bus driver card (BUSDRV-B, hardware/bus-driver/kicad/rev-b)
 * Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-06. After Ken's YACC1 bus-driver.ino.
 *
 * Arduino Nano + two MCP23017 (I2C 0x20 = U1, 0x21 = U2) wired straight onto the 30-pin System-5 bus.
 *
 * Wire protocol (the same as the YACC1 bus driver, so tools carry over):
 *   host -> card : CMD:OPERAND#            operands are DECIMAL unless noted; no line ending needed
 *   card -> host : optional "Data: ..." lines, "Complete" or "Error: ...", then the prompt ">>"
 *   A banner line is printed before the first prompt; the host looks for "s5-bus-driver" and "blocks-".
 *   Signal names starting with '-' are active low: "-MRD:1#" asserts -MRD (drives it low).
 *
 * Safety rules built in (see hardware/bus-driver/kicad/rev-b/README.md):
 *   - At reset the card is a MONITOR: every expander pin is an input. It drives the bus only after MASTER:1#,
 *     which is refused if TPA/TPB are seen toggling (a CPU is running) or the bus has no power.
 *     It cannot tell a stopped CPU card from an empty slot: pull the CPU card before MASTER:1#.
 *   - Open-collector lines (-RESET, -INT, -EF) are only ever pulled low or released (pin made an input).
 *   - While bus +5V is off (A0 / BUS_SENSE low) the expanders are held in reset by releasing nothing that could
 *     back-feed them: XRST (D4) low, I2C stopped and its pins inputs without pull-ups.
 *   - MCP23017 GPA7/GPB7 are output-only on current silicon: they are the four SPARE outputs, never bus signals.
 *
 * Commands (case sensitive):
 *   HELP:0#                    list commands
 *   STATUS:0#                  "Data: bus=on|off mode=MONITOR|MASTER"
 *   MASTER:1# / MASTER:0#      take / give up the bus (MASTER:0 makes every pin an input again)
 *   SNAP:0#                    "Data: D=hh A=hh TPA=0 TPB=0 -MRD=1 -MRW=1 -VMA=1 Q=0 N=0 -RESET=1 -INT=1 -EF=1 SP=x"
 *                              (levels as seen on the bus; active-low names show the pin level, 1 = inactive)
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
 *   SPARE:mask#                SPARE1..4 outputs (J2) = bits 0..3 of mask (works in either mode)
 *   XRST:0#                    pulse the expanders' reset (every pin back to input; mode becomes MONITOR)
 *   CLK:n#                     MONITOR, clock stepping (2026-10-31): SPARE1 (J2 pin 1) wired to the CPU card's IC8 pin 3
 *                              (the 74LS74 that halves the oscillator into the 1802's CLOCK). n rising edges on SPARE1,
 *                              each one 1802 clock edge (16 per machine cycle). After each edge the bus is read; a line
 *                              "T e ua ub va vb" (e decimal, the four GPIO ports in hex) is printed when it changed, then
 *                              "Data: e" (edges done). Any key stops it. software/busdrv/cputrace.py decodes the lines.
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
#define BANNER "s5-bus-driver blocks-1 io-2 clk-1 2026-10-31"
#define PROMPT ">>"
#define BLOCK_MAX 64
#define WBLOCK_MAX 32

// Nano pins (gen/netlist.py)
#define PIN_INT_U1 2
#define PIN_INT_U2 3
#define PIN_XRST 4
#define PIN_SENSE A0
#define SENSE_ON 700          // ADC counts: bus +5V through 10k/100k reads about 930; off reads near 0

// MCP23017 registers, IOCON.BANK = 0
#define IODIRA 0x00
#define GPINTENA 0x04
#define IOCON 0x0A
#define GPPUA 0x0C
#define GPIOA 0x12
#define OLATA 0x14
const uint8_t ADDR[2] = {0x20, 0x21};

// Where each bus signal is: chip (0 = U1, 1 = U2), port (0 = A, 1 = B), bit
struct Sig { const char *name; uint8_t chip, port, bit, flags; };
#define LOW_ACTIVE 1          // name starts with '-'
#define OPEN_COLL 2           // only ever pulled low or released
const Sig SIGS[] = {
  {"TPA", 1, 0, 2, 0}, {"TPB", 1, 0, 3, 0}, {"-MRD", 1, 0, 4, LOW_ACTIVE}, {"-MRW", 1, 0, 5, LOW_ACTIVE},
  {"-VMA", 1, 0, 6, LOW_ACTIVE}, {"Q", 1, 1, 0, 0}, {"-RESET", 1, 1, 1, LOW_ACTIVE | OPEN_COLL},
  {"-INT", 1, 1, 2, LOW_ACTIVE | OPEN_COLL}, {"-EF", 1, 1, 3, LOW_ACTIVE | OPEN_COLL},
};
const uint8_t NSIGS = sizeof(SIGS) / sizeof(SIGS[0]);
// data bus: D0-D6 = U1 GPA0-6, D7 = U2 GPA0.  address bus: A0-A6 = U1 GPB0-6, A7 = U2 GPA1.  N0-N2 = U2 GPB4-6.
// spares: SPARE1 = U1 GPA7, SPARE2 = U1 GPB7, SPARE3 = U2 GPA7, SPARE4 = U2 GPB7 (output-only pins)

uint8_t olat[2][2];           // output latch shadows [chip][port]
uint8_t iodir[2][2];          // direction shadows: 1 = input
bool busOn = false, master = false, i2cUp = false;
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

// Every pin an input except the four output-only spares (which keep their latch value).
void allInputs() {
  for (uint8_t c = 0; c < 2; c++)
    for (uint8_t p = 0; p < 2; p++) { iodir[c][p] = 0x7F; putDir(c, p); }
  master = false;
}

void expandersInit() {
  for (uint8_t c = 0; c < 2; c++) {
    wr(c, IOCON, 0x40);                       // MIRROR: INTA covers both ports; BANK 0; INT active-low push-pull
    wr(c, GPPUA, 0); wr(c, GPPUA + 1, 0);      // no pull-ups: the bus has its own levels
    olat[c][0] = olat[c][1] = 0; putLat(c, 0); putLat(c, 1);
  }
  allInputs();
}

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
    Serial.println(F("Note: bus power on, MONITOR mode"));
  } else {
    if (i2cUp) { Wire.end(); i2cUp = false; }
    pinMode(SDA, INPUT); pinMode(SCL, INPUT);  // no back-feed into the unpowered expanders
    pinMode(PIN_XRST, OUTPUT); digitalWrite(PIN_XRST, LOW);
    master = false;
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
const Sig *sigFind(const String &n) { for (uint8_t i = 0; i < NSIGS; i++) if (n == SIGS[i].name) return &SIGS[i]; return 0; }
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

// Take the bus: idle levels first (latches), then directions, so nothing glitches active.
bool takeBus(String &why) {
  if (!busOn) { why = F("bus has no power"); return false; }
  // a running CPU toggles TPA/TPB: watch for 20 ms
  uint8_t first = gpio(1, 0) & 0x0C; unsigned long t = millis();
  while (millis() - t < 20) if ((gpio(1, 0) & 0x0C) != first) { why = F("TPA/TPB toggling: a CPU is running - pull the CPU card"); return false; }
  olat[1][0] = (olat[1][0] & 0x80) | 0x70;     // U2 A: D7 0, A7 0, TPA 0, TPB 0, -MRD 1, -MRW 1, -VMA 1
  olat[1][1] = (olat[1][1] & 0x80);            // U2 B: Q 0, -RESET/-INT/-EF latch 0 (they stay inputs = released), N 0
  olat[0][1] &= 0x80; putLat(0, 1); putLat(1, 0); putLat(1, 1);
  iodir[0][1] = 0x00;                          // A0-A6 out
  iodir[1][0] = 0x01;                          // U2 A: D7 in, A7 TPA TPB -MRD -MRW -VMA out, SPARE3 out
  iodir[1][1] = 0x0E;                          // U2 B: Q out, -RESET -INT -EF in (released), N0-N2 out, SPARE4 out
  iodir[0][0] = 0x7F; putDir(0, 0); putDir(0, 1); putDir(1, 0); putDir(1, 1);
  master = true; return true;
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

// ---------------------------------------------------------------- reporting
void snapLine() {
  uint8_t ua = gpio(0, 0), ub = gpio(0, 1), va = gpio(1, 0), vb = gpio(1, 1);
  char buf[96];
  uint8_t d = (ua & 0x7F) | ((va & 1) << 7), a = (ub & 0x7F) | ((va & 2) << 6);
  snprintf(buf, sizeof buf, "D=%02X A=%02X TPA=%d TPB=%d -MRD=%d -MRW=%d -VMA=%d Q=%d N=%d -RESET=%d -INT=%d -EF=%d SP=%X",
           d, a, (va >> 2) & 1, (va >> 3) & 1, (va >> 4) & 1, (va >> 5) & 1, (va >> 6) & 1, vb & 1, (vb >> 4) & 7,
           (vb >> 1) & 1, (vb >> 2) & 1, (vb >> 3) & 1,
           ((olat[0][0] >> 7) & 1) | ((olat[0][1] >> 7) & 1) << 1 | ((olat[1][0] >> 7) & 1) << 2 | ((olat[1][1] >> 7) & 1) << 3);
  Serial.print(F("Data: ")); Serial.println(buf);
}

int hexv(char c) { if (c >= '0' && c <= '9') return c - '0'; if (c >= 'A' && c <= 'F') return c - 'A' + 10; if (c >= 'a' && c <= 'f') return c - 'a' + 10; return -1; }
void err(const __FlashStringHelper *m) { Serial.print(F("Error: ")); Serial.println(m); }
void errS(const String &m) { Serial.print(F("Error: ")); Serial.println(m); }

// ---------------------------------------------------------------- commands
void run(String c) {
  int colon = c.indexOf(':');
  if (colon < 0) { err(F("format is CMD:OPERAND#")); return; }
  String op = c.substring(0, colon), arg = c.substring(colon + 1);
  long v = arg.toInt();
  bool needMaster = !(op == "HELP" || op == "STATUS" || op == "MASTER" || op == "SNAP" || op == "WATCH" || op == "SPARE" ||
                      op == "XRST" || op == "RD-ADDRBUS" || op == "RD-DATABUS" || op == "DATABUS-RD-MODE");
  if (!busOn && op != "HELP" && op != "STATUS") { err(F("bus has no power")); return; }
  const Sig *sg = sigFind(op);
  if (sg && (sg->flags & OPEN_COLL)) needMaster = false;      // pulling an open-collector line low is safe with a CPU
  if (op == "CLK") needMaster = false;
  if (needMaster && !master) { err(F("MONITOR mode: send MASTER:1# first (CPU card out)")); return; }

  if (op == "HELP") {
    Serial.println(F("STATUS MASTER SNAP WATCH TPA TPB -MRD -MRW -VMA Q -RESET -INT -EF N WR-ADDRBUS RD-ADDRBUS"));
    Serial.println(F("WR-DATABUS RD-DATABUS DATABUS-RD-MODE RDMEM WRMEM RDBLK WRBLK OUT INP INBLK OUTBLK SPARE XRST CLK"));
  } else if (op == "STATUS") {
    Serial.print(F("Data: bus=")); Serial.print(busOn ? F("on") : F("off"));
    Serial.print(F(" mode=")); Serial.println(master ? F("MASTER") : F("MONITOR"));
  } else if (op == "MASTER") {
    if (v) { String why; if (!takeBus(why)) { errS(why); return; } }
    else allInputs();
  } else if (op == "SNAP") { snapLine();
  } else if (op == "WATCH") {
    String last; unsigned long t = millis();
    while ((v == 0 || millis() - t < (unsigned long)v) && !Serial.available()) {
      uint8_t s[4] = {gpio(0, 0), gpio(0, 1), gpio(1, 0), gpio(1, 1)};
      String key = String(s[0]) + "," + s[1] + "," + s[2] + "," + s[3];
      if (key != last) { snapLine(); last = key; }
    }
    while (Serial.available()) Serial.read();
  } else if (sigFind(op)) {
    sigWrite(*sigFind(op), v != 0);
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
  } else if (op == "CLK") {
    if (master) { err(F("CLK is for MONITOR mode (the CPU card drives the bus)")); return; }
    long n = v; if (n < 1) { err(F("CLK:n, n >= 1")); return; }
    uint8_t last[4] = {0, 0, 0, 0}, now[4]; bool first = true; long e = 0;
    char buf[32];
    for (e = 1; e <= n && !Serial.available(); e++) {
      setBit(0, 0, 7, true); putLat(0, 0);
      gpio2(0, now); gpio2(1, now + 2);
      setBit(0, 0, 7, false); putLat(0, 0);
      if (first || memcmp(now, last, 4)) {
        snprintf(buf, sizeof buf, "T %ld %02X %02X %02X %02X", e, now[0], now[1], now[2], now[3]);
        Serial.println(buf); memcpy(last, now, 4); first = false;
      }
    }
    while (Serial.available()) Serial.read();
    Serial.print(F("Data: ")); Serial.println(e - 1);
  } else if (op == "XRST") {
    pinMode(PIN_XRST, OUTPUT); digitalWrite(PIN_XRST, LOW); delay(1); pinMode(PIN_XRST, INPUT); delay(1);
    expandersInit();
  } else { err(F("Bad opcode")); return; }
  Serial.println(F("Complete"));
}

void setup() {
  Serial.begin(BAUD);
  pinMode(PIN_INT_U1, INPUT); pinMode(PIN_INT_U2, INPUT);
  pinMode(PIN_XRST, OUTPUT); digitalWrite(PIN_XRST, LOW);   // expanders held in reset until the bus has power
  pinMode(SDA, INPUT); pinMode(SCL, INPUT);
  busPower();
  Serial.println(F(BANNER));
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
