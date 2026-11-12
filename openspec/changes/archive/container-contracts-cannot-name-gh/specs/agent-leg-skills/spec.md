# agent-leg-skills

## ADDED Requirements

### Requirement: A container-bound contract may not instruct a tool the container does not have

The base images carry no GitHub CLI (`make container-audit` reports `gh MISSING` in every pinned
image), and GitHub writes are done by host-side workflow steps. Therefore no `hermes -z` leg recipe
and no `.hermes/skills/*/SKILL.md` may INSTRUCT the agent to run `gh <subcommand>`
(`gh issue`, `gh pr`, `gh api`, `gh run`, `gh repo`, `gh label`, `gh search`, `gh workflow`,
`gh release`, `gh actions`): such an instruction is unreachable code the agent can only fail on or
skip silently, and it teaches every future leg that container work can write to GitHub. A sentence
that **states gh is absent or forbids it** — the `bot-unattended` forbiddance — is the contract
itself and MUST NOT be a finding. The scan reaches exactly what a leg can read: the recipes and
every preloaded skill.

#### Scenario: the shipped tree instructs no gh anywhere a leg can read it

- **Given** the `Makefile` leg recipes and all five `.hermes/skills/*/SKILL.md`
- **When** `make check-agent-skills` runs
- **Then** it reports ok and exits 0
- **And** the `gh`-scan finds no instruction in any recipe or skill, while the real
  `bot-unattended` forbiddance is present
- **Test:** `tests/test_agent_skills.py::test_the_gh_guard_refuses_instructions_and_keeps_forbiddances`

#### Scenario: a leg recipe that instructs the agent to run gh is refused

- **Given** a `hermes -z` recipe whose prompt contains `gh issue edit --add-label …`
- **When** the gate reads that tree
- **Then** it fails naming the target, the line, and that the image has no GitHub CLI
- **Test:** `tests/test_agent_skills.py::test_the_gate_fails_each_defect`

#### Scenario: a preloaded skill that instructs the agent to run gh is refused

- **Given** `.hermes/skills/data-search/SKILL.md` carrying a `gh pr comment …` rule
- **When** `make check-agent-skills` reads the skills directory
- **Then** it fails naming the skill file and the line
- **Test:** `tests/test_agent_skills.py::test_the_gate_fails_each_defect`

#### Scenario: stating that gh is absent is the contract, not a violation

- **Given** a skill line "**You have no `gh` and no network write.** Do not comment, close, label,
  or edit anything" and another "the container has no gh; forbid gh entirely"
- **When** the gate's gh-scan reads them
- **Then** neither is a finding
- **Test:** `tests/test_agent_skills.py::test_the_gh_guard_refuses_instructions_and_keeps_forbiddances`
