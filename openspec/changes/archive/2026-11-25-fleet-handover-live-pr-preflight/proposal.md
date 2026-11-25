# Proposal: fleet-handover-live-pr-preflight

Issue: #1716
PR: #1720

## Why

`make pr-message-check PR=<n>` exists and is proved by
`tests/test_pr_message.py::test_the_live_pr_preflight_refuses_a_body_the_check_rejects`,
but no `tll-*/SOUL.md` or lane skill names it in its PR handover step (§7b still
asks lanes to run only the file-form check). A lane can therefore announce or
review a PR whose live body the seam would refuse; the merge-time hold catches
it later, but the authoring class #1710 exists to remove it. A mechanical seam
nothing calls is no more binding than the advisory instruction it replaced.

## What Changes

- Every fleet lane's `SOUL.md` "PR and review handover" section gains one
  bullet: run `make pr-message-check PR=<n>` on the PR before posting the
  `pr #<id>` / `reviewing #<id>` handover, and do NOT hand over on a non-zero
  verdict — repair the body and re-run until it is zero.
- `agents/tll-reviewer/skills/tll-reviewer/SKILL.md` carries the same preflight
  in its checks-and-filing list, so the reviewer's mirror cannot omit it.
- `tests/test_fleet_lifecycle.py` gains three guards: every lane SOUL carries
  the preflight, a non-zero verdict forbids the handover, and the reviewer
  skill mirrors it. Each is proven RED on the pre-change tree.
- The OpenSpec change is archived on the delivery branch and the index is
  regenerated (rule 6f).

## Impact

- `agents/tll-*/SOUL.md` (all eight lanes), `agents/tll-reviewer/skills/tll-reviewer/SKILL.md`.
- `tests/test_fleet_lifecycle.py` — three new tests registered in `main()`,
  plus one §8 guard row naming this module already exists (extended, not new).
- No new `make` target, no workflow change, no data or contract shape change.
- No `AGENTS.md` rulebook edit: the duty lives in the lane prompts, not the
  protected rulebook, so no rule-3c row is owed by this change.

## Not covered

- CI enforcement of the preflight: `make pr-message-check` already runs in
  `pr-closure.yml` from #1704; this change makes the lane actually call it.
- Any data, README, contract, or generated inventory change.
