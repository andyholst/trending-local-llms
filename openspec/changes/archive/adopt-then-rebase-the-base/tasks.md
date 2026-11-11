# Tasks

- [x] 1. The measured failure is recorded on #500 (run 39548077538, the STALE refusal after the work)
- [x] 2. The tracked change exists (this directory) before any code edit
- [x] 3. `worktree_base.py adopt` — cut or attach the branch, no base assertion, `behind_base=N`
- [x] 4. `worktree_base.py rebase` — fetch + rebase; conflict aborts and exits 3; dirty refused
- [x] 5. `make branch-adopt` / `make base-rebase`
- [x] 6. `issue-bot.yml`: adopt → commit → rebase → push, exit 3 tolerated, no base-asserting target
- [x] 7. The patch artifact uploads on ANY rejected push
- [x] 8. Tests: adopt (behind / existing), rebase (up-to-date / behind / conflict / dirty), the step guards
- [x] 9. Each new guard proven RED against `origin/master`
- [x] 10. `ARCHITECTURE.md` rows + §10 inventory regenerated
- [x] 11. `make test`, `make lint`, `make architecture-check`, `make openspec-check`, `make secret-scan` green; `OPENSPEC.md` regenerated
- [x] 12. `findings.md` written; the protected-file rows noted on #494
