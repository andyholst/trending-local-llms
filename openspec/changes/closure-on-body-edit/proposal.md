# Proposal: closure-on-body-edit

Issue: #290 — `tech-debt: A PR body edit never re-runs the closure check`

## Why

`make pr-closure`'s entire input is the PR **body** (rule 6e: a merged PR must close the issue
its branch implements, and GitHub binds a closing keyword to ONE reference). The body is the
one part of a PR that changes **without a new commit**: writing `closes #7` into the
description, or fixing `Closes #271 and #276` into two lines, is a body edit and nothing else.

`qa-validate.yml` triggers on `pull_request` with GitHub's **default** types (`opened`,
`synchronize`, `reopened`) — `edited` is not among them. So a body edit was never re-checked:
a PR kept the verdict its last commit had earned, and a body that *broke* its closure stayed
green until someone pushed an unrelated commit.

## What Changes

- **A new pipeline, `.github/workflows/pr-closure.yml`**, triggered on
  `pull_request: [opened, edited, synchronize, reopened]`:
  - **`guard`** first (rule 6j), admitting `pull_request` outright — a repository event has no
    caller to admit, the same clause `qa-validate`'s guard carries;
  - **`closure`** (`needs: guard`): checkout, then `make pr-closure`, which reads the webhook
    payload by path (`$GITHUB_EVENT_PATH`, the Makefile's own `PR_EVENT` default). An `edited`
    event carries the **new** body, so the verdict describes what is on screen now.
- **Read-only**: no push, no comment, no merge — asserted by the guard.
- **`qa-validate` keeps its own closure gate**: this ADDS a trigger, it does not move a check.
- **Its own pipeline rather than `edited` on `qa-validate`**: that would re-run the image
  builds, the unit suite and the 30-minute network-bound `live-smoke` — a real Firecrawl spend
  — because a sentence in a PR description changed.
- **`BOT_GUARDS`** gains the pipeline (rule 6j: a workflow cannot ship unguarded) and
  **`ARCHITECTURE.md`** describes its two jobs (rule 6h).

Verified RED by removing the workflow (the guard fails with `FileNotFoundError`, i.e. it is
reading a pipeline that must exist) and GREEN after (`PASSED 721 | FAILED 0`).

## Impact

`.github/workflows/pr-closure.yml` (new), `tests/test_workflows.py` (one test + `BOT_GUARDS`),
`ARCHITECTURE.md` (a section + the pipelines overview), this OpenSpec change and the
regenerated `OPENSPEC.md`. No make target, stage or image changes — the pipeline calls the
existing `make pr-closure`.

## Not covered

- **Re-running the FULL validation on a body edit.** A body is metadata; the code and data are
  unchanged, and validating them again would cost minutes and credits for nothing.
- **A body edited after the merge.** Nothing can; the check exists to make the body true before
  the merge closes its issue.
