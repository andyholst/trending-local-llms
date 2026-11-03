# order-guard-fixture-tolerant

## ADDED Requirements

### Requirement: a README without the 'Most loved' table is skipped, not failed

The #708 order guard `check_models_order_matches_readme` verifies the
`data/models.json` `models[]` order equals the README "Most loved" table order and
fails on a divergence. When the README lacks the "Most loved" table entirely, the
guard cannot meaningfully compare orders — the section it checks does not exist. In
that situation the guard MUST report-skip (print + return, no `fail`), so harness
fixtures whose README has no table (e.g.
`tests/test_make_commands.py::build_fixture`) do not hard-fail on a check they
cannot run. Real drift detection is NOT weakened: a README that has the table but
differs in order is still strictly caught by the byte-identical `re.findall`
divergence path.

WHEN a README lacks the "Most loved" table,
THEN the order guard reports a skip instead of failing,
AND when the README has the table but is order-divergent, the guard still fails.

#### Scenario: a placeholder README (no 'Most loved' table) is skipped

- **Given** a placeholder README with no "Most loved" section
- **When** the order guard runs against a store with a `models[]` array
- **Then** it reports a skip and records no failure (not enforceable)
- **Test:** `tests/test_validate.py::test_models_order_matches_readme` (skip case: placeholder README → no FAILURES)

#### Scenario: a present but order-divergent README is still caught

- **Given** a README whose "Most loved" section has two rows swapped
- **When** the order guard runs against the store order
- **Then** it fails, naming the divergence positions (strict path unchanged)
- **Test:** `tests/test_validate.py::test_models_order_matches_readme` (swapped-rows case: FAILURES==1, "order != README \"Most loved\" order")

#### Scenario: the real committed README still passes 0-divergence

- **Given** the committed README with its "Most loved" table and the reordered store
- **When** the order guard runs
- **Then** it reports 0 divergences (real README always has the table, strict check runs)
- **Test:** `tests/test_validate.py::test_models_order_matches_readme` (matching README → 0 divergences; real store/README 0 divergences via `make _validate`)
