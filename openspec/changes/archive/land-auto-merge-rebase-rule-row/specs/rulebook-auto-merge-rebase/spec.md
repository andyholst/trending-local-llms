# rulebook-auto-merge-rebase — spec delta

## ADDED Requirements

### Requirement: The rulebook names auto-merge's pre-squash rebase gate and its guard

`AGENTS.md` rule 6e SHALL name `make auto-merge-rebase` as the gate qa-validate's `auto-merge`
job runs BEFORE its squash (behind+clean+bot-owned → rebase onto the fetched base, regenerate
`OPENSPEC.md` on the rebased tree, `rebased=true` defers the merge to the validated head;
human-owned/conflicting branches stay report-only), §6s SHALL name the sweep rebaser's index
regeneration, and §8 SHALL carry a guard row for `tests/test_auto_merge_rebase.py`. The rows are
the ledger's, landed verbatim; a pin test locks them in the rulebook.

#### Scenario: rule 6e names the pre-squash gate and its contract

- **Given** a reader of rule 6e asking whether auto-merge may squash a behind branch
- **When** the rulebook text is read
- **Then** it names `make auto-merge-rebase` / `scripts/auto_merge_rebase.py` as auto-merge's
  pre-squash gate, `rebased=true` skipping the squash, and the report-only human partition
- **Test:** tests/test_agents_rows.py::test_the_auto_merge_rebase_row_is_written

#### Scenario: §6s names the rebaser's OPENSPEC.md regeneration and §8 carries the guard row

- **Given** a reader asking what keeps a rebased tree's index fresh and what guards a regression
  in the gate
- **When** the §6s bullet and the §8 table row are read
- **Then** §6s states the rebaser regenerates `OPENSPEC.md` on the rebased tree, and the §8 row
  names the qa-validate step, the seam script, the outranking/no-fabrication halves and both
  modules exist in the tree
- **Test:** tests/test_agents_rows.py::test_the_auto_merge_rebase_row_is_written

#### Scenario: the owed-row ledger reports the rows landed

- **Given** the two `owed-row` markers #1088 declares (`section=2 needle=auto-merge-rebase`,
  `section=8 needle=tests/test_auto_merge_rebase.py`)
- **When** `make owed-rows-check` walks the open queue against this tree's `AGENTS.md`
- **Then** both rows report `LANDED` with their `AGENTS.md:<line>` proof and `problems=0`
- **Test:** tests/test_owed_rows.py::test_a_landed_owed_row_is_reported_with_evidence
