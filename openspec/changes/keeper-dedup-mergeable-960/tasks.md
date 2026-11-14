# Tasks

- [x] 1. Proposal + capability spec `keeper-repair` written for issue #960 (mergeable-only keeper dedup; scenarios each carry their `- **Test:**` reference).
- [x] 2. `.github/workflows/qa-validate.yml`: both keeper land-steps (`index-repair`, `architecture-repair`) fetch `headRefName,mergeStateStatus` in one `gh pr list`, honour ONLY mergeable open keepers (a `DIRTY`/`CONFLICTING` keeper never suppresses), and name the refused keeper `UNMERGEABLE` in the log.
- [x] 3. `tests/test_workflows.py::test_keeper_dedup_counts_only_mergeable_keepers` added and registered in the suite runner.
- [x] 4. Red-on-old-code proof (rule 6c): the new test run against the pre-change `qa-validate.yml` fails with 6 named checks; against the patched tree `tests/test_workflows.py` is green (1098 passed / 0 failed).
- [x] 5. `AGENTS.md` §6q: both keeper paragraphs state the mergeable-only discriminator (rule 3c disclosure comment already posted on issue #960), plus the §8 guard-table row.
- [x] 6. `make openspec-index` lists the new active change; `make openspec-index-check` and `make openspec-check` green.
- [x] 7. Gates green in the branch: `make lint` (incl. the workflow-guard scan), `make openspec-index-check`/`make openspec-check`, and the targeted host suites (`test_workflows` 1098/0, `test_openspec_index` 26/0, `test_architecture` 71/0, `test_master_alarm` 27/0); PR body pre-validated with `make pr-message-check`.
