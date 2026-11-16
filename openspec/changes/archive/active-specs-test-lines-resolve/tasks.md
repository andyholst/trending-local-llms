# Tasks — active-specs-test-lines-resolve (#870)

- [x] The gate refuses a `- **Test:**` line that names no `<path>::<test>` (notes become failures) in `scripts/check_openspec_test_lines.py`
- [x] An ACTIVE change whose specs carry no `- **Test:**` line at all refuses the gate
- [x] `weekly-security-scan`'s self-test scenario cites `scripts/security_scan_self_test.py::main` (zero unresolved citations in the shipped tree)
- [x] `tests/test_openspec_spec_tests.py` asserts the refusals (rule 6c) and pins the shipped tree's zero-NOTE green
- [x] `make openspec-spec-tests-check` and `make openspec-check` run green with no NOTE lines
- [x] `make test` (full suite), `make lint`, `make architecture-check`, `make secret-scan` green; findings recorded
