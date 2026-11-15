# Tasks

- [x] 1. The tracked change exists (this directory) before any code or test edit
- [x] 2. `scripts/data_gap_analysis.py::issue_body` returns a body ending in a
      trailing newline, with an inline comment naming the contract
- [x] 3. Both fake-gh stubs (`_GH_STUB`, `_GH_STUB_LABELS`) document the
      newline contract on their `issue create` arms
- [x] 4. The suite gains
      `tests/test_data_gap_analysis.py::test_the_gap_issue_body_ends_with_a_newline`
      asserting the body ends in `\n` and the marker line survives the stub
      consumption path
- [x] 5. `OPENSPEC.md` index regenerated (this change active); the existing
      `test_data_gap_analysis.py` tests still pass; `make lint` clean (files
      end in a newline)
- [~] 6. AGENTS.md §8 gains a row for the new guard `test_the_gap_issue_body_ends_with_a_newline` — blocked: rule 3c human sign-off (AGENTS.md protected in a headless leg; the full row text is recorded as the owed-row finding on this change and applied by an attended run)
