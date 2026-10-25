# bot-agent-run-safety

## ADDED Requirements

### Requirement: Every search leg makes its Firecrawl call from the terminal tool

The scrape MUST be made from the agent's **terminal** tool (a `curl` call), because that is the only
tool whose child environment receives the `_HERMES_FORCE_<NAME>` unwrap that carries
`FIRECRAWL_API_KEY`. `execute_code` MUST be named as forbidden — its child is scrubbed of every
secret-named variable — and the supported Python route
(`python3 scripts/update_trending.py --write-raw <backend>`) MUST be named for the snapshot write,
since it reads the key in-process.

WHEN a search leg needs the Firecrawl API,
THEN it calls it from the terminal, and the prompt says so in every backend's leg.

#### Scenario: every leg carries the tool rule, from one definition

- **Given** the `Makefile`'s four `_search-*` recipes
- **When** each leg's prompt is read
- **Then** each carries `$(TOOL_ASK)`, and the block has exactly one definition
- **Test:** `tests/test_search_key.py::test_every_search_leg_pins_the_scrape_to_the_terminal_tool`

#### Scenario: the rule names the terminal and refuses execute_code

- **Given** the `TOOL_ASK` block
- **When** it is read as the agent receives it
- **Then** it names the terminal tool as the route, names `execute_code` as forbidden, states that
  its child loses every secret-named variable (`_HERMES_FORCE_` included), rules out
  `web_extract`/`web_search` for the scrape, and names the in-process write route
- **Test:** `tests/test_search_key.py::test_the_tool_rule_names_the_terminal_and_refuses_execute_code`

#### Scenario: a prompt that has lost the rule is RED

- **Given** the same assertions run against `origin/master`'s `Makefile` (the code before this
  change)
- **When** they are evaluated
- **Then** they fail — the guard cannot be satisfied by the old prompts
- **Test:** `tests/test_search_key.py::test_the_tool_rule_guard_is_red_on_the_old_makefile`

### Requirement: The written procedure agrees with the prompt

The search procedure a leg loads (`skills/gather-data.md`) and the leg's own skill
(`.hermes/skills/data-search/SKILL.md`) MUST both pin the call to the terminal tool, so a leg told
to "read the technique" cannot be led back to `execute_code`.

WHEN a leg reads either document,
THEN it finds the same tool pin the prompt carries.

#### Scenario: both documents name the terminal and the forbidden route

- **Given** `skills/gather-data.md` and `.hermes/skills/data-search/SKILL.md`
- **When** their scrape sections are read
- **Then** each names the terminal tool, names `execute_code` as keyless, and carries no instruction
  that tells the agent to scrape from `execute_code`
- **Test:** `tests/test_search_key.py::test_the_written_procedure_pins_the_same_tool`
