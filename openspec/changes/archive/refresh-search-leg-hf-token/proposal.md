# The refresh search legs receive the Hugging Face token they verify links with

**Issue:** [#363](https://github.com/andyholst/trending-local-llms/issues/363)
**Capability:** `bot-agent-run-safety` (same capability as #351/#355/#357/#359)

## Why

`refresh-bot.yml`'s `search` job (`:283-287`) set `NOUS_API_KEY`, `FIRECRAWL_API_KEY` and
`TYPESAFE_API_KEY`, and not `HF_TOKEN`, which the `aggregate` job (`:357-362`) does set.
`AGENT_SHELL_KEYS` forwards a credential **only when it is set in the job**, so the search
agent's shell never had `HF_TOKEN`, even though the run wrappers forward the name.

The legs are asked for a Hugging Face link for every model (AGENTS.md rule 5b, `skills/
gather-data.md` §3/§5). An unauthenticated `huggingface.co` API call is rate-limited and
answers `401`/`429` for a gated repo, so the canonical id reads as missing and the leg writes
the marketing name — the dead-link class #333 fixed at ingest, reintroduced one level up where
no ingest guard can see it.

The pre-flight that proves the agent's shell can see a credential (`_search-preflight` →
`agent-shell-keys-check`) narrowed to `FIRECRAWL_API_KEY` alone, so even after the token is
forwarded nothing would have failed had it been dropped again.

## What Changes

- `.github/workflows/refresh-bot.yml`: the `search` job env gains
  `HF_TOKEN: ${{ secrets.HF_TOKEN }}` (by NAME only — the value arrives at run time, rule 3e),
  with the comment that says why the leg needs it.
- `Makefile`: `_search-preflight` proves BOTH credentials the leg uses —
  `agent-shell-keys-check AGENT_SHELL_CHECK_KEYS="FIRECRAWL_API_KEY HF_TOKEN"` — so a leg whose
  container or agent shell lacks either fails loudly BEFORE the 20-minute agent run
  (`scripts/agent_shell_keys_check.py` exits 2, naming the variable, printing no value).
  The `AGENT_SHELL_CHECK_KEYS` comment no longer states "the search job is given no HF_TOKEN"
  (it now is), and the `_search-preflight` comment names the HF verification.
- `skills/gather-data.md` §5: the leg's shell carries `HF_TOKEN`, so an HF API verification is
  authenticated; use it by NAME, never print it.
- `tests/test_workflows.py`: a new guard, `test_the_refresh_search_job_forwards_every_credential
  _its_leg_uses`, derives the credentials the search leg's prompt mentions from the Makefile's
  `AGENT_SHELL_KEYS` and requires the job env to set each one — plus the pre-flight to prove
  them. Verified RED against `origin/master`'s `refresh-bot.yml`.
- `tests/test_agent_shell_keys.py`: the pre-flight wiring assertion now requires both names.
- `AGENTS.md` §8 row (the guard catalogue) and §4's local `make refresh` command (which would
  fail without the token once the pre-flight requires it); `ARCHITECTURE.md`'s search-target and
  `agent-shell-keys-check` rows.

## Impact

The refresh search legs can authenticate a Hugging Face lookup, and a job that stops forwarding
the token is caught by a green-then-red PR instead of silently degrading links. No data, README,
contract or scoring change; no new make target, stage, job or image.

## Not covered

- Which verification method a leg chooses (web search vs the HF API) is unchanged; this change
  only makes the credential reachable and proven.
- `execute_code` children still see no credentials (Hermes scrubs them, #362); the prompts
  require the terminal, so that stays a separate concern.
- `data/raw` snapshots already written with an unverified link are not re-verified here — the
  link validator (`make validate`) keeps failing them for a human / fix-bot.
