# profile-provision-backups Specification

## Purpose
TBD - created by archiving change profile-provision-backup-skills-1754. Update Purpose after archive.

## Requirements

### Requirement: Every overwritten lane-home prompt file keeps a timestamped backup

Before `provision_one` copies a lane's `SOUL.md` or any file under `skills/**` into the host
profile home, it SHALL write a byte-identical `*.bak-<UTC>` copy of the destination beside that
destination, and SHALL print one `[profile-provision] backup <dest> -> <backup>` line naming both
paths. The config backup path and the final summary line are unchanged. If the timestamped backup
already exists, the seam SHALL use `-2`, `-3`, … suffixes so an earlier backup is never replaced.

#### Scenario: A host-ahead skill survives an M-sync re-provision

- **Given** a scratch repo lane with `skills/<lane>/SKILL.md`, a home provisioned once from it, a
  host edit adding a forward clause to the home copy, and a newer base blob in the repo
- **When** the real seam provisions that lane again
- **Then** the home skill holds the newer base bytes, a `SKILL.md.bak-<UTC>` file holds the host's
  forward clause byte-for-byte, and the seam's output names that backup path

- **Test:** tests/test_agent_profile_provision.py::test_skills_and_soul_are_backed_up_before_a_reprovision_overwrites_them

#### Scenario: SOUL.md is backed up by the same rule

- **Given** a provisioned lane whose host `SOUL.md` carries a forward clause and whose repo `SOUL.md` changed
- **When** the lane is re-provisioned
- **Then** the host clause is preserved in `SOUL.md.bak-<UTC>` and the output names it

- **Test:** tests/test_agent_profile_provision.py::test_skills_and_soul_are_backed_up_before_a_reprovision_overwrites_them

#### Scenario: A nested skill reference is backed up and a fresh home writes none

- **Given** a repo lane with `skills/<lane>/references/deep.md` and one home already provisioned, plus a second home with no prior skill file
- **When** both lanes are provisioned after a host edit to the nested file
- **Then** the nested file's backup holds the host bytes and is named in the output, while the fresh home gets no `*.bak-*` under `skills/`

- **Test:** tests/test_agent_profile_provision.py::test_a_nested_skill_backup_is_named_and_a_fresh_home_writes_no_backup

#### Scenario: A repeated re-provision never overwrites the first backup

- **Given** a home whose forward clause is already in `SKILL.md.bak-<UTC>` from an earlier provision
- **When** the same lane is provisioned twice more in quick succession
- **Then** the first backup still holds the forward clause byte-for-byte and a second, uniquely suffixed backup exists

- **Test:** tests/test_agent_profile_provision.py::test_a_repeated_reprovision_never_overwrites_the_first_backup
