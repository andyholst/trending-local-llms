# Tasks

- [x] 1. The tracked OpenSpec change exists (this directory) before any code edit
- [x] 2. `scripts/data_gap_analysis.py`: `entry_id()` (per-entry hash), `marker()`
      takes an entry id, `already_filed()` consults one entry per call
- [x] 3. `scripts/data_gap_analysis.py`: `issue_body()` / `file_issue()` emit ONE
      `data-gap-signature` marker per claimed entry, and the body ends with a newline
- [x] 4. `scripts/data_gap_analysis.py::main()`: the `--issue` path decides per entry —
      `fresh = [e for e in undecided if already[e][0] is None]`, files ONLY those — so a
      volatile `starved_leg` never re-files the persistent dimensions
- [x] 5. `tests/test_data_gap_analysis.py`: `_GH_STUB`/`_GH_STUB_LABELS` record every
      marker an issue carries (not just the first), and the existing
      `test_a_gap_set_is_filed_once` / label / judged / one-issue tests still pass
- [x] 6. `tests/test_data_gap_analysis.py`:
      `test_a_fluctuating_starved_leg_refiles_only_the_new_entry` proves two runs whose
      signature differs ONLY by a fluctuating `starved_leg` produce NO second filing of the
      persistent dimensions (the issue's planted-test acceptance)
- [x] 7. Gates green: `make test` (data-gap module 274 checks, 0 failed),
      `make lint`, `make openspec-check`, `make openspec-index` + `openspec-index-check`
- [x] 8. `ARCHITECTURE.md`: the `data/gap_baseline.json` data note and the
      `data-gap-issue` target row now describe per-ENTRY dedup (rule 6h)
- [~] 9. `AGENTS.md` §8 gains a guard row for the per-entry dedup — blocked: rule 3c
      human sign-off (AGENTS.md protected in a headless leg), full row recorded verbatim
      in findings.md with the owed-row marker
