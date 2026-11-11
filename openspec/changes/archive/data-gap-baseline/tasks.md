# Tasks

- [x] 1. Write the proposal + capability spec for issue #174 (`data-gap-baseline`: the target, the host-side rule, the file-equals-`analyse(store)` contract, the wiring).
- [x] 2. `Makefile` — `data-gap-baseline`, host-side, running `--write-baseline` (and the comment saying why it is not in the refresh pipeline).
- [x] 3. `scripts/data_gap_analysis.py` — the usage block documents `--write-baseline` and both baseline writers.
- [x] 4. `tests/test_data_gap_analysis.py` — the wiring test asserts the target, its flag and its host-side shape (rule 6d); a new behavioural test drives `--write-baseline`.
- [x] 5. `tests/test_data_gap_analysis.py` — the written baseline equals `analyse(store)`'s signature and a run against it sees no change and files nothing.
- [x] 6. `ARCHITECTURE.md` (rule 6h): the target in §3's table.
- [x] 7. `AGENTS.md` §8: the `tests/test_data_gap_analysis.py` row names the new guard.
- [x] 8. Verified: `make test`, `make validate`, `make openspec-check`, `make architecture-check`, `make lint` green; the wiring guard shown failing on the pre-change Makefile (2 named checks red).
- [x] 9. `OPENSPEC.md` regenerated (`make openspec-index`).
- [x] 10. `findings.md` written for the gap found while working (the baseline's `as_of` is written but never read, so a stale baseline is invisible); `make findings-check` green.
