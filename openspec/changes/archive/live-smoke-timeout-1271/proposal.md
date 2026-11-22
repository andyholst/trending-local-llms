# Proposal: live-smoke-timeout-1271

Issue: #1271
PR: #1275

## Why

`.github/workflows/qa-validate.yml` gives the `live-smoke` job `timeout-minutes: 25`,
but the job probes the 29 curated queries (`scripts/query_vocab.py`: nvidia 11,
metal 5, cpu 4, amd 9) at `SEARCH_SMOKE_BUDGET ?= 90` with one retry, so one query
can cost 180s and the four sequential legs up to ~87 min. On a degraded lightbrd
mirror the job is killed at 25 min before it can render its #291/#296 outage
verdict, and a `cancelled` job is not green — `auto-merge` needs `live-smoke`
green, so every open PR is blocked at once (measured 2026-11-22: ten qa-validate
runs cancelled ~25 min after creation; issue #1271).

## What Changes

- The `live-smoke` job's `timeout-minutes` is raised to cover the worst-case probe
  time of the full query set (29 queries x 90s x 2 attempts = 5220s) with margin.
- A guard test pins the job timeout against the real query vocabulary, the
  Makefile budget and the retry count, so a later budget raise that is not
  matched by the timeout goes red — the exact #1224 mismatch.

## Impact

- `.github/workflows/qa-validate.yml` — the `live-smoke` job timeout only; the
  #258/#291/#296 verdict logic is untouched.
- `tests/test_smoke_search.py` — a new guard test reading the workflow, the
  vocabulary and the Makefile pin.
- `AGENTS.md` §8 gains the guard row; `ARCHITECTURE.md` §4's `live-smoke` row
  names the timeout contract.

## Not covered

- Short-circuiting a proven outage mid-leg (a follow-up; the per-leg verdict
  logic is unchanged here).
- The per-query budget itself (#1224's 90s pin is the contract).
