# qa-validate carries the trigger guard

**Issue:** [#279](https://github.com/andyholst/trending-local-llms/issues/279)
**Capability:** `bot-guards` (the owner/collaborator/`github-actions[bot]` guard every pipeline carries)

## Why

`qa-validate` is the ONE pipeline that had no trigger guard, and it is the
pipeline whose `workflow_dispatch` starts the most expensive run in the repo:

```
$ grep -c 'guard' .github/workflows/*.yml
.github/workflows/refresh-bot.yml       1   (job)
.github/workflows/fix-bot.yml           1   (first step of `fix`)
.github/workflows/issue-bot.yml         1   (job)
.github/workflows/issue-review-bot.yml  1   (job)
.github/workflows/publish-agent-image.yml 1 (job)
.github/workflows/queued-alarm.yml      1   (job)
.github/workflows/code-review-bot.yml   1   (job)
.github/workflows/qa-validate.yml       0   <-- none
```

Its `validate` job is `timeout-minutes: 30`, builds images, runs the whole
validation suite with every repo secret in scope, and its `auto-merge` job can
squash-merge. AGENTS.md §6j states the contract as "the same owner/collaborator
`guard`… checked BEFORE any secret"; `qa-validate` did not implement it, and
`tests/test_workflows.py` enumerated the guarded pipelines in `BOT_GUARDS` —
which simply did not list it, so nothing could notice.

`qa-validate` is also the only pipeline that runs on the repository's OWN
events (`pull_request`, `push`), which is why the guard cannot be a verbatim
copy: for those two events GitHub starts the run for the repository itself —
there is no caller to admit — and refusing them would leave every PR red for
ever, including contributions from outside the collaborator list.

## What Changes

- `qa-validate.yml` gains a `guard` job as its FIRST job: the standard owner /
  write+ collaborator / `github-actions[bot]` check for BOTH `github.actor` and
  `github.triggering_actor`, taken from the same shape as the other pipelines,
  plus the explicit `pull_request`/`push` bypass and the reason it exists.
- `validate` and `live-smoke` gain `needs: guard`, so a refused dispatch starts
  neither the 30-minute validation nor the network-bound smoke.
- `tests/test_workflows.py`:
  - `BOT_GUARDS` gains `("qa-validate.yml", "guard")`, so the EXISTING
    `test_guard_behaviour` (every caller class, the real guard script, a stub
    `gh`) now runs against it: owner / write+ collaborator / the bot allowed,
    read/triage collaborator, non-collaborator and a stranger's re-run refused.
  - `test_a_repo_event_run_is_admitted_by_its_guard` — a pipeline that declares
    `pull_request`/`push` must admit them whatever the actor (non-vacuous).
  - `test_a_guarded_pipeline_gates_the_jobs_that_read_secrets` — the guard is the
    first step of its job in EVERY guarded pipeline, the guard job needs nothing,
    and at least one job needs it.
- `AGENTS.md` §6j names `qa-validate` in the guard paragraph and states the
  repo-event rule; §8 gains the guard rows. §6b's pipeline list is unchanged.
- `ARCHITECTURE.md` — the `qa-validate` table gains its `guard` row (rule 6h).

## Not covered

- `auto-merge` and `dispatch-fixbot` are not gated directly: both are
  `pull_request`-only and depend on `validate`/`live-smoke`, which now need the
  guard, so a refused guard can no longer reach a merge.
- A guard for a future pipeline is not generated automatically: the contract is
  that a new workflow must be added to `BOT_GUARDS`, which the suite enforces for
  the pipelines it knows and a reviewer must apply to a new one.
