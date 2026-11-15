# Proposal: agents2-docstring-inventory-row-947

Issue: #947

## Why

Issue #947 measured that a docstring-only edit under `scripts/` rewrites one
`ARCHITECTURE.md` §10 inventory line, so `make architecture-check`'s staleness
assertion reds a change with no behavior change — green locally, red at CI for
an agent that did not run `make architecture-refresh`. Its fix landed the
staleness gate (`architecture-check` failing on a stale block, pinned by
`tests/test_architecture_bot.py`); the §2 hard-rule sentence it owed
(rule 3c) was declared in the owed-row ledger
(`section=2 needle=a docstring-only edit under scripts/ is enough to stale the inventory block`)
and `make owed-rows-check` reports it OUTSTANDING.

## What Changes

- `AGENTS.md` §2 rule 6h gains the sentence carrying that needle contiguously
  (no backticks inside it), naming the measured defect (#947) and the pin.
- `tests/test_agents_rows.py` pins the §2 sentence.

## Impact

- Capability: `agents-guard-registry`
- Affected code: `AGENTS.md`, `tests/test_agents_rows.py`
- `make owed-rows-check` reports #947's row LANDED with `AGENTS.md:<line>`
  evidence.

## Not covered

- No behaviour change (rule 3b additive-only); the gate and its tests stay as
  landed. Remaining OUTSTANDING ledger rows are separate changes (rule 6g).
