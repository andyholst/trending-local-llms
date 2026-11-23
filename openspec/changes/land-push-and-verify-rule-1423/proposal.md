# Proposal: land-push-and-verify-rule-1423

Issue: #1423

## Why

Owner directive 2026-11-23: lanes make their changes locally and PUSH; the CI jobs do the verifying.
No lane should pre-run the full containerised suite on the host. Measured on asimov@mac: a lane's
local `make validate` + `make test` costs 15–30 min inside the per-purpose Linux container, and four
lanes doing it at once drove load average to 5.80 with `Virtualization.framework` at 207% CPU while
each lane process sat at ~0% CPU in `sleep` polls (8–19 s of CPU over 1h41m–2h40m runtimes). The same
gates already run in GitHub Actions on `qa-validate`, which costs this host nothing. The rule lived
only as a host-side note in the planner profile, so a rebuilt host or another machine lost it silently.

## What Changes

- `agents/tll-implementer/skills/tll-implementer/SKILL.md`: a new
  `## Delivery procedure — push, then CI verifies` section makes the delivery sequence explicit —
  make the change in the worktree, run ONLY the fast offline checks
  (`python3 scripts/pr_body.py --check-body-file <f> --branch <b>`, `make lint`, the targeted unit
  module), PUSH, confirm CI registered on the new SHA (`gh pr checks <n>`, `gh run view <id>
  --json jobs`), report — and names the full `make validate`, the whole `make test` and
  `make live-smoke` as CI-ONLY. The `## Procedure` list points at that section.
- `agents/tll-planner/skills/tll-planner/SKILL.md`: the dispatch contract names push-and-verify as
  what `done` means and states that a dispatch never asks a lane to prove the whole containerised
  suite green on the host before it pushes.
- `tests/test_fleet_lifecycle.py::test_lane_skills_carry_the_push_and_verify_rule` pins the needles
  in both mirrors, so neither skill can drop the rule quietly.
- No `AGENTS.md` §7b/§8 edit and no `agents/*/SOUL.md` edit: §7b/§8 is rule 3c and is filed
  separately with an architect design first.

## Impact

Mirror/docs only. No make target, stage, workflow, contract, image or data change. Once the host
profiles are re-synced from the merged tree, `make fleet-host-sync-check BASE=origin/master` reports
0 divergences on the two lanes.

## Not covered

- The same sentence in `AGENTS.md` §7b/§8 — rule 3c, needs its own issue and an architect design first.
- Re-syncing the host profile homes — the owner/planner runs it after this merges.
