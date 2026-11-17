## ADDED Requirements

### Requirement: A capture the pipeline refused as misattributed states nothing for the model

The data-gap analysis SHALL read the refusal ledger (`data/refusals.json`)
before classifying captured prose, and a raw capture whose `source_post` the
ledger refused for that model under the `refuse_misattributed_measurements`
stage SHALL contribute NO text to the model's captured bucket — neither through
`captured_text`'s row scan nor through `_join_measurement_identity`'s
measurement-identity join. Pairing of ledger row to capture SHALL use one
citation normalization (case-, trailing-slash- and mirror-host-insensitive), and
the stage name SHALL be the seam's own registry value
(`update_trending.REFUSAL_STAGES`).

#### Scenario: The refused post's sentence is not captured prose

- **Given** a store model missing `context_tokens` whose raw row carries an
  engine capture stating "80k context", and a ledger row
  (`refuse_misattributed_measurements`, that model, that post)
- **When** `captured_text(store, raw_dir, refusals=ledger)` builds the capture
- **Then** the model's captured text holds neither "80k context" nor any text
  from that post, and the model is classified as an acquisition gap
  (`missing`, not `captured_prose` / `unstructured`)
- **Test:** tests/test_data_gap_analysis.py::test_a_capture_the_ledger_refused_as_misattributed_states_nothing_for_the_model

#### Scenario: The identity join re-credits nothing the scan skipped

- **Given** the same post recorded under a SIBLING raw id whose measurement
  tuple the refused model's store engine uniquely owns (the #411 join shape),
  and a ledger refusal naming the pair with a different citation spelling
  (mixed case, trailing slash)
- **When** the capture is built with the ledger in hand
- **Then** the join credits the sibling's text to no row, and the refused
  model's bucket stays free of it
- **Test:** tests/test_data_gap_analysis.py::test_a_capture_the_ledger_refused_as_misattributed_states_nothing_for_the_model

#### Scenario: An unrefused capture still counts

- **Given** a second model's capture stating "131072-token context" with no
  ledger row for that (model, post)
- **When** the capture and analysis run with the same ledger
- **Then** that model remains `captured_prose` — an ingest job its own post
  proves
- **Test:** tests/test_data_gap_analysis.py::test_a_capture_the_ledger_refused_as_misattributed_states_nothing_for_the_model

#### Scenario: The stage name is registered by the seam that writes it

- **Given** the analysis' `MISATTRIBUTION_STAGE` constant and the seam's own
  stage registry `update_trending.REFUSAL_STAGES`
- **When** the test suite compares them
- **Then** the constant equals `refuse_misattributed_measurements` and appears
  in the registry, so a rename of either turns the suite red instead of
  silently reading zero refusals
- **Test:** tests/test_data_gap_analysis.py::test_the_gap_reader_refusal_stage_is_the_seams_own_spelling

#### Scenario: The real store's misattributed claim leaves the ingest class

- **Given** the shipped store and ledger, where `qwen-3.6-27b`'s only
  "80k context" sentence comes from the post refused as measuring `Qwen 3.5 35B`
- **When** `make data-gaps` analyses the real store
- **Then** `qwen-3.6-27b` is not `unstructured` for `context_tokens`, and the
  claim reads as `untraceable` (its own store text only), while coverage counts
  stay untouched
- **Test:** tests/test_data_gap_analysis.py::test_the_real_store_reports_only_figures_it_can_point_at
