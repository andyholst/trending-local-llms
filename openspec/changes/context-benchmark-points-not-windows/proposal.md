# Proposal: context-benchmark-points-not-windows

Issue: #1017

## Why

The gap scan reported `qwen3.8-27b-strix-halo-dflash2` as
`unstructured:context_tokens` — "stated in prose only, an ingest job" — because its
captured post text

> `0K context (21.11 t/s at 32K, 21.58 at 8K)`

matched the raw `_CTX_TEXT` window detector. That sentence is a MULTI-POINT benchmark
sweep: throughput measured at 32K and at 8K, plus a 0K baseline. It states NO single
context window, so the "ingest job" framing sends a backfill looking for a figure no
post states and keeps the real kind of gap (acquisition: a search must find a post that
states one) invisible. The same shape sits in both Flash-Next captures (`61 TPS at 100K
context, 50 TPS at 200K`); they escaped the report only through the added-since
allowlist in the tests (issue #1015 named exactly this).

## What Changes

- ONE model-aware claim reader `data_gap_analysis.context_tokens_claim(model, text)`
  wraps `_CTX_TEXT`, reached through the existing `dim_claim` accessor (the #1025
  pattern): a match whose figure is one of the throughput-qualified context points of a
  multi-point sweep segment (a `;`/sentence span carrying two or more sizes next to a
  `t/s`/`TPS` reading) is refused.
- A sentence boundary is a `;`, a newline, or a `.` followed by whitespace — never the
  dot inside a decimal (`21.11` must not fragment a sweep undetected).
- A window stated apart from a sweep still claims (even in the same text), and a LONE
  benchmark point stays claimable: only MULTI-point sweeps are refused, matching the
  issue's Done-when.
- The `context_tokens` dimension registers the reader as its `claim`; the real-store
  test allowlist no longer needs the sweep models.

## Impact

- `scripts/data_gap_analysis.py` — the claim reader + `context_tokens` dimension wiring.
- `tests/test_data_gap_analysis.py` — new `test_a_benchmark_sweep_states_no_context_window`
  (synthetic sweep/stated/lone cases) and the tightened real-store assertions:
  `unstructured:context_tokens == {qwen-3.6-27b}` exactly, dflash2 in `missing`.
- `AGENTS.md` §8 guard-row for the new test.

## Not covered

- Re-homing misattributed qwen-3.6-27b rows (#1016/#1018) — rule-3b owner decisions.
- The source-post readback evidence seam (`context_token_supports`, #994) — the two
  MTPLX rows legitimately carry the 200K their post states; this change touches only
  the gap CLASSIFICATION reader, no stored value.
