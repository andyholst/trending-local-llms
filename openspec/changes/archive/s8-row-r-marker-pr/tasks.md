# Tasks: s8-row-r-marker-pr

- [x] Name #1284 and the PR-field guard in the §8 row for `tests/test_watch_monitor.py`
- [x] Regenerate the §10 inventory and run `make architecture-check`
- [x] Run `make lint`, the row guards, and `make test`
- [x] Write `findings.md`, regenerate `OPENSPEC.md` and run `make openspec-check`
- [x] Compose the PR body, open the PR, record and archive the change, push and monitor the checks

Evidence:

- The row now carries `issues #1266/#1282/#1312/#1284`, the marker shape
  `R:<run>:<status>:<conclusion>[:<workflow>][:<pr>]`, and the
  `test_r_marker_carries_its_pull_request` guard with its RED-on-base proof.
- `make lint` 0 findings; `tests/test_agents_rows.py` `PASSED 124 | FAILED 0` (the §8 table
  still parses, every named module still exists); `tests/test_watch_monitor.py` `PASSED 55 | FAILED 0`.
- `make architecture-check` green after the §10 refresh (the fetched base carried a stale block again).
- Rule 3c: the section and reason were declared on #1336's thread BEFORE this edit.
