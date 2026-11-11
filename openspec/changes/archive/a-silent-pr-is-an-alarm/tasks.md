# Tasks

- [x] 1. The tracked change exists (this directory) before any code edit
- [x] 2. `scripts/pr_health.py`: pure `findings()` + gh reads, two reasons kept apart
- [x] 3. The fix is named (`make worktree-resume`, merge the base, push to the PR's HEAD)
- [x] 4. ONE marker-deduplicated comment per PR; exit 1 when silent, 2 when gh fails
- [x] 5. `make pr-health` (+ `_pr-health`) and `pr-health.yml` (guard first, schedule bypass)
- [x] 6. `BOT_GUARDS` + `DISPATCH_ONLY_COVERAGE` (rules 6j / #231)
- [x] 7. `ARCHITECTURE.md`: target row, job row, section (rule 6h)
- [x] 8. Guard drives the real script against a stub gh (25 checks); RED without it, GREEN after
- [x] 9. `OPENSPEC.md` regenerated; `make lint`, `make test`, `make openspec-check` green
