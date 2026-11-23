## ADDED Requirements

### Requirement: The host-sync gate compares a lane config's owned blocks, not its runtime stamps

`scripts/fleet_host_sync_check.py` SHALL compare a lane `config.yaml`'s OWNED blocks —
`model`, `model_aliases`, `fallback_providers` — against the fetched base blob through the ONE
drift verdict (`agent_profile_provision.check_one`), instead of a byte compare that whitelists one
key. Any other top-level block a host carries — `_config_version`, `onboarding.seen`, or a stamp
the fix has never seen — SHALL be treated as host runtime state and tolerated. A stale owned byte
SHALL remain a divergence naming the lane's `config.yaml`. The exits are unchanged — 0 clean,
1 divergence (naming the lane and the file), 2 undecidable.

#### Scenario: A lane config carrying Hermes's runtime stamps is accepted

- **Given** a scratch profile home whose `tll-implementer/config.yaml` is the base blob plus
  `_config_version: 54`, `onboarding.seen.tool_progress_prompt: true`, or a novel
  `some_future_stamp:` block
- **When** the real seam runs with `--base HEAD --root <scratch repo> --profiles-home <home>`
- **Then** it exits 0 and prints the acceptance line naming the default profile's owned blocks
- **Test:** tests/test_fleet_lifecycle.py::test_real_seam_tolerates_hermes_runtime_stamps

#### Scenario: A stale owned byte is still refused

- **Given** the same scratch home with the lane `config.yaml`'s `model:`, `model_aliases:` or
  `fallback_providers:` block replaced by a stale scalar
- **When** the real seam runs
- **Then** it exits 1 and names `tll-implementer/config.yaml` and the drifted block
- **Test:** tests/test_fleet_lifecycle.py::test_real_seam_tolerates_hermes_runtime_stamps

#### Scenario: The tolerance does not extend to SOUL.md or the lane skill

- **Given** the same scratch home with `_config_version: 54` or an `onboarding:` block appended to
  `tll-implementer/SOUL.md`, or with one byte removed from the lane's `SKILL.md`
- **When** the real seam runs
- **Then** it exits 1 — `SOUL.md` and the lane skill stay byte-exact
- **Test:** tests/test_fleet_lifecycle.py::test_real_seam_tolerates_hermes_runtime_stamps
