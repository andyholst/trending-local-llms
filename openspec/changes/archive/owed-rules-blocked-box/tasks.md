# Tasks: owed-rules-blocked-box

- [x] `scripts/file_findings.py`: accept an optional `- **Owed-row:**` field,
      validate it through `bot_markers.parse_owed_rows` (loud failure when it
      declares nothing), and render the filed body's marker through
      `bot_markers.owed_row_marker` — verified by
      `tests/test_file_findings.py` (owed-row tests green, negatives red-then-fixed)
- [x] `issue-implement` skill: owed-rulebook contract — blocked box written at
      creation, full row text into an Owed-row finding, bare `- [ ]` forbidden —
      pinned by `tests/test_workflows.py::test_the_implement_leg_never_leaves_an_owed_rulebook_row_bare`
- [x] `AGENTS.md` §6g: state the owed-row blocked-and-declared contract
      (rule 3c; review-required diff, signed off by the PR review)
- [x] `AGENTS.md` §8: add the guard row for the new tests
- [x] Regenerate `OPENSPEC.md` (`make openspec-index`) and the generated
      `ARCHITECTURE.md` block (`make architecture-refresh`); both checks green
