# Spec delta: measurement-attribution (alias-identity-gate)

## ADDED Requirements

### Requirement: An attribution-exception counterpart shares the row's model identity
A `measurement_model_aliases` counterpart SHALL share the row's declared parameter-size
identity (the leading size of the store `params` field). The ingest merge SHALL REFUSE a
new counterpart whose params identity differs (both known), naming both sizes; a
same-identity variant (a quantization or phone variant that keeps the params figure) SHALL
still be accepted, and the check SHALL fail open when either params is unknown. A
non-pending cross-identity alias SHALL be INERT in `misattributed_measurement_reason` (it
can never legitimize a misattribution). The shipped store's historical cross-identity pairs
SHALL be REPORTED for owner review (issues #1207/#1210/#1213), never failed — the
#650/#458/#459 report-only precedent for history an agent cannot repair under rule 3b —
while the DANGLING-counterpart hard fail is unchanged. One documented load-bearing pair
awaiting an owner ruling (`CROSS_IDENTITY_ALIAS_PENDING_RULING`) stays honored until ruled.

#### Scenario: a different-size counterpart is refused at ingest
- **Given** a 125B (MoE) row and a store carrying a 27B row and a 125B Apple-Silicon variant
- **When** a capture records aliases naming the 27B row and the 125B variant
- **Then** the 27B counterpart is refused (loudly) and never added; the same-identity 125B variant is added
- **Test:** tests/test_alias_identity_gate.py::test_ingest_merge_refuses_a_new_cross_identity_counterpart

#### Scenario: a same-identity variant is allowed and unknown params fail open
- **Given** a 27B row and a bonsai-2-27b counterpart (also 27B), and a row with unknown params
- **When** cross_identity_alias_reason is asked
- **Then** the same-identity pair returns no reason; an unknown-params pair fails open
- **Test:** tests/test_alias_identity_gate.py::test_cross_identity_reason

#### Scenario: a non-pending cross-identity alias cannot rescue a misattribution
- **Given** a 27B row whose aliases name a 0.8B row (not pending) and a measurement whose text names the 0.8B model with a t/s figure
- **When** misattributed_measurement_reason is asked
- **Then** the measurement is still refused — the cross-identity alias is inert
- **Test:** tests/test_alias_identity_gate.py::test_a_non_pending_cross_identity_alias_is_inert_in_misattribution

#### Scenario: the shipped store is reported, not failed, and dangling still fails
- **Given** a store with a cross-identity alias and a separate store with a dangling counterpart
- **When** check_measurement_alias_map runs
- **Then** the cross-identity pair is REPORTED (no failure); the dangling counterpart hard-FAILS
- **Test:** tests/test_alias_identity_gate.py::test_validate_gate_reports_cross_identity_and_fails_dangling

#### Scenario: the shipped store is cleaned and the params documented
- **Given** the corrected data/models.json
- **When** the alias identity gate runs over load_store()
- **Then** no cross-identity alias fails, the three non-load-bearing contaminants are gone, the same-identity variants survive, and the flash-next row records the official 125B naming
- **Test:** tests/test_alias_identity_gate.py::test_the_shipped_store_is_clean_and_documents_the_params
