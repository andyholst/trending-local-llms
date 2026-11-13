# Proposal: write-raw-snapshot-copy-payload

Issue: #646

## Why

`write_raw_snapshot` copies only the top level of its payload
(`payload = dict(payload)`) and then rewrites `_m["id"]`, `_m["hf"]`,
`_m["formats"]` and `_m["engines"]` **in place** — those nested dicts are the
CALLER's objects. A caller that re-uses its payload (a retry, a second backend,
a future batch write) silently sees ids it never composed (`qwen3.8-27b-mlx_srv`
rewritten to `qwen3.8-27b-mlx-srv` inside its own dict) and format dicts whose
`hf` a previous write rewrote (issue #646).

## What Changes

- `write_raw_snapshot` becomes copy-on-write: each model dict and each format
  dict is copied before the normalization/refusal pass rewrites it, so the
  written snapshot carries the normalized values and the caller's payload is
  byte-for-byte unchanged. No other observable behaviour changes — same file
  naming, same `[write-raw] WARN:` refusals, same engine_repo stripping, same
  `generated_utc`.
- One new test locks it: the caller's payload is deep-compared before/after the
  call, and the same write still proves normalization, the 404-model drop and
  the URL collapse in the written snapshot.

## Impact

- `scripts/update_trending.py` — `write_raw_snapshot`'s model and format loops
  (no new make target; the `--write-raw` CLI already calls it).
- `tests/test_ingest_hf_verify.py` — new
  `test_write_raw_never_mutates_the_caller_payload`, RED on the pre-change
  writer (verified against `git stash` of the old `scripts/` file).
- `AGENTS.md` §8 guard table gains the row.

## Not covered

- Engine measurement dicts: the writer never mutates them in place today (the
  `engine_repo` strip already builds a fresh dict), so no copy is added there.
- Deep copies of values no code path writes (rule 3b: no gratuitous change).
