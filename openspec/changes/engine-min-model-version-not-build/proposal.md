# Proposal: engine-min-model-version-not-build

Issue: #1025

## Why

`_ENGINE_MIN_TEXT` still reads a `<number>` beside an engine word as an engine BUILD even
when the number is the model's own version (`glm-5.3-flash` ← "RED-SNOW-5.3-FLASH-MLX-4bit",
`qwen3.8-27b-ps5lm-native` ← "2-bit Qwen 3.8 27B (PS5LM, llama.cpp port)") or a quant
bit-width (`bonsai-2-27b-mac-m4-max` ← "MLX weights (~7GB), 1.72 bits/weight"). Triage then
re-asks an ingest job to structure a value no post states — the same fabrication class as
#998's throughput over-match, which the throughput lookahead does not cover (no rate unit
follows these numbers).

The sibling over-match #1019 lives in `_STORAGE_TEXT`: "Unsloth IQ4_XS (~14.6GB on disk), 25
layers offloaded" is a weight-file size plus a GPU-layer offload, yet the medium↔offload
proximity reads it as a storage (experts-on-SSD) requirement.

## What Changes

- `_BUILD_VERSION` refuses a version immediately followed by a bit-width unit
  (`bits`, `bits/weight`, `bpw`) — beside `tokens/s` (#998) this is the second rate shape.
- ONE claim reader `data_gap_analysis.engine_min_claim(model, text)` wraps the detector: a
  match whose only version tokens are the model's OWN id/name version tokens is refused.
  The gap scan (`unstructured:engine_min_version`) and the ingest fill
  (`update_trending.fill_engine_min_version`) both go through it — the detector stays ONE
  implementation (rule 6d).
- `_STORAGE_TEXT` refuses `layer`/`layers offload…` (GPU-layer offload) as the offload word,
  and refuses `…GB on disk` (file size) as the storage medium.

## Impact

- `scripts/data_gap_analysis.py` — the two detectors + the claim reader + dimension wiring.
- `scripts/update_trending.py` — the fill goes through `engine_min_claim`.
- `tests/test_engine_min_version_ingest.py`, `tests/test_data_gap_analysis.py` — lock the
  three #1025 sentences, the #1019 sentence, and that real builds/streams still flag.
- `AGENTS.md` §8 guard-row for the new tests.

## Not covered

- Whether a misattributed measurement should be RE-HOMED to another model row (#1018) —
  that is a rule-3b owner decision, not a reader fix.
- `engine_min_version` values already stored (#789 keeps them report-only; none of the
  false-positive sentences is in the store today).
