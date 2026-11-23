## ADDED Requirements

### Requirement: The second batch of host-ahead skill notes is landed as a lossless union

The four lane skill mirrors SHALL carry the host-ahead pitfall notes merged into their existing
sections, and SHALL retain every rule that was present in the base revision. The union SHALL NOT
introduce a duplicate of a rule already present in the base. No host timestamp header, host
timestamp or machine name SHALL appear in the landed text.

#### Scenario: Forward notes and kept master rules coexist in each mirror

- **Given** the planner, reviewer, implementer and pr-rebase lane skill mirrors
- **When** the registration test reads each mirror
- **Then** every landed forward note is present, every named base rule is still present, and the
  OpenSpec lifecycle bullet appears exactly once in the implementer mirror
- **Test:** tests/test_fleet_lifecycle.py::test_second_batch_host_ahead_notes_are_landed

#### Scenario: A home synced from these mirrors passes the real seam

- **Given** a scratch profile home copied from this tree's lane mirrors
- **When** the real `scripts/fleet_host_sync_check.py` seam runs against that tree
- **Then** it exits 0 for the four reconciled lanes
- **Test:** tests/test_fleet_lifecycle.py::test_real_seam_accepts_a_synced_home
