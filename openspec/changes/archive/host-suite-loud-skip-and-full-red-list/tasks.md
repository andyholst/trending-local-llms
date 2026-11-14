# Tasks: host-suite loud skip and full red list

- [x] 1. OpenSpec change created (proposal + spec + tasks) for issue #890.
- [x] 2. `scripts/run_tests.sh` runs every module past the first red and prints
      the full `FAILED:` list once (exit 1 when any red).
- [x] 3. `tests/test_hermes_update_needed.py` reports a loud `SKIP:` naming
      `faketime` (exit 0) when the tool is absent, instead of a traceback.
- [x] 4. `tests/test_test_runner.py` locks both behaviours by running the real
      runner against fixture dirs (multi-red dir, all-green dir, empty dir) and
      the real update gate with `faketime` off PATH.
- [x] 5. Gates green on the exact head: `make test` (full suite), `make lint`,
      `make openspec-check`, `make openspec-index-check`, `make secret-scan`.
