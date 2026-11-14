## ADDED Requirements

### Requirement: A raised t/s never erases a captured footprint trace

The captured-text join SHALL trace a captured measurement's footprint text to
the store row that uniquely owns it even when the stored t/s was raised at
ingest above the captured figure: the join SHALL accept a raw tuple whose
`(engine, hardware, source_post)` matches a unique store carrier and whose
captured t/s is numerically at most the stored t/s. A measurement with no
source post SHALL still require an equal t/s. An identity match whose t/s
comparison fails SHALL be reported loudly, never dropped silently, and joint
or unowned identities SHALL keep crediting no row.

#### Scenario: A raised t/s keeps the footprint trace

- **Given** a store row whose measurement t/s is `60` and a raw snapshot carrying the SAME (engine, hardware, source_post) with captured t/s `55` and a footprint sentence
- **When** `captured_text` builds the capture
- **Then** the sentence lands in that row's captured bucket and the row reads as an ingest job, not an acquisition gap
- **Test:** tests/test_data_gap_analysis.py::test_a_raised_tps_keeps_the_footprint_trace

#### Scenario: An unreconcilable identity is reported loudly

- **Given** a raw tuple whose post identity matches a store row but whose captured t/s is HIGHER than the stored t/s
- **When** `captured_text` builds the capture
- **Then** the text is credited to no row AND the run prints a `measurement-identity` line naming the miss
- **Test:** tests/test_data_gap_analysis.py::test_an_unreconcilable_identity_is_reported_loudly

#### Scenario: No source post means equal t/s only

- **Given** a raw tuple with NO source post whose t/s differs from the store row's t/s on the same (engine, hardware)
- **When** `captured_text` builds the capture
- **Then** the text is credited to no row
- **Test:** tests/test_data_gap_analysis.py::test_a_measurement_without_a_source_post_needs_equal_tps

#### Scenario: A raised joint figure is still credited to neither row

- **Given** TWO store rows carrying the same post identity, each with a raised t/s, and one captured sentence
- **When** `captured_text` builds the capture
- **Then** neither row receives the sentence
- **Test:** tests/test_data_gap_analysis.py::test_a_joint_raise_is_still_credited_to_neither
