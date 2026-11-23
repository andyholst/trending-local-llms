# Tasks: watcher-files-red

- [x] Add the filing half to §6w's `R:` duty
- [x] Pin the duty and the filer seam in `tests/test_watch_monitor.py`
- [x] Prove the guard RED against the base revision of the rulebook
- [x] Run `make lint`, the module, and `make test`
- [x] Write `findings.md`, regenerate `OPENSPEC.md` and run `make openspec-check`
- [x] Compose the PR body, open the PR, record and archive the change, push and monitor the checks

Evidence:

- **RED on the base rulebook** (`git show origin/master:AGENTS.md`): `PASSED 93 | FAILED 2` —
  `FAIL §6w names 'a concluded-bad run is FILED'` and `FAIL §6w names 'on a PR pipeline is filed'`.
- GREEN after: `PASSED 95 | FAILED 0`.
- The guard also pins all six main pipeline names and that `pipeline-failure-issue:` is a real
  `make` target, so the duty cannot be watered down to a pipeline that does not exist.
- `make lint` 0 findings, `make architecture-check` green, `tests/test_agents_rows.py`
  `PASSED 124 | FAILED 0`.
- Rule 3c: the section and reason were declared on #1376's thread BEFORE the edit.
