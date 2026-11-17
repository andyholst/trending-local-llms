# Tasks

- [x] 1. The tracked change exists (this directory) before any code edit
- [x] 2. `scripts/pr_health.py`: `approval_hold()` + third reason in `findings()` (pure, optional
      `holds_for`); `main()` reads `conclusion` per run and counts held runs
- [x] 3. The hold comment names the human approval remedy (rule 6t) and no rebase hint
- [x] 4. `tests/test_pr_health.py`: three new tests + gh-stub answers conclusions; green on the
      host (`python3 tests/test_pr_health.py`)
- [x] 5. `AGENTS.md` §8 guard row for the new tests (rule 6c — review-required row, stated in
      this change and flagged for reviewer sign-off in the PR body)
- [x] 6. `ARCHITECTURE.md` §4 target row + §6 script row updated + `make architecture-refresh`
      regenerated the inventory block (stale by #947 because the script docstring changed)
- [x] 7. Gates green on the exact head: full host suite 132/132, `make lint`,
      `make openspec-index` + `openspec-index-check`
- [x] 8. PR opened with the five-section body closing #1123; the change archived at the PR head
      (`make openspec-record-pr`, #779/#866); the run monitors the pipeline to green
