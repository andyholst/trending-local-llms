# bot-agent-run-safety

## ADDED Requirements

### Requirement: Every search leg makes the Firecrawl call from the terminal tool

Hermes strips provider credentials from its terminal tool and scrubs every secret-substring name out
of an `execute_code` child, so the ONE tool a search leg can authenticate from is the terminal. Each
`_search-<backend>` prompt MUST say so: the Firecrawl call is made from the terminal tool (`curl`, a
helper run through the terminal, or `python3 scripts/update_trending.py`), never from
`execute_code`, and it MUST name the reason — a keyless child sends an empty `Authorization` header
and the query dies with `HTTP 401` while the key is set in the shell.

WHEN a search leg's prompt is built,
THEN it tells the agent to make the Firecrawl call from the terminal tool and never from
`execute_code`, naming the empty-header failure.

#### Scenario: every leg's prompt carries the tool pin

- **Given** the repository's `Makefile`
- **When** the four `_search-<backend>` recipes are read
- **Then** each one names the terminal tool, forbids `execute_code`, and names the empty-Bearer
  `HTTP 401` it causes
- **Test:** `tests/test_search_key.py::test_every_leg_prompt_pins_the_tool_the_key_reaches`

#### Scenario: the pin has exactly one definition

- **Given** the repository's `Makefile`
- **When** `SCRAPE_ASK` and the four legs are read
- **Then** `SCRAPE_ASK` is defined once, every leg embeds `$(SCRAPE_ASK)`, no leg keeps a second
  copy of the sentence, and the definition carries no double quote (it lives inside
  `hermes -z "…"`)
- **Test:** `tests/test_search_key.py::test_the_tool_pin_has_exactly_one_definition`

### Requirement: A prompt's tool pin is a prompt the shell can carry

The pin is embedded in a `hermes -z "…"` string, so it MUST stay free of the characters that would
close that string or expand a value, and it MUST NOT carry the credential's value in any spelling.

WHEN the pin is added to a leg's prompt,
THEN the prompt still parses as one `hermes -z` command and carries only the variable NAME.

#### Scenario: the prompts stay valid and value-free

- **Given** the `Makefile` with the pin in all four legs
- **When** `tests/test_hermes_prompts.py` validates every prompt and the escaping test expands the
  recipe
- **Then** every prompt is valid, one logical command, and the sentinel value never appears
- **Test:** `tests/test_hermes_prompts.py::test_makefile_prompts_valid`
