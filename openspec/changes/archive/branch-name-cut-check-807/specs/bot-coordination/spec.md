# bot-coordination

## ADDED Requirements

### Requirement: The implementer's own branch cut declares the issue it implements

The `issue-bot.yml` commit step MUST cut the branch with `make branch-adopt BRANCH="$BRANCH"
ISSUE="$ISSUE"`, so the bot's branch name and the issue it implements are validated against each
other at the cut — the cheapest point in the pipeline — instead of failing at the PR webhook after
a full implementation and CI cycle (measured: PRs #805/#803, runs 43104841635 / 43104841639).

#### Scenario: the bot's declared cut is wired through the Makefile seam

- **Given** the shipped `issue-bot.yml` and `Makefile`
- **When** the wiring is asserted (the commit step passes `ISSUE="$ISSUE"`; both cut targets
  forward `ISSUE=` as `--issue`)
- **Then** no path exists from the bot to a pushed branch that skipped the name check
- **Test:** tests/test_worktree_base.py::test_the_makefile_is_the_one_seam
