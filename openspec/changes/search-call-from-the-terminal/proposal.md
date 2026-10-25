# The search leg makes its Firecrawl call from the terminal, never from `execute_code`

**Issue:** [#362](https://github.com/andyholst/trending-local-llms/issues/362)
**Capability:** `bot-agent-run-safety` (same capability as #351/#355/#357/#359)

## Why

Issue #359 made every credential a container receives visible in the agent's **terminal** shell:
`Makefile`'s `AGENT_SHELL_KEYS` list is forwarded as `_HERMES_FORCE_<NAME>`, which Hermes's terminal
env builder unwraps to `<NAME>`. That fix covers ONE tool.

It does not cover `execute_code`. Hermes's `tools/code_execution_env.py::_scrub_child_env` drops
every name carrying a secret substring (`if is_secret_env_name(k): continue`) unless the name is an
`env_passthrough` entry, and it never unwraps `_HERMES_FORCE_`. So a search leg that scraped from
`execute_code` would be **keyless again**, with the same silent `HTTP 401` #359 removed — while
`make`'s pre-flight, which reads the container's own environment, stayed green.

Measured in the bot image (Hermes v0.22.3), through the agent's real `execute_code` tool, with the
parent environment carrying the pipeline's names:

```
$ # execute_code child env
child env credential-shaped names: ['HERMES_RPC_TOKEN']
FORCE names: []
```

and the scrub itself, run for real over a source env holding the pipeline's names (plus their
`_HERMES_FORCE_` forms):

```
$ python3 -c 'from tools.code_execution_env import _scrub_child_env; ...'
SCRUBBED: ["HOME", "PATH"]
kept_credentials: []
```

The prompts never named the tool, so which one a leg used was the model's choice: run 39063620912's
amd leg used `web_extract`/`web_search` instead of a terminal `curl`. A prompt is the repo's only
leverage here — the scrub is Hermes's code, not ours, and `env_passthrough` refuses blocklisted
provider names by design (GHSA-rhgp-j443-p4rf).

## What Changes

- `Makefile`: ONE shared `TOOL_ASK` block — the same shape as `ENGINE_ASK` / `DIM_ASK` — embedded in
  all four `_search-*` prompts. It says the scrape goes through the **terminal tool** (`curl`), names
  `execute_code` as the forbidden route and says WHY (its child is scrubbed of every secret-named
  variable, `_HERMES_FORCE_` included), rules out `web_extract`/`web_search` for the scrape, and
  names the supported Python route (`python3 scripts/update_trending.py --write-raw <backend>`,
  which reads the key in-process).
- `skills/gather-data.md` and `.hermes/skills/data-search/SKILL.md`: the same tool pin, so the
  written procedure and the prompt cannot disagree.
- `tests/test_search_key.py`: the wording is locked — every leg carries the rule from the ONE
  definition, the rule names the terminal, refuses `execute_code` and states the reason; and the
  same assertions are proved RED against `origin/master`'s Makefile (a guard that passes on the old
  code guards nothing, rule 6c).
- `AGENTS.md` §3e (one sentence: the search call is a `terminal` call) and §8's guard row — a
  rulebook behaviour change, so the PR is review-required for that hunk (rule 3c).

## Impact

The four search legs. No data, contract, README or ranking change; no new script, target, job or
image, so `ARCHITECTURE.md` is untouched.

## Not covered

- Wiring a Hermes-supported credential route for `execute_code` itself. The scrub is Hermes's code
  and the sanctioned `_HERMES_FORCE_` unwrap exists only in the terminal env builder; inventing a
  repo-side workaround (writing a key to a file the child could read) would put a credential where
  rule 3d forbids it. If Hermes grows such a route, the prompt rule can be relaxed — the second
  half of the issue's "Done when" — but that is an upstream change, not this one.
- Any other tool that spawns a child process (`browser_*`, `delegate_task`): they are not how a
  search leg scrapes, and pinning them here would widen the change past its acceptance criteria.
