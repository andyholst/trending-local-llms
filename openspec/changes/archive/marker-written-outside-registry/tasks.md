# Tasks

- [x] 1. Write the proposal + `bot-markers` capability spec for issue #474.
- [x] 2. `tests/test_bot_markers.py`: `undeclared_markers()` + `families()` (derived from the registry) and `registered_names()`.
- [x] 3. Three checks: a planted marker in a known family is caught; a dedup key and an alarm marker are not; the real tree writes nothing unregistered.
- [x] 4. Wired into the module's `main()` so `make test` runs it.
- [x] 5. Verified RED on the old file (the reverse check does not exist) and GREEN after.
- [x] 6. `findings.md` written.
- [x] 7. `make openspec-index`, `make openspec-check`, `make architecture-check`, `make lint` green.
