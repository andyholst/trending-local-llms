## ADDED Requirements

### Requirement: The Nov-15 red-run ledger rows carry their landed classification

Every `data/pipeline_failures.json` entry for the diagnosed Nov-15 red runs names the merged change that fixed its class and the guard test that locks it: rows 43716345030, 43716362366, 43718826142 and 43725338063 (qa-validate `OpenSpec gate` failures — the stale generated index on `master` pushes) name `fix_pr: 1082` with `guard: "tests/test_openspec_index_repair.py"`; row 43147240875 (`owed-rows-check` exit 2 over malformed markers) names `fix_pr: 922` with `guard: "tests/test_owed_rows.py"` — so `make issue-verdict` can close each issue on ledger proof (issue #993) and the bot queue stops carrying issues whose class is already fixed.

#### Scenario: The four index-drift rows name the landed keeper sequence

Given the committed ledger entries for runs 43716345030, 43716362366, 43718826142 and 43725338063
When the pin reads them from `data/pipeline_failures.json`
Then each names `fix_pr: 1082` (merged) and `guard: "tests/test_openspec_index_repair.py"` (a module `make test` collects), and every original field the filer wrote is kept (rule 3b)

- **Test:** tests/test_pipeline_failure_guard.py::test_the_nov15_ledger_rows_are_classified_onto_their_landed_guards

#### Scenario: The owed-row exit-2 row names the landed #766 guard

Given the committed ledger entry for run 43147240875 (issue #1039)
When the pin reads it from `data/pipeline_failures.json`
Then it names `fix_pr: 922` (merged) and `guard: "tests/test_owed_rows.py"` (a module `make test` collects), with the original `targets` and `undiagnosed` fields kept (rule 3b)

- **Test:** tests/test_pipeline_failure_guard.py::test_the_nov15_ledger_rows_are_classified_onto_their_landed_guards

#### Scenario: Classified rows let the close-with-proof verdict pass

Given the committed ledger with the five rows raised as above
When the post-merge gate verdict runs with issues #1039–#1043 CLOSED
Then the verdict exits 0 — a closed pipeline failure guarded by a landed test, not laundered prose

- **Test:** tests/test_pipeline_failure_guard.py::test_the_nov15_ledger_rows_are_classified_onto_their_landed_guards
