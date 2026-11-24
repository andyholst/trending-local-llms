# Proposal: planner-parallel-dispatch-rule

Issue: #1644
PR: #1650

## Why

At fetched `origin/master` `a0f9adc5`, `make fleet-host-sync-check BASE=origin/master`
reported exactly ONE divergence on this host: `agents/tll-planner/skills/tll-planner/SKILL.md`.
The host copy carried the owner's PARALLEL dispatch rule while master still read
"Dispatch one lane at a time". PR #1624 (#1618) refused to land it as unauthorized, but the
owner has ruled repeatedly ("why are you not working on more issues in parallel?", "never
idle", "keep going") and granted full authority for improvements. A rule that lives only in a
host profile is also not durable: the next fleet re-provision rewrites that file from master
and silently drops it.

## What Changes

- `agents/tll-planner/skills/tll-planner/SKILL.md`: the "This lane" bullet becomes
  "Dispatch lanes in PARALLEL whenever their target files differ" and names the
  `make dispatch-check ISSUE=<n> MACHINE=<user@host> CLAIMS="p1 p2"` seam as the ONLY
  serialisation point (shared files: `agents/*/skills/*/SKILL.md`, `OPENSPEC.md`,
  generated artifacts).
- The same mirror's two concurrency pitfalls are reconciled into it: the ceiling stays a
  safety bound (not an idle reason), and the shared-file bullet becomes "Parallel by default —
  serialise ONLY the shared files".
- `tests/test_fleet_lifecycle.py`: a guard pins the new rule (presence of the parallel
  sentence, the `dispatch-check`/`CLAIMS=`/`#1458`/`#1569`/`#1423/#1424` references, the
  survival of the comment-before-work, claim-twice race guard, PR-is-not-the-handover and
  signed done rules, the ABSENCE of "Dispatch one lane at a time", and no host timestamp,
  machine name or absolute owner path inside the new block). The pre-existing #1469 pin
  follows the renamed bullet head.
- `findings/1644.md`: the run's analysis.

## Impact

Documentation mirror + tests only. No AGENTS.md §7b/§8 text, no other lane's SOUL or skill,
no schedule, no workflow, no data or contract change. The fleet gains continuous parallel
work with the shared-file collision still refused mechanically.

## Not covered

- No change to `scripts/dispatch_guard.py` (its stale-target, ceiling, `--claim` overlap and
  cross-host claim rules already implement the seam), no `AGENTS.md` edit, no SOUL.md edit.
