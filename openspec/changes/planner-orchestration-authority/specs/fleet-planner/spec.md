## ADDED Requirements

### Requirement: The planner skill records the owner's orchestration/delegation authority

`agents/tll-planner/skills/tll-planner/SKILL.md` SHALL carry a Procedure section recording the owner's
2026-11-23 directive that this lane has full authority to orchestrate and delegate — it STARTS the other
lanes itself. The section SHALL name the mechanism
(`env -u HERMES_HOME -u HERMES_SESSION_PROFILE hermes -p <lane> chat --query-file <file> --oneshot`,
launched with `terminal(background=true)` and monitored with `process_manage`) and SHALL keep the
guardrails explicit: delegation is still by a signed dispatch comment on the issue thread, the planner
still never writes the tree and never merges, and there is still no cron and no Actions schedule.

#### Scenario: The directive and its mechanism are written down

- **Given** the shipped planner skill at `agents/tll-planner/skills/tll-planner/SKILL.md`
- **When** a reader opens the Procedure section
- **Then** the text names the owner directive 2026-11-23 and the `hermes -p <lane> chat --query-file
  <file> --oneshot` mechanism with `terminal(background=true)` and `process_manage`
- **Test:** tests/test_planner_orchestration_authority.py::test_the_planner_skill_records_the_orchestration_authority

#### Scenario: The guardrails survive beside the authority

- **Given** the same skill file
- **When** a reader opens that section
- **Then** it states the signed dispatch comment on the issue thread, that the planner never writes the
  tree and never merges, and that there is no cron and no Actions schedule
- **Test:** tests/test_planner_orchestration_authority.py::test_the_guardrails_survive_beside_the_authority

#### Scenario: The pitfalls a lane hits are named

- **Given** the same skill file
- **When** a reader opens that section
- **Then** it names `--yolo --accept-hooks` (and the `approvals.single_query_mode: deny` it clears), the
  `git status` check of the owner's checkout after a lane run, and the 30–70 min lane duration
- **Test:** tests/test_planner_orchestration_authority.py::test_the_pitfalls_are_recorded

### Requirement: The guard reads the real skill file

`tests/test_planner_orchestration_authority.py` SHALL read the REAL
`agents/tll-planner/skills/tll-planner/SKILL.md` and assert the needles — never a fixture, a copy or a
mock (rule 6m) — so a later edit that drops the directive, a guardrail or a pitfall reds the module. The
module SHALL be discovered by the ONE runner (`scripts/run_tests.sh`), so `make test` executes it.

#### Scenario: The guard is wired into the ONE runner

- **Given** the module on disk at `tests/test_planner_orchestration_authority.py`
- **When** `scripts/run_tests.sh --list` runs
- **Then** the module is listed and the module's own `main()` calls every `test_*` it defines
- **Test:** tests/test_planner_orchestration_authority.py::test_the_guard_is_discovered_by_the_one_runner
