## ADDED Requirements

### Requirement: The architecture description names the shipped store

`ARCHITECTURE.md` §2 SHALL name the three shipped store files — `data/models.json`, `data/measurements.json` and `data/posts.json` — and `make architecture-check` SHALL fail when the data-flow region drops any one of those names.

#### Scenario: A store filename is dropped from the data-flow region

- **Given** a document whose §2 names all three shipped store files
- **When** one filename is removed and `scripts/architecture_check.py` runs
- **Then** the check reports the missing filename
- **Test:** tests/test_architecture.py::test_a_dropped_store_filename_is_red

#### Scenario: An in-step document names every store file

- **Given** a fixture tree whose §2 names the three store files
- **When** the store-file scan runs
- **Then** it raises no finding
- **Test:** tests/test_architecture.py::test_the_dataflow_region_names_every_shipped_store_file

#### Scenario: The real repository passes the scan

- **Given** the real repository at its current tip
- **When** the store-file scan runs on it
- **Then** §2 names `data/models.json`, `data/measurements.json` and `data/posts.json`
- **Test:** tests/test_architecture.py::test_the_real_document_passes_the_store_file_scan

### Requirement: The store walkthrough explains the flatten seam and per-run variants

`docs/store.md` SHALL explain, from the real files, the three-file shape, the search/trending/retention budgets, the `load_store`/`flatten_store`/`split_store` seam, and why one model carries several per-run t/s footprint variants.

#### Scenario: A reader opens the walkthrough

- **Given** a reader and the three shipped store files
- **When** they open `docs/store.md`
- **Then** the flatten seam and the per-run footprint variants are explained, and every cited store file really ships
- **Test:** tests/test_architecture.py::test_store_docs_explain_the_flatten_seam_and_per_run_variants
