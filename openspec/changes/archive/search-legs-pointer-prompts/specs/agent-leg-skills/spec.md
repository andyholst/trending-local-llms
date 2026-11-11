# agent-leg-skills

## ADDED Requirements

### Requirement: A leg's prompt is a pointer plus parameters — the rules live in its skill

Every agent leg's `hermes -z` prompt MUST be short enough to be a pointer plus that run's
parameters, and the rules it obeys MUST exist in the skill the leg preloads with `-s`. A rule that
was moved into a skill MUST NOT be restated in a recipe: two homes for one rule drift, and nothing
compares them.

WHEN a `hermes -z` leg's recipe is read
THEN its quoted prompt is at most `PROMPT_BUDGET` (900) characters, it names the skill it follows,
and it carries only that run's parameters.

#### Scenario: the four search legs are pointers

- **Given** the `_search-nvidia`, `_search-metal`, `_search-cpu` and `_search-amd` recipes
- **When** `make agent-skills-report` runs
- **Then** each prompt is under 900 characters and preloads `data-search,bot-unattended`
- **And** each still carries its own `backend`, keyword list, `$(MODEL_QUERIES)` and `--write-raw`
  command
- **Test:** `tests/test_agent_skills.py::test_the_real_legs_preload_a_real_skill`

#### Scenario: a prompt that grows back into a rulebook is refused

- **Given** a leg whose prompt is 4000 characters
- **When** the gate reads that tree
- **Then** it fails naming the target and the budget
- **Test:** `tests/test_agent_skills.py::test_the_gate_fails_each_defect`

### Requirement: A retired rule is stated in its skill and nowhere in a recipe

The engine rule, the five measurement dimensions, the terminal-tool pin and the post-signal rule
MUST each be stated by the skill they were moved to, and MUST NOT appear in any `hermes -z` recipe —
including when the skill loses the rule, which would leave the contract with a hole.

WHEN `scripts/check_agent_skills.py` reads the tree
THEN every name in `RETIRED_RULES` appears in its skill and in no leg's recipe.

#### Scenario: the shipped tree states each retired rule exactly once

- **Given** the `Makefile` and `.hermes/skills/data-search/SKILL.md`
- **When** `make check-agent-skills` runs
- **Then** it reports ok, and no recipe carries `engine_repo`, `system_ram_min`, `execute_code`,
  `/status/<id>` or the counter list
- **Test:** `tests/test_search_key.py::test_the_tool_pin_has_exactly_one_definition`

#### Scenario: a rule that left a recipe without arriving in the skill is refused

- **Given** a tree whose `data-search` skill carries none of the retired rules
- **When** the gate reads it
- **Then** it fails saying the rule never arrived in the skill it was moved to
- **Test:** `tests/test_agent_skills.py::test_the_gate_fails_each_defect`

#### Scenario: a recipe that restates a retired rule is refused

- **Given** a leg whose prompt contains `engine_repo`
- **When** the gate reads that tree
- **Then** it fails naming the recipe and the skill the rule belongs in
- **Test:** `tests/test_agent_skills.py::test_the_gate_fails_each_defect`

### Requirement: The moved rules keep every guarantee the recipes carried

A rule that moves out of the Makefile MUST be asserted at the same strength where it now lives, so
the migration cannot quietly drop a requirement.

WHEN the migrated tests read the tree
THEN the engine rule, the five dimensions, the tool pin, the post-signal rule, the per-query write
and the AMD/ROCm rules are all asserted against `.hermes/skills/data-search/SKILL.md`.

#### Scenario: the engine rule survives the move

- **Given** the `data-search` skill
- **When** its text is read
- **Then** it states that the engine must be the one the post actually names, that a t/s with no
  engine is not a valid entry, that a model/vendor/quant is never an engine, and it keeps the fork,
  `engine_repo` and verified-lookup rules
- **Test:** `tests/test_hermes_prompts.py::test_every_search_leg_asks_for_the_engine_rule_from_one_definition`

#### Scenario: the five dimensions survive the move

- **Given** the `data-search` skill
- **When** its text is read
- **Then** it names `system_ram_min`, `weight_gb`, `context_tokens`, `storage_offload` and
  `engine_min_version`, says a stated figure belongs in its field, and forbids inventing one
- **Test:** `tests/test_hermes_prompts.py::test_every_search_leg_asks_for_the_model_dimensions_from_one_definition`

#### Scenario: the post-signal rule survives the move

- **Given** the `data-search` skill
- **When** its text is read
- **Then** it requires the `…/status/<id>` URL, rejects the bare mirror or a profile page, and
  requires the counters as integers
- **Test:** `tests/test_post_signal.py::test_prompts_ask_for_post_url`

#### Scenario: the per-query write survives the move

- **Given** the `data-search` skill
- **When** its text is read
- **Then** it requires a write after EACH query and forbids one big payload
- **And** every leg's prompt still carries `--write-raw <backend> <`
- **Test:** `tests/test_search_budget.py::test_prompts_write_per_query`

#### Scenario: the AMD leg's rules survive the move

- **Given** the `data-search` skill
- **When** its text is read
- **Then** it records the AMD card as posted, puts ROCm/HIP/Vulkan in `quant` and never in the engine
  name, takes decode t/s only, and skips datacenter Instinct
- **Test:** `tests/test_amd_backend.py::test_wiring_parity`
