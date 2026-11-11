# Proposal: hardware-is-not-an-engine

Issue: #458 (the same issue; this is the second measured shape, recorded in a comment)

## Why

`#462` (merged `25d4e86`) refuses a manufactured engine name that carries a
**quantization** token. On the same day, a second shape reded the next refresh PR:

```
FAIL: bonsai-2-9b: engine 'Bonsai Oryon' has no repo url in engines registry
```

`Oryon` is **Qualcomm's CPU core**. The name was manufactured from the model plus the
CPU, carries no quant token, and the guard could not see it — so PR #461 went red and
`fix-bot` was dispatched to hand-repair it, which is the loop the guard exists to end.

## What Changes

- **`_HW_SHAPE`** in `update_trending.py`: an engine name carrying a CPU/GPU product
  token is not an engine — `Oryon`, `Snapdragon`, `Ryzen`, `EPYC`, `Xeon`, `Radeon`,
  `GeForce`, `RTX`, `GTX`, `Instinct`, `DGX`, `Strix` (not `strixite`), `Halo`,
  `Apple M<n>`, `M<n> Max/Ultra/Pro`.
- **`fabricated_engine_reason` returns the hardware reason** after the quant one, so the
  loud `[ingest] REFUSED fabricated engine …` line names which token it saw.
- **The pattern is tightened where the first rule was sloppy**: `exl\d+` (not `exl\d*`)
  and an added `q[2-8](?:_[a-z0-9]+)*`, so a REAL engine (`ExLlamaV3`) is never refused
  when the registry is not consulted, while a `Q8_0`-flavoured "engine" is.
- **`AGENTS.md` §4** names the second shape; §8 records both.
- **Tests**: `Bonsai Oryon` refused as hardware; `Q8_0 llama` refused as a quant;
  `strixite`, `ExLlamaV3`, `MLX`, `mlx-serve`, `llama.cpp` never refused (boundaries hold
  in both directions); a registered engine kept; a genuine unregistered engine kept.

## Impact

`scripts/update_trending.py`, `AGENTS.md` (§4 + §8), `tests/test_engine_registry.py`,
`OPENSPEC.md`, this change. No new target, stage, job or image.

## Not covered

- **A blanket "any unregistered engine without a repo is refused" rule is deliberately
  NOT taken here.** It would end every shape at once, but it contradicts AGENTS.md §4's
  "validation keeps failing for a human / fix-bot" for a genuinely new engine. That is a
  design decision for the owner, noted on #458.
- **The prompt is unchanged.** `ENGINE_ASK` already forbids manufacturing a name.
