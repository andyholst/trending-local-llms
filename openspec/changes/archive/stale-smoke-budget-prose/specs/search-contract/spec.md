# Spec delta: search-contract (stale-smoke-budget-prose)

## ADDED Requirements

### Requirement: Pipeline prose names the current smoke budget
Every prose description of the live search smoke SHALL name the Makefile-owned
`SEARCH_SMOKE_BUDGET ?= 90` pin instead of the retired 3s cap, and SHALL NOT claim a real
model call runs in the main CI live-smoke job (rule 6t).

#### Scenario: a stale 3s claim returns in the docs
- **Given** any of AGENTS.md, ARCHITECTURE.md, Makefile or qa-validate.yml contains the old cap phrase
- **When** `tests/test_smoke_search.py` runs
- **Then** `test_stale_smoke_budget_prose_is_gone` fails naming that file
- **Test:** tests/test_smoke_search.py

#### Scenario: the historical guard row still documents the old failure
- **Given** the #1224 regression-guard row quotes `--budget 3` as history
- **When** the guard runs
- **Then** it passes — the row is evidence, not a live claim
- **Test:** tests/test_smoke_search.py
