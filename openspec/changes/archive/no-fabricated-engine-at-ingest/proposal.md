# Proposal: no-fabricated-engine-at-ingest

Issue: #458 (filed with the measurement; a comment on it records the decisive evidence)

## Why

`ENGINE_ASK` (`Makefile:131`, added by #379 for #378) tells the search legs, **by
name**, that a model name or a quantization is never an engine:

> tokens like Nvidia/Qwen3.8-Flash-Next-FP4-Local, **NVFP4 or FP4-Local must never
> be written as the engine**

On 2026-10-20 the **metal** leg wrote `"engine": "FP4-Local"` for
`lightbrd.com/bdambrosio/status/2111548404866433346` anyway — the same post that
blocked PR #377 the day before. The instruction is present, correct, and not
sufficient: the model overrides it, and the failure lands as a red refresh PR that
`fix-bot` must hand-repair **every day**, because the post sits inside the rolling
3-day window:

```
FAIL: qwen3.8-flash-next-125b: engine 'FP4-Local' has no repo url in engines registry
```

`master` already carries the same figure correctly as **`vLLM`**, so the raw row is a
duplicate of a real measurement under an invented engine — `merge_engines` keys on
(engine, hardware, quant) and therefore adds a second row instead of updating the
real one.

## What Changes

- **`update_trending.fabricated_engine_reason(engine, model, registry)`** — says why
  a name cannot be an engine, or `None` when it could be. A name is fabricated when
  it is **absent from the engines registry** AND **carries a quantization token**
  (`FP4`, `NVFP4`, `Q8_0`, `AWQ`, `GPTQ`, `GGUF`, `EXL2`, `W4A16`, …) — the only
  provable shape: an engine name never contains one, while a model-name SUBSTRING is
  not proof (`WebLLM` really is an engine and really does appear inside
  `Llama-3.1-8B (WebLLM)`; a substring rule refused that legitimate measurement
  while this change was being written).
- **`refuse_fabricated_engines(model, registry)`** — splits a model's measurements
  into (kept, refused) and carries the **source post** with each refusal.
- **`ingest_raw_snapshots` refuses them as they enter the store**, one loud line per
  row: `[ingest] REFUSED fabricated engine 'FP4-Local' on <model>: <why>; post <url>
  — a t/s with no engine named by the post is not a valid entry (rule 5)`.
- **A genuinely new engine is NOT refused.** `SomeRealServe` (unregistered, no
  repo) still reaches the store and still reds `make validate` for a human — the
  documented behaviour, preserved deliberately.
- **`AGENTS.md` §4 states the rule** and §8 records what goes red. Rule 3c: this
  changes the rulebook, so the issue carries the note and the AGENTS.md diff is
  review-required.
- **Tests** (`tests/test_engine_registry.py`): the measured `FP4-Local` and the
  #378 spelling `NVIDIA FP4-Local` refused; a name taken from the model id refused;
  a registered engine kept; a genuine unregistered engine kept; and the REAL ingest
  end-to-end proving the fabricated row never enters the store, the `vLLM` row
  survives, and `check_model_fields` stops failing that model.

## Impact

`scripts/update_trending.py`, `AGENTS.md` (§4 + §8), `tests/test_engine_registry.py`,
`OPENSPEC.md`, this change. No new target, stage, job or image — the guard runs
inside the ingest every refresh already performs (`make merge-fetch`).

## Not covered

- **The prompt is not weakened or duplicated.** `ENGINE_ASK` stays exactly as it is;
  this is the mechanical half, not a replacement for telling the agent the rule.
- **The already-stored rows are untouched.** No existing measurement is removed
  (rule 3b); only a row arriving in a NEW raw snapshot can be refused.
- **`fix-bot`'s repair of PR #457** is not undone — this change prevents the next
  occurrence, it does not rewrite the open PR.
