# Tasks

- [ ] 1. Write the proposal + spec for the untraceable-figure class (issue #470).
- [ ] 2. `scripts/data_gap_analysis.py`: `analyse()` classifies a stated figure no captured post states as `untraceable` (never `unstructured`), keeping the four classes a disjoint partition of `missing`.
- [ ] 3. `scripts/data_gap_analysis.py`: `stated_untraceable()` + `unattributed_figures()` as the ONE implementation, plus `has_real_post()` over `update_trending._is_post_url`.
- [ ] 4. `scripts/data_gap_analysis.py`: `render()`/`issue_body()` name the class and its models as a CAPTURE job; `_gap_kind()` gives it its own kind; the class adds NO signature entry.
- [ ] 5. `scripts/validate.py`: `check_untraceable_figures` — FAIL an unattributable stated figure, REPORT the history — registered in the `data` stage.
- [ ] 6. `.hermes/skills/data-search/SKILL.md`: a requirement figure lives on the measurement whose post states it, never only in model-level prose.
- [ ] 7. `tests/test_data_gap_analysis.py`: the class, the partition, the two artefacts, the validator halves and the skill rule; the existing split/partition/detector tests updated for the fourth class.
- [ ] 8. `AGENTS.md` §8: the guard row for the class and the check.
- [ ] 9. `OPENSPEC.md` index refreshed (`make openspec-index`).
- [ ] 10. `findings.md` written and `make findings-check` green.
- [ ] 11. Gates green: `make lint`, `make test`, `make validate`, `make validate-mapped`, `make architecture-check`, `make openspec-index-check`, `make openspec-tasks-check`.
