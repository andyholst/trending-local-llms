# live-checks

## ADDED Requirements

### Requirement: A live pre-flight check fails loudly when it cannot run

`make hermes-smoke` and `make model-caps` prove the live path before a 20-minute
search leg. With no `NOUS_API_KEY` they MUST fail with a non-zero exit and a
message naming the variable, what could not be proven and the consequence — never
a green result that checked nothing (AGENTS.md: "a skipped test is a loud FAILURE,
never a silent skip").

WHEN either check runs without `NOUS_API_KEY`, THEN it exits non-zero, names the
missing variable, states what stayed unverified, and never calls the model or the
endpoint.

#### Scenario: the routing smoke fails without a key

- **Given** no `NOUS_API_KEY` in the environment
- **When** `scripts/hermes_smoke.sh` runs
- **Then** it exits non-zero, says `NOUS_API_KEY is not set`, names the `nous-deepseek` alias whose routing could not be proven, is not a `SKIP`, and never calls `hermes`
- **Test:** `tests/test_hermes_smoke.py::test_no_key_fails_loudly`

#### Scenario: the model-caps pre-flight fails without a key

- **Given** no `NOUS_API_KEY` and no `--catalog` file
- **When** `scripts/model_caps_check.py` runs
- **Then** it exits non-zero, says `NOUS_API_KEY is not set`, states that the endpoint cannot be read so the model id, its real `max_completion_tokens` and its `reasoning` support are unverified, and is not a `SKIP`
- **Test:** `tests/test_search_budget.py::test_model_caps_cli`

### Requirement: The opt-out is explicit and never reaches a pipeline

A caller that knowingly runs without a key MAY ask for the old behaviour with one
flag, `LIVE_CHECK_ALLOW_UNCONFIGURED=1`, which reports `NOT CONFIGURED` and exits 0.
It MUST NOT be the default, and no workflow may set it: CI holds the keys, so a
green CI live check always means the live path answered.

WHEN a workflow is read, THEN it contains no `LIVE_CHECK_ALLOW_UNCONFIGURED`.

#### Scenario: the opt-out reports that the check did not run

- **Given** no `NOUS_API_KEY` and `LIVE_CHECK_ALLOW_UNCONFIGURED=1`
- **When** either check runs
- **Then** it exits 0 saying `NOT CONFIGURED` and that the check did NOT run, and never calls the model or the endpoint
- **Test:** `tests/test_hermes_smoke.py::test_no_key_fails_loudly`

#### Scenario: no workflow opts out

- **Given** every file in `.github/workflows/`
- **When** they are read for the flag
- **Then** none of them sets `LIVE_CHECK_ALLOW_UNCONFIGURED`
- **Test:** `tests/test_hermes_smoke.py::test_ci_never_opts_out_of_the_live_checks`
