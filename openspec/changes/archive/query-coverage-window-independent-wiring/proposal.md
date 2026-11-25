# Proposal: query-coverage-window-independent-wiring

Issue: #1678
PR: #1684

## Why

`tests/test_query_coverage.py::test_the_prompts_and_the_guard_are_wired` keyed its
prompt-wiring assertion on the LIVE top-N trending derivation
(`UT.derived_queries(REAL_STORE)` and `UT.footprint_queries(REAL_STORE)`). Both come
from `update_trending.trending_models(store)`, which filters on
`model_band(m, now_utc())`, so the assertion silently depended on the WALL CLOCK
against the store's age. The store is refreshed weekly; once every `last_seen` is
older than `TRENDING_WINDOW_DAYS` (7) the band is legitimately empty and the suite
red'd repo-wide, blocking every open PR. Measured on master with identical data and
query code: run 45511338595 (`ab7a672b`) validate SUCCESS at 2026-11-24T23:36Z and
run 45514736549 (`e93bc67d`) validate FAILURE at 2026-11-25T00:01Z — only the date
rolled past the 7-day edge. That is an empty-but-valid ranked set reported as a
wiring failure.

## What Changes

- Add ONE seam, `scripts/query_coverage.py::prompt_queries(store)`: every derived
  query a search leg appends — the union of the TOP-N trending pair and the
  QUERY_AGED_N most-aged pair — and route `--queries` through it, so the CLI and the
  wiring test read the same implementation and cannot disagree.
- Anchor `test_the_prompts_and_the_guard_are_wired` on that union: the set must be
  non-empty and EVERY query in it must appear in the expanded `_search-amd` prompt;
  the top-N trending half is additionally asserted whenever the store has one.
- Add `test_the_prompt_derivation_survives_an_aged_out_trending_band`, a RED-first
  regression test over a synthetic aged-out store that fails on the pre-change tree.
- Leave `make query-coverage` untouched: it still exits 1 when a ranked model no
  query names, and `--top 0` is still refused (rule 6o intact).

## Impact

No data, contract, format, make target, workflow or image change. The coverage
guard's DECISION is unchanged; only the test's expectation stops depending on the
engagement window. A stale store still owes its owner-dispatched refresh (rule 6t) —
this change does not fabricate freshness.

## Not covered

- No change to `query_coverage.py`'s exit-code contract, its `--top 0` refusal, or
  `update_trending.trending_models`.
- No refresh of the stale `data/models.json`; landing data is an owner act.
- No `AGENTS.md` rule change.
