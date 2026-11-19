# fleet-model-chain

## ADDED Requirements

### Requirement: The fleet model chain has ONE source and one order

Every Hermes fleet lane derived from the tree (`agents/tll-*/SOUL.md` → `agents/tll-*/config.yaml`)
MUST run the model chain declared in
`agents/model_chain.json`: the free primary FIRST, the free fallbacks in list order, and the
Makefile-pinned model (`HERMES_MODEL` / `HERMES_ALIAS`) LAST as the paid last resort. A
`make agent-profile-model-render` renders each lane's profile settings and `model.aliases.*` from
that one file, so no lane can hold a model the chain does not name and no operator has to edit a
generated file.

#### Scenario: the shipped chain is free-first and paid-last

- **Given** `agents/model_chain.json` as shipped
- **When** the chain is read
- **Then** exactly one `primary` is first, at least one `fallback` follows it, every
  primary/fallback model ends in `:free`, the single `last_resort` is last, each step carries its
  own alias and a measured `context_window`, and the chain states how its model ids were measured
- **Test:** tests/test_agent_model_chain.py::test_every_free_step_comes_before_the_paid_last_resort

#### Scenario: the rendered configs match the chain and the gate is green

- **Given** this repository with its seven fleet lanes
- **When** `scripts/agent_model_chain.py --check` runs
- **Then** it exits 0, names every lane it verified, and prints the chain order primary-first with
  the last resort last
- **Test:** tests/test_agent_model_chain.py::test_the_shipped_chain_renders_every_lane_config_and_the_gate_is_green

#### Scenario: the render target reproduces the shipped configs from a fresh tree

- **Given** a copy of the tree carrying only the Makefile, the seam, the chain and the lanes'
  `SOUL.md`
- **When** `make agent-profile-model-render` then `make agent-model-chain-check` run in it
- **Then** both exit 0 and every rendered `agents/tll-*/config.yaml` equals the shipped one
  byte-for-byte
- **Test:** tests/test_agent_model_chain.py::test_the_make_target_renders_the_shipped_configs_from_a_fresh_tree

### Requirement: A lane config that drifted from the chain is refused, by name

`make agent-model-chain-check` MUST fail when a `agents/tll-*/config.yaml` no longer matches what
the chain renders, naming the lane's path, the exact line and both spellings (the chain's and the
file's), and telling the author to re-render through `make agent-profile-model-render` rather than
hand-edit. A lane carrying no `config.yaml` at all is refused the same way, and the gate MUST NOT
report a partial pass.

#### Scenario: a hand-edited lane config goes red

- **Given** a scratch tree whose `agents/tll-tester/config.yaml` has its `model.default` changed by
  hand to the paid model
- **When** `scripts/agent_model_chain.py --check` runs
- **Then** it exits 1, names `agents/tll-tester/config.yaml` and the drifted line with both
  spellings, stays silent about the clean lane, and points at `make agent-profile-model-render`
- **Test:** tests/test_agent_model_chain.py::test_a_hand_edited_lane_config_is_refused_and_names_the_lane_and_line

#### Scenario: a lane with no config is refused

- **Given** a scratch tree with a new fleet lane directory that carries `SOUL.md` but no
  `config.yaml`
- **When** the gate runs
- **Then** it exits 1 and names the missing `agents/<lane>/config.yaml`
- **Test:** tests/test_agent_model_chain.py::test_a_lane_without_a_config_is_refused

### Requirement: The chain's shape is the contract, and every way to break it is named

The gate MUST refuse a chain that lost its shape — two `primary` entries, no `fallback`, no
`last_resort`, a paid step ordered before a free one, a primary that is not a `:free` model, or one
alias used twice — and MUST refuse a `last_resort` whose model or alias is not the Makefile's
`HERMES_MODEL` / `HERMES_ALIAS` pin (naming the pin). A `--write` over such a chain MUST refuse to
render rather than emit configs that break the contract.

#### Scenario: each broken shape is refused in words

- **Given** a scratch tree whose `agents/model_chain.json` carries one of the six broken shapes
- **When** `scripts/agent_model_chain.py --check` runs
- **Then** each case exits 1 with a `[model-chain] FAIL` line that states the defect
- **Test:** tests/test_agent_model_chain.py::test_the_chain_shape_is_the_contract_primary_fallbacks_then_last_resort

#### Scenario: the last resort must be the pinned model

- **Given** a scratch tree whose last chain step's `model` (or `alias`) no longer matches the
  Makefile pin
- **When** `--write` and then `--check` run
- **Then** both exit 1 and the refusal names `HERMES_MODEL` / `HERMES_ALIAS`
- **Test:** tests/test_agent_model_chain.py::test_the_last_resort_must_be_the_model_the_makefile_pins

### Requirement: The chain names credentials by NAME only

Neither `agents/model_chain.json` nor any rendered `agents/tll-*/config.yaml` may assign a
credential — no `api_key`, `apikey`, `token`, `authorization` or `password` field, no secret value.
The only permitted spelling is a `key_env` whose value is an environment variable NAME, and the
fleet forwards `NOUS_API_KEY` by name to the container that runs a lane (rule 3e).

#### Scenario: an assigned credential is refused in either file

- **Given** a scratch tree with an `api_key:` line added to a lane config, and the same field added
  to the chain
- **When** the gate runs after each edit
- **Then** both runs exit 1 and name the credential field
- **Test:** tests/test_agent_model_chain.py::test_a_credential_value_or_api_key_field_is_refused_everywhere

### Requirement: An unreadable chain is a loud UNDECIDABLE, never a clean pass

When `agents/model_chain.json` is missing, truncated or unparseable, the gate MUST exit 2 naming
the file it wanted, and `--write` MUST refuse to render, so no run silently proceeds with whatever
models happened to be configured.

#### Scenario: a truncated or missing chain exits 2

- **Given** a scratch tree whose chain JSON is truncated, then deleted
- **When** `--check` (and `--write`) run
- **Then** each exits 2, prints `UNDECIDABLE`, and names `agents/model_chain.json`
- **Test:** tests/test_agent_model_chain.py::test_an_unreadable_chain_is_exit_2_never_a_silent_clean

### Requirement: The gate runs where a fleet change lands

`make agent-model-chain-check` MUST be part of `make lint` — the first gate of `qa-validate`'s
`validate` job and the first check in `scripts/fix_loop.sh` — through an internal recipe
(`_agent-model-chain-check`) that calls the script, and NO workflow may reach the script past the
Makefile (rule 6m). Its test module MUST be discovered by `make test`.

#### Scenario: the wiring is asserted, and removing it is red

- **Given** this repository's Makefile, `scripts/fix_loop.sh`, `.github/workflows/*.yml` and this
  test module
- **When** `test_the_gate_is_wired_where_it_bites` runs
- **Then** `make lint`'s recipe names `agent-model-chain-check`, the internal recipe calls the
  script, `qa-validate` runs `make lint`, no workflow names the script directly, and
  `wiring.wired(__file__)` is true
- **Test:** tests/test_agent_model_chain.py::test_the_gate_is_wired_where_it_bites
