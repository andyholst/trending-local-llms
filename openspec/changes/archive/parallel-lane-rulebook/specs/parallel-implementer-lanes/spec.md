# parallel-implementer-lanes

## ADDED Requirements

### Requirement: The rulebook allows up to three concurrent implementer lanes

`AGENTS.md` §7b SHALL explicitly allow up to three `tll-implementer` lanes to be live at once, each on a DISTINCT open issue, each in its OWN worktree and OWN branch cut from the freshly fetched `origin/master`, each carrying a signed `BOT <lane> · working on #<id> …` claim posted on that issue's thread BEFORE work starts. Each lane push SHALL be lease-checked (`git push --force-with-lease`) so a lane cannot overwrite a sibling's head, and no lane SHALL share a worktree, branch or tracked-file write, push `master` or merge a PR. The planner's `make dispatch-check` ceiling and per-lane `--claim` path guard SHALL still bind; a fourth lane, a duplicate issue or an overlapping path SHALL be refused, never silently queued. This rule SHALL be additive to the existing §7b text.

#### Scenario: three implementer lanes work distinct issues at once

- **Given** the §7b text at the freshly fetched base names only a serial implementer and a one-at-a-time planner
- **When** `test_parallel_lane_rulebook` reads the §7b region of `AGENTS.md`
- **Then** the region carries the parallel-lane bullet naming up to 3 lanes, distinct issues, own worktree/branch, signed claim and lease-checked push, and the guard is RED on the base where that bullet is absent
- **Test:** tests/test_parallel_lane_rulebook.py::test_parallel_lane_rulebook

### Requirement: The §8 guard row names the guards from all three parallel PRs

`AGENTS.md` §8 SHALL carry one guard row that names all three sibling test needles — `test_parallel_implementer_lanes` (implementer SOUL/skill mirror), `test_parallel_planner_dispatch` (planner SOUL/skill mirror) and `test_parallel_lane_rulebook` (this rulebook module) — so no half of the parallel-lane contract can be dropped silently.

#### Scenario: a later edit drops one sibling guard needle

- **Given** the §8 row names only `test_parallel_lane_rulebook`
- **When** `test_rulebook_section_8_carries_the_three_guard_needles` reads the §8 region
- **Then** it fails on the missing `test_parallel_implementer_lanes` / `test_parallel_planner_dispatch` needle and passes only when all three are present
- **Test:** tests/test_parallel_lane_rulebook.py::test_rulebook_section_8_carries_the_three_guard_needles
