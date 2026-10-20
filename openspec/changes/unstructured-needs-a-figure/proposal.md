# Proposal: unstructured-needs-a-figure

Issue: #456 — `data-gap: storage_offload (40 models)`

## Why

`make data-gaps` tells a reader that "every item below is real data the search
sees and the contract drops or leaves unstructured". For the `unstructured:*`
items — the ones that claim the value IS in the store's prose, just not in a
structured key — that sentence was partly false on the store the issue was filed
from. Twelve claims, measured on this tree (`python3 - <<'PY'` reproducing
`analyse()`'s haystack):

- **`context_tokens` — 3 of 6 claims came from an ENGINE's registry note.** The
  `DFlash2` note reads "Speculative decoding + context-lookup"; `analyse()` fed
  every `supported_engines` note into a model's haystack, so `qwen3.8-27b-coder390`,
  `qwen3.8-27b-dflash2-teksedge3090` and `qwen3.8-27b-twin-turbo` were reported as
  stating a context window in prose. An engine note is a property of the ENGINE,
  identical for every model that names it — it is not evidence about a model's
  context window (and it made the same engine-wide sentence a per-model entry in
  the gap signature).
- **`context_tokens` matched a WORD, not a figure.** `qwen3.6-27b` was reported
  for `"kv-cache q4_0"` (a KV-cache QUANT, no window at all) and
  `qwen3.8-27b-dflash2-teksedge3090` for `"context lookup"` and a
  `"25K-token document reproduction"` (a document-size test). The pattern was
  `\b\d+\s*k\b|\bcontext\b|\bkv[- ]?cache\b` — any of those three words.
- **`storage_offload` read "Flash Attention" as a storage medium.** `bonsai-2-9b`
  was reported for `"GPU offload, Flash Attention, 262,144-token context"`:
  `flash` was in the medium list (`ssd|nvme|flash|disk|hdd|storage`), so an
  attention KERNEL answered for an SSD.
- **`weight_gb` read a VRAM capacity that sat next to the word GGUF.**
  `deepseek-v4.1-flash` was reported for `"…MXFP4-engram GGUF, 32K context at
  fp16, 16GB on VRAM + 60GB RAM"`: the weights word (`GGUF`) is within 24
  characters of `16GB`, but `16GB on VRAM` is the card, not the weights — the
  same class #213 fixed for a bare capacity, surviving through a nearby format
  word.
- **The haystack was a CONCATENATION of unrelated fields**, so two words in
  different fields could satisfy a "within N characters" requirement that no
  sentence ever satisfied.

A report that names a figure the post never stated is worse than a smaller
report: it sends a backfill hunting for data that is not there (measured on
#213) and it re-files the same model for ever. This change makes the
`unstructured:*` claim mean what it says — *this model's own text states the
figure, only in prose* — and stops the analysis treating an engine-wide note as
per-model evidence.

## What Changes

- **Each field is scanned on its own** (`quant` / `hardware` / `why`, on the
  model and on every measurement); the fields and the engine notes are never
  joined into one string, so a match can only span text that actually sits
  together.
- **An engine's registry note is never scanned as a model's prose.** It is a
  property of the engine, not of the model that names it.
- **`context_tokens` requires a context-window FIGURE next to a context word**:
  `context` / `ctx` / `kv-cache` within 24 characters of a number carrying a
  `k`/`m` unit, a `token`/`tok` unit, or a bare 4+ digit count. `30 tok/s` is
  throughput, not a window (`tok` followed by `/s` never matches).
- **`storage_offload` only accepts `flash` as flash STORAGE** (`flash storage`,
  `flash memory`, `flash drive`), never bare `flash` — `Flash Attention` is a
  kernel.
- **`weight_gb` refuses a capacity qualified as memory**: a `NN GB` immediately
  followed by `VRAM`, `RAM`, `system RAM`, `unified`, `DDR*`/`GDDR*` is not a
  weight footprint, whatever weights word is nearby.

Measured on the store: `unstructured:context_tokens` 6 -> 2
(`qwen-3.6-27b` "80k context", `gemma-4-12b` "256K ctx."), `unstructured:weight_gb`
3 -> 2 (`qwen3.6-27b` "16.8GB weights", `muse-glimmer-30b` "<20GB weights"),
`unstructured:storage_offload` 1 -> 0. Every remaining claim is a figure the
model's own text states. The `missing:*` coverage counts are unchanged: those are
real gaps.

## Impact

`scripts/data_gap_analysis.py` (three patterns, the haystack builder),
`tests/test_data_gap_analysis.py` (one new test covering all four classes in both
directions plus the real-store measurement), the AGENTS.md half (blocked below),
this change and the regenerated `OPENSPEC.md`. No make target, stage, pipeline job
or image changes (`ARCHITECTURE.md` unchanged); no data file is touched.

**BLOCKED — AGENTS.md could not be written in this sandbox** (the file is
protected as an agent-instruction file and the write was refused; it is reported
instead of forced). The docs half of this change must land with it, and this is
the text:

- §3 "Post-refresh data-gap analysis (issue #115)" — `unstructured` now means
  "the model's OWN text states a FIGURE": a `context`/`kv-cache` word with no
  window (`"context lookup"`, `"kv-cache q4_0"`), `Flash Attention` read as an
  SSD, a capacity qualified as VRAM/RAM beside the word `GGUF`, and an engine
  registry note (one sentence about the ENGINE, shared by every model naming it)
  are none of them a model's own figure. Each field is scanned on its own.
- §8 row `tests/test_data_gap_analysis.py` — append: "`unstructured` claims that
  name no figure — an engine registry note read as per-model prose (the DFlash2
  `context-lookup` note, 3 models), a KV-cache QUANT / `context lookup` / a
  `25K-token document` read as a context window, `Flash Attention` read as a
  storage medium (bonsai-2-9b), and a VRAM capacity next to `GGUF` read as
  weights (deepseek-v4.1-flash) — while a genuinely stated figure (`80k
  context`, `256K ctx.`, `16.8GB weights`) stays reported and the `missing:*`
  coverage counts do not move (issue #456)".

## Not covered

- **Backfilling the `missing:*` dimensions** (58/69 models have no
  `storage_offload`, 44 no `context_tokens`, 36 no `weight_gb`, 35 no
  `engine_min_version`, 30 no `system_ram_min`). Those are acquisition gaps: the
  source post states no figure, and AGENTS.md rule 2 forbids inventing one. The
  store already holds every dimension the contract declares
  (`## Contract gaps`: none) and nothing captured is lost at ingest — measured
  here: 0 of the dimension values present in 408 `data/raw/*.json` snapshots are
  missing from `data/models.json`. Filling them is a refresh's job.
- **Structuring the 4 figures that ARE stated in prose but only on an
  untraceable source.** `gemma-4-12b` ("256K ctx.") and `muse-glimmer-30b`
  ("<20GB weights") sit on placeholder `https://lightbrd.com/` or profile-page
  `source_post` values, so the figure cannot be traced to a `…/status/<id>`
  post; `qwen-3.6-27b`'s "80k context" is a measurement whose own text names a
  DIFFERENT model (Qwen 3.5 35B). They stay unstructured, and a refresh that
  captures the real post is what closes them.
- **`system_ram_min` / `engine_min_version`'s patterns.** No false claim was
  measured for either (both reported 0 unstructured on this store).
