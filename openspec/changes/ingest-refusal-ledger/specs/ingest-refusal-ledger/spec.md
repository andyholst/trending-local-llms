# ingest-refusal-ledger

## ADDED Requirements

### Requirement: Every ingest refusal is recorded in an append-only ledger

Each of the four ingest refusal seams (`refuse_fabricated_engines`,
`refuse_misattributed_measurements`, `refuse_cross_model_duplicate_measurements`,
`refuse_weight_gb_contradictions`) MUST record the dropped measurement — stage,
backend, model, engine, reason, source post, utc — into `data/refusals.json` before
dropping it. `REFUSAL_STAGES` is the ONE registry of stage names; `record_ingest_refusals`
MUST refuse an unknown stage (rule 6d). The ledger is append-only (rule 3b): a second
run never rewrites or truncates earlier entries, and an unreadable ledger is never
overwritten — the refusal is still logged.

#### Scenario: all four seams write
- **Given** a real raw fixture that triggers every refusal seam under a real `TRENDING_DATA_DIR`
- **When** the real `ingest_raw_snapshots` runs
- **Then** all four stages appear in `data/refusals.json` with intact fields
- **Test:** tests/test_ingest_refusal_ledger.py::test_every_refusal_seam_records_to_the_ledger

#### Scenario: refusal behavior is unchanged
- **Given** the same fixture
- **When** ingest runs with the ledger live
- **Then** refused measurements still never reach the store
- **Test:** tests/test_ingest_refusal_ledger.py::test_the_refused_measurements_never_reach_the_store

#### Scenario: the ledger is append-only
- **Given** a ledger written by a first ingest run
- **When** a second run appends
- **Then** the first run's entries stand untouched
- **Test:** tests/test_ingest_refusal_ledger.py::test_the_ledger_is_append_only

#### Scenario: a corrupt ledger is never rewritten
- **Given** an unreadable `refusals.json`
- **When** a refusal records
- **Then** the corrupt file stands, the refusal is logged, and nothing is overwritten
- **Test:** tests/test_ingest_refusal_ledger.py::test_an_unreadable_ledger_is_never_rewritten

#### Scenario: an unknown stage is refused
- **Given** a call naming a stage outside `REFUSAL_STAGES`
- **When** `record_ingest_refusals` runs
- **Then** it raises — a drifting stage name can never make the ledger silently unreadable
- **Test:** tests/test_ingest_refusal_ledger.py::test_record_refuses_an_unknown_stage

#### Scenario: every call site names a registered stage
- **Given** the whole tree
- **When** the scan runs
- **Then** every refusal call site passes a `REFUSAL_STAGES` member
- **Test:** tests/test_ingest_refusal_ledger.py::test_every_refusal_call_site_names_a_registered_stage

### Requirement: The gap analysis reports "REFUSED at ingest" as its own class

`scripts/data_gap_analysis.py` MUST read the ledger and report, beside the acquisition
and ingest classes, which dimensions were REFUSED at ingest — naming stage, model and
source post — so a re-search is never filed against posts the pipeline already holds.
A new refusal changes the gap signature (a changed gap state, not invisible).

#### Scenario: refused is distinguished from never-captured
- **Given** a store whose dimension gap has a matching ledger refusal
- **When** the real `analyse` runs with a real contract
- **Then** the gap reports "REFUSED at ingest" naming the stage and source post
- **Test:** tests/test_ingest_refusal_ledger.py::test_the_gap_analysis_distinguishes_refused_from_never_captured

#### Scenario: a refusal changes the gap signature
- **Given** a ledger that gains one refusal
- **When** the signature is computed before and after
- **Then** it differs — a real refusal is a new gap state
- **Test:** tests/test_ingest_refusal_ledger.py::test_refusals_change_the_gap_signature
