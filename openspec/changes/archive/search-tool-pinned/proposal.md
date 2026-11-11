# A search prompt pins the TOOL that can see the key — never `execute_code`

**Issue:** [#362](https://github.com/andyholst/trending-local-llms/issues/362)
**Capability:** `bot-agent-run-safety` (same capability as #351/#355/#357/#359)

## Why

#359 made the agent's **terminal** see the container's credentials (`_HERMES_FORCE_<NAME>`, unwrapped
by Hermes's terminal env builder). The search prompts never said *which tool* to make the Firecrawl
call from, so the fix holds only while the agent happens to pick the terminal.

It does not hold anywhere else. Measured in this tree, through Hermes's own code
(`tools/code_execution_env.py::_scrub_child_env`, run under Hermes's interpreter with the key set):

```
FIRECRAWL_API_KEY                 DROPPED
_HERMES_FORCE_FIRECRAWL_API_KEY   DROPPED
HF_TOKEN                          DROPPED
NOUS_API_KEY                      DROPPED
PATH                              present
is_env_passthrough("FIRECRAWL_API_KEY")               -> False
is_env_passthrough("_HERMES_FORCE_FIRECRAWL_API_KEY") -> False
```

Every name carrying a secret substring is dropped from `execute_code`'s child process, the
`_HERMES_FORCE_` form is **not** unwrapped there, and `env_passthrough` cannot re-allow a blocklisted
provider name. So a leg that scrapes from `execute_code` (Python `urllib`) sends an **empty Bearer**
and gets `HTTP 401` while the key is set — exactly the silent failure #359 removed for `curl`, and
the shape that once pushed an agent into writing `export FIRECRAWL_API_KEY=<what to put here>` into a
public log (#355).

A prompt is the only lever available: Hermes offers no sanctioned route for `execute_code` to inherit
a blocklisted provider credential, so the alternative in the issue ("wire a Hermes-supported route
and prove it with `make agent-shell-keys-check`") has nothing to wire. The fix is to say which tool,
in one place, and lock the wording.

## What Changes

- **`Makefile`** — one new prompt fragment, `SEARCH_TOOL_ASK`, defined next to `ENGINE_ASK` /
  `DIM_ASK`: every Firecrawl call is made from the **terminal** tool (`curl`, or
  `python3 scripts/update_trending.py --fetch`, which reads the key in-process); `execute_code` is
  forbidden by name, with the reason (its child environment is scrubbed, so the request carries an
  empty Bearer and fails `HTTP 401` although the key is set); a `401` stays a BLOCKER to report, never
  a reason to hunt for the key. All four `_search-*` prompts take it as `$(SEARCH_TOOL_ASK)` — one
  definition, no inline copies, no double quote (it lives inside `hermes -z "…"`).
- **`.hermes/skills/data-search/SKILL.md`** — the skill the four legs actually preload carries the
  same rule, so the tool is pinned in the skill as well as the prompt.
- **`skills/gather-data.md`** — §1 says the Firecrawl call is made from the terminal tool and never
  from `execute_code`, and why.
- **`tests/test_search_key.py`** — `test_the_prompts_pin_the_tool_that_can_see_the_key`: the fragment
  is defined exactly once, names the terminal tool, forbids `execute_code`, states the empty-Bearer /
  `HTTP 401` consequence, carries no double quote; every `_search-*` prompt takes it from the
  variable and carries no second copy; the `data-search` skill and `skills/gather-data.md` carry it;
  and the fragment is not merely absent from a prompt that still invites `execute_code`.
- `AGENTS.md` rule 3e + §8 row; `OPENSPEC.md` index.

## Impact

A search leg's scrape now happens in the one child process that can see the credential, so a leg
cannot silently re-introduce the keyless 401 by choosing a different tool. No data, contract, README
or pipeline-wiring change: no new script, target, job or image.

## Not covered

- A Hermes-supported `execute_code` route for blocklisted provider credentials: it does not exist in
  the pinned Hermes (`env_passthrough` refuses the name), so nothing is wired and the alternative in
  the issue is deliberately not taken.
- A behavioural proof inside `make test` that `execute_code` is keyless: that would make the unit
  suite depend on Hermes's source tree, which only the image has; the mechanism is measured above and
  the wording is what the suite locks (the `agent-shell-keys-check` live path keeps proving the
  terminal half).
- `web_extract` / `web_search`: they fetch without a credential at all, so they neither prove nor
  break the key wiring; the documented route for the scrape is unchanged (see `findings.md`).
