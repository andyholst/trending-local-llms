# bot-agent-run-safety (change: agent-shell-keys-loud-skip-946)

## ADDED Requirements

### Requirement: The credential-visibility gate is decided by the container marker, never by silence

`scripts/agent_shell_keys_check.py` MUST decide an unresolvable Hermes terminal probe by the
environment, through ONE implementation: a probe failure whose cause is the local Hermes install
itself (the checkout or its interpreter is absent, or Hermes's own import chain fails) is a LOUD
SKIP (exit 0, a line naming the gate's authoritative home) OUTSIDE the pinned test image, and a
LOUD FAILURE (exit 2) INSIDE it. The container marker is the Makefile's own `IN_CONTAINER` when
given, else `/.dockerenv`. A credential that is not set, and a probe failure that is not an
import/wiring class, remain exit 2 everywhere. A skip is never silent: the module prints it as a
counted `skip` line in its summary.

#### Scenario: the host class — the same probe failure is a LOUD SKIP outside the marker

- **Given** a Hermes checkout whose `tools/environments/local.py` cannot import, a key set to a
  sentinel, and `IN_CONTAINER=0`
- **When** `scripts/agent_shell_keys_check.py` runs through the real product code
- **Then** it exits 0 printing `SKIP [wiring]`, naming `IN_CONTAINER=1` as the gate's authoritative
  home, and never prints the sentinel value
- **Test:** `tests/test_agent_shell_keys.py::test_probe_wiring_unresolvable_decides_loudly_by_container_marker`

#### Scenario: inside the pinned test image the no-skip policy is unchanged

- **Given** the same unresolvable probe and `IN_CONTAINER=1`
- **When** `scripts/agent_shell_keys_check.py` runs through the real product code
- **Then** it exits 2 with a `FATAL` line — the gate never skips where CI enforces it
- **Test:** `tests/test_agent_shell_keys.py::test_probe_wiring_unresolvable_decides_loudly_by_container_marker`

#### Scenario: the real-probe group is reported as a counted loud skip, never a failure

- **Given** the script's own `SKIP [wiring]` output from the fixture run outside the marker
- **When** the module's skip accounting handles it
- **Then** it reports a counted `skip` line (under `SKIPPED`, never under `FAILED`) quoting the
  script's line
- **Test:** `tests/test_agent_shell_keys.py::test_probe_wiring_unresolvable_decides_loudly_by_container_marker`

#### Scenario: a credential that is not set is still a loud failure everywhere

- **Given** no credential set in the environment, on any machine
- **When** `scripts/agent_shell_keys_check.py` runs
- **Then** it exits 2 naming the missing variables — the skip decision never reaches a key check
- **Test:** `tests/test_agent_shell_keys.py::test_a_key_missing_from_the_container_is_loud`
