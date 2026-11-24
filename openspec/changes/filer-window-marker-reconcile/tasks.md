# Tasks: filer-window-marker-reconcile

- [x] Create the tracked OpenSpec change with proposal + Given/When/Then capability spec bound to #1467
- [x] Add the paginating `window_runs()` seam and route BOTH scans (`main_pipeline_failures`, `pr_triggered_failures`) through it, with a loud page-cap overflow line
- [x] Extend the marker scan into `failure_issue_markers` and add `reconcile_marker_runs`; compute markers unconditionally in `sweep` and dedupe the merged candidate set
- [x] Close the `"issue_number": None` hole: the marker-matched backfill records the marker issue's number/url
- [x] Make `pipeline_failure_guard_check.marker_issue_states` delegate to the ONE filer seam
- [x] Backfill a marker-matched PR-blockage group's ledger row with the marker issue and the group's own #1164 keys
- [x] Ship the five Given/When/Then RED-first tests in `tests/test_pipeline_failure_issue.py` and RED-verify them against `origin/master`
- [x] Run `make lint` and the targeted modules (`test_pipeline_failure_issue.py`, `test_pipeline_failure_guard.py`) on the head
- [x] Update the `ARCHITECTURE.md` target/script rows, regenerate `OPENSPEC.md` and keep the architecture block current
- [~] Land the `AGENTS.md` §6r behaviour bullet and the §8 test row — blocked: rule 3c human sign-off (AGENTS.md protected in a headless leg); the full row text is recorded in `findings.md` with an `owed-row` marker and handed to `owner`
