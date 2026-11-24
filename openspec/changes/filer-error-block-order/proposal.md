# Proposal: filer-error-block-order

Issue: #1466

## Why

Rule 6r requires a filed pipeline failure to carry the failure's OWN error text and the exact
`make <target>` reproduction. The filer anchors extraction on the log region that GitHub's own
`##[error]` decoration marks as the step that ended the job (issue #1098) and fills the
`MAX_ERROR_LINES = 40` budget in tiers — but it then PRESENTS every selected line in log order, so
a thin failing region (a CI shell step, not a test module) is padded with earlier PASSING modules'
`PASSED n | FAILED 0` / negative-test `FAIL:` chatter printed ABOVE the two lines that actually
diagnose the run. Measured: qa-validate run 45240782844 filed #1459 with an error block of which only
the LAST TWO lines diagnose it, so a reader must scroll past dozens of unrelated lines to reach the
reproduction command. Issue #1098's §8 row claims the anchored extraction removed the
chatter-ahead-of-diagnosis defect; the anchor landed, the ORDER did not.

## What Changes

- `scripts/pipeline_failure_issue.py::extract_error_block` presents the FAILING-REGION lines FIRST —
  the anchored region that ended the job, in log order — then the strongest shapes from OTHER step
  regions, then a passing module's soft chatter. Everything after the region is preceded by ONE
  explicit `[filer] … FILLER …` marker line, so filler is announced as filler rather than merged
  silently into log order above the diagnosis. Selection (tiers, de-dupe, cap), the end-of-block drop
  note and the ungrouped-log fallback keep today's behaviour.
- `tests/test_pipeline_failure_issue.py` locks BOTH directions: a thin failing region emits its
  diagnosis before any chatter, and a region that genuinely holds the diagnosis keeps today's order.
  `tests/test_pipeline_failure_error_block.py`'s whole-block "keeps log order" assertion becomes the
  per-group contract.
- `AGENTS.md` §6r + §8: the presentation sentence names the region-first order and the filler
  marker, and the §8 guard row carries it. Attended run (rule 3c): this PR IS the sign-off and the
  issue thread states which sections changed.

**Not covered:** no change to the selection tiers or the `MAX_ERROR_LINES` cap; no rewriting of an
already-filed issue body (rule 6j); no change to the ledger schema; no fix of the separately
tracked re-diagnosis rows (#1136).

## Impact

- Affected code: `scripts/pipeline_failure_issue.py` (presentation only).
- Affected tests: `tests/test_pipeline_failure_issue.py`,
  `tests/test_pipeline_failure_error_block.py`.
- Rulebook: `AGENTS.md` §6r + §8 (review-required, rule 3c).
