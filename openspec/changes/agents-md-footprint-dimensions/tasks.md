# Tasks

- [x] 1. The tracked change exists (this directory) before the rulebook edit, with its `agents-rulebook` capability spec and this checklist
- [x] 2. `AGENTS.md` §4 — the `data/models.json` bullet's footprint sentence names all five optional per-measurement dimensions, says why the minimum engine build belongs on the measurement, and cites `#337` / `#371` (the sentence issue #375 spelled out verbatim; the write is the review-required diff of rule 3c)
- [x] 3. `AGENTS.md` §8 — one guard row for the new pin, in the same change (rule 6c)
- [x] 4. `tests/test_measurement_footprint.py::test_the_rulebook_names_every_measurement_dimension` derives the dimension set from `scripts/data_gap_analysis.DIMENSIONS` and the contracts' measurement items — no second hand-maintained list (rule 6d)
- [x] 5. The pin FAILS on the pre-change `AGENTS.md` (exactly one missing dimension, `engine_min_version`) and is GREEN with the sentence applied
- [x] 6. The pin also refuses a name §4 lists that no contract declares, and a ranked dimension with no measurement key in either contract
- [x] 7. `OPENSPEC.md` regenerated (`make openspec-index`); `make openspec-index-check` and the tasks gate green
- [x] 8. `make test`, `make lint` and `make openspec-check` green; `README.md` / `data/**` untouched (no data changed, `check_no_value_loss` has nothing to compare)
- [x] 9. `ARCHITECTURE.md` needs no edit — no make target, stage, pipeline job, image or script is added or renamed (rule 6h)
- [x] 10. `findings.md` records what this run noticed and did not fix (rule 6g)
