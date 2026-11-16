// Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-01
// sim.cpp - host co-simulation of ../video-g-ps2.ino (run.sh builds and runs it; README.md "Host simulation").
// The world: a PS/2 keyboard or mouse modelled at bit level (11-clock frames both ways, request-to-send, a host inhibit
// aborting a frame that is then sent again), the 74HCT374 latch + 74HCT74 READY flip-flop (cleared while TPB of an INP
// is high), and a CPU polling READY and running INP cycles at 1802 speed or at the bus driver's I2C-stepped speed.
// Time steps are 1 us; the sketch's port registers (Arduino.h here) drive the model. Each test runs in its own process.
#include "Arduino.h"
#include SKETCH
#include <cstring>
#include <cstdlib>
#include <string>
#include <initializer_list>

uint64_t T = 0;
Reg PORTB, DDRB, PORTC, DDRC, PORTD, DDRD, EIMSK, PCICR, PCMSK0;
FlagReg EIFR, PCIFR;
SimSerial Serial;
void (*int0_isr)() = nullptr;
static bool IE = true, in_isr = false;

enum Board { TEXT, GFX };
static Board board = TEXT;
static int strap_kind = 0;               // GFX: 0 typical (pull-up read 0), 1 marginal (pull-up read 1)
static bool mouse_on_pin = false;
static bool ready_ff = false;
static uint8_t latch = 0;
static uint64_t pd7_off_t = 0;
static bool last_clk = true, last_lddata = true, last_ready = false, last_pd7pu = false;
static int fails = 0;

static bool host_clk_low() { return (DDRD.v & _BV(2)) && !(PORTD.v & _BV(2)); }
static bool host_dat_low() { return (DDRD.v & _BV(4)) && !(PORTD.v & _BV(4)); }

// ------------------------------------------------------------------ the PS/2 device
struct Dev {
  bool present = true, mouse = false;
  bool clk_low = false, dat_low = false;
  std::deque<uint8_t> outq;
  std::vector<std::pair<uint64_t, uint8_t>> sched;
  std::vector<uint8_t> got;               // bytes the host sent (good parity)
  enum { IDLE, TX, RX, GAP } st = IDLE;
  int k = 0, ph = 0;
  uint64_t tn = 0, last_low = 0;
  uint16_t frame = 0;
  uint8_t rxb = 0; int rxones = 0; bool rxstop = false;
  int aborts = 0, host_parity_errors = 0, gap_us = 300, corrupt_next = 0;
  bool expect_led = false; uint8_t leds = 0;   // keyboard
  bool reporting = false;                      // mouse
  std::deque<std::vector<uint8_t>> pkts;       // mouse packets still to send
  std::vector<uint8_t> sent_pkts;              // mouse packet bytes actually sent while reporting
  uint64_t next_pkt = 0;
  void schedule(uint64_t t, uint8_t b) { sched.push_back({t, b}); }
  void respond(uint8_t b) { outq.push_front(b); }
  void on_host_byte(uint8_t b);
  void tick();
} dev;

static bool clk_line() { return !(host_clk_low() || dev.clk_low); }
static bool dat_line() { return !(host_dat_low() || dev.dat_low); }

void Dev::on_host_byte(uint8_t b) {
  got.push_back(b);
  if (!mouse) {
    if (expect_led) { leds = b; expect_led = false; respond(0xFA); return; }
    switch (b) {
      case 0xFF: outq.clear(); respond(0xFA); schedule(T + 350000, 0xAA); leds = 0; break;
      case 0xED: respond(0xFA); expect_led = true; break;
      case 0xEE: respond(0xEE); break;
      default: respond(0xFA);
    }
  } else {
    outq.clear();                                  // a command ends the packet being sent
    switch (b) {
      case 0xFF: reporting = false; respond(0xFA); schedule(T + 400000, 0xAA); schedule(T + 401000, 0x00); break;
      case 0xF4: respond(0xFA); reporting = true; next_pkt = T + 10000; break;
      case 0xF5: respond(0xFA); reporting = false; break;
      default: respond(0xFA);
    }
  }
}

