# Proposal: cross-model-attribution

Issue: #693 — data: cross-model duplicate attributes one source post's t/s to two
distinct models (gemma-3-1b inherits 27B's 18 t/s)

## Why

A reader asks "can I run this model, and how fast?" and gets the number from
`data/models.json` → `README.md`. The store must attach every t/s to the model
the source post actually measured. Two rows in the shipped store break that:

1. **`gemma-3-1b` carries `MLX` 18 t/s on an "Apple M5 Pro Mac mini, 64GB
   unified memory" citing pratikg's six-model Mac mini test
   (`lightbrd.com/pratikg/status/2108994425166967019`).** That post's measured
   set is named in the store's own `data/raw` snapshots: Qwen3-30B 106 / Qwen3-8B
   61 / Bonsai-2-27B 26 / Laguna XS 2.1 56 / Qwen3-14B 34 / **Gemma 3 27B 18**.
   No Gemma 3 1B was measured. The 18 is the dense 27B's number, and the same
   tuple (`engine, tps, hardware, source_post`) renders on both model IDs — a
   reader concludes a 1B runs at 18 t/s on an M5 Pro, which the post does not
   support and which is implausibly slow for a 1B.

2. **`gemma-4-26b-a4b` carries `llama.cpp` 50.7 t/s on an RTX 3080 10GB citing
   the same PaulGugAI post (`lightbrd.com/PaulGugAI/status/2110275665408704970`)
   as `lfm2.5-24b-a2b`.** The row that owns the number is LFM's: its `quant`
   reads "Q4; prefill 644 tok/s in, 50.7 tok/s out; no bespoke engine
   (FreeToken/Strata not used)" — FreeToken/Strata are LFM's own engines, so the
   S1 speed test post is about LFM 2.5 24B-A2B on llama.cpp. The Gemma row's thin
   "QAT GGUF, Q4" carries the identical `(engine, tps, hardware, source_post)`.
   Same class as #650 but a distinct instance: #650 is a row whose own text
   names a different model; this is one measured model's number copied onto a
   second model the post never measured.

3. **`qwen3.6-35b-a3b` carries `llama.cpp` 51.8 t/s on a "Radeon AI PRO R9700
   32GB" citing the same xfxjapan AMD day-0 pre-verification post
   (`lightbrd.com/xfxjapan/status/2096715285923520644`) as `qwen3.8-27b`.** The
   51.8 belongs to `qwen3.8-27b`: the earliest capture (2026-10-04, amd) is the
   day-0 pre-verification under the qwen3.8-27b row, and the dedicated
   `qwen3.8-27b-radeon-pro-r9700` id carries the same 51.8 from a SECOND post
   (Mayhem4Markets), while `qwen3.6-35b-a3b`'s identical tuple first appears
   later (2026-10-23) with reworded text. One vendor figure on two different
   model families is the same copy class.

The same-post cross-model duplicate scan (identical `(engine, tps, hardware,
source_post)` on two model IDs) flags 14 groups in the shipped store; the
reviewer's #693 counts 13 groups under a (engine, tps, hardware) key and the
xfxjapan pair as the same class. Three are copies repaired here. The other 11
are legitimate: same-family variant IDs (e.g. `qwen3.8-27b` /
`qwen3.8-27b-swift`, `bonsai-2-27b` = ternary `qwen3.8-27b`, `qwen3-30b` =
`qwen3-30b-a3b`, phone variants) or posts that genuinely measured both models
(GuideboardLabs' Agon bench reports 25.4 t/s for both LFM 2.5 and
Qwen3.6-35B-A3B; laky_fx's PS5 demo reports a range for each model). Those
stay.

## What Changes

- **`data/measurements.json` + `data/models.json` (the split store)**: the three
  copied engine rows are dropped from `data/measurements.json` (the canonical
  measurement store), and the copied `engagement.seen_posts` entries from the
  `data/models.json` catalog
  - from `gemma-3-1b`: the `MLX` 18 t/s row citing
    `lightbrd.com/pratikg/status/2108994425166967019`, and its
    `engagement.seen_posts` entry (the post has no 1B measurement; the model
    keeps its real `llama.cpp` 2.9 t/s Raspberry Pi 4 measurement from
    TrelisResearch's April 2026 post);
  - from `gemma-4-26b-a4b`: the `llama.cpp` 50.7 t/s RTX 3080 row citing
    `lightbrd.com/PaulGugAI/status/2110275665408704970`, and its
    `engagement.seen_posts` entry (the model keeps its real RTX 3080
    measurement, `llama.cpp` 22.9 t/s IQ2_M from PaulGugAI's separate
    2096528833998356946 post, plus 12 more engine rows);
  - from `qwen3.6-35b-a3b`: the `llama.cpp` 51.8 t/s Radeon R9700 row citing
    `lightbrd.com/xfxjapan/status/2096715285923520644`, and its
    `engagement.seen_posts` entry.
  The figures stay on their owner rows (`gemma-3-27b` keeps 18 t/s;
  `lfm2.5-24b-a2b` keeps 50.7 t/s; `qwen3.8-27b` keeps 51.8 t/s).
- **`README.md`**: re-rendered as-of the store's own `generated_utc`
  (`--render-only`), so the copy rows disappear from the per-model engine rows,
  the per-backend tables and the ranking cells, and the render is byte-identical
  to the store.
- **`data/snapshots/`**: one corrected snapshot appended (the same mechanism a
  refresh uses) so `check_no_value_loss`'s additive-only gate compares the
  corrected store against the corrected baseline; a removal cannot pass the gate
  against the pre-fix newest snapshot.
- **`scripts/validate.py`**: a report-only `data`-stage scan,
  `same_post_cross_model_duplicates` / `check_cross_model_attribution`, prints
  the same `(engine, tps, hardware, source_post)` tuple shared by two model IDs
  after every run — the same pattern as `check_duplicate_runs` (#459) — so a
  future copy is loud without re-flagging history this change already repaired.
- **`tests/test_cross_model_attribution.py`** (new): locks that the shipped
  store no longer carries any of the three copied rows, that the README renders
  no 1B at the 27B's figure, no Gemma 4 26B A4B at LFM's figure and no
  qwen3.6-35b-a3b at qwen3.8-27b's R9700 figure, and that every remaining
  same-post cross-model identical tuple is in the documented legitimate
  allow-list.

## Impact

`data/measurements.json` (3 engine rows removed), `data/models.json` (catalog
`engagement.seen_posts` entries + engagement recomputed), `README.md`
(re-rendered), `data/snapshots/` (one corrected snapshot), `scripts/validate.py`
(one report-only check + registration), a new `tests/test_cross_model_attribution.py`,
this OpenSpec change and the regenerated `OPENSPEC.md`. No new make target,
job, workflow or image (`ARCHITECTURE.md` unchanged, rule 6h); the
scan is registered under the existing `data` stage and reaches CI via `make
validate` (rule 6d).

## Not covered

- **`data/raw` is untouched.** The raw snapshots are historical search captures;
  the six-model measured set is cited FROM them as evidence. Check
  `check_raw_mapping` maps raw models to the store by id and carries no
  requirement that every raw row exist in the store.
- **A future re-capture could re-introduce a copy.** The ingest seam refuses a
  measurement whose text names a different model; these rows' text does not name
  a model, so only the report-only scan plus the test gate keeps the class
  visible. The data sync's search/ingest is not part of this change.
- **The remaining 11 flagged tuples are left as the documented legitimate set.**
  Same-family variant IDs and genuine multi-model posts (`GuideboardLabs` Agon
  25.4 t/s for both models, `laky_fx` PS5 demo that measured each model with its
  own range) are not copies; the test pins them exactly so a NEW copy differs
  from the allow-list and fails.
