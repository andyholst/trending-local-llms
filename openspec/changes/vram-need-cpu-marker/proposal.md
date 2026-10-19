# Proposal: vram-need-cpu-marker

Issue: #343 — `tech-debt: \`vram_min\` carries \`"CPU"\` as a marker, and \`vram_need()\` reads it as "not stated"`

## Why

Four models in the store declare `vram_min: "CPU"` — the source says the model needs **no
GPU at all**, which is a real, useful statement for the CPU table's audience. `vram_need()`
asked `_gb_value()` for a number, got `None`, and fell through to the coarse `vram_tier`,
to "smallest card it ran on", or to `("unknown", "unknown")`. The README's VRAM cell then
told a reader **"not stated"** (Gemma 3 4B) or **">=32GB"** (Qwen3-30B-A3B) about a model
whose requirement the source had stated plainly.

## What Changes

- **`CPU_ONLY_MARKER`** (`^cpu(-| )?only$`, case-insensitive, deliberately strict) in
  `scripts/update_trending.py`. Only the bare marker forms match: `CPU`, `cpu only`,
  `CPU-only`. A sentence that merely mentions system RAM — the store's
  `"system RAM holds the expert set (32GB GPU + system RAM)"` — also names a GPU, so it must
  NOT be read as CPU-only.
- **`vram_need()` honours the marker first**, returning `("CPU only", "declared")` — the
  same evidence label a stated number gets, so the cell renders `**CPU only**<br><sub>stated
  by the source</sub>` instead of a guess.
- **`README.md` re-rendered** with `make render-readme` (no store churn, #195); the
  validator's own re-render calls the same function, so gate and generator cannot disagree.
- **`tests/test_card_fit.py::test_vram_need_prefers_what_the_source_states`** gains: all
  three marker spellings resolve to the declaration, a prose `vram_min` does not, and a
  CPU-only model's README cell says `CPU only` rather than `not stated`.

Verified RED against the pre-change function (4 failures — the models rendered as tier /
card / unknown) and GREEN after (76 passed, 0 failed; `make validate --only readme` QA
PASSED).

## Impact

`scripts/update_trending.py` (one marker + three lines in `vram_need`), `README.md`
(four cells), `tests/test_card_fit.py`, this OpenSpec change and the regenerated
`OPENSPEC.md`. No new target, stage, job or image (`ARCHITECTURE.md` unchanged, rule 6h).

## Not covered

- **A free-text `vram_min` is still read by its first number** —
  `"system RAM holds the expert set (32GB GPU + system RAM)"` renders `32GB`, which is the
  GPU half of a split requirement. Reporting those (rather than guessing) is the same shape
  as #341's vocabulary report and belongs in its own change.
- **`vram_tier: "CPU"`** (7 models) still falls through `vram_need` when `vram_min` is
  empty; that is #341's "not a capacity" observation and wants the same contract decision.
