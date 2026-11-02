# measurement-store-split

## ADDED Requirements

### Requirement: The normalised split is lossless and flat-compatible

`split_store()` MUST pull the engagement counters off every measurement row into posts.json
(published once per source_post, stored as the MAX across referencing rows) while keeping the
footprint on the row, and MUST return a catalog with no inline `engines[]`. `flatten_store()`
MUST rebuild the exact pre-split flat store, splicing the counters back per source_post, so a
reader of `models.json` sees no change and a missing post entry resolves to 0.

#### Scenario: split vs flatten round-trip

- **Given** a flat store with a measurement carrying counters and a footprint
- **When** it is split and then flattened back
- **Then** every (model, engine, tps, source_post, footprint) identity survives, the counters
  are spliced back, and the reconstructed store is flat for readers
- **Test:** tests/test_split_store.py::test_flatten_reconstructs_identity and
  tests/test_split_store.py::test_split_pulls_counters_off_rows

#### Scenario: a row without a post entry

- **Given** a measurement whose source_post has no posts.json entry
- **When** flatten() is called
- **Then** its counters resolve to 0 — never a penalty
- **Test:** tests/test_split_store.py::test_missing_post_resolves_zero

#### Scenario: counters only ever grow

- **Given** two referencing rows that report the same source_post with different like counts
- **When** split_store() is called
- **Then** posts.json holds the MAX (a counter can never shrink, AGENTS §2.3b)
- **Test:** tests/test_split_store.py::test_max_counters_never_shrink

### Requirement: The shipped split files conform to their contracts and equal the split of the flat store

`data/measurements.json` and `data/posts.json` MUST validate against
`data/measurements_contract.json` and `data/posts_contract.json`, and MUST be exactly
`split_store(models.json)` — the flatten-equality guard (the #463/#525 loss class). The three
new checks MUST be registered under the `schema` stage and MUST skip cleanly when the split
files are absent (legacy stores / temp-dir make fixtures).

#### Scenario: contracts validate the shipped files

- **Given** the shipped data/measurements.json and data/posts.json
- **When** each is validated against its contract
- **Then** both conform
- **Test:** tests/test_split_store.py::test_new_contracts_validate_the_real_files

#### Scenario: the guard passes on the real store

- **Given** the real data/models.json and the shipped split files
- **When** `check_split_flatten` runs
- **Then** it reports no lost measurement and no shrunk counter
- **Test:** tests/test_split_store.py::test_validate_split_flatten_is_green and
  tests/test_split_store.py::test_shipped_split_matches_flat_store

### Requirement: The old path is untouched (additive, non-breaking)

The flat `data/models.json`, `data/model_contract.json`, `README.md`, the old test modules and
the old reader behaviour MUST be unchanged by this change; only additive files/checks are
added, and the write path additionally emits the split files.

#### Scenario: the fixture make test still passes

- **Given** a temp-dir fixture with the new contracts copied
- **When** `make _merge` then `make _validate` run against it
- **Then** both succeed (the new checks skip or pass, and the old checks pass unchanged)
- **Test:** tests/test_make_commands.py::test_make_validate

#### Scenario: the shipped store is byte-unchanged

- **Given** the git index
- **When** this change is applied
- **Then** data/models.json, data/model_contract.json and README.md have no diff
- **Test:** (verified in CI; the split guard also proves flatten == the flat store)
