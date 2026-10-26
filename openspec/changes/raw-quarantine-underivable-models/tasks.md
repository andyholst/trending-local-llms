# Tasks

- [x] 1. Write the proposal + `raw-snapshot-quarantine` capability spec for the issue.
- [x] 2. `scripts/self_correct_raw.py`: quarantine an un-derivable model (report loudly, exclude), repair a known model's `hf` from the store, drop an unattributable measurement, and make exit 1 mean "no snapshot could be read".
- [x] 3. `scripts/update_trending.py::ingest_raw_snapshots`: refuse a NEW model whose `hf` normalises to empty, loudly, keeping the rest of the merge.
- [x] 4. `tests/test_raw_quarantine.py` (new) + `tests/test_hf_id.py` updated to the new exit contract.
- [x] 5. Verified RED against `origin/master`'s modules and GREEN after.
- [x] 6. `AGENTS.md` §8 row + `ARCHITECTURE.md` `correct-raw` description updated in the same change.
- [x] 7. `findings.md` written; `OPENSPEC.md` regenerated.
- [x] 8. `make validate`, `make validate-mapped`, `make test`, `make openspec-check`, `make architecture-check` green.
