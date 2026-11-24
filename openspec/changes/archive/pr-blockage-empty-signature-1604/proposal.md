# Proposal: pr-blockage-empty-signature-1604

Issue: #1604
PR: #1636

## Why

`make pipeline-failure-issue` (rule 6r's ONE filer seam) can file a **PR-blockage issue
from runs whose failure signature is EMPTY**. Measured live on master `cb139e7c`:

```text
$ make pipeline-failure-issue REPO=andyholst/trending-local-llms WINDOW_HOURS=8 DRY=1
WOULD FILE pr-blockage shape da39a3ee5e6b on 2 open PR(s): ci/data-gap-1586-dispatch-guard-rulebook,
docs/agents-store-rows-1482 (run 45393037859)
```

`da39a3ee5e6b` is `sha1("")[:12]`. `failure_shape()` reduces to
`sha1("|".join(steps + targets + region_skeleton))`, so a job with no failing step names, no
`make` targets and no extracted region lines yields the empty key — and two runs with
**different** real errors (or two cancelled/superseded runs carrying no error text at all)
collapse into ONE "blockage" group. That issue body would carry NO error text, which rule 6r
explicitly forbids ("the failure's OWN error text — never a bare 'CI is red' artifact").

## What Changes

- The PR-blockage pass (#1164) spends `failure` runs ONLY. A `cancelled` PR-triggered run is
  SUPERSEDED by the newer head that replaced it (the queued/ghost alarms own that state) and
  carries no error text, so it is dropped before any log read or grouping. The master/schedule
  half keeps `BAD_CONCLUSIONS` (`failure` + `cancelled`): there a cancelled push run IS
  meaningful — a dropped cron delivery.
- A member whose signature is EMPTY on BOTH axes (`EMPTY_SHAPE = sha1("")[:12]`) is skipped by
  `group_pr_blockages`, never grouped. A signature is empty only when the failing steps, the
  `make` targets and the failing-region lines are ALL absent, so two unrelated branches can no
  longer collapse into one content-free blockage.
- Two regression tests drive the REAL seams: the unit test proves the candidate filter and the
  grouping (cancelled runs, empty signatures, and a real shared region that still groups); the
  end-to-end test drives the real filer through its stub `gh` scene and proves two cancelled
  open-PR runs file nothing.

## Impact

- `scripts/pipeline_failure_issue.py` — the `PR_BLOCK_CONCLUSIONS` / `EMPTY_SHAPE` constants,
  `pr_block_candidates`' conclusion filter and `group_pr_blockages`' empty-member skip. No make
  target changes; `make pipeline-failure-issue` is the ONE caller.
- `tests/test_pipeline_failure_issue.py` — two new tests (both RED on the base script: 5 named
  FAILs; green `PASSED 337 | FAILED 0`).
- `AGENTS.md` §8 — the EXISTING row for `tests/test_pipeline_failure_issue.py` must be extended
  to name the new guard. This is a protected agent-instruction file, so a headless leg records it
  as an OWED ROW instead of writing it (rule 3c).

## Not covered

- The master/schedule half's handling of cancelled runs: unchanged on purpose (a cancelled push
  run is a tracked delivery accident there).
- The `exact_failure_shape` axis semantics for non-empty blocks: unchanged.
- A rerun/superseded run whose conclusion is `failure` but whose jobs carry no error decoration:
  it is handled by the same empty-signature skip, not by a new run-state lookup.
