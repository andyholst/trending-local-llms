# tll-fleet-handover Specification

## Purpose
TBD - created by archiving change fleet-handover-live-pr-preflight. Update Purpose after archive.

## Requirements

### Requirement: A fleet PR handover calls the live body preflight

Before a lane posts the `pr #<id> · PR #<n> · base <sha> · handover tll-reviewer`
or the `reviewing #<id> · PR #<n>` comment, it SHALL run
`make pr-message-check PR=<n>` against that PR's live body. A non-zero verdict
SHALL forbid the handover comment: the lane SHALL repair the body and re-run
until the verdict is zero. The instruction SHALL appear in every fleet lane's
`SOUL.md` PR-and-review-handover section and in the reviewer skill mirror.

#### Scenario: Every lane SOUL names the live preflight

- **Given** the eight `agents/tll-*/SOUL.md` files in the tree
- **When** the fleet-lifecycle guard reads each PR-and-review-handover section
- **Then** every file carries `make pr-message-check PR=<n>` and no lane is
  silent about the seam
- **Test:** tests/test_fleet_lifecycle.py::test_every_lane_carries_the_live_pr_preflight

#### Scenario: A non-zero verdict forbids the handover

- **Given** the handover instructions in the lane SOULs
- **When** the guard reads the refusal clause
- **Then** each SOUL states that a non-zero verdict means the handover comment
  is NOT posted until the body is repaired and the check re-run
- **Test:** tests/test_fleet_lifecycle.py::test_the_preflight_refuses_a_nonzero_verdict

#### Scenario: The reviewer skill mirrors the preflight

- **Given** `agents/tll-reviewer/skills/tll-reviewer/SKILL.md`
- **When** the guard reads its checks-and-filing section
- **Then** it carries the same `make pr-message-check PR=<n>` preflight and the
  same non-zero refusal, so a reviewer cannot skip it by reading only the skill
- **Test:** tests/test_fleet_lifecycle.py::test_reviewer_skill_carries_the_live_pr_preflight
