# Capability: cross-model-duplicate-identity

The ingest-time refusal `refuse_cross_model_duplicate_measurements` reads the
SAME identity signatures the post-merge gate `validate.cross_row_duplicate_measurements`
uses, from ONE shared implementation (rule 6d).

## Requirement: the refusal and the gate share one identity definition

The identity that defines a cross-model duplicate must be computed by ONE
function that both the ingest-time refusal and the post-merge gate read, so the
two seams can never disagree about what a duplicate is.

#### Scenario: a hardware-renamed duplicate is refused at ingest
- **Given** a store whose carriers map already records an incoming measurement's
  `(engine, tps, date, source_post)` tuple on a different model id
- **When** a raw row is ingested whose measurement carries that same tuple but a
  renamed hardware label ("R9700" instead of "AMD R9700")
- **Then** the measurement is REFUSED at ingest (never enters the store), with the
  owning model id and source post named in the reason
- **Test:** `tests/test_cross_model_attribution.py::test_a_planted_hardware_renamed_duplicate_is_refused_at_ingest`

#### Scenario: the refusal identity is the gate's identity, one implementation
- **Given** the shared identity function in `scripts/update_trending.py`
- **When** both `refuse_cross_model_duplicate_measurements` and
  `validate.cross_row_duplicate_measures` key on it
- **Then** a measurement the gate flags is a measurement the refusal already
  stops at ingest, keyed by ONE function (no second key-building copy)
- **Test:** `tests/test_cross_model_attribution.py::test_the_refusal_reads_the_gate_identity`

#### Scenario: an allow-listed documented pair is still kept
- **Given** the documented `CROSS_MODEL_ALLOW_LIST` re-keyed to the same date-based identity
- **When** a measurement is captured that matches an allow-listed pair
- **Then** it is kept at ingest, never refused
- **Test:** `tests/test_cross_model_attribution.py::test_a_documented_allow_listed_pair_is_kept_at_ingest`
