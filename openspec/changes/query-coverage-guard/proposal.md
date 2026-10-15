# The searches must chase the models we rank, and say so when they do not

**Issue:** [#264](https://github.com/andyholst/trending-local-llms/issues/264)
**Capability:** `query-coverage`

## Why

The refresh searches are a fixed, hand-maintained keyword list: `SEARCH_GROUPS` in
`scripts/update_trending.py` holds 24 queries across the four backends, and the four
Hermes search prompts inline the same words. Measured against that constant:

```
naming 'strata':  NONE
naming '125':     NONE
naming 'flash':   only 'dflash' (DFlash — not Flash-Next)
naming 'qwen':    'rtx 3090 tokens per second qwen',
                  'qwen3.8-27b dflash speculative tokens',
                  'tensorfold dflash mlx qwen tokens per second',
                  'rx 7900 xtx qwen'
```

The ONE model-specific query names `qwen3.8-27b` — not `qwen3.8-flash-next-125b`, and no
query names `Strata`, the engine holding the most measurements for that model (17 in the
store, 62 raw Strata entries). So every Strata figure for the model — including the
CUDA number the README publishes — arrived **incidentally**, because a generic card query
happened to surface a post mentioning it.

The consequence is not a wrong number; it is an **unknowable one**. The pipeline cannot
look for the model or the engine, so it cannot tell "no such measurement exists" from
"we never looked", and a higher figure upstream can never enter. The repo already knows
query choice decides coverage (`skills/gather-data.md`: engine-name-only queries do not
index — "Prefer **model + token/VRAM** queries"), yet the models and engines topping the
ranking have no query of their own.

## What Changes

- **`scripts/update_trending.py`** — the ONE implementation (rule 6d) of the rule: the
  trending models are read from the store, each gets a query naming it by its own id, and
  `query_names_model()` decides — from that same store — whether any query in the set
  names a model. `SEARCH_GROUPS` stays the curated base; the derived model queries are
  appended to it, never replacing it.
- **`scripts/query_coverage.py`** — the thin CLI over those functions: `--queries` prints
  the derived model queries (what the search prompts append), and the default run prints
  the coverage report and **exits 1 when a trending model is named by no query**, so a
  gap is loud and separable from "the query ran and found nothing".
- **`Makefile`** — a `query-coverage` target (report + guard) wired into
  `_validate-search`, and the four search prompts append `$(MODEL_QUERIES)` so the
  searches actually ask for the ranked models instead of only the hardware keywords.
- **`tests/test_query_coverage.py`** — in `make _test`: the derivation, the naming rule,
  the guard, and the falsification.
- **README + `ARCHITECTURE.md`** (rule 6h), `AGENTS.md` (the rule + the section-8 row)
  and `skills/gather-data.md`.

## Impact

The search legs now ask for the models the ranking is built from, and a new trending
model that no query names turns the search validation red. Read-only against the store;
no network. It changes which posts are *looked for*, never which are accepted.

## Not covered (out of scope — separate issues)

- The per-backend cell showing hardware outside its column's stated band (#260).
- The README render and its store sync — verified in sync
  (`scripts/validate.py --only readme`: 38/38 models, "README.md matches the generator
  output").
