# Proposal: gh-json-fields-scope-boundary

Issue: #1675
PR: #1700

## Why

`scripts/gh_json_fields.py` claimed the tree scan means "a call site can never sit outside the
contract silently", and `api_jq_requests` exempted a call with "NO field expression (`--slurp`,
`-f`, `-X POST`) — it names no field to refuse". Both are false for a `gh api` read that picks
its fields in PYTHON: `.get("created_at")` answers `None` for a renamed field at RUN time and
nothing validates it. Measured on `origin/master` = `7d278c154af1f1c2336a98082750167fba5ff05f`
(equal to the design's `e93bc67d`): 32 `gh api` read sites in `scripts/`, 18 of them naming a
REST field in Python and unvalidated.

## What Changes

- The module docstring states the BOUNDARY: only `--jq`/`-q` projections are validated; a
  Python-side `.get()` field pick is OUT OF SCOPE, with the 32/18/2 counts and the
  re-derivation command.
- `api_jq_requests` docstring and the inline exemption comment name the projection-only
  exemption and cite #1675.
- Two module constants pin the boundary machine-checkably:
  `PYTHON_GET_FIELDS_OUT_OF_SCOPE = True` and `UNVALIDATED_PYTHON_API_READ_SITES = 18`.
- `ARCHITECTURE.md` §6 `scripts/gh_json_fields.py` row carries the same boundary sentence.
- `tests/test_gh_json_fields.py` gains `test_the_scope_claim_matches_the_tree`: RED on the base
  revision, GREEN here, NON-VACUOUS (a Python-pick-only scratch tree scans GREEN), with the
  discovery totals (31 discovered / 17 projecting / 14 not) and 5 identity `.[]` projections
  pinned.

## Impact

Docs plus a pinning test only. No scan behaviour change: `python3 scripts/gh_json_fields.py
--scan` stays exit 0 / 0 findings and the discovery totals are unchanged. No data, schema,
contract, API, table, workflow, Makefile or product-behaviour change; the diff is additive
(docstrings, comments, two constants, one §6 clause, one test function).

## Not covered

- Scanning Python-side `.get()` picks (option 1) — filed separately as #1683.
- Any change to `API_SHAPES`, `FIELD_SETS`, `check_argv`, `request()` or the CLI verdicts.
