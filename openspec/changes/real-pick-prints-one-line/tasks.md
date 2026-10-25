# Tasks

- [x] 1. Write the proposal + `issue-queue` capability spec for issue #578.
- [x] 2. `tests/test_issue_review.py::test_the_real_issue_pick_prints_exactly_one_line`: the REAL `make issue-pick` with the `gh` stub on PATH.
- [x] 3. Assert stdout is exactly one `issue=<n>` line, no command echo, and the reasoning on stderr.
- [x] 4. Verified RED by un-silencing the recipe (3 failures naming `python3 scripts/issue_queue.py --pick …` as the first line) and GREEN after (127 passed).
- [x] 5. `findings.md` written.
- [x] 6. `make openspec-index`, `make openspec-check`, `make architecture-check`, `make lint` green.
