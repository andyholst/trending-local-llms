# bot-agent-run-safety

## ADDED Requirements

### Requirement: The scrape is made from the tool that can see the key

Hermes strips every credential-shaped name from an `execute_code` child
(`tools/code_execution_env.py::_scrub_child_env`) and never unwraps `_HERMES_FORCE_` there, so a key
read in that child is EMPTY and the request goes out with an empty Bearer. Every search leg's
contract MUST therefore name the **terminal** tool as the only way to make the Firecrawl scrape,
name `execute_code` / `web_extract` / `web_search` as forbidden for it, and offer
`python3 scripts/update_trending.py` as the alternative that reads the key in-process. The wording
MUST live in ONE definition and be embedded by every leg.

WHEN a search leg scrapes the mirror,
THEN it does so from the terminal (or through `scripts/update_trending.py`), never from
`execute_code`, `web_extract` or `web_search`.

#### Scenario: the rule is one definition and every leg embeds it

- **Given** the repository's `Makefile`
- **When** `TOOL_ASK` and the four `_search-<backend>` recipes are read
- **Then** `TOOL_ASK` is defined exactly once and each of the four prompts carries `$(TOOL_ASK)`
- **Test:** `tests/test_search_tool_pinning.py::test_the_rule_is_one_definition_and_every_leg_embeds_it`

#### Scenario: the rule names the terminal, forbids the credential-less tools, and says why

- **Given** the `TOOL_ASK` definition
- **When** its text is read
- **Then** it names the terminal tool, names `execute_code` / `web_extract` / `web_search` as
  forbidden, names `scripts/update_trending.py` as the alternative, and gives the
  `_scrub_child_env` reason
- **Test:** `tests/test_search_tool_pinning.py::test_the_rule_forbids_the_credential_less_tools`

#### Scenario: no leg prompt invites a credential-less tool

- **Given** the four `_search-<backend>` recipes
- **When** each prompt body is read
- **Then** none tells the agent to reach the mirror with `web_extract` or `web_search`
- **Test:** `tests/test_search_tool_pinning.py::test_no_leg_prompt_invites_a_credential_less_tool`

#### Scenario: the wording really reaches the agent

- **Given** the amd leg's recipe
- **When** `make -n _search-amd` expands it, with no key in the environment
- **Then** the printed prompt carries the terminal rule and the `execute_code` prohibition
- **Test:** `tests/test_search_tool_pinning.py::test_the_wording_reaches_the_agent`

### Requirement: The documents the agent reads pin the same tool

The preloaded leg contract (`.hermes/skills/data-search/SKILL.md`) and the guide it points at
(`skills/gather-data.md`) MUST name the terminal as the scrape's tool, forbid `execute_code`, and
name the credential by the variable that exists (`FIRECRAWL_API_KEY`) — never an elided or
placeholder name, which is the #357 defect.

WHEN the agent reads its contract or the gather guide,
THEN both tell it the same tool and the same real variable name.

#### Scenario: the skill and the guide agree with the prompt

- **Given** `.hermes/skills/data-search/SKILL.md` and `skills/gather-data.md`
- **When** both are read
- **Then** each names the terminal tool and `execute_code` as forbidden, and neither sends the agent
  to `web_extract` for the mirror
- **Test:** `tests/test_search_tool_pinning.py::test_the_skill_and_the_guide_pin_the_same_tool`

#### Scenario: the documents name the variable that exists

- **Given** the same two documents
- **When** their header instructions are read
- **Then** each names `FIRECRAWL_API_KEY` and carries no elided form of it
- **Test:** `tests/test_search_tool_pinning.py::test_the_documents_name_the_variable_that_exists`

#### Scenario: the added rule keeps the prompt inside its budget

- **Given** the rendered prompts of all four legs
- **When** each is measured against `check_agent_skills.PROMPT_BUDGET`
- **Then** every one fits
- **Test:** `tests/test_search_tool_pinning.py::test_the_rule_keeps_every_leg_inside_the_prompt_budget`
