# Tasks: refusals-ledger-landing-declaration

- [x] `record_ingest_refusals` writes only when the process declared a landing (`declare_refusals_landing` / `refusals_landing_declared`, `--land-refusals`); an undeclared pass counts and prints the refusals and touches no tracked file — verified by `tests/test_refusals_land_declaration.py::test_an_undeclared_full_ingest_lands_no_refusals`
- [x] The summaries state the refusal's fate honestly (per-file `NOT landed in the refusals ledger`, run total `NONE landed … no declared … --land-refusals`) while keeping the count line the #882 grouping guard reads — verified by `test_an_undeclared_pass_still_reports_every_refusal`
- [x] `--dry-run --land-refusals` exits 2 naming both flags and writes nothing; `--dry-run` alone leaves the whole scratch tree clean — verified by `test_a_dry_run_cannot_declare_a_landing` and `test_a_dry_run_writes_nothing_at_all`
- [x] A declared stage lands the ledger, appends nothing it already holds and grows only counters (rule 3b) — verified by `test_a_declared_delivery_stage_lands_the_ledger`
- [x] The Makefile delivery recipes (`_merge`, `_merge-fetch`, `_fix`) declare the landing and no `--dry-run`/`_validate-*` recipe does — verified by `test_the_makefile_delivery_recipes_declare_the_landing`
- [x] `tests/test_ingest_refusal_ledger.py` declares the landing its fixture simulates (a `make merge` stand-in) so #1148's guards stay honest — verified by that module's 56 checks
- [x] The three modules that measured the churn pass and leave a scratch checkout of HEAD clean — verified by `test_the_measured_suite_modules_leave_the_tree_clean`
- [x] The new guards are RED on the pre-change tree — the module ran in a scratch checkout seeded from `origin/master` (`8d61a42`): `19 passed, 18 failed`, rc=1, naming the churn it refuses to accept (`rows 100 -> 206` records from one undeclared `--since 2000-…` pass, 255 refusals landed, `--land-refusals` not even a flag the old CLI knows)
- [x] AGENTS.md §8 guard row added (the `#1148` row's `make validate` twice claim amended to the narrowed rule)
- [x] OpenSpec change (proposal, spec with per-scenario tests, tasks) + `make openspec-index` (the index row for `refusals-ledger-landing-declaration` is generated)
- [x] Local gate run green (`make lint`, the refusal-ledger + grouping + gap-analysis suites, `make secret-scan`, `make openspec-check`, `make architecture-check`)
- [x] PR opened with the five-section body and one `closes #1155` (auto-merge then gates `validate` + `live-smoke` on the head commit)
