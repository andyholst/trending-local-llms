# Order guard should SKIP (not fail) when the README lacks the 'Most loved' table

**Issue:** [#711](https://github.com/andyholst/trending-local-llms/issues/711)
**Capability:** `order-guard-fixture-tolerant`

## Why

The #708 order guard `check_models_order_matches_readme` (added in PR #710,
merged as `dc45207`) is strict-correct on the committed pair: it verifies
`data/models.json` `models[]` order equals the README "Most loved" table order
and fails on any divergence. But its absent-section path is not fixture-tolerant:
whenever `README.read_text()` has no "Most loved" table, the guard hard
`fail("README has no 'Most loved' table")`.

The committed README always has the table, so production 0-divergence
enforcement is unchanged. However any fixture / build harness whose README lacks
the section — notably `tests/test_make_commands.py::build_fixture`, which points
`TRENDING_README` at a placeholder README with no table — gets a hard `fail()` on a
guard it cannot meaningfully run. That is the class of test/CI red first seen at
`083074f` and is what this change eliminates: a README without the section is not
enforceable, so the guard should report-skip rather than fail.

This is deliberately scoped to the ABSENT-section path only. A present-but-divergent
README stays strictly caught (the `re.findall` divergence check is byte-identical
to the merged shape); real drift detection is not weakened because the real
committed README always has the table.

## Delivery

- `scripts/validate.py` — in `check_models_order_matches_readme`, when the README
  lacks the "Most loved" table, print a `SKIP:` line and `return` (no `fail`). The
  strict `re.findall` divergence check that follows is byte-identical to the merged
  `f69d622`/`dc45207` shape.
- `tests/test_validate.py` — `test_models_order_matches_readme` gains a skip-case: a
  placeholder README with no "Most loved" table must not record a failure
  (not-enforceable → skipped). The existing matching-passes-0-divergence and
  swapped-rows-caught cases remain green.
- `openspec/changes/order-guard-fixture-tolerant/` — this change dir.
