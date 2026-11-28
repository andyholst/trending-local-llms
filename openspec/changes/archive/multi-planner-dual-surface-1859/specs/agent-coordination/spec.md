# agent-coordination

## ADDED Requirements

### Requirement: the canonical collaboration doc defines unbounded planner machines and dual-surface handovers

`docs/fleet-collaboration.md` MUST carry a section titled "Unbounded planner machines and dual-surface handovers" stating that the owner may start unlimited tll-planner machines each with its own tll agent lanes; that comment threads are the ONE shared surface and the single source of truth; that every claim, status, verdict, handover and done line is posted on BOTH the issue's own thread AND the relevant PR comment thread; that each bot stamps itself `user@hostname`; that a bot reads the newest comments for a live claim on ANY machine before acting, using the twice-claim guard and the `make dispatch-check` lease to serialize shared files and PR heads; and that there is no cron, scheduler or second dispatcher. Sections 1, 2, 4 and 5 MUST cross-reference the new section and MUST NOT contradict it.

#### Scenario: a second planner host joins the fleet

- **Given** an owner starts another tll-planner machine with its own tll agent lanes
- **When** that planner reads the collaboration doc before dispatching work
- **Then** it finds that an unlimited number of planner machines is supported, that no second dispatcher exists, and that the newest signed comments on both threads are the only live state
- **Test:** tests/test_fleet_lifecycle.py::test_the_collaboration_doc_covers_unbounded_planners_and_dual_surface_handovers

#### Scenario: a handover lands on both surfaces

- **Given** a PR exists for a claimed issue
- **When** a lane posts a claim, status, verdict, handover or done line on the issue thread
- **Then** the same signed line with the same `user@hostname` stamp is mirrored on the PR comment thread, and the doc's `issue thread` AND `PR comment thread` wording is pinned by the guard test
- **Test:** tests/test_fleet_lifecycle.py::test_the_collaboration_doc_covers_unbounded_planners_and_dual_surface_handovers

#### Scenario: dropping the section reddens the guard

- **Given** the guard test names the section, both surfaces and unbounded planner machines
- **When** those names are removed from the canonical doc
- **Then** `test_the_collaboration_doc_covers_unbounded_planners_and_dual_surface_handovers` fails, so the protocol cannot be silently dropped
- **Test:** tests/test_fleet_lifecycle.py::test_the_collaboration_doc_covers_unbounded_planners_and_dual_surface_handovers
