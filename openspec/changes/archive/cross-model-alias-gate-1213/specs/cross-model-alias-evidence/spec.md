## ADDED Requirements

### Requirement: The duplicate gate and ingest share one justification seam

The post-merge duplicate gate SHALL accept a cross-row duplicate whose identity key is
allow-list-exact in `CROSS_MODEL_ALLOW_LIST`, using the same key ingest uses, so a documented
joint measurement can drop its store-side alias without redding `validate --only data`. A pair
with neither an alias nor an allow-list entry SHALL still fail the gate.

#### Scenario: An allow-list-exact pair with no store alias

- **Given** two model rows carrying the same `(engine, tps, date, source_post)` with no `measurement_model_aliases`, pinned allow-list-exact in `CROSS_MODEL_ALLOW_LIST`
- **When** `cross_row_duplicate_measurements` and `check_no_duplicate_measurements` run over those rows
- **Then** no duplicate is reported and the gate records no failure
- **Test:** tests/test_engine_figure_alignment.py::test_allow_list_exact_pairs_are_justified_without_an_alias

#### Scenario: An undocumented copy still fails

- **Given** two model rows carrying the same post's figure with neither an alias nor an allow-list entry
- **When** the duplicate gate runs
- **Then** the pair is reported and `check_no_duplicate_measurements` records a failure
- **Test:** tests/test_engine_figure_alignment.py::test_make_validate_fails_on_a_planted_cross_row_duplicate

### Requirement: A stated-but-unparseable alias counterpart is refused and reported

The attribution exception SHALL NOT be granted silently when either side states a params value
that `params_identity` cannot parse. Ingest SHALL refuse such a NEW counterpart and name it in
the refusal log; the store gate SHALL print a REPORT line naming it. A genuinely absent params
keeps the documented #1207 fail-open, and a parseable different size stays refused as before.

#### Scenario: A planted alias to a stated-unparseable counterpart

- **Given** a row declaring parseable params and a counterpart whose params are stated but not parseable
- **When** `merge_measurement_aliases` runs with the store, then `check_measurement_alias_map` runs on a row carrying that alias
- **Then** the counterpart is not added, the ingest log prints REFUSED with the counterpart id, and the gate prints a REPORT line naming it without failing the shipped shape
- **Test:** tests/test_alias_identity_gate.py::test_unparseable_params_alias_is_refused_at_ingest_and_reported

#### Scenario: Same-identity variants and absent params keep working

- **Given** a same-identity variant with parseable params, and a counterpart with no params at all
- **When** `cross_identity_alias_reason` is called on each
- **Then** the variant yields no reason and the absent-params case keeps the documented fail-open
- **Test:** tests/test_alias_identity_gate.py::test_cross_identity_reason
