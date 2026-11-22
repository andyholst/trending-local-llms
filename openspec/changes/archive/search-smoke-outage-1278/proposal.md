# Proposal: search-smoke-outage-1278
PR: #1280

Issue: #1278 — a proven mirror outage is pre-empted by the #258 majority rule.

## Why

`live-smoke` measured 4 OUTAGE + 7 TIMEOUT queries on the nvidia leg; `missed * 2 > total` red the leg before the existing `if outages` excuse was reached, so every open PR reddened during a mirror degradation.

## What

Per-leg `outages/ok/fail` counts and a verdict branch: a leg with `outages > 0`, `ok == 0`, `fail == 0` is a proven outage and is not blocked. Any `OK` stays red (#292); an all-TIMEOUT leg with `outages == 0` stays red (#258).

## How

Also lower the Makefile-owned probe budget to 20s and forward it into every pipeline, so a degraded mirror cannot burn the 25-minute job limit.
