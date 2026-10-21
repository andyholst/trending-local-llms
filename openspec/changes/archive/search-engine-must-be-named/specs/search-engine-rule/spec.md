# search-engine-rule

## ADDED Requirements

### Requirement: The engine rule has one definition every leg expands

The search prompts MUST take the engine rule from ONE `Makefile` definition
(`ENGINE_ASK`), expanded as `$(ENGINE_ASK)` in every search leg, so no leg can
carry a divergent copy of it. Four byte-identical inline copies are a drift, not a
convenience.

WHEN a search leg's prompt is composed,
THEN its engine rule is the shared definition and no leg holds a second copy.

#### Scenario: every leg expands the shared definition

- **Given** the `Makefile` and the four search legs
- **When** the guard reads each leg's recipe
- **Then** each recipe expands `$(ENGINE_ASK)` and none carries the old buried engine sentence
- **Test:** `tests/test_hermes_prompts.py::test_every_search_leg_asks_for_the_engine_rule_from_one_definition`

#### Scenario: the definition is safely embeddable

- **Given** the `ENGINE_ASK` definition
- **When** it is embedded in a leg's `hermes -z "…"` command
- **Then** it carries no double quote, so the prompt string cannot be closed early
- **Test:** `tests/test_hermes_prompts.py::test_every_search_leg_asks_for_the_engine_rule_from_one_definition`

### Requirement: An engine must be one the post names, never a model or a quant

The engine rule MUST require that the `engine` field name an inference runtime or
server the post ACTUALLY NAMES. It MUST state that a model name, a vendor name or a
quantization is never an engine — the tokens of the measured post included — and
that a post which states a t/s but names no engine yields NO measurement, because a
t/s with no engine is not a valid entry and a manufactured engine has no repo to
register, which reds the whole refresh.

WHEN a captured post states a t/s without naming an engine, or names only a model
or a quant,
THEN the rule forbids storing that figure under an invented engine name.

#### Scenario: the rule names the prohibition and the fallback

- **Given** the `ENGINE_ASK` definition
- **When** the guard reads it
- **Then** it requires the engine the post ACTUALLY NAMES, states a model/vendor/quantization is NEVER an engine, names the measured tokens, and says a post naming no engine means SKIP that measurement because a t/s with no engine is not a valid entry
- **Test:** `tests/test_hermes_prompts.py::test_every_search_leg_asks_for_the_engine_rule_from_one_definition`

### Requirement: Extracting the rule must not drop what it already said

The one definition MUST keep every rule the inline copies carried: engine names as
registered in `data/models.json`, a model-specific fork recorded as its fork name,
`engine_repo` for an engine not yet registered, one verified web search when the
post names the engine but links no repo, and that a URL is never invented.

WHEN the engine rule is read by a leg,
THEN it still carries registration, fork, `engine_repo`, verified-search and
never-invent-a-URL.

#### Scenario: the pre-existing rules survive the extraction

- **Given** the `ENGINE_ASK` definition
- **When** the guard reads it
- **Then** all five pre-existing rules are present
- **Test:** `tests/test_hermes_prompts.py::test_every_search_leg_asks_for_the_engine_rule_from_one_definition`
