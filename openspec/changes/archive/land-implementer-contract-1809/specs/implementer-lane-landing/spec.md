# implementer-lane-landing

## ADDED Requirements

### Requirement: The implementer-lane contract ships under the issue the PR actually closes

The implementer-lane delivery tracked by issue #1809 SHALL carry the approved concurrent-lane contract in both tracked mirrors (`agents/tll-implementer/SOUL.md` and `agents/tll-implementer/skills/tll-implementer/SKILL.md`) byte-for-byte from the #1767 artifact, and SHALL keep the guard `tests/test_parallel_implementer_lanes.py` that fails on the pre-contract mirrors. The PR that lands it SHALL bind #1809 alone, leaving the already-closed #1767 referenced only as inline code.

#### Scenario: both mirrors carry the approved contract on the landing tree

- **Given** the rebased tree whose SOUL and skill text came from the approved #1767 branch unchanged
- **When** `test_soul_declares_the_concurrent_lane_contract` and `test_skill_declares_the_concurrent_lane_contract` read the two tracked texts
- **Then** both texts carry the contract heading and every named obligation, with no edit to the approved wording
- **Test:** `tests/test_parallel_implementer_lanes.py::test_soul_declares_the_concurrent_lane_contract`

#### Scenario: the guard still proves the contract is load-bearing

- **Given** a mirror text with the contract section removed to reproduce the pre-contract base
- **When** `test_the_guard_is_red_on_the_pre_contract_text` runs the same checker over head and base text
- **Then** the head passes, the base fails and the module exits 1 on the base, so the landing cannot ship an inert heading
- **Test:** `tests/test_parallel_implementer_lanes.py::test_the_guard_is_red_on_the_pre_contract_text`
