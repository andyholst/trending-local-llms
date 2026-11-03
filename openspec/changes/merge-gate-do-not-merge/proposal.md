# The qa-validate merge gate honors a do-not-merge label

**Issue:** [#722](https://github.com/andyholst/trending-local-llms/issues/722)
**Capability:** `merge-gate-do-not-merge`

## Why

GitHub-native auto-merge on the `qa-validate` pipeline's `auto-merge` job
(`.github/workflows/qa-validate.yml`) squashes-merge the instant `validate` and
`live-smoke` are green at the head. Its `if:` gate checks only `success()`,
event type, non-draft, same-repo fork, and `head_ref != master/main` — it has
no concept of a hold. Two live incidents proved the advisory-hold gap: PR #713
(order-guard fixture-tolerant) and PR #719 (exact Most-loved heading) both
auto-merged on green after the planner issued an advisory hold. The owner
requires a mechanical "do-not-merge" state: a PR carrying the `do-not-merge`
label must never be auto-merged by the gate, regardless of CI result.

## Delivery (non-breaking)

A labeled PR simply does not auto-merge; it stays OPEN. No schema/contract/API/
table/data-shape change.

- `.github/workflows/qa-validate.yml` — in the `auto-merge` job, add a
  `Hold if PR carries the do-not-merge label (#722)` step (id `dnm-check`)
  BEFORE the squash-merge step. It reads the PR labels; if `do-not-merge` is
  present it echoes the hold and sets `hold=true` WITHOUT calling `gh pr merge`,
  so the PR stays OPEN and the run stays green/honest (a hold, not a fail). The
  squash-merge step's `if:` mirrors the check
  (`steps.dnm-check.outputs.hold != 'true'`) so a label that appears mid-run
  still pries the merge off.
- `tests/test_workflows.py` — `test_auto_merge` now finds the merge step by
  behaviour (`gh pr merge` in its run) and adds do-not-merge wiring assertions;
  the merge step is unambiguously located even though the hold step's name also
  contains the substring "merge". New `test_auto_merge_holds_a_do_not_merge_labeled_pr`
  executes the REAL hold step (stub `gh`) for labeled -> hold=true and
  unlabeled -> hold=false.
- `openspec/changes/merge-gate-do-not-merge/` — this change dir.
