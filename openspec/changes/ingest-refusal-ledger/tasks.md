# Tasks

- [x] 1. `scripts/update_trending.py`: `REFUSALS_FILE`, the ONE stage registry
      `REFUSAL_STAGES`, `record_ingest_refusals` (append-only, unknown stage refused),
      and every existing refusal seam records before dropping
- [x] 2. `scripts/data_gap_analysis.py`: `load_refusals`, the "REFUSED at ingest"
      report class beside acquisition/ingest, identity stages derived from the writer's
      registry, refusal-aware gap signature
- [x] 3. `tests/test_ingest_refusal_ledger.py`: the REAL seams over a real raw fixture
      + the REAL `analyse` (rule 6m) — ledger fields, append-only, corrupt-ledger
      stands, unknown stage raises, call-site tree scan, analysis distinction,
      signature change
- [x] 4. `AGENTS.md` §8 guard row for the new suite
- [x] 5. `make openspec-check`, the new suite, and the surrounding suite green on the
      branch; PR opened with the five-section body closing #888 (CI state reported
      honestly on the PR)
