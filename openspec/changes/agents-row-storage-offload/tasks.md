# Tasks

- [x] 1. Write the proposal + `agents-guard-registry` capability spec for issue #369.
- [x] 2. Derive the row from `openspec/changes/data-gap-storage-offload` tasks 4/5 (the issue body is truncated) rather than guess at it.
- [x] 3. `AGENTS.md` §8: one row naming both guards, the module, both failure modes, and `#364`/PR #366 — placed below the `engine_min_version` rows.
- [x] 4. `tests/test_agents_rows.py::test_the_storage_offload_row_is_written` pins the row's content and its position, and fails when either is lost.
- [x] 5. Verified GREEN (22/22); the test is the one the closed #605 branch wrote, kept because it now pins a row that EXISTS.
- [x] 6. `make openspec-index`, `make openspec-check`, `make architecture-check`, `make lint` green.
