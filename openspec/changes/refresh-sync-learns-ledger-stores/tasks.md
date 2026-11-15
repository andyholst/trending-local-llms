# Tasks

- [x] 1. The tracked change exists (this directory) before any script or test edit (rule 6f)
- [x] 2. `scripts/refresh_base.py::GENERATED_PATHS` names ALL store files `data/update_trending`'
      merge writes: the existing `data/models.json` AND `data/measurements.json`,
      `data/posts.json`, `data/refusals.json` — additive, none moved to `KEEP_PATHS` (rule 3b)
- [x] 3. `tests/test_refresh_base.py` gains a "tree dirty exactly in the three ledgers SYNCS"
      test — a fixture whose base moved and whose only dirty paths are the three ledger stores
      exits 0 with `sync=reset`, the ledgers reset to the base's copies
- [x] 4. `tests/test_refresh_base.py` gains the coverage guard — `GENERATED_PATHS` covers every
      store path `update_trending.py` writes (the ledger names AND the model catalog), so a
      future ledger cannot strand `refresh-sync` again
- [x] 5. Gates green on the exact head: `make test` (this suite), `make validate`, `make lint`,
      `make openspec-check` (index regenerated), `make architecture-check` (no target/job/script
      changed)