void Dev::tick() {
  if (!present) { clk_low = dat_low = false; st = IDLE; return; }
  for (size_t i = 0; i < sched.size();) {
    if (sched[i].first <= T) { outq.push_back(sched[i].second); sched.erase(sched.begin() + i); } else i++;
  }
  if (mouse && reporting && !pkts.empty() && T >= next_pkt && outq.empty() && st != TX) {
    for (uint8_t x : pkts.front()) { outq.push_back(x); sent_pkts.push_back(x); }
    pkts.pop_front(); next_pkt = T + 10000;
  }
  bool cl = clk_line();
  if (!cl) last_low = T;
  bool rts = cl && !dat_line() && !dat_low;
  switch (st) {
    case IDLE:
    case GAP:
      if (rts) { st = RX; k = 1; ph = 0; tn = T + 40; rxb = 0; rxones = 0; break; }
      if (st == GAP && T < tn) break;
      st = IDLE;
      if (!outq.empty() && cl && T - last_low >= 50) {
        uint8_t b = outq.front(); int ones = 0;
        for (int i = 0; i < 8; i++) ones += (b >> i) & 1;
        int par = (ones & 1) ? 0 : 1;
        if (corrupt_next) { par ^= 1; corrupt_next--; }
        frame = (uint16_t)((b << 1) | (par << 9) | (1 << 10));     // start 0, data, parity, stop 1
        st = TX; k = 0; ph = 0; tn = T;
      }
      break;
    case TX:
      if (T < tn) break;
      if (ph == 0) { dat_low = !((frame >> k) & 1); tn = T + 20; ph = 1; }
      else if (ph == 1) {
        if (!cl) { clk_low = dat_low = false; aborts++; st = GAP; tn = T + 100; break; }   // host inhibit: abort
        clk_low = true; tn = T + 40; ph = 2;
      } else if (ph == 2) { clk_low = false; tn = T + 20; ph = 3; }
      else {
        if (!cl && k < 10) { dat_low = false; aborts++; st = GAP; tn = T + 100; break; }
        if (++k == 11) { dat_low = false; outq.pop_front(); st = GAP; tn = T + gap_us; }
        else ph = 0;
      }
      break;
    case RX:
      if (T < tn) break;
      if (ph == 0) { clk_low = true; tn = T + 40; ph = 1; }
      else if (ph == 1) {
        clk_low = false;
        int d = dat_line() ? 1 : 0;
        if (k <= 8) { rxb |= d << (k - 1); rxones += d; }
        else if (k == 9) rxones += d;
        else rxstop = d;
        if (k == 10) { tn = T + 20; ph = 2; } else { k++; tn = T + 40; ph = 0; }
      } else if (ph == 2) { dat_low = true; tn = T + 20; ph = 3; }        // acknowledge
      else if (ph == 3) { clk_low = true; tn = T + 40; ph = 4; }
      else if (ph == 4) { clk_low = false; tn = T + 20; ph = 5; }
      else {
        dat_low = false; st = GAP; tn = T + 200;
        if ((rxones & 1) && rxstop) on_host_byte(rxb); else { host_parity_errors++; respond(0xFE); }
      }
      break;
  }
}

