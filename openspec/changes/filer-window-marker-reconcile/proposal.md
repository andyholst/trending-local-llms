# Proposal: filer-window-marker-reconcile

Issue: #1467

## Why

The failure filer's candidate scan was capped at `--limit 30` per workflow, so a filed push
failure that aged past the newest 30 runs of its workflow became invisible: no ledger row and not
even a line in `--dry` output. Measured on 2026-11-23, issue #1450 carries
`pipeline-run-failure: ... run=45231126714`, which ranks 39th of the newest 100 qa-validate runs,
while `data/pipeline_failures.json` has no row for it — the guard and close gates therefore
dead-end the issue permanently. The sibling #1164 PR-blockage scan had the identical fixed cap.
Run `45240782844` sat INSIDE the newest 30 yet still had no row, so the repair path itself was
missing, not only the window.

## What Changes

- Add ONE paginating `window_runs()` helper to `scripts/pipeline_failure_issue.py`: it walks the
  REST `actions/runs` pages (`gh run list` has no offset) until a page's oldest run leaves the
  window, projects the REST rows onto the camelCase shape both callers already read, and reports
  `truncated` when the page cap is reached so the sweep prints a loud partial-window line instead
  of reading a capped view as complete. BOTH scans (`main_pipeline_failures` ~:206 and
  `pr_triggered_failures` ~:369) go through it; neither keeps a `--limit 30` literal.
- Extend the marker scan into `failure_issue_markers(repo) -> {run_id: {number, state, url}}` and
  add `reconcile_marker_runs()`: every unfiled marker-carrying run is fetched DIRECTLY by id and
  classified loudly (not a failure / out of window / untracked event / unreadable → a named skip
  line and NO row), so a filed run joins the candidate set regardless of its rank in any list.
- Close the `"issue_number": None` hole: the marker-matched backfill records the marker issue's
  number/url, which is what lets the stamp pass reach the row once its fix lands.
- Make `pipeline_failure_guard_check.marker_issue_states` delegate to the filer's seam (ONE
  implementation, rule 6d), projecting to the gate's str-keyed shape.
- The PR-blockage half shares both seams: `already`/markers are computed unconditionally, and a
  grouped shape whose earliest run is marker-matched is BACKFILLED with the marker issue's
  number/url plus the group's own #1164 keys.
- Ship five Given/When/Then RED-first tests in `tests/test_pipeline_failure_issue.py`.

## Impact

Additive only (rule 3b): the ledger gains rows and fills nulls on NEW rows; no existing key or
value is removed, no consumer contract changes, no make target/stage/workflow/image/cron/data or
contract change. A genuinely absent run stays absent — the reconcile pass never invents a row.
A capped window walk is loud rather than silent. `AGENTS.md` §6r/§8 name the new behaviour and are
owed to rule 3c (see `findings.md`); `ARCHITECTURE.md` rows ride `make architecture-refresh`.

## Not covered

- No change to the filing threshold, the error extraction, the re-diagnosis/stamp/attribution
  passes, the PR-blockage grouping key or the grace.
- No AGENTS.md write from this headless leg (rule 3c): the §6r bullet and §8 row are recorded as
  an owed row and handed to `owner`.
- No cron, no workflow edit, no CI dispatch, no merge.
