## ADDED Requirements

### Requirement: A captured measurement's footprint traces to the store row that uniquely owns the measurement

The gap analysis SHALL key a captured ENGINE row's free text by the row's own
measurement identity — the exact `(engine, tps, hardware, source_post)` tuple defined by
`update_trending._cross_model_identity` — and SHALL contribute that text to the captured
bucket of the store model that carries that tuple, when and only when exactly ONE store
model carries it. A tuple carried by two or more store models SHALL have its text copied
to none of them, and a tuple carried by no store model SHALL be attributed to no model.
The join SHALL mutate nothing but the in-memory capture: neither the store nor the raw
snapshots.

#### Scenario: A footprint captured under a sibling raw row traces to the variant that owns the tuple

- **Test:** `tests/test_data_gap_analysis.py::test_a_measurement_captured_under_a_sibling_row_traces_to_the_row_that_owns_the_tuple`
- **Given** a store where `plain` carries (llama.cpp 91, RTX 4090 24GB, …/status/1) and `variant` carries (llama.cpp 55, Ryzen AI Max 128GB, …/status/6), and a raw snapshot whose `plain` row cites BOTH posts — the `variant`-tuple row stating "131072-token context"
- **When** the capture is built and the store analysed
- **Then** `variant`'s captured bucket contains the sentence its own tuple carries
- **And** `variant` is classified as the ingest job the captured post proves (`captured_prose`), never an acquisition gap (`not_captured`)
- **And** the four classes still partition the missing set disjointly

#### Scenario: A joint or unowned measurement text is never copied to a row

- **Test:** `tests/test_data_gap_analysis.py::test_a_joint_or_unowned_measurement_text_is_never_traced_to_a_row`
- **Given** a store where `echoed` and `quoted` carry the SAME tuple and a raw row carries that joint tuple with a footprint sentence plus a tuple no store row carries
- **When** the capture is built
- **Then** neither `echoed` nor `quoted` receives either sentence
- **And** the raw id that maps to no store row has no bucket at all
