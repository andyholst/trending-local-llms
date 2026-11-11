# Tasks

- [x] 1. Write the proposal + spec for the queued-run alarm (issue #252, mirrors llgenie #254).
- [x] 2. `scripts/queued_run_alarm.py`: read the `queued`/`in_progress` runs, flag the jobs queued past `--minutes`, render them, and `--comment` once per affected run (marker dedup).
- [x] 3. `.github/workflows/queued-alarm.yml`: its own `concurrency`, the owner/collaborator/bot guard FIRST with the `schedule` bypass, `make queued-alarm` as the one command.
- [x] 4. `make queued-alarm` target (`REPO=`, `MINUTES=`, `COMMENT=`) + `.PHONY`.
- [x] 5. `tests/test_queued_run_alarm.py` wired into `make _test`: the decision, the dedup, the wiring (fake `gh` on PATH).
- [x] 6. README + `ARCHITECTURE.md`; run `make lint`, `make test`, `make architecture-check`, `make openspec-check`.
- [x] 7. Commit, push, open the PR (closes #252).
- [x] 8. AGENTS.md: rule 6l (a stuck `queued` job is an ALARM) + the section-8 guard row for `tests/test_queued_run_alarm.py` (MANDATORY - the repo's rulebook must carry the alarm).
- [x] 9. The one comment uses the DEFAULT `github.token`, never the owner PAT: AGENTS.md rule 6e is explicit that the PAT cannot comment. Pinned by a test and falsified.
