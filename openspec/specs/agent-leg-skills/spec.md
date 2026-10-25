# agent-leg-skills Specification

## Purpose
TBD - created by archiving change agent-leg-skills. Update Purpose after archive.

## Requirements

### Requirement: Every agent leg preloads its contract from a project skill

Every `hermes -z` recipe in the `Makefile` MUST preload a skill with `-s <skill>,bot-unattended`.
The skill MUST exist at `.hermes/skills/<name>/SKILL.md`, its frontmatter `name` MUST equal its
directory name, and it MUST carry `## Inputs`, `## Output` and `## Rules`. A leg's inline prompt is
a pointer plus that run's parameters, never the rulebook.

#### Scenario: the shipped tree preloads a real skill on every leg

- **Given** the `Makefile` and `.hermes/skills/`
- **When** `make check-agent-skills` runs
- **Then** it reports ok and exits 0
- **And** every leg it found names `bot-unattended` and a skill that exists with the required
  sections
- **Test:** `tests/test_agent_skills.py::test_the_real_legs_preload_a_real_skill`

#### Scenario: a leg that preloads nothing is refused

- **Given** a leg whose `hermes -z` recipe carries no `-s`
- **When** the gate reads that tree
- **Then** it fails naming the target and saying its rules are inline
- **Test:** `tests/test_agent_skills.py::test_the_gate_fails_each_defect`

#### Scenario: a leg naming a skill that does not exist is refused

- **Given** a leg preloading `no-such-skill`
- **When** the gate reads that tree
- **Then** it fails saying the leg would run with no contract at all
- **Test:** `tests/test_agent_skills.py::test_the_gate_fails_each_defect`

#### Scenario: a skill whose frontmatter name disagrees with its directory is refused

- **Given** `.hermes/skills/bot-unattended/SKILL.md` whose frontmatter says `name: other`
- **When** the gate reads that tree
- **Then** it fails because `-s bot-unattended` would not resolve it
- **Test:** `tests/test_agent_skills.py::test_the_gate_fails_each_defect`

### Requirement: The unattended contract lives in exactly one skill

`NEVER ask a question` (case-insensitive) MUST appear in `.hermes/skills/bot-unattended/SKILL.md`
and in NO make recipe and NO other skill, so a leg cannot carry half of it and the paragraph cannot
drift between legs.

#### Scenario: the shipped contract is in one place

- **Given** the `Makefile` and every `.hermes/skills/*/SKILL.md`
- **When** both are read
- **Then** exactly one skill states the rule and no recipe inlines it
- **Test:** `tests/test_agent_skills.py::test_the_unattended_contract_lives_in_one_place`

#### Scenario: a recipe that inlines the contract is refused

- **Given** a leg whose prompt contains the unattended sentence
- **When** the gate reads that tree
- **Then** it fails naming the target and the skill the text belongs in
- **Test:** `tests/test_agent_skills.py::test_the_gate_fails_each_defect`

### Requirement: The skills directory is registered and the registration is proved

`_setup` MUST register the checkout's `.hermes/skills` in the container's Hermes home
(`scripts/hermes_skills_register.py`, through the Hermes CLI) and MUST read it back with
`--check`. A missing directory, a missing CLI or an unreadable config MUST be a loud non-zero exit,
never a skip.

#### Scenario: a fresh Hermes home is not registered, and registering fixes it

- **Given** a Hermes home with no `skills.external_dirs`
- **When** the register script runs with `--check` and then for real
- **Then** `--check` exits 1 before and 0 after, and the value read back is a real list
- **Test:** `tests/test_agent_skills.py::test_setup_registers_the_directory_and_reads_it_back`

#### Scenario: a second registration does not duplicate the entry

- **Given** a home already carrying the directory
- **When** the register script runs again
- **Then** the config still names it exactly once
- **Test:** `tests/test_agent_skills.py::test_setup_registers_the_directory_and_reads_it_back`

#### Scenario: setup registers and reads back

- **Given** the `_setup` recipe
- **When** its body is read
- **Then** it calls both `_hermes-skills-register` and `_hermes-skills-check`
- **Test:** `tests/test_agent_skills.py::test_setup_registers_the_directory_and_reads_it_back`

### Requirement: A workflow names rc=3 as "the agent asked for input"

Every workflow that runs a leg MUST have an `rc == 3` branch whose text says the agent asked for
input (a detached, unattended run), and in `issue-bot.yml` that branch MUST come before the generic
"produced no implementation" message.

#### Scenario: the issue-bot's rc=3 branch precedes its generic failure

- **Given** `.github/workflows/issue-bot.yml`
- **When** its failure step is read
- **Then** the `RC == 3` branch exists, mentions the agent asking for input, names the seam, and
  appears before `::error::issue-bot produced no implementation`
- **Test:** `tests/test_agent_skills.py::test_the_workflows_name_rc_3_as_a_question`

#### Scenario: both reviewer paths name rc=3

- **Given** `.github/workflows/issue-review-bot.yml`
- **When** its two agent steps are read
- **Then** both carry the rc=3 branch
- **Test:** `tests/test_agent_skills.py::test_the_workflows_name_rc_3_as_a_question`

### Requirement: The gate is reachable from `make lint` and the suite

`make check-agent-skills` MUST run `scripts/check_agent_skills.py check`, `make lint` MUST call it
(so CI's `validate` job executes it), and `tests/test_agent_skills.py` MUST be discovered by
`make test`.

#### Scenario: lint executes the gate

- **Given** the `Makefile`
- **When** `make -n lint` runs
- **Then** the gate's command is in the executed recipe and the target exists
- **Test:** `tests/test_agent_skills.py::test_the_gate_is_wired_to_the_lint_target_and_the_suite`

#### Scenario: the new module is part of the suite

- **Given** `scripts/run_tests.sh --list`
- **When** the list is read
- **Then** `test_agent_skills.py` is in it
- **Test:** `tests/test_agent_skills.py::test_the_gate_is_wired_to_the_lint_target_and_the_suite`
