# refresh-publish

## ADDED Requirements

### Requirement: A refresh's generated tree is moved onto the fetched base before it is published

`make refresh-sync` MUST fetch the base and, when the tree is behind it, reset ONLY the
generated files (`README.md`, `data/models.json`, `data/snapshots/`, `data/raw/`,
`data/gap_baseline.json`) onto the fetched tip, keep the run's raw snapshots and the gap
baseline, and report the oldest kept snapshot's capture stamp so the caller can re-ingest
exactly this run's data. It MUST refuse a HEAD carrying commits of its own and any dirty
path outside the generated set.

#### Scenario: the base moved while the search legs ran

- **Given** a checkout behind the fetched base carrying a regenerated README, store, baseline and one new raw snapshot
- **When** `make refresh-sync` runs
- **Then** it exits 0, prints `sync=reset` and the fetched `base_sha`, HEAD is that tip, the generated README is the base's again, and the raw snapshot and gap baseline are still in the tree
- **Test:** tests/test_refresh_base.py::test_sync_moves_the_generated_tree_onto_the_fetched_base

#### Scenario: the tree is already on the tip

- **Given** a checkout at the fetched base
- **When** `make refresh-sync` runs
- **Then** it is a green no-op printing `sync=current` and nothing is reset
- **Test:** tests/test_refresh_base.py::test_sync_is_a_no_op_on_the_fetched_tip

#### Scenario: a dirty path a refresh does not generate

- **Given** a checkout with an edit under `scripts/` and a base that has moved
- **When** `make refresh-sync` runs
- **Then** it is REFUSED, the message names the path, and the edit is still in the tree
- **Test:** tests/test_refresh_base.py::test_sync_refuses_a_dirty_path_a_refresh_does_not_generate

#### Scenario: a HEAD with commits of its own

- **Given** a checkout on a branch whose commit the fetched base does not have
- **When** `make refresh-sync` runs
- **Then** it is REFUSED and points at `make base-rebase`, so no commit is reset away
- **Test:** tests/test_refresh_base.py::test_sync_refuses_a_head_with_its_own_commits

### Requirement: The oldest raw snapshot's stamp is reported for the re-derivation

`sync` MUST print `raw_floor=<ISO8601Z>` for the oldest raw snapshot it kept, so the caller
re-runs `make merge SINCE=<stamp>` and the base's own `generated_utc` cannot skip this run's
data; `make merge` MUST forward `SINCE` only when it is set, and `_merge` MUST NOT see an
empty `--since`.

#### Scenario: the base is newer than this run's snapshots

- **Given** a synced tree whose kept snapshot is stamped `2026-10-21T12:00:00Z`
- **When** `make refresh-sync` runs
- **Then** it prints `raw_floor=2026-10-21T12:00:00Z`, and `make merge` forwards it as `--since`
- **Test:** tests/test_refresh_base.py::test_sync_moves_the_generated_tree_onto_the_fetched_base

### Requirement: A refresh never publishes a branch the fetched base has left

Before the push and before the PR, the pipeline MUST prove the branch already contains the
fetched base; when it does not, the run MUST fail loudly, naming the repair, and no PR may
be opened.

#### Scenario: a branch behind the base

- **Given** a committed refresh branch and a base that has merged since
- **When** `make refresh-require-tip` runs
- **Then** it exits 1, prints `behind_base=1`, and says `STALE` with `make refresh-sync && make merge` as the repair
- **Test:** tests/test_refresh_base.py::test_require_tip_fails_on_a_branch_behind_the_fetched_base

#### Scenario: after a sync

- **Given** a tree synced onto the fetched base and the refresh committed on it
- **When** `make refresh-require-tip` runs
- **Then** it exits 0 and prints `behind_base=0` and `published_on_base=true`
- **Test:** tests/test_refresh_base.py::test_require_tip_passes_after_the_tree_is_synced

#### Scenario: the base cannot be fetched

- **Given** a remote that does not exist
- **When** `make refresh-require-tip` runs
- **Then** it exits 1 with `REFUSED`, because a base that cannot be fetched must never pass as fresh
- **Test:** tests/test_refresh_base.py::test_require_tip_is_loud_when_the_base_cannot_be_fetched

### Requirement: The pipeline runs the sync and the guard in order

`refresh-bot`'s commit step MUST run `make refresh-sync` before the branch is cut, re-run
`make merge SINCE=` on that base, and run `make refresh-require-tip` after the commit and
before both the push and `gh pr create`; a re-derivation that changed nothing MUST open no PR.

#### Scenario: the step's order

- **Given** the workflow file
- **When** the wiring is read
- **Then** sync < branch cut < merge SINCE, and require-tip < push < PR creation
- **Test:** tests/test_refresh_base.py::test_the_seam_is_wired_to_the_makefile_and_the_pipeline
