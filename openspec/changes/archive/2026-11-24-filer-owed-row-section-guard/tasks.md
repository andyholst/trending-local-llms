# Tasks: filer-owed-row-section-guard

- [x] `scripts/file_findings.py` refuses an explicit `- **Owed-row:**` whose section id is not a
  `## <id>.` heading in `AGENTS.md`, through `owed_rows_check.sections()` — verified: the new
  guard test's refusal branch is green (`NOT an AGENTS.md` + the unknown id named) and NO
  `gh issue create` call is made
- [x] A real heading still files exactly one issue carrying the ONE registered marker — verified:
  the same test's non-vacuity branch (`section=8`) exits 0 with `issue create` called once
- [x] RED-first: the same module against `origin/master`'s `scripts/file_findings.py` answers
  `PASSED 7 | FAILED 1`; on this head `PASSED 8 | FAILED 0`
- [x] OpenSpec change created with proposal, capability spec (per-scenario `**Test:**` lines) and
  this checklist; `OPENSPEC.md` regenerated
- [x] Fast offline gates on the branch: `make lint`, `make openspec-index-check`,
  `python3 scripts/pr_body.py --check-body-file` for the PR body
- [~] The EXISTING `AGENTS.md` §8 row for `tests/test_filer_owed_rows.py` is extended to name `test_an_explicit_owed_row_section_that_is_not_a_heading_is_refused` — blocked: rule 3c human sign-off (AGENTS.md protected in a headless leg); declared in `findings/1642.md` as an owed row
