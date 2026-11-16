# Proposal: agents2-owed-row-1014

Issue: #1014
PR: #1064

## Why

Hard rule 2 ("Never fabricate data") is the repo's central data rule, and the
data-gap filer's dedup contract — the filed body must END with its registered
`data-gap-signature` marker line, guard
`tests/test_data_gap_analysis.py::test_the_gap_issue_body_ends_with_a_newline`
(issue #1002, landed by PR #1003) — is the guard that keeps a finding filed
once and never re-filed by amnesia. The headless change that landed the guard
could not write its owed `AGENTS.md` §2 row (rule 3c), so issue #1014 declares
it (`owed-row: section=2 needle=tests/test_data_gap_analysis.py`) and
`make owed-rows-check` reports it OUTSTANDING.

## What Changes

- `AGENTS.md` §2 hard rule 2 gains its guard sentence naming
  `tests/test_data_gap_analysis.py` contiguously (the ledger needle) inside the
  §2 span.
- `tests/test_agents_rows.py` pins the row: the needle must appear in the §2
  span and name the landed issues.

## Impact

- Capability: `agents-guard-registry`
- Affected code: `AGENTS.md`, `tests/test_agents_rows.py`
- `make owed-rows-check` reports #1014's row LANDED with `AGENTS.md:<line>`
  evidence.

## Not covered

- No behaviour change in any script, filer, or contract (rule 3b additive-only).
- The other OUTSTANDING ledger rows (#1062 and siblings) are separate changes
  (rule 6g).
