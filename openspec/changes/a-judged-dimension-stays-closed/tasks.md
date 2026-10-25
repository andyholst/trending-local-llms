# Tasks

- [x] 1. Write the proposal + `data-gap-analysis` capability spec for issue #491.
- [x] 2. `already_filed()` returns the OPEN issue and the CLOSED ones with `closedAt` (the `gh` read asks for it).
- [x] 3. `dimension_of()` + `judged_dimensions()`; `JUDGED_DAYS = 21`.
- [x] 4. `main()` records a close's stamp per dimension in the baseline and files nothing when every dimension is inside its window, naming each on stderr.
- [x] 5. `write_baseline()` persists `judged` beside `as_of`/`signature`.
- [x] 6. `tests/test_data_gap_analysis.py::test_a_closed_dimension_is_not_re_filed_inside_the_window`: recent close → no filing + baseline stamped; 30-day-old close → filed again.
- [x] 7. Verified RED on `origin/master`'s script (2 failures: it files, and it records no judgement) and GREEN after (186 passed).
- [x] 8. `findings.md` written; `make openspec-check`, `make architecture-check`, `make lint` green.
