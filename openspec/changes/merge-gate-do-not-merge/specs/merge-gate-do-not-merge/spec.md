# merge-gate-do-not-merge

## ADDED Requirements

### Requirement: a do-not-merge-labeled PR is never auto-merged by the merge gate

The `qa-validate` pipeline's `auto-merge` job merges a green PR the instant
`validate` and `live-smoke` go green. A PR carrying the `do-not-merge` label
must NOT be auto-merged by that gate, however green it is: the labeled PR stays
OPEN and the run stays green (the hold is a hold, not a failure). Removing the
label lets the same green PR auto-merge normally, and a PR without the label
behaves exactly as before.

WHEN the `auto-merge` job runs against a green PR
THEN it checks the PR's labels for `do-not-merge` before any merge call,
AND a PR carrying `do-not-merge` is NOT merged (no `gh pr merge`, PR stays OPEN),
AND an unlabeled PR merges exactly as before,
AND the squash-merge step's `if:` also skips while the label is present.

#### Scenario: a labeled green PR is held, not merged

- **Given** a PR with validate + live-smoke green that carries the `do-not-merge` label
- **When** the `auto-merge` job runs
- **Then** it reports the hold and exits without calling `gh pr merge` (PR stays OPEN, run green)
- **Test:** `tests/test_workflows.py::test_auto_merge_holds_a_do_not_merge_labeled_pr` — real hold step, stub `gh`, labeled -> `hold=true`, output names the hold

#### Scenario: an unlabeled green PR merges normally

- **Given** a green PR without the `do-not-merge` label
- **When** the `auto-merge` job runs
- **Then** `hold=false`, the squash-merge step runs exactly as before (squash, delete branch, owner PAT)
- **Test:** `tests/test_workflows.py::test_auto_merge_holds_a_do_not_merge_labeled_pr` — real hold step, stub `gh`, unlabeled -> `hold=false`; `test_auto_merge` keeps the existing squash-merge assertions

#### Scenario: the hold runs before the merge and the merge step mirrors the check

- **Given** the `auto-merge` job steps
- **When** they are read in order
- **Then** the do-not-merge hold step precedes the squash-merge step, and the squash-merge step's `if:` carries `steps.dnm-check.outputs.hold != 'true'`
- **Test:** `tests/test_workflows.py::test_auto_merge` — wiring assertions (hold present, before merge, reads labels, `if:` mirror)
