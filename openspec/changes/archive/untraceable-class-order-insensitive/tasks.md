# Tasks: untraceable-class-order-insensitive

- [x] `tests/test_data_gap_analysis.py:504` changed to `set(...) == {...}`; lines 505-506 and all `scripts/` files byte-identical
- [x] RED-first proof on a reordered copy of the real store: base rc=1 `PASSED 331 | FAILED 1` with the exact FAIL line
- [x] GREEN proof: fixed code on the reordered store rc=0 `PASSED 332 | FAILED 0`, and on the committed base store rc=0 `PASSED 332 | FAILED 0`
- [x] `findings/1826.md` records the measured evidence and the class-boundary non-regression
- [x] OpenSpec change (proposal, capability spec with four Given/When/Then scenarios and resolving Test lines, this fully ticked list) and index regenerated
- [x] Fast offline checks green; no containerised suite; no new schedule, label, data, README, workflow or schema change
- [x] One READY PR whose title and body carry `Closes #1826`, authored as Andy Holst
