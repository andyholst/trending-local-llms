# agent-identity

## ADDED Requirements

### Requirement: The agent identity has one definition

`scripts/agent_identity.py` MUST be the only place the agent's name, address and the accepted
identity sets are written, and `scripts/check_commit_authorship.py` MUST import them from it.

#### Scenario: the guard's sets are the one definition

- **Given** the authorship guard and the identity module
- **When** the guard reads the allowed sets
- **Then** they are the module's own tuples, not a second copy
- **Test:** tests/test_workflows.py::test_the_agent_identity_has_one_definition

#### Scenario: no workflow spells the identity out

- **Given** every workflow under `.github/workflows/`
- **When** the guard scans them
- **Then** none contains the agent's address or its `git config user.name` literal
- **Test:** tests/test_workflows.py::test_the_agent_identity_has_one_definition

### Requirement: Committing jobs set the identity through the seam

Every job step that commits MUST call `make git-identity`, which runs the module's `--git-config`.

#### Scenario: the committing jobs

- **Given** every workflow step whose `run` contains `git commit`
- **When** the guard inspects it
- **Then** it calls `make git-identity` and carries no identity literal
- **Test:** tests/test_workflows.py::test_every_committing_bot_job_commits_as_the_agent

#### Scenario: the seam

- **Given** the Makefile
- **When** the guard reads the `git-identity` recipe
- **Then** it runs `python3 scripts/agent_identity.py --git-config` and is a host target
- **Test:** tests/test_workflows.py::test_the_agent_identity_has_one_definition
