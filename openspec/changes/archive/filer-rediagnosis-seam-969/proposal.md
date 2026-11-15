# Change: filer-rediagnosis-seam-969

Issue: #969
PR: #985

## Why

`make pipeline-failure-issue` files a failed main-pipeline run UNDIAGNOSED when its own log fetch
fails, and today it never revisits those rows: `data/pipeline_failures.json` has no code path that
re-reads a run whose log later became readable (issue #923 fixed the reader, but the 14 rows filed
before the fix stay UNDIAGNOSED forever unless a human re-diagnoses each one by hand — measured:
#820–#825 all needed a manual change each). A filer that re-reads every still-`undiagnosed` row on
its next scheduled sweep repairs the whole class automatically, with no per-row manual change.

## What Changes

- `scripts/pipeline_failure_issue.py` gains a re-diagnosis pass inside `sweep()`: for every ledger
  row carrying `undiagnosed` and no `rediagnosed_utc`, it re-derives the failed job from the run's
  job list, re-fetches its log through the escape-tolerant reader, and raises the row
  APPEND-ONLY — adds `rediagnosed_utc`, `error_excerpt` (scrubbed) and `rediagnosis_note`, GROWS
  `targets` only (rule 3b: nothing removed or shrunk, the `undiagnosed` field KEPT).
  `fix_pr`/`guard` stay null — attribution remains each fix's own decision (rule 6r).
- A row whose log is STILL unreadable is reported loudly per sweep and retried next sweep — never
  marked done on a failure.
- `--dry` previews the raise (`WOULD RAISE`) and writes nothing.
- No new make targets, no workflow changes: the pass rides the existing weekly
  `queued-alarm.yml` call of `make pipeline-failure-issue`, and the existing ledger-PR step lands
  the raises (its `git diff --quiet -- data/pipeline_failures.json` check sees modified rows).

## Impact

- Capability: `alarms` (rule 6r filer)
- Affected code: `scripts/pipeline_failure_issue.py`, `tests/test_pipeline_failure_issue.py`,
  `ARCHITECTURE.md` (two descriptive rows)
- Not covered: a terminal "log expired" state for rows whose logs age out of Actions retention
  (filed as a finding by this change — rule 6g: analysis files, a separate change fixes);
  attribution of `fix_pr`/`guard` for the remaining UNDIAGNOSED issues (each fix's own change).
