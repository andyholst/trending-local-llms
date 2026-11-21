# Proposal: search-smoke-realistic-budget

Issue: #1224
PR: #1225

## Why

`Makefile:916` hardcodes `python3 scripts/smoke_search.py --budget 3`, while the
script's own docstring says a 1-3s budget is *expected to time out before any
200* because a Firecrawl scrape of the lightbrd mirror genuinely takes tens of
seconds on a cache miss. On qa-validate run `44920165690` all four cpu queries
ended at exactly `3.0s` with `http=0` — the client alarm fired before Firecrawl
answered. The majority rule (issue #258) then correctly red the leg, so every
open PR with a green `validate` stayed unmergeable on `live-smoke` even though
the source was reachable. Lowering the majority threshold or excusing timeouts
would hide a genuinely dead mirror, which is the one failure this gate exists
to catch.

## What Changes

- One Makefile-owned `SEARCH_SMOKE_BUDGET ?= 90` pin; `_search-smoke` uses it,
  and the public `search-smoke` recipe forwards it into the container.
- Both pipelines (`qa-validate.yml` `live-smoke` and `refresh-bot.yml`
  reachability step) pass `SEARCH_SMOKE_BUDGET=90` explicitly and name the new
  budget in their step titles.
- A test that fails on the old hardcoded code, proving the budget is owned in
  the Makefile, is at least 30s, is used by the probe, and is passed by both
  workflows. A legitimately dead source still misses EVERY query and fails.

## Impact

CI search reachability takes longer per cached miss, but it measures the source
instead of the client's alarm. No credential, source URL, keyword list, verdict
rule or gate threshold changes; the #258 majority rule and #291 outage rule stay
intact.

## What is not covered

No change to the Firecrawl key, the mirror URL, the curated vocabulary, the
search prompts, or a degraded-mode bypass for a real outage. Host fleet profiles
and the TLL lane handover rules are untouched.
