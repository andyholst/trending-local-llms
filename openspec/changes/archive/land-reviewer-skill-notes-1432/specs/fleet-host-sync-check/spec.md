## ADDED Requirements

### Requirement: The tll-reviewer host-ahead pitfall notes are landed, reconciled, in the repo mirror

The `tll-reviewer` lane skill mirror SHALL carry the two host-ahead pitfall rules merged into its own
list — the OpenSpec-lifecycle note (with its #866 reference and offline reproduction command) and the
extension of the hand-rolled-test-hygiene note about a `test_*` listed twice in `main()`. Neither rule
SHALL appear under a `## Host notes ahead of master` header, and no host timestamp header, host
timestamp or machine-specific name SHALL remain in the landed text. No `config.yaml` or `SOUL.md` is
part of this change.

#### Scenario: The reviewer mirror carries both reconciled notes with their references

- **Given** the `agents/tll-reviewer/skills/tll-reviewer/SKILL.md` mirror
- **When** the guard reads the skill text
- **Then** both landed rules appear with their references, and the host timestamp header, the host
  timestamp and the machine name appear nowhere in the file
- **Test:** tests/test_fleet_lifecycle.py::test_reviewer_skill_carries_landed_host_ahead_notes

#### Scenario: A home synced from the reviewer mirror passes the real seam

- **Given** a scratch profile home copied from this tree's lane mirrors
- **When** the real `scripts/fleet_host_sync_check.py` seam runs against that tree
- **Then** it exits 0 — the landed reviewer mirror is the bytes a re-synced host carries
- **Test:** tests/test_fleet_lifecycle.py::test_real_seam_accepts_a_synced_home
