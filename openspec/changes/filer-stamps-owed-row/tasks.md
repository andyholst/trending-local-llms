# Tasks — filer-stamps-owed-row (issue #765)

- [x] 1. The tracked change exists (this directory) before any test edit
- [x] 2. `scripts/owed_row_derive.py` — the ONE derivation (rule 6d): section only
      from `§<id>` / `AGENTS.md section <id>` / `rule <id>` AND only ids that are
      `## <id>.` headings via the ledger's own `owed_rows_check.sections()`; needle
      only from a guard-row identifier the text names (`make <target>`,
      `tests/test_*.py`, `scripts/*.py`, `check_*`)
- [x] 3. `scripts/file_findings.py` runs the derivation on each finding's
      Done-when when no explicit `- **Owed-row:**` field is present, and the
      derived rows render through `bot_markers.owed_row_marker` (ONE writer)
- [x] 4. `scripts/data_gap_analysis.py::issue_body()` stamps the derived rows on
      the gap issue body it composes (`## Owed rulebook rows`)
- [x] 5. `tests/test_filer_owed_rows.py` locks the derivation bounds, both filers
      (real scripts, `gh` stubbed), and the end-to-end read by the REAL
      `owed_rows_check` against the REAL `AGENTS.md` (OUTSTANDING, problems=0)
- [x] 6. The owed §8 row itself lands in `AGENTS.md` (rule 3c), and
      `ARCHITECTURE.md` §6 gains the `scripts/owed_row_derive.py` role +
      `make architecture-refresh` regenerates §10
- [x] 7. Gates green on the exact head: `make lint`, `make test`,
      `make architecture-check`, `make openspec-check`, `make owed-rows-check`
      (the #765 row reports LANDED); `OPENSPEC.md` regenerated
- [ ] 8. PR opened with the five-section body and `closes #765`; the change is
      recorded+archived (`make openspec-record-pr`) on the head that auto-merge
      lands (openspec-archive-check, #779/#866)
