# Proposal: engine-meta-guard-agents-row

Issue: #745
PR: #906

## Why

Rule 6c requires a change's guard row in `AGENTS.md` §8 **in the same change**. The
`engine-meta-capture-at-ingest` change (#334, landed via #505 / PR #744) added a guard —
`tests/test_engine_registry.py::test_capture_meta_keeps_the_fixture_covering_the_registry` —
that keeps the refresh commit step naming `tests/fixtures/github_meta.json` in BOTH its lists
(the `git diff --quiet` change check and the `git add` list), but recorded its owed §8 row as a
finding "for review" instead of writing it, as rule 3c requires for a rulebook edit. The guard
shipped registered in `make test` and undiscoverable from the rulebook — the exact drift §8
exists to prevent. #745 is the owed-row issue; this is its dedicated review-required change
(the `owed-guard-rows` pattern).

## What Changes

- **§8 gains one row** naming
  `tests/test_engine_registry.py::test_capture_meta_keeps_the_fixture_covering_the_registry`
  beside the existing `tests/test_engine_registry.py` rows, stating the BOTH-lists failure it
  catches (the fixture dropped from the change check or the `git add` list, so a refresh that
  captured the engine metadata leaves it uncommitted and the next run silently re-ingests
  against a fixture that no longer covers the registry), citing #745 and #505/PR #744.
- **`tests/test_agents_rows.py` gains `test_the_engine_meta_row_is_written`** (7 checks): the
  row is present, names its module, states the both-lists failure, cites the issue and the
  change that owed it, sits beside its sibling rows — and the guard it names is a REAL function
  of that module while the workflow's two commit lists still name the fixture (a row describing
  a moved guard is the #369 defect shape). Verified RED on the pre-change `AGENTS.md` (5 fails,
  naming "row absent") and GREEN after (75/0).

## Impact

`AGENTS.md` (§8 table), `tests/test_agents_rows.py` (one new check function, registered in
`main()`), this OpenSpec change and the regenerated `OPENSPEC.md`. No code, target, stage, job
or image changes.

## Not covered

- The refresh commit step itself and its guard already landed (#505 / PR #744); nothing here
  re-implements them.
- Other open owed-row issues (#369 remains out of scope exactly as
  `land-the-owed-rulebook-rows` declared it) — this change lands the #745 row only.
