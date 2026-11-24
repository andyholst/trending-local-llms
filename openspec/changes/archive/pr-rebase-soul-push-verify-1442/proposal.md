# Proposal: pr-rebase-soul-push-verify-1442

Issue: #1442
PR: #1628

## Why

Issue #1427 landed the `SKILL.md` half of owner directive #1423 (lanes change locally, push, and
`qa-validate` verifies) but deliberately left `agents/tll-pr-rebase/SOUL.md` untouched because
`agents/*/SOUL.md` was a rule-3c protected instruction file. That left the lane contract
contradicting itself: the skill the lane reads second said push-and-verify, while the SOUL it reads
first still told it to run `validate` + `live-smoke` + closure + guard on the host before pushing —
the exact 15–30 min / one-VM-contention waste directive #1423 removes.

Owner authorization #1591 (plus the config setting landed by PR #1624) makes the protected write
landable now, so issue #1442 names this one line.

## What Changes

- `agents/tll-pr-rebase/SOUL.md:53` becomes the push-and-verify rule matching AGENTS.md §7b and
  `agents/tll-pr-rebase/skills/tll-pr-rebase/SKILL.md` step 10: change/rebase locally, run only
  the FAST offline checks (`make lint`, the targeted unit module), PUSH, then confirm CI registered
  on the new head (`gh pr checks <n>`, `gh run view <id> --json jobs`). The full `make validate`,
  the whole `make test`, closure and guard are named CI-ONLY, and the "a rebase that ships a red
  head is not a rebase" intent is kept as: CI red at your head means the rebase is not done.
- `tests/test_pr_rebase_soul_push_verify.py` pins that one bullet, so no later edit can regress it.

## Impact

One instruction-file line plus one guard module. No code path, data shape, contract, workflow,
schedule or merge behavior changes; the other seven lane SOULs and AGENTS.md §7b/§8 are untouched.

## Not covered

- Re-syncing the host profile mirror for `tll-pr-rebase` — an owner/host action
  (`make agent-profile-provision LANE=tll-pr-rebase`), outside this branch's write scope.
- Any other `agents/*/SOUL.md`, any AGENTS.md §7b/§8 edit, any schedule.
