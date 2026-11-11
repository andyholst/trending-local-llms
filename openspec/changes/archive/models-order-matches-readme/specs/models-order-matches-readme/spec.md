# models-order-matches-readme

## ADDED Requirements

### Requirement: data/models.json order equals the README 'Most loved' table order

The `data/models.json` `models[]` array MUST be in the same order as the README
"Most loved" table (the render's rank order: band → 7-day score → posts → peak
t/s), because llgenie's `sync_registry.check_readme_matches` enforces strict
`readme_order` equality between the vendored registry list and the README table
(the regex `^| [**(.+?)**]` on the "Most loved" section). A drift — models.json
order != README order — breaks the producing-repo contract and reds the llgenie
hf-live tests (issue #708, introduced by #695 at 24 positions). The fix reorders
`models.json` to the README order and adds a guard so the order cannot silently
drift again.

WHEN `data/models.json` is produced,
THEN its `models[]` array order equals the README "Most loved" table order (the
guard `check_models_order_matches_readme` fails otherwise).

#### Scenario: the reordered store matches the README 'Most loved' order

- **Given** the real store with 117 rows and the committed README
- **When** the models[] array is reordered to the README "Most loved" table order
- **Then** the guard reports 0 divergences against the committed README
- **Test:** `tests/test_validate.py::test_models_order_matches_readme` (pass: committed README vs real store, 0 divergences)

#### Scenario: a swapped 'Most loved' row is caught

- **Given** a README copy whose first two "Most loved" rows are swapped
- **When** the guard runs against the real store order
- **Then** it fails, naming the divergence positions
- **Test:** `tests/test_validate.py::test_models_order_matches_readme` (fail: swapped rows caught)

#### Scenario: the store values are unchanged by the reorder

- **Given** the pre-#695 store content and the reordered array
- **When** the reorder lands
- **Then** no model id or value is lost or added (pure positional reorder; id/content multiset identical), and `--render-only` of `update_trending.py` produces no README diff
- **Test:** `scripts/verify` diffstat (41/41 add/del) covered during authoring; `validate --only data,schema,removal` passes including the additive-only + split/flatten guards
