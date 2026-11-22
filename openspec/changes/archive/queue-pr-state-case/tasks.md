# Tasks: queue-pr-state-case

- [x] Compare the PR state case-insensitively in ONE helper in `scripts/issue_queue.py`
- [x] Add the RED-first guards in `tests/test_issue_review.py` (real `OPEN` spelling + the one-place seam)
- [x] Prove the guards RED against the base revision of the queue
- [x] Run `make lint`, the module, and `make test`
- [x] Write `findings.md`, regenerate `OPENSPEC.md` and run `make openspec-check`
- [x] Compose the PR body, open the PR, record and archive the change, push and monitor the checks

Evidence:

- **Byte-checked on the real gh** (`origin/master` `9250657`): `repr(pull['state'])` → `'OPEN'`;
  `pull['state'] == 'open'` → `False`; `pull['state'].lower() == 'open'` → `True`;
  `issue_queue._closes_issue(pull, 1176)` → `True`. The parser and the body were fine — only the
  state comparison was dead.
- RED on the base seam (`git show origin/master:scripts/issue_queue.py`): `PASSED 9 | FAILED 2`,
  and the failure prints the exact production symptom — `issue=1176 position=0 has_implementer=0 …
  reason=next-sweep` while an `OPEN` PR closes #1176.
- GREEN after: `PASSED 16 | FAILED 0`.
- **Live proof**: running the fixed `build()` against the real repo, #1176 is no longer offered at
  all (it has an implementer) — before the fix it was `position=2 … reason=next-sweep`.
- The guard's fixture now plants gh's real `OPEN` spelling (it defaulted to lowercase `open`, which
  is why the suite passed while production failed), and pins that the seam carries exactly one
  `get("state")`.
- `make lint` and `make architecture-check` green; the §10 inventory did not move.
