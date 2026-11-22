# Tasks: queue-open-window

- [x] Request `--state open` in `scripts/issue_queue.py::_pulls`
- [x] Add the RED-first guards in `tests/test_issue_queue_predicate.py`
- [x] Prove the guards RED against the base revision of the queue
- [x] Run `make lint`, the module, and `make test`
- [x] Write `findings.md`, regenerate `OPENSPEC.md` and run `make openspec-check`
- [x] Compose the PR body, open the PR, record and archive the change, push and monitor the checks

Evidence:

- **RED on the base seam** (`git show origin/master:scripts/issue_queue.py`): `PASSED 17 | FAILED 3`, and the
  failure reproduces the production symptom exactly — `issue=1176 position=0 has_implementer=0 … reason=next-sweep`
  while a live OPEN PR (#1289) closes #1176 and 150 newer `MERGED` rows filled the window
  (`the live open closing PR is in the window [9149, 9148, 9147, 9146, 9145]`).
- GREEN after: `PASSED 20 | FAILED 0`.
- The guard drives the REAL `_pulls`/`build` through a stub `gh` that honours `--state` and `--limit`
  (the only stand-in is the external CLI, rule 6m), so a return to `--state all` turns CI red.
- `make lint` and `make architecture-check` green; the §10 inventory regenerated (226 → 228 lines)
  because `issue_queue.py`'s docstring changed.
