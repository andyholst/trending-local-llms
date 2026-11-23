# Tasks: fleet-mirror-union-no-duplicates

- [x] Pin the pre-union base revision and the four host-ahead mirrors in `tests/test_fleet_lifecycle.py`
- [x] Add `mirror_units()` / `unexpected_growth()` and compare base -> head as a line+clause multiset (real files, no mocks)
- [x] Assert every landed note needle EXACTLY ONCE, keeping the presence checks and the #1463 single-bullet pin
- [x] Add the RED-first detector self-test (pure addition silent; repeated bullet and interleaved clause red)
- [x] Verify the guard is RED on the pre-dedupe tree (`e27c774`) and GREEN on the deduplicated tree
- [x] Regenerate `OPENSPEC.md` and run `make openspec-check`
- [x] Run the focused module and `make lint` at the exact head
