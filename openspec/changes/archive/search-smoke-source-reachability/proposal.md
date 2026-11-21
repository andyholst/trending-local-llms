# Proposal: search-smoke-source-reachability

Issue: #1224
PR: #1225

## Why

Raising the probe budget to 90s (change `search-smoke-realistic-budget`) made
nvidia and metal answer in 0.1s, but all four cpu queries still hung for 90s on
both attempts while the same mirror answered the other legs. The smoke answers
"is the mirror reachable?", not "is every curated query cached?"; reddening a
PR for one leg's query-level cache stall is the same misleading signal as the
3s client alarm it replaced — and it blocked every PR again.

## What Changes

- `scripts/smoke_search.py::main` collects each leg's outcome and then decides:
  a leg whose EVERY query misses is reported as `QUERY-STARVED` (non-blocking)
  when another leg proved the mirror reachable with a real HTTP 200 in the SAME
  run; a dead mirror that answers NO leg still blocks with the #258 majority
  verdict.
- A pytest-collectable guard proves both halves and is red on the old script.

## Impact

Per-leg signal is louder (the note names the starved leg and why it is not an
outage). No keyword, URL, credential, budget or credential rule changes.

## What is not covered

No change to the #258 majority rule for a genuinely unreachable source, to the
#291 upstream-5xx `OUTAGE` label, to the #858 yielded-empty vocabulary gate, or
to the separate `--require-hits` "search returns data" gate.
