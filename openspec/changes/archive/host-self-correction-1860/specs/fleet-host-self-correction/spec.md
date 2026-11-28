## ADDED Requirements

### Requirement: The comparison set includes the host rulebook

`fleet_host_sync_check.py` SHALL define ONE comparison set: the per-lane `MIRROR_RELS` plus a single `RULEBOOK_REL = "AGENTS.md"` at the profile-home root, compared against the repo-root `AGENTS.md` at the resolved base. `fleet_host_reconcile.py` SHALL import those definitions instead of restating them (rule 6d). `config.yaml` SHALL NOT be part of the byte comparison set.

#### Scenario: A stale host rulebook converges to the fetched base

- **Given** a profile home whose `AGENTS.md` is missing a line present in the repo-root `AGENTS.md` at the base
- **When** the attended write path runs with `--write --attended-signoff`
- **Then** the host rulebook carries the base line, the stale lane mirror converges in the same run, and the pre-write rulebook is backed up
- **Test:** tests/test_fleet_host_reconcile.py::test_stale_host_rulebook_and_soul_converge_to_base

#### Scenario: A forward host rulebook note is preserved

- **Given** a host rulebook that carries its own extra note and deletes nothing from the base
- **When** the attended write path computes the union
- **Then** the host note survives verbatim and the union is classified FORWARD
- **Test:** tests/test_fleet_host_reconcile.py::test_forward_host_rulebook_note_is_preserved

#### Scenario: config.yaml is never reconciled

- **Given** a divergent `config.yaml` in a host lane directory
- **When** the attended write path lands the mirrors
- **Then** the config bytes are unchanged, no config backup is written, and no second config drift verdict is printed
- **Test:** tests/test_fleet_host_reconcile.py::test_config_yaml_is_untouched

### Requirement: Protected instruction writes fail closed

A write to a protected instruction file (`AGENTS.md`) SHALL require BOTH `WRITE=1` (`--write`) and an attended sign-off (`ATTESTED=1` / `--attended-signoff`). Without the sign-off the SHALL refuse the whole invocation before any backup or write — fail closed, not fail open for the other files (rule 3c).

#### Scenario: An unattended protected write changes nothing

- **Given** a pending set containing a stale host rulebook and a stale lane mirror
- **When** `--write` is invoked without `--attended-signoff`
- **Then** the command exits 2, names rule 3c, leaves every file byte-identical and writes no backup
- **Test:** tests/test_fleet_host_reconcile.py::test_protected_rulebook_write_fails_closed_without_signoff

### Requirement: CI verifies the seam offline and never writes a host

`qa-validate.yml` SHALL run the reconcile seam report-only against a repo tree, including the rulebook via `RULEBOOK=AGENTS.md`; the guard module SHALL be discovered by `make test`, which CI already runs. No workflow step SHALL pass `WRITE=1`. The Makefile SHALL plumb `ATTESTED=1` to `--attended-signoff` and `RULEBOOK=...` to `--rulebook`. No cron and no new Actions schedule SHALL be added.

#### Scenario: The offline CI path covers the rulebook read-only

- **Given** the checked-out repo tree with no live host profile home
- **When** `make fleet-host-reconcile BASE=HEAD PROFILES_HOME=agents RULEBOOK=AGENTS.md` runs
- **Then** the comparison includes the repo-root rulebook, the verdict is OK when the tree matches the base, and no file is written
- **Test:** tests/test_fleet_host_reconcile.py::test_make_and_ci_wire_the_signoff_and_rulebook

### Requirement: No Hermes runtime stamp is wiped

The seam SHALL NOT write `config.yaml`, rename or delete a profile home, or overwrite a Hermes runtime stamp. It SHALL NOT require hand-editing a host file to make `fleet-host-sync-check` green.

#### Scenario: Runtime-owned state survives a convergence

- **Given** host-owned `config.yaml` bytes that differ from the repo
- **When** the attended write path repairs a stale rulebook and SOUL
- **Then** the config bytes are unchanged and no second drift verdict for it is emitted
- **Test:** tests/test_fleet_host_reconcile.py::test_config_yaml_is_untouched
