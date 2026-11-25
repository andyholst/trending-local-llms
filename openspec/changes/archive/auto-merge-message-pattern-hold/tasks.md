# Tasks: auto-merge-message-pattern-hold

- [x] `qa-validate.yml`'s `auto-merge` job runs `make pr-message-check PR_EVENT=github.event_path`
  before any rebase/squash step and publishes the allowlisted `hold=` key — verified by the new
  guard test's structural checks and by executing the REAL step shell against a stub `make`
- [x] A refusal HOLDS: the rebase, head-check, squash-merge and closure-proof steps all carry
  `steps.message-check.outputs.hold != 'true'` in their `if:` — verified: the executed step exits 0
  with `hold=true`, prints the refusal, and makes no `gh pr merge` call
- [x] A clean verdict keeps the merge path byte-identical — verified: the executed step exits 0
  with `hold=false`; the squash command itself is unchanged (same owner PAT, `--match-head-commit`,
  `--subject`/`--body-file`)
- [x] RED-first: the same module against `origin/master`'s `.github/workflows/qa-validate.yml`
  answers `FAIL` on the hold's existence/ordering/gating checks; green on this head
- [x] OpenSpec change created BEFORE the code (proposal, capability spec with per-scenario
  `**Test:**` lines, this checklist); `OPENSPEC.md` regenerated
- [x] Fast offline gates on the branch: `make lint`, `make architecture-check`,
  `make openspec-check`, `make check-secret-output`
- [~] The EXISTING `AGENTS.md` §8 row for `tests/test_workflows.py` is extended to name `test_auto_merge_holds_a_non_conforming_body` — blocked: rule 3c human sign-off (AGENTS.md protected in a headless leg); declared in `findings/1704.md` as an owed row
