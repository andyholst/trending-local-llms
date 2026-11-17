# Proposal: engine-min-version-detector-precision

Issue: #1020

## Why

`_ENGINE_MIN_TEXT` still reads a `<number>` beside a bare engine name as an engine BUILD
whenever the throughput figure is spelled in a shape the #998 lookahead never learned, or the
rate sits on the engine side of the adjacency. #1020 measured the survivor class on the
shipped captures: `qwen2.5-0.5b` "same post: llama.cpp 306.9 tokens/s", `gemma-4-e4b`
"llama.cpp 44.8 tokens/s", `minicpm-v-4.7` "ExLlamaV3 + Hermes Agent",
`qwen3.8-27b-ps5lm-native` "PS5LM, llama.cpp port", `bonsai-2-27b-mac-m4-max` "ternary MLX
weights", `glm-5.3-flash` "TensorFold vs vLLM" — engine NAMES beside throughput figures and
quant descriptions, not build claims. Only `qwen3.8-27b-bonsai-2` ("stock llama.cpp rejects
the format so the PrismML fork ran it") is a genuine build requirement, and it is already
carried by the engine name `llama.cpp (PrismML fork)`. Structuring any of the false shapes
would store a speed or a model name as an engine build (rule 2 fabrication, the #998/#1025
class). The over-match is still live today in three shapes the reader answers as a claim:
`llama.cpp 21.11 t/s` and `llama.cpp 44.8 tokens per second` (the #998 lookahead only reads
`tokens/s`/`tok/s`/`TPS`, not the bare `t/s` or the per-second spelling), and
`345.9 vs llama.cpp's 306.9 tokens/s` — where the rate sits beside the ENGINE name, so the
version-side lookahead never bites and the branch reads the comparison speed `345.9` as a
build. `0.0.3 (C++/CUDA` is the same collision from the other side: `CUDA` inside the
toolchain compound `C++/CUDA` names the implementation language, not an engine the run used.

## What Changes

- `_TPUT_RATE` covers every throughput spelling the posts use: bare `t/s`, `tok[en]s?/s`,
  `…/sec(ond)`, `tokens per second`, plus the existing `TPS` — so a version followed by any
  rate unit stays refused at the token (extends #998, one shared token definition).
- The version→engine adjacency branch refuses a match when the ENGINE name is the side the
  rate sits on (`llama.cpp` immediately followed by `'s <N> <rate>` / `<N> <rate>`): the
  engine name sits beside a throughput figure, so the version the branch matched is a
  comparison speed, not a build (#1020).
- `cuda` inside the `C++/` (or `C/`) compound is refused as the engine word — an
  implementation language, not a run-time engine (#1020; `CUDA 12.4` after a space still
  matches).
- No new detector, no second copy (rule 6d): every consumer still goes through the ONE
  `_ENGINE_MIN_TEXT` wrapped by `engine_min_claim`/`dim_claim`.

## Impact

- `scripts/data_gap_analysis.py` — `_TPUT_RATE`, the adjacency branch, the engine-name
  vocabulary (all inside the ONE detector).
- `tests/test_engine_min_version_ingest.py` — planted fill tests for the #1020 sentences:
  the seven issue-quoted strings fill NOTHING; explicit build phrases still claim.
- `tests/test_data_gap_analysis.py` — real-store readback: the seven candidates stay out of
  the `engine_min_version` ingest classes, and the shipped throughput sentences the candidate
  rows actually carry claim nothing while the PrismML sentence still claims.
- `AGENTS.md` §8 guard rows for the new tests (owed — rule 3c human sign-off, recorded in
  findings.md).

## Not covered

- `engine_min_version` values already in the store (#789 keeps them report-only; rule 3b
  forbids removing them here — a genuine removal is a human decision).
- Whether `llama.cpp (PrismML fork)`-style engine-name identity should also stamp a
  structured `engine_min_version` — that is a data-model decision, not a detector fix.
- Acquiring build sentences the searches never captured (the acquisition half of the same
  dimension — rule 6o queries already ask; only a new search closes it).
