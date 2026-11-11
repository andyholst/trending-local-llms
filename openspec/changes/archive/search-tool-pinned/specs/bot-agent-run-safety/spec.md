# bot-agent-run-safety

## ADDED Requirements

### Requirement: A search prompt names the TOOL that can see the credential

An instruction that has the agent authenticate MUST say which tool to make the authenticated call
from, when the tools differ in what they can see. Hermes strips provider credentials from more than
the terminal: `execute_code`'s child environment drops every name carrying a secret substring and
does **not** unwrap the `_HERMES_FORCE_<NAME>` form, so a call made there carries an empty Bearer and
fails `HTTP 401` while the key is set. The rule MUST live in ONE definition the prompts take by
variable, so the four legs cannot drift apart.

WHEN a search prompt tells the agent to call the Firecrawl scrape API,
THEN it names the terminal tool as the place to make that call, forbids `execute_code` by name with
the reason, and takes the wording from a single `SEARCH_TOOL_ASK` definition.

#### Scenario: the fragment is defined once and pins the terminal tool

- **Given** the repository's `Makefile`
- **Then** `SEARCH_TOOL_ASK :=` is defined exactly once, its text names the TERMINAL tool, forbids the call from `execute_code`, and states the empty-Bearer / `HTTP 401` consequence
- **Test:** `tests/test_search_key.py::test_the_prompts_pin_the_tool_that_can_see_the_key`

#### Scenario: every leg takes the rule from the variable and keeps no second copy

- **Given** the four `_search-nvidia`, `_search-metal`, `_search-cpu`, `_search-amd` recipes
- **Then** each contains `$(SEARCH_TOOL_ASK)`, and none repeats the prohibition inline
- **Test:** `tests/test_search_key.py::test_the_prompts_pin_the_tool_that_can_see_the_key`

#### Scenario: the fragment cannot break the prompt string

- **Given** the `SEARCH_TOOL_ASK` definition, which is expanded inside `hermes -z "…"`
- **Then** it carries no double quote
- **Test:** `tests/test_search_key.py::test_the_prompts_pin_the_tool_that_can_see_the_key`

### Requirement: The skill a leg preloads pins the same tool

The four legs preload `.hermes/skills/data-search/SKILL.md`, and `AGENTS.md` points a human at
`skills/gather-data.md`. Both MUST carry the same tool rule, or an agent that follows the skill
instead of the prompt re-introduces the keyless call.

WHEN a leg reads its skill or the data-gathering guide,
THEN both say the scrape is made from the terminal tool and never from `execute_code`.

#### Scenario: the preloaded skill and the guide carry the rule

- **Given** `.hermes/skills/data-search/SKILL.md` and `skills/gather-data.md`
- **Then** each names the terminal tool and forbids `execute_code`
- **Test:** `tests/test_search_key.py::test_the_skill_the_leg_preloads_pins_the_same_tool`
