# Proposal: filer-error-block-names-the-failing-step

Issue: #1098

## Why

Rule 6r says a filed pipeline failure must carry the failure's OWN error text. The filer's
extraction (`scripts/pipeline_failure_issue.py:267` `extract_error_block`) scans the whole 60 KB
log tail for ANY error-shaped line — `##[error]`, `make: ***`, `FAIL: `, `FAIL `, `FAILED`,
`Traceback` — de-dupes and caps at `MAX_ERROR_LINES = 40`, with no notion of WHICH step wrote a
line. Measured on the real log of qa-validate run 43725338063 (job 132845951479): the tail holds
46 error-shaped lines, 43 of them are a PASSING module's planted-fixture chatter (`FAIL: m1:
engines not ordered newest-date-first`, `PASSED 199 | FAILED 0`), and the three lines that
actually diagnose the run — `[openspec-index] FAIL OPENSPEC.md is stale or missing (2 active, 305
archived on disk)`, `make: *** [Makefile:367: openspec-index-check] Error 1`, `##[error]Process
completed with exit code 2.` — are hits #43-#45 and are CUT BY THE CAP. That is why ledger rows
`43716345030`, `43716362366`, `43718826142`, `43725338063` carry `targets: []` and why issues
#1040-#1043 were filed quoting noise: the reproduction command the issue promises was never read,
so a red gate was filed with no way to reproduce it (measured consequence: the four issues had to
be closed on ledger proof rather than on the diagnosis in their own bodies).

## What Changes

- `extract_error_block` becomes **region-aware and failure-anchored**. GitHub writes every step's
  output as a `##[group]<label>` … `##[endgroup]` region and writes its own `##[error]`
  decoration INSIDE the region of the step that ended the job, so the region carrying
  `##[error]` is the diagnosis, not a guess. New seams in the filer (one implementation, rule 6d):
  `log_regions`, `failing_region`, `failing_step_names`, and a tiered `extract_error_block`
  (strong shapes inside the failing region first, then soft shapes there, then strong shapes
  elsewhere, then a passing module's soft chatter ONLY for spare room), selecting by tier and
  presenting in log order; when chatter is dropped for room, the block says so.
- The filed issue and the ledger row name the failing step TWICE from two real sources: GitHub's
  own job `steps[]` (conclusion `failure`/`cancelled`) and the label of the log region the block
  was taken from. Additive ledger keys `failing_steps` and `error_region` (rule 3b: keys added,
  never removed or shrunk; existing rows untouched).
- When a block yields no `make` target while the failing step IS known, the filing line and the
  issue say so explicitly instead of quoting whatever noise filled the cap.
- The re-diagnosis pass (issue #987) extracts through the SAME seam, so a row re-read later gets
  the same diagnosis.

**Not covered:** no rewriting of an already-filed issue body (the filer never edits a body, rule
6j); no rewrite of the four `targets: []` rows' stored values (rule 3b — a removal is a human
decision); no change to `data/pipeline_failures.json` history; no fix of the separately filed
`error_excerpt`-empty rows finding (#1136).

## Impact

- Affected specs: `alarms` (the pipeline-failure filer requirement).
- Affected code: `scripts/pipeline_failure_issue.py` (extraction + filing),
  `tests/test_pipeline_failure_error_block.py` (new guard), the `queued-alarm` filer step unchanged.
- Affected tests: new module; `tests/test_pipeline_failure_issue.py` keeps its existing contracts.
