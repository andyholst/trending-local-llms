# Proposal: local-endpoint-probe-1352

Issue: #1352

## Why

The fleet chain's `local_fallback` tier (issue #1192) points at the owner's own box. When that box
goes silent a lane blocks until its own client timeout before the paid last resort, and **neither
the outage nor the recovery is visible to any gate**: `make agent-model-chain-check` is a static
shape/render gate and stayed green through both states (measured, issue #1194 — `GET /v1/models`
answered 200 with a loaded model on 2026-11-21 while `POST /v1/chat/completions` timed out at 45 s
and 120 s; the same box was connection-refused at 2026-11-22T18:37Z and serving again by
23:35Z). So the chain's provenance can go silently stale and a dead fallback is indistinguishable
from a healthy one.

## What Changes

- `scripts/local_endpoint_probe.py` — the detector, in two halves:
  - `--probe` (live, host-run): reads the `local_fallback` step's OWN `base_url`/`model` from the
    ONE chain (`agents/model_chain.json`), POSTs a one-token chat completion with a **capped**
    timeout, and records the result in the chain's `measured.local` — `last_probe` plus an
    additive `probe_history`. The local tier is credential-less, so no key is read or printed.
  - `--check` (offline, CI): refuses a **missing** record, or one whose endpoint/model no longer
    matches the chain (the record did not follow the chain), and **reports staleness loudly**
    (`STALE age_h=…`) without touching the endpoint.
- `Makefile`: the pins `LOCAL_PROBE_TIMEOUT_SECONDS` (20), `LOCAL_PROBE_MAX_AGE_HOURS` (24),
  `LOCAL_PROBE_HISTORY_MAX` (50), the internal `_local-endpoint-probe`/`_local-endpoint-probe-check`
  recipes, the public `local-endpoint-probe` / `local-endpoint-probe-check` targets, and the offline
  check **bundled into `make lint`** (so `qa-validate` and the fix loop both run it).
- `tests/test_local_endpoint_probe.py`: drives the real seam against a REAL local HTTP server —
  live, dead, slow (capped), missing, drifted and stale records, plus the wiring pins.
- `ARCHITECTURE.md`: the two targets in §3 and the script in §6; §10 regenerated.
- `AGENTS.md` §8: the guard row. Rule 3c: **review-required** — a headless leg cannot write the
  protected rulebook, so the row is declared blocked and filed as its own owed-row issue.

## Impact

A silent local-tier outage becomes a recorded, checkable state instead of an invisible one, and a
stale record is reported. Auto-merge does **not** depend on the box: the live probe is host-run and
the CI half reads only the committed record (a missing/drifted record is red; a merely stale one is
reported). No data format, contract, image or workflow wiring change; no model call; no new cron.

## Not covered

- No change to the chain's shape, the `local_fallback` tier's position, or its credential-less rule.
- No probe of the REMOTE tier (the free catalogue already has `free-model-refresh`, issue #1195).
- No CI dispatch, no merge, no `master` push, no collaborator grant.
