# The agent's shell sees every credential a container receives

**Issue:** [#359](https://github.com/andyholst/trending-local-llms/issues/359)
**Capability:** `bot-agent-run-safety` (same capability as #351/#355/#357)

## Why

Every bot's agent runs its commands through Hermes's terminal tool, and Hermes **strips provider
credentials from that shell on purpose**: `FIRECRAWL_API_KEY`, `HF_TOKEN` and the provider keys
(`NOUS_API_KEY` …) are on `tools/environments/local_env_policy.py::_STATIC_PROVIDER_ENV_BLOCKLIST`,
and `env_passthrough` can never re-allow a blocklisted name (GHSA-rhgp-j443-p4rf). The one
sanctioned way through is `_HERMES_FORCE_<NAME>`, which the terminal env builder unwraps to
`<NAME>`.

`DOCKER_RUN` forwarded only the plain names. The key reached the container and Hermes — `make`'s
#357 pre-flight saw it — while the agent's `curl` sent an EMPTY Bearer:

- refresh run 39063620912: the step listing shows `FIRECRAWL_API_KEY: ***` in every search job,
  and the cpu / nvidia / amd legs report `HTTP 401` ("`FIRECRAWL_API_KEY` is unset in the shell,
  absent from `env`"). The same in 38902898149, 38959544994, 39024041477.
- reproduced in the published bot image (Hermes v0.22.0+119), dummy values, through Hermes's real
  `LocalEnvironment.execute`: plain names → agent-shell lengths `NOUS=0 FIRECRAWL=0 HF=0
  TYPESAFE=23`; with `_HERMES_FORCE_<NAME>` → `23 23 23 23`.

## What Changes

- `Makefile`: ONE list `AGENT_SHELL_KEYS` (`NOUS_API_KEY FIRECRAWL_API_KEY HF_TOKEN
  $(NERVE_KEY_ENV)`); on the host make exports `_HERMES_FORCE_<NAME>` from `<NAME>` by reference
  (only for a set key — the value is never on a command line), and `DOCKER_RUN` / `TEST_RUN`
  forward every forced name by NAME (`$(AGENT_SHELL_FORWARD)`). Inside a container nothing is
  re-exported, so the check proves what `docker run` forwarded.
- `scripts/agent_shell_keys_check.py` + `make agent-shell-keys-check`: drives Hermes's real
  terminal environment in the bot image and fails, naming the variable, when a key set in the
  container is empty in the agent's shell. Lengths only, never a value; a key missing from the
  container is a loud exit 2.
- Wired: `qa-validate`'s `live-smoke` (real secrets) and `_search-preflight` (every search leg,
  `FIRECRAWL_API_KEY`), and `tests/test_agent_shell_keys.py` in `make test`.
- `AGENTS.md` §3e sentence + §8 row (rule 3c — review-required), `ARCHITECTURE.md`.

## Impact

Every agent run (search legs, fix, implement, review) gets the credentials it was always meant to
have in its shell. No data, README or contract change.

## Not covered

- `execute_code` children: Hermes blocks every secret-substring name there and the force form does
  not apply; the prompts use the terminal, so this is a finding, not a change here.
- Key rotation: the log audit found no exposed value.
