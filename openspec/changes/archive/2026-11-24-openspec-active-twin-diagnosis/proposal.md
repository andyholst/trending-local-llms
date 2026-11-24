# Proposal: openspec-active-twin-diagnosis

Issue: #1477

## Why

A branch can carry an ACTIVE `openspec/changes/<name>/` directory whose name is
ALREADY archived under `openspec/changes/archive/<name>/` — the ordinary shape
when an implementation commit precedes its record commit, or when a branch is cut
from an unmerged PR's head. `scripts/check_openspec_test_lines.py::change_for`
answered `None` whenever the archive copy existed, so the required gate printed
`[openspec-test-lines] FAIL <name>: no active change (archived/missing)` while the
active copy sat in the tree: the message named neither duplicate path nor remedy,
and `scripts/openspec_index.py` counted the same tree as two actives. Measured by
CI run 45275172404 (PR #1475, step `OpenSpec gate`, `make: *** [Makefile:392:
openspec-spec-tests-check] Error 1`).

## What Changes

- `change_for(name)` returns the ACTIVE directory whenever one exists; an archived
  twin no longer hides it.
- New `archived_twin(name)` names the archived copy, so the caller can distinguish
  the two shapes through ONE seam.
- `check_all` FAILS a tree carrying both copies, naming BOTH paths and the exact
  remedy (`git rm -r openspec/changes/<name>` then `make openspec-index`).

## Impact

- `scripts/check_openspec_test_lines.py` — `change_for` semantics plus
  `archived_twin`; no new make target, no workflow edit (rule 6d).
- `tests/test_openspec_spec_tests.py` — the twin diagnosis test (RED on the
  pre-change script: the old `no active change (archived/missing)` line and the
  missing `archived_twin`).
- `AGENTS.md` §8 owes a row naming this guard (rule 3c: review-required, declared
  on #1477 and recorded in `findings.md`).
- `ARCHITECTURE.md` §10 is regenerated from the script docstring in the same change.

## Not covered

- `make openspec-record-pr` refusing to WRITE a second archive of an active change
  (the other site the Done-when allows); the observed failure is the read gate.
- Any change to archiving/index semantics (rule 3b — additive only).
