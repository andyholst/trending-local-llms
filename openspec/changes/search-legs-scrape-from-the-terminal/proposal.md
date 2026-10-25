# The search legs send the Firecrawl call from the terminal tool

**Issue:** [#362](https://github.com/andyholst/trending-local-llms/issues/362)
**Capability:** `bot-agent-run-safety` (same capability as #351/#355/#357/#359)

## Why

#359 made every credential a container receives visible in the **terminal** tool by forwarding it as
`_HERMES_FORCE_<NAME>`. It explicitly left `execute_code` uncovered, and that gap is real:

- `tools/code_execution_env.py::_scrub_child_env` drops every name carrying a secret substring
  (`KEY`, `TOKEN`, `SECRET`, `AUTH`, `BEARER`, …) unless it is an `env_passthrough` name, and it
  never unwraps `_HERMES_FORCE_` — so `_HERMES_FORCE_FIRECRAWL_API_KEY` is dropped by the same rule.
- `tools/env_passthrough.py::is_env_passthrough` re-applies the provider blocklist on every child
  build and fails closed, so a skill cannot register `FIRECRAWL_API_KEY` either.

A leg that scrapes with `execute_code` (Python `urllib`) is therefore keyless, and the scrape dies
with the silent `HTTP 401` that #359 fixed for `curl`. The four `_search-*` prompts said only
"POST … with header", never which tool to make the call from, so the tool was the agent's choice.

## What Changes

- `Makefile`: ONE `SCRAPE_ASK` definition (like `ENGINE_ASK` / `DIM_ASK`) stating that every
  Firecrawl call is made from the **terminal** tool — `curl`, or a helper run through the terminal,
  or `python3 scripts/update_trending.py`, which reads the key in its own process — and never from
  `execute_code`, because Hermes scrubs every secret-substring variable out of that child. All four
  `_search-*` prompts embed `$(SCRAPE_ASK)`; no leg keeps a copy.
- `tests/test_search_key.py`: two guards in `make test` — every leg's prompt carries the pin, and
  the pin has exactly one definition (no divergent copy, no double quote inside `hermes -z "…"`).
- `AGENTS.md` §8: the `tests/test_search_key.py` row names the new guard (rule 6c).

## Impact

The search legs' scrape route is pinned to the tool that can actually see the key. No data,
contract, README or architecture change: no new target, script, job or image.

## Not covered

- Wiring `execute_code` itself: Hermes offers no sanctioned route for a blocklisted provider
  credential in that child (`env_passthrough` refuses it by design, GHSA-rhgp-j443-p4rf), so the
  prompt pin is the fix the issue's own "Done when" names first.
- `skills/gather-data.md` / `.hermes/skills/data-search/SKILL.md`: they describe the scrape but do
  not repeat the tool pin (one definition, in the Makefile, is deliberate) — reported in
  `findings.md`.
