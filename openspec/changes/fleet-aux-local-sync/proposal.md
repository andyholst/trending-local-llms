# Proposal: fleet-aux-local-sync

Issue: #1198
PR: (unset until opened)

## Why

The #1192 seam provisions the chain's owned blocks (`model:`, `model_aliases:`,
`fallback_providers:`) into every Hermes home, but the local tier's model id also
lives in two blocks the seam does not own: `custom_providers[strata]` and the
`moa:` presets. Measured 2026-11-21 across all 30 host homes: 23 still name the
retired `qwen3.8-flash-next-q2_0` there while the chain's local tier names
`qwen3.8-flash-next-iq3_xxs` (the box no longer serves q2_0). The MoA auxiliary
tool and the strata provider entry would call a retired id.

## What Changes

- New seam `scripts/agent_aux_local_sync.py` + `make agent-aux-local-sync`:
  propagate the chain's `local_fallback` model id into the strata
  `custom_providers` entry (model + models map) and every local-referencing
  `moa:` preset entry, in named homes or all homes including `default`.
- Only those two top-level blocks are touched; every other block stays
  byte-for-byte (verified). Backup `config.yaml.bak-<UTC>`, idempotent,
  `--check` (exit 1 on drift) and `--dry-run`. Refuses (exit 2) when the chain
  names no local tier; no credential needed (writes only local-tier references).
- Standalone tests `tests/test_agent_aux_local_sync.py`.

## Impact

- Affected specs: `fleet-model-chain` (ADDED requirement: the local tier's id
  reaches the host's auxiliary blocks).
- Affected code: new script + test, Makefile target, agents/README.md row.
- Depends on #1192 / PR #1197 (the `local_fallback` tier); stacked on its head,
  rebases onto master once it lands.
