# Tasks: branch-name-cut-check-807

- [x] `scripts/worktree_base.py`: `--issue` on `new`/`adopt`; the name is validated through
      `pr_closure.implemented_issue` before any worktree/branch/commit exists; `--issue` elsewhere
      is exit 2; `adopt` still attaches existing branches (verified: 151/151 suite green)
- [x] Makefile: `worktree-new` / `branch-adopt` forward `ISSUE=` as `--issue` (verified by the
      Makefile wiring assertions in tests/test_worktree_base.py)
- [x] `issue-bot.yml`: the commit step cuts with `ISSUE="$ISSUE"` (verified by the
      `make branch-adopt BRANCH="$BRANCH" ISSUE="$ISSUE"` wiring assertion)
- [x] AGENTS.md §6n rule + §8 guard row (pinned by `test_the_rulebook_states_the_rule`)
- [x] New tests go RED on the pre-fix script (verified against
      `git show HEAD:scripts/worktree_base.py`: old exits 2 with a generic argparse usage error,
      new exits 1 with the targeted refusal)
- [x] Full worktree suite green on the new code (151 passed, 0 failed)
- [ ] `make test` + `make lint` green (whole suite incl. wiring guards)
- [ ] `make openspec-check` + `make openspec-index-check` + `make architecture-check` green
- [ ] PR opened, CI monitored to green (rule 6e)
