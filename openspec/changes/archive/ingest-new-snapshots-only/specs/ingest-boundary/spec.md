# ingest-boundary

## ADDED Requirements

### Requirement: A merge folds in only the snapshots newer than the store

`ingest_raw_snapshots` MUST merge only the raw snapshots strictly newer than the
`since` boundary it is given. A snapshot whose capture instant is at or before
`since` MUST NOT change the store — it was captured before the merge that
produced `since`, so its content is already in the store. A snapshot whose
capture instant cannot be read MUST still be merged (fail-open): a file this
code cannot date is never silently dropped. The capture instant MUST be the
snapshot's own `generated_utc`, falling back to the
`<backend>-<YYYYMMDD>-<HHMMSS>.json` stamp in its filename.

WHEN the boundary is applied to a directory of raw snapshots,
THEN only the snapshots newer than the boundary are merged, older ones leave the
store untouched, and an undateable snapshot is merged.

#### Scenario: an old snapshot cannot change the store

- **Given** a store whose `generated_utc` is newer than a raw snapshot's capture instant
- **When** ingest runs with that store's stamp as the boundary
- **Then** the old snapshot is skipped and the store is untouched: 0 added, 0 updated
- **Test:** `tests/test_ingest_watermark.py::test_an_old_snapshot_cannot_change_the_store`

#### Scenario: a fresh refresh still merges its own legs

- **Given** a raw snapshot captured after the store's `generated_utc`
- **When** ingest runs with that store's stamp as the boundary
- **Then** the snapshot is merged and its new model lands in the store
- **Test:** `tests/test_ingest_watermark.py::test_a_snapshot_newer_than_the_store_is_merged`

#### Scenario: a snapshot at the boundary is already in the store

- **Given** a raw snapshot captured at exactly the store's `generated_utc`
- **When** ingest runs with that stamp as the boundary
- **Then** it is not merged — the rule is strictly newer
- **Test:** `tests/test_ingest_watermark.py::test_a_snapshot_at_the_boundary_is_already_in_the_store`

#### Scenario: a snapshot with no usable date is still merged

- **Given** a raw snapshot with no `generated_utc` and no filename stamp
- **When** ingest runs with a boundary set
- **Then** it is merged anyway — the boundary fails open, never dropping a file it cannot date
- **Test:** `tests/test_ingest_watermark.py::test_a_snapshot_with_no_usable_stamp_is_still_merged`

#### Scenario: the filename stamp dates a snapshot with no generated_utc

- **Given** a raw snapshot named `<backend>-<YYYYMMDD>-<HHMMSS>.json` with no `generated_utc`
- **When** ingest runs with a boundary
- **Then** the filename stamp decides: an old name is skipped and a new name is merged
- **Test:** `tests/test_ingest_watermark.py::test_the_filename_stamp_dates_a_snapshot`

### Requirement: The boundary is derived from the store and can be overridden

`main()` MUST derive the boundary from the store's own `generated_utc`, so an
ordinary `make merge` / `make merge-fetch` is incremental with no caller change.
`--since <YYYY-MM-DDTHH:MM:SSZ>` MUST override it, and a malformed stamp MUST
fail loudly rather than silently disabling the boundary. A store with no usable
`generated_utc` MUST read every snapshot.

WHEN the CLI runs without `--since`,
THEN the store's own stamp bounds the merge end to end.

#### Scenario: the CLI derives the boundary from the store

- **Given** a data dir whose store is newer than a raw snapshot, and a second whose store is older
- **When** `scripts/update_trending.py` runs with no `--since`
- **Then** the older snapshot leaves the store untouched and the newer one is merged
- **Test:** `tests/test_ingest_watermark.py::test_the_cli_derives_the_boundary_from_the_store`

#### Scenario: --since overrides the derived boundary

- **Given** a raw snapshot older than the store's `generated_utc`
- **When** the CLI runs with an explicit older `--since`
- **Then** the snapshot is merged — and a malformed `--since` exits non-zero
- **Test:** `tests/test_ingest_watermark.py::test_the_since_flag_overrides_the_derived_boundary`

### Requirement: A corrected snapshot is re-merged, never skipped as old

`self_correct_raw.correct_snapshot` MUST refresh a snapshot's `generated_utc`
when, and only when, it actually changes the file, so a correction applied after
a merge is re-admitted by the next one instead of being skipped as "old". An
already-conformant snapshot MUST be left byte-identical, so the next merge does
not re-read it.

WHEN a snapshot is corrected after the merge that last read it,
THEN its refreshed stamp makes the next merge re-read it.

#### Scenario: a corrected snapshot's stamp is refreshed past the store

- **Given** a raw snapshot that needs correction and a store with an older stamp
- **When** `correct_snapshot` runs
- **Then** the snapshot's `generated_utc` is newer than the store's and the file changed on disk
- **Test:** `tests/test_ingest_watermark.py::test_self_correct_refreshes_a_corrected_snapshot`

#### Scenario: an untouched snapshot is left byte-identical

- **Given** a snapshot that already conforms
- **When** `correct_snapshot` runs a second time
- **Then** the file is unchanged and no stamp is written
- **Test:** `tests/test_ingest_watermark.py::test_self_correct_refreshes_a_corrected_snapshot`

### Requirement: The boundary's tests run where the suite runs

`tests/test_ingest_watermark.py` MUST be executed by `make test` through both the
pytest path and the `_test` fallback chain, so the guard cannot be green by never
running (rule 6d).

WHEN `make test` runs — with pytest present or absent,
THEN the boundary's tests execute.

#### Scenario: the module is in the fallback chain

- **Given** the Makefile's `_test` recipe
- **When** every `tests/test_*.py` is compared against the chain
- **Then** none is missing — the existing guard fails on a test file that no chain member runs
- **Test:** `tests/test_amd_backend.py::test_wiring_parity`
