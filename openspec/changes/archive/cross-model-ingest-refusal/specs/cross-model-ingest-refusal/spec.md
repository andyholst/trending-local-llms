# cross-model-ingest-refusal

## ADDED Requirements

### Requirement: a cross-model copy is refused at the ingest seam, reusing the #695 allow-list

A raw measurement whose `(engine, tps, hardware, source_post)` tuple is ALREADY
carried by a DIFFERENT, already-merged model id is a copy of another model's
figure onto a post that never measured it — it MUST be refused loudly at ingest
before the row merges, exactly as the fabricated-engine and text-misattribution
seams refuse at the same seam. A tuple that `update_trending.CROSS_MODEL_ALLOW_LIST`
pins as legitimate (same-family variant ids, or a post that genuinely measured
both models) is kept. The allow-list is defined ONCE and shared by the ingest
refusal and the #695 post-merge gate so the two gates never disagree. A refused
row is excluded and the rest of the snapshot still merges (non-breaking). The
report-only same-post cross-model scan stays report-only for history.

WHEN a raw snapshot carries a measurement whose identity tuple already exists
on a different stored model id and the tuple is not allow-listed,
THEN the measurement is refused loudly with the owning model id and never merged.

#### Scenario: a re-captured copy is refused before it ever merges

- **Given** a store where a `(engine, tps, hardware, source_post)` tuple is already carried by one model id (the owner)
- **When** a raw snapshot re-captures that same tuple onto a SECOND model id that is not an allow-listed pair
- **Then** the measurement is refused at ingest with the owning model id, never lands on the second model, and the rest of that raw row still merges
- **Test:** `tests/test_cross_model_attribution.py::test_ingest_refuses_a_re_capture_before_it_merges` and `::test_a_copy_onto_a_model_the_post_never_measured_is_refused`

#### Scenario: an established owner's own tuple is never refused

- **Given** a store where a model id carries a tuple it already owns
- **When** that same model's raw row re-captures it at ingest
- **Then** the measurement is kept (only a copy arriving on a DIFFERENT model id is refused)
- **Test:** `tests/test_cross_model_attribution.py::test_cross_model_carriers_are_the_store_already_merged`

#### Scenario: a documented allow-listed pair is kept

- **Given** the allow-list pins a tuple as a legitimate pair (same-family variant ids, or a post that measured both models)
- **When** a raw row for one of those model ids arrives carrying that tuple at ingest
- **Then** the measurement is kept, not refused
- **Test:** `tests/test_cross_model_attribution.py::test_a_documented_allow_listed_pair_is_kept_at_ingest`

#### Scenario: the ingest seam and the report-only scan never disagree

- **Given** the identity key `validate.same_post_cross_model_duplicates` reports on
- **When** the ingest-time refusal is applied
- **Then** the refusal identifies a copy by the SAME `(engine, tps, hardware, source_post)` key and the SAME `CROSS_MODEL_ALLOW_LIST` the #695 post-merge gate pins
- **Test:** `tests/test_cross_model_attribution.py::test_cross_model_carriers_are_the_store_already_merged` (identity-key assertion) and `::test_cross_model_refusal_is_wired_into_ingest` (seam registration)
