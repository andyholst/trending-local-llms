# Spec delta: validate-source-post-readback (footprint-hard-fields-gate-789)

## MODIFIED Requirements

### Requirement: Hard footprint fields are a failing gate; prose stays report-only

`check_source_post_readback` MUST add a `data`-stage FAILURE for every stored footprint value
of a hard field (`weight_gb`, `context_tokens`, `system_ram_min`, `storage_offload`) that
appears in neither its cited post's captured structured fields nor its text, naming each with
model, engine, tps, field, value and source post — while a flag of the prose field
`engine_min_version` remains a printed WARN with its reason and never a failure (measured
precision: 10 of the 23 #531 flags were prose distillations; gating on them reds refresh PRs
on parser misses, the outcome #458/#459 refused). The gate/report field split lives in ONE
declaration in `scripts/validate.py`.

#### Scenario: a planted hard-field contradiction fails the data stage

- Given a fixture store whose `weight_gb` states a figure the cited post's capture nowhere
  states, and its raw tree holding that capture
- When `check_source_post_readback` runs (with `FAILURES` cleared)
- Then exactly one FAILURE is recorded naming model, field, value and source post, and the
  hard-field field name appears in it
- **Test:** tests/test_source_post_readback.py::test_a_hard_field_contradiction_fails_the_data_stage

#### Scenario: a prose-field contradiction stays a report, never a failure

- Given a fixture store whose `engine_min_version` distills a claim the captured post text
  does not restate verbatim and no structured capture states
- When `check_source_post_readback` runs (with `FAILURES` cleared)
- Then no FAILURE is added and the WARN line names the flag and its report-only reason
- **Test:** tests/test_source_post_readback.py::test_a_prose_field_distillation_stays_report_only

#### Scenario: the field split is declared once and exactly

- Given the shipped `scripts/validate.py`
- When the test reads the declared gate and report field sets
- Then the gate set is exactly the four numeric/hard footprint fields, the report set is
  exactly `engine_min_version`, and their union is the footprint tuple the scan walks
- **Test:** tests/test_source_post_readback.py::test_the_gate_and_report_field_sets_are_declared

#### Scenario: the shipped store lands green under the new gate

- Given the real `data/models.json` and `data/raw/` as shipped
- When the real scan runs over them
- Then it flags nothing on any field, so promoting the hard fields adds no failure today
- **Test:** tests/test_source_post_readback.py::test_the_shipped_store_flags_no_unsupported_footprint_values

#### Scenario: every hard-field contradiction is caught, each hard field gated

- Given a fixture store carrying a contradicted value in EACH hard field while the prose
  field stays clean
- When `check_source_post_readback` runs
- Then each hard field contributes exactly one FAILURE and the prose field contributes none
- **Test:** tests/test_source_post_readback.py::test_every_hard_field_contradiction_fails_and_prose_does_not
