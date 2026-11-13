# Spec delta: measurement-ingest

## ADDED Requirements

### Requirement: The search contract may carry an attribution exception

`data/search_contract.json` SHALL declare the optional model-item key
`measurement_model_aliases` (array of store model ids, unique, at least one
member), never in `required`, with `additionalProperties: false` kept. A raw
search snapshot carrying the key SHALL conform to the search stage.

#### Scenario: A raw snapshot carrying a resolvable exception conforms

- **Given** a raw search snapshot whose model item carries
  `measurement_model_aliases: ["<a model id stored in data/models.json>"]`
- **When** the search stage validates it against `data/search_contract.json`
  (`make validate --only search`)
- **Then** the snapshot conforms — the key is not pruned and the stage is green.
- **Test:** tests/test_measurement_attribution.py::test_raw_snapshot_carrying_the_exception_conforms

### Requirement: A captured exception flows through ingest additively

A NEW model captured with `measurement_model_aliases` SHALL keep the key on its
new store row. An EXISTING store row SHALL gain the captured counterparts as the
union with what the row already documents — deduped, never narrowed, never
overwritten (rule 3b).

#### Scenario: A new model keeps its captured exception

- **Given** a fixture raw directory holding a NEW model whose row carries a
  `measurement_model_aliases` counterpart present in the store
- **When** `ingest_raw_snapshots` (the real function, `raw_dir=` seam) merges it
- **Then** the appended store row carries the key with that counterpart.
- **Test:** tests/test_measurement_attribution.py::test_new_model_keeps_captured_exception

#### Scenario: An existing row gains counterparts as a union

- **Given** a store row documenting `["a"]` and a raw capture of the same id
  carrying `["a", "b"]`
- **When** the same ingest merges the snapshot
- **Then** the row carries `["a", "b"]` — `a` is not duplicated or removed, and
  no other key on the row changed.
- **Test:** tests/test_measurement_attribution.py::test_existing_row_gains_aliases_additively

### Requirement: The mapping gate refuses a dangling exception in a raw snapshot

`check_measurement_alias_map` SHALL validate the counterparts on every
`data/raw/*.json` model item as well as the store's, and a counterpart that is
not a model id in the store SHALL fail the mapping stage naming BOTH sides — the
snapshot file and raw model, the dangling counterpart, and the store it must
resolve in.

#### Scenario: A dangling counterpart in a snapshot is refused naming both sides

- **Given** a fixture raw snapshot whose model carries
  `measurement_model_aliases: ["ghost-model"]` while `data/models.json` has no
  such id
- **When** `check_measurement_alias_map` runs (the mapping stage, as
  `make validate --only search,mapping` wires it)
- **Then** it fails, and the failure line names the snapshot file, the raw
  model, `ghost-model`, and the store.
- **Test:** tests/test_validate.py::test_dangling_raw_alias_counterpart_is_refused_naming_both_sides

#### Scenario: The store-side refusal from #652 stays green-locked

- **Given** a store row whose counterpart id is not in the store
- **When** the same gate runs
- **Then** it still fails exactly as issue #652 locked it.
- **Test:** tests/test_validate.py::test_measurement_alias_map_gate_refuses_a_dangling_alias

### Requirement: Both contracts declare the same key

`data/model_contract.json` and `data/search_contract.json` SHALL declare
`measurement_model_aliases` with the same name, both optional (never
`required`) — the pair-declaration pattern
`tests/test_measurement_footprint.py` already enforces for the footprint
dimensions.

#### Scenario: The contracts-declare-the-same-key test covers the alias key

- **Given** the two contract files
- **When** `make test` runs the attribution suite's pair assertion
- **Then** `measurement_model_aliases` is declared in both and absent from both
  `required` lists.
- **Test:** tests/test_measurement_attribution.py::test_alias_key_declared_in_both_contracts
