# Tasks — captured-cells-trace-by-measurement-identity (issue #411)

- [x] Red tests first: sibling-trace fixture (variant bucket empty + acquisition class today) and joint/unowned fixture — `tests/test_data_gap_analysis.py::test_a_measurement_captured_under_a_sibling_row_traces_to_the_row_that_owns_the_tuple`, `::test_a_joint_or_unowned_measurement_text_is_never_traced_to_a_row` (the two sibling checks failed red on the pre-change code; the pinning checks were already green)
- [x] `_join_measurement_identity` in `scripts/data_gap_analysis.py`: owners indexed from STORE measurements via `update_trending._cross_model_identity` (one key, rule 6d); captured ENGINE-row text joined only for tuples with exactly one carrier; joint (≥2 carriers) and unowned (0) attributed to nobody
- [x] Wire the join into `captured_text` before its return; extend its docstring with the #411 rule
- [x] `python3 tests/test_data_gap_analysis.py` 249/249 green; `make test` full suite green
- [x] Real-store verification: the analysis run names the flipped cells — a variant whose own post states its footprint moves from the acquisition class to the ingest class, and the four classes still partition the missing set
