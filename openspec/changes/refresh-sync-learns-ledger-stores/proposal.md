# Proposal: refresh-sync-learns-ledger-stores

Issue: #997 — "`refresh_base.py`'s `GENERATED_PATHS` never learned the three ledger stores
`make merge` writes, so every refresh with new data is refused at `refresh-sync` and no refresh PR
can open"

## Why

`make refresh-sync` (scripts/refresh_base.py, issue #177) refuses a dirty tree whose changes fall
outside `GENERATED_PATHS` — the files a refresh is allowed to rewrite — so a reset can never
silently discard somebody's real edit. When the store was split into three ledgers (issues
#531/#888: measurement identity, post counters and ingest refusals), `update_trending.py` began
writing `data/measurements.json`, `data/posts.json` and `data/refusals.json` on every merge — but
`GENERATED_PATHS` still names only the pre-ledger set (`README.md`, `data/models.json`,
`data/gap_baseline.json`, `data/snapshots/`, `data/raw/`, `tests/fixtures/github_meta.json`). A
refresh that actually changes data therefore carries those three tracked ledgers as un-generated
dirty paths, and `refresh-sync` refuses the whole run: measured on runs 43681222348 and
43676720912 ending at `Commit + open PR if changed` with
`REFUSED: CANNOT SYNC: the tree carries changes a refresh does not generate: data/measurements.json,
data/posts.json, data/refusals.json …` — even while the same step had logged them as produced
(`[ok] wrote data/models.json (catalog), data/measurements.json, data/posts.json, README.md,
snapshot …`).

## What Changes

- `scripts/refresh_base.py::GENERATED_PATHS` gains `data/measurements.json`, `data/posts.json` and
  `data/refusals.json` — the three ledger stores `make merge` re-derives from the kept raw snapshots
  plus the fetched base, with the same re-derivation semantics as `data/models.json` (NOT added to
  `KEEP_PATHS`, which holds what the reset must retain).
- `tests/test_refresh_base.py` locks it **both ways**:
  1. a tree dirty in exactly those three ledgers (with the base moved behind it) SYNCS — exit 0,
     `sync=reset`, the ledgers reset to the base's copies — proving a real refresh's new data lands
     instead of being refused;
  2. a guard test asserts `GENERATED_PATHS` covers **every** store path `update_trending.py` writes,
     so a future ledger can never strand `refresh-sync` again.

## Impact

The refresh pipeline stops dying at `refresh-sync` whenever its merge changes the ledgers, so new
measurements/posts/refusals actually reach the store and a refresh PR can open. No other behaviour
changes: the sync still refuses any genuinely foreign dirty path, and the three ledgers are NOT
kept — they are re-derived by the doc's mandated `make merge` re-run.

## Not covered

No change to `KEEP_PATHS` (the ledgers remain re-derivable, so they are reset with the generated
tree). No change to `update_trending.py`'s write behaviour — only to the sync guard's enumeration of
what a refresh generates.
