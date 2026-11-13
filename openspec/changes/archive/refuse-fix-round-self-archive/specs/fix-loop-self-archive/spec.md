# fix-loop-self-archive

## ADDED Requirements

### Requirement: The fix loop baselines its OpenSpec changes after the base merge

The fix loop MUST record which OpenSpec changes are active AFTER its base merge —
a merge may legitimately archive the base's merged changes, and those belong to
the baseline, never to a dismantle — and MUST take the snapshot only inside a git
checkout. A change archived before the snapshot is not a dismantle; a change made
after the snapshot is this run's own artifact and is not guarded. The guard MUST
NOT pass vacuously: a baseline it cannot read is a loud exit 2.

#### Scenario: a clean tree is green and a base-archived change is not reported

- **Given** a planted tree with one active change and one already-archived change, snapshotted by the REAL `scripts/self_archive_guard.py`
- **When** `check` runs against the untouched tree
- **Then** it exits 0, and the base-archived change is recorded in the baseline's `archive` set and never reported
- **Test:** tests/test_self_archive_guard.py::test_snapshot_then_check_on_a_clean_tree_is_green
- **Test:** tests/test_self_archive_guard.py::test_an_archive_already_at_the_baseline_is_not_a_dismantle

#### Scenario: a guard with no baseline refuses loudly instead of passing

- **Given** `SELF_ARCHIVE_BASELINE` pointing at a file that does not exist
- **When** `check` runs
- **Then** it exits 2 naming the missing baseline (never exit 0)
- **Test:** tests/test_self_archive_guard.py::test_a_missing_baseline_is_a_loud_error

#### Scenario: a change the run creates itself is not guarded

- **Given** a snapshot taken while the tree holds `foo`, then a new change `bar` created after it
- **When** `check` runs
- **Then** `bar` is not treated as a dismantled baseline change
- **Test:** tests/test_self_archive_guard.py::test_a_change_made_after_the_snapshot_is_this_runs_own_artifact

### Requirement: A round that dismantles a baseline-active change is reported before any green exit

After EVERY Hermes round — before the loop's green re-check can `exit 0` on the
dismantled state — the loop MUST compare the tree against the baseline: a
baseline-ACTIVE change gone from `openspec/changes/` is reported (exit 1, naming
the change) and its report folded into the next round's repair notes; a guard
that could not run (exit 2) is itself recorded there. Outside a git checkout the
loop never dies on the guard (issue #383's rule).

#### Scenario: the measured dismantle — a round archives its own change mid-loop

- **Given** the REAL fix loop in a REAL git repository whose stub round moves the branch's own change `foo` from `openspec/changes/` into `openspec/changes/archive/`, with the REAL guard script wired through the recorder
- **When** the loop runs the round and re-checks
- **Then** the snapshot and the guard both ran, the loop names the dismantling round, the change is back in `openspec/changes/`, the fresh archive copy is gone, and the loop goes on and still lands green
- **Test:** tests/test_fix_loop.py::test_a_round_that_archives_its_own_change_is_refused_and_restored

### Requirement: Restoration is a real restore, and a loss that cannot be restored is loud

With `SELF_ARCHIVE_RESTORE=1` the guard MUST bring the change back on disk before
reporting: a copy sitting under `openspec/changes/archive/` is moved back and the
index re-staged so the committed tree can never carry the phantom deletion; a
change whose working-tree copy is gone comes back from `SELF_ARCHIVE_REF`; a loss
neither can recover is reported `unrecoverable`, never silently accepted. The
restore run stays red (exit 1) — the round that dismantled must still be reported.

#### Scenario: a committed mid-run move is restored and re-staged

- **Given** a baseline-active change whose move into the archive is already COMMITTED
- **When** the guard runs with `SELF_ARCHIVE_RESTORE=1`
- **Then** the change is back on disk and staged, and the archive copy is out of the index
- **Test:** tests/test_self_archive_guard.py::test_a_committed_mid_run_move_is_restored_and_the_index_restaged

#### Scenario: a vanished change is restored from the reference

- **Given** a baseline-active change with no working-tree copy and no archive copy, and a valid `SELF_ARCHIVE_REF`
- **When** the guard runs with `SELF_ARCHIVE_RESTORE=1`
- **Then** the files come back from the reference commit
- **Test:** tests/test_self_archive_guard.py::test_a_vanished_change_is_restored_from_the_reference

#### Scenario: an unrecoverable loss says so

- **Given** a dismantled change with no archive copy and no restorable reference
- **When** the guard runs with `SELF_ARCHIVE_RESTORE=1`
- **Then** it exits 1 reporting the change `unrecoverable` rather than passing
- **Test:** tests/test_self_archive_guard.py::test_an_unrecoverable_loss_is_reported_loudly_not_silently

#### Scenario: a plain move is reported and restored

- **Given** a baseline-active change moved into the archive without a commit
- **When** the guard runs first without restore, then with `SELF_ARCHIVE_RESTORE=1`
- **Then** the first run exits 1 naming the change and leaves the tree, the second restores it (change back, archive copy gone) and the tree then checks clean
- **Test:** tests/test_self_archive_guard.py::test_a_move_into_the_archive_is_reported_and_restored
