# Tasks: nerve-check-test-value-marker

- [x] `nerve_key_check` imports `TEST_VALUE_MARKER` from `check_secret_output` and `scan_tree` exempts a marked file — verified by the new suite
- [x] `tests/test_nerve_key_wiring.py::test_marked_test_value_file_is_exempt` green on the new code and RED on `origin/master`'s `scripts/nerve_key_check.py` (3 FAIL: marked-file exempt, marker constant, marker import)
- [x] `make nerve-check` green in the test image; the PR #1274 head file (`9f4266c9`) that failed run `45003287466` passes the shape scan under the fix
- [x] OpenSpec change (proposal, spec, tasks) + index regenerated
- [x] Full local gate run green (`make lint`; `make test` 148 modules green, the only red being this change's own unticked task box)
- [ ] PR opened with the five-section body and `closes #1277`; change recorded and archived at the PR head
