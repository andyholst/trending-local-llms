# fleet-host-sync-check Specification

## Purpose
TBD - created by archiving change fleet-host-sync-config-version. Update Purpose after archive.

## Requirements

### Requirement: The host-sync gate tolerates Hermes's own `_config_version` runtime stamp

`scripts/fleet_host_sync_check.py` SHALL ignore exactly one host-owned scalar — a line matching
`_config_version: <value>` — on the host copy of a lane `config.yaml` before comparing it with
`git show <base>:agents/<lane>/config.yaml`. It SHALL NOT ignore that key on `SOUL.md` or on the
lane skill, and SHALL NOT ignore any other key: a stale `model:` / `model_aliases:` /
`fallback_providers:` byte remains a divergence. The exits are unchanged — 0 clean, 1 divergence
(naming the lane and the file), 2 undecidable.

#### Scenario: A lane config carrying Hermes's runtime stamp is accepted

- **Given** a scratch profile home whose `tll-implementer/config.yaml` is the base blob plus one
  appended line `_config_version: 54`
- **When** the real seam runs with `--base HEAD --root <scratch repo> --profiles-home <home>`
- **Then** it exits 0 and prints the acceptance line naming the default profile's owned blocks
- **Test:** tests/test_fleet_lifecycle.py::test_real_seam_tolerates_hermes_config_version

#### Scenario: A stale model byte is still refused

- **Given** the same scratch home with the lane `config.yaml`'s top-level `model:` key replaced by
  a stale scalar
- **When** the real seam runs
- **Then** it exits 1 and names `tll-implementer/config.yaml` with `diverges from`
- **Test:** tests/test_fleet_lifecycle.py::test_real_seam_tolerates_hermes_config_version

#### Scenario: The tolerance does not extend to SOUL.md

- **Given** the same scratch home with `_config_version: 54` appended to
  `tll-implementer/SOUL.md`
- **When** the real seam runs
- **Then** it exits 1 — `SOUL.md` stays byte-exact
- **Test:** tests/test_fleet_lifecycle.py::test_real_seam_tolerates_hermes_config_version
