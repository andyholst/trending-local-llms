# Tasks — ranked-gaps-ask-every-dimension (issue #460)

- [x] 1. `MODEL_FOOTPRINT_SUFFIX` widened to `vram ram context weights offload engine version` (`scripts/update_trending.py`) — verified: `footprint_query()` emits the words (test `test_a_footprint_query_names_each_ranked_model` checks each ask).
- [x] 2. `DIMENSION_ASK_TOKENS` + `dimensions_not_asked()` pin the suffix to `data_gap_analysis.DIMENSIONS` (rule 6d; unknown keys fall back to their own name) — verified: `test_every_ranked_gap_dimension_is_asked` asserts the real list against the real suffix.
- [x] 3. `make query-coverage` fails (exit 1) naming any ranked dimension no query asks; `--json` carries `dimensions_missing` — verified: guard CLI run green on the real store, test asserts `dimensions_missing == []`.
- [x] 4. Search contract updated: `skills/gather-data.md` + `.hermes/skills/data-search/SKILL.md` name all five footprint asks — verified: `test_the_rule_is_documented` pins the new skill line.
- [x] 5. AGENTS.md §6o wording + §8 guard row extended (rule 3c: the PR body names them; reviewer sign-off required) — verified: `make lint` + rule-number test green.
- [x] 6. README regenerated from the widened template (`make _render-readme`) — verified: `test_readme_generated` green.
- [x] 7. `ARCHITECTURE.md` regenerated (`make architecture-refresh`) and `make architecture-check`, `make lint`, `make openspec-check`, `make query-coverage`, `python3 tests/test_query_coverage.py` all green.
