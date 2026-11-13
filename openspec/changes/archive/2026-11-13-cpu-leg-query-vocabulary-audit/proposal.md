# The CPU leg's curated vocabulary is audited, homed, and yield-gated

**Issue:** [#858](https://github.com/andyholst/trending-local-llms/issues/858)
**PR:** [#891](https://github.com/andyholst/trending-local-llms/pull/891)
**Capability:** `search-query-vocabulary`

## Why

The CPU search leg went green on the 2026-11-11 refreshes while capturing ZERO
models — seven per-query `data/raw/cpu-*.json` snapshots, every one
`"models": []`, while the same runs' nvidia/metal/amd legs captured 9/5/2 —
after capturing plenty all through October. Its AND-style queries (`llm tokens
per second no gpu cpu`) kept answering HTTP 200 with hundreds of mirror posts
while yielding no CPU figure, and every gate stayed green: `search-smoke`,
`engine-check`, `validate-fetch` and `query-coverage` all stop at HTTP status
or query COUNTS. Nothing read the WORDS a returned page contains. The same
keyword lists were also hand-written in three places — the four `_search-<backend>`
prompts, `scripts/smoke_search.py`, and `update_trending.SEARCH_GROUPS` — so a
query fixed in one place stayed broken in the other two.

## What Changes

- **`scripts/query_vocab.py` (new)** — the ONE home of each leg's curated
  keyword vocabulary (`LEG_KEYWORDS`). The `Makefile` prompts receive it through
  `$(<BACKEND>_KEYWORDS)` indirections, `smoke_search.py` probes it, and the
  CPU fetch sampling in `update_trending.py` imports the same dict.
- **The measured CPU vocabulary**: `cpu tokens per second`,
  `llama.cpp cpu tokens per second`, `raspberry pi tokens per second` and
  `no gpu tokens per second` replace `llm tokens per second no gpu cpu` —
  probe-verified co-occurrence queries (the silent AND-query and the yielding
  natural queries were measured against the live mirror).
- **`make search-smoke` gains the yield audit**: every answered query is
  labelled `yield: N rate-posts, M model-posts` or SILENT, and a CPU leg whose
  answered pages yield NO candidate at all exits 2 naming the vocabulary — the
  mirror being reachable is exactly the state that hid the starved leg. The
  #258 majority rule and the #291/#296 outage classification are untouched;
  each rule's verdict sentence is printed only for the rule that fired.
- **`tests/test_cpu_query_vocabulary.py` (new)** locks all three halves (one
  home incl. the resolved Makefile indirection; the gate through `main`'s real
  probe seam over fixture pages taken from the archived starved snapshots; the
  audited vocabulary incl. posts captured VERBATIM from the live mirror that
  yield candidates under the new queries' own regexes).

## Impact

- `scripts/`: `query_vocab.py` (new), `smoke_search.py`, `update_trending.py`
- `Makefile`: `SEARCH_<BACKEND>_QUERIES` indirections + `QUERY_VOCAB_RUN`
- `.hermes/skills/data-search/SKILL.md`, `skills/gather-data.md`: the leg
  vocabulary is stated as owned by `scripts/query_vocab.py`
- `tests/`: `test_cpu_query_vocabulary.py` (new); `test_smoke_search.py`
  fixtures now carry rate/model text so the yield labels are real
- `AGENTS.md`: rule 6o paragraph + §8 guard row (rule 3c: this issue changes
  §6o's behaviour — the vocabulary home and the yield gate are new rules)

## Not covered

- Yield-gating the nvidia/metal/amd legs' SILENT state (labels are printed for
  them; only the CPU leg is gate-red today — the suite pins that scope).
- Deriving `update_trending.SEARCH_GROUPS` for CUDA/Metal/ROCm from the home:
  those `--fetch` hand lists already diverge from the prompt vocabulary
  (measured 15 vs 11 / 6 vs 5 / 10 vs 9) and are filed as a separate finding.
- A live end-to-end refresh run (bounded by the 3 s probe budget; a real
  refresh will exercise the gate on its own cadence).