// ------------------------------------------------------------------ the CPU reading the latch
struct Cpu {
  bool on = true, slow = false;
  enum { POLL, READ, PROC } st = POLL;
  uint64_t t0 = 0, tn = 0;
  bool tpb = false, rd = false;
  uint8_t at_start = 0, sample = 0;
  std::vector<uint8_t> got;
  int changed_under_read = 0, proc_us = 150;
  void tick() {
    if (!on) { rd = tpb = false; return; }
    if (st == POLL) { if (T >= tn && ready_ff) { st = READ; t0 = T + 1 + (uint64_t)(rand() % 10); } return; }
    if (st == PROC) { if (T >= tn) st = POLL; return; }
    if (T < t0) return;
    uint64_t dt = T - t0;
    if (!slow) {                                   // 1802 at ~1.76 MHz: read enable 2T..8T, TPB 7T..8T
      rd = dt < 4; tpb = dt >= 3 && dt < 4;
      if (dt == 0) at_start = latch;
      if (dt == 3) sample = latch;
      if (dt == 4) { got.push_back(sample); st = PROC; tn = T + proc_us; }
    } else {                                       // the bus driver's INP:n#: TPB ~250 us, D0-6 then D7 sampled
      rd = dt < 400; tpb = dt >= 100 && dt < 350;
      if (dt == 0) at_start = latch;
      if (dt == 175) sample = latch & 0x7F;
      if (dt == 275) sample |= latch & 0x80;
      if (dt == 400) { got.push_back(sample); st = PROC; tn = T + proc_us; }
    }
    if (rd && latch != at_start) { changed_under_read++; at_start = latch; }
  }
} cpu;

// ------------------------------------------------------------------ edges, interrupts, time
static void set_ready(bool r) { ready_ff = r; }
static void check_edges() {
  bool c = clk_line();
  if (last_clk && !c) EIFR.v |= 1;
  last_clk = c;
  bool ld = (DDRD.v & _BV(6)) ? (PORTD.v & _BV(6)) != 0 : true;
  if (!last_lddata && ld) {                        // LDDATA rising: the latch and READY
    latch = (uint8_t)((PORTC.v & 0x3F) | ((PORTB.v & 3) << 6));
    if (!cpu.tpb) set_ready(true);
  }
  last_lddata = ld;
  if (cpu.tpb) set_ready(false);                   // CLR held while TPB of the INP
  if (ready_ff != last_ready) { if (PCMSK0.v & _BV(2)) PCIFR.v |= 1; last_ready = ready_ff; }
  bool pu = (PORTD.v & _BV(7)) && !(DDRD.v & _BV(7));
  if (last_pd7pu && !pu) pd7_off_t = T;
  last_pd7pu = pu;
}
void sim_reg_written() { check_edges(); }
static void deliver() {
  if (!IE || in_isr) return;
  if ((EIFR.v & 1) && (EIMSK.v & 1) && int0_isr) {
    EIFR.v &= ~1; in_isr = true; IE = false; int0_isr(); IE = true; in_isr = false;
  }
  if ((PCIFR.v & 1) && (PCICR.v & 1)) {
    PCIFR.v &= ~1; in_isr = true; IE = false; isr_PCINT0_vect(); IE = true; in_isr = false;
  }
}
void sim_ie(bool on) { IE = on; if (on) deliver(); }
void sim_advance(uint64_t us) {
  for (uint64_t i = 0; i < us; i++) { T++; dev.tick(); cpu.tick(); check_edges(); deliver(); }
}
static bool pd7_level() {
  bool pu = (PORTD.v & _BV(7)) && !(DDRD.v & _BV(7));
  if (board == TEXT) return pu || T - pd7_off_t < 2000;         // open pin: keeps its charge a while
  if (strap_kind == 1) return pu;                                // marginal GFX: pull-up wins, R6 drains it when off
  return false;
}
uint8_t sim_pind() {
  uint8_t v = 1 | (PORTD.v & 2);
  if (clk_line()) v |= 4;
  if (PORTD.v & 8) v |= 8;
  if (dat_line()) v |= 16;
  if (PORTD.v & 32) v |= 32;
  if ((DDRD.v & 64) ? (PORTD.v & 64) : 1) v |= 64;
  if (pd7_level()) v |= 128;
  return v;
}
uint8_t sim_pinb() {
  uint8_t v = PORTB.v & 3;
  if (ready_ff) v |= 4;
  if (board == GFX) { if (mouse_on_pin) v |= 8; } else if (PORTB.v & 8) v |= 8;
  return (uint8_t)(v | (PORTB.v & 0x30));
}

