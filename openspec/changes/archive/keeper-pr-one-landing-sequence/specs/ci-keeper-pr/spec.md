# Spec delta: keeper-PR landing sequence

## ADDED Requirements

### Requirement: ONE keeper-landing sequence reached through `make keeper-pr`

The keeper-PR landing sequence — land a generated-file repair as a reviewed PR
with no closing keyword — SHALL have exactly one implementation,
`scripts/keeper_pr.py`, reached only through `make keeper-pr`, and every keeper
job SHALL call that target instead of spelling the sequence in its `run:` block.

#### Scenario: nothing changed lands nothing

- **Test:** tests/test_keeper_pr.py::test_no_change_exits_zero_without_a_branch_or_pr
- **Given** a keeper job whose repair left its file byte-identical (DRIFT=none)
- **When** `make keeper-pr` runs
- **Then** it prints the nothing-to-land message and exits 0 without a branch, commit, push or PR.

#### Scenario: a repair that touched more than its file is refused

- **Test:** tests/test_keeper_pr.py::test_extra_changes_refuse_exit_1_and_land_nothing
- **Given** a tree where the keeper's file AND another tracked file changed
- **When** `make keeper-pr` runs
- **Then** it exits 1 naming every changed file and pushes no branch.

#### Scenario: a mergeable keeper suppresses a duplicate; an unmergeable one does not

- **Test:** tests/test_keeper_pr.py::test_mergeable_keeper_suppresses_and_dirty_keeper_does_not
- **Given** `DEDUPE=1` and the repo carries an open keeper on the branch prefix
- **When** the keeper is MERGEABLE, the run exits 0 naming the suppression; when
  every open keeper is DIRTY/CONFLICTING, the run names them UNMERGEABLE (#960)
  and files a fresh keeper against the current tip.

#### Scenario: the landed keeper is one agent-identity commit on a timestamped branch

- **Test:** tests/test_keeper_pr.py::test_keeper_lands_one_commit_touching_only_its_file
- **Given** exactly the keeper's file changed
- **When** `make keeper-pr` runs
- **Then** a branch `<BRANCH_PREFIX>-<UTC>` carries ONE commit authored by the
  repo agent identity touching only that file, pushed to origin, and the PR is
  opened with the title given and the body produced by `make <BODY_TARGET> BODY_ARGS` —
  no closing keyword composed by the sequence itself.

#### Scenario: a keeper job that re-implements the sequence is red

- **Test:** tests/test_keeper_pr.py::test_no_keeper_job_spells_the_landing_sequence_anymore
- **Given** every workflow under `.github/workflows/`
- **When** the guard scans keeper land steps
- **Then** each keeper job (its step names match keeper landing) contains
  `make keeper-pr` and no hand-written `git switch -c` / `git push origin "HEAD:refs/heads/`
  landing shell, and no step re-spells the `startswith("ci/` dedupe or the
  `git status --porcelain` guard.
