# Proposal: parallel-lane-rulebook

Issue: #1767 (parallel implementer lanes — rulebook §7b/§8 half; the implementer and planner SOUL/skill mirrors are the two sibling PRs)
PR: pending

## Why

The owner directed on 2026-11-26 that up to three `tll-implementer` lanes may work distinct issues in parallel, each in its own worktree/branch with a signed issue claim and a lease-checked push. At the freshly fetched base `37c6d88150fdb73fd0583a59099aee0b418d7927`, `AGENTS.md` §7b named only the planner's one-at-a-time `make dispatch-check` ceiling and §8 carried no guard row: the rulebook still described a serial implementer, so the shared half of the three-PR contract would never land.

## What Changes

- Additively extend `AGENTS.md` §7b with a bullet allowing up to 3 concurrent `tll-implementer` lanes on distinct open issues, each with its own worktree/branch from the fetched `origin/master`, a signed issue-thread claim before work, and lease-checked pushes; append the Rule 3c note clause for #1767.
- Add an `AGENTS.md` §8 guard row naming the three sibling test needles (`test_parallel_implementer_lanes`, `test_parallel_planner_dispatch`, `test_parallel_lane_rulebook`) so a later edit cannot drop any half silently.
- Add `tests/test_parallel_lane_rulebook.py::test_parallel_lane_rulebook` (wired into `main()`): a source-level guard RED on the base `AGENTS.md` (bullet and row absent) and GREEN on this head.
- Add `findings/1767.md` with Evidence/Why/Done when for both findings; regenerate the root `OPENSPEC.md` index.

## Impact

- Capability: `parallel-implementer-lanes` — the rulebook explicitly permits and pins up to three concurrent implementer lanes.
- Additive only to `AGENTS.md`; no existing rule text removed. No `agents/*` SOUL.md, skill mirror, Makefile, script, workflow, data file or host profile is touched — those belong to the two sibling PRs / are out of scope.
- Scoped: this change lands only the rulebook half of #1767; the issue stays open (`Refs #1767`) until all three PRs land. No closing keyword is used.
