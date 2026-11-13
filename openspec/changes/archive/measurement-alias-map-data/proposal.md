# Proposal: measurement-alias-map-data

Issue: #652
PR: #881

## Why

The documented exceptions to the measurement-attribution rule — "this row MAY carry
a measurement whose text names model X" — live in `MEASUREMENT_MODEL_ALIASES`, a
module-level `dict[str, set[str]]` literal in `scripts/update_trending.py`
(empty today). A reviewer cannot see a documented exception in a data diff, the
model contract cannot validate it, and `misattributed_measurement_reason`'s own
refusal text tells humans to "record a documented exception in
MEASUREMENT_MODEL_ALIASES" — a Python literal, not data. AGENTS.md's additive
contract rule wants real values in the store/contract so a refresh carries them
forward; the repo already has the exact precedent for a model-level mapping
(`engine_aliases` lives on the model row, applied at ingest).

## What Changes

- `data/model_contract.json` gains the optional model-row key
  `measurement_model_aliases` (array of store model ids, unique, `additionalProperties:
  false` kept, never added to `required` — rule 3b): the documented counterpart
  models whose measurements this row may legitimately carry.
- `scripts/update_trending.py` drops the `MEASUREMENT_MODEL_ALIASES` literal;
  `misattributed_measurement_reason` reads the mapping from DATA: the incoming
  model row's own `measurement_model_aliases` plus the same-id store row's, and
  resolves each counterpart id through the store exactly as the old dict did. The
  refusal text names the data key, not a code dict.
- `scripts/validate.py` gains `check_measurement_alias_map` (mapping stage): an
  alias counterpart that is not a model id in the store fails validation — a
  dangling alias is a silent no-op today, the exact defect class rule 3b exists
  to prevent. Registered in a stage AND a Makefile `--only` list (rule 6d).
- `data/MODEL_CONTRACT.md` documents the new key next to `engine_aliases`.

## Impact

- `data/model_contract.json`, `data/MODEL_CONTRACT.md` (contract widened additively)
- `scripts/update_trending.py` (mapping moves from code to row data)
- `scripts/validate.py` (+ its stage registration and the Makefile wiring comment)
- `tests/test_measurement_attribution.py` (the alias scenario now drives the DATA
  key; the empty-store case still refuses), `tests/test_validate.py` (dangling
  counterpart refused; the wiring test stays green)
- `AGENTS.md` §4 (the row key) and §8 (its guard row) — the issue carries the
  rule-3c comment naming exactly these sections.

## Not covered

- Populating any real alias entries — none exist today; the change makes the
  mechanism reviewable data, it does not invent exceptions (rule 3).
- Search-side capture of aliases (search agents never write alias keys; only the
  store row holds them).
- Changing the attribution REFUSAL logic itself (#651's joint-figure rule stays
  byte-identical; only where the exception lives moves).
