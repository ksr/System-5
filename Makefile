# System-5 QA entry points: the same three targets as in YACC1-D, p8x and P32W (2026-11-20).
# None of them changes a tracked file; a skipped test is reported, never counted as a pass.
# tools/qa.py says what each runs.
#
#   make qa-quick   ~4 min   before every commit (the fast s5emu suites, busdrv, the netlist proofs, ...)
#   make qa         ~50 min  the whole suite, before an order (adds the gate-level s5emu suites, GBASIC, ...)
#   make qa-fresh   ~5 s     every committed firmware/software build against a fresh one (in a temp copy)
#
# The builds themselves stay where they are (firmware/*/build.py, software/*/build.py, gen/build.sh).

.PHONY: qa-quick qa qa-fresh

qa-quick:
	python3 tools/qa.py quick

qa:
	python3 tools/qa.py full

qa-fresh:
	python3 tools/qa.py fresh