// ------------------------------------------------------------------ test helpers
static void run_for(uint64_t us) { uint64_t end = T + us; while (T < end) { loop(); sim_advance(8); } }
static void check(bool ok, const char *what) { printf("  %s %s\n", ok ? "ok  " : "FAIL", what); if (!ok) fails++; }
static std::string hexs(const std::vector<uint8_t> &v) {
  std::string s; char b[4];
  for (uint8_t x : v) { snprintf(b, sizeof b, "%02X ", x); s += b; }
  return s;
}
static uint64_t kt;
static void kb(std::initializer_list<int> bs) { for (int b : bs) dev.schedule(kt, (uint8_t)b); kt += 15000; }
static void press(int c) { kb({c}); kb({0xF0, c}); }
static void press_ext(int c) { kb({0xE0, c}); kb({0xE0, 0xF0, c}); }
static bool find_key(char ch, int &code, bool &sh) {
  for (unsigned i = 0; i < sizeof kmap / sizeof kmap[0]; i++) {
    if (kmap[i][1] == (uint8_t)ch) { code = kmap[i][0]; sh = false; return true; }
    if (kmap[i][2] == (uint8_t)ch) { code = kmap[i][0]; sh = true; return true; }
  }
  return false;
}
static void type(const char *s) {
  for (; *s; s++) {
    int code; bool sh;
    if (!find_key(*s == '\n' ? 13 : *s, code, sh)) { printf("no key for %c\n", *s); continue; }
    if (sh) kb({0x12});
    press(code);
    if (sh) kb({0xF0, 0x12});
  }
}
static std::vector<uint8_t> bytes(const char *s) { std::vector<uint8_t> v; for (; *s; s++) v.push_back(*s == '\n' ? 13 : (uint8_t)*s); return v; }
static bool starts_with(const std::vector<uint8_t> &v, std::initializer_list<int> w) {
  size_t i = 0; for (int x : w) { if (i >= v.size() || v[i] != x) return false; i++; } return true;
}
static int count_seq(const std::vector<uint8_t> &v, std::initializer_list<int> w) {
  std::vector<int> ww(w); int n = 0;
  for (size_t i = 0; i + ww.size() <= v.size(); i++) { bool m = true; for (size_t j = 0; j < ww.size(); j++) if (v[i + j] != ww[j]) m = false; if (m) n++; }
  return n;
}
static void boot_keyboard() { board = TEXT; setup(); run_for(1200000); kt = T + 1000; dev.got.clear(); }
static void boot_mouse() { board = GFX; dev.mouse = true; dev.gap_us = 150; setup(); run_for(200000); }

