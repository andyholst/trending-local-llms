# fix-loop-self-archive-verdict Specification

## Purpose
TBD - created by archiving change fix-loop-self-archive-exit-mapping. Update Purpose after archive.

## Requirements

### Requirement: The self-archive guard publishes a verdict that survives the make exit rewrite

`scripts/self_archive_guard.py` SHALL print exactly one line of the form
`[self-archive] verdict=<v>` on stdout, where `<v>` is `ok`, `restored`,
`dismantled` or `unreadable`, in addition to its existing prose. A baseline that
cannot be read SHALL print `verdict=unreadable` on stdout before exiting non-zero.

#### Scenario: A dismantled change is restored

- **Given** a real throwaway git repository whose snapshot marks a change active and whose tree has that change moved into `openspec/changes/archive/`
- **When** the real guard runs with `SELF_ARCHIVE_RESTORE=1`
- **Then** it exits non-zero, prints `[self-archive] verdict=restored` and restores the change directory
- **Test:** tests/test_self_archive_guard.py::test_a_restored_dismantle_emits_the_verdict_marker

#### Scenario: An unreadable baseline prints no restored marker

- **Given** a snapshot path that does not exist
- **When** the real guard runs with `SELF_ARCHIVE_RESTORE=1`
- **Then** it exits 2, prints `[self-archive] verdict=unreadable` and prints no `verdict=restored` line
- **Test:** tests/test_self_archive_guard.py::test_an_unreadable_baseline_has_no_restored_marker

#### Scenario: A clean tree prints the ok verdict

- **Given** a real repository whose baseline-active changes are all still on disk
- **When** the real guard runs a plain check
- **Then** it exits 0 and prints exactly one `[self-archive] verdict=ok` line
- **Test:** tests/test_self_archive_guard.py::test_a_clean_tree_prints_the_ok_verdict

### Requirement: The fix loop classifies from the verdict, not from the make exit code

`scripts/fix_loop.sh` SHALL branch on the guard's own verdict marker, so a make exit of
`2` produced by a restored dismantle is reported as a restoration and only a genuinely
unreadable or broken guard is reported as `could not run`.

#### Scenario: The stale equality branch is gone

- **Given** `scripts/fix_loop.sh` on the branch
- **When** the module reads the guard-classification block
- **Then** it matches on `[self-archive] verdict=restored` and no longer carries the unreachable `[ "$sa_rc" = "1" ]` branch
- **Test:** tests/test_self_archive_guard.py::test_fix_loop_branches_on_the_verdict_marker
