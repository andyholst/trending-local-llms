# Tasks: rulebook-dispatch-guard-1586

- [x] Add the §7b bold-led bullet naming all four refusal classes plus the cross-host refusal and the 0/1/2 exit contract, between the implementer-PR handover bullet and the planner-delegation bullet.
- [x] Append the ONE `Rule 3c note:` clause at the END of that line, re-read immediately before writing so no sibling clause is overwritten.
- [x] Add the §8 row immediately BEFORE the `tests/test_fleet_lifecycle.py` row, keeping the two-cell shape.
- [x] Add `test_rulebook_section_7b_carries_the_dispatch_guard_bullet` and `test_rulebook_section_8_carries_the_dispatch_guard_row` to the EXISTING `tests/test_dispatch_guard.py` and register both in `main()`.
- [x] RED-first proof: run the two functions verbatim against a scratch copy of pristine base `AGENTS.md` (9 failures), then green on the landed tree (`PASSED 111 | FAILED 0`).
- [x] Run `python3 tests/test_dispatch_guard.py`, `make lint`, `make architecture-check`, `make openspec-index` and `make openspec-check`.
- [x] Open the PR READY with `Closes #1586` in BOTH the title and the body; post the PR-and-handover comment on the issue.
