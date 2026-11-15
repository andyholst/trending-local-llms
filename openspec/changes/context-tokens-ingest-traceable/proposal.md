# Proposal: context-tokens-ingest-traceable

Issue: #991 — "data-gap: context_tokens (69 models) (2026-11-15)"

## Why

The ranked `context_tokens` gap on the shipped store lists models whose captured
post states a context figure the store holds only as free text, not as the
structured `context_tokens` measurement key. Most of that list is an ACQUISITION
gap (no captured post states a figure — only a new search can close it, which
the refresh's footprint queries already re-ask, rule 6o) or an untraceable/
estimate class. But two of the named models are a genuine INGEST gap: the
captured post states the context window and the value is correctly attributed,
so structuring it closes a real gap without inventing anything.

- `qwen3-8-flash-next-125b` / MTPLX 126.5 t/s — the captured post
  (Oluwaphilemon1/…/2113748519588635100) states "61 TPS at 100K context, 50 TPS
  at 200K"; the row has no structured `context_tokens`.
- `qwen3-8-flash-next-125b-mtplx-rd1-1` / MTPLX 126.5 t/s — the same post states
  "50 TPS at 200K"; the row has no structured `context_tokens`.

Adding `context_tokens: "200K"` to those two measurements is additive (rule 3b),
contract-declared (the measurements contract already declares `context_tokens`
as an OPTIONAL string), and traceable to the exact post the measurement cites —
so the `data`-stage source-post readback gate stays clean.

## What Changes

- `data/measurements.json`: the `MTPLX` measurement on `qwen3-8-flash-next-125b`
  and the `MTPLX` measurement on `qwen3-8-flash-next-125b-mtplx-rd1-1` each gain
  `"context_tokens": "200K"` (the exact figure their shared source post states).
- Adds a shipped-store regression guard under `tests/test_data_gap_analysis.py`
  locking: the two rows carry the structured `context_tokens` figure that their
  source post states, and `source_post_figure_flags` reports no hard
  (`gated`) readback contradiction on them (issue #789).

## Impact

- The `context_tokens` ingest-gap count drops by 2 (from 4 stated-in-prose to 2);
  the remaining two are a misattributed row (`qwen-3.6-27b`) and an ambiguous
  test-point row (`qwen3.8-27b-strix-halo-dflash2`), both recorded as findings.
- README regenerated (`make merge` / `make _render-readme`), so the store and
  the generated tables stay in sync (rule 4). No contract, prompt, workflow or
  ingest-script behaviour changes.

## Not covered

- The 63 acquisition-gap models (a fresh search closes them; the footprint
  queries already re-ask their ids).
- The 2 declared-estimate `context_tokens` values (re-ask a search), the
  `qwen-3.6-27b` misattributed "80k" post (removal is a rule-3b human decision)
  and the storage/engine_min_version false positives. Each is filed as a
  finding (rule 6g).
