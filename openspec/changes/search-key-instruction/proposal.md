# A prompt names the credential's variable, never its value — and a leg without it fails

**Issue:** [#357](https://github.com/andyholst/trending-local-llms/issues/357)
**Capability:** `bot-agent-run-safety` (same capability as #351/#355)

## Why

The four refresh search legs told the agent to authenticate with a variable that does not exist:

```
Authorization: Bearer \$${FI...KEY}
```

Byte-verified: the segment after `Bearer ` is **13 characters**, character classes `\$${AA...AAA}`,
hex `426561726572205c24247b46492e2e2e4b45597d`; `grep -c '\$\${FIRECRAWL_API_KEY}' Makefile` = 0 and
`grep -c '\*\*\*' Makefile` = 0. Present since `0b35b1a` (#15).

The key itself is fine — `gh secret list` shows `FIRECRAWL_API_KEY` (set 2026-09-28), the `search`
job passes it (`refresh-bot.yml:269-271`) and `DOCKER_RUN` forwards `-e FIRECRAWL_API_KEY`, and the
platform's own step listing shows it **masked, not empty** (`FIRECRAWL_API_KEY: ***`, ×41 in run
39063620912). But the header the agent was told to build resolved to nothing:

- every leg failed with `HTTP 401` / "the key is not available";
- the agent then hunted for the key — 30 lines across 76 runs, e.g. "`FIRECRAWL_API_KEY` is unset
  (verified `${#FIRECRAWL_API_KEY}` = 0)", "`/root/.hermes/.env` … only `# FIRECRAWL_API_KEY=***` —
  commented out";
- and while hunting it wrote `export FIRECRAWL_API_KEY=<what to put here>` into a **public log** —
  the placeholder shape #355 exists to contain.

Nothing was exposed (all 76 refresh + 29 other runs scanned per line: 0 credential shapes, 42
`NAME=` hits all placeholder prose, every `***` classified) — so nothing rotates. This is the
opposite failure of #355: not a leak, but an agent pushed into talking about keys.

## What Changes

- **`Makefile`** — all four `_search-*` prompts name the variable as an INSTRUCTION, escaped so it
  reaches the agent literally: `header 'Authorization: Bearer \$${FIRECRAWL_API_KEY}' - \$${FIRECRAWL_API_KEY}
  is the NAME of the environment variable that holds the key: read its VALUE from the environment
  and put it in that header, and never print, echo or write the value anywhere`.
- **`scripts/require_env.py`** + **`_search-preflight`** — every public search target (`search-nvidia`,
  `search-metal`, `search-cpu`, `search-amd`, `search`) checks the credential BEFORE the agent starts:
  `require_env.py` fails (exit 2) when the name is missing **or empty** (the shape a missing GitHub
  secret takes at run time), naming the variable and how to set it and never printing a value; then
  the EXISTING `search-smoke BACKEND=<b>` proves the key is accepted and the mirror answers — one
  implementation, the same one `live-smoke` runs (rule 6d).
- **`skills/gather-data.md`** — the agent learns the header from the environment, never printed, and
  that a `401` is a BLOCKER to report rather than a reason to search the filesystem.
- **`tests/test_search_key.py`** (new) — the four prompts name the real variable and carry no elided
  form; the escaping asserted **at the shell level** (a fixture recipe run through `make` with the
  key set: the prompt must contain the NAME and must not contain the VALUE — a backslash too few
  would expand the secret into the agent's prompt and the log); every public leg runs the pre-flight;
  `require_env.py` passes on set, fails on missing AND on empty, never prints the value, and its
  `--allow-unconfigured` opt-out reports NOT CONFIGURED and never reaches a workflow.
- `AGENTS.md` §3d/§8, `ARCHITECTURE.md`, `OPENSPEC.md`.

## Impact

A search leg with no usable credential fails loudly at the pre-flight instead of running keyless and
letting the agent narrate its search; a leg that runs authenticates with the variable it was always
meant to use. No data, README or contract change.

## Not covered

- Rotating anything: measured clean, nothing to rotate.
- The agent's own misreport ("verified `${#FIRECRAWL_API_KEY}` = 0" while the variable was set):
  addressed by the prompt fix and the pre-flight, which remove the reason to investigate the key at
  all; a behavioural guarantee on the model's self-reports is out of scope.
