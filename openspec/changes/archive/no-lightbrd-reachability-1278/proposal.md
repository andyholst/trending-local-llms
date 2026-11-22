# Proposal: no-lightbrd-reachability-1278
PR: #1280

Issue: #1278 / #1279 — owner directive: no search reachability to the lightbrd links at all.

## Why

The live Firecrawl → lightbrd probe timed out repeatedly (HTTP 522 / read timeouts), cancelled `live-smoke` at 25 minutes and reddened every PR on a third-party mirror. The probe measured external reachability, not the PR.

## What

Retire the live probe from every pipeline: `make _search-smoke` now runs the OFFLINE probe tests; qa-validate and refresh-bot lose their reachability steps; `scripts/smoke_search.py` remains a manual tool. Add the missing #1278 verdict: a proven outage (outages>0, ok==0, fail==0) is excused, while any real answer alongside outages is a HALF-answering mirror and stays red.

## How

Tests: 77 offline probe checks, 1208 workflow checks, 62 fetch checks; no pipeline calls the live probe.
