# Tasks

- [x] 1. Write the proposal + `raw-snapshot-quarantine` capability spec for issue #382.
- [x] 2. `scripts/self_correct_raw.py`: add the bounded HF-token diagnosis to the `QUARANTINED:` line for an un-derivable `hf` (row link / malformed `hf` / `formats[i].hf` / another row's token / none), leaving the quarantined set, exit code and write rule untouched.
- [x] 3. `tests/test_raw_quarantine.py`: lock every branch of the diagnosis through the REAL command, plus the bounded length, and prove the row is still excluded and the rest still merges.
- [x] 4. Verified RED against `origin/master`'s `self_correct_raw.py` and GREEN after.
- [x] 5. `ARCHITECTURE.md` (`correct-raw` target row + the `scripts/` row) and `AGENTS.md` §8's `test_raw_quarantine.py` row updated in the same change.
- [x] 6. `findings.md` written; `OPENSPEC.md` regenerated.
- [x] 7. `make validate`, `make validate-mapped`, `make test`, `make openspec-check`, `make architecture-check` green.
