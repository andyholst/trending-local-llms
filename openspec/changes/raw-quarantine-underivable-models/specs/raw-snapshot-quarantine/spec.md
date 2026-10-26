# raw-snapshot-quarantine

## ADDED Requirements

### Requirement: An un-derivable model is quarantined, never fatal

`scripts/self_correct_raw.py` MUST distinguish a snapshot that carries rows it cannot complete
from a capture that is unusable. A model row whose `hf` cannot be derived and which does not
resolve to an existing store model MUST be excluded from the snapshot, reported in ONE loud
`QUARANTINED:` line naming the model, the reason and its source posts, and the command MUST
exit 0 — the remaining models in the same snapshot, and every other snapshot, still conform
and still merge.

#### Scenario: one hf-less model beside a good one

- **Given** a raw snapshot holding a good model and a new model with no `hf`
- **When** `scripts/self_correct_raw.py` runs
- **Then** it exits 0, the good model is still in the file, the hf-less row is gone, and the output names that model and its source post on a `QUARANTINED:` line
- **Test:** tests/test_raw_quarantine.py::test_an_underivable_model_is_quarantined_and_the_rest_merges

#### Scenario: the remaining snapshot validates against the search contract

- **Given** the same snapshot after the quarantine
- **When** it is validated against `data/search_contract.json`
- **Then** it conforms (`hf` is `required` there), and a second run rewrites nothing and quarantines nothing
- **Test:** tests/test_raw_quarantine.py::test_an_underivable_model_is_quarantined_and_the_rest_merges

### Requirement: A stored model is repaired from the store, not quarantined

When a row with no `hf` resolves to a model already in `data/models.json`, the `hf` MUST be
filled from that stored model (data already present, never invented) and the row MUST be kept,
so a known model's newly captured measurements are not lost to a missing field.

#### Scenario: a known model arrives without its hf

- **Given** the store holds `qwen3.6-27b` with `hf: Qwen/Qwen3.6-27B` and a raw snapshot carries that model with no `hf` and a new measurement
- **When** the correction runs
- **Then** the row is kept, `hf` is the stored id, the new measurement survives, and the report says `hf <- store`
- **Test:** tests/test_raw_quarantine.py::test_a_known_model_is_repaired_from_the_store

### Requirement: An unattributable measurement is dropped, loudly

A measurement with no `source_post` MUST be dropped from its model with a loud report (rule 5b:
every figure carries its post); the model itself is kept while any measurement survives, and is
quarantined only when none does.

#### Scenario: one of two measurements has no post

- **Given** a model with two measurements, one of which has no `source_post`
- **When** the correction runs
- **Then** it exits 0, the model keeps the measurement that has its post, and the dropped one is reported by engine name
- **Test:** tests/test_raw_quarantine.py::test_a_measurement_without_a_post_is_dropped

#### Scenario: a model whose only measurement has no post

- **Given** a model with a single measurement that carries no `source_post`
- **When** the correction runs
- **Then** the model row is quarantined too (it has no valid figure) and reported
- **Test:** tests/test_raw_quarantine.py::test_a_measurement_without_a_post_is_dropped

### Requirement: Only an unreadable capture fails the step

The command MUST exit non-zero ONLY when nothing could be processed — every discovered snapshot
unreadable — which is the state that genuinely needs a re-search. An unreadable snapshot beside
readable ones MUST be reported loudly and skipped, and the readable ones MUST still be corrected.

#### Scenario: one corrupt snapshot beside a good one

- **Given** a `data/raw` with one unparseable file and one good snapshot holding an hf-less row
- **When** the correction runs
- **Then** it exits 0, reports the unreadable file and the quarantined row, and the good snapshot conforms
- **Test:** tests/test_raw_quarantine.py::test_a_capture_where_no_snapshot_can_be_read_is_the_unusable_state

#### Scenario: nothing can be read at all

- **Given** a `data/raw` where every snapshot is unparseable
- **When** the correction runs
- **Then** it exits non-zero with `SELF-CORRECT INCOMPLETE` (a re-search is needed)
- **Test:** tests/test_raw_quarantine.py::test_a_capture_where_no_snapshot_can_be_read_is_the_unusable_state

### Requirement: Ingest refuses a new model with no HF link

`update_trending.ingest_raw_snapshots` MUST NOT add a NEW model whose `hf` is empty after
normalisation: it MUST print a loud `[ingest] REFUSED` line naming the model and the snapshot
and continue with the rest, so the merge cannot put an unreachable HF link into the store even
when it runs before `correct-raw`. An EXISTING model still merges and keeps its stored `hf`.

#### Scenario: the merge sees an hf-less new model

- **Given** a raw snapshot newer than the store holding a good new model and a new model with no `hf`
- **When** `ingest_raw_snapshots` runs
- **Then** only the good model is added, the refusal names the other model and the snapshot, and no stored model loses anything
- **Test:** tests/test_raw_quarantine.py::test_ingest_refuses_a_new_model_without_an_hf

#### Scenario: a pasted URL that cannot become a repo id

- **Given** a raw snapshot whose `hf` is `https://huggingface.co/onlyone` for a model the store already holds
- **When** the correction runs
- **Then** the un-reducible value counts as missing (reported `hf <- MISSING`), the row is repaired from the store instead of dropped, and the command exits 0 (it no longer aborts the refresh)
- **Test:** tests/test_hf_id.py::test_correct_raw_reduces_a_url_shaped_hf
