# Spec delta: keeper-PR landing sequence (the weekly architecture keeper lands through the seam)

## ADDED Requirements

### Requirement: The seam lands the keeper's whole set of owned generated files

`scripts/keeper_pr.py` SHALL accept a space-separated set of files it owns. It
commits every owned file that changed in ONE commit, exits 0 when none of them
changed, and refuses (exit 1) when any tracked change falls outside the set. A
keeper given a single file behaves exactly as before.

#### Scenario: a multi-file keeper lands one commit touching both files

- **Test:** tests/test_keeper_pr.py::test_multi_file_keeper_lands_one_commit_touching_both_files
- **Given** a tree where BOTH files named by `--file "GENERATED.md EXTRA.md"` changed
- **When** `make keeper-pr` runs
- **Then** one agent-identity commit carrying exactly both files lands on a
  timestamped branch, and the PR body still comes from the keeper's own target.

#### Scenario: a partial set still lands what changed

- **Test:** tests/test_keeper_pr.py::test_multi_file_keeper_lands_only_the_owned_file_that_changed
- **Given** a tree where only ONE of the keeper's two files changed
- **When** `make keeper-pr` runs
- **Then** the commit carries that one file and exits 0.

#### Scenario: a wider drift is still refused

- **Test:** tests/test_keeper_pr.py::test_extra_changes_refuse_exit_1_and_land_nothing
- **Given** a tree where a file OUTSIDE the keeper's set changed
- **When** `make keeper-pr` runs
- **Then** it exits 1 naming every changed file and pushes no branch.

### Requirement: the weekly architecture keeper lands through the seam

The `architecture-bot.yml` refresh job SHALL land its regenerated documents
through ONE `make keeper-pr` invocation — no spelled `git switch -c` / `git push
origin "HEAD:refs/heads/…"` / `gh pr create` shell — on branch prefix
`ci/architecture-refresh` with `DEDUPE=1` and body target
`architecture-pr-body`.

#### Scenario: the shipped land step really commits, pushes and opens the PR through the seam

- **Test:** tests/test_architecture_bot.py::test_the_shipped_steps_actually_commit_push_and_open_a_pr
- **Given** the shipped `run:` text extracted from `architecture-bot.yml`, a real
  repo, a real bare remote and a stub `gh` standing in only for the network
- **When** the land step executes after a regeneration drift
- **Then** it pushes one `ci/architecture-refresh-<UTC>Z` branch whose single
  Asimov-authored commit carries the drifted documents, with a body from
  `architecture-pr-body` and NO closing keyword.

#### Scenario: no keeper job re-spells the landing shell

- **Test:** tests/test_keeper_pr.py::test_no_keeper_job_spells_the_landing_sequence_anymore
- **Given** every keeper job of the seam's scope (index-repair, architecture-repair,
  the queued-alarm ledger step, and now the weekly architecture keeper)
- **When** the Done-when scan reads their `run:` blocks
- **Then** each calls `make keeper-pr` and none spells `git switch -c`,
  `git push origin "HEAD:refs/heads/…"`, `status --porcelain` or `git config`.
