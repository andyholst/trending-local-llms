# Proposal: pin-flash-1017-snapshot

Issue: #447 (filed first, with the measurement)

## Why

`HERMES_MODEL := deepseek/deepseek-v4.1-flash` is a **floating alias**. The
endpoint serves both spellings side by side:

```
$ curl -s https://inference-api.nousresearch.com/v1/models | jq -r '.data[].id' | grep v4.1-flash
deepseek/deepseek-v4.1-flash-1017
deepseek/deepseek-v4.1-flash:batch
deepseek/deepseek-v4.1-flash:US
deepseek/deepseek-v4.1-flash
```

`-1017` is the dated snapshot; the undated id is a pointer the provider may
repoint at a newer build. Every artifact that records this repo's pin — the
image tag, `HERMES_MAX_TOKENS`, the AGENTS.md budget paragraph, the skill, the
search prompts — then describes a model the pipeline no longer talks to, and a
change in model quality lands **with no commit and no red check**. That is the
install-URL defect (#218) one layer down: the pin is a name, not a version.

This is also a correctness issue for the repo's own claim: `make model-caps`
checks the model's declared `max_completion_tokens` against `HERMES_MAX_TOKENS`,
and the 65,536 figure was measured on the previous family pin. Against a dated
sku the measurement belongs to a fixed build instead of a moving target.

## What Changes

- **`HERMES_MODEL := deepseek/deepseek-v4.1-flash-1017`** — the dated snapshot,
  so the alias the bots call (`nous-deepseek`) resolves to a fixed build.
- **`AGENTS.md` §4 states the rule** — the pin is the DATED snapshot, never the
  floating family alias, and why; §6's prose names the new pin.
- **`skills/gather-data.md`** and **`refresh-bot.yml`'s PR body** name the new
  pin, so the run's own text never quotes a model the pipeline does not run.
- **A regression guard**: `tests/test_search_budget.py` now refuses a
  `HERMES_MODEL` that equals the floating alias, so a future bump back to it
  goes red locally instead of silently at run time (the existing stale-pin scan
  only knew about the RETIRED `v4-flash-0731` string).
- **`tests/test_install_hermes_ci.py`'s stub hermes** answers the new pin, which
  is what `_hermes-alias-check` compares against (rule 6b: the fixture moves with
  the pin).

## Impact

`Makefile` (one variable), `AGENTS.md` (§4 + §6), `skills/gather-data.md`,
`.github/workflows/refresh-bot.yml` (PR body prose only), two test modules,
`OPENSPEC.md` (regenerated), this change. No new target, stage, job or image,
and no credential changes: `key_env` stays `NOUS_API_KEY`.

## Not covered

- **The live cap is not re-measured here.** `deepseek/deepseek-v4.1-flash-1017`
  declares no `max_completion_tokens`, exactly like the alias did, so
  `HERMES_MAX_TOKENS := 65536` stays conservative and `make model-caps` proves
  it on the PR (the `live-smoke` job).
- **`#218` itself** — pinning the *install URL* to a version — is separate work;
  this change pins the MODEL, not the agent binary.
