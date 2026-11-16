# architecture-inventory — the agent lanes are part of the generated description

## ADDED Requirements

### Requirement: the generated block names each pipeline's agent lanes

The generated §10 block renders, for every pipeline, the `hermes -z` legs it
calls with the skill contracts each leg preloads (resolved through wrapper
targets by `scripts/check_agent_skills.py`'s single legs parser), and the
marker verbs that pipeline announces, read from `scripts/bot_markers.py`'s
REGISTRY. A leg that preloads nothing and a marker registered for a pipeline
are both visible in the block; the block never re-spells a marker verb.

WHEN the generator renders a pipeline's §10 entry
THEN every `hermes -z` leg it calls appears with its `-s` preload set,
AND the pipeline's registered marker verbs are listed as `bot_markers.py` names them,
AND no marker verb is re-spelled inside the generator.

#### Scenario: a planted leg's preload set and its pipeline's marker verbs appear in the block

- **Given** a fixture repo whose `make implement-issue` leg preloads `issue-implement,bot-unattended` and whose `issue-bot.yml` calls it
- **When** `scripts/architecture_bot.py --write` regenerates `ARCHITECTURE.md`
- **Then** the block names `make implement-issue` with both preloaded skills
- **Test:** tests/test_architecture_bot.py::test_agent_lanes_skill_contracts_and_bot_verbs_are_named

#### Scenario: the pipeline's announced verbs come from the one marker registry

- **Given** the same fixture repo
- **When** the block is regenerated
- **Then** the pipeline's lane line lists its `issue-bot` registry verbs (e.g. `issue-bot-start`) exactly as `scripts/bot_markers.py` registers them
- **Test:** tests/test_architecture_bot.py::test_agent_lanes_skill_contracts_and_bot_verbs_are_named

### Requirement: every skill contract on disk is inventoried, orphan labeled

The generated block lists every `agents/skills/*/SKILL.md`; each is labeled with
the legs that preload it, or as `no leg — orphan contract` when none does.

WHEN the block renders the Agent skill contracts inventory
THEN every skill directory on disk is named,
AND each carries its preloading legs or the explicit orphan label.

#### Scenario: an orphan skill is printed as an orphan

- **Given** a fixture repo with a `lonely-skill` no leg preloads
- **When** `scripts/architecture_bot.py --write` regenerates the block
- **Then** `lonely-skill` appears labeled `no leg — orphan contract`
- **Test:** tests/test_architecture_bot.py::test_agent_lanes_skill_contracts_and_bot_verbs_are_named

### Requirement: the checker refuses unnamed lane contracts

`make architecture-check` fails when a skill contract on disk is not named in
the description, or when a skill name a Makefile leg passes to `-s` is not
named in the description — a dropped `-s` pointer or a rotting orphan cannot
hide under a green gate.

WHEN `scripts/architecture_check.py` collects findings over the tree
THEN a skill contract on disk that the description does not name is a finding,
AND a skill name a Makefile leg preloads that the description does not name is a finding,
AND `make architecture-check` exits non-zero on either.

#### Scenario: an unnamed contract, orphan and preload each go red; naming them goes green

- **Given** a fixture repo whose description names none of its lane skills
- **When** `scripts/architecture_check.py` collects findings
- **Then** the on-disk contract, the orphan and the un-named preload each produce a `#935` finding, and naming all three turns the lane findings green
- **Test:** tests/test_architecture.py::test_agent_skill_contracts_and_leg_preloads_must_be_named

#### Scenario: the shipped repository's own lanes are current

- **Given** this repository as shipped
- **When** the checker validates the generated block against the real Makefile legs, marker registry and `agents/skills/` tree
- **Then** `--check` passes with zero findings
- **Test:** tests/test_architecture.py::test_real_repo_description_is_current
