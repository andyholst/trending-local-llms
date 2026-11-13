# Proposal: rulebook-pipelines-read-bullets-only

Issue: #660
PR: #909

## Why

`scripts/architecture_check.py::rulebook_pipelines()` returns **every backticked token
ending in `.yml` anywhere** in `AGENTS.md` §6b. The guard therefore cannot tell a CLAIM
(a pipeline bullet — the shape §6b requires, `- **`<name>.yml`**` at the start of a line)
from PROSE about the guard itself: while implementing PR #656, the preamble sentence
"a §6b line naming a `.yml` that is not a workflow" made `make architecture-check` report
``AGENTS.md §6b names `.yml`, which is not a workflow`` and exit 1. The only paragraph
that documents the failure mode it prevents turns the check red, so the next contributor
either drops the explanation or weakens the check (measured, issue #660).

## What Changes

- `rulebook_pipelines()` reads the section's pipeline **bullets only**: a claim is a line
  starting ``- **`<name>.yml`** ``. A backticked `.yml` inside prose is no longer a claim.
- `tests/test_architecture.py` gains the case the fix exists for: a prose sentence naming a
  backticked `.yml` does NOT register as a pipeline claim, while a bullet naming `ghost.yml`
  still is (the existing ghost test stays green).

## Impact

`scripts/architecture_check.py` (one reader), `tests/test_architecture.py` (one test). No
target, stage, job, image or `AGENTS.md` rule changes.

## Not covered

- Any other backticked-token reader in the checker (`described_targets` etc.) — §6b's
  bullet shape is the only claim grammar the issue names.
