# Tasks: dispatch-guard-thread-claims-1569

- [x] Extend `scripts/dispatch_guard.py` to read the ISSUE THREAD and parse the signed `working on`/`dispatch` markers, their machine line (`user@host`) and `createdAt`, replaying newest-wins and clearing on a later `done`/`pr`/`reviewing`.
- [x] Refuse a NEWER ACTIVE claim held by a DIFFERENT named host, naming the holding host, lane and comment id; allow the caller's OWN newest claim; leave an unnameable host unattributed rather than inventing one.
- [x] Forward `MACHINE=<user@host>` and `COMMENTS_FILE=<thread.json>` through `make dispatch-check`; derive the caller's machine id from the host by default.
- [x] Keep every existing refusal intact (closed issue, merged bound PR, ceiling, in-repo registry, `--claim`/`CLAIMS` overlap) as an ADDITIONAL cross-host refusal.
- [x] Fixture-test the parsing offline with recorded threads — no network, no credential values — through both the CLI and the make seam.
- [x] Run `python3 tests/test_dispatch_guard.py`, `make lint`, `make openspec-index` and `make openspec-spec-tests-check`; RED-first proof on a pristine `origin/master` tree.
- [x] Open the PR ready for review with `Closes #1569` in BOTH the title and the body; post the PR-and-handover comment on the issue.
