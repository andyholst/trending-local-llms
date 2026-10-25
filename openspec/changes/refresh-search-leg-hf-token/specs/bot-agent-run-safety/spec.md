# bot-agent-run-safety

## ADDED Requirements

### Requirement: A search leg receives every credential its work needs, and proves it before the agent starts

The refresh `search` job MUST set every credential the search agent's shell is expected to use,
and its pre-flight (`_search-preflight`) MUST prove the AGENT's shell can see each of them
through Hermes's real terminal environment. A leg is not allowed to start on a credential that is
missing from the container or EMPTY in the agent's shell: the check fails loudly (exit 2), names
the variable and prints no value.

The Hugging Face token is one of those credentials: the legs record an HF link for every model
(rule 5b), and an unauthenticated `huggingface.co` API call is rate-limited, so a gated repo reads
as missing.

When the refresh `search` job runs, the job env SHALL carry `HF_TOKEN` from the repository secret
alongside the Firecrawl and Nous credentials.

#### Scenario: the search job forwards the Hugging Face token by name

- **Given** `.github/workflows/refresh-bot.yml` and the Makefile's one `AGENT_SHELL_KEYS` list
- **When** the `search` job's `env` is read
- **Then** it SHALL set `HF_TOKEN` from `secrets.HF_TOKEN`, and every credential that list
  carries and the leg needs SHALL be set there too (never a value, always the secret reference)
- **Test:** `tests/test_workflows.py::test_the_refresh_search_job_forwards_every_credential_its_leg_uses`

#### Scenario: a rotated or dropped token fails before the agent runs

- **Given** a search leg whose container or agent shell cannot see `HF_TOKEN`
- **When** `_search-preflight` runs
- **Then** `agent-shell-keys-check` SHALL run with both `FIRECRAWL_API_KEY` and `HF_TOKEN`, and
  SHALL exit non-zero naming the missing variable rather than starting the search
- **Test:** `tests/test_agent_shell_keys.py::test_the_check_is_wired_to_a_make_target_ci_runs`

#### Scenario: the pre-flight still proves the Firecrawl key the scrape itself needs

- **Given** the same pre-flight
- **When** it is read
- **Then** `require_env.py FIRECRAWL_API_KEY` and `search-smoke` SHALL still run first, unchanged
- **Test:** `tests/test_search_key.py::test_every_public_leg_checks_the_key_before_the_agent`
