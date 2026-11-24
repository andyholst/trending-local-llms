# Proposal: agents-store-rows

Issue: #1482
PR: #1597

## Why

PR #1479 (`fix/store-architecture-doc-1395`, head `92d2612c`) landed #1395's docs
and guard slice — `ARCHITECTURE.md` §2 corrected to the shipped three-file store,
`docs/store.md`, and `scripts/architecture_check.py::store_file_findings` — but the
rule-3c-declared `AGENTS.md` edits were NOT in that tree: the headless leg could not
write the protected file (approval prompt timed out), so they survive only as a
`- [~] … blocked: rule 3c human sign-off` box in the archived change and as thread
prose on #1395 (`issuecomment-7106615088`). Measured at base `663c8d9b`:
`AGENTS.md` names `posts.json` 0 times, `measurements.json` 0 times, `#1395` 0 times
and `store_file_findings` 0 times, so the rulebook's §7b remit and §8 guard table do
not describe the store shape the tree actually ships. No other issue tracked them.

## What Changes

- `AGENTS.md` §7b CHANGE 1: the fleet paragraph names the store architecture page's two
  artifacts — `ARCHITECTURE.md` §2 plus `docs/store.md`.
- `AGENTS.md` §7b CHANGE 2: the `Rule 3c note` gains one clause recording that the
  artifact names were added by issue #1395 and are review-required.
- `AGENTS.md` §8: one regression row for `tests/test_architecture.py`'s data-flow tests
  plus `scripts/architecture_check.py::store_file_findings` (rules 6h/3c, issue #1395),
  inserted beside its existing `test_architecture.py` sibling.
- `tests/test_agents_store_rows.py`: reads the real `AGENTS.md` and locks the three
  texts verbatim, so a later re-wording or dropped row reds.

All three texts are applied VERBATIM from the reviewer's signed approval on #1482
(`issuecomment-7128719625`), which accepted the architect's design
(`issuecomment-7128409545`).

## Impact

Rulebook prose plus one deterministic test. No data, contract, schema, API, table,
workflow or cron change; no line is deleted or restated (the landing is additive).
The `AGENTS.md` diff is review-required under rule 3c, signed off by `tll-reviewer`
on this issue before any implementer touches it.

## Not covered

- The push-and-verify rows (#1423/#1424): landed in lane skills only, rulebook half
  filed separately by `tll-planner`.
- The dispatch-guard rows (#1416/#1458/#1569): owned by #1586.
- `AGENTS.md` §4's flat-store bullet: tracked separately as #1402.
