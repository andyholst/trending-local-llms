# Tasks: openspec-active-twin-diagnosis

- [x] `change_for(name)` returns the ACTIVE dir even when an archived twin exists; new `archived_twin(name)` names the archive copy; `check_all` FAILS the twin tree naming BOTH paths and the exact remedy — verified by `tests/test_openspec_spec_tests.py` (34 checks, 0 FAIL)
- [x] The twin guard is RED on the pre-change code: against `git show origin/master:scripts/check_openspec_test_lines.py` the module answers `FAIL twin: both paths are named`, `FAIL twin: the exact remedy is named`, `FAIL twin: change_for returns the ACTIVE dir` + `AttributeError: ... has no attribute 'archived_twin'` (rc=1); on the head rc=0
- [x] Tracked OpenSpec change created before the code (`openspec/changes/openspec-active-twin-diagnosis`: proposal, capability spec with per-scenario `- **Test:**` lines, this checklist) and bound with a bare `Issue: #1477`
- [x] `make lint`, `make architecture-refresh` + `make architecture-check`, `make openspec-index` + `make openspec-check` green on the branch head
- [x] Full `make test` on the branch head green — first run `169 module(s) passed, 1 FAILED: test_check_openspec_tasks.py`, whose ONLY failures were the two real-repo assertions reading this change's own unticked boxes (the documented bootstrap); after ticking, the re-run is green
- [ ] Change archived/recorded on the head before the PR's first validate run; PR open non-draft with `Closes #1477` in title and body; outcome posted on #1477
- [~] AGENTS.md §8 row naming this guard — blocked: rule 3c human sign-off (AGENTS.md protected in a headless leg); the full row text is recorded in `findings.md` as an `owed-row` finding
