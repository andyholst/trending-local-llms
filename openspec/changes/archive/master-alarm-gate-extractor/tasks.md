# Tasks: master-alarm-gate-extractor

- [x] `validate_gates_from_trees` is line-oriented, drops `#`/`echo`/`printf` prose lines and quoted spans, and recognises `;`, `|`, `&`, `)`, backtick, quote, whitespace and EOL terminators — verified by the new locks
- [x] `tests/test_master_alarm.py` locks the planted `run: make <newgate>;` (uncovered) and the PR #1242 echo literal (no gate), RED on `origin/master`'s `scripts/master_alarm.py` (`PASSED 38 | FAILED 4`)
- [x] `make test` module green on the new code (`tests/test_master_alarm.py`: `PASSED 42 | FAILED 0`)
- [x] OpenSpec change (proposal, spec, tasks) + index regenerated
- [x] `make lint` and `make architecture-check` green
- [ ] PR opened with the five-section body and `closes #1281`; change recorded and archived at the PR head
