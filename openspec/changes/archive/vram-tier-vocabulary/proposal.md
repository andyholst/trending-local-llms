# Proposal: vram-tier-vocabulary

Issue: #341 — `tech-debt: \`vram_tier\` holds values the contract does not describe, and nothing notices`

## Why

`data/model_contract.json` declares `vram_tier` as a bare `string`, while
`data/MODEL_CONTRACT.md` documents six capacity categories (`8GB`, `12GB`, `16GB`, `24GB`,
`32GB`, `48GB`). Measured on the store:

```
{'16GB': 10, '8GB': 10, 'CPU': 7, '24GB': 6, '48GB': 3, '12GB': 2, '128GB': 2,
 '2GB': 2, '18GB': 2, '9GB': 2, '512GB': 1, '6GB': 1, '48': 1, '8': 1}
```

`48` and `48GB` are one category spelled two ways; `9GB`/`18GB` are measurements rather
than categories; `CPU` is not a capacity at all (that is #343's question). Nothing noticed
any of it: the field is unvalidated free text, and `README`/card-fit happened to avoid it.

The contract cannot simply be narrowed to an enum — a `enum` REJECTS the store as it
stands, which rule 3b forbids — so the honest first step is to make the drift visible and
fix the spelling that carries no information.

## What Changes

- **`scripts/validate.py::check_vram_tier_vocabulary`** (REPORT ONLY, `data` stage): prints
  the distribution, names every unit-less value as a spelling of `NNGB`, and names every
  value outside the documented categories. It never fails a run — the answer to `CPU`/`9GB`
  is a contract decision (#343), not a red build — and an empty store, a missing key or junk
  input are all reportable states, never exceptions.
- **The two unit-less values are normalised in the store**: `qwen3-next-80b-a3b` `48` →
  `48GB`, `qwen2.5-1.5b-instruct` `8` → `8GB`; `README.md` re-rendered with
  `make render-readme` (#195) so the same change carries the cell text and no store churn.
- **`tests/test_vram_tier_vocabulary.py`** drives the real check: the distribution, the
  unit-less spelling, an out-of-category value, `CPU` NOT being reported as out-of-category,
  three degenerate stores that must not raise, the real store carrying no bare number, and
  the wiring (`data` stage registered, selected by a make target).

Verified RED against the pre-change tree (the check does not exist → the guard fails loudly
naming it) and GREEN after (`PASSED 11 | FAILED 0`; `make validate-mapped` 121 checks).

## Impact

`scripts/validate.py` (one report-only check + its registration), `data/models.json` (two
spellings), `README.md` (re-rendered), a new `tests/test_vram_tier_vocabulary.py`, this
OpenSpec change and the regenerated `OPENSPEC.md`. No new make target, stage, job or image
(`ARCHITECTURE.md` unchanged, rule 6h).

## Not covered

- **The contract itself.** Turning `vram_tier` into an enum — or splitting "capacity
  category" from "model needs a CPU" — is a breaking-shape decision that needs its own
  `model_contract.vN.json` (rule 6b) and is exactly what #343 asks. This change only makes
  today's vocabulary visible.
- **The `9GB`/`18GB` measurements.** They are real information (a 9 GB run is not an 8 GB
  card), so they stay; the report is where a human sees that the "category" is being used
  as a measurement.
- **Telling the crawl the vocabulary.** The search prompts do not ask for `vram_tier` at
  all (the model row is derived at ingest), so there is no prompt wording to fix here.
