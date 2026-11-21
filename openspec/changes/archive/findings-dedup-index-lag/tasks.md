# Tasks

- [x] 1. The tracked change exists (this directory) before any script or test edit
- [x] 2. `scripts/file_findings.py::already_filed` gains `attempts` / `delay`: a read that may
      follow a create re-reads the label list with a pause until the index catches up
- [x] 3. `scripts/file_findings.py::file_findings` waits for a just-created issue to become
      discoverable before reporting success, and exits non-zero (naming the duplicate risk)
      when it never does
- [x] 4. `tests/test_file_findings.py`: the gh stub models the index lag (`FAKE_GH_LAG`), and
      `test_two_immediate_invocations_file_exactly_one_issue` +
      `test_a_create_that_never_becomes_discoverable_fails_loudly` lock both behaviours
      (both RED on the pre-change script)
- [x] 5. Gates green on the exact head: `make lint`, `make test`, `make openspec-check`,
      `make architecture-check` (with `make architecture-refresh` for the script docstring)
