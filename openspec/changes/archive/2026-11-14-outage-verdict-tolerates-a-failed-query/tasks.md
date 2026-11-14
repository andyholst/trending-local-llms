# Tasks

- [x] 1. Write the proposal + spec for the outage verdict tolerating an unclassifiable query (#296).
- [x] 2. `scripts/update_trending.py`: `zero_hit_verdict` decides `refused` FIRST and excuses the outage when `outage > 0`, `refused == 0`, `with_hits == 0` and no query answered a real page (`queries - outage - refused - failed == 0`); the excused message names the transport-failed queries and says it is not blocking.
- [x] 3. `tests/test_firecrawl_fetch.py`: `test_a_transport_failed_query_does_not_unmask_a_proven_outage` locks the real run's outcomes (`outage=23 failed=1` → `outage`, exit 0), that no proven outage is ever excused (`outage=0`), that a mirror which ANSWERED real pages still blocks, and that a refusal wins over an outage.
- [x] 4. Verified RED against the pre-change tree (the new checks fail there) and green against this change (54/0 vs 50/4).
- [x] 5. `AGENTS.md` §4 states the classification rule (a `failed` query never disqualifies; a partial outage stays red) and §8's `test_firecrawl_fetch.py` row carries the case.
- [x] 6. `make test`, `make openspec-check`, `make architecture-check`, `make lint`, `make secret-scan` green.
- [x] 7. File the finding — `make findings-check` / `make file-findings`: what this change did NOT fix belongs to its own issue.
- [x] 8. Commit, push, update the PR.
