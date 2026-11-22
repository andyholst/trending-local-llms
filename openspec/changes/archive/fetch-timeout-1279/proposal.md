# Proposal: fetch-timeout-1279
PR: #1280

Issue: #1279 — stop live-smoke hanging on unreachable lightbrd links.

## Why

`make validate-fetch` used a hard-coded 30s timeout across ~24 queries and an all-timeout result was reported as a quiet search, so a third-party outage cancelled PR jobs at 25m and blocked auto-merge.

## What

Add a `--fetch-timeout` seam (CI passes 5s), track timeouts separately, and classify a TOTAL timeout/522 as the same non-blocking outage already excused for an all-error-page mirror — while keeping partial timeouts and quiet searches red.

## How

`is_upstream_timeout`, `stats["timeouts"]` and a new `zero_hit_verdict` branch; four offline tests cover the seam and both verdict directions.
