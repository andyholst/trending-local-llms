# An unclassifiable query must not flip a proven mirror outage back to `quiet`

**Issues:** #296 (one transport-failed query re-blocked every open PR), complementing #291 and #293
**Capability:** `search-fetch` (the Firecrawl → lightbrd fetch and the `live-smoke` verdict that gates `auto-merge`)

## Why

#292 (merged, `90fc5de`) taught `live-smoke` to tell an upstream outage from a refusal and from a
quiet search, so a down mirror no longer reds every open PR. It excuses an outage **only when
`outage == queries`**. Measured on run **38862487215** (PR #294, rebased onto #292), that is one
query away from the behaviour #291 asked for:

```
[warn] CUDA fetch failed for 'rtx 3090 vs 5090 27b tokens': <urlopen error [Errno 111] Connection refused>
[warn] CUDA fetch failed for 'freetoken gpu llm tokens per second': the target answered HTTP 502 (lightbrd.com | 502: Bad gateway)
… 22 more, every one of them "the target answered HTTP 502" …
[info] fetch outcomes: queries=24 with-hits=0 outage=23 refused=0 failed=1
make: *** [Makefile:427: _validate-fetch] Error 1
```

23 of 24 queries prove the mirror is down (its own `502` page, Firecrawl reporting `success: true`).
One hit a connection-level error. The verdict then came back **`quiet`, exit 1**:

```
[error] the mirror answered 0/24 queries with NO upstream error and 0 model hits — a QUIET SEARCH
        on a reachable mirror: check the query set (SEARCH_GROUPS and the derived model queries)
[error] 24 querie(s) did not answer normally; an outage is only excused when EVERY query is one
```

Two defects in one line of diagnosis:

1. it **blames the query set** for a mirror that answered `502` 23 times — the exact mis-diagnosis
   #291 exists to end;
2. it **re-blocks every open PR**, because `live-smoke` gates `qa-validate`'s `auto-merge`.

A `failed` query is a query we could not classify: a transport error is **not evidence the mirror is
healthy** and **not evidence our configuration is wrong** (that is `refused`). It must not outweigh 23
queries that could be classified. The protection #292 added stays exactly as it was: a mirror that
*answers real pages* and still yields no model is a genuine quiet search and stays red.

## What Changes

- `zero_hit_verdict` excuses an outage when the target's own error page is what **every query we could
  classify** got — `outage > 0`, `refused == 0`, `with_hits == 0`, and no query returned a real page
  (`answered = queries - outage - refused - failed == 0`).
- A `refused` verdict is checked FIRST, so our own misconfiguration always wins over an outage.
- The excused message **names the transport-failed queries** instead of hiding them, and still says it
  is not blocking.
- A wholesale transport failure (`outage == 0`) is unchanged: it proves no outage, so it is never
  excused.
- A mirror that ANSWERED real pages still blocks, even with a failure beside it.

## Not covered

- The outage itself (lightbrd.com's origin is down) — infrastructure, not ours.
- Retrying a `failed` query: a retry policy is its own change.