// ------------------------------------------------------------------ tests
static void t_kb_start() {
  board = TEXT; setup(); run_for(1200000);
  printf("  device got: %s\n", hexs(dev.got).c_str());
  check(starts_with(dev.got, {0xFF, 0xED, 0x00}), "start: reset FF, then LEDs ED 00, bit-exact both ways");
  check(dev.host_parity_errors == 0, "no parity errors seen by the keyboard");
  check(!mouse_mode, "strap open -> keyboard mode");
  check(Serial.out.find("keyboard mode (TEXT)") != std::string::npos, "banner");
}
static void t_kb_typing() {
  boot_keyboard();
  type("Hello, World!\n");
  run_for(kt - T + 100000);
  check(cpu.got == bytes("Hello, World!\n"), "\"Hello, World!\" + Enter arrives exactly (Enter = $0D)");
  check(cpu.changed_under_read == 0, "the latch never changed under a read");
  if (cpu.got != bytes("Hello, World!\n")) printf("  got: %s\n", hexs(cpu.got).c_str());
}
static void t_kb_caps() {
  boot_keyboard();
  press(0x58); press(0x1C); kb({0x12}); press(0x1C); kb({0xF0, 0x12});          // Caps, a, Shift-a
  kb({0x58}); kb({0x58}); kb({0x58}); kb({0xF0, 0x58});                          // Caps held: repeats
  press(0x1C);
  run_for(kt - T + 100000);
  check(cpu.got == bytes("Aaa"), "Caps Lock: a -> A, Shift-a -> a; a held Caps Lock toggles once");
  check(count_seq(dev.got, {0xED, 0x04}) == 1 && count_seq(dev.got, {0xED, 0x00}) == 1, "LEDs: ED 04 once, ED 00 once");
  printf("  cpu got: %s  device got: %s\n", hexs(cpu.got).c_str(), hexs(dev.got).c_str());
}
static void t_kb_special() {
  boot_keyboard();
  press_ext(0x75);                                              // grey Up
  kb({0x12}); press_ext(0x75); kb({0xF0, 0x12});                // Shift + grey Up
  kb({0xE0, 0xF0, 0x12}); press_ext(0x75); kb({0xE0, 0x12});    // fake shifts (Num Lock on style) around Up
  press(0x75);                                                  // keypad 8, Num Lock off
  press(0x73);                                                  // keypad 5
  press(0x77); press(0x75);                                     // Num Lock on, keypad 8
  press(0x05); press(0x83); press(0x07);                        // F1 F7 F12
  press_ext(0x71); press_ext(0x70);                             // Delete, Insert
  press_ext(0x6C); press_ext(0x69); press_ext(0x7D); press_ext(0x7A); press_ext(0x6B); press_ext(0x74); press_ext(0x72);
  press(0x66); press(0x5A); press_ext(0x5A); press(0x76); press(0x0D); press_ext(0x4A);   // BS Enter kpEnter Esc Tab kp/
  kb({0x14}); press(0x21); kb({0xF0, 0x14});                    // Ctrl-C
  kb({0xE1, 0x14, 0x77, 0xE1, 0xF0, 0x14, 0xF0, 0x77});         // Pause
  kb({0xE0, 0x12, 0xE0, 0x7C}); kb({0xE0, 0xF0, 0x7C, 0xE0, 0xF0, 0x12});   // Print Screen
  press(0x1C);                                                  // a: no shift stuck
  run_for(kt - T + 100000);
  std::vector<uint8_t> want = {0x91, 0xD1, 0x91, 0x91, 0x94, '8', 0x80, 0x86, 0x8B, 0x9A, 0x99,
                               0x90, 0x96, 0x92, 0x98, 0x93, 0x95, 0x97, 0x08, 0x0D, 0x0D, 0x1B, 0x09, '/', 0x03, 'a'};
  printf("  got:  %s\n  want: %s\n", hexs(cpu.got).c_str(), hexs(want).c_str());
  check(cpu.got == want, "special keys: PAK-VI codes, Shift +$40, keypad by Num Lock, BS 08, Enter 0D, Esc 1B, Ctrl-C 03, Pause/PrtSc nothing");
  check(count_seq(dev.got, {0xED, 0x02}) == 1, "Num Lock LED");
}
static void t_kb_hotplug() {
  boot_keyboard();
  press(0x58);                                                  // Caps on
  kb({0xAA});                                                   // keyboard unplugged and plugged in again
  run_for(kt - T + 100000);
  check(count_seq(dev.got, {0xED, 0x04}) == 2, "$AA from the keyboard: LEDs (ED 04) sent again");
}
static void t_kb_during_led() {
  boot_keyboard();
  kb({0x58}); kt -= 15000 - 1500; kb({0x1C}); kb({0xF0, 0x58}); kb({0xF0, 0x1C});   // a pressed 1.5 ms after Caps
  run_for(kt - T + 100000);
  check(cpu.got == bytes("A"), "a key typed while the LED command waits for $FA is kept (R2-10) and comes after it");
  printf("  cpu got: %s  device got: %s  aborts %d\n", hexs(cpu.got).c_str(), hexs(dev.got).c_str(), dev.aborts);
}
static void t_kb_burst(bool slow) {
  boot_keyboard();
  cpu.slow = slow; cpu.proc_us = 2000;               // slower than the typing: a backlog builds
  const char *s = "the quick brown fox 0123456789";
  for (const char *p = s; *p; p++) { int code; bool sh; find_key(*p, code, sh); kb({code}); kt -= 15000 - 900; }  // makes 0.9 ms apart
  run_for(400000);
  check(cpu.got == bytes(s), slow ? "burst read by the bus driver's slow INP: no loss, no doubles" : "burst at 1802 speed: no loss, no doubles");
  check(cpu.changed_under_read == 0, "the latch never changed under a read");
  printf("  got %zu bytes, latch changes under a read %d, load retries %u: \"%.*s\"\n", cpu.got.size(), cpu.changed_under_read, load_retries, (int)cpu.got.size(), (const char *)cpu.got.data());
}
static void t_kb_stress() {
  boot_keyboard();
  srand(7);
  std::vector<uint8_t> want; bool caps = false;
  for (int i = 0; i < 300; i++) {
    if (i % 37 == 5) { kb({0x58}); kt -= 15000 - (uint64_t)(rand() % 3000); kb({0xF0, 0x58}); caps = !caps; kt -= 15000 - (uint64_t)(rand() % 3000); continue; }
    const char *letters = "abcdefghijklmnopqrstuvwxyz";
    char ch = letters[rand() % 26]; int code; bool sh; find_key(ch, code, sh);
    kb({code}); kt -= 15000 - (uint64_t)(rand() % 3000); kb({0xF0, code}); kt -= 15000 - (uint64_t)(rand() % 3000);
    want.push_back(caps ? ch - 32 : ch);
  }
  run_for(kt - T + 300000);
  check(cpu.got == want, "300 keys at random 0-3 ms spacing with Caps Lock LED commands in between: exact");
  printf("  got %zu of %zu, device aborts %d (host inhibits mid-frame), frame errors %u\n", cpu.got.size(), want.size(), dev.aborts, frame_errors);
}
static void t_mouse() {
  boot_mouse();
  check(mouse_mode, "strap 10k -> mouse mode");
  check(starts_with(dev.got, {0xF5}), "MOUSE-ON low at start: the mouse is told to stop ($F5)");
  for (int i = 0; i < 12; i++) dev.pkts.push_back({(uint8_t)(0x08 | (i & 1)), (uint8_t)i, (uint8_t)(0x80 - i)});
  dev.got.clear(); mouse_on_pin = true; run_for(1000000);
  printf("  device got: %s\n", hexs(dev.got).c_str());
  check(starts_with(dev.got, {0xFF, 0xF4}), "MOUSE-ON rises: reset FF ($FA $AA $00), enable F4");
  check(cpu.got == dev.sent_pkts && cpu.got.size() == 36, "12 packets reach the CPU whole and in order");
  check(cpu.changed_under_read == 0, "the latch never changed under a read");
  dev.got.clear(); mouse_on_pin = false;
  for (int i = 0; i < 5; i++) dev.pkts.push_back({0x09, 1, 1});
  run_for(300000);
  size_t n = cpu.got.size();
  run_for(300000);
  check(starts_with(dev.got, {0xF5}) && cpu.got.size() == n && cpu.got.size() <= 39, "MOUSE-ON falls: F5, nothing more reaches the CPU");
  printf("  device aborts %d (the $F5 request-to-send during a packet)\n", dev.aborts);
}
static void t_mouse_hotplug() {
  boot_mouse();
  mouse_on_pin = true; run_for(700000);
  dev.got.clear();
  dev.reporting = false; dev.outq.clear(); dev.outq.push_back(0xAA); dev.outq.push_back(0x00);   // replugged: BAT
  for (int i = 0; i < 4; i++) dev.pkts.push_back({0x08, 2, 3});
  run_for(1200000);
  printf("  device got: %s\n", hexs(dev.got).c_str());
  check(starts_with(dev.got, {0xFF, 0xF4}), "$AA $00 then silence: the mouse is reset and enabled again");
  check(cpu.got.size() == 12 && cpu.got == dev.sent_pkts, "its packets arrive after the restart");
}
static void t_mouse_late() {
  dev.present = false; boot_mouse();
  mouse_on_pin = true; run_for(3000000);
  dev.present = true; dev.got.clear(); dev.pkts.push_back({0x0A, 5, 6});
  run_for(3000000);
  check(starts_with(dev.got, {0xFF, 0xF4}), "no mouse at MOUSE-ON: retried every 2 s, started once plugged in");
  check(cpu.got.size() == 3, "and its packet arrives");
}
static void t_mouse_resync() {
  boot_mouse();
  mouse_on_pin = true; run_for(700000);
  for (int i = 0; i < 40; i++) dev.pkts.push_back({0x08, (uint8_t)(0x10 + i), (uint8_t)(0x18 | (i & 7))});   // Y bytes with bit 3 set: worst case
  run_for(55000); dev.corrupt_next = 1;                         // one byte goes bad (parity): dropped by the receiver
  run_for(600000);                                              // the stroke goes on (misaligned: Y always has bit 3)
  size_t before = cpu.got.size();
  run_for(100000);                                              // the mouse pauses
  for (int i = 0; i < 10; i++) dev.pkts.push_back({0x09, (uint8_t)(0x40 + i), 0x1F});   // the next stroke
  run_for(400000);
  std::vector<uint8_t> tail(cpu.got.begin() + (long)before, cpu.got.end()), want;
  for (int i = 0; i < 10; i++) { want.push_back(0x09); want.push_back((uint8_t)(0x40 + i)); want.push_back(0x1F); }
  printf("  frame errors %u; CPU got %zu bytes in the stroke, then %zu: %s\n", frame_errors, before, tail.size(), hexs(tail).c_str());
  check(before % 3 == 0, "a lost byte: only whole packets reach the CPU");
  check(tail == want, "the stream is aligned again after a 25 ms pause (the part packet is dropped)");
}
static void t_strap(Board b, int kind, bool want_mouse, const char *what) {
  board = b; strap_kind = kind; if (b == GFX) dev.mouse = true;
  setup(); run_for(20000);
  check(mouse_mode == want_mouse, what);
  printf("  pull-up read %u, release read %u\n", strap_pullup, strap_release);
}
static void t_vt100() {
  boot_keyboard();
  press_ext(0x75); press_ext(0x71); press(0x05); press_ext(0x7D);
  run_for(kt - T + 100000);
  std::vector<uint8_t> want = {0x1B, '[', 'A', 0x7F, 0x1B, '[', '5', '~'};
  printf("  got: %s\n", hexs(cpu.got).c_str());
  check(cpu.got == want, "KEYS_VT100 1: Up = ESC [ A, Delete = 7F, F1 nothing, PgUp = ESC [ 5 ~");
}

