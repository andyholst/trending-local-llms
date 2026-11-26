# Proposal: ci-keeper-ledger-45788860357

Issue: #1784

## Why

`make pipeline-failure-guard-check` is a required `qa-validate` gate. Merged keeper PR #1777
(`fix(ci): archive the three completed openspec changes - Closes #1763`, squash `d286fb38`) closed
pipeline-failure issue #1763 with a bare `Closes` and no `data/pipeline_failures.json` row for its
run 45788860357. The gate therefore REDs on every open PR: "issue #1763 (run 45788860357) is
CLOSED but the ledger records nothing for that run". Issue #1784 tracks this; its body hands the
keeper attribution/guard PR to `tll-implementer` (remedy 2).

## What Changes

- Append ONE diagnosed ledger row for run 45788860357 (event `push`, workflow `qa-validate.yml`,
  failing job `validate`, target `openspec-archive-check`) with `fix_pr` #1777 (merged 13:28:28Z,
  the closer of #1763) and collected guard `tests/test_openspec_archive_check.py`.
- Append-only: no existing key or value is removed, renamed or shrunk.
- This PR is a keeper with NO closing keyword; it records a fix, it does not implement/close an issue.

## Impact

- Capability: `pipeline-failure-ledger` — a merged fix for a closed pipeline-failure issue is
  recorded with its guard, so the required gate reports it as landed instead of RED on every PR.
- No model, measurement, data-store, contract, workflow or rulebook value changes.

## What is not covered

- The owner's alternative remedy (reopening #1763) is not taken here: this records the landed fix.
- The systemic guard gap named in #1784 (a `Closes` with no ledger row re-reds the fleet) is left
  to a separate reviewed change; this keeper only clears the recorded red.
