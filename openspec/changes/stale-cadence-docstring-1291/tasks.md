# Tasks: stale-cadence-docstring-1291

- [x] Module docstring names the dispatch-only entry point, no weekly/Wednesday claim — verified by the new test.
- [x] `tests/test_pipeline_failure_issue.py::test_the_module_docstring_names_the_dispatch_only_entry_point` green on the changed head (`PASSED 233 | FAILED 0`) and RED on `origin/master`'s `scripts/pipeline_failure_issue.py` (`PASSED 230 | FAILED 3`).
- [x] `ARCHITECTURE.md` inventory regenerated (`make architecture-refresh`) and `make architecture-check` green.
- [x] `make lint` green; full `make test` 151 modules passed with the only red the circular tasks gate while this box was unticked (re-run after ticking returns rc=0).
- [x] OpenSpec change (proposal, spec with per-scenario tests, tasks) + `OPENSPEC.md` index regenerated.
