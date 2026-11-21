# Proposal: stale-last-seen-gap

Issue: #1183
PR: #1216

## Why

The pipeline could not distinguish "no post exists" from "we stopped finding it" (rule 6o's
blindness for a model): the seven `qwen3.8-flash-next-125b*` rows sit at 2026-11-08/09 and
older, while `Edge0-145B (Qwen3.8-Flash-Next base)` is `🔥 trending, last seen 2026-11-16`
in the same rendered README. `last_seen` staleness was never a signal — `query-coverage` asks
whether a query NAMES a model and `search-smoke` whether a leg yielded nothing, but nothing
asked whether a model's newest capture aged out while a same-base sibling stayed current.
The list silently drops the most-measured model; the rank itself is correct (it uses 7-day
post buzz — see the correction on #1182).

## What Changes

- `scripts/data_gap_analysis.py`: `stale_last_seen(store)` detects a row whose `last_seen`
  is older than the store-wide newest by more than `update_trending.TRENDING_WINDOW_DAYS`
  (7 — the same window the rank uses) AND whose same-base sibling has newer captured
  evidence. The store-wide newest is the clock, never the wall clock (rule 2). ONE class
  signature entry `stale_last_seen` (#472 lesson — per-model entries re-filed 12 times);
  per-row evidence (id, last_seen, lag days, sibling, sibling date) lives in the report and
  issue BODY. The filer's existing per-entry marker dedup applies unchanged.
- `tests/test_stale_last_seen_gap.py`: 17 checks (detection, no false positives, signature
  + issue body + dedup marker, the shipped store's real flash-next gap, RED on the
  pre-change analysis, wiring).
- Additive only (rule 3b): the gap REPORTS a capture hole; it never shrinks a row, re-sorts
  history, invents a value, or changes the ranking. No data file changes.

## Impact

- Affected specs: `data-gap-analysis` (ADDED: a stale `last_seen` with a newer same-base
  sibling is a declared acquisition gap).
- Affected code: scripts/data_gap_analysis.py, tests/test_stale_last_seen_gap.py.
- Not covered: the #1182 aggregate-consistency defect, re-running the refresh (owner/cron
  dispatch only — never the agent), and adding posts that do not exist (rule 2).

## Verification

New suite 17/17; `tests/test_data_gap_analysis.py` 330/330; `validate --only data` QA PASSED;
lint_syntax OK (231 modules); linefeeds OK (3122 files). The shipped store's flash-next rows
are detected with the Edge0 sibling as evidence.
