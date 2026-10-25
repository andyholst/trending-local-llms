# The search legs make their Firecrawl call from the terminal, never from execute_code

Issue: #362 — tech-debt: execute_code children cannot see any credential, and the force form does not apply there
Capability: `bot-agent-run-safety` (same capability as #351/#355/#357/#359)

## Why

#359 made every credential a container receives visible in the **agent's shell**, by forwarding it as
`_HERMES_FORCE_<NAME>`, which Hermes's terminal environment builder unwraps to `<NAME>`. That fix is
real and proved (`make agent-shell-keys-check`), and it covers exactly one tool.

The `execute_code` child is a different environment, and it has no such route.
`tools/code_execution_env.py::_scrub_child_env` drops every name that contains a secret substring
(`KEY`, `TOKEN`, `SECRET`, `PASSWORD`, `CREDENTIAL`, `AUTH`, `BEARER`, `COOKIE` …) unless it is an
`env_passthrough` name — and `env_passthrough` refuses a blocklisted provider name. It never unwraps
`_HERMES_FORCE_` (the forced name contains `KEY`, so it is dropped by the same rule). So a leg that
scraped with `execute_code` (Python `urllib`) instead of the terminal (`curl`) would read an EMPTY
`FIRECRAWL_API_KEY` and send an empty Bearer — the measured #359 defect, one tool over.

Nothing in the leg's contract said which tool to use. The four `_search-*` prompts said "POST … with
header" and pinned no tool; `skills/gather-data.md` §1 told the agent to reach the mirror "via
`web_extract`"; the preloaded `data-search` skill named no tool either. Run 39063620912 (the amd leg)
used `web_extract`/`web_search`, which is the shape the prompt invited.

## What Changes

- `Makefile`: ONE `TOOL_ASK` definition — the same one-string-per-rule shape as `ENGINE_ASK` and
  `DIM_ASK` — naming the **terminal** tool (`curl`) as the only way to make the Firecrawl scrape,
  naming `execute_code` / `web_extract` / `web_search` as forbidden, and giving the reason
  (`_scrub_child_env` drops the key; `_HERMES_FORCE_` is not unwrapped there). The alternative route
  it offers is `python3 scripts/update_trending.py`, which reads the key in-process. Every
  `_search-<backend>` prompt embeds it, so no leg can drift.
- `.hermes/skills/data-search/SKILL.md` (the contract the legs actually preload, issue #549): the
  same rule as a `Rules` bullet, and the header instruction now names the real variable
  (`${FIRECRAWL_API_KEY}`) instead of an asterisk placeholder.
- `skills/gather-data.md` §1: the mirror is reached with the Firecrawl scrape API **from the
  terminal**, not "via `web_extract`" (which is what the guide told the agent, and what run
  39063620912 followed), and a long page is read from a scratch file instead of a `web_extract`
  cache footer that no longer exists on this path.
- `tests/test_search_tool_pinning.py`: locks the wording at four levels — the rule is ONE
  definition, every leg embeds it, no leg prompt instructs a credential-less tool, and the wording
  really reaches the agent (the recipe is expanded by `make -n` and read, never a regex over the
  Makefile), plus both documents say it and the rendered prompt stays inside
  `check_agent_skills.PROMPT_BUDGET`.
- `AGENTS.md` §8 row for the guard (rule 6c).

## Impact

Only the search legs' instructions and their guard. No data, contract, README or pipeline change; no
new make target, script, job or image.

## Not covered

- A Hermes-supported credential route for `execute_code`: this change takes the issue's FIRST
  option (pin the tool + lock the wording). `_scrub_child_env` is Hermes's code, not this repo's,
  and an `env_passthrough` entry for a blocklisted provider name is refused by design.
- The other agent legs (`_fix`, `_implement-issue`, `_review-issue`): they reach the network through
  `make` targets that read a key in-process, and they carry no scrape of their own. Their prompts are
  unchanged.
