# Tasks

- [x] 1. The tracked change exists (this directory) before any code edit
- [x] 2. `merge_engines` fills the representative measurement's dimension keys from the other members of its concordant group, fill-only
- [x] 3. A higher-engagement incoming row can no longer drop a dimension the store already held
- [x] 4. The 21 unambiguous captured measurement cells are backfilled into `data/models.json` (8 models)
- [x] 5. `tests/test_measurement_footprint.py` drives the REAL ingest for both merge orders (store row wins; incoming row wins)
- [x] 6. `tests/test_data_gap_analysis.py` proves every measurement-level dimension value appears verbatim in the model's captured raw text, and locks a coverage floor (43 measurements)
- [x] 7. `README.md` regenerated from the store; the card-fit tables read the new per-measurement `weight_gb`
- [x] 8. `findings.md` records the analysis' model-only counting and the duplicate measurement rows this run found, as their own work
- [x] 9. `OPENSPEC.md` regenerated; `openspec-index-check` and `check_openspec_tasks` green
- [x] 10. `make validate`, `make validate-mapped`, `make test`, `make openspec-check` and `make architecture-check` green
