# bot-agent-run-safety

## ADDED Requirements

### Requirement: Every credential a container receives is forwarded to the agent's shell

Hermes strips provider credentials from its terminal tool, so a key forwarded only under its own
name never reaches the agent's commands. Every credential a run wrapper forwards MUST be listed in
the ONE `AGENT_SHELL_KEYS` list and ALSO forwarded by name as `_HERMES_FORCE_<NAME>`, exported from
`<NAME>` on the host — never as a value on a command line.

WHEN a run wrapper forwards a credential into a container,
THEN the same credential is forwarded as `_HERMES_FORCE_<NAME>`, by name, from the one list.

#### Scenario: the run wrappers forward every key the list names, by name

- **Given** the repository's `Makefile`
- **When** `DOCKER_RUN` and `TEST_RUN` are read
- **Then** both forward `$(AGENT_SHELL_FORWARD)`, and every plain `-e <NAME>` they carry is in `AGENT_SHELL_KEYS`
- **Test:** `tests/test_agent_shell_keys.py::test_the_list_names_every_credential_a_container_receives`

#### Scenario: the value never reaches a command line

- **Given** every key set to a sentinel value
- **When** `make -n agent-shell-keys-check` prints the command it would run
- **Then** each `-e _HERMES_FORCE_<NAME>` is present and the sentinel is not
- **Test:** `tests/test_agent_shell_keys.py::test_the_forced_names_travel_by_name_never_by_value`

#### Scenario: make exports the forced name only for a set key, and only on the host

- **Given** `FIRECRAWL_API_KEY` and `HF_TOKEN` set and `NOUS_API_KEY` unset
- **When** a recipe reads the forced names through the real Makefile
- **Then** the set keys are exported with the same length, the unset one is not, and inside a container nothing is re-created
- **Test:** `tests/test_agent_shell_keys.py::test_make_exports_the_forced_name_from_the_plain_one`

### Requirement: The agent's shell is PROVEN to see each credential

A check MUST run a command through Hermes's real terminal environment, in the bot image, and fail —
naming the variable, printing no value — when a credential set in the container is empty in the
agent's shell. It runs in `qa-validate`'s `live-smoke` job and before every search leg.

WHEN the credentials reach the container,
THEN the agent's shell sees each of them, or the check fails and names the one it cannot see.

#### Scenario: plain names leave the agent's shell blind

- **Given** the keys forwarded under their plain names only (the wiring before this change)
- **When** the check drives Hermes's real `LocalEnvironment`
- **Then** it exits 1, reports `FIRECRAWL_API_KEY` EMPTY in the agent's shell, names the fix, and prints no value
- **Test:** `tests/test_agent_shell_keys.py::test_plain_names_leave_the_agent_shell_blind`

#### Scenario: the forced names make every key visible

- **Given** every key and its `_HERMES_FORCE_<NAME>` set
- **When** the check drives Hermes's real `LocalEnvironment`
- **Then** it exits 0 and reports every key visible, printing no value
- **Test:** `tests/test_agent_shell_keys.py::test_forced_names_make_every_key_visible`

#### Scenario: a key missing from the container is loud

- **Given** no credential in the environment
- **When** the check runs
- **Then** it exits 2 and names the variable; the opt-out reports NOT CONFIGURED and is never used by a workflow
- **Test:** `tests/test_agent_shell_keys.py::test_a_key_missing_from_the_container_is_loud`

#### Scenario: the check is wired where it bites

- **Given** the Makefile and `qa-validate.yml`
- **When** they are read
- **Then** `_agent-shell-keys-check` runs the script on the one list, the public target runs in `DOCKER_RUN`, every search leg's pre-flight runs it, `live-smoke` calls it, and the suite is in `make test`
- **Test:** `tests/test_agent_shell_keys.py::test_the_check_is_wired_to_a_make_target_ci_runs`
