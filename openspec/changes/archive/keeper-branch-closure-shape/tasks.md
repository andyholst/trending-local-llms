# Tasks

- [x] 1. Proposal + `pr-lifecycle` spec for issue #872 (keeper branch shape; the planted collision scenarios).
- [x] 2. `scripts/pr_closure.py`: the declared keeper shape `KEEPER_BRANCH` (`ci/keeper-<slug>[-<issue>]`) next to the parser; `implemented_issue()` reads a keeper branch as a reference (returns none), docstrings state why (measured #867/#871).
- [x] 3. `tests/test_pr_closure.py`: the three planted scenarios — keeper branch passes with zero closing keywords; keeper branch carrying `Closes #N` is refused as a false claim; the measured #867 branch shape and the `ci/data-gap-<n>-…` implementer shape still demand a binding.
- [x] 4. `.hermes/skills/issue-implement/SKILL.md`: name the convention where the agent cuts the branch — implementation branches keep the binding; a drift-recording keeper lands as `ci/keeper-<slug>[-<issue>]` with `refs #N` and no closing keyword.
- [x] 5. Verified green: `make test`, `make lint`, `make openspec-check`, `make openspec-index`; and the guard proven against the OLD file — the five keeper assertions FAIL on `git show origin/master:scripts/pr_closure.py` (58 passed / 5 failed) and the suite is green on this tree (rule 6c).
- [x] 6. `findings.md` written (`make findings-check` green) and `OPENSPEC.md` regenerated (`make openspec-index`).
- [x] 7. PR body composed with the five sections (issue #771) and ONE `Closes #872`; `make pr-message-check` passes on this branch+body locally before push.
