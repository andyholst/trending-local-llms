# Tasks: queue-closing-pr-implementer

- [x] Read each open PR's body and mark a closing PR's issue as implemented in `scripts/issue_queue.py`
- [x] Add the RED-first guard in `tests/test_issue_review.py`
- [x] Prove the guard RED against the base revision of the queue
- [x] Run `make lint`, the module, and `make test`
- [x] Write `findings.md`, regenerate `OPENSPEC.md` and run `make openspec-check`
- [x] Compose the PR body, open the PR, record and archive the change, push and monitor the checks

Evidence:

- RED on the base revision (`git show origin/master:scripts/issue_queue.py`), driven in the test container:
  `FAIL queue: a fix/-prefixed closing PR marks its issue implemented` and the base output shows the exact bug —
  `issue=1176 position=0 has_implementer=0 … reason=next-sweep` while an open `fix/pr-block-grace-derived-1176`
  carries one `closes #1176`.
- GREEN after: `PASSED 141 | FAILED 0` in the same container.
- The binding is read through `pr_closure.closing_bindings` (the ONE parser, rule 6d); the guard also pins that
  the module names it, so a second copy of the keyword list turns CI red.
- `make lint` and `make architecture-check` green; the §10 inventory did not move (the module docstring is unchanged).