static void t_kb_inhibit() {
  boot_keyboard();
  kb({0x1C}); kb({0xF0, 0x1C});                                 // 'a'
  while (!(rx_n == 10 && clk_line() && dev.st == Dev::TX && dev.k == 10 && T > kt - 30000)) { loop(); sim_advance(1); }
  uint64_t t_hit = T;
  bool acked = ps2_command(0xF4);                               // host command in the high phase before the 11th clock
  run_for(kt - T + 100000);
  printf("  RTS at T=%llu, command acked %d, device aborts %d, cpu got: %s\n", (unsigned long long)t_hit, acked, dev.aborts, hexs(cpu.got).c_str());
  check(dev.aborts == 1, "the request-to-send came in the high phase before the 11th clock: the keyboard aborted");
  check(cpu.got == bytes("a"), "the aborted key arrives once (INT0 masked: the host's own edge did not complete the frame)");
}
static void t_kb_late() {
  dev.present = false; boot_keyboard();
  dev.present = true; dev.got.clear(); dev.outq.push_back(0xAA);  // plugged in: its self-test byte
  kt = T + 50000; type("ok\n");
  run_for(kt - T + 100000);
  check(starts_with(dev.got, {0xED, 0x00}), "no keyboard at start; plugged in later: its $AA brings the LED command");
  check(cpu.got == bytes("ok\n"), "and typing works");
}
static void t_mouse_on_at_start() {
  board = GFX; dev.mouse = true; dev.gap_us = 150; mouse_on_pin = true;     // an FTDI-only reset with MOUSE-ON = 1
  setup(); dev.pkts.push_back({0x08, 1, 2}); run_for(1000000);
  check(starts_with(dev.got, {0xFF, 0xF4}) && cpu.got.size() == 3, "MOUSE-ON already 1 at start: the mouse is started");
}
static void t_console() {
  boot_keyboard();
  Serial.out.clear(); Serial.in.push_back('?'); run_for(1000);
  printf("  %s", Serial.out.c_str());
  check(Serial.out.find("keyboard mode: LEDs 00, queue 0, READY 0") != std::string::npos, "'?' prints the status");
  Serial.out.clear(); Serial.in.push_back('d'); run_for(1000); press(0x1C); run_for(kt - T + 50000);
  check(Serial.out.find("kb 1C") != std::string::npos && Serial.out.find("-> 61") != std::string::npos, "'d': scan codes and loads shown");
  Serial.out.clear(); Serial.in.push_back('r'); run_for(1500000);
  check(Serial.out.find("restart") != std::string::npos && count_seq(dev.got, {0xFF, 0xED, 0x00}) == 1, "'r': the keyboard reset again");
}

