# fleet-model-chain

## ADDED Requirements

### Requirement: The free tier is refreshed from a LIVE read on the weekly cadence

`make free-model-refresh` (`scripts/free_model_refresh.py`) MUST read `GET <chain.base_url>/models`
with the credential the chain names, by NAME only, and update ONLY the free steps of
`agents/model_chain.json`: every surviving `:free` id keeps its order and alias, every new `:free`
id appends as a fallback with a deterministic unique alias and its REAL `context_length`, every
retired id drops, a retired primary hands over to the first survivor, and a surviving model's
`context_window` follows the live read. The `local_fallback` tier and the paid `last_resort` MUST
survive byte-untouched. The read MUST be recorded in `measured.at/how` plus an additive
`refresh_history` row. An unchanged live set MUST write nothing. The refresh rides `refresh-bot`'s
existing cron as a deterministic job (rule 6t: the ONLY scheduled pipeline) and lands any change
through `make keeper-pr` — never a direct push, never a model call.

#### Scenario: a new free model enters with its live context and the non-free tiers survive

- **Given** a scratch chain pointed at a real local HTTP server whose payload adds one `:free` id
- **When** the real refresh script runs with the credential present by name
- **Then** the id appends as a fallback with the payload's `context_length` and a generated unique
  alias, the primary stays first, the local tier and paid pin are unchanged, and `measured` records
  the read with the addition in `refresh_history`
- **Test:** tests/test_free_model_refresh.py::test_a_new_free_model_is_appended_with_its_live_context_and_the_non_free_tiers_survive

#### Scenario: a retired free model drops and a retired primary hands over

- **Given** a live payload missing the chain's primary free id
- **When** the refresh runs
- **Then** the retired id is gone, the first survivor becomes primary, the retirement is announced
  and recorded, and the paid pin stays LAST
- **Test:** tests/test_free_model_refresh.py::test_a_retired_free_model_drops_and_a_retired_primary_hands_over

#### Scenario: an unchanged set is a byte-identical no-op and a context drift follows the read

- **Given** a live payload equal to the chain's free set (then one with a drifted context)
- **When** the refresh runs
- **Then** the equal set writes nothing and says `no change`; the drifted context updates to the
  live value
- **Test:** tests/test_free_model_refresh.py::test_an_unchanged_live_set_writes_nothing
- **Test:** tests/test_free_model_refresh.py::test_a_context_drift_follows_the_live_read

### Requirement: A refresh that cannot prove its read refuses loudly and writes nothing

An absent credential, a failed/unreachable/unparseable read, or a free id without a usable
`context_length` MUST exit 2 (`UNDECIDABLE`/`REFUSED`, naming the variable or the defect) with the
chain file byte-untouched. A live set carrying NO `:free` model MUST exit 1 refused — the refresh
may not empty the free tier and break the chain's own gate. `--dry-run` MUST plan without writing.

#### Scenario: every unreadable shape is a loud refusal with no write

- **Given** a scratch chain and (a) no credential in the environment, (b) a server answering 500,
  (c) an unreachable endpoint, (d) a payload with no free model, (e) a free id without context
- **When** the refresh runs in each case
- **Then** (a)–(c) and (e) exit 2 naming the variable/defect, (d) exits 1 refused, and the chain
  file is byte-identical in every case; no credential value is printed
- **Test:** tests/test_free_model_refresh.py::test_an_absent_credential_or_a_failed_read_is_exit_2_and_writes_nothing
- **Test:** tests/test_free_model_refresh.py::test_a_live_set_with_no_free_model_or_no_context_is_refused

#### Scenario: a dry run plans, and the refreshed chain satisfies the real gate

- **Given** a scratch chain pointed at a local server adding one free id
- **When** `--dry-run` runs, then `--write`, then the shipped remote endpoint is restored
- **Then** the dry run writes nothing, and the refreshed chain passes the REAL offline
  `agent_model_chain` gate (shape, Makefile pins, credential NAMES)
- **Test:** tests/test_free_model_refresh.py::test_a_dry_run_plans_without_writing_and_the_refreshed_chain_passes_the_real_gate

### Requirement: The refresh lands as a keeper PR and is wired where it bites

The keeper body (`--pr-body`, `make free-model-refresh-pr-body`) MUST be composed from the chain's
own last `refresh_history` row, carry NO closing keyword, and ref the refresh issue. The Makefile
MUST define the internal recipe + public target, and `refresh-bot.yml` — the ONLY scheduled
pipeline (rule 6t) — MUST run `make free-model-refresh` and land changes through `make keeper-pr`
on the `ci/free-model-refresh` prefix; no other workflow may reach the script.

#### Scenario: the keeper body records the read and closes nothing

- **Given** a scratch chain refreshed with one added free id
- **When** `--pr-body` runs with `RUN_URL` set
- **Then** the body names the added id and the run URL, refs #1195, and carries no `closes`/`fixes`
  keyword
- **Test:** tests/test_free_model_refresh.py::test_the_pr_body_is_a_keeper_with_no_closing_keyword

#### Scenario: the wiring is asserted, and removing it is red

- **Given** this repository's Makefile and `.github/workflows/`
- **When** `test_the_seam_is_wired_where_it_bites` runs
- **Then** the recipe + target exist, refresh-bot runs `make free-model-refresh` and `keeper-pr`
  on `ci/free-model-refresh`, no other workflow names the script, and `wiring.wired(__file__)` is
  true
- **Test:** tests/test_free_model_refresh.py::test_the_seam_is_wired_where_it_bites
