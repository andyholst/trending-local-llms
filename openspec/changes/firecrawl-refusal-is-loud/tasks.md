# Tasks

- [x] 1. Write the proposal + spec for the fetch-outcome classification.
- [x] 2. `scripts/update_trending.py`: `fetch_via_firecrawl` raises `FirecrawlRefusal` on a refusal / no page / non-JSON / bot wall and `UpstreamOutage` on the target's own error page (`metadata.statusCode >= 500`, Cloudflare `Error code 5NN`); `FIRECRAWL_SCRAPE_URL` is the endpoint seam (default unchanged).
- [x] 3. `scripts/update_trending.py`: `gather_x(store, stats)` records queries / with-hits / outage / refused / failed; `zero_hit_verdict(stats)` returns `outage` (loud, exit 0) / `refused` / `quiet` (loud, exit non-zero), with a partial outage staying blocking; the run prints the outcome counts (issue #293).
- [x] 4. `scripts/smoke_search.py`: `probe` carries the upstream status, labels an upstream `>= 500` page `OUTAGE` (never retried, not a smoke failure) and a `4xx` page `FAIL`.
- [x] 5. `tests/test_firecrawl_fetch.py`: a real local server drives the REAL client — the request it builds, the refusal, the outage classes, and the END-TO-END exit code of the exact command `live-smoke` runs.
- [x] 6. `tests/test_smoke_search.py`: the `OUTAGE` label as a pytest-collectable test, the upstream status, no retry, and a 403 staying a `FAIL`.
- [x] 7. Wire the new module into the `_test` fallback chain (rule 6d/6m: a test nothing runs).
- [x] 8. Verified RED against `origin/master` (the new checks fail there) and green against this change.
- [x] 9. `AGENTS.md` §4 states the classification rule and §8 gains the guard rows.
- [x] 10. `make test`, `make openspec-check`, `make architecture-check`, `make lint`, `make secret-scan` green.
- [x] 11. File the finding (`make findings-check` + `make file-findings`) — what this change did NOT fix belongs to its own issue.
- [x] 12. Commit, push, update the PR.
