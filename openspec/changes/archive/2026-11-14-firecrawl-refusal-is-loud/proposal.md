# A fetch outcome is CLASSIFIED — an outage, a refusal and a quiet search are told apart

**Issues:** #291 (a mirror outage reds `live-smoke`, so no PR can auto-merge), #293 (`--require-hits` says `0 model hits` for every failure)
**Capability:** `search-fetch` (the Firecrawl → lightbrd fetch the searches and the live checks share)

## Why

Every PR's `live-smoke` job went red from ~03:05Z on 2026-10-16:

```
python3 scripts/update_trending.py --fetch --require-hits --dry-run
[error] Firecrawl->lightbrd search returned 0 model hits
[info] X model-hits this run: 0 across ['CUDA', 'Metal', 'CPU', 'ROCm']
```

That message blames the mirror and the query set. Two facts in the same log say
otherwise, and both were measured (runs **38843768204**, **38854399980**):

1. the whole check finished in **6 seconds** — `gather_x` scrapes every query in
   `SEARCH_GROUPS` through Firecrawl, which cannot happen that fast unless the
   answers come back cached;
2. there was **no `[warn]` line at all**, so nothing was raising.

The real cause, measured with the real key on 2026-10-16 (`POST
https://api.firecrawl.dev/v1/scrape`):

```
HTTP 200 {"success": true, "data": {"markdown": "# Bad gatewayError code 502 …",
  "metadata": {"statusCode": 502, "title": "lightbrd.com | 502: Bad gateway", "cacheState": "hit"}}}
```

**lightbrd.com's origin was down** and Cloudflare answered `502` for it — the
home page too, for every Firecrawl result. Firecrawl reports that faithfully and,
crucially, **`success: true`**: it answers 200 of its own and puts the page's real
status in `data.metadata.statusCode`. So the client returned *the error page* as
if it were a page, every query "succeeded" with zero known models, and the check
reported a QUIET SEARCH for a DOWN MIRROR.

An earlier draft of this change assumed Firecrawl "refuses" with
`success: false`. That is a real case (no credits, a bad key, a banned target)
and worth guarding — but it is NOT what happened here, and a refusal-shaped guard
alone leaves the live check exactly as red as before, which the next run proved.

Two defects follow:

* **The diagnosis is wrong** — the same three words (`0 model hits`) covered an
  upstream outage, a Firecrawl refusal and a genuinely quiet search, and the
  message pointed at the query set for all three (#293);
* **It blocks everything** — `live-smoke` gates qa-validate's `auto-merge`, so one
  upstream outage stopped EVERY open PR at once, while `make search-smoke` stayed
  GREEN through it (it printed "all backends returned HTTP 200" for a 502 mirror,
  because Firecrawl's own status was 200) (#291).

## What Changes

- `scripts/update_trending.py`: the fetch outcome is **classified**, never
  collapsed. `fetch_via_firecrawl` raises `FirecrawlRefusal` (no page at all, a
  `success: false` payload, a non-JSON body, a bot wall) or `UpstreamOutage`
  (the page IS the target's own error page: `data.metadata.statusCode >= 500`, or
  Cloudflare's `Error code 5NN` / `5xx-error-landing` page) instead of returning
  either as a page. `gather_x(store, stats)` records
  queries / with-hits / outage / refused / failed, and `zero_hit_verdict(stats)`
  turns those counts into one of three verdicts with the exit code each deserves:
  `outage` (loud, exit 0 — not ours, and it must not block every PR), `refused`
  and `quiet` (loud, exit non-zero). A **partial** outage stays red: an outage is
  only excused when EVERY query is one.
- The scrape endpoint moves behind `FIRECRAWL_SCRAPE_URL` (default unchanged:
  `https://api.firecrawl.dev/v1/scrape`), the same offline seam
  `ENGINE_REGISTRY_META_FILE` already provides, so a test can point the REAL
  client at a REAL local server instead of stubbing it (rule 6m).
- `scripts/smoke_search.py`: `probe` carries the upstream status and gives an
  upstream `>= 500` page its own `OUTAGE` label — loud, never retried, not a
  smoke failure — so the reachability check can no longer call a down mirror
  "all backends returned HTTP 200".
- `tests/test_firecrawl_fetch.py` (new, wired into the `_test` fallback chain):
  a real `http.server` stands in for Firecrawl; the test asserts the request the
  client BUILDS (path, the `Authorization` header, `formats: [markdown]`, the
  lightbrd URL), that a refusal, an outage and a bot wall each raise their own
  class, and — end to end — the exit code of the exact command `live-smoke` runs
  (`--fetch --require-hits --dry-run`), which is the level at which the outage
  actually hurt. Verified RED against `origin/master`.
- `tests/test_smoke_search.py`: the `OUTAGE` label, the upstream status it
  carries, that it is not retried, and that a 403 is not excused as an outage.
- `AGENTS.md` §4 (the classification rule) and §8 (the guard rows).

## Not covered

- **The outage itself.** lightbrd.com being down is not fixable here; the point is
  that the pipeline now SAYS so, loudly, and that one down mirror cannot red every
  PR in the repository.
- `--require-hits` remains a *hit* requirement on a healthy mirror: a quiet search
  and a refusal both still fail. The only case it stops failing is the one that is
  provably not ours.
- The SyntaxWarning `update_trending.py` prints on every run (`invalid escape
  sequence '\ '`, issue #190) — its own issue, its own change.
- The plain-urllib fallback (no `FIRECRAWL_API_KEY`) is untouched: it already
  raises, and lightbrd answers it with 403.
