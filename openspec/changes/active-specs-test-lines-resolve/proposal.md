# active-specs-test-lines-resolve

**Issue:** [#870](https://github.com/andyholst/trending-local-llms/issues/870)

## Why

Rule 6f says every Scenario's `- **Test:**` line names the test that LOCKS it, and calls "a scenario whose test does not exist" a defect. But `scripts/check_openspec_test_lines.py` tolerates a `- **Test:**` line that names no `path::symbol` as a NOTE — printed on every run, green forever. Measured (issue #870): `make openspec-spec-tests-check` printed tolerated NOTEs naming file-plus-prose citations (`weekly-security-scan/specs/weekly-security-scan/spec.md:84` cites `scripts/security_scan_self_test.py` with no symbol); the `weekly-cadence-wednesday` notes named in the issue are gone only because that change was archived. A gate that prints "not resolved" and exits 0 trains readers to skim gate output — the exact failure mode the gate exists to close.

## What Changes

- The gate STOPS tolerating notes: a `- **Test:**` line that names no resolvable `<path>::<test>` is now a FAIL, and an ACTIVE change whose specs carry no `- **Test:**` line at all is a FAIL too. The scan can never again report "OK" while its citations are prose.
- The one live offender is repaired honestly: `weekly-security-scan`'s self-test scenario cites `scripts/security_scan_self_test.py::main` — the real top-level entry that runs the pinned trivy/grype images — so the tree carries zero unresolved citations.
- `tests/test_openspec_spec_tests.py` flips its tolerance assertions to refusal assertions (rule 6c: the tests change with the gate), adds the shipped-tree zero-NOTE pin, and the wiring substring for `openspec-check`'s prerequisite list is kept byte-identical.

## Impact

- Capability: `openspec-test-lines-gate` (the resolution half of `make openspec-check`, run by `qa-validate` on every PR/push).
- Affected: `scripts/check_openspec_test_lines.py`, `tests/test_openspec_spec_tests.py`, `openspec/changes/weekly-security-scan/specs/weekly-security-scan/spec.md`.

## Not covered

- ARCHIVED changes keep the shape they were reviewed with (unchanged exclusion).
- The other ACTIVE change (`attribution-joint-figure-alias`) is another agent's in-flight work — untouched; it already resolves cleanly.
- No new AGENTS.md row is owed: rule 6f already states the contract ("a scenario whose test does not exist is a defect"); this change makes the gate enforce what the rule already said.
