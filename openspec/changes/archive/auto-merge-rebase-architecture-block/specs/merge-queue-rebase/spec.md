## ADDED Requirements

### Requirement: The bot rebase refreshes every generated artifact on the rebased tree

`pr_health.rebase_and_push` SHALL regenerate `OPENSPEC.md` AND `ARCHITECTURE.md` on the rebased tree,
each through that tree's own generator, and SHALL NOT push until both regenerations succeed. A failed
architecture regeneration SHALL leave the remote branch byte-identical, exactly as a failed index
regeneration does.

#### Scenario: A clean rebase of a behind-and-clean bot branch

- **Given** a bot branch behind master that added a script and refreshed its own `ARCHITECTURE.md` block
- **When** `make auto-merge-rebase` classifies it `behind-and-clean-bot` and rebases it
- **Then** the pushed head carries an `ARCHITECTURE.md` block that `scripts/architecture_bot.py --check`
  accepts, and `OPENSPEC.md` is still regenerated
- **Test:** tests/test_auto_merge_rebase.py::test_rebase_regenerates_the_architecture_block_too

### Requirement: A conflict confined to the two generated files is resolved by regeneration

A rebase that leaves ONLY `OPENSPEC.md` and/or `ARCHITECTURE.md` unmerged SHALL take the branch's side
of those paths, continue the rebase, and regenerate both from the merged tree. A rebase with any other
unmerged path SHALL abort and leave the remote branch byte-identical.

#### Scenario: Both generated files conflict on the rebase

- **Given** a bot branch whose commit edited the generated pair and a master that moved both
- **When** the rebaser replays the commit onto master
- **Then** the seam reports `verdict=rebased`, and the pushed head is green at both
  `scripts/openspec_index.py --check` and `scripts/architecture_bot.py --check`
- **Test:** tests/test_auto_merge_rebase.py::test_a_conflict_in_the_two_generated_files_is_resolved_by_regeneration

#### Scenario: A conflict outside the generated files still aborts

- **Given** a rebase that leaves a hand-written file unmerged
- **When** the rebaser inspects the unmerged paths
- **Then** it aborts, reports `kept`, and the remote branch does not move
- **Test:** tests/test_auto_merge_rebase.py::test_conflicting_branches_are_never_rewritten
