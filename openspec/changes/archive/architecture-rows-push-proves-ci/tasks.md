# Tasks: architecture-rows-push-proves-ci

- [x] Restore the four #1616 clauses in `ARCHITECTURE.md` verbatim from head `5eea2616` and prove the file differs from its base only in those rows
- [x] Regenerate §10 with `make architecture-refresh` (`scripts/architecture_bot.py --write`), never by hand
- [x] Prove `scripts/architecture_check.py` and `scripts/architecture_bot.py --check` green on the repaired head
- [x] Add the RED-first row guard `tests/test_architecture_rows_1616.py` and prove rc=1 on pristine `origin/master`'s `ARCHITECTURE.md`, rc=0 on the repaired head
- [x] Save the doc deltas as a patch beside the branch before any rebase, so a `--continue` cannot silently drop them again
- [x] Re-check the surviving `AGENTS.md` §8 pin names the #1616 contract
- [x] Open a READY PR carrying `Closes #1648` in title and body, run `make openspec-record-pr ISSUE=1648 PR=<n>` on the branch, and confirm CI registers real jobs on the pushed head
