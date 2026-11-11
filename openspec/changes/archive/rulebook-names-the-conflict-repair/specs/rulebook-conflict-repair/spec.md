# rulebook-conflict-repair

## ADDED Requirements

### Requirement: §6b names the conflict-repair path a bot PR takes

`AGENTS.md` §6b MUST state, after the `fix-bot.yml` bullet, that a bot PR which cannot merge
because its base moved is a REPAIR: the silent-PR sweep dispatches `fix-bot` for a `ci/…` branch
capped at 2 `fix-bot:` commits, `scripts/fix_loop.sh` merges the fetched base before its first
round, a CONFLICTED merge is kept with its hunks handed to the round (generated artifacts
REGENERATED, never hand-merged), the merge is completed when the index comes back clean, and it is
`--abort`ed if the last round cannot resolve it so nothing half-merged is pushed — while a human's
branch is reported, never dispatched to.

#### Scenario: the reader is told what happens to a conflicting bot PR

- **Given** `AGENTS.md` describes the four pipelines in §6b
- **When** a reader looks for what happens to a `ci/…` PR whose base moved
- **Then** §6b names the sweep's dispatch, the cap, the base merge before the first round, the
  kept conflict with its hunks, the completion on a clean index, the final `--abort`, the
  regenerated-never-hand-merged rule, and the human's branch left alone
- **Test:** tests/test_agents_rows.py::test_the_conflict_repair_path_is_named_in_6b

### Requirement: §8 carries a row for the conflict-repair path

`AGENTS.md` §8 MUST carry a row naming the guards of the conflict-repair path (the real modules
`tests/test_fix_loop.py` and `tests/test_pr_health.py`) and the failures they catch — a conflicted
base merge aborting instead of being repaired, a round leaving conflict markers behind, a branch
pushed half-merged, an unresolved conflict reported as green, and a repair dispatched onto a
human's branch — and `tests/test_agents_rows.py` MUST pin that row so it cannot become prose again.

#### Scenario: the owed row is written and pinned

- **Given** the conflict-repair code merged (#478) with its §8 row owed (#476)
- **When** `make test` runs the owed-rows suite
- **Then** the `#476` row exists in §8 with its phrase, and the §6b paragraph is present
- **Test:** tests/test_agents_rows.py::test_the_rows_this_session_owed_are_written
