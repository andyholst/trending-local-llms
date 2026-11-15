# refresh-sync-guard

## ADDED Requirements

### Requirement: a refresh's generated set covers every store file `make merge` writes

`refresh_base.GENERATED_PATHS` MUST name every tracked store file that `data/update_trending`'s
merge writes — the model catalog `data/models.json` AND the three ledgers `data/measurements.json`,
`data/posts.json`, `data/refusals.json` — so a tree carrying those files as dirty is treated as the
refresh's own generated output (reset + re-derived by `make merge`), never as foreign work that
refuses the sync. None of them is added to `KEEP_PATHS`: whether the reset retains a path and
whether the sync treats it as re-derivable are two separate questions, and the ledgers are
re-derived from the kept raw snapshots plus the fetched base, exactly like `data/models.json`.

#### Scenario: a tree dirty only in the three ledger stores syncs onto the moved base

- **Given** a checkout behind its fetched base whose only dirty tracked paths are
  `data/measurements.json`, `data/posts.json` and `data/refusals.json` (the exact shape a merge
  that changed data leaves behind)
- **When** `make refresh-sync` runs on it
- **Then** it exits 0 with `sync=reset`, resets onto the fetched base, and its ledger files now
  hold the base's copies (they are re-derived by the following `make merge`)
- **Test:** tests/test_refresh_base.py::test_sync_accepts_a_tree_dirty_only_in_the_ledger_stores

#### Scenario: a dirty path a refresh does not generate is still refused

- **Given** a checkout whose dirty tree includes a path outside `GENERATED_PATHS` (for example a
  new `scripts/some_guard.py`)
- **When** `make refresh-sync` runs on it
- **Then** it exits 1 with `REFUSED: CANNOT SYNC`, names the path, and leaves the edit in the tree
- **Test:** tests/test_refresh_base.py::test_sync_refuses_a_dirty_path_a_refresh_does_not_generate

### Requirement: the sync guard stays in sync with what the store writes

`tests/test_refresh_base.py` MUST prove `GENERATED_PATHS` covers every store path that
`update_trending.py` writes, so adding a future ledger to the merge output strands `refresh-sync`
loudly (the test goes red) instead of silently refusing every refresh again. The enumerated set is
derived from the writer itself, never a second hand-maintained copy of the path list.

#### Scenario: every `_DATA_DIR / "*.json"` store path the writer defines is generated

- **Given** the store-path definitions `update_trending.py` declares (its `_DATA_DIR / "<name>.json"`
  constants)
- **When** each is checked against `refresh_base.GENERATED_PATHS`
- **Then** every one resolves under `GENERATED_PATHS` (catalog and ledgers alike), so a future
  ledger the writer gains is covered by the guard
- **Test:** tests/test_refresh_base.py::test_generated_paths_cover_every_store_path_update_trending_writes
