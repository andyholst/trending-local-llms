# Tasks

- [x] 1. The measured race is recorded on #520 (picked 14:37, closed 14:38, RED 14:41)
- [x] 2. The tracked change exists (this directory) before any code edit
- [x] 3. `issue_verdict.py --state`: 0 open / 4 closed / 2 unreadable, one `gh issue view` read
- [x] 4. `make issue-state ISSUE=<n> [REPO=]`
- [x] 5. `issue-bot.yml`: the failure step asks the state FIRST, green on 4, red otherwise
- [x] 6. ONE marker-deduplicated comment on a mid-run-closed issue, with the default token
- [x] 7. Tests: the three exit codes; the step's order, its green branch, its untouched red paths
- [x] 8. `ARCHITECTURE.md` row + the §10 inventory regenerated
- [x] 9. `make test`, `make lint`, `make architecture-check`, `make openspec-check`, `make secret-scan` green; `OPENSPEC.md` regenerated
- [x] 10. `findings.md` written; the protected-file rows noted on #494
