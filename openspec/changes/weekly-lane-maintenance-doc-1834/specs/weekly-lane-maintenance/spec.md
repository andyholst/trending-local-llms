## ADDED Requirements

### Requirement: the maintenance pass is a planner-run cadence, never a timer

The weekly lane-maintenance pass SHALL be a checklist executed by the planner when the owner starts
it on the host (`hermes -p tll-planner chat`). The doc SHALL state explicitly that there is no
Hermes cron, no new GitHub Actions `schedule:`, no workflow added to run the fleet and no edit to
an existing schedule. The only scheduled pipeline in the tree SHALL remain the data gatherer.

#### Scenario: a reader looks for the trigger

- **Given** a person or a new bot on any host reads the maintenance doc
- **When** they look for what starts the pass
- **Then** they find an owner-started weekly cadence and an explicit no-cron / no-new-Actions-schedule statement
- **Test:** tests/test_weekly_lane_maintenance_doc.py::test_the_pass_is_a_cadence_not_a_timer

### Requirement: the pass runs the exact per-host sync check and files drift

Step 1 SHALL run `git fetch origin master` and `make fleet-host-sync-check BASE=origin/master` from
THIS host against the freshly fetched repo, comparing host lane `SOUL.md` / `skills/<lane>/SKILL.md`
and `AGENTS.md` to the in-tree `agents/tll-*` copies. Drift SHALL be reported and filed as a small
`enhancement` issue, fixed through `tll-implementer` and the in-tree mirror refresh (#696). The doc
SHALL forbid wiping Hermes runtime stamps or byte-copying host-ahead notes into `master` to force
the check green.

#### Scenario: the check is red on this host

- **Given** the host fleet carries legitimate host-ahead notes
- **When** the planner runs the pass and the check reports drift
- **Then** the drift is recorded on the issue and filed as a small enhancement, and no stamp is wiped to fake green
- **Test:** tests/test_weekly_lane_maintenance_doc.py::test_the_pass_names_the_exact_per_host_sync_command

#### Scenario: the filing path is named

- **Given** a reader of the doc finds a divergence
- **When** they look for how to fix it
- **Then** the doc names `tll-implementer`, the in-tree mirror refresh #696 and the prohibition on force-greening
- **Test:** tests/test_weekly_lane_maintenance_doc.py::test_the_pass_defines_the_drift_filing_path

### Requirement: the checklist covers all five steps and records the pass

The doc SHALL carry a runnable five-step checklist: per-host sync, roster verification (four
instances per delegable lane plus the single planner, `hermes -p <name> doctor`), collaboration-doc
verification, the board note naming in-progress lanes and PRs awaiting review, and a signed pass
record on issue #1834 with base sha, checks run, drift found, issues filed and next pass owner.

#### Scenario: the planner executes a pass

- **Given** the owner has started the planner on a host
- **When** the planner works down the checklist
- **Then** every one of the five steps has a box to tick and the last step produces an auditable signed comment
- **Test:** tests/test_weekly_lane_maintenance_doc.py::test_the_pass_covers_roster_collab_board_and_record

### Requirement: the canonical collaboration doc points at the checklist

Once `docs/fleet-collaboration.md` is on the fetched base, §6 of that document SHALL cross-link
`docs/weekly-lane-maintenance.md` so a reader of the collaboration model can find the runnable
pass. The guard is conditional on that file being present, since it arrives with companion PR
#1836 and the two doc issues serialize on the shared file.

#### Scenario: both doc PRs have landed

- **Given** the collaboration doc and the maintenance doc are both on `origin/master`
- **When** the guard reads them
- **Then** the collaboration doc links to the maintenance checklist
- **Test:** tests/test_weekly_lane_maintenance_doc.py::test_the_collaboration_doc_points_at_this_checklist
