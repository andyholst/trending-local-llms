# Proposal: stale-smoke-budget-prose

Issue: #1228
PR: (recorded at head)

## Why

PR #1225 replaced the hardcoded 3s reachability budget with the single Makefile pin
`SEARCH_SMOKE_BUDGET ?= 90`, but four prose locations still described the retired 3s cap
(.github/workflows/qa-validate.yml:15, Makefile:1194, AGENTS.md:1298/1747,
ARCHITECTURE.md:190). Two of them also still promised a real Hermes call in live-smoke,
which rule 6t / #1029 removed. A reader of the pipeline's own header could not trust the
description of the gate that blocks every merge.

## What Changes

- The four prose locations now name `SEARCH_SMOKE_BUDGET ?= 90`; no gate, budget value or
  retry policy changes (the #1224 guard row documenting the old 3s failure is untouched).
- The stale "one real Hermes call through the search alias" claim is replaced with the
  rule-6t statement that no model call gates a merge.
- `tests/test_smoke_search.py::test_stale_smoke_budget_prose_is_gone` fails if any of the
  four phrases returns; the suite stays 74/74.

## Impact

Specs: search-contract (docs only). No code or data change.

## Verification

74/74 smoke tests, validate --only data QA PASSED, architecture-check green, linefeeds green.
