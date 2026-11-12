## ADDED Requirements

### Requirement: The write-time link check refuses dead `source_post` and `engine_repo`

`write_raw_snapshot(..., verify_hf=True)` SHALL refuse a definitively dead
(`HTTP 404`/`410`) `source_post` by dropping that engine measurement, and SHALL
refuse a definitively dead `engine_repo` by stripping the key while keeping the
measurement's figure. Each refusal SHALL print one loud `[write-raw] WARN:`
naming the backend, the model id, the field and the refused value. An
indeterminate answer (403/429/5xx/transport error) SHALL keep the value.

#### Scenario: A dead source_post refuses the measurement

- **Given** a raw payload whose model carries an engine measurement with a
  `source_post` a real local server answers `404`
- **When** `write_raw_snapshot(..., verify_hf=True)` writes the snapshot
- **Then** the written snapshot holds no measurement with that `source_post`,
  the surviving measurement is intact, and the WARN names the model, the field
  and the refused value
- **Test:** tests/test_write_raw_link_verify.py::test_dead_source_post_refuses_the_measurement

#### Scenario: A dead engine_repo is stripped, the figure stays

- **Given** a measurement whose `engine_repo` answers `404` and whose
  `source_post` answers `200`
- **When** the snapshot is written with `verify_hf=True`
- **Then** the measurement survives with its t/s and `source_post` and without
  the `engine_repo` key, and the WARN names the refused repo URL
- **Test:** tests/test_write_raw_link_verify.py::test_dead_engine_repo_is_stripped_and_the_figure_kept

#### Scenario: An indeterminate answer keeps the value

- **Given** a `source_post` answered `503` and an `engine_repo` answered `429`
  by the local server
- **When** the snapshot is written with `verify_hf=True`
- **Then** both values are kept in the written snapshot and nothing is refused
- **Test:** tests/test_write_raw_link_verify.py::test_indeterminate_answers_keep_the_values

#### Scenario: verify_hf=False performs no link requests

- **Given** a payload carrying a `source_post` a server would answer `404`
- **When** `write_raw_snapshot(..., verify_hf=False)` writes the snapshot
- **Then** the value is written unchanged (the check is opt-in, as for `hf`)
- **Test:** tests/test_write_raw_link_verify.py::test_verify_hf_false_does_not_check_links
