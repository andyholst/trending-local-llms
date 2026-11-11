# agent-image

## ADDED Requirements

### Requirement: ONE installer seam for the Hermes CLI

The Hermes CLI MUST enter this repository through ONE implementation —
`scripts/install_hermes_ci.sh` — used by the image build and by `make _setup`
alike, and the install pin MUST be overridable without editing the Dockerfile.

WHEN something needs the Hermes CLI present, THEN it runs the seam, which tries an
existing `hermes` on PATH, then `HERMES_INSTALL_URL`, then
`uv tool install $HERMES_PACKAGE`, and fails loudly when none of the three works.

#### Scenario: a CLI that is already installed is used as-is

- **Given** a `hermes` on PATH and a configured `HERMES_INSTALL_URL`
- **When** the seam runs
- **Then** it reports the installed CLI, exits 0, and neither downloads nor calls the package manager
- **Test:** `tests/test_install_hermes_ci.py::test_a_present_cli_is_used_and_nothing_is_downloaded`

#### Scenario: the configured installer is fetched and run

- **Given** no `hermes` on PATH and `HERMES_INSTALL_URL` set to an installer that produces one
- **When** the seam runs
- **Then** that URL is fetched with `curl -fsSL`, the fetched script is executed, and the installed CLI is reported
- **Test:** `tests/test_install_hermes_ci.py::test_the_configured_installer_is_fetched_and_run`

#### Scenario: an installer that produces nothing falls through to the package manager

- **Given** a URL installer that exits 0 without putting a `hermes` on PATH, and a `uv` that can install the package
- **When** the seam runs
- **Then** it says the installer produced nothing and then runs `uv tool install $HERMES_PACKAGE`, reporting the CLI that produced
- **Test:** `tests/test_install_hermes_ci.py::test_an_installer_that_produces_nothing_falls_through_to_uv`

#### Scenario: nothing works, loudly

- **Given** no `hermes`, no `HERMES_INSTALL_URL` and no `uv`
- **When** the seam runs
- **Then** it exits non-zero and names all three paths it tried, because an agent image without an agent must not build
- **Test:** `tests/test_install_hermes_ci.py::test_nothing_works_is_a_loud_failure_naming_every_path`

#### Scenario: a failed download is not silently retried elsewhere

- **Given** a `HERMES_INSTALL_URL` whose download fails
- **When** the seam runs
- **Then** it fails naming that URL and never reaches the package-manager path
- **Test:** `tests/test_install_hermes_ci.py::test_a_failed_download_is_a_loud_failure_without_a_second_attempt`

### Requirement: The image proves the agent it carries, at build time

The image build MUST write the model alias from the repository's own pins and then
verify it, so a wrong model, a provider that is not `custom` or a `key_env` that is
not `NOUS_API_KEY` fails the BUILD rather than a bot run.

WHEN the base image is built, THEN it runs `make _setup` (which writes
`model.aliases.$(HERMES_ALIAS).*` from `HERMES_MODEL`, `NOUS_BASE` and the key
NAME) followed by `make _hermes-alias-check`, which reads every field back.

#### Scenario: the build asserts the alias after writing it

- **Given** the `Dockerfile`
- **When** its steps are read
- **Then** it copies and runs the seam, carries the pin as build args, and runs `make _setup` followed by `make _hermes-alias-check` in one `RUN` with the CLI on PATH
- **Test:** `tests/test_install_hermes_ci.py::test_the_dockerfile_asserts_the_alias_at_build_time`

#### Scenario: the pin has one value across the two files

- **Given** the `Dockerfile`'s `ARG HERMES_INSTALL_URL` / `ARG HERMES_PACKAGE` defaults and the Makefile's `?=` defaults
- **When** they are compared
- **Then** they are the same values, so the image build and the host path install from the same place
- **Test:** `tests/test_install_hermes_ci.py::test_the_install_pin_has_one_definition_across_the_two_files`

#### Scenario: the alias name has one definition for writer and reader

- **Given** the Makefile
- **When** `_setup` and `_hermes-alias-check` are read
- **Then** both use `$(HERMES_ALIAS)`, no hardcoded alias name remains in `_setup`, and the name is defined exactly once
- **Test:** `tests/test_install_hermes_ci.py::test_the_alias_has_one_name_for_the_writer_and_the_reader`

#### Scenario: a different alias fails the check loudly

- **Given** a `hermes` whose `provider` is not `custom`
- **When** `make _hermes-alias-check` runs
- **Then** it exits non-zero, names that field and its expected value, reports every mismatch rather than the first, and refuses in words
- **Test:** `tests/test_install_hermes_ci.py::test_the_alias_check_passes_on_the_pin_and_fails_on_a_different_one`

### Requirement: No credential is baked into the agent image

The image MUST know only the NAME of the credential it reads at run time (rule 3e):
no key value may appear in the Dockerfile or the seam.

WHEN the Dockerfile and the seam are read, THEN no key name is assigned a value,
no `ENV`/`ARG` carries a credential, and the seam neither reads a key, writes
`config.yaml`, nor forwards a key to a command.

#### Scenario: the image names the key, never holds it

- **Given** the `Dockerfile` and `scripts/install_hermes_ci.sh`
- **When** both are read for a credential value
- **Then** only NAMEs appear (the alias's `key_env=NOUS_API_KEY` and the documented nerve mapping), and the seam never expands or forwards one
- **Test:** `tests/test_install_hermes_ci.py::test_no_credential_value_is_baked_into_the_image`
