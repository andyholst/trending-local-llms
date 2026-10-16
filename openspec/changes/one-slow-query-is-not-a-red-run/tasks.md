# Tasks

- [x] 1. Reproduce the shape: scheduled run 38723723638 — `search (cpu)` answered 3 of 4 queries, `aggregate` succeeded, the run was FAILURE on a per-query 3 s budget.
- [x] 2. `scripts/smoke_search.py`: `leg_verdict(total, missed)` — the ONE per-leg decision (majority blocks; a minority does not; a clean leg is silent).
- [x] 3. `main()` decides per leg, prints `SAMPLED: …` for a non-blocking miss, and no longer claims "all backends returned HTTP 200" for a leg that sampled slow.
- [x] 4. `main(probe_fn=None)` seam so a whole leg can be driven offline — the verdict, the summary and the exit code under test are production code.
- [x] 5. `tests/test_smoke_search.py`: `test_one_slow_query_does_not_red_a_leg` + `test_the_run_summary_distinguishes_a_flake_from_a_dead_source`, both called from `main()`.
- [x] 6. Verified RED on `origin/master`'s `smoke_search.py` (2 named failures) and green with the fix (59 checks, 0 failures).
- [x] 7. `findings.md`: `- none` (no new gap; the sibling probe-budget question is the issue's own "not covered").
- [x] 8. `make openspec-check`, `make lint`, `make architecture-check`, `make findings-check` green.
- [x] 9. Commit, push, open the PR (ready for review, never a draft).
