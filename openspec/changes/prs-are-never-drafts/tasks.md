# Tasks

- [x] 1. Write the proposal + spec for issue #276 (`pr-lifecycle`: a run opens a reviewable PR).
- [x] 2. `AGENTS.md` rule 6e: the PR is opened **ready for review, never `--draft`**, with why (the merge gate skips a draft) + the §8 row for the new guard; the rule-3c disclosure comment on #276 names the section.
- [x] 3. `tests/test_workflows.py::test_no_pipeline_opens_a_draft_pr` — no `gh pr create` in any workflow carries `--draft`, and the two branch-cutting pipelines open theirs against `master` with the PAT, ready for review; registered in `main()`.
- [x] 4. Verified: `make test`, `make lint`, `make openspec-check`, `make architecture-check` green; the new guard shown failing on a workflow that opens a draft.
- [x] 5. `OPENSPEC.md` regenerated (`make openspec-index`); PR #272 updated (marked ready for review — a draft is excluded by the merge gate — and its body now names this change).
