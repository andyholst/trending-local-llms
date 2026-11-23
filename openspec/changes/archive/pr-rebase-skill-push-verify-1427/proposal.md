# Proposal: pr-rebase-skill-push-verify-1427

Issue: #1427
PR: #1429

## Why

Owner directive 2026-11-23 (#1423): no lane pre-runs the full containerised suite on the host — lanes
change locally, push, and `qa-validate` verifies. PR #1424 landed that rule in the `tll-implementer`
and `tll-planner` mirrors, but step 10 of
`agents/tll-pr-rebase/skills/tll-pr-rebase/SKILL.md` still told the rebase lane to run the whole gate
locally before pushing (`validate` + `live-smoke` + closure + guard). That is the exact 15–30 min /
one-VM-contention waste the directive removes, and it contradicts the sibling mirrors.

## What Changes

- `agents/tll-pr-rebase/skills/tll-pr-rebase/SKILL.md` step 10 becomes the push-and-verify order:
  rebase onto freshly fetched `origin/master`, run only the FAST offline checks (`make lint` and the
  targeted unit module), **PUSH**, then confirm CI registered on the new SHA (`gh pr checks <n>`,
  `gh run view <id> --json jobs`). The full `make validate`, the whole `make test`, closure and guard
  are named CI-ONLY. The "a rebase that ships a red head is not a rebase" intent is kept as: CI red at
  your head means the rebase is not done.
- `tests/test_fleet_lifecycle.py::test_pr_rebase_skill_is_push_and_verify` pins that step 10 carries
  the fast-check list, the push and the CI-registered confirmation, names the four heavy gates
  CI-ONLY, and carries no pre-push local-gate instruction.
- No `agents/*/SOUL.md` edit and no `AGENTS.md` §7b/§8 edit: `agents/tll-pr-rebase/SOUL.md:53` carries
  the same old wording but is a rule-3c protected instruction file, owed to the owner; §7b/§8 is rule
  3c too and needs its own issue with an architect design first.

## Impact

Mirror/docs plus one guard test. No make target, stage, workflow, contract, image or data change.

## Not covered

- `agents/tll-pr-rebase/SOUL.md:53` — rule-3c protected, owed to the owner.
- `AGENTS.md` §7b/§8 — rule 3c, needs its own issue and an architect design first.
