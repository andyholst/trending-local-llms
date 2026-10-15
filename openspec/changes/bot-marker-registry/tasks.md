# Tasks

- [x] 1. Write the proposal + spec for the one marker registry (issue #197).
- [x] 2. `scripts/bot_markers.py`: the registry (bot → kind → name), `ARTIFACTS`, `WRITTEN`, `DECLARED_BY`, the parser (`parse_markers`/`read_marker`/`ts_of`) and the writers (`start_marker`/`end_marker`).
- [x] 3. Route every marker read in `scripts/issue_queue.py` through the registry; make the reviewer union (start OR window) explicit instead of a substring accident.
- [x] 4. `tests/test_bot_markers.py`: round-trip, the two reviewer markers kept distinct, a placeholder refused, every written marker has a writer, AGENTS.md 6j parity; wired into `make _test`.
- [x] 5. `tests/test_issue_review.py`: the two fixtures that used a placeholder `x` for a timestamp now carry real ones (their leniency was the old substring reader).
- [x] 6. AGENTS.md rule 6j marker table + §8 guard row; ARCHITECTURE.md describes `scripts/bot_markers.py`.
- [x] 7. Run `make lint`, `make test`, `make architecture-check`, `make openspec-check`; commit, push, open the PR (closes #197).
