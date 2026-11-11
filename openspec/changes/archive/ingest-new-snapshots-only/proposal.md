# Proposal: ingest-new-snapshots-only

Issue: #175

## Why

`ingest_raw_snapshots` walked `sorted(RAW_DIR.glob("*.json"))` on every merge —
every raw snapshot ever written, for ever. Measured on a store that already
contained all but 5 of the models:

```
[info] ingested raw snapshots: 5 added, 210 updated
```

on every run, against a `data/raw/` holding hundreds of snapshots. Three costs,
all of them growth with history for zero new information:

- the work grows with the whole raw history (every model re-merged, every
  placeholder post re-derived) on every refresh and every fix round;
- the log says nothing about **which** file introduced a change — `5 added, 210
  updated` names no snapshot, so a refresh cannot be read as "what is new today";
- a re-run of `make merge` is only accidentally idempotent, which is what the
  fix-bot round trip and `make qa-report` rely on.

A snapshot older than the store's own `generated_utc` was captured before the
last merge, so its content is already in the store. Re-merging it cannot add
anything.

## What Changes

- **`scripts/update_trending.py` — `ingest_raw_snapshots(store, since=None)`.**
  A snapshot whose capture instant is **not strictly newer** than `since` is
  skipped. The date is read from the snapshot's own `generated_utc`, falling
  back to the `<backend>-<YYYYMMDD>-<HHMMSS>.json` stamp its writer put in the
  filename. A snapshot whose date cannot be read either way is **always
  merged** (fail-open): a file this code cannot place in time is never silently
  dropped, so the boundary can only skip what it can prove is old.
- **`scripts/update_trending.py` — `main()` derives the boundary** from the
  store's `generated_utc`, so every `make merge` / `make merge-fetch` is
  incremental without any caller change. `--since <ISO8601Z>` overrides it, and
  a malformed stamp is refused loudly rather than silently disabling the
  boundary.
- **`scripts/self_correct_raw.py` — a corrected snapshot is re-merged, never
  skipped as "old".** The module has always documented "re-writes the file in
  place only when changes were made" but wrote unconditionally; it now writes
  only when the snapshot actually changed and, when it did, refreshes its
  `generated_utc`. The refresh pipeline runs `make correct-raw` *after*
  `make merge-fetch`, so without this a correction applied in run N would never
  reach the store: run N+1 would skip the snapshot as old. The refreshed stamp
  is what re-admits it.
- **`tests/test_ingest_watermark.py`** (new) — the boundary, the fail-open
  path, the filename fallback, the `--since` override end to end through the
  real CLI, and the corrected-snapshot re-merge.
- **`Makefile`** — the new module is added to the `_test` fallback chain, so it
  runs whether pytest is available or not.
- **`ARCHITECTURE.md`** — the merge/correct-raw target rows and the two scripts
  rows name the boundary (rule 6h).
- **`AGENTS.md` §8** — the guard row this change owes (rule 6c) is **owed, not
  written**: the file is protected and the write was refused, so the row, its
  exact text and the rule 3c disclosure are recorded on issue #175 and in
  `findings.md` for a reviewer to apply. `AGENTS.md` is otherwise untouched.

## Impact

`scripts/update_trending.py`, `scripts/self_correct_raw.py`, `Makefile` (the
`_test` chain), `tests/test_ingest_watermark.py` (new), `ARCHITECTURE.md`, the
OpenSpec change + `OPENSPEC.md`. `AGENTS.md` is unchanged — its §8 row is owed
and recorded for review (see above).

No `data/**` file is edited and no store key changes: the boundary only decides
**which raw files are read**, and every snapshot it skips is one an earlier
merge already folded in. Gates: `make lint`, `make test`, `make validate`,
`make validate-mapped`, `make openspec-check`, `make architecture-check`.

## Not covered

- **A raw edited in place by something other than `self_correct_raw`.** The
  boundary is a date, not a content fingerprint. `self_correct_raw` refreshes the
  stamp when it corrects a snapshot, but an edit that does not go through it
  (the fix prompt also tells the agent it may update `data/raw/*.json` directly)
  is not re-admitted unless it also refreshes `generated_utc`. The fix prompt
  requires the same correction in `data/models.json`, so the fix still lands —
  but the coupling is real and is filed as its own finding rather than solved
  here.
- **Snapshots already in the store are not re-validated.** The boundary trusts
  `generated_utc` to mean "already merged". A store whose stamp is wrong in the
  other direction (older than a snapshot it did merge) simply re-merges that
  snapshot — the fail-open direction.
- **Per-model files / a merge driver**, one of the two options the issue offered
  for the overlap problem in refresh PRs (#177). This change takes the
  `--since` boundary option, which adds no new generated file and so adds no new
  conflict.
