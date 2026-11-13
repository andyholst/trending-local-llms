# Tasks

- [x] 1. The tracked change exists (this directory) and its `.openspec.yaml` is the `openspec-new` scaffold
- [x] 2. The owed text was read from #745's own body, not re-invented
- [x] 3. §8 gains the `test_capture_meta_keeps_the_fixture_covering_the_registry` row beside its sibling rows, naming BOTH commit-step lists and citing #745 + #505/PR #744
- [x] 4. `tests/test_agents_rows.py` gains `test_the_engine_meta_row_is_written` (row present, module named, failure stated, citations, sibling placement, guard is a real function of that module, the workflow's two lists still name the fixture) and is registered in `main()`
- [x] 5. Verified RED on the pre-change `AGENTS.md` (`git show origin/master:AGENTS.md` → 5 FAILED naming "row absent") and GREEN after (75 PASSED / 0 FAILED)
- [x] 6. `OPENSPEC.md` regenerated; `make openspec-check` green
- [x] 7. `make lint`, `make architecture-check`, `make secret-scan`, `make test` green
- [x] 8. `findings.md` written and `make findings-check` green
