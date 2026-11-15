# Proposal: agents8-implement-stream-row-1062

Issue: #1062
PR: #1065

## Why

PR #1057 (issue #833) moved the four `hermes` agent legs from the base image
(`$(DOCKER_RUN …)`, no pytest, no `markdown-it-py`) into the test-capable image
(`$(TEST_RUN …)`), guarded by `tests/test_implement_stream.py`. Its headless leg
could not write the `AGENTS.md` §8 row rule 6c requires (rule 3c protects the
rulebook), so issue #1062 declares it in the owed-row ledger
(`section=8 needle=test_implement_stream`) and `make owed-rows-check` reports it
OUTSTANDING.

## What Changes

- `AGENTS.md` §8 gains the guard-table row for
  `tests/test_implement_stream.py::test_agent_legs_run_in_the_test_image` +
  `::test_markdown_it_is_a_test_image_dependency`, carrying the ledger needle
  `test_implement_stream` contiguously, beside the other suite-seam rows.
- `tests/test_agents_rows.py` pins the row.

## Impact

- Capability: `agents-guard-registry`
- Affected code: `AGENTS.md`, `tests/test_agents_rows.py`
- `make owed-rows-check` reports #1062's row LANDED with `AGENTS.md:<line>`
  evidence.

## Not covered

- No behaviour change (rule 3b additive-only); the landed wiring and its tests
  stay exactly as PR #1057 shipped them.
- Remaining OUTSTANDING ledger rows are separate changes (rule 6g).
