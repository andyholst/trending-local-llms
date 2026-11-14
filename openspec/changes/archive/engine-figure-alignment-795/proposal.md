# Proposal: engine-figure-alignment-795

Issue: #795 — "the highest t/s per inference engine must stay an aligned, tested
PR: #970
contract": engine spellings split figures, an unknown engine stranded a captured
34.8 t/s, and variant rows duplicate measurements.

## Why

The repo's core promise (rules 5, 5b, 6) is that every figure is attributed to exactly
one, correctly-spelled, repo-linked engine. Three places where that alignment degrades
silently, re-measured green against the fetched base on 2026-11-14:

1. `make engine-check` WARNs forever: 49 raw snapshots name the engine `mlx.fast` while
   the registry knows only `MLX-fast (Bonsai 2)` (`no-repo` decision on every run); the
   normalization that hides it is per-model `engine_aliases` luck, not a declared rule.
2. `make engine-check` WARNs `Bonsai Oryon: unknown — no inference-engine signal`: the
   rule decision (packaging vs engine) is recorded on one data row's private alias map,
   not in the registry — a `Bonsai Oryon` capture for any other model strands exactly
   like the 34.8 t/s figure the issue names.
3. A measurement `(engine + tps + date + source_post)` appearing under two model ids has
   no failing gate: `check_cross_model_attribution` (issue #693) keys on
   (engine, tps, **hardware**, source_post) and is REPORT ONLY. A variant row renames
   hardware ("R9700" vs "AMD R9700"), so the same figure copied onto
   `qwen3.8-27b-swift`-style ids slips through the hardware key — the date key is the
   stable one. On the shipped store: 43 exact-signature groups over 40 model-id pairs,
   plus variant pairs sharing engine+tps+date across distinct posts (the issue's own
   `961.6 t/s (TokenSpeed)` pair).

## What Changes

- `scripts/engine_registry.py`: `ENGINE_NAME_ALIASES` — the ONE engine-spelling map
  (rule 6d): `mlx.fast` → `MLX-fast (Bonsai 2)`, `Bonsai Oryon` →
  `llama.cpp (PrismML fork)`, each with its decision recorded in a comment;
  `canonical_engine_name()`; `register_new_engines` resolves a captured spelling through
  the map before classifying, so `make engine-check` stops warning on aliased spellings
  (a target that is NOT registered keeps the old loud WARN — the map never hides an
  unknown engine).
- `scripts/update_trending.py`: `apply_engine_aliases` folds the registry map under the
  model-specific aliases (model rows keep their own maps — rule 3b additive), so a
  captured `mlx.fast` / `Bonsai Oryon` re-homes to its registered engine at ingest for
  EVERY model, and `fabricated_engine_reason` treats a declared spelling as its
  canonical target (never "fabricated").
- `data/models.json` (additive only, rule 3b): the `llama.cpp (PrismML fork)` and
  `MLX-fast (Bonsai 2)` registry notes record the decisions (Bonsai Oryon is packaging
  of the fork; the `mlx.fast` spelling re-homes here); every shipped cross-row duplicate
  pair gains a `measurement_model_aliases` justification on the variant/spelling row or
  on both members of a joint-benchmark pair — a justified-as-data exception, never a
  removed row or shrunk value.
- `scripts/validate.py`: `cross_row_duplicate_measurements` + the FAILING gate
  `check_no_duplicate_measurements` registered in the `data` stage (rule 6d): a shared
  `(engine, tps, date, source_post)` under two model ids fails, and a shared
  `(engine, tps, date)` between **variant-related** ids (normalized prefix/equality —
  one id is the other plus a suffix) fails too; a pair may stay only when justified as
  data by `measurement_model_aliases` on either row — the same exemption the attribution
  seam (#652) reads. An unrelated pair of models that merely reports the same figure on
  the same day from different posts stays legal (a coincidence is not a copy).
- `tests/test_engine_figure_alignment.py` (new suite, wired via `make test`) and the
  `AGENTS.md` §8 guard row.

## Impact

- Pipeline stage: `validate` (`data` stage) gains a failing gate — a new cross-row copy
  reds `make validate` instead of being re-discovered by hand.
- Data: `data/models.json` model rows gain optional `measurement_model_aliases`
  (already contract-declared by #652); engine registry notes gain the two decisions.
  No measurement, value, key, or row is removed or shrunk (rule 3b).
- CI: no new make target — the gate rides the existing `_validate-data` / `validate`
  wiring (rule 6d/6m), and the new test suite rides `make test`.

## What is NOT covered

- No row is merged or deleted from `data/models.json` — merging a duplicate model id is
  a rule-3b human decision; this change justifies every shipped pair instead.
- The ingest-time refusal seam `refuse_cross_model_duplicate_measurements` (#702,
  hardware-keyed) is left as-is; extending its identity to the date key is recorded as a
  finding in `findings.md`, fixed in its own change (rule 6g).
- README table rendering is unchanged: justified same-family pairs keep their rows and
  the #693 documented design (variants may share a measurement) stays.
