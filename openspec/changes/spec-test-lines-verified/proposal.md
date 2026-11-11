# A spec's `- **Test:**` line is resolved against the tree, or the gate goes red

**Issue:** #621
**Capability:** `openspec-spec-tests-check` (the resolution of every spec's
`- **Test:**` citation as a gate in `make openspec-check`).

## Why

`AGENTS.md` rule 6f says "a scenario whose test does not exist is a defect" and
that a scenario's `- **Test:**` line names the test that LOCKS the behaviour —
but the gate proves only that the line is PRESENT. Measured: change
`agents-md-footprint-dimensions` cited `tests/test_agents_rows.py::test_the_footprint_sentence_names_every_dimension`
in all four scenarios while the file did not exist on origin/master
(`git ls-tree origin/master tests/ | grep agent_row` → no rows), yet
`make openspec-check` reported every change valid and ticked. The scenario then
locks nothing and the passing gate was the reviewer's only signal that it did.

`make openspec-check` today = `openspec validate --changes` (structure) +
`openspec-tasks-check` (checkboxes) + `openspec-index-check` (index). None of
them resolves a `- **Test:** <path>::<test>` reference against the tree.

## What Changes

- **`scripts/check_openspec_test_lines.py`** — a new gate: for every ACTIVE
  change spec, it parses each `- **Test:**` line, extracts a `<path>::<symbol>`
  reference, and resolves it — the `<path>` must exist in the tree, and for a
  tracked Python module the `<symbol>` must be defined top-level (`def`/`class`/
  module-level assignment). It fails naming the change, the spec file:line and
  the missing target. A `- **Test:**` line that names no `path::symbol` (prose
  or a bare path) is REPORTED as a note, never treated as resolved, and a change
  whose specs carry no Test: references is reported — so a vacuous scan cannot
  read as verified. Archived changes are excluded (they keep the shape they were
  reviewed with).
- **`Makefile`** — new target `make openspec-spec-tests-check`, bundled as a
  dependency of `make openspec-check` (rule 6d: reachable from a make target CI
  runs — `qa-validate` runs `openspec-check`).
- **`tests/test_openspec_spec_tests.py`** — drives the REAL script: proves RED
  against the measured shipped reference (`tests/test_agents_rows.py::test_the_footprint_sentence_names_every_dimension`),
  plus missing-file / prose-span / vacuous-scan / archived-ignored cases, and
  green on the real repository tree.
- **`AGENTS.md`** §8 — a guard row for `tests/test_openspec_spec_tests.py` +
  `make openspec-spec-tests-check` naming the shipped failure and every
  loud-exit behaviour. (Protected file — review-required, rule 3c.)

## Not covered

- **`openspec validate`'s structural checks** — unchanged; this resolves the
  reference half only.
- **A scenario with no `- **Test:**` line at all** — reported by `openspec
  validate` as a structure defect, not re-checked here.
- **The archived `agents-md-footprint-dimensions` change** — excluded by design;
  its reference was corrected to `tests/test_measurement_footprint.py` when the
  prototype change landed and is no longer active.
