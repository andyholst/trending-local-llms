# bot-agent-run-safety

## ADDED Requirements

### Requirement: A prompt names the credential's environment variable, never its value

An instruction that has the agent authenticate MUST name the environment variable that holds the
credential, escaped so the text reaches the agent as a NAME and cannot expand into the value. A
prompt that names a variable which does not exist leaves the agent unable to authenticate while
holding the credential — and sends it looking for the key in the open.

WHEN a prompt tells the agent to build an authenticated request,
THEN it names the environment variable, and the escaping is proven at the shell level so the value cannot appear in the prompt.

#### Scenario: the four legs name the real variable

- **Given** the repository's `Makefile`
- **Then** every `_search-*` prompt contains `Bearer \$${FIRECRAWL_API_KEY}` and no elided form (`FI...KEY`)
- **Test:** `tests/test_search_key.py::test_every_leg_prompt_names_the_variable_it_must_use`

#### Scenario: the escaping cannot expand the secret into the prompt

- **Given** a recipe with the same escaping, run through `make` with the variable set to a sentinel
- **Then** the text the agent receives contains the NAME and not the VALUE
- **Test:** `tests/test_search_key.py::test_the_escaping_keeps_the_value_out_of_the_prompt`

### Requirement: A leg without a usable credential fails loudly before the agent starts

A public target that runs the agent MUST verify the credential it needs before the agent runs, and
MUST fail (non-zero, naming the variable) when it is missing **or empty** — the shape a missing
GitHub secret takes at run time. Running keyless and narrating is the defect: it puts an agent's
account of the key into a public log.

WHEN a search leg starts,
THEN it requires its credential by name and proves the backend answers, or it stops.

#### Scenario: a missing variable fails loudly and names it

- **Given** no `FIRECRAWL_API_KEY` in the environment
- **Then** `require_env.py` exits 2, names the variable, and says how to set the secret
- **Test:** `tests/test_search_key.py::test_a_missing_variable_fails_loudly`

#### Scenario: an empty variable counts as missing

- **Given** `FIRECRAWL_API_KEY=` (empty)
- **Then** the check exits 2
- **Test:** `tests/test_search_key.py::test_an_empty_variable_counts_as_missing`

#### Scenario: the value is never printed

- **Given** a set credential
- **Then** the check's output names the variable and never the value
- **Test:** `tests/test_search_key.py::test_a_set_variable_passes_and_the_value_is_never_printed`

#### Scenario: every public leg runs the pre-flight, and the opt-out never reaches CI

- **Given** the four `search-<backend>` targets and `search`
- **Then** each runs `_search-preflight` first, and `--allow-unconfigured` appears in no workflow
- **Test:** `tests/test_search_key.py::test_every_public_leg_checks_the_key_before_the_agent`