int main(int argc, char **argv) {
  const char *t = argc > 1 ? argv[1] : "";
  printf("%s\n", t);
  if (!strcmp(t, "kb_start")) t_kb_start();
  else if (!strcmp(t, "kb_typing")) t_kb_typing();
  else if (!strcmp(t, "kb_caps")) t_kb_caps();
  else if (!strcmp(t, "kb_special")) t_kb_special();
  else if (!strcmp(t, "kb_hotplug")) t_kb_hotplug();
  else if (!strcmp(t, "kb_during_led")) t_kb_during_led();
  else if (!strcmp(t, "kb_burst_fast")) t_kb_burst(false);
  else if (!strcmp(t, "kb_burst_slow")) t_kb_burst(true);
  else if (!strcmp(t, "kb_stress")) t_kb_stress();
  else if (!strcmp(t, "mouse")) t_mouse();
  else if (!strcmp(t, "mouse_hotplug")) t_mouse_hotplug();
  else if (!strcmp(t, "mouse_late")) t_mouse_late();
  else if (!strcmp(t, "mouse_resync")) t_mouse_resync();
  else if (!strcmp(t, "strap_text")) t_strap(TEXT, 0, false, "TEXT: PD7 open -> keyboard mode");
  else if (!strcmp(t, "strap_gfx")) t_strap(GFX, 0, true, "GFX: R6 10k, typical pull-up -> mouse mode");
  else if (!strcmp(t, "strap_gfx_marginal")) t_strap(GFX, 1, true, "GFX: pull-up at its strongest (reads 1): the release test still finds mouse mode");
  else if (!strcmp(t, "vt100")) t_vt100();
  else if (!strcmp(t, "kb_inhibit")) t_kb_inhibit();
  else if (!strcmp(t, "kb_late")) t_kb_late();
  else if (!strcmp(t, "mouse_on_at_start")) t_mouse_on_at_start();
  else if (!strcmp(t, "console")) t_console();
  else { printf("unknown test\n"); return 2; }
  return fails ? 1 : 0;
}
