# fleet-collaboration

## ADDED Requirements

### Requirement: one canonical document explains how the fleet works together

The repository MUST carry one reader-facing document that explains the fleet end to end: who
starts it, where its state lives, what each lane owns, and how a work item moves from a claim to
a reviewed PR. It MUST name all eight lanes, the issue-thread board and the exact signed
claim, dispatch, PR-delivery, review and done comment formats. `agents/README.md` MUST point at
that document as canonical instead of restating the protocol.

#### Scenario: a new bot on another host can learn the protocol from one file

- **Given** a reader who has never seen a lane's SOUL.md or the planner skill
- **When** they open `docs/fleet-collaboration.md`
- **Then** they find the owner start (`hermes -p tll-planner chat`), the machine-id signature,
  all eight lanes with their remits, and the `working on` / `dispatch` / `pr` / `reviewing` /
  `done` signed formats
- **Test:** tests/test_fleet_lifecycle.py::test_the_canonical_collaboration_doc_covers_every_lane_and_the_board_protocol

#### Scenario: the short roster table is a pointer

- **Given** `agents/README.md`'s one-line-per-lane table
- **When** a reader follows its collaboration link
- **Then** they reach `docs/fleet-collaboration.md`, which the table calls canonical
- **Test:** tests/test_fleet_lifecycle.py::test_agents_readme_points_at_the_canonical_collaboration_doc

### Requirement: four instances share one protocol and the cadence is not a timer

The document MUST state that the fleet scales to four instances of each delegable lane with the
planner single, that `make dispatch-check` enforces the active-lane ceiling and the claim-twice
race guard serializes shared files, and that the weekly maintenance pass is work the planner
performs when started — never a Hermes cron and never a new Actions `schedule:`.

#### Scenario: same-role instances behave identically

- **Given** four instances of a delegable lane on one or several hosts
- **When** they read the canonical doc
- **Then** they find the same remit, the same signed formats, the three-lane ceiling and the
  180-second settle-before-claim guard, so none can claim an issue another holds
- **Test:** tests/test_fleet_lifecycle.py::test_the_canonical_collaboration_doc_covers_every_lane_and_the_board_protocol

#### Scenario: cadence is a checklist, not a scheduler

- **Given** the companion weekly-pass issue #1834
- **When** the doc describes the pass
- **Then** it names the per-host host-sync step and says explicitly the pass is cadence work the
  planner runs, not a cron and not a timer
- **Test:** tests/test_fleet_lifecycle.py::test_the_collaboration_doc_keeps_cadence_distinct_from_a_timer
