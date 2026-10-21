# Proposal: search-engine-must-be-named

Issue: #378
PR: #379

## Why

The search legs fabricated an **engine** out of a **model name**. The post behind
PR #377's only validation failure names no engine at all:

> Nvidia/Qwen3.8-Flash-Next-FP4-Local is Amazing! RTX6000 pro: Median 191 /
> 90th percentile 271 / Peak 328. Older Docker container of Qwen3.8-Flash-Next
> NVFp4, same workload 85–88

`Nvidia/Qwen3.8-Flash-Next-FP4-Local` is the **model**, `NVFP4` is the **quant**,
"Docker container" is how it shipped — so the capture stored
`{"engine": "NVIDIA FP4-Local", "engine_repo": null, "tps": "191", …}`, an engine
manufactured from the model name to fill the contract's required `engine` field.
`make validate` then rejected the PR:

    FAIL: qwen3.8-flash-next-125b: engine 'NVIDIA FP4-Local' has no repo url in engines registry

An engine with no repo can never be auto-registered (§4), so the figure is a
fabrication (rule 2) and breaks rule 5 ("t/s is always per engine") — and the whole
refresh PR is red for it.

## What Changes

- **One shared `ENGINE_ASK`, used by all four legs.** The engine rule was four
  byte-identical inline copies (the same shape `DIM_ASK` was extracted from under
  issue #167); it is now ONE `Makefile` definition expanded as `$(ENGINE_ASK)` in
  `_search-nvidia`, `_search-metal`, `_search-cpu` and `_search-amd`, so the legs
  cannot drift from it.
- **The rule now forbids manufacturing an engine**, and says what to do instead:
  the engine must be the one the post ACTUALLY NAMES; a model name, a vendor name
  or a quantization is never an engine (the tokens from the measured post are named
  explicitly); and a post that states a t/s but names no engine yields **no
  measurement** — a t/s with no engine is not a valid entry.
- **The rule it already carried is kept** verbatim in the one definition: engine
  names as registered, model-specific forks as their fork name, `engine_repo` for
  an unregistered engine, one verified web search when the post links no repo,
  never an invented URL.
- **A guard locks it**: `tests/test_hermes_prompts.py` gains
  `test_every_search_leg_asks_for_the_engine_rule_from_one_definition`, which
  asserts the definition exists exactly once, carries both the new prohibitions and
  the old rules, carries no double quote (it lives inside `hermes -z "…"`), and
  that every leg expands `$(ENGINE_ASK)` with no leftover copy of the old sentence.

## Impact

`Makefile` (`ENGINE_ASK` + the four legs), `tests/test_hermes_prompts.py` (the new
guard), `tests/test_engine_aliases.py` and `tests/test_engine_registry.py` (their
prompt assertions now read the one definition and check each leg expands it, in the
same change — rule 6b), the OpenSpec change and the regenerated `OPENSPEC.md` index.

No `data/**` file changes and no rendered table changes: this is the gathering
rule, not the store. No make target, stage, pipeline job, image or script is added
or renamed, so `ARCHITECTURE.md` is unchanged (rule 6h) — verified by
`make architecture-check`.

## Not covered

- **Correcting PR #377's data.** The fabricated measurement is already captured on
  that branch; this change stops the next capture from producing one. The PR's own
  repair (fix-bot / a human) is separate from the rule that caused it (rule 6g).
- **An ingest-side guard that drops a measurement whose engine is not a registered
  engine and has no repo.** Deleting a measurement is loss (§3b) and the engine may
  be real but unrepo'd; §4 already says such a figure keeps failing for a human /
  fix-bot, which is what happened here.
- **The `AGENTS.md` §8 guard row for this test.** `AGENTS.md` is a protected
  agent-instruction file and this run has no approver (rule 3c); the exact row is
  spelled out in `findings.md`.
