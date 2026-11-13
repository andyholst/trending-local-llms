# Proposal: engine-min-version-ingest

Issue: #877

## Why

#876 widened the `engine_min_version` detector so `make data-gaps` can now SEE the
build sentences posts actually use — but the detection stops at the report. Measured
on `origin/master` c9e2786: `captured:engine_min_version` names **7 models** whose
CAPTURED post text states a build (`BigMoeOnEdge on stock llama.cpp (untouched
upstream, submodule)`, `MLX 4-bit Swift 1.5 adapter`, …) while `data/models.json`
carries no structured value for them — the report already names this class the
INGEST job. `data/model_contract.json` and `data/search_contract.json` ALREADY hold
the per-measurement `engine_min_version` key, `merge_engines` already carries a
STATED value onto the same post's merged row, and the `data-search` skill already
asks for it (#371) — so the missing piece is one step: nobody COMPUTES the value
from the build sentence the post stated. A gap the pipeline can see but never closes
re-files itself every sweep.

## What Changes

- `scripts/update_trending.py` gains `fill_engine_min_version`: during
  `ingest_raw_snapshots`, every incoming raw measurement whose OWN text
  (`quant`/`hardware` — the capturing post's record, never the model's `why` prose,
  rule #470) matches the ONE detector `data_gap_analysis._ENGINE_MIN_TEXT` gets
  `engine_min_version` filled with the matched phrase VERBATIM. The measurement's
  existing `source_post` is the citation, and `merge_engines`' existing same-post
  dimension fill then carries the value into the store row it merges into.
- The fill is ADDITIVE (rule 3b): it only fills a missing key, never overwrites an
  existing value, never raises or shrinks any other field; a measurement with no
  build phrase gains NOTHING (the precision class from #458/#213 stays exact).
- The detector has exactly ONE implementation (rule 6d): `update_trending` imports
  `_ENGINE_MIN_TEXT` from `data_gap_analysis`; a second copy is refused by a test.
- The fill prints loudly (`[engine-build-fill] N measurement(s) gained
  engine_min_version from captured phrasing`), like `refuse_fabricated_engines`.

## Impact

- `scripts/update_trending.py` (new fill seam + its call in `ingest_raw_snapshots`)
- `tests/test_engine_min_version_ingest.py` (new: fill, precision, no-overwrite,
  detector-single-implementation, merge carries the value to the store row)
- Measured Done-when: with the seam live, re-ingesting the CURRENT raw snapshots
  (`--since` replay) closes the class — `captured:engine_min_version` shrinks from
  the baseline 7 (measured 2026-11-13 on c9e2786) and the closed models gain the
  structured value on the measurement their citing post produced. The 2
  `unstructured` models match only the model's `why` prose and are NEVER filled
  (#470: `why` is not evidence); the 4 `untraceable` ones have no post behind the
  text and stay untraceable.

## Not covered

- The 52 `not_captured` models (acquisition gap — only new searches close them;
  the prompts already ask since #371).
- The 4 `untraceable` models (capture gap — no post behind the value; no ingest
  may invent one).
- The 2 `unstructured` models whose only match is `model.why` agent prose — the
  #470 rule forbids filling from it.
- Widening `_ENGINE_MIN_TEXT` itself (done by #876; this change consumes it).
