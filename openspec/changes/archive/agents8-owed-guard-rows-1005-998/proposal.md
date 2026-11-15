# Proposal: agents8-owed-guard-rows-1005-998

Issue: #1005 · #998
PR: #1063

## Why

Two guards shipped registered in `make test` but undiscoverable from the rulebook: the
newline contract of the data-gap filer's body renderer (#1002, landed by PR #1003 — guard
`test_the_gap_issue_body_ends_with_a_newline`) and the ledger-evidence gate on closing
pipeline-failure issues (#993, landed by PR #995 — guard
`test_a_pipeline_failure_close_is_accepted_only_with_a_merged_ledger_row`). Rule 6c requires
each guard's §8 row in the same change; both changes were headless legs, so the rows became
owed-row ledger items #1005 and #998 (rule 3c: `AGENTS.md` is protected, the sign-off is an
attended act). `make owed-rows-check` reports both OUTSTANDING. This is the attended landing
of both rows, with their pin tests, exactly as #1001 was landed by #1013.

## What Changes

- `AGENTS.md` §8 gains the two owed rows. Each carries its ledger needle verbatim and
  contiguous — `tests/test_data_gap_analysis.py::test_the_gap_issue_body_ends_with_a_newline`
  and
  `tests/test_issue_triage.py::test_a_pipeline_failure_close_is_accepted_only_with_a_merged_ledger_row`
  — beside the rows of their sibling guards, so `make owed-rows-check` reports each LANDED
  with its `AGENTS.md:<line>` evidence.
- `tests/test_agents_rows.py` gains two pin tests, one per row (rule 6c: the row and its pin
  ship together; a removed or gutted row goes red).

## Impact

- `AGENTS.md` §8 (two new table rows)
- `tests/test_agents_rows.py` (two new pins)

## Not covered

- No behaviour change: the guards, the renderer and the verdict gate are already landed;
  this change makes them discoverable in the rulebook and closes the two owed-row ledger
  items. Closing those issues happens through their own threads after the ledger reports
  LANDED (rule 6j: a close with the ledger quoted on the thread).
