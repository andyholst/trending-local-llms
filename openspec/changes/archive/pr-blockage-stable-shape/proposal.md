# Proposal: pr-blockage-stable-shape

Issue: #1476
PR: #1555

## Why

A master-move race reds one PR per branch. Five concluded-bad `qa-validate` runs inside one hour
failed the SAME step with the SAME first line, and the filer recorded none of them: measured on
host `asimov@omarchy`, `make pipeline-failure-issue REPO=… DRY=1 WINDOW_HOURS=6` answered
`failures=1 filed=0`. Cause read out of the seam: `failure_shape` digested the WHOLE extracted
block, and a state-gate failure presents as two diagnosis lines plus a `[filer] … FILLER …` marker
and then whatever passing modules printed — so every head hashed differently and
`PR_BLOCK_MIN_PRS` (2 distinct OPEN branches) was unreachable for a per-branch race. A prefix
digest was already wrong in the other direction (#1175); the region boundary is the seam neither
error points past.

## What Changes

- `failure_shape` anchors on the FAILING STEP region's own quoted lines (everything before the
  ONE `[filer] … FILLER …` marker), keeping the failing step names and the `make` targets. A
  block with no filler marker is digested whole, so #1175's later-line discrimination is unchanged.
- Add `exact_failure_shape` — the pre-change whole-block digest — and use it as a SECOND dedup
  axis in `group_pr_blockages`, so a group forms on either key while the stable shape is the one
  recorded.
- Each PR-blockage item carries an additive `exact_shape`; the ledger gains no new key (rule 3b).
- A filed PR-blockage issue NAMES every blocked OPEN pull request (`compose_body`/`file_issue`
  gain an optional `branches`), so the thread carries the fleet-wide scope and not only the ledger
  row.
- `tests/test_pipeline_failure_issue.py` drives the REAL filer against the stub `gh` with two
  diverging-chatter logs of one defect on two different OPEN branches: RED on the base revision
  (`create-count=2`, no `run=700` body), GREEN at the head (one issue naming `ci/a` and `ci/b`).

## Impact

No data format, contract, image or workflow wiring change. The master/schedule half of the filer
is untouched; a lone red PR is still that author's own noise. Only the PR-blockage grouping key and
the optional body scope change, and both are additive for a caller that passes no branches.

## Not covered

- No change to `extract_error_block`'s tiers or presentation (#1098/#1466 stay as they are).
- No change to `PR_BLOCK_MIN_PRS`, the log-read budget (#1174) or the window walk (#1467).
- No CI dispatch, no merge, no master push, no collaborator grant.
