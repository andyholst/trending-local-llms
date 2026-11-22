# Tasks: prechange-guard-fixtures-1292

- [x] Recover authentic pre-change blobs from `e2bad5f6^` and `1a4c1e4e^`
- [x] Replace the two `git show origin/master:` probes with in-memory fixtures
- [x] Add loud authenticity guards so an empty/garbled blob fails closed
- [x] Wire the new guards into both suites' `main()` and update docstrings
- [x] Verify both suites green (9 passed / 7 passed) and no `subprocess` import remains
- [x] Write proposal, capability spec with Given/When/Then + Test lines, and this checklist
- [x] Run `make openspec-check`, `make lint`, `make findings-check`, regenerate `OPENSPEC.md`
- [x] Commit, record PR, open PR and report on issue #1292
