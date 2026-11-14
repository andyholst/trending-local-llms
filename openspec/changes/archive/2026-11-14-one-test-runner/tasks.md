# Tasks

- [x] 1. The tracked change exists (this directory) before any code edit
- [x] 2. The dead `python3 -m pytest … 2>/dev/null ||` branch is gone (pytest is not in the test image)
- [x] 3. `scripts/run_tests.sh` discovers `tests/test_*.py`, runs each in its own process, stops at the first red, and supports `--list`
- [x] 4. `make _test` is one line through that runner
- [x] 5. `tests/test_ci_wiring.py` drives the runner for real: listing, first-red stop + output, green, empty-is-red
- [x] 6. The wiring assertion is removed from `tests/test_amd_backend.py` (issue #192)
- [x] 7. `ARCHITECTURE.md` describes the script and the `test` target's new shape
- [x] 8. `OPENSPEC.md` regenerated; `openspec-index-check` and `check_openspec_tasks` green
- [x] 9. `make lint`, `make test`, `make architecture-check` and `make openspec-check` green
