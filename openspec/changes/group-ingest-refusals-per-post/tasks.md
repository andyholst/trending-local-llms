# Tasks

- [x] 1. The tracked change exists (this directory) before the merge
- [x] 2. `scripts/update_trending.py`: `_note_run_refusal` records every seam
      refusal keyed `(rule, model id, engine, post)`; the four per-snapshot prints
      are replaced by the grouped flush at the end of `ingest_raw_snapshots`
- [x] 3. `tests/test_ingest_refusal_grouping.py` locks the grouped line for a
      thrice-captured post, the no-swallow rule for distinct refusals, and the
      shipped-raw replay (unique per `(rule, engine, model, post)`, counts intact)
- [x] 4. `tests/test_cross_model_attribution.py` wiring assertion updated to the
      grouped flush (rule 6b)
- [x] 5. Gates green on the exact head: `make lint` green (workflow-guard-scan
      OK), `make openspec-check` green after this tick, `make architecture-refresh`
      + `architecture-check` green ("inventory block matches the tree, 190 lines"),
      `make openspec-index` + index-check green ("OPENSPEC.md is current:
      3 active, 333 archived"); `make test` green locally before the push (host
      suite, rule 6b change)
- [ ] 6. PR opens with the five-section body closing #882; `make
      openspec-record-pr ISSUE=882 PR=<pr>` archives at head; CI monitored green
