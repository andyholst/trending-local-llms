# Restore models.json order to the README 'Most loved' table (24-position drift from #695) + a guard

**Issue:** [#708](https://github.com/andyholst/trending-local-llms/issues/708)
**Capability:** `models-order-matches-readme`

## Why

The producer repo (this one) commits `data/models.json` alongside the README, and the
README's "Most loved" table lists every model in the render's rank order
(`sort_models` output). Producers that vendor both files — llgenie's
`sync_registry.check_readme_matches`, which enforces strict order equality via the
`readme_order` regex `^| [**(.+?)**]` on the "Most loved" section — require that the
`models.json` `models[]` array order equal the README table order. Issue #695 committed
a `models.json` whose array drifted from that order at **24 positions**; the llgenie
hf-live tests went red and its #1634 stayed open.

This change reorders `data/models.json` models[] to exactly the README "Most loved"
table order — a pure positional reorder with **no value/content change** (verified
41/41 add/del, all 117 rows present, id/content multiset unchanged) — and adds a guard
check to `scripts/validate.py` so the producer order cannot silently drift again.

Non-breaking and additive: no schema, contract, data-value, or workflow change; the
reorder restores the committed array to what `--render-only` already produces (byte-identical
README), and the guard is a new `data`-stage validator registration.

## Delivery

- `data/models.json` — reordered `models[]` array to match the README "Most loved" order (pure positional; 41/41; verified content + id multiset unchanged, `--render-only` produces no README diff).
- `scripts/validate.py` — new `check_models_order_matches_readme(store)` (mirrors the llgenie `readme_order` contract) registered under the `data` stage; fails when `models.json` order != README "Most loved" order.
- `tests/test_validate.py` — `test_models_order_matches_readme` runs the REAL check on the committed README + real store (pass, 0 divergences) and on a temp README with two "Most loved" rows swapped (caught).
- `openspec/changes/models-order-matches-readme/` — this change dir.
