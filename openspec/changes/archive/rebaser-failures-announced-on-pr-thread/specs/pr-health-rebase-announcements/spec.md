## ADDED Requirements

### Requirement: A failed rebaser round announces itself on the PR thread

When `make pr-health` runs with `--rebase --comment`, every PR whose planned
`rebase-if-behind` attempt did NOT land (`kept: …`, `refs unreadable`, push or
worktree failure) SHALL receive exactly ONE comment on its own thread carrying
the registered marker `pr-health-rebase-failed` stamped with the branch and the
head oid the attempt failed on, the failure reason, and the concrete remedy
(`make worktree-resume BRANCH=<head>`, `make base-rebase BRANCH=<head>`, and
the rule-6s partition that conflict resolution belongs to the PR's own fix loop
or a human). The announcement SHALL be deduplicated: a thread already carrying
a marker for the same (branch, head) SHALL not be commented again, and a
branch whose head oid moved MAY be announced again next round. A failed attempt
SHALL still leave the branch byte-identical (the rebaser never force-pushes a
conflicted result), and the rebaser half SHALL remain orthogonal to the
silent-PR verdict.

#### Scenario: A git-rejected rebase posts the marker comment

- **Given** an open bot-owned PR whose branch is behind `origin/master` and
  whose rebase git rejects with a conflict (GitHub has not yet labelled the PR
  CONFLICTING), with no prior marker on its thread
- **When** `make pr-health` runs with `--rebase --comment`
- **Then** the PR receives one comment carrying
  `<!-- pr-health-rebase-failed: <stamp> run=<branch>_<oid> -->`, names the
  failure, names `make worktree-resume` and `make base-rebase` as the remedy,
  and the remote branch is byte-identical to before
- **Test:** tests/test_pr_health.py::test_a_failed_rebase_round_announces_on_the_pr_thread_once

#### Scenario: The same failed round is never double-announced

- **Given** the same failing (branch, head) whose thread ALREADY carries this
  round's `pr-health-rebase-failed` marker
- **When** the next sweep round runs `make pr-health --rebase --comment`
- **Then** nothing is posted for that PR and the run says it was already
  announced
- **Test:** tests/test_pr_health.py::test_a_failed_rebase_round_announces_on_the_pr_thread_once

#### Scenario: A landed rebase posts nothing

- **Given** a behind-and-clean bot branch whose rebase succeeds
- **When** the sweep runs with `--rebase --comment`
- **Then** the branch is pushed rebased and NO rebase-failed comment is posted
- **Test:** tests/test_pr_health.py::test_a_failed_rebase_round_announces_on_the_pr_thread_once

### Requirement: The pr-health markers are registered in bot_markers, not spelled privately

The marker names `pr-health-alarm` and `pr-health-rebase-failed` SHALL be
declared in `scripts/bot_markers.py` (REGISTRY under the `pr-health` family,
listed in WRITTEN and ARTIFACTS) and `scripts/pr_health.py` SHALL derive them
through `bot_markers.marker_name` instead of carrying private literals. The
AGENTS.md §6j table SHALL name both markers in the same change.

#### Scenario: Registry, writer and table agree

- **Given** the `pr-health` family registered in `scripts/bot_markers.py` with
  both markers, each written by `scripts/pr_health.py`
- **When** `tests/test_bot_markers.py` runs
- **Then** every written marker is registered, every registered marker has a
  writer, and the AGENTS.md §6j section names both marker literals
- **Test:** tests/test_bot_markers.py::test_every_marker_the_tree_writes_is_registered
