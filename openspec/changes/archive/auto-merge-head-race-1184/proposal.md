# Proposal: auto-merge-head-race-1184

Issue: #1184
PR: #1315

## Why

`qa-validate`'s `auto-merge` job reads the `pull_request` event head, waits for
`validate` + `live-smoke` to go green, then squashes that SHA with
`--match-head-commit`. If a host push (`git push --force-with-lease`, the rebase
and review flow of rules 6e/6s) moves the branch between the event and the
squash, GitHub refuses with `Head branch was modified. Review and try the merge
again.` The run reports the merge job as failed while the PR is left BLOCKED:
green checks belong to a head that no longer exists and the current head has
never been validated. No repairer owns this PR-side stall (the rule 6q keepers
repair pushes to `master`, not a blocked PR), so every such PR waits for a human.

## What Changes

- `scripts/auto_merge_head_check.py` (new, reached through
  `make auto-merge-head-check`) re-reads the PR's `headRefOid` immediately before
  the squash and compares it with the event head the checks were green on. Its
  pure `head_verdict` partitions `same` / `moved` / `unreadable`, case-insensitively;
  only a proved `same` reports `head_moved=false`. A moved OR unreadable head
  fails closed (`head_moved=true`), names both SHAs and refuses the squash.
- `qa-validate.yml` gains a dedicated `head-check` step (default `github.token`,
  read-only) between the rebase step and the squash; the squash step's `if:`
  additionally requires `steps.head-check.outputs.moved != 'true'`, so a moved
  head skips the merge cleanly and the fresh `pull_request` run the push fired
  re-validates and merges the new head instead of a false red.
- `tests/test_auto_merge_head_check.py` drives the real seam with a stub `gh`:
  same/moved/unreadable verdicts, both SHAs in the refusal, the field-contract
  request, exit 2 on a failed read, and the workflow/Makefile wiring. The guard
  is RED on `git show origin/master:` of the workflow and Makefile (8 failures).

## Impact

One new Makefile target + internal recipe, one new script, one new test module,
one new workflow step in the existing `auto-merge` job (no new pipeline, no new
cron, no new secret; reads use the default token). No data, contract or image
change. Part 2 of the issue — a 0-job `action_required` PR run reaching the alarm
family — is already landed by the #1115 fix (`ghost_verdict` in
`scripts/ghost_run_alarm.py`, commit `92beb4d8`, 2026-11-17, before this issue was
filed); it is deliberately not re-implemented here.

## Not covered

- Dispatching CI from the skip path: the head move already fires a fresh
  `pull_request` run, so no agent or job dispatches anything (owner directive,
  §6m).
- Changing the #1115 ghost alarm or the #1049 rebase seam beyond adding the
  `head-check` step between them.
- The AGENTS.md §8 regression-guard row is a rule-3c human sign-off and is owed
  on this headless leg (declared in `findings.md` as an owed row).
