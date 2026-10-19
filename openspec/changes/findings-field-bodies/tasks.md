# Tasks

- [x] 1. The tracked change exists (this directory) before any code edit
- [x] 2. `_fields()` captures a marker's line AND its continuation to the next marker / `## ` heading / blank line
- [x] 3. The four single-line `_FIELD` regexes are gone; a marker must be a bullet carrying a field name
- [x] 4. `parse()` still defaults every field, so a missing `Signature` falls back to the title slug
- [x] 5. `tests/test_file_findings.py::test_a_multiline_field_keeps_its_continuation_lines` files a wrapped finding through the REAL script and asserts the body keeps it
- [x] 6. The same test proves prose quoting another marker is not read as that field
- [x] 7. Verified RED on the pre-change script (`PASSED 29 | FAILED 3`) and GREEN after (`PASSED 33 | FAILED 0`)
- [x] 8. `OPENSPEC.md` regenerated; `openspec-index-check` and `check_openspec_tasks` green
- [x] 9. `make lint`, `make test`, `make architecture-check` and `make openspec-check` green
