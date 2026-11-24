## ADDED Requirements

### Requirement: The push-proves-CI contract stays documented in ARCHITECTURE.md

The four hand-written `ARCHITECTURE.md` rows that name issue #1616's contract SHALL keep their
clause: the `auto-merge-rebase` target row, the qa-validate `auto-merge` job row, and the
`scripts/pr_health.py` / `scripts/auto_merge_rebase.py` script rows. A rebase or a hand edit
that re-words or drops one of them is a defect, because the PR body claims the rows and a reader
of the document sees the pre-#1616 contract.

#### Scenario: The generated inventory is regenerated through the tree's own generator

- **Given** the restored rows on the branch head
- **When** the §10 inventory block is regenerated with `make architecture-refresh`
- **Then** `make architecture-check` and `architecture_bot.py --check` stay green and no
  generated section is hand-edited
- **Test:** tests/test_architecture_rows_1616.py::test_the_push_proves_ci_rows_still_name_issue_1616

#### Scenario: A later rebase drops a clause again

- **Given** a branch whose `ARCHITECTURE.md` matches master's (no `#1616` clause in any row)
- **When** the row guard runs over the REAL `ARCHITECTURE.md`
- **Then** it exits non-zero naming the missing clause and its row, so the drop is loud
- **Test:** tests/test_architecture_rows_1616.py::test_the_push_proves_ci_rows_still_name_issue_1616

#### Scenario: The repaired head carries every clause in its own row

- **Given** the repaired head with the four clauses restored verbatim from `5eea2616`
- **When** the row guard reads the REAL `ARCHITECTURE.md`
- **Then** each clause is found inside its own named row and the module exits 0
- **Test:** tests/test_architecture_rows_1616.py::test_the_push_proves_ci_rows_still_name_issue_1616
