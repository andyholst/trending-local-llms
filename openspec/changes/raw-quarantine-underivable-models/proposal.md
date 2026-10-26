# Quarantine an un-derivable model instead of aborting the whole refresh

**Issue:** [#381](https://github.com/andyholst/trending-local-llms/issues/381)
**Capability:** `raw-snapshot-quarantine`

## Why

`scripts/self_correct_raw.py` (`make correct-raw`, the aggregate's normalisation step) treated a
single model row it could not complete as a failure of the WHOLE capture: it collected every
underivable `hf` / `source_post` into one `CANNOT_DERIVE:` note and returned 1.

Measured on scheduled refresh-bot run **39159853260** (2026-10-18): all four search legs went
green, then `aggregate` died at `make correct-raw`:

```
CANNOT_DERIVE: qwen3.8-flash-next-125b: hf missing (cannot derive); qwen3.6-35b-a3b: …; qwen3.6-27b: …
SELF-CORRECT INCOMPLETE: some fields (hf/source_post) cannot be derived — re-search needed.
make: *** [Makefile:_correct-raw] Error 1
```

No PR was opened and none of the four legs' captured data landed — the opposite of the
graceful-degradation rule the pipeline promises (§4: preserve last-known data, never blank the
store). The ingest layer had the mirror-image hole: a new model with no `hf` was accepted into
`data/models.json` with `formats[0].hf: ""`, which then fails `check_links_present` on the PR.

## What Changes

- **`scripts/self_correct_raw.py`** — a model row that cannot be completed is now
  QUARANTINED, not fatal:
  - `hf` missing after normalisation, and the row does NOT resolve to an existing store model
    → the row is excluded from the snapshot with one loud `QUARANTINED:` line naming the model,
    the reason and its source posts. The rest of the snapshot still merges.
  - `hf` missing but the row DOES resolve to a stored model → the `hf` is filled FROM THE STORE
    (`hf <- store …`), so a known model's new measurements are never thrown away. Only data
    already present is used (nothing is invented).
  - a measurement with no `source_post` → that measurement is dropped loudly (it can never be
    attributed to a post, so it is not a valid entry); the model is quarantined only when no
    measurement survives.
  - exit codes now distinguish the two states: **0** = every snapshot was processed and now
    conforms (quarantined rows are reported, never hidden); **1** = the capture is unusable —
    no snapshot could be read at all (a re-search is genuinely needed). One sloppy model can no
    longer discard four legs.
- **`scripts/update_trending.py::ingest_raw_snapshots`** — a NEW model whose `hf` is empty after
  normalisation is REFUSED at ingest with a loud `[ingest] REFUSED …` line naming the model and
  the snapshot, so an hf-less row can never reach the store even when the merge runs before
  `correct-raw` (the aggregate's step order). An EXISTING model still merges: its stored `hf`
  is kept (rule 3b).
- **`tests/test_raw_quarantine.py`** (new) + **`tests/test_hf_id.py`** (the irreducible-URL case
  now asserts the new contract) — the behaviours above, against the real modules and the real
  `data/search_contract.json`.
- **`AGENTS.md`** §8 row and **`ARCHITECTURE.md`**'s `correct-raw` row describe the new behaviour
  in the same change (rules 6c/6h).

## Impact

The refresh aggregate only. A conforming capture behaves exactly as before (no rewrite, no
stamp bump, exit 0); a capture with one bad row now lands the good rows instead of nothing.
`data/models.json` can only gain models that carry their HF link — a refusal never removes a
stored value, so `check_no_value_loss` is untouched.

## Not covered (out of scope)

- **Re-searching the quarantined models.** The issue allows "excluded OR the leg is retried";
  this change excludes, loudly. Retrying a leg is a search-budget decision and would need the
  legs to report a per-leg status the aggregate can act on.
- **Recovering the quarantined rows automatically.** A quarantined row is reported in the run
  log (model id, reason, source posts) — the fix is a new capture carrying the `hf`, not a
  guessed repo id.
- **A model already in the store WITHOUT an `hf`.** Additive-only (rule 3b) forbids removing it
  here; such a row can only be repaired by a human decision.
