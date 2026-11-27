# Tasks: findings-prepush-guard-1804

- [x] `scripts/file_findings.py` gains `--prepush` reusing `analysis_path` → `slice_analysis_path` → `parse` (no shape exemption, exit 2 when no issue is bound)
- [x] `findings-check-for-pr` accepts `PREPUSH=1 ISSUE=<n>`; plain CI invocation stays host-side and unchanged
- [x] `agents/skills/issue-implement/SKILL.md` directs host lanes to run the guard before any push
- [x] `tests/test_file_findings.py` extended with missing / no-issue / none / one-slice / two-slice / wiring guards — ran `python3 tests/test_file_findings.py`: PASSED 119 | FAILED 0
- [x] Guards proven RED on the pre-change seam: base `file_findings.py --prepush` errors `unrecognized arguments: --prepush` (rc 2); branch refuses a missing file (rc 1)
- [x] `python3 scripts/check_agent_skills.py check` green after the skill edit
- [x] `python3 scripts/openspec_index.py --write` run and `--check` green; `findings/1804.md` written
- [~] Full `make test`, `make validate` and `make architecture-check` — blocked: CI-only on qa-validate (the host has no Docker; rule 7b pushes fast offline checks and lets CI verify)
- [~] §8 guard-row extension naming `tests/test_file_findings.py`'s pre-push guards — blocked: rule 3c human sign-off (AGENTS.md protected in a headless leg)
