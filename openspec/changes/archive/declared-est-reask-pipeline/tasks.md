# Tasks

- [x] 1. The tracked change exists (this directory) before any code edit
- [x] 2. `scripts/declared_estimate.py` is the one detector: marker regex, footprint field set, `has_declared_estimate()`, `footprint_estimates()` (measurement rows AND model rows)
- [x] 3. `data_gap_analysis.py` imports the module (no own regex) and reports `declared_estimates`
- [x] 4. Signature carries the class once per field (`reask_estimate:<field>`); an empty class adds nothing
- [x] 5. `render()` and `issue_body()` name every model+field as re-askable (rule 6o footprint query replaces it; rule 3b forbids deleting the estimate)
- [x] 6. Guards: `test_declared_estimates_surface_as_a_reaskable_class` + `test_the_declared_estimate_detector_is_one_detector` (field set == DIMENSIONS, analysis carries no marker regex)
- [~] 7. `validate.py` imports the module instead of its own `_DECLARED_ESTIMATE` literal — blocked: issue #933 (the validator side) must merge into `master` first; this branch rebases onto it and collapses the copy in the same change
- [x] 8. `ARCHITECTURE.md` §6 row for the new script; inventory regenerated (`make architecture-refresh`)
- [x] 9. `AGENTS.md` §8 guard row added in the same change (rule 6c)
- [x] 10. `OPENSPEC.md` regenerated; `make lint`, `make data-gaps`, `make test`, `make openspec-check` green; PR opened against #936 and monitored to green
- [~] 11. This change archived on its own closing head by `make openspec-record-pr ISSUE=936 PR=<pr>` — blocked: the PR number exists only after `gh pr create`; the record runs on this branch immediately after opening (rule 6f's required shape)
