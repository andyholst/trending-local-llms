# implementer-lane-concurrency

## ADDED Requirements

### Requirement: An implementer lane declares the concurrent-lane contract in both mirrors

The tracked `agents/tll-implementer/SOUL.md` and `agents/tll-implementer/skills/tll-implementer/SKILL.md` SHALL each carry one `## Concurrent-lane contract (issue #1767)` section. That section SHALL declare exactly these obligations: one issue, one worktree and one branch per lane; a signed working-claim on the issue's own thread before work; no shared branch or file edits between lanes; a ceiling of at most 3 live implementer lanes; a push checked with `--force-with-lease` against the last-read remote sha; never pushing `master` or merging a PR by hand; and every lane reading its own profile's `SOUL.md` and `SKILL.md` before claiming. Existing claim, worktree and handover rules SHALL remain in force.

#### Scenario: two implementer lanes are dispatched to distinct issues

- **Given** two lanes working different issues in different worktrees off the same fetched `origin/master`
- **When** `test_soul_declares_the_concurrent_lane_contract` and `test_skill_declares_the_concurrent_lane_contract` read the two tracked texts
- **Then** both texts carry the heading and every named obligation, and neither lane may edit the other's branch, worktree or files
- **Test:** `tests/test_parallel_implementer_lanes.py::test_soul_declares_the_concurrent_lane_contract`

#### Scenario: the guard fails on the pre-contract mirrors

- **Given** a mirror text with the added `#1767` contract section removed, reproducing the base text
- **When** `test_the_guard_is_red_on_the_pre_contract_text` runs the same checker over both head and base texts
- **Then** the head text passes, the base text fails, and the module exits 1 on the base and 0 on the head without crashing
- **Test:** `tests/test_parallel_implementer_lanes.py::test_the_guard_is_red_on_the_pre_contract_text`

#### Scenario: a heading-only edit is refused

- **Given** a text that declares the contract heading but none of the obligations
- **When** `test_a_heading_only_edit_cannot_satisfy_the_guard` runs
- **Then** the guard reports every missing obligation rather than passing on the title alone
- **Test:** `tests/test_parallel_implementer_lanes.py::test_a_heading_only_edit_cannot_satisfy_the_guard`
