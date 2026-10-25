# Tasks

- [x] 1. Write the proposal + `issue-bot-artifacts` capability spec for issue #539.
- [x] 2. `Makefile`: `issue-thread`'s recipe starts with `@`, so `issue.md` holds only the thread.
- [x] 3. `tests/test_workflows.py`: the derived guard — every non-`*.log` `make … > file` a workflow performs must be a silenced recipe, non-vacuous, with `issue-thread` covered.
- [x] 4. Verified RED against `origin/master`'s Makefile (`issue-thread` named) and GREEN after.
- [x] 5. `AGENTS.md` §8 guard row (rule 6c, review-required rule 3c).
- [x] 6. `findings.md` written; `OPENSPEC.md` regenerated; `make lint`, `make test`, `make openspec-check`, `make architecture-check` green.
