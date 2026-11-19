# fleet-profile-provision

## ADDED Requirements

### Requirement: A rendered fleet lane config reaches the Hermes profile home that runs it

The fleet's model chain is only real where a lane RUNS. `make agent-profile-provision` MUST copy
each lane's rendered config (`agents/tll-<lane>/config.yaml`, rendered by
`agent_model_chain.render_text` from `agents/model_chain.json`) into that lane's Hermes profile home
(`<profiles-home>/tll-<lane>/config.yaml`, default `~/.hermes/profiles`), byte-for-byte, so the
profile a lane starts from is the config the gate can read. A lane config that exists only in the
repository while the live home carries a hand-written one is the state this requirement refuses.

#### Scenario: a named lane's config lands in its profile home and replaces the hand-written shape

- **Given** a scratch tree whose lanes were rendered from the chain, and a profile home whose
  `tll-tester/config.yaml` is the measured hand-materialised shape (`provider: strata` /
  `qwen3.8-flash-next-q2_0` / a local `base_url`)
- **When** the seam runs with that lane named and the chain's credential present
- **Then** it exits 0, the profile home's config equals what the chain renders byte-for-byte, the
  strata/local spelling is gone, the seam names the lane, the destination and the backup, and no
  sibling lane home is touched
- **Test:** tests/test_agent_profile_provision.py::test_a_lane_config_copies_into_the_profile_home_and_the_prior_file_is_kept

#### Scenario: every fleet lane in the tree is provisioned by --all, derived from the tree

- **Given** a scratch tree carrying two fleet lanes under `agents/`
- **When** the seam runs with `--all`
- **Then** every lane the tree derives (`agent_model_chain.fleet_lanes`) is written and equals its
  rendered config, and the summary counts the lanes it read from the tree rather than a hand-kept
  list
- **Test:** tests/test_agent_profile_provision.py::test_all_provisions_every_fleet_lane_in_the_tree

### Requirement: Provisioning keeps the profile it replaced (rule 3b)

A profile home is an operator's state, not the agent's to overwrite. When a lane's
`config.yaml` already exists, the seam MUST copy it to `config.yaml.bak-<UTC>` in the same lane home
before writing the new file, and MUST never delete or rewrite a backup. Restoring a prior profile is
a human act.

#### Scenario: the prior config survives as a timestamped backup

- **Given** a lane home that already carries a `config.yaml`
- **When** the seam provisions that lane
- **Then** exactly one `config.yaml.bak-<UTC>` file exists in that home holding the OLD bytes, the
  new `config.yaml` holds the rendered bytes, and the seam prints the backup path
- **Test:** tests/test_agent_profile_provision.py::test_a_lane_config_copies_into_the_profile_home_and_the_prior_file_is_kept

### Requirement: A lane is never provisioned keyless, and a credential stays a NAME (rule 3e)

Before anything is written, the seam MUST check — through `scripts/require_env.py`, the ONE
credential pre-flight (issue #357) — that every `key_env` NAME the chain carries is SET in the
environment. If one is absent it MUST refuse with exit 2, name the VARIABLE, state that no value was
read, and write NOTHING into the profile home. The seam MUST never read, print or measure a
credential VALUE, and every config it writes MUST carry `key_env` NAMES only.

#### Scenario: the absent credential is a loud refusal that writes nothing

- **Given** a scratch tree whose chain names `NOUS_API_KEY` and a process environment that does not
  carry it
- **When** the seam runs with `--all`
- **Then** it exits 2, names `NOUS_API_KEY`, says no value was read, and the profile home is left
  completely empty
- **Test:** tests/test_agent_profile_provision.py::test_provisioning_refuses_without_the_credential_the_chain_names_and_writes_nothing

#### Scenario: what lands in a profile home names credentials and never carries one

- **Given** a successful `--all` provisioning with the credential supplied only as a named
  environment variable
- **Then** every provisioned config carries `key_env: NOUS_API_KEY`, no provisioned config assigns a
  credential field (`api_key` / `token` / `password` / `authorization`), the value never appears in
  any written file or in the seam's output, and the summary prints the NAMES it required
- **Test:** tests/test_agent_profile_provision.py::test_the_provisioned_config_carries_key_env_NAMES_and_never_a_credential_value

### Requirement: A config the chain gate would refuse is never provisioned

`make agent-model-chain-check` refuses a lane config that drifted from the chain. The provisioning
seam MUST apply the same comparison (`agent_model_chain.config_problems`, plus a byte check of the
file it is about to copy) and MUST refuse — exit 2, naming the lane, writing nothing — rather than
carry that drift into a live profile home, where no gate would ever see it again.

#### Scenario: a hand-edited lane config is refused, not copied

- **Given** a scratch tree whose `tll-tester/config.yaml` has been hand-edited away from what the
  chain renders
- **When** the seam runs with `--all`
- **Then** it exits 2, names `tll-tester`, and the profile home is left empty — nothing drifted was
  installed
- **Test:** tests/test_agent_profile_provision.py::test_a_lane_config_that_drifted_from_the_chain_is_refused_not_copied

### Requirement: Writing a profile home is an explicit act, wired into the pipeline

The seam MUST refuse when nothing is named (no lane, no `--all`) — installing into a live profile
home is never a default — and MUST refuse an unknown lane by naming it and the real fleet.
`--dry-run` MUST prove the chain, the credential and every lane config while writing nothing. The
seam MUST be reachable only through `make agent-profile-provision` (`LANE=` / `ALL=` /
`PROFILES_HOME=`) and MUST be executed by a pipeline job (rule 6m), against a runner temp home so a
CI run never writes a real profile home.

#### Scenario: no lane named is a refusal, an unknown lane is a refusal, --dry-run writes nothing

- **Given** a scratch tree and an empty profile home
- **When** the seam runs with no `--lane` and no `--all`, then with an unknown lane, then with
  `--all --dry-run`
- **Then** each of the first two exits 2 naming what it needs (`LANE=<lane>` / `ALL=1`, or the
  unknown lane plus the real fleet), the dry run exits 0 and prints `DRY RUN`, and in all three the
  profile home is still empty
- **Test:** tests/test_agent_profile_provision.py::test_writing_a_profile_home_is_never_the_default_and_an_unknown_lane_is_refused

#### Scenario: the target is wired to the Makefile and to a pipeline job

- **Given** this repository
- **When** the wiring is read
- **Then** the Makefile defines `_agent-profile-provision` (the seam, not a second copy) and the
  public `agent-profile-provision` that delegates to it, `qa-validate`'s `live-smoke` job runs
  `make agent-profile-provision` against `$RUNNER_TEMP`, no workflow reaches
  `scripts/agent_profile_provision.py` past the Makefile (rule 6m), the script has a row in
  `ARCHITECTURE.md` (rule 6h), and this suite is discovered by `make test`
- **Test:** tests/test_agent_profile_provision.py::test_the_target_is_wired_to_the_makefile_and_a_pipeline_job
