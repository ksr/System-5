// Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-11-01
// Arduino.h - a fake Arduino/AVR core for running ../video-g-ps2.ino on the host (sim.cpp defines the world behind it).
#pragma once
#include <stdint.h>
#include <stdio.h>
#include <string>
#include <deque>
#include <vector>

#define PROGMEM
#define pgm_read_byte(p) (*(const uint8_t *)(p))
#define F(s) (s)
typedef char __FlashStringHelper;   // F() strings are plain strings here
#define _BV(b) (1 << (b))
#define HIGH 1
#define LOW 0
#define INPUT 0
#define OUTPUT 1
#define INPUT_PULLUP 2
#define FALLING 2
#define HEX 16
#define DEC 10
#define PB0 0
#define PB1 1
#define PB2 2
#define PB3 3
#define PB4 4
#define PB5 5
#define PD0 0
#define PD1 1
#define PD2 2
#define PD3 3
#define PD4 4
#define PD5 5
#define PD6 6
#define PD7 7
#define INT0 0
#define INTF0 0
#define PCINT2 2
#define PCIF0 0
#define PCIE0 0

void sim_reg_written();
uint8_t sim_pinb();
uint8_t sim_pind();
void sim_advance(uint64_t us);
void sim_ie(bool on);
extern uint64_t T;

struct Reg {
  uint8_t v = 0;
  operator uint8_t() const { return v; }
  Reg &operator=(int x) { v = (uint8_t)x; sim_reg_written(); return *this; }
  Reg &operator|=(int x) { v |= (uint8_t)x; sim_reg_written(); return *this; }
  Reg &operator&=(int x) { v &= (uint8_t)x; sim_reg_written(); return *this; }
};
struct FlagReg {                       // write 1 to clear
  uint8_t v = 0;
  operator uint8_t() const { return v; }
  FlagReg &operator=(int x) { v &= (uint8_t)~x; return *this; }
};
extern Reg PORTB, DDRB, PORTC, DDRC, PORTD, DDRD, EIMSK, PCICR, PCMSK0;
extern FlagReg EIFR, PCIFR;
#define PINB (sim_pinb())
#define PIND (sim_pind())

inline void noInterrupts() { sim_ie(false); }
inline void interrupts() { sim_ie(true); }
inline unsigned long micros() { unsigned long t = (unsigned long)T; sim_advance(1); return t; }
inline unsigned long millis() { unsigned long t = (unsigned long)(T / 1000); sim_advance(1); return t; }
inline void delayMicroseconds(unsigned int us) { sim_advance(us ? us : 1); }
inline void delay(unsigned long ms) { sim_advance(ms * 1000); }

inline void pin_regs(uint8_t pin, Reg *&port, Reg *&ddr, uint8_t &bit) {
  if (pin < 8) { port = &PORTD; ddr = &DDRD; bit = pin; }
  else if (pin < 14) { port = &PORTB; ddr = &DDRB; bit = pin - 8; }
  else { port = &PORTC; ddr = &DDRC; bit = pin - 14; }
}
inline void pinMode(uint8_t pin, uint8_t mode) {
  Reg *port, *ddr; uint8_t bit; pin_regs(pin, port, ddr, bit);
  if (mode == OUTPUT) *ddr |= _BV(bit);
  else { *ddr &= ~_BV(bit); if (mode == INPUT_PULLUP) *port |= _BV(bit); else *port &= ~_BV(bit); }
}
inline int digitalRead(uint8_t pin) {
  if (pin < 8) return (sim_pind() >> pin) & 1;
  if (pin < 14) return (sim_pinb() >> (pin - 8)) & 1;
  return (PORTC.v >> (pin - 14)) & 1;
}
inline void digitalWrite(uint8_t pin, uint8_t val) {
  Reg *port, *ddr; uint8_t bit; pin_regs(pin, port, ddr, bit);
  if (val) *port |= _BV(bit); else *port &= ~_BV(bit);
}
extern void (*int0_isr)();
inline int digitalPinToInterrupt(int p) { return p == 2 ? 0 : p == 3 ? 1 : -1; }
inline void attachInterrupt(int n, void (*f)(), int) { if (n == 0) { int0_isr = f; EIMSK |= 1; } }
#define ISR(vec) void isr_##vec()

struct SimSerial {
  std::string out;
  std::deque<int> in;
  bool echo = false;
  void begin(long) {}
  void put(const std::string &s) { out += s; if (echo) fputs(s.c_str(), stdout); }
  void print(const char *s) { put(s); }
  void print(char c) { put(std::string(1, c)); }
  void print(int v, int base = DEC) { char b[24]; snprintf(b, sizeof b, base == HEX ? "%X" : "%d", v); put(b); }
  void print(unsigned v, int base = DEC) { print((int)v, base); }
  void print(long v, int base = DEC) { print((int)v, base); }
  void print(unsigned long v, int base = DEC) { print((int)v, base); }
  template <typename X> void println(X x) { print(x); put("\n"); }
  template <typename X> void println(X x, int base) { print(x, base); put("\n"); }
  void println() { put("\n"); }
  int available() { return (int)in.size(); }
  int read() { if (in.empty()) return -1; int c = in.front(); in.pop_front(); return c; }
};
extern SimSerial Serial;
