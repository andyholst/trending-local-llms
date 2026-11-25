## ADDED Requirements

### Requirement: The planner mirror dispatches lanes in parallel and serialises only shared files

The planner `SKILL.md` mirror SHALL tell the lane to dispatch lanes in PARALLEL whenever their
target files differ, naming worktrees and push-and-verify as the reason the serial cap is gone.
It SHALL name `make dispatch-check ISSUE=<n> MACHINE=<user@host> CLAIMS="p1 p2"` as the ONLY
serialisation seam — a path overlap with an ACTIVE lane (#1458) or a newer ACTIVE working-claim
held by another host (#1569) — and SHALL keep the comment-before-work rule, the claim-twice race
guard, the issue-thread handover and the signed done marker. It SHALL NOT carry the obsolete
"Dispatch one lane at a time" sentence, nor a host timestamp, machine name or absolute owner
path inside the new rule.

#### Scenario: The serial cap is gone from the mirror

- **Given** the tree's `agents/tll-planner/skills/tll-planner/SKILL.md`
- **When** the guard reads the mirror
- **Then** it carries the parallel-dispatch sentence and the `dispatch-check`/`CLAIMS=` seam,
  and the string "Dispatch one lane at a time" is absent
- **Test:** tests/test_fleet_lifecycle.py::test_the_planner_mirror_carries_the_owners_parallel_dispatch_rule

#### Scenario: The protocol rules the owner kept are still present

- **Given** the same mirror after the parallel rule lands
- **When** the guard reads it
- **Then** it still carries the comment-before-work sentence, the claim-twice race guard,
  the PR-is-not-the-handover rule and the signed `done #<id> · handover` marker
- **Test:** tests/test_fleet_lifecycle.py::test_the_planner_mirror_carries_the_owners_parallel_dispatch_rule

#### Scenario: The reconciled block names no host state

- **Given** the new parallel rule block in the mirror
- **When** the guard scans that block for `/home/asimov/`, `asimov@`, a `20:`-prefixed stamp or
  `## Host notes ahead of master`
- **Then** none of them appears
- **Test:** tests/test_fleet_lifecycle.py::test_the_planner_mirror_carries_the_owners_parallel_dispatch_rule
