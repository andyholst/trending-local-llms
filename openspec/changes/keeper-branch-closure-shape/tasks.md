# Tasks

- [x] 1. Proposal + `pr-lifecycle` spec for issue #872 (keeper branch shape; the planted collision scenarios).
- [ ] 2. `scripts/pr_closure.py`: the declared keeper shape `KEEPER_BRANCH` (`ci/keeper-<slug>[-<issue>]`) next to the parser; `implemented_issue()` reads a keeper branch as a reference (returns none), docstrings state why (measured #867/#871).
- [ ] 3. `tests/test_pr_closure.py`: the three planted scenarios — keeper branch passes with zero closing keywords; keeper branch carrying `Closes #N` is refused as a false claim; the measured #867 branch shape and the `ci/data-gap-<n>-…` implementer shape still demand a binding.
- [ ] 4. `.hermes/skills/issue-implement/SKILL.md`: name the convention where the agent cuts the branch — implementation branches keep the binding; a drift-recording keeper lands as `ci/keeper-<slug>[-<issue>]` with `refs #N` and no closing keyword.
- [ ] 5. Verified green: `make test`, `make lint`, `make openspec-check`, `make openspec-index`; and the guard proven against the OLD file — the new keeper tests FAIL on `git show origin/master:scripts/pr_closure.py` (rule 6c).
- [ ] 6. PR opened ready-for-review (never draft), body composed with the five sections and ONE `Closes #872`; `make pr-message-check` passes on the body before push; CI monitored to green.
