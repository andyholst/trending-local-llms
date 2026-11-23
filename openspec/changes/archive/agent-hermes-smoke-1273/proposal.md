# Proposal: agent-hermes-smoke-1273
PR: #1274

Issue: #1273 — test the new Hermes Docker image so its calls work.

## Why

Live-smoke and validate reds were traced to external search timeouts, stale generated inventory and a missing PR closing keyword — not to the new image. One offline check should prove the image's Hermes call path is internally consistent.

## What

Add `make agent-hermes-smoke` (`scripts/agent_hermes_smoke.py`) plus fixture tests. It verifies the Makefile/Dockerfile pin agree, the installer is present, the chain has a primary model and credential NAME, and the base_url is https — without a network call or credential value.

## How

Pure filesystem checks with stable `[agent-hermes-smoke] OK/FAIL` output; six planted refusal fixtures stay red.
