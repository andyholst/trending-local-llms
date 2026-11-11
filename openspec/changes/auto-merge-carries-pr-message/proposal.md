## Why

qa-validate's `auto-merge` calls `gh pr merge --squash` with no `--subject`/`--body`, so GitHub composes the landed squash commit from the PR **title alone**. This repository's own push gate on master (`make commit-message-check`, wired by the message-pattern change #771 in `pr-closure.yml`) refuses a title-only commit — so **every bot merge leaves master red**. Measured: run 43050329961 landed squash `d3d4116` as the single line "fix(tech-debt): implement #779 archive-check gates the closing PR (#785)" — four of the five required sections missing, no bound `Closes`, and every later agent is misled into blaming its own PR for the master failure.

## What Changes

- The `auto-merge` merge step reads the merged PR's own title and body (`gh pr view --json title` / `--json body`) and passes BOTH to the merge: `--subject <title>` and `--body-file <body>`. The body arrives through a file, never shell interpolation (it is arbitrary markdown).
- `tests/test_workflows.py::test_auto_merge` gains three guards: the merge step reads the merged PR's title and body first, and passes `--subject` and `--body-file`. The guards go RED on the old step (rule 6c).
- `ARCHITECTURE.md` §4 auto-merge row and an `AGENTS.md` §8 regression-guard row scroll with the change.

## Impact

Affected specs: qa-pipeline (auto-merge lands a commit carrying the PR title+body)
Affected code: `.github/workflows/qa-validate.yml` (auto-merge merge step), `tests/test_workflows.py`
Not covered: the `main` vs `master` naming slip in issue #787's own text (`master` is this repo's base branch — no rename here); the arm64 `openspec` image tag defect (its own issue #767).

## Open Questions

- None.
