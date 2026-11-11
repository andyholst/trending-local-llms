# Proposal: one-post-one-row

Issue: #389 — `tech-debt: One real post becomes several store measurements that disagree`

## Why

`merge_engines` decides "same measurement" by engine + GPU-size identity + a concordant t/s
(within 5%). A post captured twice — different hardware wording, a different t/s, a re-scan
in an overlapping window — therefore stayed **several store rows**, each carrying its own
copy of the run's dimensions. Measured on the store:

- `qwen3.6-35b-a3b`: **four** Ollama rows dated `2026-10-16` from
  `.../niklaslenz_ai/status/2111204284453044383`, two with `context_tokens: "66000"` and two
  with `"67000"`;
- `qwen3.8-27b`: **two** llama.cpp rows dated `2026-10-14` from
  `.../Oluwaphilemon1/status/2110312777415893173` with `8192` and `65536`.

The card-fit and traceability views then read contradictory dimensions for what the source
recorded once — and the duplicate rows inflate a model's measurement counts.

## What Changes

- **`_real_post(m)`** — the model-agnostic identity of a post: its `/status/<id>` URL, or
  `""` for a placeholder (a bare mirror link, a profile page, nothing). Placeholder posts are
  explicitly **not** a key: keying on `""` would collapse every uncited row in the store.
- **`_collapse_one_post(rows)`** — rows sharing `(engine, date, source_post)` collapse into
  one: the **highest t/s** is kept (never averaged down or lowered), engagement counters are
  kept at their max (never shrunk), and `MEASUREMENT_DIMENSION_FIELDS` fill only (a stated
  value is never overwritten, an unstated one never invented) — AGENTS.md §2.3b at
  measurement level.
- **`merge_engines` runs it FIRST**, so the ingest seam — not just a direct caller — produces
  one row per post; the existing engine/GPU-size/concordance grouping then works on the
  deduplicated set.
- **`COUNTER_FIELDS`** named once, beside `MEASUREMENT_DIMENSION_FIELDS`.
- **`tests/test_one_post_one_row.py`** (13 checks): the measured four-row case collapses to
  one with the highest t/s and a single `context_tokens`; two posts stay two; one post with
  two engines stays two; placeholders never group; a stored value is never overwritten and an
  unstated one is filled; the ingest path (`merge_engines`) is the one under test; and the
  store's own two measured models have no contradictory duplicate left.

**Two fixtures updated in the same change (rule 6b), because the contract changed:**
`test_7day_aggregation.py`'s synthetic rows all shared ONE `source_post` — a shortcut that now
means "one measurement", so each row gets its own post (the cases are about t/s concordance);
and `test_engine_aliases.py` asserted the store's row count is unchanged by a re-ingest, which
may now legitimately FALL when the store itself holds duplicates — it asserts no growth plus
"nothing left to collapse" instead. The collapse also never writes an explicit null into a
dimension (a `weight_gb: null` fails `model_contract`, measured here).

Verified RED against the pre-change script (both symbols missing → the guard fails naming
them) and GREEN after (`PASSED 13 | FAILED 0`; full suite `[test] 63 module(s) passed`).

## Impact

`scripts/update_trending.py` (two helpers, one tuple, one call in `merge_engines`), a new
`tests/test_one_post_one_row.py`, this OpenSpec change and the regenerated `OPENSPEC.md`. No
store edit: the existing duplicates clean up on the next ingest that touches them, and the
collapse can only raise a t/s or a counter (rule 3b). No target, stage, job or image changes.

## Not covered

- **Cleaning the store by hand.** The fix is at the ingest seam; rewriting `data/models.json`
  here would be an unreviewable data diff, and the next refresh re-ingests the raws anyway.
- **A post that genuinely states two different runs** (two quants, two t/s on one post). The
  issue asks for `(engine, date, source_post)`; a per-quant key would be a different rule, and
  a post stating two quants is the case to bring back as evidence before changing it.
