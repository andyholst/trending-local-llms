# Proposal: planner-skill-ahead-1781

Issue: #1781
PR: #1786

## Why

`make fleet-host-sync-check BASE=origin/master` measured one divergence at base `c33a62b1`:
the host's `tll-planner` skill carries additive owner clauses (standing style, a `User style`
section, a `PR gate diagnosis` recipe, an OpenSpec-lifecycle subclass and gate section, and the
delivered #1775 bullet) that are not in the tracked mirror. The host copy also renamed the base's
`## Docs lane scope (owner-mandated)` heading and drifted `690/600s` to `660/600s`, so copying the
host file into master would delete base prose. Issue #1781 records the required derivative merge.

## What Changes

- `agents/tll-planner/skills/tll-planner/SKILL.md`: insert the five genuinely-new owner clauses
  verbatim-once, keeping every base line byte-identical — in particular the `## Docs lane scope`
  heading and the `690/600s` wording. Purely additive (0 deletions). The host's "never declare the
  board done while an issue is open…" sentence is deliberately NOT copied: that clause already
  exists verbatim in the base skill (the `Idling with an open board is wrong` bullet), and
  re-adding it reddens `test_mirror_unions_add_no_duplicate_or_interleaved_bullets`.
- `tests/test_fleet_lifecycle.py`: add `test_the_planner_mirror_carries_the_owner_style_and_pr_gate_notes`
  pinning every new clause once and both preserved base needles; register it in `main()`.

## Impact

Documentation-only. No data, contract, store, workflow, target, schedule or host-profile change in
the repository. The lane's byte comparison is unchanged; a host reconcile (with backup) is required
after the merge so the two sides match.

## Not covered

- No `AGENTS.md` rulebook edit (the planner skill mirrors an existing owner directive; no new rule).
- No `scripts/fleet_host_sync_check.py` change, no new make target or pipeline job.
- No rewrite of the other seven lane skills or their SOUL files.
