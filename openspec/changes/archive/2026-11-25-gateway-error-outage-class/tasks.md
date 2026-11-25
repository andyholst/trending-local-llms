# Tasks: gateway-error-outage-class

- [x] RED-first guards in `tests/test_firecrawl_fetch.py`: `is_upstream_timeout` accepts a 502/503/`Bad Gateway`/`Service Unavailable` transport error and rejects `connection refused`; a 34-timeouts + one `HTTP 502` run verdicts `outage`/exit 0 while one genuinely answered query verdicts `quiet`/exit 1 — observed RED on the base revision (`PASSED 64 | FAILED 7`, exit 1: the four token checks plus the counter, the verdict and the outage line; the verdict came back `('quiet', 1)`)
- [x] `scripts/update_trending.py::is_upstream_timeout` recognises the gateway-error token set — GREEN on the same module (`[test] ok test_firecrawl_fetch.py`, exit 0), plus a wiring pin that `gather_x` still consults it
- [x] Neighbouring modules green with the fix: `test_smoke_search`, `test_query_coverage` (2 modules passed)
- [x] Update the `ARCHITECTURE.md` §6 row for `scripts/update_trending.py` to name the widened token set, then `make architecture-refresh` — `[architecture-bot] OK the inventory block matches the tree (244 lines)`
- [x] Write `findings/1699.md` and regenerate `OPENSPEC.md`; `make findings-check ISSUE=1699` green (1 finding)
- [ ] Push with the agent identity and open a READY PR carrying `Closes #1699`, then record the PR number on the archived change
