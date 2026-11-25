# Proposal: auto-merge-message-pattern-hold

Issue: #1704

## Why

Rule 6f says the squash commit message "follows by construction — its title comes from
`pr_body.title()` and its body is the **validated** PR body", but nothing makes that validation
binding. `pr-closure.yml`'s `closure` job runs `make pr-message-check`, and `closure` is **not**
one of master's required status checks (rule 1 names only `validate` + `live-smoke`). So
`qa-validate`'s `auto-merge` squashed whatever body the PR carried, and a non-conforming body
landed verbatim as a `master` commit — after which the push-to-master `closure` job refused it,
reddening the base with no repairer (rule 6q).

Measured: run [45539207073](https://github.com/andyholst/trending-local-llms/actions/runs/45539207073),
job `closure`, push head `8184e59d`:

```text
[commit-message-check] REFUSED: (no branch) — missing required section(s):
  ## Why, ## What, ## How, ## Benefits, ## Technical Solution
```

That head is PR #1696's squash; its message is the PR body verbatim (`## What changed` /
`## Evidence`). Reproduced offline against that body:

```text
$ python3 scripts/pr_body.py --check-body-file body.md --branch fix/owed-row-prose-quotes-1690
[pr-message-check] REFUSED: fix/owed-row-prose-quotes-1690 — 1 problem(s):
  - missing required section(s): ## Why, ## What, ## How, ## Benefits, ## Technical Solution
exit 1
```

## What Changes

- `qa-validate.yml`'s `auto-merge` job gains a **message-pattern hold** step, mirroring the
  existing `do-not-merge` label hold (#722): it runs `make pr-message-check PR_EVENT=$GITHUB_EVENT_PATH`
  against THIS run's own event payload and publishes `hold=true|false`. A refusal HOLDS — the
  rebase, head-check, squash and post-squash closure proof steps are all skipped via their `if:` —
  leaving the PR OPEN and the run **green**, so an author can fix the body instead of a red run
  hiding the reason.
- `tests/test_workflows.py` gains a guard for the hold: the step exists and runs before the squash,
  it reaches the product through `make` (rule 6m), it reads `github.event_path`, the merge step's
  `if:` carries `steps.message-check.outputs.hold != 'true'`, and the REAL step shell is executed
  against a stub `make` for both verdicts (refusal → `hold=true`, clean → `hold=false`), each exit 0.

## Impact

- `.github/workflows/qa-validate.yml` — one step plus four `if:` clauses in `auto-merge`. The
  squash command itself is byte-identical (same owner PAT, same `--match-head-commit`,
  `--subject`/`--body-file`).
- `tests/test_workflows.py` — extended in place (the repo's single workflow-wiring module).
- `AGENTS.md` §8 — the EXISTING row for `tests/test_workflows.py` must name the new guard.
  Protected agent-instruction file: a headless leg records it as an OWED ROW (rule 3c),
  declared in `findings/1704.md`.
- No make target is added or renamed, so `master_alarm.GATES` is unchanged (the registry covers
  the `validate` job; `unchecked_gates` slices that job only).

## Not covered

- Making `closure` a required status check on master: that is an owner repository-settings act
  (rule 1) and is deliberately not attempted. The hold removes the defect the missing requirement
  exposed.
- Widening `commit-message-check` to accept a non-conforming message: the refusal is correct; the
  merge path was what was missing.
- Composing a different squash message: once the hold binds, the authored body IS the validated
  body, so composition needs no change.
- The lane-side half (a push must run the fast offline
  `python3 scripts/pr_body.py --check-body-file <f> --branch <b>` first): already required by §7b;
  #1696's leg pushed a body that check refuses, which is a lane-behaviour finding, not this change.
