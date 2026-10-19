# Proposal: pr-exercises-every-pipeline

Issue: #231 — `tech-debt: A workflow_dispatch-only pipeline can ship broken`

## Why

Seven of the eight workflows never run on a pull request: `refresh-bot`, `fix-bot`,
`issue-bot`, `issue-review-bot`, `code-review-bot`, `queued-alarm` and `publish-agent-image`
are `schedule` / `workflow_dispatch` only, and `qa-validate`'s `validate` job is the only
thing a PR exercises. So a change to one of those pipelines is verified by *nothing* until its
next real run — with secrets, side effects and a queue — and the repo has the scars to prove
it: `make issue-thread` before the checkout (#281), a draft PR that could never merge (#276),
an implementer verdict step that broke `$GITHUB_OUTPUT` after the work was done (#346).

The tests existed but the CLAIM was untracked: nothing said which test exercises which
pipeline, so a new workflow could be added with no coverage at all and no guard noticed.

## What Changes

- **`DISPATCH_ONLY_COVERAGE`** in `tests/test_workflows.py` — every workflow no PR runs, each
  naming the test module that exercises its logic inside `make test`.
- **`workflow_triggers()` / `coverage_problems()`** — the decision, as pure functions: a
  pipeline that no PR runs MUST be named in the map; a pipeline a PR DOES run must NOT be
  (a stale entry is refused); a named module must exist and be one `scripts/run_tests.sh`
  discovers (so "covered" means "executed by `make test`").
- **`test_every_pipeline_is_exercised_on_a_pr_or_names_its_coverage`** — asserts the map is
  true in both directions AND that the guard can fail: an unclassified dispatch-only workflow
  is refused, a stale entry is refused, an empty map fails.

On its first run the guard found **two real gaps the issue had not named** —
`publish-agent-image.yml` (dispatch only) and `refresh-bot.yml` (schedule + dispatch) — both
now named, with `tests/test_publish_agent_image.py` and `tests/test_refresh_run_block.py`.

## Impact

`tests/test_workflows.py` (two pure functions, one map, one test, 5 new checks: 689 passing),
this OpenSpec change and the regenerated `OPENSPEC.md`. **No workflow, target, stage, job or
image changes** — the pipelines themselves are untouched (`ARCHITECTURE.md` unchanged, rule
6h).

## Not covered

- **Running a bot pipeline end to end on a PR.** That needs its secrets and its side effects
  (pushes, comments, merges); the honest substitute is the coverage map plus the existing
  tests that execute each pipeline's real scripts against a stub `gh`.
- **A new workflow added without a guard.** That is `tests/test_workflows.py`'s `BOT_GUARDS`
  rule (rule 6j), which already fails for it; this change closes the other half — a pipeline
  with no PR and no named test.
