## ADDED Requirements

### Requirement: Lane contracts make the heavy containerised gate CI-only

The `tll-implementer` and `tll-planner` lane skill mirrors SHALL teach push-and-verify: a lane makes
its change in the worktree, runs only the fast offline checks, PUSHES, and confirms CI registered on
the new SHA before reporting. Both mirrors SHALL name the full `make validate`, the whole
`make test` and `make live-smoke` as CI-ONLY, and the planner's dispatch wording SHALL NOT ask a
lane to prove the whole containerised suite green on the host before it pushes.

#### Scenario: The implementer mirror carries the delivery procedure and the fast-check list

- **Given** `agents/tll-implementer/skills/tll-implementer/SKILL.md`
- **When** the guard reads the delivery procedure
- **Then** it names the fast offline checks (`python3 scripts/pr_body.py --check-body-file <f>
  --branch <b>`, `make lint`, the targeted unit module), the push, and the CI-registered
  confirmation (`gh pr checks <n>`, `gh run view <id> --json jobs`), and it names the full
  `make validate`, the whole `make test` and `make live-smoke` as CI-ONLY
- **Test:** tests/test_fleet_lifecycle.py::test_lane_skills_carry_the_push_and_verify_rule

#### Scenario: The planner mirror's dispatch wording is push-and-verify, not a pre-push local gate

- **Given** `agents/tll-planner/skills/tll-planner/SKILL.md`
- **When** the guard reads the dispatch contract
- **Then** a dispatch's `done` is named as the push-and-verify sequence, and the skill carries no
  instruction to gate the whole containerised suite green on the host before pushing
- **Test:** tests/test_fleet_lifecycle.py::test_lane_skills_carry_the_push_and_verify_rule

#### Scenario: A home synced from these mirrors passes the real seam

- **Given** a scratch profile home copied from this tree's lane mirrors
- **When** the real `scripts/fleet_host_sync_check.py` seam runs against that tree
- **Then** it exits 0 — the landed mirrors are the bytes a re-synced host carries
- **Test:** tests/test_fleet_lifecycle.py::test_real_seam_accepts_a_synced_home
